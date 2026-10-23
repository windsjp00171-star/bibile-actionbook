#!/usr/bin/env python3
"""
用 sparks.bible 的專名標籤（USFM pn）當參照，批次找出我們漏標／疑似誤標的詞。

sparks 的經文 HTML 內嵌 `-bmc-usfm-tag: pn`（人名、地名、族名…），是一份獨立的專名清單。
本工具整卷（或整本）抓下來，與 mark_bible.annotate() 的結果比對，只回「小結」。
這只是**參照**，不是答案：pn 抓到的詞要人工確認、再照 CLAUDE.md 的準確優先原則決定要不要收。
不複製對方的註釋或任何內容，只比對「哪些字被視為專名」。

用法（從 repo 根目錄執行）：
  python tools/sparks_diff.py 使徒行傳            # 整卷漏標，依出現次數排序
  python tools/sparks_diff.py 使徒行傳 13         # 單章，列出逐節
  python tools/sparks_diff.py 創世記 --reverse    # 另外列出我們有標、但 sparks 沒視為專名的詞（疑似誤標）
  python tools/sparks_diff.py --all --limit 60    # 全本掃，只印前 60 筆

對方站台：抓取有 0.3 秒間隔、快取在 .cache/sparks/（請勿提交），同章不會重抓。
版本用 CUNP89T（新標點和合本，繁體）；與 cuv.json 用字若有差異會在小結標示對不上的節數。
"""
import os
import re
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

API = "https://www.sparks.bible/webapi/portal/bible/common/"
VERSION = "CUNP89T"
CACHE = os.path.join(ROOT, ".cache", "sparks")
DELAY = 0.3

_PN = re.compile(r'<span[^>]*usfm-tag:\s*pn[^>]*>(.*?)</span>', re.S)
_TAG = re.compile(r'<[^>]+>')


def _get(path, **params):
    url = API + path + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                d = json.load(r)
            if d.get("code") == 0:
                return d["data"]
        except Exception:
            pass
        time.sleep(1 + attempt)
    return None


