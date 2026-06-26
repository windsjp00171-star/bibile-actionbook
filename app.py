import os
import re
import json
from flask import Flask, render_template
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
                annotated = {tuple(x) for x in json.load(f)}
        return entities, annotated
    from data.annotations import ENTITIES as seed_ent, ANNOTATED as seed_ann
    return dict(seed_ent), set(seed_ann)


ENTITIES, ANNOTATED = _load_annotations()

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

_TYPE_CLASS = {"person": "anno-person", "place": "anno-place", "concept": "anno-concept"}

# 依字長由長到短排序，確保「非利士人」優先於較短的詞被匹配。
_ENTITY_NAMES = sorted(ENTITIES.keys(), key=len, reverse=True)
_ENTITY_RE = re.compile("|".join(re.escape(n) for n in _ENTITY_NAMES)) if _ENTITY_NAMES else None


def annotate(text):
    """把經文中的實體詞包成可點擊 span，其餘字元做 HTML 轉義。"""
    if not _ENTITY_RE:
        return Markup(str(escape(text)))
    out, last = [], 0
    for m in _ENTITY_RE.finditer(text):
        out.append(str(escape(text[last:m.start()])))
        word = m.group(0)
        cls = _TYPE_CLASS.get(ENTITIES[word]["type"], "anno-person")
        out.append(f'<span class="anno {cls}" data-entity="{escape(word)}">{escape(word)}</span>')
        last = m.end()
    out.append(str(escape(text[last:])))
    return Markup("".join(out))


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


def get_chapter(book, chapter):
    """從 cuv.json 取一章，回傳 [{verse, html}]；標注僅套用於已整理章節。"""
    chap = BIBLE.get(book, {}).get(str(chapter), {})
    do_anno = (book, chapter) in ANNOTATED
    verses = []
    for vnum in sorted(chap.keys(), key=lambda x: int(x)):
        text = chap[vnum]
        html = annotate(text) if do_anno else Markup(str(escape(text)))
        verses.append({"verse": int(vnum), "html": html})
    return verses


def chapter_entities(book, chapter):
    """本章實際用到的實體（給前端卡片與地圖）。"""
    if (book, chapter) not in ANNOTATED:
        return {}
    chap = BIBLE.get(book, {}).get(str(chapter), {})
    joined = "".join(chap.values())
    return {name: ENTITIES[name] for name in ENTITIES if name in joined}


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
