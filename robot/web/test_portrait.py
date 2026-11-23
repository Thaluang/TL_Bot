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


# ---- ระบบภายนอก (ปุ่ม 2–5): เปิดซ้อนในจอได้ไหม — ไม่ได้ต้องขึ้น QR แทนจอว่าง ----
import portrait_systems as ps

ORIGIN = "http://localhost:5000"


def test_frameable_without_headers():
    assert ps.frameable({}, ORIGIN) is True


def test_frameable_x_frame_options_blocks():
    assert ps.frameable({"X-Frame-Options": "DENY"}, ORIGIN) is False
    assert ps.frameable({"x-frame-options": "SAMEORIGIN"}, ORIGIN) is False


def test_frameable_frame_ancestors():
    csp = lambda fa: {"Content-Security-Policy": "default-src 'self'; frame-ancestors " + fa + "; base-uri 'self'"}
    assert ps.frameable(csp("'none'"), ORIGIN) is False
    assert ps.frameable(csp("'self' https:"), ORIGIN) is False        # TLMis ตอนนี้: จอ Pi เป็น http → ยังโดนบล็อก
    assert ps.frameable(csp("'self' https: http://localhost:5000"), ORIGIN) is True
    assert ps.frameable(csp("http://localhost:*"), ORIGIN) is True
    assert ps.frameable(csp("http:"), ORIGIN) is True
    assert ps.frameable(csp("*"), ORIGIN) is True
    assert ps.frameable(csp("'self' https:"), "https://kiosk.example") is True
    assert ps.frameable({"Content-Security-Policy": "default-src 'self'"}, ORIGIN) is True   # ไม่มี frame-ancestors


def test_systems_endpoint_marks_embed(monkeypatch):
    blocked = "https://tl-mis.vercel.app/login"
    monkeypatch.setattr(ps, "fetch_headers", lambda url: {"X-Frame-Options": "DENY"} if url == blocked else {})
    ps.clear_cache()
    rows = make_client().get("/pv/systems").get_json()
    by = {r["key"]: r for r in rows}
    assert set(by) == {"admit", "mis", "sch", "room"}
    assert by["mis"]["url"] == blocked and by["mis"]["embed"] is False
    assert by["admit"]["embed"] is True
    assert by["admit"]["url"] == "https://tctatc.github.io/thaluang-admission/"
    assert by["sch"]["url"] == "https://thaluangcementhaianusorn.github.io/scholarship-system/"
    assert by["room"]["url"] == "https://tctatc.github.io/nasakorn-thaluang-room-booking2/#/"


def test_systems_endpoint_fetch_error_means_qr(monkeypatch):
    def boom(url):
        raise OSError("no net")
    monkeypatch.setattr(ps, "fetch_headers", boom)
    ps.clear_cache()
    rows = make_client().get("/pv/systems").get_json()
    assert all(r["embed"] is False for r in rows)


# ---- ตัวลบอีโมจิของหน้าแนวตั้ง (portrait_util.js) — เครื่องนี้ไม่มี Node จึงรันใน Chrome headless ----
import shutil
import subprocess
from pathlib import Path

import pytest


def _chrome():
    for c in ["C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"]:
        if Path(c).exists():
            return c
    return shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")


