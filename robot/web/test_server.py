"""
เทสต์เซิร์ฟเวอร์เว็บ — Flask test client + mock ask_ai (ไม่ยิง API จริง)
รันจากโฟลเดอร์ robot/:  & $py -m pytest web/test_server.py -v
"""
import pytest

import server  # web/ ถูกใส่ใน sys.path โดย pytest (prepend import mode)
from stats import Stats


@pytest.fixture(autouse=True)
def temp_stats(tmp_path, monkeypatch):
    """ทุกเทสต์ใช้ฐานสถิติชั่วคราว ไม่เขียนลง robot/stats.db ตัวจริง"""
    st = Stats(tmp_path / "stats.db")
    monkeypatch.setattr(server, "stats", st)
    server.answers.clear()   # คำตอบที่จำไว้ของเทสต์ก่อน ไม่ให้ปนกัน
    return st


def make_client():
    server.app.config["TESTING"] = True
    server.state["value"] = "idle"
    return server.app.test_client()


def test_state_default_is_idle():
    c = make_client()
    r = c.get("/state")
    assert r.status_code == 200
    assert r.get_json()["state"] == "idle"


def test_post_state_updates_value():
    c = make_client()
    r = c.post("/state", json={"state": "listening"})
    assert r.get_json()["state"] == "listening"
    assert c.get("/state").get_json()["state"] == "listening"


