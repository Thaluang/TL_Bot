"""รูป ผอ.สอจ.สระบุรี — ถาม/ตอบถึงใคร ขึ้นรูปท่านนั้นทางซ้าย"""
from pathlib import Path

import directors

STATIC = Path(__file__).resolve().parent / "static"


def names(photos):
    return [p["name"] for p in photos]


def test_every_director_has_photo_file():
    assert len(directors.DIRECTORS) == 7
    for d in directors.DIRECTORS:
        assert (STATIC / d["photo"].removeprefix("/static/")).is_file(), d["photo"]


def test_question_names_director():
    got = directors.photos_for("ขอประวัติ ผอ.เจนวิทย์ หน่อย", "")
    assert names(got) == ["นายเจนวิทย์ ตั้งเจริญวรคุณ"]
    assert got[0]["person"] is True and "วิทยาลัยเทคนิคสระบุรี" in got[0]["caption"]


def test_answer_names_director():
    """ถามตามวิทยาลัย ไม่มีชื่อในคำถาม → ใช้ชื่อในคำตอบ"""
    got = directors.photos_for("ผอ.วิทยาลัยเทคนิคมวกเหล็กชื่ออะไร", "ผู้อำนวยการคือ นางปราณี ต่อมดวงแก้ว ครับ")
    assert names(got) == ["นางปราณี ต่อมดวงแก้ว"]


def test_question_wins_over_answer():
    got = directors.photos_for("ประวัติ นายณรงค์ องศากิจบริบูรณ์",
                               "ท่านเคยทำงานร่วมกับ นายเจนวิทย์ ตั้งเจริญวรคุณ")
    assert names(got) == ["นายณรงค์ องศากิจบริบูรณ์"]


def test_many_directors_in_order():
    ans = "นายเฉลิมชนม์ เวทสรากุล ... นางสาวภัทรวรรณ ตันสกุล ... ดร.ทิฐินันท์ ทุมมา"
    assert names(directors.photos_for("ผอ.ในสระบุรีมีใครบ้าง", ans)) == [
        "นายเฉลิมชนม์ เวทสรากุล", "นางสาวภัทรวรรณ ตันสกุล", "ดร.ทิฐินันท์ ทุมมา"]


def test_unrelated_text_no_photos():
    assert directors.photos_for("สมัครเรียนยังไง", "สมัครออนไลน์ได้เลยครับ") == []


def test_short_name_in_question():
    """ถามแค่ชื่อเล่นแบบชื่อต้น ไม่มีคำนำหน้า/นามสกุล ก็เจอ"""
    assert names(directors.photos_for("ทิฐินันท์ เป็นใคร", "")) == ["ดร.ทิฐินันท์ ทุมมา"]


def test_menu_list_has_questions():
    items = directors.menu_list()
    assert len(items) == 7 and items[0]["name"]["th"] == "นายเจนวิทย์ ตั้งเจริญวรคุณ"   # ผอ.สอจ. ขึ้นก่อน
    assert items[1]["name"]["th"] == "นายเฉลิมชนม์ เวทสรากุล"                          # ผอ.วิทยาลัยเราตามมา
    for it in items:
        assert it["photo"].startswith("/static/directors/") and it["q"]["th"] and it["q"]["en"]
        assert it["name"]["th"] in it["q"]["th"]
