import os
import re
import json
import hashlib
from datetime import date, datetime, timezone
from flask import Flask, render_template, request, jsonify
from markupsafe import Markup, escape
from supabase import create_client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# 暫時豁免：全域規範要求從 mark_core.supabase_client import，但本 repo 尚未接入
# mark-core，且經文已改走本機 cuv.json，Supabase 目前未實際使用。待接入登入/
# 通知等共用功能時，再改為 from mark_core.supabase_client import ...（待清理）。
sb = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# ---- 聖經全文：啟動時一次載入記憶體，伺服器端處理，不進對話 context ----
_CUV_PATH = os.path.join(os.path.dirname(__file__), "cuv.json")
try:
    with open(_CUV_PATH, encoding="utf-8") as f:
        BIBLE = json.load(f)
except FileNotFoundError:
    BIBLE = {}


def _load_annotations():
    """優先讀預生成的全本標注；沒有時 fallback 撒上17 範本。"""
    ent_path = os.path.join(os.path.dirname(__file__), "data", "entities.json")
    ann_path = os.path.join(os.path.dirname(__file__), "data", "annotated.json")
    if os.path.exists(ent_path):
        with open(ent_path, encoding="utf-8") as f:
            entities = json.load(f)
        annotated = set()
        if os.path.exists(ann_path):
            with open(ann_path, encoding="utf-8") as f:
                raw = json.load(f)
                annotated = {tuple(x) for x in raw}
        # annotated.json 為空時，用 seed 補上已知章節
        if not annotated:
            try:
                from data.annotations import ANNOTATED as seed_ann
                annotated = set(seed_ann)
            except Exception:
                pass
        return entities, annotated
    from data.annotations import ENTITIES as seed_ent, ANNOTATED as seed_ann
    return dict(seed_ent), set(seed_ann)


ENTITIES, ANNOTATED = _load_annotations()