def set_valid_key(monkeypatch):
    """ตั้ง key ปลอมที่ 'พร้อมใช้' — /ask ต้องมี key ก่อนถึงจะเรียกสมอง"""
    monkeypatch.setattr(server.config, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(server.config, "GEMINI_API_KEY", "test-key")


def test_ask_returns_answer_and_sets_answering(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)
    # mock สมองไม่ให้ยิง API จริง (monkeypatch คืนค่าเดิมให้อัตโนมัติหลังจบเทสต์)
    monkeypatch.setattr(server, "ask_ai", lambda question, college_data, saraburi_data, lang="th": f"ตอบ: {question}")
    r = c.post("/ask", json={"question": "เปิดสอนอะไร"})
    assert r.status_code == 200
    assert r.get_json()["answer"] == "ตอบ: เปิดสอนอะไร"
    assert server.state["value"] == "answering"


def test_ask_error_sets_error_state_and_500(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)

    def boom(question, college_data, saraburi_data, lang="th"):
        raise RuntimeError("เน็ตล่ม")

    monkeypatch.setattr(server, "ask_ai", boom)
    r = c.post("/ask", json={"question": "x"})
    assert r.status_code == 500
    assert "error" in r.get_json()
    assert server.state["value"] == "error"


def test_ask_without_api_key_returns_setup_instructions(monkeypatch):
    """key ว่าง → ต้องบอกวิธีตั้งค่าเป็นภาษาไทย และห้ามเรียกสมองจริง"""
    c = make_client()
    monkeypatch.setattr(server.config, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(server.config, "GEMINI_API_KEY", "")
    called = []
    monkeypatch.setattr(server, "ask_ai", lambda q, c, s, lang="th": called.append(q) or "x")
    r = c.post("/ask", json={"question": "เปิดสอนอะไร"})
    assert r.status_code == 500
    err = r.get_json()["error"]
    assert "GEMINI_API_KEY" in err
    assert ".env" in err
    assert called == []
    assert server.state["value"] == "error"


def test_ask_with_placeholder_key_returns_setup_instructions(monkeypatch):
    """key ยังเป็นค่าตัวอย่างจาก .env.example → ถือว่ายังไม่ได้ตั้งค่า"""
    c = make_client()
    monkeypatch.setattr(server.config, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(server.config, "GEMINI_API_KEY", "AIzaxxxxxxxxxxxxxxxxxxxxxxxx")
    monkeypatch.setattr(server, "ask_ai", lambda q, c, s, lang="th": "x")
    r = c.post("/ask", json={"question": "เปิดสอนอะไร"})
    assert r.status_code == 500
    assert "GEMINI_API_KEY" in r.get_json()["error"]


def test_pages_are_served():
    c = make_client()
    face = c.get("/face")
    screen = c.get("/screen")
    assert face.status_code == 200
    assert b"eye-ball" in face.data        # มาร์กเกอร์ของจอใบหน้า
    assert screen.status_code == 200
    assert b'id="mic"' in screen.data      # มาร์กเกอร์ของจอเนื้อหา


def test_logo_asset_served():
    c = make_client()
    r = c.get("/static/logo.jpg")
    assert r.status_code == 200
    assert r.data[:3] == b"\xff\xd8\xff"   # magic bytes ของไฟล์ JPEG


def test_screen_header_uses_real_logo():
    c = make_client()
    screen = c.get("/screen")
    assert screen.status_code == 200
    assert b"/static/logo.jpg" in screen.data   # header อ้างโลโก้จริง


def test_screen_has_onscreen_keyboard():
    """หน้าแชทโหลดคีย์บอร์ดบนจอ (osk.js) ที่มีทั้งแป้นไทยและอังกฤษ — คีย์บอร์ดของระบบโดน kiosk เต็มจอบัง"""
    c = make_client()
    html = c.get("/screen").get_data(as_text=True)
    assert '<script src="/static/osk.js"></script>' in html
    assert html.index("/static/screen.js") < html.index("/static/osk.js")   # ต้องโหลดหลัง screen.js
    js = c.get("/static/osk.js")
    assert js.status_code == 200
    src = js.get_data(as_text=True)
    assert "ฟหกดเ" in src and "qwertyuiop" in src


def test_campus_tour_only_in_sidebar():
    """ปุ่มแนะนำสถานที่วิทยาลัย (ทัวร์ 3 มิติ) อยู่ในเมนูทั้งหมดที่เดียว และหน้าทัวร์เปิดได้จริง"""
    c = make_client()
    html = c.get("/screen").get_data(as_text=True)
    allmenu = html[html.index('id="allMenuTpl"'):html.index("</template>", html.index('id="allMenuTpl"'))]
    assert 'data-action="campusTour"' in allmenu
    assert html.count('data-action="campusTour"') == 1
    r = c.get("/static/campus_tour.html")
    assert r.status_code == 200 and "Campus Tour" in r.get_data(as_text=True)


def test_screen_has_quick_questions():
    """จอเนื้อหามีแถบคำถามยอดนิยมให้แตะถามได้"""
    c = make_client()
    screen = c.get("/screen")
    assert screen.status_code == 200
    html = screen.data.decode("utf-8")
    dock = html[html.index('id="dockQs"'):html.index("</div>", html.index('id="dockQs"'))]
    assert dock.count('class="chip') == 4      # ชิปแนะนำ 4 ปุ่ม (จุดเด่นวิทยาลัย/สมัครเรียน/สถานที่ท่องเที่ยว/แผนผัง) — หลักสูตรอยู่ในเมนูทั้งหมด


# ---------- wayfinding ----------

import wayfinding


def test_wants_map_true_for_location_keywords():
    assert wayfinding.wants_map("สาขาอิเล็กทรอนิกส์อยู่ตึกไหน") is True
    assert wayfinding.wants_map("งานพัสดุอยู่อาคารไหน") is True
    assert wayfinding.wants_map("ห้องสมุดอยู่ที่ไหน") is True
    assert wayfinding.wants_map("ไปยังหอประชุมได้ยังไง") is True
    assert wayfinding.wants_map("แผนผังวิทยาลัยมีไหม") is True
    assert wayfinding.wants_map("โรงอาหารอยู่ตรงไหน") is True
    assert wayfinding.wants_map("ที่จอดรถอยู่ที่ไหน") is True


def test_wants_map_false_for_non_location():
    assert wayfinding.wants_map("ค่าเทอมเท่าไหร่") is False
    assert wayfinding.wants_map("เปิดสอนสาขาอะไรบ้าง") is False
    assert wayfinding.wants_map("สมัครเรียนต้องมีคุณสมบัติอะไร") is False
    assert wayfinding.wants_map("ติดต่อวิทยาลัยได้ช่องทางไหนบ้าง") is False
    assert wayfinding.wants_map("") is False
    assert wayfinding.wants_map("สาขานี้มีจุดเด่นอะไร") is False


def test_wants_map_false_for_off_campus_questions():
    """ถามที่เที่ยว/ของฝากนอกวิทยาลัย ต้องไม่แนบแผนผังวิทยาลัย แม้มีคำว่า 'ที่ไหน'"""
    assert wayfinding.wants_map("เสาไห้มีที่ไหนน่าเที่ยว") is False
    assert wayfinding.wants_map("สระบุรีมีที่เที่ยวที่ไหนบ้าง") is False
    assert wayfinding.wants_map("ซื้อของฝากได้ที่ไหน") is False
    assert wayfinding.wants_map("น้ำตกเจ็ดสาวน้อยไปยังไง") is False
    assert wayfinding.wants_map("ใกล้วิทยาลัยมีร้านอาหารอร่อยตรงไหนบ้าง") is False


# ---------- map asset ----------

def test_map_asset_served():
    c = make_client()
    r = c.get("/static/map.jpg")
    assert r.status_code == 200
    assert r.data[:3] == b"\xff\xd8\xff"  # JPEG magic bytes


# ---------- /ask + image ----------

def test_ask_location_question_includes_image(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)
    monkeypatch.setattr(server, "ask_ai", lambda q, c, s, lang="th": "อาคาร 7 ครับ")
    monkeypatch.setattr(server, "wants_map", lambda q: True)
    r = c.post("/ask", json={"question": "สาขาอิเล็กทรอนิกส์อยู่ตึกไหน"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["answer"] == "อาคาร 7 ครับ"
    assert d.get("image") == "/static/map.jpg"


def test_ask_non_location_question_no_image(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)
    monkeypatch.setattr(server, "ask_ai", lambda q, c, s, lang="th": "ตอบ: ค่าเทอม")
    monkeypatch.setattr(server, "wants_map", lambda q: False)
    r = c.post("/ask", json={"question": "ค่าเทอมเท่าไหร่"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["answer"] == "ตอบ: ค่าเทอม"
    assert "image" not in d


# ---------- map chip ----------

def test_screen_has_map_chip():
    c = make_client()
    screen = c.get("/screen")
    assert screen.status_code == 200
    html = screen.data.decode("utf-8")
    assert "แผนผังวิทยาลัย" in html
    assert 'data-action="showMap"' in html


def test_screen_chips_cover_college_and_saraburi():
    html = make_client().get("/screen").data.decode("utf-8")
    assert "ค่าเทอมเท่าไหร่" not in html          # ไม่มีข้อมูลค่าเทอม กดแล้วได้แค่ "ติดต่อเจ้าหน้าที่"
    assert 'data-q="สระบุรีมีที่เที่ยวที่ไหนบ้าง"' in html
    assert 'data-q="ติดต่อวิทยาลัยได้ช่องทางไหนบ้าง"' in html


# ---------- gpio_btn ----------

import queue as _queue
import gpio_btn


def test_gpio_btn_init_simulator_mode():
    """SIMULATOR_MODE=True: init ต้องไม่ crash และ queue ต้องว่าง"""
    q = _queue.Queue()
    btn = gpio_btn.GpioButton(q)
    assert q.empty()


# ---------- SSE /events ----------


def test_events_endpoint_returns_stream(monkeypatch):
    """/events ต้องคืน text/event-stream และเริ่มด้วย 'data: connected'"""
    def finite_stream():
        yield "data: connected\n\n"
    monkeypatch.setattr(server, "_make_sse_stream", finite_stream)
    c = make_client()
    r = c.get("/events")
    assert r.status_code == 200
    assert "text/event-stream" in r.content_type
    assert b"data: connected" in r.data


# ---------- ภาษา (th/en) ----------

def test_state_carries_language_for_face():
    """จอเนื้อหาเลือกภาษา → เซิร์ฟเวอร์จำไว้ → จอใบหน้าอ่านจาก GET /state"""
    c = make_client()
    server.state["lang"] = "th"
    assert c.get("/state").get_json()["lang"] == "th"
    r = c.post("/state", json={"state": "idle", "lang": "en"})
    assert r.get_json()["lang"] == "en"
    assert c.get("/state").get_json()["lang"] == "en"
    c.post("/state", json={"state": "idle", "lang": "fr"})   # ภาษาที่ไม่รองรับ ไม่เปลี่ยน
    assert c.get("/state").get_json()["lang"] == "en"
    server.state["lang"] = "th"


def test_ask_passes_language_to_ai(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)
    seen = []
    monkeypatch.setattr(server, "ask_ai", lambda q, c_, s, lang="th": seen.append(lang) or "ok")
    c.post("/ask", json={"question": "hello", "lang": "en"})
    c.post("/ask", json={"question": "สวัสดี"})                 # ไม่ส่ง lang = ไทย
    c.post("/ask", json={"question": "x", "lang": "evil"})      # ค่าแปลก = ไทย
    assert seen == ["en", "th", "th"]


def test_wants_map_english_questions():
    assert wayfinding.wants_map("Where is the canteen?") is True
    assert wayfinding.wants_map("Can I see the campus map?") is True
    assert wayfinding.wants_map("Where is the electronics building?") is True
    assert wayfinding.wants_map("Where is the workshop?") is True
    assert wayfinding.wants_map("What are the places to visit in Saraburi?") is False
    assert wayfinding.wants_map("Where can I buy souvenirs?") is False
    assert wayfinding.wants_map("What programs does the college offer?") is False


def test_screen_has_language_and_theme_switches():
    """จอหน้าวิทยาลัยใช้ภาษาไทยอย่างเดียว (เจ้าของสั่งเอาภาษาอังกฤษออก)"""
    html = make_client().get("/screen").data.decode("utf-8")
    assert 'data-lang="en"' not in html and 'id="langSeg"' not in html
    js = make_client().get("/static/screen.js").data.decode("utf-8")
    assert 'let lang = "th"' in js
    assert 'id="themeBtn"' not in html   # ดีไซน์ใหม่มีโหมดสว่างอย่างเดียว


# ---------- คำตอบแบบทยอยไหล (/ask/stream) ----------

import json as _json


def _lines(r):
    return [_json.loads(l) for l in r.get_data(as_text=True).splitlines() if l.strip()]


def test_ask_stream_sends_pieces_then_done(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)
    monkeypatch.setattr(server, "ask_ai_stream", lambda q, c_, s, lang="th": iter(["สวัส", "ดีค่ะ"]))
    monkeypatch.setattr(server, "wants_map", lambda q: False)
    r = c.post("/ask/stream", json={"question": "hi"})
    assert r.status_code == 200
    assert _lines(r) == [{"t": "สวัส"}, {"t": "ดีค่ะ"}, {"done": True, "image": None, "photos": []}]
    assert server.state["value"] == "answering"


def test_ask_stream_passes_language_and_map(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)
    seen = []
    monkeypatch.setattr(server, "ask_ai_stream", lambda q, c_, s, lang="th": seen.append(lang) or iter(["x"]))
    r = c.post("/ask/stream", json={"question": "Where is the canteen?", "lang": "en"})
    assert seen == ["en"]
    assert _lines(r)[-1] == {"done": True, "image": "/static/map.jpg", "photos": []}


def test_ask_stream_error_midway_keeps_text_and_reports(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)

    def broken(q, c_, s, lang="th"):
        yield "ครึ่ง"
        raise RuntimeError("503 overloaded")

    monkeypatch.setattr(server, "ask_ai_stream", broken)
    lines = _lines(c.post("/ask/stream", json={"question": "x"}))
    assert lines[0] == {"t": "ครึ่ง"}
    assert "ยุ่ง" in lines[-1]["error"]          # 503 → ข้อความที่คนอ่านเข้าใจ
    assert server.state["value"] == "error"


def test_ask_stream_without_key_returns_500(monkeypatch):
    c = make_client()
    monkeypatch.setattr(server.config, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(server.config, "GEMINI_API_KEY", "")
    r = c.post("/ask/stream", json={"question": "x"})
    assert r.status_code == 500
    assert "GEMINI_API_KEY" in r.get_json()["error"]


def test_friendly_error_messages():
    quota = RuntimeError("429 RESOURCE_EXHAUSTED. quota exceeded")
    assert "โควตา" in server.friendly_error(quota, "th")
    assert "quota" in server.friendly_error(quota, "en")
    assert "busy" in server.friendly_error(RuntimeError("503 UNAVAILABLE"), "en")
    assert server.friendly_error(RuntimeError("อื่น ๆ"), "th") == "อื่น ๆ"


# ---------- รูปสถานที่ + เมนู ----------

PHOTO = {"src": "/static/places/a.jpg", "name": "n", "caption": "c"}


def test_ask_stream_done_has_photos_from_full_answer(monkeypatch):
    # stream แยกชื่อเป็น 2 ท่อน → ต้องคำนวณจากคำตอบที่ต่อครบแล้ว
    c = make_client()
    set_valid_key(monkeypatch)
    monkeypatch.setattr(server, "ask_ai_stream", lambda q, c_, s, lang="th": iter(["ไปน้ำตกเจ็ด", "สาวน้อยค่ะ"]))
    monkeypatch.setattr(server, "wants_map", lambda q: False)
    seen = []
    monkeypatch.setattr(server, "photos_for", lambda q, a, d, lang="th": seen.append((q, a, lang)) or [PHOTO])
    last = _lines(c.post("/ask/stream", json={"question": "เที่ยวไหนดี"}))[-1]
    assert seen == [("เที่ยวไหนดี", "ไปน้ำตกเจ็ดสาวน้อยค่ะ", "th")]
    assert last["photos"] == [PHOTO]


def test_ask_includes_photos(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)
    monkeypatch.setattr(server, "ask_ai", lambda q, c_, s, lang="th": "Jet Sao Noi")
    monkeypatch.setattr(server, "wants_map", lambda q: False)
    seen = []
    monkeypatch.setattr(server, "photos_for", lambda q, a, d, lang="th": seen.append(lang) or [PHOTO])
    d = c.post("/ask", json={"question": "where?", "lang": "en"}).get_json()
    assert d["photos"] == [PHOTO]
    assert seen == ["en"]


def test_map_question_has_map_and_no_photos(monkeypatch):
    c = make_client()
    set_valid_key(monkeypatch)
    monkeypatch.setattr(server, "ask_ai", lambda q, c_, s, lang="th": "อาคาร 7")
    monkeypatch.setattr(server, "ask_ai_stream", lambda q, c_, s, lang="th": iter(["อาคาร 7"]))
    monkeypatch.setattr(server, "wants_map", lambda q: True)

    def no_photos(*a, **k):
        raise AssertionError("ไม่ควรหารูปที่เที่ยวตอนโชว์แผนผัง")

    monkeypatch.setattr(server, "photos_for", no_photos)
    d = c.post("/ask", json={"question": "โรงอาหารอยู่ไหน"}).get_json()
    assert d["image"] == "/static/map.jpg" and d["photos"] == []
    last = _lines(c.post("/ask/stream", json={"question": "โรงอาหารอยู่ไหน"}))[-1]
    assert last == {"done": True, "image": "/static/map.jpg", "photos": []}


def _no_ai(*a, **k):
    raise AssertionError("เมนูห้ามเรียก AI")


def test_menu_endpoint_returns_tree_without_ai(monkeypatch):
    monkeypatch.setattr(server, "ask_ai", _no_ai)
    monkeypatch.setattr(server, "ask_ai_stream", _no_ai)
    r = make_client().get("/menu")
    assert r.status_code == 200
    m = r.get_json()
    assert set(m) == {"trips", "souvenirs", "stay", "food", "cafe", "market"}
    assert [c["key"] for c in m["trips"]["categories"]] == list(server.saraburi_data["ท่องเที่ยวสระบุรี"])


def test_menu_endpoint_with_empty_data(monkeypatch):
    monkeypatch.setattr(server, "saraburi_data", {})
    m = make_client().get("/menu").get_json()
    assert m["trips"]["categories"] == [] and m["souvenirs"]["categories"] == [] and m["stay"]["categories"] == []


def test_screen_trip_and_souvenir_chips_open_menu():
    html = make_client().get("/screen").get_data(as_text=True)
    assert 'data-menu="trips"' in html and 'data-menu="souvenirs"' in html
    # ยังมี data-q ไว้เป็นทางสำรองตอน /menu โหลดไม่ได้
    assert 'data-q="สระบุรีมีที่เที่ยวที่ไหนบ้าง"' in html


def test_screen_js_uses_menu_and_photos():
    js = make_client().get("/static/screen.js").get_data(as_text=True)
    assert 'fetch("/menu")' in js and "photos" in js and "place-photo" in js


def test_place_card_shows_hours_phone_address():
    js = make_client().get("/static/screen.js").get_data(as_text=True)
    for needle in ("it.hours", "it.phone", "it.address"):
        assert needle in js, needle


# ---- ทักทาย: แขนโบก + หน้าหุ่น + คำทัก ----
class FakeArm:
    def __init__(self, ok=True):
        self.calls = 0
        self.ok = ok

    def wave_async(self):          # แขนสเต็ปเปอร์ผ่าน ESP32 (stepper.StepperArms)
        self.calls += 1
        return self.ok


def test_greet_waves_arm(monkeypatch):
    c = make_client()
    arm = FakeArm()
    monkeypatch.setattr(server, "arm", arm)
    r = c.post("/greet")
    assert r.status_code == 200
    assert r.get_json() == {"ok": True, "waving": True}
    assert arm.calls == 1


def test_greet_while_arm_busy_reports_not_waving(monkeypatch):
    c = make_client()
    monkeypatch.setattr(server, "arm", FakeArm(ok=False))
    assert c.post("/greet").get_json()["waving"] is False


def test_request_greet_pushes_event_to_screen():
    """เซนเซอร์ (เช่น อัลตราโซนิก) เรียก request_greet() → จอได้สัญญาณ greet ทาง /events"""
    while not server.button_queue.empty():
        server.button_queue.get_nowait()
    server.request_greet()
    assert server.button_queue.get_nowait() == "greet"


def test_face_has_greeting_mood():
    c = make_client()
    html = c.get("/face").data.decode("utf-8")
    assert "state-greeting" in html
    js = c.get("/static/face.js").data.decode("utf-8")
    assert "greeting" in js


def test_face_shows_waving_hand_when_greeting():
    """บนคอมไม่มีแขนจริง — หน้าหุ่นต้องมีมือโบกให้เห็นตอนทักทาย"""
    html = make_client().get("/face").data.decode("utf-8")
    assert 'class="hand"' in html
    assert "body.state-greeting .hand" in html


def test_screen_greets_as_male_tantawan():
    c = make_client()
    js = c.get("/static/screen.js").data.decode("utf-8")
    assert "ผมชื่อน้องทานตะวัน-Bot" in js and "ทีแอลบอท" not in js
    assert "หนู" not in js and "ค่ะ" not in js
    assert "/greet" in js


def test_tapping_attract_video_always_greets():
    """แตะคลิปหน้ารอ ("แตะจอเพื่อถามหุ่นยนต์") → แขนโบกทักทุกครั้ง ไม่ต้องรอครบเวลาเงียบ"""
    c = make_client()
    js = c.get("/static/screen.js").data.decode("utf-8")
    assert "if (quiet || attractOn) greet();" in js


# ---- สถิติ: เก็บคำถาม + ให้ดาว ----
def test_ask_stream_logs_question(monkeypatch, temp_stats):
    c = make_client()
    set_valid_key(monkeypatch)
    monkeypatch.setattr(server, "ask_ai_stream", lambda q, c_, s, lang="th": iter(["ok"]))
    monkeypatch.setattr(server, "wants_map", lambda q: False)
    c.post("/ask/stream", json={"question": "สาขาอะไรบ้าง"}).get_data()
    assert temp_stats.summary()["top"] == [{"question": "สาขาอะไรบ้าง", "count": 1}]


def test_rate_saves_stars(temp_stats):
    c = make_client()
    r = c.post("/rate", json={"stars": 4, "question": "ติดต่อยังไง", "lang": "th"})
    assert r.status_code == 200
    s = temp_stats.summary()
    assert s["ratings_total"] == 1 and s["average"] == 4


def test_rate_rejects_bad_stars(temp_stats):
    c = make_client()
    for bad in (0, 6, "5", None):
        assert c.post("/rate", json={"stars": bad, "question": "q"}).status_code == 400
    assert temp_stats.summary()["ratings_total"] == 0


def test_stats_page_and_json(temp_stats):
    c = make_client()
    temp_stats.add_rating(5, "q", "th")
    assert c.get("/stats").status_code == 200
    assert c.get("/stats.json").get_json()["ratings_total"] == 1


def test_screen_has_star_rating():
    js = make_client().get("/static/screen.js").data.decode("utf-8")
    assert "/rate" in js


# ---- โหมดรอ: วิดีโอวน ----
def test_attract_lists_videos(tmp_path, monkeypatch):
    vids = tmp_path / "videos"
    vids.mkdir()
    (vids / "b.mp4").write_bytes(b"x")
    (vids / "a.webm").write_bytes(b"x")
    (vids / "readme.txt").write_text("ไม่ใช่วิดีโอ", encoding="utf-8")
    monkeypatch.setattr(server, "VIDEO_DIR", vids)
    monkeypatch.setattr(server.config, "IDLE_VIDEO_SECONDS", 90)
    d = make_client().get("/attract").get_json()
    assert d["videos"] == ["/static/videos/a.webm", "/static/videos/b.mp4"]
    assert d["after"] == 90


def test_attract_without_video_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "VIDEO_DIR", tmp_path / "ไม่มี")
    assert make_client().get("/attract").get_json()["videos"] == []


# ---- ประกาศตามเวลา ----
def test_announcements_due(tmp_path, monkeypatch):
    import json
    from datetime import datetime
    p = tmp_path / "announcements.json"
    p.write_text(json.dumps([{"เวลา": "08:00", "ข้อความ": "สวัสดีตอนเช้าค่ะ"}], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(server.config, "ANNOUNCEMENTS_PATH", str(p))
    monkeypatch.setattr(server, "_now", lambda: datetime(2026, 11, 2, 8, 0, 5))
    d = make_client().get("/announcements/due").get_json()
    assert [a["text"] for a in d["due"]] == ["สวัสดีตอนเช้าค่ะ"]
    monkeypatch.setattr(server, "_now", lambda: datetime(2026, 11, 2, 9, 0, 5))
    assert make_client().get("/announcements/due").get_json()["due"] == []


# ---- /tts: เสียงพูด AI ----
@pytest.fixture
def tts_env(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(server.config, "TTS_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(server.config, "AI_VOICE", True)
    monkeypatch.setattr(server.config, "VOICE_ENGINE", "edge")

    def fake_edge(text, lang):
        calls.append((text, lang))
        yield b"ID3"
        yield b"mp3data"
    monkeypatch.setattr(server, "edge_mp3_stream", fake_edge)
    return calls


def test_tts_streams_mp3_and_caches(tts_env):
    c = make_client()
    r = c.get("/tts", query_string={"text": "สวัสดีครับ", "lang": "th"})
    assert r.status_code == 200 and r.mimetype == "audio/mpeg" and r.get_data() == b"ID3mp3data"
    r2 = c.get("/tts", query_string={"text": "สวัสดีครับ", "lang": "th"})
    assert r2.status_code == 200 and r2.get_data() == b"ID3mp3data"
    assert tts_env == [("สวัสดีครับ", "th")]   # ครั้งที่สองใช้ไฟล์ที่เก็บไว้ ไม่สร้างซ้ำ


def test_tts_rejects_empty_or_too_long(tts_env):
    c = make_client()
    assert c.get("/tts", query_string={"text": ""}).status_code == 400
    assert c.get("/tts", query_string={"text": "ก" * 601}).status_code == 400


def test_tts_edge_failure_returns_503(tts_env, monkeypatch):
    def broken(text, lang):
        raise ConnectionError("no internet")
        yield b""
    monkeypatch.setattr(server, "edge_mp3_stream", broken)
    assert make_client().get("/tts", query_string={"text": "สวัสดี"}).status_code == 503


def test_tts_disabled_by_config(tts_env, monkeypatch):
    monkeypatch.setattr(server.config, "AI_VOICE", False)
    assert make_client().get("/tts", query_string={"text": "สวัสดี"}).status_code == 404


def test_tts_gemini_engine_quota_cools_down(tts_env, monkeypatch):
    monkeypatch.setattr(server.config, "VOICE_ENGINE", "gemini")
    monkeypatch.setattr(server.config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(server, "_tts_off_until", 0.0)
    hits = []

    def boom(text, lang):
        hits.append(text)
        raise RuntimeError("429 RESOURCE_EXHAUSTED")
    monkeypatch.setattr(server, "speak_wav", boom)
    c = make_client()
    assert c.get("/tts", query_string={"text": "หนึ่ง"}).status_code == 503
    assert c.get("/tts", query_string={"text": "สอง"}).status_code == 503
    assert hits == ["หนึ่ง"]


def test_gemini_voice_gets_only_the_text(monkeypatch):
    import ai
    seen = []

    class Models:
        def generate_content_stream(self, model, contents, config):
            seen.append(contents)
            part = type("P", (), {"inline_data": type("D", (), {"data": b"\x00\x00"})()})()
            yield type("C", (), {"candidates": [type("X", (), {"content": type("Y", (), {"parts": [part]})()})()]})()
    monkeypatch.setattr(ai, "_gemini_client", lambda key: type("Cl", (), {"models": Models()})())
    assert b"".join(ai.speak_pcm_stream("สวัสดีครับ", "th")) == b"\x00\x00"
    assert seen == ["สวัสดีครับ"]   # ไม่มีคำสั่งนำหน้า (เคยโดนอ่านออกเสียง)


def test_screen_uses_ai_voice_with_local_fallback():
    js = make_client().get("/static/screen.js").data.decode("utf-8")
    assert "/tts?lang=" in js and "localSpeak" in js and "TTS_TIMEOUT_MS" in js
    assert "startAttract()" in js and "STARTS_IN_ATTRACT" not in js   # วิดีโอแทรกเมื่อว่างนาน (ไม่เริ่มที่วิดีโอ)


# ---- จำคำตอบ: ถามซ้ำตอบได้ทันที ไม่ถาม AI ใหม่ ----
def test_repeat_question_answered_from_cache(monkeypatch):
    calls = []

    def fake_stream(q, c_, s, lang="th"):
        calls.append(q)
        yield "มีสาขา"
        yield "ยานยนต์ไฟฟ้าครับ"
    monkeypatch.setattr(server.config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(server, "ask_ai_stream", fake_stream)
    c = make_client()
    first = c.post("/ask/stream", json={"question": "มีสาขายานยนต์ไฟฟ้าไหม"}).get_data(as_text=True)
    again = c.post("/ask/stream", json={"question": "มีสาขายานยนต์ไฟฟ้าไหมครับ ?"}).get_data(as_text=True)
    assert calls == ["มีสาขายานยนต์ไฟฟ้าไหม"]   # ครั้งที่สองไม่ถาม AI (ต่างแค่ "ครับ ?")
    text = lambda out: "".join(_json.loads(l).get("t", "") for l in out.splitlines() if l.strip())   # noqa: E731
    assert text(first) == text(again) == "มีสาขายานยนต์ไฟฟ้าครับ"
    assert sum(t["count"] for t in server.stats.summary()["top"]) == 2   # ตอบจากที่จำไว้ก็ยังนับสถิติ


def test_failed_answer_is_not_cached(monkeypatch):
    calls = []

    def flaky(q, c_, s, lang="th"):
        calls.append(q)
        yield "ครึ่ง"
        raise RuntimeError("503 UNAVAILABLE")
    monkeypatch.setattr(server.config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(server, "ask_ai_stream", flaky)
    c = make_client()
    c.post("/ask/stream", json={"question": "ห้องสมุดอยู่ไหน"}).get_data()
    c.post("/ask/stream", json={"question": "ห้องสมุดอยู่ไหน"}).get_data()
    assert len(calls) == 2


# ---------- สแกน QR ----------
def qr_file(tmp_path, monkeypatch, data):
    import json
    p = tmp_path / "qr.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(server.config, "QR_CODES_PATH", str(p))   # ROBOT_DIR / ไฟล์แบบ absolute = ไฟล์นั้น


def test_qr_question_code(tmp_path, monkeypatch):
    qr_file(tmp_path, monkeypatch, {"TL-A": {"ชื่อ": "ห้อง A", "คำถาม": "ห้อง A อยู่ไหน", "คำถามอังกฤษ": "Where is A?"}})
    c = make_client()
    assert c.get("/qr?code=tl-a").get_json() == {"label": "ห้อง A", "question": "ห้อง A อยู่ไหน"}
    assert c.get("/qr?code=TL-A&lang=en").get_json()["question"] == "Where is A?"


def test_qr_fixed_answer_is_counted_in_stats(tmp_path, monkeypatch, temp_stats):
    qr_file(tmp_path, monkeypatch, {"TL-B": {"ชื่อ": "ทดสอบ", "คำตอบ": "ใช้ได้"}})
    r = make_client().get("/qr?code=TL-B")
    assert r.get_json() == {"label": "ทดสอบ", "answer": "ใช้ได้"}
    assert [r[0] for r in temp_stats._conn.execute("SELECT question FROM questions")] == ["[QR] ทดสอบ"]


def test_qr_unknown_code_404(tmp_path, monkeypatch):
    qr_file(tmp_path, monkeypatch, {})
    assert make_client().get("/qr?code=WHAT").status_code == 404


# ---- ฟังเสียงที่เซิร์ฟเวอร์ (Chromium บน Pi ใช้ Web Speech ของ Google ไม่ได้) ----
@pytest.fixture
def stt_env(monkeypatch):
    set_valid_key(monkeypatch)
    calls = []

    def fake_transcribe(audio, mime, lang):
        calls.append((audio, mime, lang))
        return "ห้องสมุดอยู่ไหน"
    monkeypatch.setattr(server, "transcribe", fake_transcribe)
    return calls


def test_stt_returns_text(stt_env):
    r = make_client().post("/stt?lang=th", data=b"webmdata", content_type="audio/webm;codecs=opus")
    assert r.status_code == 200 and r.get_json() == {"text": "ห้องสมุดอยู่ไหน"}
    assert stt_env == [(b"webmdata", "audio/webm", "th")]


def test_stt_rejects_empty_or_too_big(stt_env):
    c = make_client()
    assert c.post("/stt", data=b"", content_type="audio/webm").status_code == 400
    big = b"x" * (server.STT_MAX_BYTES + 1)
    assert c.post("/stt", data=big, content_type="audio/webm").status_code == 413
    assert stt_env == []


def test_stt_quota_error_is_friendly(stt_env, monkeypatch):
    def boom(audio, mime, lang):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")
    monkeypatch.setattr(server, "transcribe", boom)
    r = make_client().post("/stt", data=b"a", content_type="audio/webm")
    assert r.status_code == 503 and r.get_json()["error"]


def test_transcribe_sends_audio_and_cleans_no_speech(monkeypatch):
    import ai
    seen = []

    class Models:
        def __init__(self, reply): self.reply = reply
        def generate_content(self, model, contents, config):
            seen.append(contents)
            return type("R", (), {"text": self.reply})()
    monkeypatch.setattr(ai, "_keys_in_order", lambda: [(0, "k")])
    monkeypatch.setattr(ai, "_gemini_client", lambda key: type("Cl", (), {"models": Models(" ห้องสมุดอยู่ไหน \n")})())
    assert ai.transcribe(b"aud", "audio/webm", "th") == "ห้องสมุดอยู่ไหน"
    monkeypatch.setattr(ai, "_gemini_client", lambda key: type("Cl", (), {"models": Models("ห้อง สมุด อยู่ ไหน ครับ ห้อง 301")})())
    assert ai.transcribe(b"aud", "audio/webm", "th") == "ห้องสมุดอยู่ไหนครับห้อง 301"
    part = seen[0][0]
    assert part.inline_data.data == b"aud" and part.inline_data.mime_type == "audio/webm"
    monkeypatch.setattr(ai, "_gemini_client", lambda key: type("Cl", (), {"models": Models("[NO_SPEECH]")})())
    assert ai.transcribe(b"aud", "audio/webm", "th") == ""


# ---- โฟลเดอร์ข้อมูลถาวร (แฟลชไดรฟ์บน Pi) ----
def test_stats_db_lives_in_data_dir():
    # (fixture แทน server.stats ด้วยฐานชั่วคราว — เช็กไฟล์จริงที่สร้างตอน import แทน)
    assert server.DATA.path("stats.db").is_file()


def test_config_defaults_for_kiosk():
    assert server.config.IDLE_VIDEO_SECONDS == 60          # เท่ากับ GREET_IDLE_SECONDS: คลิปขึ้นพร้อมจังหวะที่แขนพร้อมโบกทัก
    assert server.config.IDLE_VIDEO_SECONDS == server.config.GREET_IDLE_SECONDS
    assert hasattr(server.config, "ADMIN_PASSWORD")


# ---- ข่าวประชาสัมพันธ์ + หน้าครู ----
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100


@pytest.fixture
def news_env(tmp_path, monkeypatch):
    from news import NewsStore
    store = NewsStore(tmp_path)
    monkeypatch.setattr(server, "news", store)
    monkeypatch.setattr(server.config, "ADMIN_PASSWORD", "ครู1234")
    server._admin_tokens.clear()
    return store


def login(c, pw="ครู1234"):
    return c.post("/admin/login", json={"password": pw})


def news_form(**kw):
    d = {"category": "event", "title": "งานเปิดบ้าน", "subtitle": "20 ธ.ค.", "detail": "มีกิจกรรม"}
    d.update(kw)
    return d


def test_admin_login_wrong_and_right(news_env):
    c = make_client()
    assert login(c, "ผิด").status_code == 401
    r = login(c)
    assert r.status_code == 200 and "tlbot_admin=" in r.headers.get("Set-Cookie", "")
    assert c.get("/admin/news").status_code == 200


def test_admin_disabled_without_password(news_env, monkeypatch):
    monkeypatch.setattr(server.config, "ADMIN_PASSWORD", "")
    assert login(make_client(), "").status_code == 403


def test_admin_needs_login(news_env):
    c = make_client()
    assert c.get("/admin/news").status_code == 401
    assert c.post("/admin/news", data=news_form()).status_code == 401
    assert c.delete("/admin/news/abc").status_code == 401


def test_add_news_with_image_shows_on_screen(news_env):
    import io
    c = make_client(); login(c)
    r = c.post("/admin/news", data={**news_form(), "image": (io.BytesIO(JPEG), "a.jpg")},
               content_type="multipart/form-data")
    assert r.status_code == 201
    pub = make_client().get("/news").get_json()
    item = pub["items"][0]
    assert item["title"] == "งานเปิดบ้าน" and item["image_url"].startswith("/news/img/")
    assert make_client().get(item["image_url"]).data == JPEG
    assert pub["version"]


def test_add_news_rejects_non_image(news_env):
    import io
    c = make_client(); login(c)
    r = c.post("/admin/news", data={**news_form(), "image": (io.BytesIO(b"hello"), "a.txt")},
               content_type="multipart/form-data")
    assert r.status_code == 400 and r.get_json()["error"]


def test_add_news_rejects_huge_upload(news_env):
    import io
    c = make_client(); login(c)
    big = b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024)
    r = c.post("/admin/news", data={**news_form(), "image": (io.BytesIO(big), "a.jpg")},
               content_type="multipart/form-data")
    assert r.status_code == 413


def test_edit_delete_and_order(news_env):
    c = make_client(); login(c)
    a = c.post("/admin/news", data=news_form(title="A")).get_json()
    b = c.post("/admin/news", data=news_form(title="B")).get_json()
    assert c.post(f"/admin/news/{a['id']}", data={"title": "A2"}).get_json()["title"] == "A2"
    assert c.post("/admin/news/order", json={"ids": [a["id"], b["id"]]}).status_code == 200
    assert [n["title"] for n in c.get("/news").get_json()["items"]] == ["A2", "B"]
    assert c.delete(f"/admin/news/{a['id']}").status_code == 200
    assert c.delete(f"/admin/news/{a['id']}").status_code == 404
    assert c.post("/admin/news/nope", data={"title": "x"}).status_code == 404


def test_admin_news_reports_storage(news_env):
    c = make_client(); login(c)
    st = c.get("/admin/news").get_json()["storage"]
    assert set(st) == {"persistent", "path"}


def test_news_image_bad_name_404(news_env):
    assert make_client().get("/news/img/..%2Fnews.json").status_code == 404


def test_news_reaches_ai_and_resets_cache(news_env, monkeypatch):
    import ai
    seen = []
    monkeypatch.setattr(server, "ask_ai_stream", lambda q, c, s, lang="th": (seen.append(ai.extra_context()) or iter(["ตอบ"])))
    monkeypatch.setattr(server.config, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(server.config, "AI_PROVIDER", "gemini")
    c = make_client()
    c.post("/ask/stream", json={"question": "มีงานอะไรบ้าง"}).get_data()
    login(c); c.post("/admin/news", data=news_form(title="งานเปิดบ้าน"))
    c.post("/ask/stream", json={"question": "มีงานอะไรบ้าง"}).get_data()
    assert len(seen) == 2 and "งานเปิดบ้าน" in seen[1]


def fake_weather(monkeypatch, payload=None, fail=False):
    import json as _json

    class R:
        def __init__(self, b): self.b = b
        def read(self): return self.b
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def opener(url, timeout=None):
        if fail:
            raise OSError("no internet")
        return R(_json.dumps(payload).encode())
    monkeypatch.setattr(server, "urlopen", opener)


WX = {"current": {"temperature_2m": 33.4, "weather_code": 2},
      "daily": {"temperature_2m_max": [35.1], "temperature_2m_min": [24.2], "precipitation_probability_max": [40]}}


def test_weather_ok(monkeypatch):
    monkeypatch.setattr(server, "_weather_cache", {"at": 0, "data": None})
    fake_weather(monkeypatch, WX)
    d = make_client().get("/weather").get_json()
    assert d["temp"] == 33 and d["text_th"] == "แดดสลับเมฆ" and d["high"] == 35 and d["low"] == 24 and d["rain"] == 40


def test_weather_offline_without_cache_503(monkeypatch):
    monkeypatch.setattr(server, "_weather_cache", {"at": 0, "data": None})
    fake_weather(monkeypatch, fail=True)
    assert make_client().get("/weather").status_code == 503


def test_weather_offline_uses_recent_cache(monkeypatch):
    import time
    monkeypatch.setattr(server, "_weather_cache", {"at": time.time() - 3600, "data": {"temp": 30}})
    fake_weather(monkeypatch, fail=True)
    assert make_client().get("/weather").get_json()["temp"] == 30


def test_stats_page_has_news_admin():
    html = make_client().get("/stats").get_data(as_text=True)
    for needle in ('id="newsTab"', 'id="newsForm"', 'id="newsList"', 'id="loginBox"', "function shrinkImage",
                   'fetch("/stats.json")', "/admin/news", 'id="storageWarn"'):
        assert needle in html, needle
    for cat in ("admission", "event", "scholarship", "award", "general"):
        assert f'value="{cat}"' in html, cat



# ---- จอ 1920 แบบใหม่ (ข่าว + แชท) ----
def test_new_screen_layout():
    html = make_client().get("/screen").get_data(as_text=True)
    for needle in ('id="app"', 'id="home"', 'id="board"', 'id="newsGrid"', 'id="clock"', 'id="weather"',
                   'id="chat"', 'id="mic"', 'id="composer"', 'id="dockQs"', 'data-action="allMenu"', 'id="allMenuTpl"',
                   'class="osk-host', 'id="stopTalk"', 'id="attract"', 'id="tourView"', 'id="announce"'):
        assert needle in html, needle
    assert "<aside" not in html and 'id="welcomeSlot"' not in html
    assert html.index("/static/vendor/qrcode.js") < html.index("/static/news.js") < html.index("/static/screen.js") < html.index("/static/osk.js")


def test_dock_chips_and_all_menu():
    html = make_client().get("/screen").get_data(as_text=True)
    dock = html[html.index('id="dockQs"'):html.index("</div>", html.index('id="dockQs"'))]
    assert 'data-action="showMap"' in dock and 'data-menu="trips"' in dock
    assert "สมัครเรียน" in dock and "หลักสูตร" not in dock and "สถานที่ท่องเที่ยว" in dock
    # ลำดับ: จุดเด่นวิทยาลัย → สมัครเรียน → สถานที่ท่องเที่ยว → แผนผัง
    assert (dock.index("จุดเด่นวิทยาลัย") < dock.index("สมัครเรียน") < dock.index('data-menu="trips"')
            < dock.index('data-action="showMap"'))
    tpl = html[html.index('id="allMenuTpl"'):html.index("</template>", html.index('id="allMenuTpl"'))]
    for needle in ('data-action="showMap"', 'data-menu="trips"', 'data-menu="souvenirs"', 'data-menu="stay"', 'data-menu="food"', 'data-menu="cafe"', 'data-menu="market"',
                   'data-q="ติดต่อวิทยาลัยได้ช่องทางไหนบ้าง"',
                   'data-q="เปิดสอนสาขาอะไรบ้าง"'):   # หลักสูตรยังอยู่ในเมนูทั้งหมด
        assert needle in tpl, needle


def test_news_js_drives_left_side():
    js = make_client().get("/static/news.js").get_data(as_text=True)
    for needle in ('fetch("/news")', 'fetch("/weather")', "window.Board", "news-read", "news-refresh", "th-TH"):
        assert needle in js, needle


def test_screen_preview_mode_is_silent():
    js = make_client().get("/static/screen.js").get_data(as_text=True)
    assert "const PREVIEW" in js and "if (PREVIEW) return" in js
    assert "Board.show" in js and "news-read" in js


def test_news_version_changes_at_midnight(news_env, monkeypatch):
    from datetime import datetime
    monkeypatch.setattr(server, "_now", lambda: datetime(2026, 11, 10, 23, 59))
    v1 = make_client().get("/news").get_json()["version"]
    monkeypatch.setattr(server, "_now", lambda: datetime(2026, 11, 11, 0, 1))
    assert make_client().get("/news").get_json()["version"] != v1


def test_news_save_failure_is_503(news_env, monkeypatch):
    c = make_client(); login(c)

    def boom(items):
        raise OSError("drive gone")
    monkeypatch.setattr(news_env, "_save_items", boom)
    r = c.post("/admin/news", data=news_form())
    assert r.status_code == 503 and r.get_json()["error"]


def test_admin_news_rechecks_storage(news_env, monkeypatch):
    c = make_client(); login(c)
    monkeypatch.setattr(server.DATA, "persistent", True)
    monkeypatch.setattr(server, "_writable", lambda p: False)
    assert c.get("/admin/news").get_json()["storage"]["persistent"] is False


def test_news_read_aloud_in_thai():
    js = make_client().get("/static/screen.js").get_data(as_text=True)
    block = js[js.index('window.addEventListener("news-read"'):]
    block = block[:block.index("});")]
    assert 'speakAnswer(text, "th")' in block   # ข่าวที่ครูเขียนเป็นภาษาไทย อ่านด้วยเสียงไทยเสมอ


def test_news_layout_reaches_screen(news_env):
    c = make_client(); login(c)
    c.post("/admin/news", data=news_form(layout="portrait"))
    assert make_client().get("/news").get_json()["items"][0]["layout"] == "portrait"


def test_four_equal_news_blocks():
    js = make_client().get("/static/news.js").get_data(as_text=True)
    assert "PER_PAGE = 4" in js and "portrait" in js and "landscape" in js
    html = make_client().get("/stats").get_data(as_text=True)
    assert 'name="layout" value="portrait"' in html.replace("  ", " ") or 'value="portrait"' in html
    assert 'value="landscape"' in html


def test_news_tap_shows_picture_big():
    js = make_client().get("/static/screen.js").get_data(as_text=True)
    block = js[js.index('window.addEventListener("news-read"'):]
    block = block[:block.index("});")]
    assert "image_url" in block and "showPictures" in block   # แตะข่าวมีรูป → รูปขึ้นใหญ่ฝั่งซ้าย


def test_map_offers_3d_tour():
    js = make_client().get("/static/screen.js").get_data(as_text=True).replace(chr(13), "")
    assert "เยี่ยมชม" in js and "3D" in js
    show = js[js.index("function showPictures"):]
    show = show[:show.index("\n}\n")]
    assert 'data-action="campusTour"' in show   # บนแผนผังมีปุ่มเปิดทัวร์ 3D


def test_screen_js_texts_are_single_line():
    """ข้อความในตาราง T ต้องอยู่ในบรรทัดเดียว (เคยมีการขึ้นบรรทัดจริงในสตริง → JS พังทั้งไฟล์ จอขาว)"""
    js = make_client().get("/static/screen.js").get_data(as_text=True).replace(chr(13), "")
    table = js[js.index("const T = {"):js.index("\n};", js.index("const T = {"))]
    for line in table.split("\n"):
        assert line.replace('\\"', "").count('"') % 2 == 0, line[:60]


def _screen_js():
    return make_client().get("/static/screen.js").get_data(as_text=True).replace(chr(13), "")


def test_answer_speaks_before_stream_ends():
    js = _screen_js()
    assert "function earlySpeech(" in js
    ask = js[js.index("async function ask("):js.index("// ---- ทักทาย")]
    assert "earlySpeech(tw.text" in ask            # ระหว่างคำตอบไหล ได้ช่วงต้นครบแล้วพูดเลย
    assert "spokeEarly" in ask                     # จบแล้วไม่พูดซ้ำ


def test_idle_video_loops_until_tap():
    js = _screen_js()
    play = js[js.index("function playVideo()"):js.index("function startAttract()")]
    assert "stopAttract()" not in play.split('video.addEventListener("ended"')[1].split("\n")[0]
    assert 'video.addEventListener("ended", () => { vidIdx++; playVideo(); });' in js


def test_new_chat_button_under_ready_led():
    """ปุ่มคุยใหม่อยู่หัวแชท ใต้ป้าย "พร้อมคุย" — ไม่ซ่อนในเมนูทั้งหมดแล้ว ช่องนั้นเป็นจุดเด่นวิทยาลัยแทน"""
    html = make_client().get("/screen").get_data(as_text=True)
    head = html[html.index('class="chat-panel'):html.index('id="scroll"')]
    assert head.index('class="led"') < head.index('data-action="newChat"')
    tpl = html[html.index('id="allMenuTpl"'):html.index("</template>", html.index('id="allMenuTpl"'))]
    assert 'data-action="newChat"' not in tpl
    assert 'data-q="วิทยาลัยมีจุดเด่นอะไรบ้าง"' in tpl


def test_admission_link_is_real_not_demo():
    import json
    adm = json.loads((server.ROBOT_DIR / "college_data.json").read_text(encoding="utf-8"))["การรับสมัคร"]
    text = json.dumps(adm, ensure_ascii=False)
    assert "ทดลอง" not in text and "demo" not in text.lower()
    assert adm["สมัครเรียนออนไลน์"]["ลิงก์"].startswith("https://")


def test_wat_tako_and_crocodile_farm_in_trips():
    names = [e["ชื่อ"] for cat in server.saraburi_data["ท่องเที่ยวสระบุรี"].values() for e in cat]
    assert "วัดตะโก" in names and "ฟาร์มจระเข้ศรีอยุธยา" in names


def test_admin_page_installable_as_app():
    """หน้าหลังบ้าน (/stats) ติดตั้งเป็นแอปบนมือถือ/คอมได้: manifest + ไอคอน + ค่า iPhone"""
    import json
    c = make_client()
    html = c.get("/stats").get_data(as_text=True)
    assert '<link rel="manifest" href="/static/admin.webmanifest">' in html
    assert 'name="apple-mobile-web-app-capable" content="yes"' in html
    assert 'rel="apple-touch-icon"' in html
    r = c.get("/static/admin.webmanifest")
    assert r.status_code == 200
    m = json.loads(r.get_data(as_text=True))
    assert m["start_url"] == "/stats" and m["display"] == "standalone"
    for icon in m["icons"]:
        assert c.get(icon["src"]).status_code == 200, icon["src"]
    assert {i["sizes"] for i in m["icons"]} >= {"192x192", "512x512"}
