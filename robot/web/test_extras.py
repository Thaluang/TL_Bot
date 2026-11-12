"""
เทสต์ปฏิทินแนะแนว / คลังภาพกิจกรรม / แบบประเมินความพึงพอใจ / ผลงานรางวัล
รันจากโฟลเดอร์ robot/:  python -m pytest web/test_extras.py -v
"""
import io
from datetime import date, datetime

import pytest

import server
from content import GalleryStore, GuidanceStore
from news import NewsError
from stats import Stats

JPG = b"\xff\xd8\xff\xe0" + b"0" * 100


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "stats", Stats(tmp_path / "stats.db"))
    monkeypatch.setattr(server, "guidance", GuidanceStore(tmp_path))
    monkeypatch.setattr(server, "gallery", GalleryStore(tmp_path))
    monkeypatch.setattr(server.config, "ADMIN_PASSWORD", "ครู1234")
    monkeypatch.setattr(server, "_now", lambda: datetime(2026, 11, 12, 10, 0))
    server._admin_tokens.clear()
    server.app.config["TESTING"] = True
    return tmp_path


def client(logged=True):
    c = server.app.test_client()
    if logged:
        assert c.post("/admin/login", json={"password": "ครู1234"}).status_code == 200
    return c


# ---------- ปฏิทินแนะแนว ----------
def test_guidance_store_validates_and_sorts(tmp_path):
    g = GuidanceStore(tmp_path / "x")
    with pytest.raises(NewsError):
        g.add({"title": "ไม่มีวันที่"})
    with pytest.raises(NewsError):
        g.add({"date": "2026-12-01"})
    with pytest.raises(NewsError):
        g.add({"date": "2026-12-05", "end": "2026-12-01", "title": "ถอยหลัง"})
    g.add({"date": "2026-12-10", "title": "ข"})
    g.add({"date": "2026-12-01", "title": "ก", "end": "2026-12-01"})
    assert [d["title"] for d in g.all()] == ["ก", "ข"]
    assert g.all()[0]["end"] == ""          # วันเดียวกัน ไม่ต้องเก็บวันสิ้นสุด
    assert GuidanceStore(tmp_path / "x").all() == g.all()   # อยู่รอดหลังรีสตาร์ท


def test_guidance_admin_crud_and_public(env):
    assert client(False).post("/admin/guidance", json={"date": "2026-12-01", "title": "x"}).status_code == 401
    c = client()
    r = c.post("/admin/guidance", json={"date": "2026-12-01", "title": "แนะแนว ร.ร.เสาไห้", "time": "09.00 น.", "place": "หอประชุม"})
    assert r.status_code == 201
    gid = r.get_json()["id"]
    assert c.post("/admin/guidance", json={"title": "ไม่มีวัน"}).status_code == 400
    assert c.post(f"/admin/guidance/{gid}", json={"place": "โรงอาหาร"}).get_json()["place"] == "โรงอาหาร"
    pub = client(False).get("/guidance").get_json()
    assert pub["today"] == "2026-11-12" and pub["items"][0]["title"] == "แนะแนว ร.ร.เสาไห้"
    assert c.delete(f"/admin/guidance/{gid}").status_code == 200
    assert c.delete(f"/admin/guidance/{gid}").status_code == 404


def test_robot_knows_upcoming_guidance(env):
    server.guidance.add({"date": "2026-11-01", "title": "งานที่ผ่านไปแล้ว"})
    server.guidance.add({"date": "2026-12-05", "title": "แนะแนว ร.ร.บ้านหมอ", "time": "13.00 น."})
    text = server.ai.extra_context()
    assert "แนะแนว ร.ร.บ้านหมอ" in text and "5 ธ.ค. 2569" in text and "13.00" in text
    assert "งานที่ผ่านไปแล้ว" not in text


