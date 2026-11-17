"""
เทสต์ข้อมูลวิทยาลัย — ผู้บริหารสถานศึกษา
รันจากโฟลเดอร์ robot/:  python -m pytest test_college_data.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import load_college_data, format_all_data


def test_college_data_has_director_name():
    data = load_college_data()
    assert data["ผู้บริหารสถานศึกษา"]["ผู้อำนวยการ"]["ชื่อ"] == "นายเฉลิมชนม์ เวทสรากุล"
    assert len(data["ผู้บริหารสถานศึกษา"]["รองผู้อำนวยการ"]) == 4


def test_director_name_reaches_ai_prompt():
    result = format_all_data(load_college_data(), {})
    assert "นายเฉลิมชนม์ เวทสรากุล" in result


def test_sar_2568_included_without_internal_sections():
    from database import load_sar_text
    sar = load_sar_text()
    assert "คลังคำถาม-คำตอบ (266 ข้อ)" in sar
    assert "Fact Sheet" in sar
    # ส่วนข้อมูลภายในของเอกสารต้นฉบับไม่ส่งให้หุ่น
    assert "จุดที่ควรพัฒนาและแผนปี 2569 (ข้อมูลภายใน)" not in sar
    assert "ข้อความที่ขัดกัน" not in sar
    assert "รายงาน SAR ปีการศึกษา 2568" in format_all_data({}, {})


def test_programs_follow_sar_2568():
    progs = load_college_data()["หลักสูตรที่เปิดสอน"]
    pvc = [k for k in progs["ปวช"] if not k.startswith("_")]
    pvs = [k for k in progs["ปวส"] if not k.startswith("_")]
    assert len(pvc) == 13 and len(pvs) == 13
    assert "ยานยนต์ไฟฟ้า" in pvc and "เมคคาทรอนิกส์และหุ่นยนต์" in pvs
    assert "สาขาวิชาเครื่องมือกลและซ่อมบำรุง" not in progs["ปวช"]   # ชื่อเดิมจากเว็บไซต์


def test_presentation_document_reaches_ai_prompt():
    """ข้อมูลจากเอกสาร นำเสนอวิทยาลัย.docx — ประวัติ จุดเด่น ผลงาน ภาคีเครือข่าย บริการชุมชน"""
    data = load_college_data()
    works = [w["ผลงาน"] for w in data["ผลงานและรางวัล"]["รายการ"]]
    assert "สมาร์ทฟาร์มต้นไม้ใบด่างด้วยเทคโนโลยี IoT" in works and "ทีมเซปักตะกร้อหญิง" in works
    assert data["ภาคีเครือข่าย"]["รวมมูลค่าการสนับสนุน"].startswith("6,320,000")
    prompt = format_all_data(data, {}, sar_text="")
    for text in ("ปี พ.ศ. 2527", "โรงเรียนโรงงาน", "Fix it Center", "สมาร์ทนา", "MOU"):
        assert text in prompt


def test_phonebook_reaches_ai_prompt_without_mobile_numbers():
    """สมุดโทรศัพท์ tel69.pdf — เบอร์ภายใน + รายชื่อบุคลากร (ไม่ใส่เบอร์มือถือส่วนตัว)"""
    import re
    book = load_college_data()["สมุดโทรศัพท์และบุคลากร"]
    assert book["เบอร์ภายใน"]["112"] == "งานทะเบียน" and book["เบอร์ภายใน"]["118"] == "งานแนะแนว"
    prompt = format_all_data(load_college_data(), {}, sar_text="")
    for text in ("นายวิศรุต ไวโสภา", "งานห้องสมุด-งานเอกสารการพิมพ์", "036-281-295"):
        assert text in prompt
    assert not re.search(r"0[689]\d-?\d{3}-?\d{4}", str(book))   # ไม่มีเบอร์มือถือ


def test_saraburi_college_directors_reach_ai_prompt():
    """คำสั่ง สอจ.สระบุรี ที่ 20/2569 — ผอ.ทุกวิทยาลัยในสระบุรี + คณะกรรมการประกวดสิ่งประดิษฐ์"""
    data = load_college_data()
    directors = data["ผู้อำนวยการวิทยาลัยในจังหวัดสระบุรี"]["ผู้อำนวยการแต่ละวิทยาลัย"]
    assert list(directors)[0] == "วิทยาลัยเทคนิคท่าหลวงซิเมนต์ไทยอนุสรณ์"
    assert directors["วิทยาลัยเทคนิคท่าหลวงซิเมนต์ไทยอนุสรณ์"] == "นายเฉลิมชนม์ เวทสรากุล"
    assert directors["วิทยาลัยเทคนิคมวกเหล็ก"] == "นางปราณี ต่อมดวงแก้ว"
    assert directors["วิทยาลัยการอาชีพหนองแค"] == "นายทิฐินันท์ ทุมมา"
    committees = data["คณะกรรมการประกวดสิ่งประดิษฐ์ของคนรุ่นใหม่ 2569"]["คณะกรรมการ"]
    assert len(committees) == 21
    assert sum(len(v) for v in committees.values()) == 214
    prompt = format_all_data(data, {}, sar_text="")
    for text in ("นายเจนวิทย์ ตั้งเจริญวรคุณ", "นายพสิษฐ์ นาหว่าน", "นางสาวกาญจนา เทพนม", "อาคารอเนกประสงค์ (โดม)"):
        assert text in prompt


def test_unqualified_director_question_rule():
    """ถาม ผอ. เฉย ๆ ต้องตอบ ผอ.ท่าหลวงฯ เท่านั้น"""
    from ai import _rules
    rules = _rules("th")
    assert "โดยไม่ระบุวิทยาลัย ให้ตอบผู้อำนวยการวิทยาลัยเทคนิคท่าหลวงซิเมนต์ไทยอนุสรณ์" in rules
