"""
เตรียมข้อความภาษาไทยก่อนส่งให้เสียงพูด (edge-tts Niwat) — ใช้กับทุกเสียงที่หุ่นพูด (คำตอบ ทักทาย ประกาศ ข่าว)
เป้าหมาย: พูดต่อเนื่อง ลื่น ๆ ไม่ติดขัด แต่ยังหยุดหายใจตอนจบประโยค
- ช่องว่างทั่วไประหว่างคำไทย → คงไว้ (เสียงพูดต่อกันไป ไม่หยุด)
- จบประโยค (หลัง ครับ/ค่ะ/คะ/นะ… หรือขึ้นบรรทัดใหม่) → "." หยุดสั้น ๆ แล้วพูดต่อ
- "Bot" ที่ติดคำไทย → "บอท" (เสียงไม่ต้องสลับไปอ่านภาษาอังกฤษ ไม่สะดุด)
- "ๆ" ติดกับคำข้างหน้า ("ต่าง ๆ" → "ต่างๆ")
ภาษาอังกฤษ ตัวเลข เบอร์โทร ไม่แตะ
"""
import re

_THAI = "฀-๿"
_END = ".,!?;:…)\"'”"
_SPACE_BEFORE_MAI_YAMOK = re.compile(r"\s+ๆ")
# "น้องทานตะวัน-Bot" → "น้องทานตะวันบอท"
_BOT = re.compile(rf"(?<=[{_THAI}])\s*-?\s*Bot\b", re.IGNORECASE)
# คำลงท้ายประโยค ตามด้วยช่องว่างแล้วขึ้นคำไทยใหม่ = จบประโยค
_SENTENCE_END = re.compile(rf"(ครับ|ค่ะ|คะ|นะ|จ้า|จ้ะ)\s+(?=[{_THAI}])")


def thai_pauses(text: str) -> str:
    lines = []
    for line in (text or "").split("\n"):
        line = " ".join(line.split())
        if not line:
            continue
        line = _BOT.sub("บอท", line)
        line = _SPACE_BEFORE_MAI_YAMOK.sub("ๆ", line)
        line = _SENTENCE_END.sub(r"\1. ", line)
        lines.append(line)
    # ขึ้นบรรทัด = จบประโยค (บรรทัดสุดท้ายไม่ต้อง เสียงจบเองอยู่แล้ว)
    return " ".join([l if l[-1] in _END else l + "." for l in lines[:-1]] + lines[-1:])
