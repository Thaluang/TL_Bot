"""
ข่าวประชาสัมพันธ์ที่ครูลงผ่านหน้า /stats แล้วขึ้นจอหน้าวิทยาลัย

เก็บในโฟลเดอร์ข้อมูลถาวร (ดู datadir.py):  news.json + news/<id>.jpg|png|webp
ข่าวหนึ่งรายการ:
  {"id", "category", "title", "subtitle", "detail", "link", "image",
   "start": "YYYY-MM-DD" | "", "end": "YYYY-MM-DD" | "", "hidden": bool, "order": int}
"""
import json
import os
import re
import threading
import uuid
from datetime import date
from pathlib import Path

CATEGORIES = ("admission", "event", "scholarship", "award", "general")
CATEGORY_NAMES = {"admission": "รับสมัคร", "event": "กิจกรรม", "scholarship": "ทุนการศึกษา",
                  "award": "ผลงาน", "general": "ประกาศทั่วไป"}
LIMITS = {"title": 80, "subtitle": 80, "detail": 1000, "link": 500}
MAX_IMAGE_BYTES = 3 * 1024 * 1024
_MAGIC = ((b"\xff\xd8\xff", ".jpg"), (b"\x89PNG\r\n\x1a\n", ".png"))
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NAME = re.compile(r"^[0-9a-f]{12}(-[0-9a-f]{6})?\.(jpg|png|webp)$")


class NewsError(ValueError):
    """ข้อมูลข่าวไม่ถูกต้อง — ข้อความอ่านให้ครูเข้าใจ"""


def _image_ext(data: bytes) -> str:
    if len(data) > MAX_IMAGE_BYTES:
        raise NewsError("รูปใหญ่เกิน 3 MB")
    for magic, ext in _MAGIC:
        if data.startswith(magic):
            return ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise NewsError("รองรับเฉพาะรูป JPG, PNG หรือ WebP")


def _date_ok(s: str) -> str:
    s = (s or "").strip()
    if s and not _DATE.match(s):
        raise NewsError("วันที่ต้องเป็นรูปแบบ ปปปป-ดด-วว")
    if s:
        try:
            date.fromisoformat(s)
        except ValueError:
            raise NewsError("วันที่ไม่ถูกต้อง")
    return s