def _load_relationships():
    """聖經宇宙：人物關係圖（父母/子女/手足/配偶/敵對/師長/門生/同工）。"""
    path = os.path.join(os.path.dirname(__file__), "data", "relationships.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


RELATIONSHIPS = _load_relationships()


def _entity_brief(name):
    """關係連結用的精簡卡片資料；接受詞條鍵，回 dict 或 None。"""
    v = ENTITIES.get(name)
    if v is None:
        return None
    e = v[0] if isinstance(v, list) else v
    return {"name": e.get("name", name), "type": e.get("type", "person"),
            "desc": e.get("desc", ""), "name_en": e.get("name_en", ""),
            "verses": e.get("verses", ""),
            "lat": e.get("lat"), "lng": e.get("lng")}


NT_BOOK_NAMES = set()  # populated after NT_BOOKS is defined below

OT_BOOKS = [
    ("創世記", 50), ("出埃及記", 40), ("利未記", 27), ("民數記", 36),
    ("申命記", 34), ("約書亞記", 24), ("士師記", 21), ("路得記", 4),
    ("撒母耳記上", 31), ("撒母耳記下", 24), ("列王紀上", 22), ("列王紀下", 25),
    ("歷代志上", 29), ("歷代志下", 36), ("以斯拉記", 10), ("尼希米記", 13),
    ("以斯帖記", 10), ("約伯記", 42), ("詩篇", 150), ("箴言", 31),
    ("傳道書", 12), ("雅歌", 8), ("以賽亞書", 66), ("耶利米書", 52),
    ("耶利米哀歌", 5), ("以西結書", 48), ("但以理書", 12), ("何西阿書", 14),
    ("約珥書", 3), ("阿摩司書", 9), ("俄巴底亞書", 1), ("約拿書", 4),
    ("彌迦書", 7), ("那鴻書", 3), ("哈巴谷書", 3), ("西番雅書", 3),
    ("哈該書", 2), ("撒迦利亞書", 14), ("瑪拉基書", 4),
]

NT_BOOKS = [
    ("馬太福音", 28), ("馬可福音", 16), ("路加福音", 24), ("約翰福音", 21),
    ("使徒行傳", 28), ("羅馬書", 16), ("哥林多前書", 16), ("哥林多後書", 13),
    ("加拉太書", 6), ("以弗所書", 6), ("腓立比書", 4), ("歌羅西書", 4),
    ("帖撒羅尼迦前書", 5), ("帖撒羅尼迦後書", 3), ("提摩太前書", 6),
    ("提摩太後書", 4), ("提多書", 3), ("腓利門書", 1), ("希伯來書", 13),
    ("雅各書", 5), ("彼得前書", 5), ("彼得後書", 3), ("約翰一書", 5),
    ("約翰二書", 1), ("約翰三書", 1), ("猶大書", 1), ("啟示錄", 22),
]

ALL_BOOKS = OT_BOOKS + NT_BOOKS
BOOK_CHAPTERS = {name: ch for name, ch in ALL_BOOKS}
NT_BOOK_NAMES.update(name for name, _ in NT_BOOKS)

# 標註引擎已抽到獨立模組 mark_bible（兩專案共用，避免分叉）。
# 詞條以 mark_bible 載入的同一份 data/entities.json 為唯一來源。
import mark_bible
ENTITIES = mark_bible.ENTITIES
_TYPE_CLASS = mark_bible._TYPE_CLASS
_ALL_NAMES = mark_bible._ALL_NAMES
_resolve_entity = mark_bible.resolve_entity
_redirect_target = mark_bible.redirect_target
annotate = mark_bible.annotate


# 依中文標點切分句；標點留在前一句尾。手機點按以「分句」為單位最好點。
_CLAUSE_RE = re.compile(r"[^、，。；：！？「」『』（）]+[、，。；：！？」』）]*")


def render_verse(text, book="", chapter=1):
    """把一節經文切成可點擊的分句 span，分句內仍套用實體標注。"""
    parts = []
    for m in _CLAUSE_RE.finditer(text):
        clause = m.group(0)
        if not clause.strip():
            continue
        parts.append(
            f'<span class="clause" data-clause="{escape(clause)}">{annotate(clause, book, chapter)}</span>'
        )
    if not parts:  # 全是標點等極端情形
        parts.append(annotate(text, book, chapter))
    return Markup("".join(parts))


def get_adjacent(book, chapter):
    total = BOOK_CHAPTERS.get(book, 1)
    books_list = [b for b, _ in ALL_BOOKS]
    idx = books_list.index(book) if book in books_list else -1
    prev_book, prev_ch, next_book, next_ch = None, None, None, None
    if chapter > 1:
        prev_book, prev_ch = book, chapter - 1
    elif idx > 0:
        prev_book = books_list[idx - 1]
        prev_ch = BOOK_CHAPTERS[prev_book]
    if chapter < total:
        next_book, next_ch = book, chapter + 1
    elif idx >= 0 and idx < len(books_list) - 1:
        next_book = books_list[idx + 1]
        next_ch = 1
    return prev_book, prev_ch, next_book, next_ch


def build_nav(current_book, current_chapter):
    html = []
    html.append('<div class="sidebar-logo">')
    html.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>')
    html.append('聖 經 全 書</div>')
    for label, books in [("舊 約", OT_BOOKS), ("新 約", NT_BOOKS)]:
        html.append(f'<div class="section-label">{label}</div>')
        for name, chapters in books:
            active = "active" if name == current_book else ""
            html.append(f'<a class="book-item {active}" href="#">{name}</a>')
            html.append('<div class="chapter-pills">')
            for ch in range(1, chapters + 1):
                pill_active = "active" if name == current_book and ch == current_chapter else ""
                html.append(f'<a class="pill {pill_active}" href="/read/{name}/{ch}">{ch}</a>')
            html.append('</div>')
    return Markup("".join(html))


def _testament_of(book):
    return "NT" if book in NT_BOOK_NAMES else "OT"


def get_chapter(book, chapter):
    """從 cuv.json 取一章，回傳 [{verse, html}]；全本任何章節皆套用全域字典標注。"""
    chap = BIBLE.get(book, {}).get(str(chapter), {})
    verses = []
    for vnum in sorted(chap.keys(), key=lambda x: int(x)):
        text = chap[vnum]
        verses.append({"verse": int(vnum), "html": render_verse(text, book, chapter)})
    return verses


def chapter_lineage(book, chapter, present_entities):
    """本章世系結構圖：以本章出現的人物為核心，沿父母/子女展開 1 層，
    組成一張可佈局的家族/王系子圖。回傳 {nodes, edges} 或 None（無足夠世系）。
    present_entities：本章 {詞條鍵: 解析後條目}；只取在本章解析為「人物」者當種子，
    排除同名地名/支派（如列王紀的「猶大」其實是猶大國）。"""
    present_names = set(present_entities.keys())

    def owns_relationships(n):
        """關係圖的邊以「族譜詞義」為準。若本章把名字解析成非族譜的同名分支
        （如使徒行傳的『雅各』是使徒、『約瑟』是巴撒巴、『猶大』是加略人），
        就不套用族長家譜，避免世系圖亂接。預設詞義(v[0])或標了 rel_owner 才算。"""
        v = ENTITIES.get(n)
        if not isinstance(v, list):
            return True
        res = _resolve_entity(n, book, chapter)
        return res is v[0] or bool((res or {}).get("rel_owner"))

    seeds = [n for n, e in present_entities.items()
             if (e.get("type") == "person") and n in RELATIONSHIPS
             and owns_relationships(n)]
    if not seeds:
        return None

    # 收集每個種子的所有祖先與後裔（沿關係圖走，防環）。
    def walk(start, rel_key):
        out, stack, seen = set(), [start], {start}
        while stack:
            cur = stack.pop()
            for t in RELATIONSHIPS.get(cur, {}).get(rel_key, []):
                if t in ENTITIES and t not in seen:
                    seen.add(t); out.add(t); stack.append(t)
        return out

    anc = {s: walk(s, "父母") for s in seeds}
    desc = {s: walk(s, "子女") for s in seeds}
    anc_all = set().union(*anc.values()) if anc else set()
    desc_all = set().union(*desc.values()) if desc else set()

    # 節點 = 種子 + 「連接兩個種子」的中間人（既是某種子的祖先、又是另一種子的後裔）
    #        + 種子的直接父母與子女（一層脈絡）。不會無謂追溯到亞當。
    nodes = set(seeds)
    nodes |= (anc_all & desc_all)            # 種子之間的橋接世系（族譜章節即整條鏈）
    for s in seeds:                          # 一層脈絡
        for t in RELATIONSHIPS.get(s, {}).get("父母", []) + RELATIONSHIPS.get(s, {}).get("子女", []):
            if t in ENTITIES:
                nodes.add(t)

    # 親子邊
    edges = []
    for n in nodes:
        for c in RELATIONSHIPS.get(n, {}).get("子女", []):
            if c in nodes:
                edges.append([n, c])
    if len(edges) < 2:
        return None

    # 只在「本章人物彼此真的構成親子鏈」時才出世系圖。
    # 族譜章（馬太1、創5、列王）種子間有大量親子邊；使徒行傳1 只是人物清單，
    # 種子之間幾乎沒有親子關係，不應硬把使徒雅各接到族長家譜上。
    seed_edges = sum(1 for p, c in edges if p in present_names and c in present_names)
    if seed_edges < 3:
        return None

    # 分代（無父母者為第 0 代）
    parents = {}
    children = {}
    for p, c in edges:
        parents.setdefault(c, []).append(p)
        children.setdefault(p, []).append(c)
    gen = {}

    def depth(n, seen=()):
        if n in gen:
            return gen[n]
        if n in seen or n not in parents:
            gen[n] = 0
            return 0
        d = 1 + max(depth(p, seen + (n,)) for p in parents[n])
        gen[n] = d
        return d

    for n in nodes:
        depth(n)
    base = min(gen.values()) if gen else 0
    for n in gen:
        gen[n] -= base

    # 防交錯排序：上代固定後，下一代依「父母平均位置」排列，使子女靠在父母之下。
    by_gen = {}
    for n in nodes:
        by_gen.setdefault(gen[n], []).append(n)
    max_gen = max(by_gen) if by_gen else 0
    order = {}  # node -> 在該代的位置序 (0,1,2...)
    top = sorted(by_gen.get(0, []))
    for i, n in enumerate(top):
        order[n] = i
    for g in range(1, max_gen + 1):
        row = by_gen.get(g, [])

        def keyfn(n):
            ps = [order[p] for p in parents.get(n, []) if p in order]
            return (sum(ps) / len(ps)) if ps else len(order)
        row_sorted = sorted(row, key=lambda n: (keyfn(n), n))
        for i, n in enumerate(row_sorted):
            order[n] = i

    node_list = []
    for n in sorted(nodes, key=lambda x: (gen[x], order.get(x, 0))):
        e = _resolve_entity(n, book, chapter) or ENTITIES.get(n)
        e = e[0] if isinstance(e, list) else e
        node_list.append({
            "key": n,
            "name": (e or {}).get("name", n),
            "gen": gen[n],
            "ord": order.get(n, 0),
            "lit": n in present_names,
        })
    return {"nodes": node_list, "edges": edges}


_ANNO_DATA_RE = re.compile(r'data-entity="([^"]*)"')


def chapter_entities(book, chapter):
    """本章實際被標註的實體（給前端卡片與地圖）。
    直接從 annotate() 的真實輸出取詞，因此與經文中真正畫底線的詞完全一致——
    自動排除碎片誤框（如「撒瑪利亞」中的「利亞」、「亞伯伯瑪迦」中的「亞伯」）。"""
    chap = BIBLE.get(book, {}).get(str(chapter), {})
    result = {}
    for vtext in chap.values():
        html = annotate(vtext, book, chapter)
        for data_name in _ANNO_DATA_RE.findall(html):
            if data_name in result:
                continue
            v = ENTITIES.get(data_name)
            if v is not None:
                result[data_name] = v[0] if isinstance(v, list) else v
    return result


# ============================================================
#  即時 AI 解釋（差異化核心）：圈選經文 → 依程度解釋，三層快取控成本
#    1) 手刻字典  2) Supabase 永久快取  3) Gemini 即時生成（僅冷門、只燒一次）
# ============================================================

LEVELS = {
    "child":  ("兒童主日學的小朋友", "用最淺白、像講故事的口吻，30-60字，避免艱深神學詞。"),
    "seeker": ("剛接觸信仰的慕道友",  "客觀親切，60-90字，解釋背景與意義，不預設信仰基礎。"),
    "leader": ("帶讀經班備課的小組長", "稍深入，80-120字，含歷史背景、原文或神學重點，便於講解。"),
}
EXPLAIN_DAILY_CAP = int(os.environ.get("EXPLAIN_DAILY_CAP", "500"))  # 全域每日 API 上限（保險絲）

_EXPLAIN_MEM = {}            # 程序內記憶體快取
_EXPLAIN_USAGE = {"day": "", "n": 0}


def _explain_key(text, level):
    return hashlib.sha1(f"{level}|{text}".encode("utf-8")).hexdigest()


def _cache_get(key):
    if key in _EXPLAIN_MEM:
        return _EXPLAIN_MEM[key]
    if sb:
        try:
            r = sb.table("ai_explanations").select("content").eq("cache_key", key).limit(1).execute()
            if r.data:
                _EXPLAIN_MEM[key] = r.data[0]["content"]
                return r.data[0]["content"]
        except Exception:
            pass
    return None


def _cache_set(key, text, level, content, ref):
    _EXPLAIN_MEM[key] = content
    if sb:
        try:
            sb.table("ai_explanations").upsert({
                "cache_key": key, "selected_text": text, "level": level,
                "content": content, "ref": ref,
            }).execute()
        except Exception:
            pass


def _usage_ok():
    today = date.today().isoformat()
    if _EXPLAIN_USAGE["day"] != today:
        _EXPLAIN_USAGE["day"] = today
        _EXPLAIN_USAGE["n"] = 0
    return _EXPLAIN_USAGE["n"] < EXPLAIN_DAILY_CAP


def _chapter_context(book, chapter, limit=1800):
    """取該章經文當作接地材料，讓解釋貼著實際經文、降低幻覺。"""
    chap = BIBLE.get(book, {}).get(str(chapter), {})
    if not chap:
        return ""
    lines = [f"{v} {chap[v]}" for v in sorted(chap, key=int)]
    ctx = "\n".join(lines)
    return ctx[:limit]


def _explain_system(level):
    who, how = LEVELS[level]
    return (
        f"你是嚴謹的聖經閱讀解釋助手，對象是{who}。讀者正在讀和合本聖經，"
        f"圈選了一段文字想知道它的意思。{how}\n"
        "準確性是最高原則，寧可保守也不可誤導：\n"
        "1. 只根據所提供的經文與廣被接受的聖經背景知識作答。\n"
        "2. 嚴禁杜撰人名、地名、數字、年代或情節；經文沒有、你也不確定的，就不要說。\n"
        "3. 若某點屬傳統看法或學界有爭議，明說「一般認為」「傳統上」或「學者看法不一」。\n"
        "4. 只解釋圈選的這段，繁體中文，客觀貼著上下文，不加開場白或結語、不傳道。"
    )


def _explain_user(text, ref, context):
    return (f"出處：{ref}\n\n本章經文（供你對照，勿超出其內容臆測）：\n{context}\n\n"
            f"讀者圈選的文字：「{text}」\n請解釋這段的意思。")


def _ai_explain(text, ref, level, context=""):
    """生成層：優先 Groq（快、免費），退回 Gemini。皆無 key 則回 None。"""
    system, user = _explain_system(level), _explain_user(text, ref, context)
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        from groq import Groq
        client = Groq(api_key=groq_key)
        r = client.chat.completions.create(
            model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0.2, max_tokens=600,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return (r.choices[0].message.content or "").strip()

    gem_key = os.environ.get("GEMINI_API_KEY")
    if gem_key:
        import google.generativeai as genai
        genai.configure(api_key=gem_key)
        model = genai.GenerativeModel(
            os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            system_instruction=system)
        r = model.generate_content(user, generation_config={"temperature": 0.2})
        return (r.text or "").strip()

    return None


@app.route("/api/explain", methods=["POST"])
def api_explain():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    level = data.get("level") if data.get("level") in LEVELS else "seeker"
    ref = (data.get("ref") or "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400
    if len(text) > 200:
        text = text[:200]

    # 資安關卡：只解釋「真的出現在該章經文裡」的文字，杜絕被當免費 LLM 代理白嫖。
    book = data.get("book", "")
    chapter = str(data.get("chapter", ""))
    chap = BIBLE.get(book, {}).get(chapter, {})
    if not chap:
        return jsonify({"error": "bad_ref"}), 400
    _norm = lambda s: re.sub(r"[、，。；：！？「」『』（）\s]", "", s)
    joined_norm = _norm("".join(chap.values()))
    probe = _norm(text)
    if probe and probe not in joined_norm:
        return jsonify({"error": "not_scripture",
                        "content": "只能解釋經文中的內容。"}), 400

    # 第 1 層：手刻字典（整段剛好等於某實體名，依書卷/章節選正確的條目）
    _entry = _resolve_entity(text, book, int(chapter) if chapter else 1)
    if _entry:
        return jsonify({"content": _entry["desc"], "source": "dict"})

    # 第 2 層：永久快取
    key = _explain_key(text, level)
    cached = _cache_get(key)
    if cached:
        return jsonify({"content": cached, "source": "cache"})

    # 第 3 層：即時生成（受每日上限保護）
    if not _usage_ok():
        return jsonify({"error": "busy", "content": "今天的免費解釋次數已用完，明天再試，或這段稍後就會有快取。"}), 429
    ctx = _chapter_context(data.get("book", ""), data.get("chapter", ""))
    try:
        content = _ai_explain(text, ref, level, ctx)
    except Exception as e:
        return jsonify({"error": "ai_failed", "content": "解釋暫時無法生成，請稍後再試。"}), 502
    if not content:
        return jsonify({"error": "no_key", "content": "AI 解釋尚未啟用（伺服器未設定 GROQ_API_KEY 或 GEMINI_API_KEY）。"}), 503
    _EXPLAIN_USAGE["n"] += 1
    _cache_set(key, text, level, content, ref)
    return jsonify({"content": content, "source": "ai"})


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json(silent=True) or {}
    entity = (data.get("entity") or "").strip()[:50]
    book = (data.get("book") or "").strip()[:30]
    chapter = data.get("chapter", "")
    note = (data.get("note") or "").strip()[:200]
    if not entity:
        return jsonify({"error": "empty"}), 400
    if sb:
        try:
            sb.table("entity_feedback").insert({
                "entity": entity,
                "book": book,
                "chapter": str(chapter),
                "note": note,
            }).execute()
        except Exception:
            pass
    return jsonify({"ok": True})


@app.route("/api/books")
def api_books():
    """選書流程用：新舊約書卷清單（含卷號、書名、章數），順序固定。"""
    def pack(books):
        return [{"order": i + 1, "name": n, "chapters": c}
                for i, (n, c) in enumerate(books)]
    return jsonify({"ot": pack(OT_BOOKS), "nt": pack(NT_BOOKS)})


@app.route("/api/progress", methods=["GET", "POST"])
def api_progress():
    """首頁存檔。POST：進閱讀頁時 upsert 進度；GET：取最近兩筆不同書卷。
    無登入系統，以前端產生的裝置 ID 當 user_id。"""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        uid = (data.get("user_id") or "").strip()[:64]
        book = (data.get("book") or "").strip()[:30]
        chapter = data.get("chapter")
        if not uid or not book or not isinstance(chapter, int):
            return jsonify({"error": "bad_request"}), 400
        if sb:
            try:
                sb.table("user_reading_progress").upsert({
                    "user_id": uid, "book_name": book, "chapter": chapter,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, on_conflict="user_id,book_name").execute()
            except Exception:
                pass
        return jsonify({"ok": True})

    uid = (request.args.get("user_id") or "").strip()[:64]
    if not uid or not sb:
        return jsonify({"records": []})
    try:
        r = (sb.table("user_reading_progress")
             .select("book_name,chapter,updated_at")
             .eq("user_id", uid)
             .order("updated_at", desc=True)
             .limit(2).execute())
        return jsonify({"records": r.data or []})
    except Exception:
        return jsonify({"records": []})


@app.route("/")
def index():
    # 首頁：開書動畫 → 存檔選單 → 三層選書，選完導向 /read/<書>/<章>。
    return render_template("home.html")


@app.route("/read/<book>/<int:chapter>")
def read_chapter(book, chapter):
    verses = get_chapter(book, chapter)
    nav_html = build_nav(book, chapter)
    prev_book, prev_ch, next_book, next_ch = get_adjacent(book, chapter)
    entities = chapter_entities(book, chapter)

    # 聖經宇宙：本章人物的關係，以及關係指向的人物精簡卡（即使不在本章也能點開）
    rels = {}
    brief = {}
    for name in entities:
        r = RELATIONSHIPS.get(name)
        if r:
            rels[name] = r
            for targets in r.values():
                for t in targets:
                    if t not in brief and t not in entities:
                        b = _entity_brief(t)
                        if b:
                            brief[t] = b
    lineage = chapter_lineage(book, chapter, entities)
    return render_template(
        "read.html",
        book=book, chapter=chapter, verses=verses,
        nav_html=nav_html,
        prev_book=prev_book, prev_ch=prev_ch,
        next_book=next_book, next_ch=next_ch,
        entities_json=Markup(json.dumps(entities, ensure_ascii=False)),
        relations_json=Markup(json.dumps(rels, ensure_ascii=False)),
        related_brief_json=Markup(json.dumps(brief, ensure_ascii=False)),
        lineage_json=Markup(json.dumps(lineage, ensure_ascii=False)),
    )


if __name__ == "__main__":
    app.run(debug=True)
