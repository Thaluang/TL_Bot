"""
เทสต์หน้าจอสัมผัสแนวตั้ง (/screen-v) และการสลับหน้าจอหลักด้วย config.SCREEN_LAYOUT
รันจากโฟลเดอร์ robot/:  py -m pytest web/test_portrait.py -v
"""
import server


def make_client():
    server.app.config["TESTING"] = True
    return server.app.test_client()


def test_screen_v_route_serves_portrait_page():
    r = make_client().get("/screen-v")
    assert r.status_code == 200
    assert b'data-layout="portrait"' in r.data


def test_screen_layout_switch(monkeypatch):
    c = make_client()
    monkeypatch.setattr(server.config, "SCREEN_LAYOUT", "portrait")
    assert b'data-layout="portrait"' in c.get("/screen").data
    assert b'data-layout="portrait"' in c.get("/").data
    monkeypatch.setattr(server.config, "SCREEN_LAYOUT", "landscape")
    assert b'data-layout="portrait"' not in c.get("/screen").data
    assert b'id="mic"' in c.get("/screen").data   # หน้าเดิมยังมา


REQUIRED_IDS = ["chat", "scroll", "composer", "q", "mic", "stopTalk", "allMenuTpl", "announce", "announceText",
    "attract", "vidProg", "tourView", "lightbox", "net", "clock", "hello", "today", "weather", "topRow", "wxIcon",
    "wxTemp", "wxText", "newsGrid", "pager", "home", "board", "boardIcon", "boardTitle", "boardSub", "boardBody",
    "boardAuto", "pvInfo", "pvMore", "pvWeb", "pvQr"]


def test_screen_v_has_all_ids_scripts_need():
    html = make_client().get("/screen-v").get_data(as_text=True)
    for i in REQUIRED_IDS:
        assert f'id="{i}"' in html, i
    assert 'class="led-text"' in html


def test_screen_v_script_order():
    html = make_client().get("/screen-v").get_data(as_text=True)
    order = ["/static/vendor/qrcode.js", "/static/news.js", "/static/screen.js", "/static/extras.js", "/static/osk.js",
             "/static/portrait_util.js", "/static/portrait.js"]
    pos = [html.index(s) for s in order]
    assert pos == sorted(pos)


def test_screen_v_has_no_emoji():
    import re
    html = make_client().get("/screen-v").get_data(as_text=True)
    found = re.findall(r"[\U0001F300-\U0001FAFF☀-➿⭐⭕⌚-⏿]", html)
    assert not found, found


def test_screen_v_css_braces_balanced():
    """กฎ CSS ที่ห้อยค้าง (ปีกกาไม่ครบ) ทำให้กฎถัดไปพังเงียบ ๆ — เคยทำหน้ารอโผล่ทับหน้าแรก"""
    html = make_client().get("/screen-v").get_data(as_text=True)
    css = html[html.index("<style>"):html.index("</style>")]
    depth = 0
    for line in css.splitlines():
        depth += line.count("{") - line.count("}")
        assert depth >= 0, line
    assert depth == 0
