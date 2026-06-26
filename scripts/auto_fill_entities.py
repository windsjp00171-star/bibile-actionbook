"""
用 Groq API 自動補充 entities.json 缺少的聖經詞條。
用法：GROQ_API_KEY=xxx python scripts/auto_fill_entities.py
"""
import json, os, re, sys, time
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
ENTITIES_PATH = ROOT / "data" / "entities.json"
BIBLE_PATH = ROOT / "scripture" / "cuv.json"

# ── 1. 掃 cuv.json 找高頻詞候選 ──────────────────────────────────────
print("載入聖經全文...")
bible = json.loads(BIBLE_PATH.read_text(encoding="utf-8"))
entities = json.loads(ENTITIES_PATH.read_text(encoding="utf-8"))
existing = set(entities.keys())

STOPWORDS = {
    "的","了","是","在","他","她","它","我","你","神","主","人","地","天","說",
    "和","也","就","都","但","因","為","以","有","無","不","到","對","從","把",
    "如","其","所","自","於","與","及","或","雖","然後","一個","這個","那個",
    "他們","我們","你們","什麼","怎麼","這樣","那樣","一切","所有","一些",
    "可以","應該","知道","這是","那是","沒有","已經","只是","因此","然而",
    "但是","所以","因為","如果","即使","不過","耶和華","基督","耶穌",
    "以色列","摩西","大衛","亞伯拉罕","上帝","聖靈","萬軍","萬民",
}

freq: Counter = Counter()
for book, chapters in bible.items():
    for ch, verses in chapters.items():
        for v, text in verses.items():
            for m in re.finditer(r'[一-鿿]{2,5}', text):
                w = m.group()
                if w not in existing and w not in STOPWORDS:
                    freq[w] += 1

candidates = [
    w for w, c in freq.most_common(600)
    if c >= 5 and len(w) >= 2
][:250]

print(f"已有 {len(existing)} 個詞條，找到 {len(candidates)} 個候選詞")

if not candidates:
    print("沒有新候選詞，已完成。")
    sys.exit(0)

# ── 2. 呼叫 Groq 批次生成詞條 ──────────────────────────────────────
try:
    from groq import Groq
except ImportError:
    print("請先 pip install groq")
    sys.exit(1)

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("請設定 GROQ_API_KEY 環境變數")
    sys.exit(1)

client = Groq(api_key=api_key)

SYSTEM = """你是聖經詞典助手。我給你一批中文聖經詞語，請判斷哪些是聖經中真正的專有名詞（人名、地名、宗教術語），並為每個生成 JSON。

輸出格式（JSON array）：
[
  {
    "name": "詞語",
    "name_en": "English",
    "type": "person|place|concept",
    "testament": "OT|NT|both",
    "desc": "20-50字說明此詞在聖經中的身份或意義"
  }
]

判斷規則：
- 只收錄明確的聖經專有名詞
- 普通動詞、形容詞、量詞、常用語氣詞一律略過
- desc 必須是具體說明，不能是「聖經中的人物」這種廢話
- 只輸出 JSON array，不加其他文字"""

added_total = 0
BATCH = 25

for i in range(0, len(candidates), BATCH):
    batch = candidates[i:i+BATCH]
    prompt = "請為以下詞語生成詞條（非聖經專有名詞略過）：\n" + "、".join(batch)

    print(f"\n批次 {i//BATCH+1}/{(len(candidates)-1)//BATCH+1}（{len(batch)} 個詞）...", end=" ", flush=True)
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        new_entries = json.loads(raw)
        added = 0
        for entry in new_entries:
            name = entry.get("name", "").strip()
            if name and name not in entities and len(name) >= 2:
                obj = {
                    "type": entry.get("type", "concept"),
                    "name": name,
                    "name_en": entry.get("name_en", ""),
                    "desc": entry.get("desc", ""),
                }
                if "testament" in entry:
                    obj["testament"] = entry["testament"]
                entities[name] = obj
                added += 1

        added_total += added
        print(f"新增 {added}")

        ENTITIES_PATH.write_text(
            json.dumps(entities, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        time.sleep(1)

    except Exception as e:
        print(f"錯誤：{e}")
        continue

print(f"\n完成！共新增 {added_total} 個，總計 {len(entities)} 個詞條。")
