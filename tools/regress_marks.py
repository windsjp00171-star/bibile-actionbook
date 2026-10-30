#!/usr/bin/env python3
"""
回歸檢查：與基準分支比對全本標註，列出「原本標得到、現在標不到」的詞（以及新增的標註數）。

新增詞條可能因字面比對的左邊優先而「吃掉」鄰近字（如新增「以希」會讓「所以希伯崙」的希伯崙失效），
改完 entities.json 後務必跑一次。只印小結。

用法：python tools/regress_marks.py [基準 ref，預設 origin/main]
"""
import os, re, sys, json, subprocess, tempfile, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
tmp = tempfile.mkdtemp()
for rel in ("data/entities.json", "mark_bible.py"):
    os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
    with open(os.path.join(tmp, rel), "wb") as f:
        f.write(subprocess.check_output(["git", "-C", ROOT, "show", f"{ref}:{rel}"]))

CODE = r'''
import sys, re, json
sys.path.insert(0, sys.argv[1])
import mark_bible as mb
cuv = json.load(open(sys.argv[2], encoding="utf-8"))
out = {}
for b, cs in cuv.items():
    for c, vs in cs.items():
        for v, t in vs.items():
            h = mb.annotate(t, b, int(c))
            sp = []; plain = 0; last = 0
            for m in re.finditer(r'<span class="anno[^>]*data-entity="([^"]+)"[^>]*>([^<]+)</span>', h):
                plain += len(re.sub(r"<[^>]+>", "", h[last:m.start()])); w = m.group(2)
                sp.append((plain, plain + len(w), w)); plain += len(w); last = m.end()
            out[f"{b}|{c}|{v}"] = sp
json.dump(out, sys.stdout, ensure_ascii=False)
'''
def run(base):
    env = dict(os.environ)
    env.pop("BIBLE_ENTITIES_PATH", None)
    r = subprocess.run([sys.executable, "-c", CODE, base, os.path.join(ROOT, "cuv.json")],
                       capture_output=True, env=env, check=True)
    return json.loads(r.stdout)

old, new = run(tmp), run(ROOT)
lost = collections.Counter(); ex = {}; allref = {}
gained = 0
for k, o in old.items():
    ns = new[k]
    for (s0, e0, t) in o:
        if not any(s1 <= s0 and e1 >= e0 for (s1, e1, _) in ns):
            lost[t] += 1; ex.setdefault(t, k.replace("|", " ", 1).replace("|", ":")); allref.setdefault(t, []).append(k.replace("|", " ", 1).replace("|", ":"))
gained = sum(len(new[k]) for k in new) - sum(len(old[k]) for k in old)
print(f"# 與 {ref} 比對：標註總數變化 {gained:+d}；真正消失（未被更長標註涵蓋）的詞 {len(lost)} 種（共 {sum(lost.values())} 處）")
for t, n in lost.most_common():
    print(f"  {t} ×{n}  例 {ex[t]}")

if os.environ.get("REGRESS_VERBOSE"):
    for t in os.environ["REGRESS_VERBOSE"].split(","):
        print(t, allref.get(t))