def test_strip_emoji_selftest(tmp_path):
    chrome = _chrome()
    if not chrome:
        pytest.skip("ไม่มี Chrome/Chromium")
    page = (Path(__file__).parent / "static" / "portrait_selftest.html").resolve().as_uri()
    out = subprocess.run([chrome, "--headless=new", "--disable-gpu", f"--user-data-dir={tmp_path}", "--dump-dom", page],
                         capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
    assert "PASS" in out, out[-500:]


def test_screen_v_boots_in_chrome(tmp_path, monkeypatch):
    """เปิดหน้าใน Chrome จริง (เซิร์ฟเวอร์ทดสอบในเทรด) — portrait.js ต้องรันจบ (สคริปต์พังเงียบ = จอทั้งหน้าใช้ไม่ได้)"""
    import threading
    from werkzeug.serving import make_server
    chrome = _chrome()
    if not chrome:
        pytest.skip("ไม่มี Chrome/Chromium")
    monkeypatch.setattr(ps, "fetch_headers", lambda url: {})
    srv = make_server("127.0.0.1", 0, server.app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_port}/screen-v?preview=1"
        out = subprocess.run([chrome, "--headless=new", "--disable-gpu", f"--user-data-dir={tmp_path}", "--timeout=8000",
                              "--dump-dom", url], capture_output=True, text=True, encoding="utf-8", timeout=90).stdout
    finally:
        srv.shutdown()
    assert 'data-pv-ready="1"' in out, out[-800:]
    assert 'id="siteQr"><svg' in out          # QR ท้ายจอวาดแล้ว
    assert 'data-menu="trips"' in out          # เมนูอื่นๆ เติมแล้ว


def test_screen_rotate_config_valid():
    """start.sh หมุนจอสัมผัสตาม config ตอน SCREEN_LAYOUT = portrait — ค่าผิดแล้ว wlr-randr ไม่หมุน จอจะเป็นแนวนอนเฉย ๆ"""
    import config
    assert config.SCREEN_LAYOUT in ("landscape", "portrait")
    assert config.SCREEN_ROTATE in ("90", "270")


def test_start_sh_rotates_touchscreen_from_config():
    sh = (Path(__file__).resolve().parent.parent / "pi" / "start.sh").read_text(encoding="utf-8")
    assert "SCREEN_ROTATE" in sh and "wlr-randr --output HDMI-A-1 --transform" in sh
    assert sh.index("--transform") < sh.index("--class=tlbot-screen")   # หมุนก่อนเปิดหน้าจอ


def test_system_page_bar_has_phone_qr(tmp_path, monkeypatch):
    """เว็บระบบที่เปิดในจอ: แถบบนมี QR ให้สแกนไปกรอกในมือถือ (คีย์บอร์ดบนจอพิมพ์ลงเว็บที่ฝังไม่ได้)"""
    import threading
    from werkzeug.serving import make_server
    chrome = _chrome()
    if not chrome:
        pytest.skip("ไม่มี Chrome/Chromium")
    monkeypatch.setattr(ps, "fetch_headers", lambda url: {})
    ps.clear_cache()
    srv = make_server("127.0.0.1", 0, server.app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_port}/screen-v?preview=1&pv=sys:admit"
        out = subprocess.run([chrome, "--headless=new", "--disable-gpu", f"--user-data-dir={tmp_path}", "--timeout=8000",
                              "--dump-dom", url], capture_output=True, text=True, encoding="utf-8", timeout=90).stdout
    finally:
        srv.shutdown()
    assert 'id="pvWebQr"' in out and 'id="pvWebQr" class="on"' in out, out[-600:]


def test_new_chat_button_stays_in_chat(tmp_path, monkeypatch):
    """ปุ่ม "คุยใหม่" ในหน้าแชท = ล้างแชทแต่ยังอยู่หน้าแชท (ล้างตอนหมดเวลาว่างเท่านั้นที่กลับหน้าแรก)"""
    import threading
    from werkzeug.serving import make_server
    chrome = _chrome()
    if not chrome:
        pytest.skip("ไม่มี Chrome/Chromium")
    monkeypatch.setattr(ps, "fetch_headers", lambda url: {})
    srv = make_server("127.0.0.1", 0, server.app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_port}/screen-v?preview=1&pv=newchat"
        out = subprocess.run([chrome, "--headless=new", "--disable-gpu", f"--user-data-dir={tmp_path}", "--timeout=8000",
                              "--dump-dom", url], capture_output=True, text=True, encoding="utf-8", timeout=90).stdout
    finally:
        srv.shutdown()
    body = out[out.index("<body"):out.index(">", out.index("<body"))]
    assert "view-chat" in body, body


def test_screen_layout_endpoint(monkeypatch):
    """หน้าครู (/stats) ใช้ค่านี้จัดกรอบจอตัวอย่างข่าวให้ตรงกับจอจริง"""
    c = make_client()
    monkeypatch.setattr(server.config, "SCREEN_LAYOUT", "portrait")
    assert c.get("/screen-layout").get_json() == {"layout": "portrait"}
    monkeypatch.setattr(server.config, "SCREEN_LAYOUT", "landscape")
    assert c.get("/screen-layout").get_json() == {"layout": "landscape"}


def test_stats_preview_follows_screen_layout():
    html = make_client().get("/stats").get_data(as_text=True)
    assert "/screen-layout" in html and "pv=info" in html


# ---- ความลื่นบน Pi 4 (วัดจริง 23 พ.ย. 2569): หน้ารอของเดิม Chromium กิน CPU 159–189% คลิปกระตุก
#      ต้นเหตุ 1) การ์ดแตะจอขยายเข้าออกวนตลอด 2) หน้าแรกใต้หน้ารอยังเล่นแอนิเมชันตกแต่ง — แก้แล้วเหลือ ~66% นิ่ง ----
def _css():
    html = make_client().get("/screen-v").get_data(as_text=True)
    return html[html.index("<style>"):html.index("</style>")]


def test_attract_has_no_looping_animation():
    css = _css()
    rules = [r.strip() for r in css.split("}") if ("#attract" in r or ".at-" in r) and "infinite" in r]   # ดูทีละกฎ (กฎยาวขึ้นบรรทัดใหม่)
    assert not rules, rules


def test_attract_hides_pages_underneath():
    css = _css().replace(" ", "")
    for part in ("#home", "#pvChat", "#board"):
        assert f"body:has(#attract.open){part}" in css, part
