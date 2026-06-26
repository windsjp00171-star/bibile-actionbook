import os
from flask import Flask, render_template
from markupsafe import Markup
from supabase import create_client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

sb = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

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
    if not sb:
        return []
    res = (
        sb.table("bible_verses")
        .select("verse, text")
        .eq("book", book)
        .eq("chapter", chapter)
        .order("verse")
        .execute()
    )
    return res.data or []


@app.route("/")
def index():
    return read_chapter("撒母耳記上", 17)


@app.route("/read/<book>/<int:chapter>")
def read_chapter(book, chapter):
    verses = get_chapter(book, chapter)
    nav_html = build_nav(book, chapter)
    return render_template("read.html", book=book, chapter=chapter,
                           verses=verses, nav_html=nav_html)


if __name__ == "__main__":
    app.run(debug=True)
