# -*- coding: utf-8 -*-
"""聖經標注預生成腳本（生產級，可斷點續跑）。

逐章掃描 cuv.json，用 Claude Haiku 抽取人物／地名／族群概念，生成 60–100 字
工具書式說明，去重後輸出：
  data/entities.json   全域實體字典 { name: {type, name, name_en, desc, lat, lng, verses} }
  data/annotated.json  已處理章節 [["創世記",1], ...]
  data/gen_progress.json  進度檔（斷點續跑用）

用法：
  pip install anthropic
  export ANTHROPIC_API_KEY=sk-...
  python gen_annotations.py                # 從上次進度接著跑
  python gen_annotations.py --limit 50     # 只跑 50 章（試水溫）
  python gen_annotations.py --book 撒母耳記上   # 只跑單卷

設計重點：
- 同名實體只生成一次說明（known set），保證全本一致、省 API。
- 每章失敗重試 3 次；連續失敗會中止並保留進度，可重跑接續。
- 每 BATCH_SAVE 章存檔一次，中途斷線不丟資料。
- 座標：先請模型給知名地名的近似經緯度（approx=True），日後可用 OpenBible 校正。
"""
import os
import re
import sys
import json
import time
import argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
CUV_PATH = os.path.join(ROOT, "cuv.json")
ENTITIES_PATH = os.path.join(DATA, "entities.json")
ANNOTATED_PATH = os.path.join(DATA, "annotated.json")
PROGRESS_PATH = os.path.join(DATA, "gen_progress.json")

BATCH_SAVE = 20          # 每處理幾章存檔一次
MAX_RETRY = 5            # 單章最大重試
ABORT_AFTER = 15         # 連續失敗幾章就中止（保留進度）

# 太泛、到處都是的稱謂不標注，避免整頁底線噪音
STOPWORDS = {"以色列", "耶和華", "神", "上帝", "主", "以色列人", "耶和華神"}

BOOK_ORDER = [
    ("創世記",50),("出埃及記",40),("利未記",27),("民數記",36),("申命記",34),
    ("約書亞記",24),("士師記",21),("路得記",4),("撒母耳記上",31),("撒母耳記下",24),
    ("列王紀上",22),("列王紀下",25),("歷代志上",29),("歷代志下",36),("以斯拉記",10),
    ("尼希米記",13),("以斯帖記",10),("約伯記",42),("詩篇",150),("箴言",31),
    ("傳道書",12),("雅歌",8),("以賽亞書",66),("耶利米書",52),("耶利米哀歌",5),
    ("以西結書",48),("但以理書",12),("何西阿書",14),("約珥書",3),("阿摩司書",9),
    ("俄巴底亞書",1),("約拿書",4),("彌迦書",7),("那鴻書",3),("哈巴谷書",3),
    ("西番雅書",3),("哈該書",2),("撒迦利亞書",14),("瑪拉基書",4),
    ("馬太福音",28),("馬可福音",16),("路加福音",24),("約翰福音",21),("使徒行傳",28),
    ("羅馬書",16),("哥林多前書",16),("哥林多後書",13),("加拉太書",6),("以弗所書",6),
    ("腓立比書",4),("歌羅西書",4),("帖撒羅尼迦前書",5),("帖撒羅尼迦後書",3),
    ("提摩太前書",6),("提摩太後書",4),("提多書",3),("腓利門書",1),("希伯來書",13),
    ("雅各書",5),("彼得前書",5),("彼得後書",3),("約翰一書",5),("約翰二書",1),
    ("約翰三書",1),("猶大書",1),("啟示錄",22),
]

SYSTEM_PROMPT = """你是聖經工具書的標注助手。讀者閱讀和合本經文時，會點擊人名、地名、族群／概念名詞看背景資料。
你的任務：從給定的一章經文中，抽出**專有名詞實體**，分三類：
- person：具體人物（如 大衛、撒母耳）
- place：地理位置（城、地、山、谷、河，如 伯利恆、以拉谷）
- concept：族群、支派、宗教群體、外邦民族（如 非利士人、利未人、法利賽人）

規則：
1. 只抽和合本經文中**實際出現的詞**，用經文裡的寫法。
2. 每個實體提供：
   - name：經文中的寫法
   - type：person / place / concept
   - name_en：英文名（如 David、Bethlehem）
   - desc：60–100 字繁體中文說明，工具書語氣、客觀，含身份簡述＋在聖經中的角色。
   - 若是 place，**務必**給 lat、lng（該地點的近似經緯度，浮點數）。
3. 不要抽太泛的稱謂：以色列、耶和華、神、主 一律略過。
4. 嚴格只輸出 JSON，格式：
{"entities":[{"name":"大衛","type":"person","name_en":"David","desc":"..."},{"name":"伯利恆","type":"place","name_en":"Bethlehem","desc":"...","lat":31.7,"lng":35.2}]}
不要任何 JSON 以外的文字。"""


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_all(entities, annotated, progress):
    os.makedirs(DATA, exist_ok=True)
    with open(ENTITIES_PATH, "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=1)
    with open(ANNOTATED_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(annotated), f, ensure_ascii=False)
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False)


