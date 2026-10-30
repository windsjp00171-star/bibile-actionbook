import os
import re
import json
from datetime import datetime, timezone
from urllib.parse import unquote_to_bytes
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from markupsafe import Markup
from supabase import create_client

app = Flask(__name__)


@app.context_processor
def _inject_static_v():
    """static 檔加上 ?v=<mtime>。sw.js 對 /static/ 是 cache-first，檔案改了但網址不變
    的話，已安裝的 PWA 會一直用舊版 JS，跟新版模板對不上。"""
    def static_v(filename):
        path = os.path.join(app.static_folder, filename)
        try:
            v = int(os.path.getmtime(path))
        except OSError:
            v = 0
        return url_for("static", filename=filename, v=v)
    return {"static_v": static_v}


class _DecodePathInfo:
    """Vercel 的 WSGI 轉接層沒有對 PATH_INFO 做 percent-decode。

    WSGI 規格要求 PATH_INFO 是「已解碼」的路徑，但 Vercel 直接把原始 URL 塞進來，
    Flask 於是收到字面上的 `/read/%E5%89%B5%E4%B8%96%E8%A8%98/2`，書卷名對不上
    cuv.json 的鍵，每一章都變成「查無此章經文」（本站書卷名全是中文，等於全站掛掉）。

    這裡照 WSGI 慣例補回來：解碼成 bytes 後用 latin-1 存進 PATH_INFO，Werkzeug 之後
    會自己 latin-1 → bytes → UTF-8 還原成中文。只在 Vercel 上啟用（VERCEL 是 Vercel
    runtime 內建的環境變數），本機與 gunicorn 走原本正確的路徑，順便避開路徑裡真的
    含有 %25 時被二次解碼的邊界情況。
    """

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if "%" in path:
            environ["PATH_INFO"] = unquote_to_bytes(path).decode("latin-1")
        return self.wsgi_app(environ, start_response)


if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    app.wsgi_app = _DecodePathInfo(app.wsgi_app)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# 暫時豁免：全域規範要求從 mark_core.supabase_client import，但本 repo 尚未接入
# mark-core，且經文已改走本機 cuv.json，Supabase 目前未實際使用。待接入登入/
# 通知等共用功能時，再改為 from mark_core.supabase_client import ...（待清理）。
sb = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

import mark_bible
from bible_data import (
    ALL_BOOKS, BIBLE, ENTITIES, NT_BOOKS, OT_BOOKS, RELATIONSHIPS, ROUTES,
    _entity_brief, build_nav, chapter_entities, chapter_lineage, get_adjacent,
    get_chapter,
)


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json(silent=True) or {}
    entity = (data.get("entity") or "").strip()[:50]
    book = (data.get("book") or "").strip()[:30]
    chapter = data.get("chapter", "")
    note = (data.get("note") or "").strip()[:200]
    try:
        verse = int(data.get("verse")) if data.get("verse") not in (None, "") else None
    except (TypeError, ValueError):
        verse = None
    if not entity:
        return jsonify({"error": "empty"}), 400
    if sb:
        try:
            row = {"entity": entity, "book": book,
                   "chapter": str(chapter), "note": note}
            if verse is not None:
                row["verse"] = verse
            sb.table("entity_feedback").insert(row).execute()
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


@app.route("/api/search")
def api_search():
    """經文全文搜尋。GET ?q=關鍵字&limit=  → 依聖經順序回符合的節。"""
    q = (request.args.get("q") or "").strip()
    if len(q) < 1:
        return jsonify({"query": q, "total": 0, "results": []})
    try:
        limit = min(max(int(request.args.get("limit", 200)), 1), 500)
    except ValueError:
        limit = 200
    scope = (request.args.get("book") or "").strip()  # 限定書卷（可空）
    results = []
    total = 0
    for book, _ch_count in ALL_BOOKS:
        if scope and book != scope:
            continue
        chapters = BIBLE.get(book, {})
        for ch in sorted(chapters.keys(), key=lambda x: int(x)):
            verses = chapters[ch]
            for v in sorted(verses.keys(), key=lambda x: int(x)):
                text = verses[v]
                if q in text:
                    total += 1
                    if len(results) < limit:
                        results.append({
                            "book": book, "chapter": int(ch),
                            "verse": int(v), "text": text,
                        })
    return jsonify({"query": q, "total": total,
                    "truncated": total > len(results), "results": results})


