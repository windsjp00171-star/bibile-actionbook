"""路由 smoke test：頁面與 API 能回 200、關鍵內容存在。執行：pytest tests/"""
import os
import sys
from urllib.parse import quote

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app as app_module  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return app_module.app.test_client()


@pytest.mark.parametrize("url", [
    "/", "/search", "/kings", "/sw.js", "/manifest.json",
    "/api/books", "/api/entities", "/api/routes",
    "/api/search?q=" + quote("摩西"),
    "/api/entity?name=" + quote("摩西"),
    "/api/book_places?book=" + quote("創世記"),
])
def test_page_ok(client, url):
    assert client.get(url).status_code == 200


def test_every_chapter_renders(client):
    for book, n in app_module.OT_BOOKS + app_module.NT_BOOKS:
        for ch in (1, n):
            r = client.get(f"/read/{book}/{ch}")
            assert r.status_code == 200, (book, ch)


def test_read_page_has_tour_hooks_and_versioned_assets(client):
    html = client.get("/read/" + quote("馬太福音") + "/1").get_data(as_text=True)
    assert html.count('data-tour="') >= 12
    assert "/static/style.css?v=" in html
    assert "/static/js/read-core.js?v=" in html


def test_static_version_follows_content_not_mtime(tmp_path):
    p = os.path.join(app_module.app.static_folder, "style.css")
    before = os.stat(p).st_mtime
    os.utime(p, (before + 1000, before + 1000))
    app_module._STATIC_HASH.clear()
    v1 = app_module._static_version("style.css")
    os.utime(p, (before, before))
    app_module._STATIC_HASH.clear()
    assert v1 == app_module._static_version("style.css")


def test_header_art_rules_live_in_section_art_css():
    css = open(os.path.join(app_module.app.static_folder, "section-art.css"), encoding="utf-8").read()
    assert ".header-art" in css and "overflow:hidden" in css


def test_tool_pages_have_no_header_art(client):
    for url in ("/search", "/kings"):
        assert "header-art" not in client.get(url).get_data(as_text=True)


def test_missing_chapter_does_not_crash(client):
    assert client.get("/read/" + quote("不存在的書") + "/1").status_code < 500


def test_json_api_envelope_not_required_for_bookmarks_without_supabase(client):
    # Supabase 未設定時，書籤 API 應該安靜回應而不是 500
    assert client.get("/api/bookmarks").status_code < 500
