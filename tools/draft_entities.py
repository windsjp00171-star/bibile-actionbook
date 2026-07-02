#!/usr/bin/env python3
"""
用 Groq（便宜快速）幫漏標回報預先寫草稿 —— 省 Claude token 用。

設計目的：
  逐節查經文、比對現有 1000+ 詞條、判斷消歧義，這件事需要「全局視野」，
  便宜模型單次呼叫做不到，還是要靠 Claude 人工審。
  但草稿的「初稿」——列出候選詞、猜測 type/name_en/desc——是 Groq 可以先做的，
  能大幅減少 Claude 審核時要讀的量。

用法：
  export GROQ_API_KEY=...   # app 本來就用這支 key
  python tools/draft_entities.py 約書亞記 19        # 草擬單章
  python tools/draft_entities.py 約書亞記 19-21     # 草擬章節區間
  python tools/draft_entities.py 士師記 --notes notes.txt  # 附上回報備註提示

輸出：JSON 草稿印到 stdout（可用 > 存檔），格式：
  [{"name":"...", "type":"person|place|concept", "name_en":"...",
    "testament":"OT|NT|both", "desc":"...", "confidence":"high|low",
    "note":"與現有詞條可能衝突/需人工確認的地方"}, ...]

草稿只是「粗胚」，仍需要人工（或下次 Claude session）核對：
  - 是否與現有 entities.json 衝突、需不需要消歧義
  - type 判斷是否正確（人/地/族要看上下文）
  - desc 是否準確（模型可能編造細節，務必對照經文）
"""
import os
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SYSTEM_PROMPT = """你是聖經（和合本）專有名詞標註助手。你會收到一段經文和既有詞條清單，
任務：找出經文中「值得標註但不在既有清單裡」的專有名詞（人名、地名、族名），
排除：一般敘述用詞、族譜「誰生誰」等低價值人名（除非神學上關鍵）、太常見不需標註的詞。

回覆格式：只回 JSON 陣列，每個元素：
{"name": "詞條字面（完全比照經文原文）", "type": "person|place|concept",
 "name_en": "英文/轉寫名（不確定就留空字串）",
 "testament": "OT|NT|both",
 "desc": "一句話描述，必須完全根據你收到的經文內容，不要編造經文沒提到的細節",
 "confidence": "high|low"}

準確優先於數量：不確定的，desc 從簡、confidence 設為 low，不要杜撰。
不要回任何 JSON 以外的文字。"""


def _cuv():
    with open(os.path.join(ROOT, "cuv.json"), encoding="utf-8") as f:
        return json.load(f)


def _existing_names():
    import mark_bible
    return set(mark_bible.ENTITIES.keys())


def _chapter_text(cuv, book, ch):
    chap = cuv.get(book, {}).get(str(ch))
    if not chap:
        return None
    return "\n".join(f"{v}. {t}" for v, t in sorted(chap.items(), key=lambda x: int(x[0])))


def draft_chapter(book, ch, notes=""):
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        print("# 錯誤：未設定 GROQ_API_KEY", file=sys.stderr)
        sys.exit(1)
    from groq import Groq
    client = Groq(api_key=groq_key)

    text = _chapter_text(_cuv(), book, ch)
    if text is None:
        print(f"# 找不到 {book} {ch} 章", file=sys.stderr)
        return []

    existing = _existing_names()
    # 只列出「本章有出現的既有詞條」給模型參考，避免整包 1000+ 塞進 prompt
    present = sorted(n for n in existing if n in text)

    user = (
        f"經文（{book} 第{ch}章）：\n{text}\n\n"
        f"既有詞條（本章已出現、不需要重複列出）：{'、'.join(present) if present else '（無）'}\n"
    )
    if notes:
        user += f"\n讀者回報的提示（可能指出漏標或標錯之處，僅供參考）：\n{notes}\n"

    r = client.chat.completions.create(
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.1, max_tokens=2000,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": user}],
    )
    raw = (r.choices[0].message.content or "").strip()
    # 模型有時會包 ```json 區塊，剝掉
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        print(f"# 警告：{book}{ch} 回應無法解析為 JSON，原始回應：\n{raw}", file=sys.stderr)
        return []
    for it in items:
        it["_ref"] = f"{book} 第{ch}章"
        it["_already_in_db"] = it.get("name") in existing
    return items


def main():
    p = argparse.ArgumentParser(description="用 Groq 預先草擬漏標詞條（省 Claude token）")
    p.add_argument("book")
    p.add_argument("chapters", help="單章如 19，或區間如 19-21")
    p.add_argument("--notes", help="讀者回報備註的文字檔路徑（選填）")
    args = p.parse_args()

    if "-" in args.chapters:
        a, b = args.chapters.split("-")
        chs = range(int(a), int(b) + 1)
    else:
        chs = [int(args.chapters)]

    notes = ""
    if args.notes and os.path.exists(args.notes):
        notes = open(args.notes, encoding="utf-8").read()

    all_items = []
    for ch in chs:
        print(f"# 草擬 {args.book} 第{ch}章…", file=sys.stderr)
        items = draft_chapter(args.book, ch, notes)
        all_items.extend(items)

    print(json.dumps(all_items, ensure_ascii=False, indent=2))
    hi = sum(1 for i in all_items if i.get("confidence") == "high")
    lo = len(all_items) - hi
    print(f"# 共 {len(all_items)} 個候選（高信心 {hi}／低信心 {lo}）— 務必人工審核後才寫入 entities.json", file=sys.stderr)


if __name__ == "__main__":
    main()