def extract_json(text):
    """從模型回覆中穩健抽出 JSON 物件。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON found")
    return json.loads(m.group(0))


def setup_llm():
    """偵測可用的 API key，回傳 (provider, model, complete_fn, pace_sec)。
    優先免費：OpenRouter → Groq → Gemini → Anthropic(付費)。complete_fn(user)->str。"""
    or_key = os.environ.get("OPENROUTER_API_KEY")
    groq = os.environ.get("GROQ_API_KEY")
    gem = os.environ.get("GEMINI_API_KEY")
    ant = os.environ.get("ANTHROPIC_API_KEY")

    if or_key:
        import httpx
        ca = "/root/.ccr/ca-bundle.crt"
        proxy = os.environ.get("HTTPS_PROXY")
        model = "google/gemini-flash-1.5:free"

        def complete(user):
            headers = {
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/windsjp00171-star/bibile-actionbook",
            }
            payload = {
                "model": model,
                "temperature": 0.2,
                "max_tokens": 2000,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                ],
            }
            kwargs = {"headers": headers, "json": payload, "timeout": 60}
            if proxy:
                kwargs["proxy"] = proxy
            verify = ca if os.path.exists(ca) else True
            r = httpx.post("https://openrouter.ai/api/v1/chat/completions",
                           verify=verify, **kwargs)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        return "OpenRouter", model, complete, 2.0

    if groq:
        from groq import Groq
        import httpx
        ca = "/root/.ccr/ca-bundle.crt"
        proxy = os.environ.get("HTTPS_PROXY")
        hc = httpx.Client(proxy=proxy, verify=ca if os.path.exists(ca) else True,
                          timeout=60) if proxy else None
        client = Groq(api_key=groq, http_client=hc)
        model = "llama-3.3-70b-versatile"

        def complete(user):
            r = client.chat.completions.create(
                model=model, temperature=0.2, max_tokens=2000,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": user}],
            )
            return r.choices[0].message.content
        return "Groq", model, complete, 2.5

    if gem:
        import google.generativeai as genai
        genai.configure(api_key=gem)
        model = "gemini-2.0-flash"
        gm = genai.GenerativeModel(model, system_instruction=SYSTEM_PROMPT)

        def complete(user):
            r = gm.generate_content(user, generation_config={"temperature": 0.2})
            return r.text
        return "Gemini", model, complete, 4.0

    if ant:
        import anthropic
        client = anthropic.Anthropic()
        model = "claude-haiku-4-5-20251001"

        def complete(user):
            msg = client.messages.create(
                model=model, max_tokens=2000, system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return "Anthropic", model, complete, 0.3

    sys.exit("✗ 沒有任何 API key（GROQ_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY 擇一）。")


def call_chapter(complete, book, chapter, verses_text):
    user = f"書卷：{book}　第 {chapter} 章\n\n經文：\n{verses_text}"
    return extract_json(complete(user))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="最多處理幾章（0=全部）")
    ap.add_argument("--book", type=str, default="", help="只跑指定單卷")
    args = ap.parse_args()

    provider, model, complete, pace = setup_llm()
    print(f"▶ 使用 {provider} / {model}（每章間隔 {pace}s）", flush=True)

    with open(CUV_PATH, encoding="utf-8") as f:
        bible = json.load(f)

    # 以撒上17 範本當種子，確保格式與品質基準一致
    entities = load_json(ENTITIES_PATH, None)
    if entities is None:
        try:
            from data.annotations import ENTITIES as SEED
            entities = dict(SEED)
        except Exception:
            entities = {}
    annotated = set(tuple(x) for x in load_json(ANNOTATED_PATH, []))

    processed = 0
    fails = 0

    targets = [(b, c) for b, n in BOOK_ORDER for c in range(1, n + 1)
               if (not args.book or b == args.book)]

    for book, chapter in targets:
        if (book, chapter) in annotated:
            continue
        if args.limit and processed >= args.limit:
            break
        chap = bible.get(book, {}).get(str(chapter))
        if not chap:
            annotated.add((book, chapter))
            continue
        verses_text = "\n".join(f"{v} {chap[v]}" for v in sorted(chap, key=int))

        ok = False
        for attempt in range(1, MAX_RETRY + 1):
            try:
                result = call_chapter(complete, book, chapter, verses_text)
                for ent in result.get("entities", []):
                    name = (ent.get("name") or "").strip()
                    if not name or name in STOPWORDS:
                        continue
                    if name in entities:
                        continue  # 已有，保留首次說明
                    etype = ent.get("type")
                    if etype not in ("person", "place", "concept"):
                        continue
                    rec = {
                        "type": etype, "name": name,
                        "name_en": ent.get("name_en") or "",
                        "desc": (ent.get("desc") or "").strip(),
                        "verses": f"{book}{chapter}",
                    }
                    if etype == "place" and ent.get("lat") is not None:
                        rec["lat"] = ent["lat"]
                        rec["lng"] = ent["lng"]
                    entities[name] = rec
                ok = True
                break
            except Exception as e:
                print(f"  ! {book}{chapter} 第{attempt}次失敗：{e}", flush=True)
                time.sleep(min(60, 15 * attempt))

        if not ok:
            fails += 1
            print(f"  ✗ {book}{chapter} 放棄（連續失敗 {fails}）", flush=True)
            if fails >= ABORT_AFTER:
                print("✗ 連續失敗過多，中止並保留進度，可重跑接續。", flush=True)
                break
            continue

        fails = 0
        annotated.add((book, chapter))
        processed += 1
        time.sleep(pace)
        if processed % 5 == 0:
            print(f"  … 已處理 {processed} 章，實體累計 {len(entities)}（最近 {book}{chapter}）", flush=True)
        if processed % BATCH_SAVE == 0:
            save_all(entities, [list(x) for x in annotated],
                     {"last": [book, chapter], "processed": processed})

    save_all(entities, [list(x) for x in annotated],
             {"last": None, "processed": processed})
    print(f"✓ 完成這輪：處理 {processed} 章，實體總數 {len(entities)}，已標注 {len(annotated)} 章。", flush=True)


if __name__ == "__main__":
    main()