@app.route("/search")
def search_page():
    """獨立的全本搜尋頁（首頁與閱讀頁皆可進）。"""
    return render_template("search.html", q=(request.args.get("q") or "").strip())


@app.route("/kings")
def kings_page():
    """南北國列王對照表：純參考頁，資料為列王紀/歷代志原文記載的在位年數與交叉紀年。"""
    path = os.path.join(os.path.dirname(__file__), "data", "kings_timeline.json")
    with open(path, encoding="utf-8") as f:
        timeline = json.load(f)
    return render_template("kings.html", timeline=timeline)


@app.route("/api/entities")
def api_entities():
    """人物/地點/概念索引：列出全部詞條（依類型分組）。
    傳 book 參數時，另標記每個詞條是否出現在該卷（給「只看本卷」過濾用）。"""
    book = (request.args.get("book") or "").strip()
    joined = ""
    if book:
        chapters = BIBLE.get(book, {})
        joined = "".join(t for ch in chapters.values() for t in ch.values())
    groups = {"person": [], "place": [], "concept": []}
    for name, val in ENTITIES.items():
        e = val[0] if isinstance(val, list) else val
        t = e.get("type", "person")
        item = {
            "key": name,
            "name": e.get("name", name),
            "name_en": e.get("name_en", ""),
            "has_map": e.get("lat") is not None,
            "testament": e.get("testament", "both"),
        }
        if t == "concept":
            item["cat"] = e.get("cat", "theo")
        if book:
            disp = e.get("name", name)
            item["in_book"] = (name in joined) or (disp in joined)
        groups.setdefault(t, []).append(item)
    for t in groups:
        groups[t].sort(key=lambda x: x["name"])
    return jsonify(groups)


@app.route("/api/entity")
def api_entity():
    """取單一詞條的卡片資料（給索引點擊後直接看標註內容）。"""
    name = (request.args.get("name") or "").strip()
    card = mark_bible.entity_card(name) if name else None
    if not card:
        return jsonify({"error": "not_found"}), 404
    return jsonify(card)


@app.route("/api/book_places")
def api_book_places():
    """整卷地圖：某書卷中出現、且有座標的地點（去重）。"""
    book = (request.args.get("book") or "").strip()
    chapters = BIBLE.get(book, {})
    if not chapters:
        return jsonify({"book": book, "places": []})
    joined = "".join(t for ch in chapters.values() for t in ch.values())
    seen, places = set(), []
    for name, val in ENTITIES.items():
        e = val[0] if isinstance(val, list) else val
        if e.get("type") != "place" or e.get("lat") is None:
            continue
        if name in seen or name not in joined:
            continue
        seen.add(name)
        places.append({"name": e.get("name", name), "key": name,
                       "lat": e["lat"], "lng": e["lng"],
                       "desc": e.get("desc", "")})
    return jsonify({"book": book, "places": places})


@app.route("/api/routes")
def api_routes():
    """聖經路線圖：列出路線（可依 book 過濾為情境推薦），或回單一路線細節。"""
    rid = (request.args.get("id") or "").strip()
    if rid:
        r = ROUTES.get(rid)
        if not r:
            return jsonify({"error": "not_found"}), 404
        return jsonify(dict(r, id=rid))
    book = (request.args.get("book") or "").strip()
    items = []
    for k, r in ROUTES.items():
        relevant = (not book) or (book in r.get("books", []))
        items.append({
            "id": k, "name": r.get("name", k), "ref": r.get("ref", ""),
            "color": r.get("color", "#8B6840"), "testament": r.get("testament", "OT"),
            "stops": len(r.get("waypoints", [])), "relevant": relevant,
        })
    items.sort(key=lambda x: (not x["relevant"], x["name"]))
    return jsonify({"book": book, "routes": items})


