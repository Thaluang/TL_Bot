"""
เนื้อหาที่ครูลงผ่านหน้า /stats แล้วขึ้นจอหุ่น (นอกจากข่าว)
- ปฏิทินแนะแนวการศึกษา:  guidance.json
    {"id", "date": "YYYY-MM-DD", "end": "YYYY-MM-DD" | "", "title", "time", "place", "detail"}
- คลังภาพกิจกรรม:          gallery.json + gallery/<id>-xxxxxx.jpg|png|webp
    {"id", "title", "date": "YYYY-MM-DD" | "", "image", "order": int}
เก็บในโฟลเดอร์ข้อมูลถาวรเดียวกับข่าว (ดู datadir.py) — เขียนไฟล์ก่อน สำเร็จแล้วค่อยเปลี่ยนในหน่วยความจำ
"""
import json
import os
import re
import threading
import uuid
from datetime import date
from pathlib import Path

from news import NewsError, _date_ok, _image_ext

_NAME = re.compile(r"^[0-9a-f]{12}-[0-9a-f]{6}\.(jpg|png|webp)$")
TH_MONTHS = ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")


def th_date(s: str) -> str:
    """2026-12-05 → 5 ธ.ค. 2569"""
    d = date.fromisoformat(s)
    return f"{d.day} {TH_MONTHS[d.month - 1]} {d.year + 543}"


class _JsonList:
    """รายการ dict ในไฟล์ JSON ไฟล์เดียว — ปลอดภัยกับไฟดับ/แฟลชไดรฟ์หลุดกลางเขียน"""

    def __init__(self, folder, filename):
        self.folder = Path(folder)
        self.file = self.folder / filename
        self._lock = threading.Lock()
        self._items = self._load()
        self.version = uuid.uuid4().hex[:8]

    def _load(self) -> list:
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
            return [d for d in data if isinstance(d, dict) and d.get("id")] if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _save_items(self, items: list) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(items, ensure_ascii=False, indent=1))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.file)

    def _commit(self, items: list) -> None:
        self._save_items(items)
        self._items = items
        self.version = uuid.uuid4().hex[:8]

    def get(self, item_id: str):
        with self._lock:
            return next((dict(d) for d in self._items if d["id"] == item_id), None)


# ================= ปฏิทินแนะแนวการศึกษา =================
GUIDANCE_LIMITS = {"title": 100, "time": 40, "place": 100, "detail": 500}


class GuidanceStore(_JsonList):
    def __init__(self, folder):
        super().__init__(folder, "guidance.json")

    def _clean(self, fields: dict, current: dict) -> dict:
        out = dict(current)
        for key in ("date", "end", *GUIDANCE_LIMITS):
            if key in fields:
                out[key] = str(fields[key] if fields[key] is not None else "").strip()
        for key, n in GUIDANCE_LIMITS.items():
            out[key] = (out.get(key) or "")[:n]
        out["date"], out["end"] = _date_ok(out.get("date")), _date_ok(out.get("end"))
        if not out["date"]:
            raise NewsError("เลือกวันที่แนะแนวก่อน")
        if not out["title"]:
            raise NewsError("ใส่ชื่องานแนะแนว / โรงเรียนก่อน")
        if out["end"] and out["end"] < out["date"]:
            raise NewsError("วันสิ้นสุดต้องไม่ก่อนวันเริ่ม")
        if out["end"] == out["date"]:
            out["end"] = ""
        return out

    def all(self) -> list:
        """เรียงตามวัน (เก่า → ใหม่)"""
        with self._lock:
            return sorted((dict(d) for d in self._items), key=lambda d: (d["date"], d.get("time", "")))

    def upcoming(self, today: date) -> list:
        day = today.isoformat()
        return [d for d in self.all() if (d.get("end") or d["date"]) >= day]

    def add(self, fields: dict) -> dict:
        blank = {"id": uuid.uuid4().hex[:12], "date": "", "end": "", "title": "", "time": "", "place": "", "detail": ""}
        item = self._clean(fields, blank)
        with self._lock:
            self._commit(self._items + [item])
        return dict(item)

    def update(self, item_id: str, fields: dict) -> dict:
        cur = self.get(item_id)
        if cur is None:
            raise KeyError(item_id)
        item = self._clean(fields, cur)
        with self._lock:
            self._commit([item if d["id"] == item_id else d for d in self._items])
        return dict(item)

    def delete(self, item_id: str) -> bool:
        if self.get(item_id) is None:
            return False
        with self._lock:
            self._commit([d for d in self._items if d["id"] != item_id])
        return True

    def ai_text(self, today: date) -> str:
        """กำหนดการแนะแนวที่ยังไม่ผ่าน — ต่อท้ายข้อมูลที่ส่งให้ AI (หุ่นตอบว่าแนะแนววันไหนได้)"""
        items = self.upcoming(today)[:20]
        if not items:
            return ""
        lines = ["## ปฏิทินแนะแนวการศึกษาของวิทยาลัย (ครูลงไว้ — กำหนดการที่ยังไม่ผ่าน)"]
        for d in items:
            when = th_date(d["date"]) + (f" ถึง {th_date(d['end'])}" if d.get("end") else "")
            line = f"- {when}"
            if d.get("time"):
                line += f" เวลา {d['time']}"
            line += f": {d['title']}"
            if d.get("place"):
                line += f" ณ {d['place']}"
            if d.get("detail"):
                line += f" — {d['detail']}"
            lines.append(line)
        return "\n".join(lines)


