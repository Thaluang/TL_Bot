from tts_text import thai_pauses


def test_space_between_long_phrases_kept_as_breath():
    assert thai_pauses("งานทะเบียนอยู่ชั้นหนึ่ง อาคารอำนวยการ") == "งานทะเบียนอยู่ชั้นหนึ่ง อาคารอำนวยการ"


def test_short_words_split_by_spaces_flow_together():
    assert thai_pauses("ห้อง สมุด อยู่ ไหน") == "ห้องสมุดอยู่ไหน"
    assert thai_pauses("เปิด จันทร์ ถึง ศุกร์ ตั้งแต่แปดโมงเช้า") == "เปิดจันทร์ถึงศุกร์ ตั้งแต่แปดโมงเช้า"


def test_sentence_end_particle_always_gets_a_short_breath():
    assert thai_pauses("สวัสดีครับ ยินดีต้อนรับครับ") == "สวัสดีครับ ยินดีต้อนรับครับ"
    assert thai_pauses("ได้ครับ ไป") == "ได้ครับ ไป"
    assert thai_pauses("ได้เลยค่ะ ไปกันเลย") == "ได้เลยค่ะ ไปกันเลย"


def test_new_line_becomes_short_breath_not_full_stop():
    assert thai_pauses("งานทะเบียนอยู่อาคาร 1\nเปิดทุกวันครับ") == "งานทะเบียนอยู่อาคาร 1 เปิดทุกวันครับ"
    assert thai_pauses("ได้เลยครับ!\nไปกันเลย") == "ได้เลยครับ! ไปกันเลย"


def test_mai_yamok_stays_with_word():
    assert thai_pauses("กิจกรรมต่าง ๆ มากมาย") == "กิจกรรมต่างๆ มากมาย"


def test_numbers_and_english_untouched():
    assert thai_pauses("โทร 036-281-295 ต่อ 112") == "โทร 036-281-295 ต่อ 112"
    assert thai_pauses("แผนก IT Support ครับ") == "แผนก IT Support ครับ"


def test_empty_and_blank_lines():
    assert thai_pauses("") == ""
    assert thai_pauses("\n  \nครับ\n\n") == "ครับ"


def test_bot_name_read_in_thai_without_switching_language():
    assert thai_pauses("ผมชื่อน้องทานตะวัน-Bot ผู้ช่วยตอบคำถาม") == "ผมชื่อน้องทานตะวันบอท ผู้ช่วยตอบคำถาม"
    assert thai_pauses("น้องทานตะวัน Bot") == "น้องทานตะวันบอท"


def test_greeting_flows():
    assert (thai_pauses("สวัสดีครับผมชื่อน้องทานตะวันบอท มีอะไรให้ช่วยไหมครับ")
            == "สวัสดีครับผมชื่อน้องทานตะวันบอท มีอะไรให้ช่วยไหมครับ")


def test_multiple_spaces_and_tabs_collapse():
    assert thai_pauses("ห้องสมุด   อยู่\tชั้นสอง") == "ห้องสมุดอยู่ชั้นสอง"
