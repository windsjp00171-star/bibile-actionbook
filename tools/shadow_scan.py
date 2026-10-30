#!/usr/bin/env python3
"""
掃出「左邊優先」造成的誤標：一個已標的詞 W，與右邊另一個真正專名 L 部分重疊（L 起點在 W 內、終點在 W 外），
L 因此標不到。例：「所以掃羅」被標成「以掃」，吃掉「掃羅」。
輸出 (W, L) 組合、次數與範例，並印出建議的守衛字串（左側加一字，只含 W、不含 L，用來擋掉 W）。
用法：python tools/shadow_scan.py [--limit 60] [--out 檔]
"""
import os, re, sys, json, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import mark_bible as mb
cuv = json.load(open(os.path.join(ROOT, "cuv.json"), encoding="utf-8"))
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 60
pairs = collections.Counter(); ex = {}
for b, cs in cuv.items():
    for c, vs in cs.items():
        c = int(c)
        for v, t in vs.items():
            sel, pos = [], 0
            while True:                                    # 與 annotate() 相同的選取邏輯
                m = mb._ALL_RE.search(t, pos)
                if not m: break
                if mb._is_partial_of_longer(t, m.start(), m.end(), m.group(0)) or not mb.resolve_entity(m.group(0), b, c):
                    pos = m.start() + 1; continue
                sel.append((m.start(), m.end(), m.group(0))); pos = m.end()
            for (s0, e0, w) in sel:
                for i in range(s0 + 1, e0):
                    m = mb._ALL_RE.match(t, i)
                    if not m or m.end() <= e0: continue
                    l = m.group(0)
                    if not mb.resolve_entity(l, b, c) or any(s1 <= i and e1 >= m.end() for s1, e1, _ in sel): continue
                    left = t[s0 - 1] if s0 > 0 else ""
                    key = (w, l, left + w)
                    pairs[key] += 1; ex.setdefault(key, f"{b}{c}:{v} {t[max(0, s0-3):m.end()+3]}")
print(f"# 被吃掉的真專名：{sum(pairs.values())} 處，{len(pairs)} 種組合")
for (w, l, g), n in pairs.most_common(limit):
    print(f"  標「{w}」吃掉「{l}」×{n}  守衛「{g}」  例 {ex[(w,l,g)]}")
