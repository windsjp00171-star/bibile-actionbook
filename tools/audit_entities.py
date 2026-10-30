#!/usr/bin/env python3
"""
詞條庫稽核（只讀、只印小結）：找出會靜默失效或明顯可疑的詞條。

  1. 死詞條：key 在其 books/chapters 範圍內的經文中從未出現（標註永遠標不到、也不會報錯）
  2. 資料缺漏：缺 desc／desc 過短／缺 type
  3. 座標異常：lat/lng 不在合理範圍
  4. 類型與說明矛盾：type=person 但說明以「…的城／山／河」收尾，等
  5. 循環定義：說明只是把名字換句話說

用法：python tools/audit_entities.py [--list 類別]
"""
import os, re, sys, json, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ent = json.load(open(os.path.join(ROOT, "data/entities.json"), encoding="utf-8"))
cuv = json.load(open(os.path.join(ROOT, "cuv.json"), encoding="utf-8"))
NT = {"馬太福音","馬可福音","路加福音","約翰福音","使徒行傳","羅馬書","哥林多前書","哥林多後書","加拉太書","以弗所書","腓立比書","歌羅西書","帖撒羅尼迦前書","帖撒羅尼迦後書","提摩太前書","提摩太後書","提多書","腓利門書","希伯來書","雅各書","彼得前書","彼得後書","約翰一書","約翰二書","約翰三書","猶大書","啟示錄"}
verses = [(b, int(c), t) for b, cs in cuv.items() for c, vs in cs.items() for t in vs.values()]
def in_scope(e, b, c):
    if "books" in e and b not in e["books"]: return False
    cr = e.get("chapters")
    if cr and not (cr[0] <= c <= cr[1]): return False
    ts = e.get("testament", "both")
    if "books" not in e and ts != "both" and (ts == "NT") != (b in NT): return False
    return True
dead, thin, geo, mism, circ = [], [], [], [], []
for k, v in ent.items():
    for e in (v if isinstance(v, list) else [v]):
        name = e.get("name", k)
        if not any(k in t and in_scope(e, b, c) for b, c, t in verses):
            dead.append(f"{k}（{','.join(e.get('books', []))[:20] or e.get('testament','')}）")
        d = e.get("desc", "")
        if len(d) < 8 or not e.get("type"): thin.append(k)
        if "lat" in e and not (-90 <= e["lat"] <= 90 and -180 <= e["lng"] <= 180): geo.append(k)
        if e.get("type") == "person" and re.search(r"(的城|城邑|的山|山脈|的河|的谷|地方)[（。；]?$", d.split("（")[0].rstrip("。；")): mism.append(k)
        if re.fullmatch(rf"{re.escape(name)}的?(後裔|子孫|人|族)[。（]?.{{0,6}}", d): circ.append(k)
cat = {"死詞條": dead, "缺漏或過短": thin, "座標異常": geo, "類型與說明可能矛盾": mism, "循環定義": circ}
print(f"# 詞條 {len(ent)} 個鍵")
for n, l in cat.items(): print(f"  {n}：{len(l)}")
if "--list" in sys.argv:
    n = sys.argv[sys.argv.index("--list") + 1]
    print(n, "→", " ".join(cat[n]))
