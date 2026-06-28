#!/usr/bin/env python3
"""
聖經 / 標註查詢工具 —— 省 token 用。

設計目的：處理漏標回報、驗證標註時，不要把整本 cuv.json（約 3 萬節）
或整包 entities.json 讀進對話視窗。一律用本工具在子程序裡查，只回「小結」。

用法（一律從 repo 根目錄執行）：

  # 全本搜尋關鍵字，列出 卷 章:節（預設不印整節全文，--full 才印）
  python tools/bible_query.py search 歌利亞
  python tools/bible_query.py search 猶大地 --full --limit 40

  # 某名在各卷的出現次數分布（找消歧義範圍用）
  python tools/bible_query.py dist 猶大

  # 測某章標了哪些詞（只印 詞→類型，不印經文）
  python tools/bible_query.py mark 創世記 38
  python tools/bible_query.py mark 馬太福音 2 --verses   # 連同每節標到的詞

  # 測一句話會被標成什麼（直接給文字）
  python tools/bible_query.py marktext 猶大地的伯利恆阿 --book 馬太福音 --chapter 2

  # 查某詞條目前的設定（人物/地名、books、redirect…）
  python tools/bible_query.py entity 猶大

  # 看某節原文（精準定位用）
  python tools/bible_query.py verse 創世記 38 3
  python tools/bible_query.py verse 創世記 38 3-5

  # 抓 Supabase 回報（需設 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY）
  #   —— 一般由 Claude 用 MCP 抓，這裡備援用
  python tools/bible_query.py feedback --limit 50

輸出刻意精簡：能用一行表達就不換行，能回計數就不回全文。
"""
import os
import re
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_CUV = None


def cuv():
    global _CUV
    if _CUV is None:
        with open(os.path.join(ROOT, "cuv.json"), encoding="utf-8") as f:
            _CUV = json.load(f)
    return _CUV


def _book_order():
    # cuv.json 的 key 順序即聖經書卷順序
    return list(cuv().keys())


def cmd_search(args):
    kw = args.term
    hits = []
    for book in _book_order():
        for ch, verses in cuv()[book].items():
            for v, text in verses.items():
                if kw in text:
                    hits.append((book, int(ch), int(v), text))
    print(f"# 「{kw}」共 {len(hits)} 節")
    shown = hits[: args.limit]
    for book, ch, v, text in shown:
        if args.full:
            print(f"{book} {ch}:{v}  {text}")
        else:
            print(f"{book} {ch}:{v}")
    if len(hits) > len(shown):
        print(f"…（還有 {len(hits) - len(shown)} 節，加 --limit 看更多）")


def cmd_dist(args):
    name = args.name
    print(f"# 「{name}」各卷出現次數")
    total = 0
    for book in _book_order():
        c = 0
        for verses in cuv()[book].values():
            for text in verses.values():
                c += text.count(name)
        if c:
            total += c
            print(f"{c:>4}  {book}")
    print(f"# 合計 {total} 次")


def cmd_mark(args):
    import mark_bible
    book, ch = args.book, args.chapter
    chap = cuv().get(book, {}).get(str(ch))
    if not chap:
        print(f"# 找不到 {book} {ch}")
        return
    found = {}  # 詞 -> 類型
    per_verse = []
    for v, text in chap.items():
        html = mark_bible.annotate(text, book, ch)
        spans = re.findall(r'anno-(\w+)"\s+data-entity="([^"]+)"', html)
        if spans:
            per_verse.append((int(v), spans))
        for typ, ent in spans:
            found[ent] = typ
    print(f"# {book} {ch}：共標到 {len(found)} 個不同詞條")
    for ent, typ in sorted(found.items(), key=lambda x: x[1]):
        print(f"  [{typ}] {ent}")
    if args.verses:
        print("# 逐節：")
        for v, spans in per_verse:
            tags = " ".join(f"{e}({t})" for t, e in spans)
            print(f"  {v}: {tags}")


def cmd_marktext(args):
    import mark_bible
    html = mark_bible.annotate(args.text, args.book, args.chapter)
    spans = re.findall(r'anno-(\w+)"\s+data-entity="([^"]+)"', html)
    print(f"# 「{args.text}」（{args.book or '—'} {args.chapter}）")
    if not spans:
        print("  （無標註）")
    for typ, ent in spans:
        print(f"  [{typ}] {ent}")


def cmd_entity(args):
    import mark_bible
    val = mark_bible.ENTITIES.get(args.name)
    if val is None:
        print(f"# 「{args.name}」不在詞條庫")
        return
    print(json.dumps(val, ensure_ascii=False, indent=1))


def cmd_verse(args):
    book, ch, spec = args.book, args.chapter, args.verse
    chap = cuv().get(book, {}).get(str(ch))
    if not chap:
        print(f"# 找不到 {book} {ch}")
        return
    if "-" in spec:
        a, b = spec.split("-")
        vs = range(int(a), int(b) + 1)
    else:
        vs = [int(spec)]
    for v in vs:
        text = chap.get(str(v))
        if text:
            print(f"{book} {ch}:{v}  {text}")


def cmd_feedback(args):
    import urllib.request
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        print("# 未設 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY，略過")
        return
    q = (f"{url}/rest/v1/entity_feedback?select=entity,book,chapter,verse,note,created_at"
         f"&order=created_at.desc&limit={args.limit}")
    req = urllib.request.Request(q, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req) as r:
        rows = json.load(r)
    print(f"# 最近 {len(rows)} 筆回報")
    for x in rows:
        note = (x.get("note") or "").replace("\r", " ").replace("\n", " ")[:40]
        loc = f"{x.get('book')} {x.get('chapter')}"
        if x.get("verse"):
            loc += f":{x['verse']}"
        print(f"  {x.get('entity')} @ {loc}  {note}")


def main():
    p = argparse.ArgumentParser(description="聖經/標註查詢（省 token）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="全本搜尋關鍵字")
    s.add_argument("term")
    s.add_argument("--full", action="store_true", help="印出整節全文")
    s.add_argument("--limit", type=int, default=60)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("dist", help="某名各卷出現次數")
    s.add_argument("name")
    s.set_defaults(func=cmd_dist)

    s = sub.add_parser("mark", help="測某章標了哪些詞")
    s.add_argument("book")
    s.add_argument("chapter", type=int)
    s.add_argument("--verses", action="store_true", help="逐節列出")
    s.set_defaults(func=cmd_mark)

    s = sub.add_parser("marktext", help="測一句話會標成什麼")
    s.add_argument("text")
    s.add_argument("--book", default="")
    s.add_argument("--chapter", type=int, default=1)
    s.set_defaults(func=cmd_marktext)

    s = sub.add_parser("entity", help="查詞條目前設定")
    s.add_argument("name")
    s.set_defaults(func=cmd_entity)

    s = sub.add_parser("verse", help="看某節原文")
    s.add_argument("book")
    s.add_argument("chapter", type=int)
    s.add_argument("verse", help="如 3 或 3-5")
    s.set_defaults(func=cmd_verse)

    s = sub.add_parser("feedback", help="抓 Supabase 回報")
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(func=cmd_feedback)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