# ---------- คลังภาพ ----------
def test_gallery_upload_list_delete(env):
    assert client(False).post("/admin/gallery", data={"title": "x"}).status_code == 401
    c = client()
    r = c.post("/admin/gallery", data={"title": "ต้อนรับผู้ปกครอง", "date": "2026-11-10",
                                         "image": (io.BytesIO(JPG), "a.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 201
    item = r.get_json()
    assert c.post("/admin/gallery", data={"title": "ไม่มีรูป"}).status_code == 400
    assert c.post("/admin/gallery", data={"title": "", "image": (io.BytesIO(JPG), "a.jpg")},
                  content_type="multipart/form-data").status_code == 400
    pub = client(False).get("/gallery").get_json()["items"]
    assert pub[0]["title"] == "ต้อนรับผู้ปกครอง" and pub[0]["image_url"] == item["image_url"]
    assert client(False).get(item["image_url"]).status_code == 200
    assert c.delete(f"/admin/gallery/{item['id']}").status_code == 200
    assert client(False).get(item["image_url"]).status_code == 404
    assert client(False).get("/gallery/img/..%2Fgallery.json").status_code == 404


def test_gallery_rejects_non_image(env):
    r = client().post("/admin/gallery", data={"title": "x", "image": (io.BytesIO(b"hello"), "a.txt")},
                      content_type="multipart/form-data")
    assert r.status_code == 400


# ---------- แบบประเมิน ----------
def _resp(**kw):
    d = {"gender": "female", "role": "student", "usage": ["voice"], "scores": [5] * 10, "liked": "", "improve": ""}
    d.update(kw)
    return d


def test_survey_form_matches_document(env):
    """แบบประเมินตามเอกสาร: ตอนที่ 1 เพศ/สถานะ/สิ่งที่ใช้งาน · ตอนที่ 2 10 ข้อตามขั้นการประชาสัมพันธ์ · ตอนที่ 3 ข้อเสนอแนะ"""
    f = client(False).get("/survey").get_json()
    assert len(f["items"]) == 10
    assert f["items"][0] == {"stage": "ดึงดูดความสนใจ", "text": "น้องทานตะวันหน้าตาน่ารัก เป็นมิตร น่าเข้าไปใช้งาน"}
    assert f["items"][9]["stage"] == "ภาพรวม"
    assert [g["name"] for g in f["genders"]] == ["ชาย", "หญิง", "ไม่ระบุ"]
    assert {r["key"] for r in f["roles"]} == {"student", "parent", "staff", "guest"}
    assert [u["name"] for u in f["usages"]] == ["ถามด้วยเสียง", "พิมพ์/กดปุ่มคำถาม", "ดูการต้อนรับ/ท่าทางของหุ่นยนต์"]


def test_survey_validation(env):
    c = client(False)
    for bad in (_resp(gender=""), _resp(role="alien"), _resp(usage=[]), _resp(usage=["fly"]),
                _resp(scores=[5] * 9), _resp(scores=[5] * 9 + [6]), _resp(scores=["5"] * 10)):
        assert c.post("/survey", json=bad).status_code == 400, bad
    assert c.post("/survey", json=_resp()).status_code == 200


def test_survey_summary_mean_sd_pass_csv(env):
    c = client(False)
    c.post("/survey", json=_resp(scores=[5] * 10, usage=["voice", "type"], liked="หน้าน่ารัก"))
    c.post("/survey", json=_resp(gender="male", role="parent", scores=[4] * 10, usage=["greet"], improve="  ตอบ   เร็วขึ้น "))
    s = c.get("/survey.json").get_json()
    assert s["total"] == 2
    assert s["items"][0]["average"] == 4.5 and s["items"][0]["sd"] == 0.71 and s["items"][0]["stage"] == "ดึงดูดความสนใจ"
    assert s["average"] == 4.5 and s["level"] == "มาก" and s["pass"] is True and s["pass_cut"] == 3.51
    assert {x["key"]: x["count"] for x in s["genders"]} == {"male": 1, "female": 1, "none": 0}
    assert {x["key"]: x["count"] for x in s["usages"]} == {"voice": 1, "type": 1, "greet": 1}
    assert s["comments"][0]["improve"] == "ตอบ เร็วขึ้น" and s["comments"][1]["liked"] == "หน้าน่ารัก"
    csv = c.get("/survey.csv").get_data(as_text=True)
    assert csv.startswith("﻿") and "ผู้ปกครอง" in csv and "ถามด้วยเสียง / พิมพ์/กดปุ่มคำถาม" in csv
    assert "หน้าน่ารัก" in csv and "สิ่งที่ควรปรับปรุง" in csv and csv.count(chr(10)) == 3


def test_survey_fails_below_cut(env):
    client(False).post("/survey", json=_resp(scores=[3] * 10))
    s = client(False).get("/survey.json").get_json()
    assert s["average"] == 3.0 and s["pass"] is False and s["level"] == "ปานกลาง"


def test_osk_types_into_survey_fields():
    """คีย์บอร์ดบนจอใช้พิมพ์ช่องข้อเสนอแนะ (data-osk) ได้"""
    js = client(False).get("/static/osk.js").get_data(as_text=True)
    assert '"#q, [data-osk]"' in js and "input === main" in js
    ex = client(False).get("/static/extras.js").get_data(as_text=True)
    assert ex.count("data-osk") >= 2 and "liked" in ex and "improve" in ex


def test_survey_level_cutoffs():
    from stats import survey_level
    assert [survey_level(v) for v in (5, 4.51, 4.5, 3.51, 3.5, 2.51, 2.5, 1.51, 1.5, None)] == [
        "มากที่สุด", "มากที่สุด", "มาก", "มาก", "ปานกลาง", "ปานกลาง", "น้อย", "น้อย", "น้อยที่สุด", ""]


# ---------- หน้าจอ ----------
def test_five_blocks_after_overview():
    """ข้างหัวข้อข่าวเด่น: คู่มือ · ภาพรวมการทำงาน · ปฏิทินแนะแนว · คลังภาพกิจกรรม · แบบประเมิน"""
    html = client(False).get("/screen").get_data(as_text=True)
    head = html[html.index("ข่าวเด่นวันนี้"):html.index('id="newsGrid"')]
    assert head.count('class="guide-chip"') == 5
    order = [head.index(x) for x in ("user-guide.jpg", "overview.jpg", 'data-action="showCalendar"',
                                     'data-action="showGallery"', 'data-action="showSurvey"')]
    assert order == sorted(order)
    assert html.index("/static/screen.js") < html.index("/static/extras.js")
    js = client(False).get("/static/extras.js").get_data(as_text=True)
    for needle in ('"/guidance"', '"/gallery"', '"/survey"', "window.Extras", "showCalendar", "showGallery", "showSurvey"):
        assert needle in js, needle
    assert "Extras[action]" in client(False).get("/static/screen.js").get_data(as_text=True)


def test_highlight_chip_became_awards():
    html = client(False).get("/screen").get_data(as_text=True)
    assert "จุดเด่นวิทยาลัย" not in html and "วิทยาลัยมีจุดเด่นอะไรบ้าง" not in html
    assert html.count('data-q="วิทยาลัยมีผลงานและรางวัลอะไรบ้าง"') == 2   # ชิปล่าง + เมนูทั้งหมด
    assert "ผลงานรางวัล" in html


def test_admin_page_has_new_tabs():
    html = client(False).get("/stats").get_data(as_text=True)
    for v in ("guidance", "gallery", "survey"):
        assert f'data-view="{v}"' in html and f'id="view-{v}"' in html
    assert 'href="/survey.csv"' in html and 'multiple' in html


def test_guide_pictures_have_no_3d_button():
    """คู่มือการใช้งาน / ภาพรวมการทำงาน ขึ้นรูปทางซ้ายแต่ไม่มีปุ่มเยี่ยมชม 3D (มีเฉพาะแผนผัง)"""
    js = client(False).get("/static/screen.js").get_data(as_text=True)
    line = next(l for l in js.splitlines() if 'action === "showGuide"' in l)
    assert "noTour: true" in line
    show = js[js.index("function showPictures"):]
    assert 'pics[0].tour === false ? ""' in show[:show.index("\n}")]


def test_hiding_keyboard_does_not_press_mic():
    """กด ⌄ ซ่อนคีย์บอร์ด / ส่ง แล้วนิ้วไม่ไปโดนปุ่มไมค์ที่โผล่ขึ้นมาใต้นิ้ว"""
    js = client(False).get("/static/osk.js").get_data(as_text=True)
    assert 'act === "hide") { swallowTap();' in js and 'act === "enter") { swallowTap();' in js
    assert "stopImmediatePropagation" in js