# ================= คลังภาพกิจกรรม =================
GALLERY_MAX = 300   # เก็บไม่เกินเท่านี้รูป (แฟลชไดรฟ์ไม่เต็ม จอโหลดไม่หนัก)


class GalleryStore(_JsonList):
    def __init__(self, folder):
        super().__init__(folder, "gallery.json")
        self.img_dir = self.folder / "gallery"

    def all(self) -> list:
        """รูปใหม่ล่าสุดก่อน"""
        with self._lock:
            return sorted((dict(d) for d in self._items), key=lambda d: d.get("order", 0))

    def _clean(self, fields: dict, current: dict) -> dict:
        out = dict(current)
        for key in ("title", "date"):
            if key in fields:
                out[key] = str(fields[key] if fields[key] is not None else "").strip()
        out["title"] = (out.get("title") or "")[:100]
        out["date"] = _date_ok(out.get("date"))
        if not out["title"]:
            raise NewsError("ใส่ชื่อกิจกรรมก่อน")
        return out

    def add(self, fields: dict, image: bytes) -> dict:
        if not image:
            raise NewsError("เลือกรูปก่อน")
        item = self._clean(fields, {"id": uuid.uuid4().hex[:12], "title": "", "date": "", "image": ""})
        ext = _image_ext(image)
        with self._lock:
            if len(self._items) >= GALLERY_MAX:
                raise NewsError(f"คลังภาพเต็มแล้ว ({GALLERY_MAX} รูป) — ลบรูปเก่าออกก่อน")
        self.img_dir.mkdir(parents=True, exist_ok=True)
        item["image"] = f"{item['id']}-{uuid.uuid4().hex[:6]}{ext}"
        path = self.img_dir / item["image"]
        path.write_bytes(image)
        try:
            with self._lock:
                item["order"] = min((d.get("order", 0) for d in self._items), default=1) - 1   # รูปใหม่ขึ้นก่อน
                self._commit(self._items + [item])
        except OSError:
            path.unlink(missing_ok=True)
            raise
        return dict(item)

    def update(self, item_id: str, fields: dict) -> dict:
        cur = self.get(item_id)
        if cur is None:
            raise KeyError(item_id)
        item = self._clean(fields, cur)
        with self._lock:
            self._commit([item if d["id"] == item_id else d for d in self._items])
        return dict(item)

    def delete(self, item_id: str) -> bool:
        cur = self.get(item_id)
        if cur is None:
            return False
        with self._lock:
            self._commit([d for d in self._items if d["id"] != item_id])
        p = self.image_path(cur.get("image", ""))
        if p:
            try:
                p.unlink()
            except OSError:
                pass
        return True

    def image_path(self, name: str):
        if not name or not _NAME.match(name):
            return None
        p = self.img_dir / name
        return p if p.is_file() else None
