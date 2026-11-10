"""
หาโฟลเดอร์เก็บข้อมูลที่ต้องอยู่รอดหลังรีบูต (ข่าว รูปข่าว สถิติ)

บน Pi แอปรันจาก RAM (/dev/shm) และการ์ด SD เขียนแล้วพัง → เก็บบนแฟลชไดรฟ์ USB แทน
ลำดับ: ตัวแปร TLBOT_DATA_DIR → แฟลชไดรฟ์ที่ desktop เมานต์ให้ (/media/<user>/<ไดรฟ์>/tlbot-data)
→ โฟลเดอร์สำรองในเครื่อง (robot/data — บน Pi อยู่ใน RAM รีบูตแล้วหาย, หน้าครูจะเตือน)
"""
import os
from pathlib import Path

SUBDIR = "tlbot-data"


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write-test"
        probe.write_bytes(b"ok")
        probe.unlink()
        return True
    except OSError:
        return False


def _usb_candidates(media_roots):
    for root in media_roots:
        try:
            users = sorted(p for p in Path(root).iterdir() if p.is_dir())
        except OSError:
            continue
        for user in users:
            try:
                yield from sorted(p for p in user.iterdir() if p.is_dir())
            except OSError:
                continue


def resolve_data_dir(env, media_roots, fallback):
    """คืน (โฟลเดอร์, อยู่ถาวรไหม)"""
    want = (env.get("TLBOT_DATA_DIR") or "").strip()
    if want and _writable(Path(want)):
        return Path(want), True
    for drive in _usb_candidates(media_roots):
        if _writable(drive / SUBDIR):
            return drive / SUBDIR, True
    fallback = Path(fallback)
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback, False


class DataDir:
    def __init__(self, folder, persistent: bool):
        self.folder = Path(folder)
        self.persistent = persistent

    def path(self, name: str) -> Path:
        return self.folder / name
