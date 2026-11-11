"""
เทสต์ตัวจับคู่รูปสถานที่ + โครงเมนู — ใช้ข้อมูลจำลอง ไม่พึ่งรูปจริง
รันจากโฟลเดอร์ robot/:  & $py -m pytest web/test_places.py -v
"""
import pytest

from places import photos_for, menu_tree, map_link

DATA = {
    "ท่องเที่ยวสระบุรี": {
        "น้ำตก": [
            {"ชื่อ": "น้ำตกเจ็ดสาวน้อย", "อำเภอ": "มวกเหล็ก", "จุดเด่น": "น้ำตก 7 ชั้น",
             "รูป": "jedsaonoi.jpg", "ชื่ออังกฤษ": "Jet Sao Noi Waterfall", "ชื่อเรียกอื่น": ["เจ็ดสาวน้อย"]},
            {"ชื่อ": "น้ำตกมวกเหล็ก", "อำเภอ": "มวกเหล็ก", "จุดเด่น": "เย็นสบาย", "รูป": "muaklek.jpg"},
        ],
        "วัดและสถานที่ศักดิ์สิทธิ์": [
            {"ชื่อ": "วัดพระพุทธบาท", "อำเภอ": "พระพุทธบาท", "จุดเด่น": "รอยพระพุทธบาท", "รูป": "buddhabat.jpg"},
        ],
        "ธรรมชาติและสวน": [
            {"ชื่อ": "ไร่กุสุมา", "อำเภอ": "เมืองสระบุรี", "จุดเด่น": "ไร่", "รูป": "kusuma.jpg"},
        ],
        "ตลาดและแหล่งช้อป": [
            {"ชื่อ": "ตลาดท่าน้ำแก่งคอย", "อำเภอ": "แก่งคอย", "จุดเด่น": "ตลาดริมน้ำ", "รูป": "kaengkhoi.jpg"},
        ],
        "ใกล้วิทยาลัย_อำเภอบ้านหมอ": [
            {"ชื่อ": "ตลาดท่าน้ำแก่งคอย", "อำเภอ": "แก่งคอย", "จุดเด่น": "ตลาดริมน้ำ", "รูป": "kaengkhoi.jpg"},
        ],
    },
    "OTOP_สระบุรี": {
        "อาหารและขนม": [
            {"ชื่อ": "หมูทุบไร้มัน", "อำเภอ": "เมืองสระบุรี", "จุดเด่น": "หมูทุบ"},
        ],
    },
}


@pytest.fixture
def DIR(tmp_path):
    # มีไฟล์จริงทุกรูป ยกเว้น kusuma.jpg (ทดสอบกรณี JSON อ้างรูปที่ไม่มีไฟล์)
    for name in ("jedsaonoi.jpg", "muaklek.jpg", "buddhabat.jpg", "kaengkhoi.jpg"):
        (tmp_path / name).write_bytes(b"")
    return tmp_path


def test_name_in_question_gives_that_photo_only(DIR):
    p = photos_for("น้ำตกเจ็ดสาวน้อยไปยังไง", "มีน้ำตกมวกเหล็กด้วยนะ", DATA, places_dir=DIR)
    assert [x["src"] for x in p] == ["/static/places/jedsaonoi.jpg"]


def test_alias_matches(DIR):
    assert photos_for("เจ็ดสาวน้อยสวยไหม", "", DATA, places_dir=DIR)[0]["name"] == "น้ำตกเจ็ดสาวน้อย"


def test_broad_question_uses_answer_order_max_three(DIR):
    ans = "แนะนำ วัดพระพุทธบาท ตลาดท่าน้ำแก่งคอย น้ำตกมวกเหล็ก และ น้ำตกเจ็ดสาวน้อย"
    p = photos_for("สระบุรีมีที่เที่ยวที่ไหนบ้าง", ans, DATA, places_dir=DIR)
    assert [x["name"] for x in p] == ["วัดพระพุทธบาท", "ตลาดท่าน้ำแก่งคอย", "น้ำตกมวกเหล็ก"]


def test_no_names_gives_empty(DIR):
    assert photos_for("เปิดสอนสาขาอะไรบ้าง", "มีช่างยนต์ ช่างไฟฟ้า", DATA, places_dir=DIR) == []


def test_missing_file_not_returned(DIR):
    assert photos_for("ไร่กุสุมาเป็นยังไง", "", DATA, places_dir=DIR) == []