# 經文簡稱 → 全名（路線資料 ref 用簡稱，用來判斷某章經過哪些路線站點）
_ROUTE_BOOK_ABBR = {
    "創": "創世記", "出": "出埃及記", "利": "利未記", "民": "民數記", "申": "申命記",
    "書": "約書亞記", "士": "士師記", "得": "路得記", "撒上": "撒母耳記上", "撒下": "撒母耳記下",
    "王上": "列王紀上", "王下": "列王紀下", "拉": "以斯拉記", "尼": "尼希米記", "詩": "詩篇",
    "賽": "以賽亞書", "耶": "耶利米書", "結": "以西結書", "但": "但以理書",
    "太": "馬太福音", "可": "馬可福音", "路": "路加福音", "約": "約翰福音", "徒": "使徒行傳",
}
_REF_RE = re.compile(r"^([一-鿿]+?(?:上|下)?)(\d+)(?::(\d+))?")


def _parse_route_ref(ref):
    """把『出17:1』『王上19:8』解析為 (book, chapter, verse)；無法解析回 None。"""
    m = _REF_RE.match(ref or "")
    if not m:
        return None
    pre = m.group(1)
    book = _ROUTE_BOOK_ABBR.get(pre) or (_ROUTE_BOOK_ABBR.get(pre[0]) if len(pre) > 1 else None)
    if not book:
        return None
    return book, int(m.group(2)), (int(m.group(3)) if m.group(3) else None)


@app.route("/api/routes_here")
def api_routes_here():
    """本章浮現：回傳經過某書卷某章的路線站點（讀經時自動提示用）。"""
    book = (request.args.get("book") or "").strip()
    try:
        ch = int(request.args.get("chapter") or 0)
    except ValueError:
        ch = 0
    hits = []
    for rid, r in ROUTES.items():
        for i, w in enumerate(r.get("waypoints", [])):
            nav = _parse_route_ref(w.get("ref", ""))
            if nav and nav[0] == book and nav[1] == ch:
                hits.append({
                    "id": rid, "route": r.get("name", rid), "color": r.get("color", "#8B6840"),
                    "stop": i + 1, "name": w.get("name", ""), "ref": w.get("ref", ""),
                })
    return jsonify({"here": hits})


@app.route("/api/bookmarks", methods=["GET", "POST", "DELETE"])
def api_bookmarks():
    """書籤。POST 新增 / DELETE 移除 / GET 取清單。以裝置 ID 當 user_id。"""
    if request.method == "GET":
        uid = (request.args.get("user_id") or "").strip()[:64]
        if not uid or not sb:
            return jsonify({"bookmarks": []})
        try:
            r = (sb.table("user_bookmarks")
                 .select("book_name,chapter,verse,text,created_at")
                 .eq("user_id", uid).order("created_at", desc=True).limit(300).execute())
            return jsonify({"bookmarks": r.data or []})
        except Exception:
            return jsonify({"bookmarks": []})

    data = request.get_json(silent=True) or {}
    uid = (data.get("user_id") or "").strip()[:64]
    book = (data.get("book") or "").strip()[:30]
    try:
        chapter = int(data.get("chapter"))
        verse = int(data.get("verse"))
    except (TypeError, ValueError):
        return jsonify({"error": "bad_request"}), 400
    if not uid or not book or not sb:
        return jsonify({"ok": True})

    if request.method == "DELETE":
        try:
            (sb.table("user_bookmarks").delete()
             .eq("user_id", uid).eq("book_name", book)
             .eq("chapter", chapter).eq("verse", verse).execute())
        except Exception:
            pass
        return jsonify({"ok": True})

    try:
        sb.table("user_bookmarks").upsert({
            "user_id": uid, "book_name": book, "chapter": chapter,
            "verse": verse, "text": (data.get("text") or "")[:300],
        }, on_conflict="user_id,book_name,chapter,verse").execute()
    except Exception:
        pass
    return jsonify({"ok": True})


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


@app.route("/sw.js")
def service_worker():
    """Service worker 必須從網站根目錄送出。

    SW 的預設控制範圍（scope）就是它自己所在的目錄，放在 /static/sw.js 只能控制
    /static/*，碰不到 / 與 /read/*——離線快取因此形同虛設，Chrome 也會因為
    「沒有 SW 控制 start_url」而不給安裝。檔案仍留在 static/ 方便維護，這裡只是
    換一個根目錄的網址送出去。
    """
    resp = send_from_directory(app.static_folder, "sw.js", mimetype="text/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/manifest.json")
def manifest():
    """跟 sw.js 一樣放到根目錄，讓 scope 與 start_url 都落在 / 底下。"""
    return send_from_directory(app.static_folder, "manifest.json",
                               mimetype="application/manifest+json")


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
