"""
聖經標註引擎（獨立模組，可跨專案共用）。

從 entities.json 載入詞條，提供：
  annotate(text, book="", chapter=1)  → 把經文中的專名包成可點 span（HTML）
  entity_card(name, book="", chapter=1) → 取得某詞條的卡片資料（給前端卡片）
  resolve_entity / redirect_target      → 底層消歧義（一般不直接用）

設計重點（與 bible-actionbook 一致）：
  - 四層消歧義（書卷+章節 > 書卷 > 約別 > 通用）
  - 同節關鍵字轉址 context_redirect、緊前頭銜轉址 prefix_redirect
  - 最長匹配（長名優先）、碎片守衛 _EXT_GUARD、單字白名單
  - entities.json 為唯一資料來源；兩專案共用同一份（git submodule），不分叉。

entities.json 路徑：預設讀模組同層的 data/entities.json，
可用環境變數 BIBLE_ENTITIES_PATH 覆寫。
"""
import os
import re
import json
from markupsafe import escape

# ---- 載入詞條 ----
_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "data", "entities.json")
_ENTITIES_PATH = os.environ.get("BIBLE_ENTITIES_PATH", _DEFAULT_PATH)
try:
    with open(_ENTITIES_PATH, encoding="utf-8") as f:
        ENTITIES = json.load(f)
except FileNotFoundError:
    ENTITIES = {}

# ---- 新約書卷（判斷約別用）----
NT_BOOK_NAMES = {
    "馬太福音", "馬可福音", "路加福音", "約翰福音", "使徒行傳", "羅馬書",
    "哥林多前書", "哥林多後書", "加拉太書", "以弗所書", "腓立比書", "歌羅西書",
    "帖撒羅尼迦前書", "帖撒羅尼迦後書", "提摩太前書", "提摩太後書", "提多書",
    "腓利門書", "希伯來書", "雅各書", "彼得前書", "彼得後書", "約翰一書",
    "約翰二書", "約翰三書", "猶大書", "啟示錄",
}


def _testament_of(book):
    return "NT" if book in NT_BOOK_NAMES else "OT"


_TYPE_CLASS = {"person": "anno-person", "place": "anno-place", "concept": "anno-concept"}

# 單字詞預設不標（易誤框），僅放行白名單中安全的度量衡單位（如「肘」總接在數字後）。
_SINGLE_CHAR_OK = {"肘", "閃", "含", "噩", "揝", "纛", "圭"}
_ALL_NAMES = sorted(
    [n for n in ENTITIES if len(n) >= 2 or n in _SINGLE_CHAR_OK],
    key=len, reverse=True,
)
_ALL_RE = re.compile("|".join(re.escape(n) for n in _ALL_NAMES)) if _ALL_NAMES else None


def resolve_entity(name, book, chapter):
    """依四層優先度找出這個詞條在目前位置最適用的條目；無合適條目回 None。"""
    val = ENTITIES.get(name)
    if val is None:
        return None
    entries = val if isinstance(val, list) else [val]
    testament = _testament_of(book)
    for e in entries:  # 1. 書卷+章節
        if "books" in e and book in e["books"]:
            cr = e.get("chapters")
            if cr and cr[0] <= chapter <= cr[1]:
                return e
    for e in entries:  # 2. 書卷
        if "books" in e and book in e["books"] and "chapters" not in e:
            return e
    for e in entries:  # 3. 約別
        if "books" not in e and e.get("testament", "both") == testament:
            return e
    for e in entries:  # 4. 通用
        if "books" not in e and e.get("testament", "both") == "both":
            return e
    return None


# 防誤植：較長專名「包含」字典中某短名但意義不同，比對到短名而落在長名內則不框。
_EXT_GUARD = {
    "亞伯米何拉", "亞伯伯瑪迦", "亞伯瑪音", "亞伯什亭", "亞伯基拉明", "亞伯米斯拉音",
    "迦特希弗", "迦特臨門",
    "耶西末", "加略希斯崙", "以利沙瑪", "亞倫巴古",
    "他施恩", "他施行", "他施捨", "他施報", "他施展",
    "約拿達", "約拿大", "猶大書",
    "米利亞", "亞利亞", "比利亞", "加利亞",
    "希伯崙", "希伯倫", "希伯來",
    "示羅密",
}


def _is_partial_of_longer(text, start, end, word):
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


def redirect_target(name, entry, verse_text, before=""):
    """消歧義轉址：先看緊前頭銜 prefix_redirect，再看同節關鍵字 context_redirect。"""
    pre_rules = (entry or {}).get("prefix_redirect")
    if pre_rules and before:
        for rule in pre_rules:
            if any(p in before for p in rule.get("prefix", [])):
                tgt = rule.get("target")
                if tgt and tgt in ENTITIES:
                    return tgt
    rules = (entry or {}).get("context_redirect")
    if rules:
        for rule in rules:
            if any(kw in verse_text for kw in rule.get("keywords", [])):
                tgt = rule.get("target")
                if tgt and tgt in ENTITIES:
                    return tgt
    return None


def annotate(text, book="", chapter=1):
    """把經文中的專名包成可點擊 span（class="anno anno-person/place/concept"，
    data-entity 為解析後的詞條鍵），其餘字元 HTML 轉義。回傳 HTML 字串。"""
    if not _ALL_RE:
        return str(escape(text))
    out, last = [], 0
    for m in _ALL_RE.finditer(text):
        word = m.group(0)
        out.append(str(escape(text[last:m.start()])))
        if _is_partial_of_longer(text, m.start(), m.end(), word):
            out.append(str(escape(word)))
        else:
            entry = resolve_entity(word, book, chapter)
            if entry:
                before = text[max(0, m.start() - 6):m.start()]
                tgt = redirect_target(word, entry, text, before)
                data_name = tgt or word
                if tgt:
                    te = ENTITIES[tgt]
                    entry = te[0] if isinstance(te, list) else te
                cls = _TYPE_CLASS.get(entry["type"], "anno-person")
                out.append(f'<span class="anno {cls}" data-entity="{escape(data_name)}">{escape(word)}</span>')
            else:
                out.append(str(escape(word)))
        last = m.end()
    out.append(str(escape(text[last:])))
    return "".join(out)


def entity_card(name, book="", chapter=1):
    """取得詞條的卡片資料（dict）。name 為 annotate 輸出的 data-entity 鍵。"""
    val = ENTITIES.get(name)
    if val is None:
        return None
    e = resolve_entity(name, book, chapter) or (val[0] if isinstance(val, list) else val)
    return {
        "name": e.get("name", name),
        "name_en": e.get("name_en", ""),
        "type": e.get("type", "person"),
        "desc": e.get("desc", ""),
        "reading": e.get("reading", ""),  # 生僻字注音／拼音
        "verses": e.get("verses", ""),
        "lat": e.get("lat"),
        "lng": e.get("lng"),
    }


def chapter_entities_brief():
    """全部詞條的精簡查表（給前端一次載入，點標註詞時本地查）。"""
    out = {}
    for name in ENTITIES:
        c = entity_card(name)
        if c:
            out[name] = c
    return out
