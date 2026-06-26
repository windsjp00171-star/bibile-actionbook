import os
from flask import Flask, render_template
from supabase import create_client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

sb = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


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
    return render_template("read.html", book=book, chapter=chapter, verses=verses)


if __name__ == "__main__":
    app.run(debug=True)