def test_district_name_does_not_match_place(DIR):
    assert photos_for("อำเภอมวกเหล็กมีอะไรบ้าง", "", DATA, places_dir=DIR) == []
    assert photos_for("อำเภอพระพุทธบาทอยู่ไหน", "", DATA, places_dir=DIR) == []


def test_duplicate_entry_appears_once(DIR):
    p = photos_for("ตลาดท่าน้ำแก่งคอย ตลาดท่าน้ำแก่งคอย", "", DATA, places_dir=DIR)
    assert len(p) == 1


def test_english_answer_case_insensitive_and_caption_lang(DIR):
    p = photos_for("Where to visit?", "Try JET SAO NOI waterfall!", DATA, lang="en", places_dir=DIR)
    assert p[0]["name"] == "Jet Sao Noi Waterfall"
    assert photos_for("น้ำตกเจ็ดสาวน้อย", "", DATA, lang="th", places_dir=DIR)[0]["caption"] == "มวกเหล็ก"


def test_menu_tree_shape(DIR):
    m = menu_tree(DATA, places_dir=DIR)
    assert set(m) == {"trips", "souvenirs", "stay", "food", "cafe", "market"}
    assert [c["key"] for c in m["trips"]["categories"]] == list(DATA["ท่องเที่ยวสระบุรี"])
    item = m["trips"]["categories"][0]["items"][0]
    assert item["name"] == {"th": "น้ำตกเจ็ดสาวน้อย", "en": "Jet Sao Noi Waterfall"}
    assert item["photo"] == "/static/places/jedsaonoi.jpg"
    otop = m["souvenirs"]["categories"][0]["items"][0]
    assert otop["photo"] is None and otop["name"]["en"] == "หมูทุบไร้มัน"   # ไม่มีชื่ออังกฤษ → ไทย


def test_menu_tree_empty_data(DIR):
    assert menu_tree({}, places_dir=DIR) == {
        "trips": {"label": {"th": "ที่เที่ยวสระบุรี", "en": "Places to visit"}, "categories": []},
        "souvenirs": {"label": {"th": "ของฝากสระบุรี", "en": "Souvenirs"}, "categories": []},
        "stay": {"label": {"th": "ที่พักใกล้วิทยาลัย", "en": "Places to stay"}, "categories": []},
        "food": {"label": {"th": "ร้านอาหารใกล้วิทยาลัย", "en": "Places to eat"}, "categories": []},
        "cafe": {"label": {"th": "คาเฟ่แนะนำ", "en": "Cafés"}, "categories": []},
        "market": {"label": {"th": "ตลาดใกล้วิทยาลัย", "en": "Markets"}, "categories": []}}


def test_refusal_answer_shows_no_photo_of_other_place(DIR):
    # ถามที่ที่ไม่มีในข้อมูล → AI ปฏิเสธแล้วแนะนำที่อื่น: ห้ามขึ้นรูปที่อื่นใต้คำถามนั้น
    th = "ขออภัย ยังไม่มีข้อมูลในส่วนนี้ค่ะ แต่สระบุรีมีน้ำตกเจ็ดสาวน้อยนะคะ"
    en = "Sorry, I don't have that information yet. Saraburi has Jet Sao Noi Waterfall though."
    assert photos_for("น้ำตกเอราวัณอยู่ที่ไหน", th, DATA, places_dir=DIR) == []
    assert photos_for("Where is Erawan waterfall?", en, DATA, lang="en", places_dir=DIR) == []


# ---- QR นำทาง (Google Maps) + ข้อมูลสำหรับเสียงพูด ----
def test_trip_items_have_google_maps_link(DIR):
    from urllib.parse import unquote_plus
    m = menu_tree(DATA, places_dir=DIR)
    temple = m["trips"]["categories"][1]["items"][0]
    assert temple["map"].startswith("https://www.google.com/maps/search/?api=1&query=")
    q = unquote_plus(temple["map"].split("query=", 1)[1])
    assert "วัดพระพุทธบาท" in q and "พระพุทธบาท" in q and "สระบุรี" in q


def test_trip_map_uses_coordinates_when_given(DIR):
    data = {"ท่องเที่ยวสระบุรี": {"วัด": [{"ชื่อ": "วัดทดสอบ", "อำเภอ": "เสาไห้", "พิกัด": "14.5401, 100.8623"}]}}
    item = menu_tree(data, places_dir=DIR)["trips"]["categories"][0]["items"][0]
    assert item["map"] == "https://www.google.com/maps/search/?api=1&query=14.5401%2C100.8623"


