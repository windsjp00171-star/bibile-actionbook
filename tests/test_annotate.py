"""標註引擎的左邊優先問題：被守衛擋下或當前書卷無適用條目的詞，不可吞掉與它重疊的真正專名。"""
import re
import mark_bible as mb


def marked(text, book, chapter):
    html = mb.annotate(text, book, chapter)
    return re.findall(r'data-entity="[^"]+"[^>]*>([^<]+)</span>', html)


def test_books_limited_entry_does_not_shadow_neighbour():
    # 「哥哥亞倫」不可因為某個限定書卷的「哥亞」類詞條而丟掉亞倫
    assert "亞倫" in marked("你哥哥亞倫", "出埃及記", 7)


def test_guard_blocks_wrong_prefix_then_finds_real_name():
    assert marked("所以掃羅使大衛離開", "撒母耳記上", 18)[0] == "掃羅"
    assert "撒母耳" in marked("已經指示撒母耳說", "撒母耳記上", 9)
    assert marked("所以法老當揀選", "創世記", 41) == ["法老"]


def test_levites_not_marked_as_eli():
    assert marked("所以利未人在他弟兄中", "申命記", 10) == ["利未人"]


def test_longer_name_still_wins():
    assert marked("以弗崙", "創世記", 23) == ["以弗崙"]
