import os
import re
import json
import hashlib
from datetime import date
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

_TYPE_CLASS = {"person": "anno-person", "place": "anno-place", "concept": "anno-concept"}


def _build_entity_maps(entities):
    """把 entities.json 展開成 OT 和 NT 兩張查閱表。
    值為 dict → 視 testament 欄位（預設 both）決定加入哪張表。
    值為 list → 每個子條目各自處理（同名異義用此格式）。
    """
    ot_map: dict = {}
    nt_map: dict = {}
    for name, val in entities.items():
        entries = val if isinstance(val, list) else [val]
        for entry in entries:
            t = entry.get("testament", "both")
            if t in ("OT", "both"):
                ot_map[name] = entry
            if t in ("NT", "both"):
                nt_map[name] = entry
    return ot_map, nt_map


_OT_ENTITY_MAP, _NT_ENTITY_MAP = _build_entity_maps(ENTITIES)

_OT_NAMES = sorted([n for n in _OT_ENTITY_MAP if len(n) >= 2], key=len, reverse=True)
_NT_NAMES = sorted([n for n in _NT_ENTITY_MAP if len(n) >= 2], key=len, reverse=True)
_OT_RE = re.compile("|".join(re.escape(n) for n in _OT_NAMES)) if _OT_NAMES else None
_NT_RE = re.compile("|".join(re.escape(n) for n in _NT_NAMES)) if _NT_NAMES else None


# 防誤植：這些較長的專有名詞「包含」字典裡某個短名，但意義完全不同。
# 比對到短名時，若該處其實是這些長名的一部分，就不要框（例：亞伯拉罕≠亞伯）。
_EXT_GUARD = {
    # 亞伯(Abel) 誤夾進這些地名（亞伯拉罕/亞伯蘭已另立卡片，靠最長匹配處理）
    "亞伯米何拉", "亞伯伯瑪迦", "亞伯瑪音", "亞伯什亭", "亞伯基拉明", "亞伯米斯拉音",
    # 迦特(Gath)
    "迦特希弗", "迦特臨門",
    # 耶西(Jesse) / 希斯崙 / 沙瑪(Shammah) / 亞倫(Aaron)
    "耶西末", "加略希斯崙", "以利沙瑪", "亞倫巴古",
    # 他施(Tarshish) 撞動詞「施」：向他施恩、他施行…
    "他施恩", "他施行", "他施捨", "他施報", "他施展",
    # 約拿(Jonah) 其餘變體（約拿單已另立卡片）
    "約拿達", "約拿大", "猶大書",
}


def _is_partial_of_longer(text, start, end, word):
    """word 在 text[start:end]；若此位置其實落在某個更長名字內，回 True。"""
    for g in _EXT_GUARD:
        if len(g) <= len(word) or word not in g:
            continue
        lo = max(0, start - len(g) + 1)
        seg = text[lo:end + len(g) - 1]
        i = seg.find(g)
        while i != -1:
            gs, ge = lo + i, lo + i + len(g)
            if gs <= start and ge >= end:
                return True
            i = seg.find(g, i + 1)
    return False


def annotate(text, testament="OT"):
    """把經文中的實體詞包成可點擊 span，其餘字元做 HTML 轉義。
    testament="NT" 時改用新約實體表，避免同名異義（如猶大、掃羅）顯示錯誤的卡片。
    """
    entity_re  = _NT_RE       if testament == "NT" else _OT_RE
    entity_map = _NT_ENTITY_MAP if testament == "NT" else _OT_ENTITY_MAP
    if not entity_re:
        return str(escape(text))
    out, last = [], 0
    for m in entity_re.finditer(text):
        word = m.group(0)
        out.append(str(escape(text[last:m.start()])))
        if _is_partial_of_longer(text, m.start(), m.end(), word):
            out.append(str(escape(word)))   # 是更長名字的一部分 → 純文字，不框
        else:
            cls = _TYPE_CLASS.get(entity_map[word]["type"], "anno-person")
            out.append(f'<span class="anno {cls}" data-entity="{escape(word)}">{escape(word)}</span>')
        last = m.end()
    out.append(str(escape(text[last:])))
    return "".join(out)


# 依中文標點切分句；標點留在前一句尾。手機點按以「分句」為單位最好點。
_CLAUSE_RE = re.compile(r"[^、，。；：！？「」『』（）]+[、，。；：！？」』）]*")


def render_verse(text, testament="OT"):
    """把一節經文切成可點擊的分句 span，分句內仍套用實體標注。"""
    parts = []
    for m in _CLAUSE_RE.finditer(text):
        clause = m.group(0)
        if not clause.strip():
            continue
        parts.append(
            f'<span class="clause" data-clause="{escape(clause)}">{annotate(clause, testament)}</span>'
        )
    if not parts:  # 全是標點等極端情形
        parts.append(annotate(text, testament))
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
    testament = _testament_of(book)
    verses = []
    for vnum in sorted(chap.keys(), key=lambda x: int(x)):
        text = chap[vnum]
        verses.append({"verse": int(vnum), "html": render_verse(text, testament)})
    return verses


def chapter_entities(book, chapter):
    """本章實際出現的實體（給前端卡片與地圖）。只回傳長度>=2、與標注一致者。"""
    chap = BIBLE.get(book, {}).get(str(chapter), {})
    joined = "".join(chap.values())
    testament = _testament_of(book)
    entity_map = _NT_ENTITY_MAP if testament == "NT" else _OT_ENTITY_MAP
    return {name: entity_map[name] for name in entity_map if len(name) >= 2 and name in joined}


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

    # 第 1 層：手刻字典（整段剛好等於某實體名，依約章選正確的條目）
    _testament = _testament_of(book)
    _emap = _NT_ENTITY_MAP if _testament == "NT" else _OT_ENTITY_MAP
    if text in _emap:
        return jsonify({"content": _emap[text]["desc"], "source": "dict"})

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


@app.route("/")
def index():
    return read_chapter("撒母耳記上", 17)


@app.route("/read/<book>/<int:chapter>")
def read_chapter(book, chapter):
    verses = get_chapter(book, chapter)
    nav_html = build_nav(book, chapter)
    prev_book, prev_ch, next_book, next_ch = get_adjacent(book, chapter)
    entities = chapter_entities(book, chapter)
    return render_template(
        "read.html",
        book=book, chapter=chapter, verses=verses,
        nav_html=nav_html,
        prev_book=prev_book, prev_ch=prev_ch,
        next_book=next_book, next_ch=next_ch,
        entities_json=Markup(json.dumps(entities, ensure_ascii=False)),
    )


if __name__ == "__main__":
    app.run(debug=True)
