"""
เก็บสถิติการใช้หุ่นลงไฟล์ SQLite (มากับ Python ไม่ต้องลงอะไรเพิ่ม)
- คำถามทุกข้อที่มีคนถาม (ไว้ดูว่าคนสนใจเรื่องอะไร)
- ดาว 1–5 ที่คนให้หลังได้คำตอบ (ข้อที่ได้ดาวน้อย = ข้อมูลที่ควรเติม)
ไม่เก็บข้อมูลส่วนตัวของคนถาม เก็บแค่ข้อความคำถาม ภาษา และเวลา
"""
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

MAX_QUESTION_CHARS = 500

_SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY, ts TEXT NOT NULL, question TEXT NOT NULL, lang TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY, ts TEXT NOT NULL, stars INTEGER NOT NULL, question TEXT NOT NULL, lang TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS survey_responses (
    id INTEGER PRIMARY KEY, ts TEXT NOT NULL, gender TEXT NOT NULL, role TEXT NOT NULL, usage TEXT NOT NULL,
    scores TEXT NOT NULL, liked TEXT NOT NULL, improve TEXT NOT NULL
);
"""

# แบบประเมินความพึงพอใจการใช้งาน น้องทานตะวัน-Bot (ตามเอกสาร เอกสาร/แบบประเมินความพึงพอใจ...docx)
# ตอนที่ 2: 10 ข้อ เรียงตามขั้นการประชาสัมพันธ์ — มาตราส่วน 5 ระดับ 5 = มากที่สุด … 1 = น้อยที่สุด
SURVEY_ITEMS = (
    ("ดึงดูดความสนใจ", "น้องทานตะวันหน้าตาน่ารัก เป็นมิตร น่าเข้าไปใช้งาน"),
    ("ต้อนรับ", "การทักทายและท่าทาง (โบกมือ หันหน้า) เป็นธรรมชาติ ชวนให้อยากคุย"),
    ("เข้าถึงง่าย", "ใช้งานง่าย ไม่ต้องมีคนสอน (พูด พิมพ์ หรือกดปุ่ม)"),
    ("สื่อสาร", "ฟังคำถามเข้าใจ และตอบตรงคำถาม"),
    ("สื่อสาร", "ข้อมูลถูกต้อง ชัดเจน เชื่อถือได้"),
    ("สื่อสาร", "ตอบกลับรวดเร็ว ไม่ต้องรอนาน"),
    ("เข้าใจและจดจำ", "เสียง ข้อความ และภาพบนจอ ช่วยให้เข้าใจและจำข้อมูลได้"),
    ("ความปลอดภัย", "รู้สึกปลอดภัยขณะอยู่ใกล้หุ่นยนต์"),
    ("ภาพลักษณ์องค์กร", "ทำให้วิทยาลัยดูทันสมัย น่าเชื่อถือมากขึ้น"),
    ("ภาพรวม", "พึงพอใจโดยรวม และอยากแนะนำให้ผู้อื่นมาใช้"),
)
# ตอนที่ 1: ข้อมูลทั่วไป
SURVEY_GENDERS = {"male": "ชาย", "female": "หญิง", "none": "ไม่ระบุ"}
SURVEY_ROLES = {"student": "นักเรียน/นักศึกษา", "parent": "ผู้ปกครอง", "staff": "ครู/บุคลากร", "guest": "บุคคลทั่วไป"}
SURVEY_USAGES = {"voice": "ถามด้วยเสียง", "type": "พิมพ์/กดปุ่มคำถาม", "greet": "ดูการต้อนรับ/ท่าทางของหุ่นยนต์"}
SURVEY_TEXT_MAX = 300      # ตอนที่ 3: ข้อเสนอแนะ (ไม่บังคับ)
SURVEY_PASS = 3.51         # เกณฑ์ผ่าน: ภาพรวมระดับมากขึ้นไป


def _mean_sd(values):
    """ค่าเฉลี่ย + ส่วนเบี่ยงเบนมาตรฐานแบบกลุ่มตัวอย่าง (n-1) — ปัดทศนิยม 2 ตำแหน่ง"""
    n = len(values)
    if not n:
        return None, None
    m = sum(values) / n
    sd = (sum((v - m) ** 2 for v in values) / (n - 1)) ** 0.5 if n > 1 else 0.0
    return round(m, 2), round(sd, 2)


def survey_level(avg) -> str:
    """แปลผลค่าเฉลี่ยตามเกณฑ์ 5 ระดับที่ใช้กันทั่วไป"""
    if avg is None:
        return ""
    for cut, name in ((4.51, "มากที่สุด"), (3.51, "มาก"), (2.51, "ปานกลาง"), (1.51, "น้อย")):
        if avg >= cut:
            return name
    return "น้อยที่สุด"


def _clean(q) -> str:
    return " ".join(str(q or "").split())[:MAX_QUESTION_CHARS]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Stats:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()   # Flask เปิดหลายเธรด — เขียนทีละคน
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def _db(self):
        return self._conn

    def log_question(self, question, lang="th"):
        q = _clean(question)
        if not q:
            return
        with self._lock:
            self._conn.execute("INSERT INTO questions(ts, question, lang) VALUES (?, ?, ?)", (_now(), q, lang))
            self._conn.commit()

    def add_rating(self, stars, question, lang="th"):
        if type(stars) is not int or not 1 <= stars <= 5:
            raise ValueError("stars ต้องเป็นจำนวนเต็ม 1–5")
        with self._lock:
            self._conn.execute("INSERT INTO ratings(ts, stars, question, lang) VALUES (?, ?, ?, ?)",
                               (_now(), stars, _clean(question), lang))
            self._conn.commit()

    def add_survey(self, data: dict):
        data = data if isinstance(data, dict) else {}
        gender, role, usage, scores = data.get("gender"), data.get("role"), data.get("usage"), data.get("scores")
        if gender not in SURVEY_GENDERS:
            raise ValueError("เลือกเพศก่อน")
        if role not in SURVEY_ROLES:
            raise ValueError("เลือกสถานะผู้ตอบก่อน")
        if not isinstance(usage, list) or not usage or any(u not in SURVEY_USAGES for u in usage):
            raise ValueError("เลือกสิ่งที่ใช้งานอย่างน้อย 1 ข้อ")
        if (not isinstance(scores, list) or len(scores) != len(SURVEY_ITEMS)
                or any(type(s) is not int or not 1 <= s <= 5 for s in scores)):
            raise ValueError(f"ต้องให้คะแนน 1–5 ครบ {len(SURVEY_ITEMS)} ข้อ")
        text = lambda k: " ".join(str(data.get(k) or "").split())[:SURVEY_TEXT_MAX]   # noqa: E731
        usage = [u for u in SURVEY_USAGES if u in usage]   # เรียงตามแบบฟอร์ม ไม่ซ้ำ
        with self._lock:
            self._conn.execute(
                "INSERT INTO survey_responses(ts, gender, role, usage, scores, liked, improve) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (_now(), gender, role, ",".join(usage), ",".join(map(str, scores)), text("liked"), text("improve")))
            self._conn.commit()

    def survey_rows(self):
        """ทุกแบบประเมิน (เก่า → ใหม่) — scores/usage แปลงเป็นรายการแล้ว"""
        with self._lock:
            rows = [dict(r) for r in self._conn.execute("SELECT * FROM survey_responses ORDER BY id")]
        for r in rows:
            r["scores"] = [int(s) for s in r["scores"].split(",")]
            r["usage"] = [u for u in r["usage"].split(",") if u]
        return rows

    def survey_summary(self, now=None):
        today = (now or datetime.now()).strftime("%Y-%m-%d")
        rows = self.survey_rows()
        items = []
        for i, (stage, q) in enumerate(SURVEY_ITEMS):
            m, sd = _mean_sd([r["scores"][i] for r in rows])
            items.append({"stage": stage, "text": q, "average": m, "sd": sd, "level": survey_level(m)})
        # ภาพรวม: รวมทุกคะแนนทุกข้อทุกคน
        m, sd = _mean_sd([s for r in rows for s in r["scores"]])
        count = lambda key, names: [{"key": k, "name": v, "count": sum(1 for r in rows if (k in r[key] if key == "usage" else r[key] == k))}   # noqa: E731
                                    for k, v in names.items()]
        comments = [{"ts": r["ts"], "liked": r["liked"], "improve": r["improve"]}
                    for r in reversed(rows) if r["liked"] or r["improve"]][:30]
        return {"total": len(rows), "today": sum(1 for r in rows if r["ts"].startswith(today)),
                "items": items, "average": m, "sd": sd, "level": survey_level(m),
                "pass": m is not None and m >= SURVEY_PASS, "pass_cut": SURVEY_PASS,
                "genders": count("gender", SURVEY_GENDERS), "roles": count("role", SURVEY_ROLES),
                "usages": count("usage", SURVEY_USAGES), "comments": comments}

    def summary(self, now=None):
        today = (now or datetime.now()).strftime("%Y-%m-%d")
        one = lambda sql, *a: self._conn.execute(sql, a).fetchone()[0]   # noqa: E731
        with self._lock:
            dist = {n: 0 for n in range(1, 6)}
            for row in self._conn.execute("SELECT stars, COUNT(*) c FROM ratings GROUP BY stars"):
                dist[row["stars"]] = row["c"]
            avg = one("SELECT AVG(stars) FROM ratings")
            top = [{"question": r["question"], "count": r["c"]} for r in self._conn.execute(
                "SELECT question, COUNT(*) c FROM questions GROUP BY question ORDER BY c DESC, MAX(id) DESC LIMIT 10")]
            low = [{"question": r["question"], "stars": r["stars"], "ts": r["ts"]} for r in self._conn.execute(
                "SELECT question, stars, ts FROM ratings WHERE stars <= 2 ORDER BY id DESC LIMIT 20")]
            return {
                "questions_total": one("SELECT COUNT(*) FROM questions"),
                "questions_today": one("SELECT COUNT(*) FROM questions WHERE ts LIKE ?", today + "%"),
                "ratings_total": sum(dist.values()),
                "ratings_today": one("SELECT COUNT(*) FROM ratings WHERE ts LIKE ?", today + "%"),
                "average": round(avg, 2) if avg is not None else None,
                "distribution": dist,
                "top": top,
                "low": low,
            }
