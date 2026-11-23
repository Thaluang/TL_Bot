"""
ค่าร่วมของเทสต์ในโฟลเดอร์ web/

หุ่นตัวจริงใช้จอแนวตั้งเป็นหลัก (config.SCREEN_LAYOUT = "portrait") แต่เทสต์เดิมใน test_server.py ทดสอบหน้าแนวนอน
ผ่าน /screen — ตั้งค่าเป็น "landscape" ให้ทุกเทสต์ก่อน เทสต์หน้าแนวตั้งใช้ /screen-v หรือ monkeypatch ค่าเอง (test_portrait.py)
"""
import pytest

import config


@pytest.fixture(autouse=True)
def _screen_layout_landscape(monkeypatch):
    monkeypatch.setattr(config, "SCREEN_LAYOUT", "landscape")
