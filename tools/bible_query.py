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

  # 稽核路線：停靠點地名是否對得上引用經文
  python tools/bible_query.py routecheck
  python tools/bible_query.py routecheck --id exodus

  # 掃漏：自動找「含罕用字、卻沒被標」的候選專名（給人工審）
  python tools/bible_query.py gaps 民數記
  python tools/bible_query.py gaps 民數記 1 --limit 20

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


_ROUTE_ABBR = {
    "創": "創世記", "出": "出埃及記", "利": "利未記", "民": "民數記", "申": "申命記",
    "書": "約書亞記", "士": "士師記", "得": "路得記", "撒上": "撒母耳記上", "撒下": "撒母耳記下",
    "王上": "列王紀上", "王下": "列王紀下", "拉": "以斯拉記", "尼": "尼希米記", "詩": "詩篇",
    "賽": "以賽亞書", "耶": "耶利米書", "結": "以西結書", "但": "但以理書", "拿": "約拿書",
    "太": "馬太福音", "可": "馬可福音", "路": "路加福音", "約": "約翰福音", "徒": "使徒行傳",
}
_ROUTE_REF_RE = re.compile(r"^([一-鿿]+?(?:上|下)?)(\d+)(?::(\d+))?")


def _parse_route_ref(ref):
    m = _ROUTE_REF_RE.match(ref or "")
    if not m:
        return None
    pre = m.group(1)
    book = _ROUTE_ABBR.get(pre) or (_ROUTE_ABBR.get(pre[0]) if len(pre) > 1 else None)
    if not book:
        return None
    return book, int(m.group(2)), (int(m.group(3)) if m.group(3) else None)


def cmd_routecheck(args):
    """稽核路線：比對每個停靠點地名是否出現在引用的經文章節，列出對不上的（可能錯/變體）。"""
    with open(os.path.join(ROOT, "data", "routes.json"), encoding="utf-8") as f:
        routes = json.load(f)
    ids = [args.id] if args.id else list(routes.keys())
    total_flags = 0
    for rid in ids:
        r = routes.get(rid)
        if not r:
            print(f"# {rid}: 找不到此路線")
            continue
        flags = []
        for i, w in enumerate(r.get("waypoints", [])):
            name, ref = w.get("name", ""), w.get("ref", "")
            nav = _parse_route_ref(ref)
            if not nav:
                flags.append(f"  ⚠ #{i+1} {name}：ref「{ref}」無法解析")
                continue
            book, ch, _ = nav
            chap = cuv().get(book, {}).get(str(ch), {})
            if not chap:
                flags.append(f"  ⚠ #{i+1} {name}：{book} {ch} 章不存在")
                continue
            joined = "".join(chap.values())
            # 拆解「主名（別名）」「名1／名2」複合顯示格式，任一段落比對到即算通過；
            # 各段再去尾字（山/地/曠野/溪/海/平原/城）比對一次
            parts = re.split("／", re.sub(r"（.*?）", "", name)) + re.findall(r"（(.*?)）", name)
            parts = [p for p in parts if p] or [name]
            found = False
            for p in parts:
                stem = re.sub(r"(山|地|曠野|溪|河|海|平原|城|的.*)$", "", p)
                if p in joined or (stem and stem in joined):
                    found = True
                    break
            if not found:
                flags.append(f"  ⚠ #{i+1} {name}：未在 {book} {ch} 出現（ref={ref}）")
        total_flags += len(flags)
        mark = "✓" if not flags else f"{len(flags)} 處待查"
        print(f"# {rid}（{r.get('name','')}）— {len(r.get('waypoints',[]))} 站，{mark}")
        for fl in flags:
            print(fl)
    print(f"# 合計 {total_flags} 處待人工確認")


_GAP_STOP = set("的了在和與及就是這那你我他祂神主說有要不必他們你們我們將都並又或如若因所以為從到向上下中前後左右大小多少眾各每兩")
_COMMON_WORDS = {
    "以色列", "耶和華", "利未人", "祭司", "會幕", "帳幕", "燔祭", "素祭", "贖罪",
    "安息日", "亞瑪力", "迦南人", "赫人", "希未人", "比利洗人", "耶布斯人", "亞摩利人",
}


def _char_freq():
    """全本聖經各字出現次數（用來判斷哪些是罕用『譯名專用字』）。"""
    freq = {}
    for chs in cuv().values():
        for verses in chs.values():
            for text in verses.values():
                for c in text:
                    freq[c] = freq.get(c, 0) + 1
    return freq


def _name_chars():
    """從現有人名／地名詞條學出『譯名常用字』。"""
    import mark_bible
    chars = set()
    for name, val in mark_bible.ENTITIES.items():
        e = val[0] if isinstance(val, list) else val
        if e.get("type") in ("person", "place"):
            chars.update(name)
    return chars - _GAP_STOP


def cmd_gaps(args):
    """掃漏：找由譯名字組成、含罕用字、卻未被標註的候選詞（給人工審）。"""
    import mark_bible
    nc = _name_chars()
    freq = _char_freq()
    # 罕用『譯名專用字』：是名字字元且全本出現次數低（幾乎只見於譯名）
    rare = {c for c in nc if freq.get(c, 0) <= args.rare}
    known = set(mark_bible.ENTITIES.keys())
    book = args.book
    chs = [str(args.chapter)] if args.chapter else list(cuv().get(book, {}).keys())
    cand = {}   # 候選詞 -> [次數, 首見 ref]
    for ch in chs:
        for v, text in cuv().get(book, {}).get(ch, {}).items():
            html = mark_bible.annotate(text, book, int(ch))
            marked = set(re.findall(r'>([^<>]+)</span>', html))
            # 把已標詞挖空，避免「父葉忒羅」這類黏連假陽性
            scan = text
            for m in sorted(marked, key=len, reverse=True):
                if m:
                    scan = scan.replace(m, " ")
            run = ""
            for c in scan + " ":
                if c in nc:
                    run += c
                else:
                    if (len(run) >= 2 and run not in _COMMON_WORDS and run not in known
                            and any(c in rare for c in run)):       # 至少含一個罕用字
                        cand.setdefault(run, [0, f"{ch}:{v}"])
                        cand[run][0] += 1
                    run = ""
    items = sorted(cand.items(), key=lambda x: -x[1][0])[: args.limit]
    print(f"# {book}{('/' + str(args.chapter)) if args.chapter else ''} 候選漏標 {len(items)} 個（含罕用字、出現多者優先）")
    for w, (n, ref) in items:
        print(f"  {w}  ×{n}  首見 {ref}")
    print("# 註：啟發式候選，需人工確認是否真為專名再決定標註。")


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

    s = sub.add_parser("routecheck", help="稽核路線停靠點與經文是否對得上")
    s.add_argument("--id", default="", help="只查單一路線（預設全查）")
    s.set_defaults(func=cmd_routecheck)

    s = sub.add_parser("gaps", help="掃漏：找候選未標專名")
    s.add_argument("book")
    s.add_argument("chapter", type=int, nargs="?", default=0, help="省略則掃全卷")
    s.add_argument("--limit", type=int, default=40)
    s.add_argument("--rare", type=int, default=120, help="罕用字頻率門檻（全本出現<=此數）")
    s.set_defaults(func=cmd_gaps)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
