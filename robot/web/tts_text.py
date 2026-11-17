"""
เตรียมข้อความภาษาไทยก่อนส่งให้เสียงพูด (edge-tts Niwat) — ใช้กับทุกเสียงที่หุ่นพูด (คำตอบ ทักทาย ประกาศ ข่าว)
เป้าหมาย: พูดไหลลื่นต่อเนื่องเหมือนคนคุย ไม่หยุดเป็นห้วง ๆ
- เว้นวรรคเหมือนคนพูด: คนหยุดหายใจตรงจบวลี/ประโยค ไม่ได้หยุดทุกคำ
  ช่องว่างระหว่างวลียาว ๆ → คงไว้ (หายใจสั้น ๆ)
  ช่องว่างที่แยกคำสั้น ๆ ออกมา ("ห้องสมุด อยู่ ชั้นสอง") → ต่อติดกัน ไม่หยุดกลางวลี
- จบประโยค (หลัง ครับ/ค่ะ/คะ/นะ… หรือขึ้นบรรทัดใหม่) → เว้นวรรคเดียว = หายใจสั้น ๆ แล้วพูดต่อ
  (ไม่ใส่ "." แล้ว — จุดทำให้เสียงหยุดนานเหมือนจบเรื่อง ฟังกระตุก)
- "Bot" ที่ติดคำไทย → "บอท" (เสียงไม่ต้องสลับไปอ่านภาษาอังกฤษ ไม่สะดุด)
- "ๆ" ติดกับคำข้างหน้า ("ต่าง ๆ" → "ต่างๆ") และเว้นวรรคหลัง ๆ ไว้ (ให้เสียงรู้ว่าซ้ำคำไหน)
ภาษาอังกฤษ ตัวเลข เบอร์โทร ไม่แตะ
"""
import re

_THAI = "฀-๿"
_SPACE_BEFORE_MAI_YAMOK = re.compile(r"\s+ๆ")
# "น้องทานตะวัน-Bot" → "น้องทานตะวันบอท"
_BOT = re.compile(rf"(?<=[{_THAI}])\s*-?\s*Bot\b", re.IGNORECASE)
# คำลงท้ายประโยค ตามด้วยช่องว่างแล้วขึ้นคำไทยใหม่ = จบประโยค (\x00 = จุดหายใจ กันไม่ให้โดนต่อติด)
_SENTENCE_END = re.compile(rf"(ครับ|ค่ะ|คะ|นะ|จ้า|จ้ะ)\s+(?=[{_THAI}])")
_THAI_CHAR = re.compile(rf"[{_THAI}]")
PHRASE_MIN = 8   # วลีสั้นกว่านี้ (ตัวอักษร) ยังไม่หยุดหายใจ พูดต่อกับคำถัดไปเลย


def _human_gaps(line: str) -> str:
    """ต่อคำสั้น ๆ เข้าวลี — เว้นวรรคไว้เฉพาะระหว่างวลีที่ยาวพอจะหายใจ (และหลังคำลงท้ายประโยคเสมอ)"""
    out, phrase = "", ""
    for tok in line.split(" "):
        if not out:
            out = phrase = tok
            continue
        prev_end, nxt = out[-1], tok
        thai_join = (_THAI_CHAR.fullmatch(prev_end) and prev_end != "ๆ" and nxt and _THAI_CHAR.match(nxt[0]))
        if thai_join and (len(phrase) < PHRASE_MIN or len(nxt) < PHRASE_MIN):
            out += tok
            phrase += tok
        else:
            out += " " + tok
            phrase = tok
    return out


def thai_pauses(text: str) -> str:
    lines = []
    for line in (text or "").split("\n"):
        line = " ".join(line.split())
        if not line:
            continue
        line = _BOT.sub("บอท", line)
        line = _SPACE_BEFORE_MAI_YAMOK.sub("ๆ", line)
        # จบประโยค = หายใจเสมอ — แยกเป็นท่อน แล้วจัดวรรคในแต่ละท่อนแบบคนพูด
        parts = _SENTENCE_END.sub("\\1\x00", line).split("\x00")
        lines.append(" ".join(_human_gaps(p) for p in parts))
    # ขึ้นบรรทัด = จบประโยค → เว้นวรรคหายใจสั้น ๆ พอ
    return " ".join(lines)
