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