def test_trip_full_name_and_distance_for_speech(DIR):
    data = {"ท่องเที่ยวสระบุรี": {"น้ำตก": [{"ชื่อ": "น้ำตกสามหลั่น", "ชื่อเต็ม": "อุทยานแห่งชาติน้ำตกสามหลั่น",
                                          "อำเภอ": "เมืองสระบุรี", "ระยะทางจากวิทยาลัย": "ประมาณ 40 กม."}]}}
    item = menu_tree(data, places_dir=DIR)["trips"]["categories"][0]["items"][0]
    assert "อุทยานแห่งชาติน้ำตกสามหลั่น" in item["map"].replace("+", " ") or "%" in item["map"]
    assert item["distance"] == "ประมาณ 40 กม."


def test_stay_has_map_and_distance(DIR):
    data = {"ที่พักใกล้วิทยาลัย": {"ใกล้วิทยาลัย": [{"ชื่อ": "ที่พักทดสอบ", "ระยะทางจากวิทยาลัย": "2.6 กิโลเมตร"}]}}
    cat = menu_tree(data, places_dir=DIR)["stay"]["categories"][0]
    assert cat["icon"] == "🏨"
    assert cat["items"][0]["distance"] == "2.6 กิโลเมตร" and cat["items"][0]["map"].startswith("https://")


def test_food_cafe_market_have_map_and_contact_info(DIR):
    """ร้านอาหาร/คาเฟ่/ตลาด เป็นสถานที่จริง: QR นำทาง + ระยะทาง และส่งที่อยู่ โทร เวลาเปิด ไปให้การ์ด"""
    data = {
        "ร้านอาหารใกล้วิทยาลัย": {"ร้านอาหาร": [{"ชื่อ": "ร้านทดสอบ", "ที่อยู่": "111 หมู่ 3 ต.บ้านครัว",
                                              "โทร": "081-851-8848", "เวลาเปิด": "08:00–20:30 น."}]},
        "คาเฟ่แนะนำ": {"คาเฟ่": [{"ชื่อ": "คาเฟ่ทดสอบ", "ระยะทางจากวิทยาลัย": "350 เมตร"}]},
        "ตลาดใกล้วิทยาลัย": {"ตลาด": [{"ชื่อ": "ตลาดทดสอบ"}]},
    }
    m = menu_tree(data, places_dir=DIR)
    icons = {k: m[k]["categories"][0]["icon"] for k in ("food", "cafe", "market")}
    assert icons == {"food": "🍜", "cafe": "☕", "market": "🛒"}
    food = m["food"]["categories"][0]["items"][0]
    assert food["map"].startswith("https://")
    assert (food["address"], food["phone"], food["hours"]) == ("111 หมู่ 3 ต.บ้านครัว", "081-851-8848", "08:00–20:30 น.")
    cafe = m["cafe"]["categories"][0]["items"][0]
    assert cafe["distance"] == "350 เมตร" and "phone" not in cafe   # ไม่มีข้อมูล = ไม่ส่งช่องนั้น


def test_souvenirs_have_no_map(DIR):
    m = menu_tree(DATA, places_dir=DIR)
    assert "map" not in m["souvenirs"]["categories"][0]["items"][0]


def test_place_card_speaks_and_shows_map_qr():
    from test_server import make_client
    js = make_client().get("/static/screen.js").get_data(as_text=True).replace(chr(13), "")
    card = js[js.index("const it = c.items[j];"):]
    card = card[:card.index("return true;")]
    assert "it.map" in card and "qrSvg(it.map)" in card       # QR เปิด Google Maps
    assert "speakPlace(" in card                               # หุ่นพูดชื่อ + จุดเด่น
    assert "function speakPlace" in js


def test_map_link_other_province():
    """ที่เที่ยวนอกสระบุรี (เช่น อยุธยา) ใส่ "จังหวัด" → ค้นแผนที่ด้วยจังหวัดนั้น ไม่ต่อท้ายสระบุรี"""
    url = map_link({"ชื่อ": "วัดตะโก", "อำเภอ": "ท่าเรือ", "จังหวัด": "พระนครศรีอยุธยา"})
    from urllib.parse import unquote_plus
    q = unquote_plus(url)
    assert "พระนครศรีอยุธยา" in q and "สระบุรี" not in q and "อำเภอท่าเรือ" in q
    assert "สระบุรี" in unquote_plus(map_link({"ชื่อ": "น้ำตก"}))   # ไม่ใส่ = สระบุรีเหมือนเดิม
