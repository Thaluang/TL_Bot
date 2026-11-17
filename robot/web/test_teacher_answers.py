"""คำตอบที่ได้ 1–2 ดาว → ครูเพิ่มคำตอบที่ถูกในหน้า /stats → หุ่นใช้ตอบรอบหน้า + ดาวน์โหลดเป็นไฟล์ Word"""
from datetime import datetime

import pytest

import server
from content import TeacherAnswerStore
from news import NewsError
from stats import Stats


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "stats", Stats(tmp_path / "stats.db"))
    monkeypatch.setattr(server, "teacher_answers", TeacherAnswerStore(tmp_path))
    monkeypatch.setattr(server.config, "ADMIN_PASSWORD", "ครู1234")
    monkeypatch.setattr(server, "_now", lambda: datetime(2026, 11, 17, 10, 0))
    server._admin_tokens.clear()
    server.app.config["TESTING"] = True
    return tmp_path


def client(logged=True):
    c = server.app.test_client()
    if logged:
        assert c.post("/admin/login", json={"password": "ครู1234"}).status_code == 200
    return c


# ---------- ที่เก็บ ----------
def test_store_validates_and_survives_restart(tmp_path):
    s = TeacherAnswerStore(tmp_path / "x")
    with pytest.raises(NewsError):
        s.add({"question": "หอพักมีไหม", "answer": "  "})
    with pytest.raises(NewsError):
        s.add({"question": "", "answer": "มี"})
    a = s.add({"question": "หอพักมีไหม", "answer": "ไม่มีหอพักในวิทยาลัยครับ"})
    assert TeacherAnswerStore(tmp_path / "x").all() == s.all() == [a]


def test_same_question_replaces_old_answer(tmp_path):
    """ถามเหมือนกัน (ต่างแค่ ครับ/ช่องว่าง/?) = ข้อเดียวกัน — เพิ่มซ้ำคือแก้คำตอบเดิม ไม่ใช่เพิ่มอีกข้อ"""
    s = TeacherAnswerStore(tmp_path)
    first = s.add({"question": "หอพักมีไหม", "answer": "เก่า"})
    again = s.add({"question": "หอพัก มีไหมครับ?", "answer": "ใหม่"})
    assert again["id"] == first["id"] and [d["answer"] for d in s.all()] == ["ใหม่"]
    assert s.has("หอพักมีไหมคะ") and not s.has("ค่าเทอมเท่าไหร่")


def test_ai_text_lists_answers(tmp_path):
    s = TeacherAnswerStore(tmp_path)
    assert s.ai_text() == ""
    s.add({"question": "หอพักมีไหม", "answer": "ไม่มีหอพักในวิทยาลัยครับ"})
    text = s.ai_text()
    assert "หอพักมีไหม" in text and "ไม่มีหอพักในวิทยาลัยครับ" in text and "ครู" in text


# ---------- หน้าเว็บ/เซิร์ฟเวอร์ ----------
def test_admin_crud_needs_login():
    assert client(False).post("/admin/answers", json={"question": "q", "answer": "a"}).status_code == 401
    assert client(False).get("/admin/answers").status_code == 401
    c = client()
    r = c.post("/admin/answers", json={"question": "หอพักมีไหม", "answer": "ไม่มีครับ"})
    assert r.status_code == 201
    aid = r.get_json()["id"]
    assert c.post("/admin/answers", json={"question": "x", "answer": ""}).status_code == 400
    assert c.post(f"/admin/answers/{aid}", json={"answer": "มีหอพักชาย 1 หลัง"}).get_json()["answer"] == "มีหอพักชาย 1 หลัง"
    assert [d["question"] for d in c.get("/admin/answers").get_json()["items"]] == ["หอพักมีไหม"]
    assert c.delete(f"/admin/answers/{aid}").status_code == 200
    assert c.delete(f"/admin/answers/{aid}").status_code == 404


def test_robot_uses_teacher_answers():
    server.teacher_answers.add({"question": "หอพักมีไหม", "answer": "ไม่มีหอพักในวิทยาลัยครับ"})
    assert "ไม่มีหอพักในวิทยาลัยครับ" in server.ai.extra_context()


def test_answered_questions_leave_low_list():
    server.stats.add_rating(1, "หอพักมีไหม", "th")
    server.stats.add_rating(2, "หอพักมีไหม", "th")
    server.stats.add_rating(1, "ค่าเทอมเท่าไหร่", "th")
    low = client(False).get("/stats.json").get_json()["low"]
    assert [x["question"] for x in low] == ["ค่าเทอมเท่าไหร่", "หอพักมีไหม"]
    assert low[1]["count"] == 2 and low[1]["stars"] == 1          # ข้อเดียวกันรวมเป็นแถวเดียว
    server.teacher_answers.add({"question": "หอพักมีไหมครับ", "answer": "ไม่มีครับ"})
    d = client(False).get("/stats.json").get_json()
    assert [x["question"] for x in d["low"]] == ["ค่าเทอมเท่าไหร่"] and d["low_answered"] == 1


def test_download_word_file():
    server.stats.add_rating(1, "หอพักมีไหม", "th")
    server.stats.add_rating(2, "ค่าเทอม <เท่าไหร่>", "th")
    server.stats.add_rating(5, "ดีมาก", "th")
    server.teacher_answers.add({"question": "หอพักมีไหม", "answer": "ไม่มีหอพักครับ"})
    r = client(False).get("/low_ratings.doc")
    assert r.status_code == 200 and "msword" in r.mimetype
    assert "attachment" in r.headers["Content-Disposition"]
    html = r.get_data(as_text=True)
    assert "หอพักมีไหม" in html and "ไม่มีหอพักครับ" in html          # ข้อที่ครูตอบแล้วก็อยู่ในไฟล์ พร้อมคำตอบ
    assert "ค่าเทอม &lt;เท่าไหร่&gt;" in html and "<เท่าไหร่>" not in html
    assert "ดีมาก" not in html


def test_stats_page_has_controls():
    html = client(False).get("/stats").get_data(as_text=True)
    assert 'href="/low_ratings.doc"' in html and 'id="taList"' in html and "/admin/answers" in html
