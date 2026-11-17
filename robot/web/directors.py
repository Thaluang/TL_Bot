"""
ข้อมูล ผอ.สอจ.สระบุรี — รูปผู้อำนวยการวิทยาลัยอาชีวศึกษาในจังหวัดสระบุรี 7 ท่าน
ถาม/ตอบถึงท่านไหน หน้าจอขึ้นรูปท่านนั้นทางซ้าย (ประวัติ/ผลงานให้ AI ตอบจาก college_data.json)
รูปอยู่ static/directors/ (จากไฟล์ เอกสาร/ข้อมูล ผู้บริหาร อาชีวศึกษา จังหวัดสระบุรี.docx)
"""

# ลำดับ = ลำดับในเมนู: ผอ.สอจ. ก่อน แล้ว ผอ.วิทยาลัยเรา แล้ววิทยาลัยอื่น
DIRECTORS = [
    {"name": "นายเจนวิทย์ ตั้งเจริญวรคุณ", "first": "เจนวิทย์", "photo": "/static/directors/jenwit.jpg",
     "role": "ผอ.วิทยาลัยเทคนิคสระบุรี · ปฏิบัติหน้าที่ ผอ.สอจ.สระบุรี",
     "role_en": "Director, Saraburi Technical College · Acting Director, Saraburi Provincial Vocational Education Office"},
    {"name": "นายเฉลิมชนม์ เวทสรากุล", "first": "เฉลิมชนม์", "photo": "/static/directors/chalermchon.jpg",
     "role": "ผอ.วิทยาลัยเทคนิคท่าหลวงซิเมนต์ไทยอนุสรณ์",
     "role_en": "Director, Tha Luang Cement Thai Anusorn Technical College"},
    {"name": "นางสาวภัทรวรรณ ตันสกุล", "first": "ภัทรวรรณ", "photo": "/static/directors/phattarawan.jpg",
     "role": "ผอ.วิทยาลัยอาชีวศึกษาสระบุรี", "role_en": "Director, Saraburi Vocational College"},
    {"name": "นายชัยวัฒน์ พรแสน", "first": "ชัยวัฒน์", "photo": "/static/directors/chaiwat.jpg",
     "role": "ผอ.วิทยาลัยสารพัดช่างสระบุรี", "role_en": "Director, Saraburi Polytechnic College"},
    {"name": "นายณรงค์ องศากิจบริบูรณ์", "first": "ณรงค์", "photo": "/static/directors/narong.jpg",
     "role": "ผอ.วิทยาลัยการอาชีพสระบุรี", "role_en": "Director, Saraburi Industrial and Community Education College"},
    {"name": "ดร.ทิฐินันท์ ทุมมา", "first": "ทิฐินันท์", "photo": "/static/directors/thitinan.jpg",
     "role": "ผอ.วิทยาลัยการอาชีพหนองแค", "role_en": "Director, Nong Khae Industrial and Community Education College"},
    {"name": "นางปราณี ต่อมดวงแก้ว", "first": "ปราณี", "photo": "/static/directors/pranee.jpg",
     "role": "ผอ.วิทยาลัยเทคนิคมวกเหล็ก", "role_en": "Director, Muak Lek Technical College"},
]
MAX_PHOTOS = len(DIRECTORS)


def _surname(d: dict) -> str:
    return d["name"].split()[-1]


def _find(text: str, short: bool) -> list[dict]:
    """ท่านที่ชื่อปรากฏในข้อความ เรียงตามตำแหน่งที่เจอ
    คำถาม (short=True): ชื่อต้นอย่างเดียวก็นับ — คนถามมักพิมพ์สั้น ๆ
    คำตอบ (short=False): ต้องมีชื่อ+นามสกุล — ชื่อต้นสั้น ๆ อย่าง 'ณรงค์' อาจเป็นคนอื่นในรายชื่อกรรมการ"""
    hits = []
    for d in DIRECTORS:
        keys = [f"{d['first']} {_surname(d)}", f"{d['first']}{_surname(d)}"] + ([d["first"]] if short else [])
        pos = [i for i in (text.find(k) for k in keys) if i >= 0]
        if pos:
            hits.append((min(pos), d))
    return [d for _, d in sorted(hits, key=lambda h: h[0])]


def _photo(d: dict, lang: str) -> dict:
    return {"src": d["photo"], "name": d["name"], "caption": d["role_en"] if lang == "en" else d["role"], "person": True}


def photos_for(question: str, answer: str, lang: str = "th") -> list[dict]:
    """รูป ผอ. ที่จะขึ้นทางซ้าย: ชื่อในคำถามก่อน ถ้าไม่มีค่อยดูชื่อในคำตอบ"""
    found = _find(question, short=True) or _find(answer, short=False)
    return [_photo(d, lang) for d in found][:MAX_PHOTOS]


def menu_list() -> list[dict]:
    """รายชื่อในเมนู ข้อมูล ผอ.สอจ.สระบุรี — แตะท่านไหนถาม AI ประวัติท่านนั้น (คำตอบได้รูปท่านกลับมาเอง)"""
    return [{
        "name": {"th": d["name"], "en": d["name"]},
        "role": {"th": d["role"], "en": d["role_en"]},
        "photo": d["photo"],
        "q": {"th": f"ขอประวัติและผลงานของ {d['name']} {d['role'].split(' · ')[0]}",
              "en": f"Tell me about {d['name']}, {d['role_en'].split(' · ')[0]}"},
    } for d in DIRECTORS]