def book_codes():
    """cuv.json 書卷順序 ↔ sparks bookCode（兩邊都是標準 66 卷順序）。"""
    path = os.path.join(CACHE, "books.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    data = _get("getBibleBook", versionCode=VERSION)
    codes = [b["bookCode"] for g in data for b in sorted(g["booklist"], key=lambda b: b["sort"])]
    os.makedirs(CACHE, exist_ok=True)
    json.dump(codes, open(path, "w", encoding="utf-8"))
    return codes


def sparks_chapter(code, ch):
    """回傳 {節: [pn 詞…]}；失敗回 None。"""
    path = os.path.join(CACHE, f"{code}_{ch}.json")
    if os.path.exists(path):
        return {int(k): v for k, v in json.load(open(path, encoding="utf-8")).items()}
    time.sleep(DELAY)
    data = _get("getBibleChapter", versionCode=VERSION, bookCode=code, chapterCode=ch)
    if not data:
        return None
    out = {}
    for s in data["sectionList"]:
        if s.get("isTitle"):
            continue
        names = [_TAG.sub("", m).strip().replace("‧", "") for m in _PN.findall(s["contentStyle"])]
        names = [n for n in names if n]
        if names:
            nums = [int(x) for x in re.findall(r"\d+", s["sectionCode"])]
            if not nums:
                continue
            for vn in range(nums[0], nums[-1] + 1):   # 合併節（如 29-30）每節都記
                out.setdefault(vn, []).extend(names)
    os.makedirs(CACHE, exist_ok=True)
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def main():
    import mark_bible
    ap = argparse.ArgumentParser(description="以 sparks.bible 專名標籤比對漏標")
    ap.add_argument("book", nargs="?")
    ap.add_argument("chapter", nargs="?", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--reverse", action="store_true")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--out", help="把完整報告（含全部書卷分布）寫入此檔，終端只印計數")
    a = ap.parse_args()

    cuv = json.load(open(os.path.join(ROOT, "cuv.json"), encoding="utf-8"))
    books = list(cuv)
    codes = book_codes()
    targets = books if a.all else [a.book]
    if not targets or targets == [None] or any(b not in cuv for b in targets):
        sys.exit("請給書卷名（如 使徒行傳）或 --all")

    missing = {}   # 詞 -> [次數, [ref…], 是否已有詞條]
    extra = {}     # 我們標了、sparks 無 pn 的詞 -> [次數, [ref…]]
    mismatch = 0
    for book in targets:
        code = codes[books.index(book)]
        chs = [str(a.chapter)] if a.chapter else list(cuv[book])
        for ch in chs:
            pn = sparks_chapter(code, ch)
            if pn is None:
                print(f"# 抓不到 {book} {ch}，略過")
                continue
            for v, text in cuv[book].get(ch, {}).items():
                html = mark_bible.annotate(text, book, int(ch))
                marked = re.findall(r'data-entity="([^"]+)"[^>]*>([^<]+)</span>', html)
                marked_txt = [t for _, t in marked]
                for name in pn.get(int(v), []):
                    if name not in text:
                        mismatch += 1          # 兩版本用字不同，無法判定
                        continue
                    if any(name in t for t in marked_txt):
                        continue
                    # 只標到名字的片段（如「善以別」只標「以別」）也算漏標，另行註記
                    frag = any(t in name for t in marked_txt)
                    key = name + ("〔碎片〕" if frag else "")
                    m = missing.setdefault(key, [0, [], name in mark_bible.ENTITIES, {}])
                    m[0] += 1
                    m[3][book] = m[3].get(book, 0) + 1
                    if len(m[1]) < 3:
                        m[1].append(f"{book}{ch}:{v}")
                if a.reverse:
                    names = pn.get(int(v), [])
                    for _, t in marked:
                        if not any(t in n or n in t for n in names):
                            e = extra.setdefault(t, [0, []])
                            e[0] += 1
                            if len(e[1]) < 3:
                                e[1].append(f"{book}{ch}:{v}")

    scope = "全本" if a.all else f"{a.book}{(' ' + str(a.chapter)) if a.chapter else ''}"
    items = sorted(missing.items(), key=lambda x: -x[1][0])
    print(f"# {scope}：sparks 視為專名、我們沒標到 {len(items)} 種（共 {sum(m[0] for m in missing.values())} 處）；用字不同略過 {mismatch} 處")
    def line(name, n, refs, known, dist):
        tag = "有詞條但沒標到" if known else "無詞條"
        # 單卷＝同名衝突風險低；多卷＝需人工分群（寧缺勿錯）
        kind = "單卷" if len(dist) == 1 else f"{len(dist)}卷"
        bk = " ".join(f"{b}×{c}" for b, c in sorted(dist.items(), key=lambda x: -x[1]))
        return f"{name} ×{n} [{tag}|{kind}] {bk}  例 {', '.join(refs)}"

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(f"# {scope} 漏標報告（sparks pn 參照）\n")
            for name, (n, refs, known, dist) in items:
                f.write(line(name, n, refs, known, dist) + "\n")
        single = sum(1 for _, m in items if len(m[3]) == 1)
        print(f"# 完整報告已寫入 {a.out}：單卷 {single} 種（風險低）、多卷 {len(items) - single} 種（需分群）")
    else:
        for name, (n, refs, known, dist) in items[: a.limit]:
            print("  " + line(name, n, refs, known, dist))
    if a.reverse:
        ex = sorted(extra.items(), key=lambda x: -x[1][0])[: a.limit]
        print(f"# 我們有標、sparks 沒視為專名（疑似誤標或 sparks 漏，需人工看）{len(extra)} 種")
        for t, (n, refs) in ex:
            print(f"  {t} ×{n}  例 {', '.join(refs)}")
    print("# 註：僅為參照，須人工核對經文、依 CLAUDE.md 準確優先原則決定是否收錄。")


if __name__ == "__main__":
    main()