class NewsStore:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.img_dir = self.folder / "news"
        self.file = self.folder / "news.json"
        self._lock = threading.Lock()
        self._items = self._load()
        self.version = uuid.uuid4().hex[:8]

    # ---- อ่าน/เขียนไฟล์ ----
    def _load(self) -> list:
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
            return [d for d in data if isinstance(d, dict) and d.get("id")] if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _save_items(self, items: list) -> None:
        """เขียนรายการลงไฟล์ — สำเร็จแล้วค่อยเปลี่ยนในหน่วยความจำ (ไดรฟ์หลุด = ทุกอย่างเหมือนเดิม)"""
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(items, ensure_ascii=False, indent=1))
            f.flush()
            os.fsync(f.fileno())   # ไฟดับกลางเขียนบนแฟลชไดรฟ์ (FAT) ไม่ให้ได้ไฟล์ว่าง
        os.replace(tmp, self.file)

    def _commit(self, items: list) -> None:
        """เรียกขณะถือ lock: บันทึกก่อน แล้วค่อยใช้รายการใหม่"""
        self._save_items(items)
        self._items = items
        self.version = uuid.uuid4().hex[:8]

    def _write_image(self, news_id: str, data: bytes) -> str:
        ext = _image_ext(data)
        self.img_dir.mkdir(parents=True, exist_ok=True)
        name = f"{news_id}-{uuid.uuid4().hex[:6]}{ext}"   # ชื่อใหม่ทุกครั้ง เบราว์เซอร์จะได้ไม่ใช้รูปเก่าที่จำไว้
        (self.img_dir / name).write_bytes(data)
        return name

    def _drop_image(self, name: str) -> None:
        p = self.image_path(name)
        if p:
            try:
                p.unlink()
            except OSError:
                pass

    # ---- ตรวจข้อมูล ----
    def _clean(self, fields: dict, current: dict) -> dict:
        out = dict(current)
        for key in ("category", "title", "subtitle", "detail", "link", "start", "end"):
            if key in fields:
                out[key] = str(fields[key] if fields[key] is not None else "").strip()
        if "hidden" in fields:
            out["hidden"] = fields["hidden"] in (True, 1, "1", "true", "on")
        if out.get("category") not in CATEGORIES:
            raise NewsError("เลือกหมวดข่าวก่อน")
        for key, n in LIMITS.items():
            out[key] = (out.get(key) or "")[:n]
        if not out["title"]:
            raise NewsError("ใส่หัวข้อข่าวก่อน")
        if out["link"] and not re.match(r"^https?://", out["link"]):
            raise NewsError("ลิงก์ต้องขึ้นต้นด้วย http:// หรือ https://")
        out["start"], out["end"] = _date_ok(out.get("start")), _date_ok(out.get("end"))
        if out["start"] and out["end"] and out["end"] < out["start"]:
            raise NewsError("วันหมดอายุต้องไม่ก่อนวันเริ่ม")
        return out

    # ---- ใช้งาน ----
    def all(self) -> list:
        with self._lock:
            return sorted((dict(d) for d in self._items), key=lambda d: d.get("order", 0))

    def get(self, news_id: str):
        with self._lock:
            return next((dict(d) for d in self._items if d["id"] == news_id), None)

    def active(self, today: date) -> list:
        day = today.isoformat()
        return [d for d in self.all()
                if not d.get("hidden") and (not d.get("start") or d["start"] <= day) and (not d.get("end") or day <= d["end"])]

    def add(self, fields: dict, image) -> dict:
        blank = {"id": uuid.uuid4().hex[:12], "category": "", "title": "", "subtitle": "", "detail": "",
                 "link": "", "image": "", "start": "", "end": "", "hidden": False}
        item = self._clean(fields, blank)
        if image:
            item["image"] = self._write_image(item["id"], image)
        try:
            with self._lock:
                item["order"] = min((d.get("order", 0) for d in self._items), default=1) - 1   # ข่าวใหม่ขึ้นบนสุด
                self._commit(self._items + [item])
        except OSError:
            self._drop_image(item["image"])   # บันทึกไม่สำเร็จ ไม่ทิ้งรูปค้าง
            raise
        return dict(item)

    def update(self, news_id: str, fields: dict, image, remove_image: bool = False) -> dict:
        cur = self.get(news_id)
        if cur is None:
            raise KeyError(news_id)
        item = self._clean(fields, cur)
        old = cur.get("image", "")
        if image:
            item["image"] = self._write_image(news_id, image)
        elif remove_image:
            item["image"] = ""
        try:
            with self._lock:
                self._commit([item if d["id"] == news_id else d for d in self._items])
        except OSError:
            if item["image"] and item["image"] != old:
                self._drop_image(item["image"])
            raise
        if old and old != item["image"]:
            self._drop_image(old)
        return dict(item)

    def delete(self, news_id: str) -> bool:
        cur = self.get(news_id)
        if cur is None:
            return False
        with self._lock:
            self._commit([d for d in self._items if d["id"] != news_id])
        if cur.get("image"):
            self._drop_image(cur["image"])
        return True

    def reorder(self, ids: list) -> None:
        with self._lock:
            rank = {i: k for k, i in enumerate(ids)}
            rest = len(rank)
            for d in sorted(self._items, key=lambda d: d.get("order", 0)):
                if d["id"] not in rank:
                    rank[d["id"]] = rest
                    rest += 1
            self._commit([{**d, "order": rank[d["id"]]} for d in self._items])

    def image_path(self, name: str):
        if not name or not _NAME.match(name):
            return None
        p = self.img_dir / name
        return p if p.is_file() else None

    def ai_text(self, today: date, lang: str = "th") -> str:
        """ข่าวที่ขึ้นจออยู่ เป็นข้อความต่อท้ายข้อมูลที่ส่งให้ AI (หุ่นจะตอบเรื่องข่าวได้)"""
        items = self.active(today)
        if not items:
            return ""
        lines = ["## ข่าวประชาสัมพันธ์ล่าสุดของวิทยาลัย (ครูลงไว้ ขึ้นจออยู่ตอนนี้)"]
        for d in items:
            line = f"- [{CATEGORY_NAMES[d['category']]}] {d['title']}"
            if d.get("subtitle"):
                line += f" — {d['subtitle']}"
            if d.get("detail"):
                line += f": {d['detail']}"
            if d.get("link"):
                line += f" (ลิงก์: {d['link']})"
            lines.append(line)
        return "\n".join(lines)
