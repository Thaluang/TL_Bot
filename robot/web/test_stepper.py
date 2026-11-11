"""
เทสต์ตัวคุยกับ ESP32 (แขน 2 ข้าง + คอ สเต็ปเปอร์) — ใช้ ESP32 จำลอง ไม่ต้องมีบอร์ดจริง
รันจาก robot/:  python -m pytest web/test_stepper.py -q
"""
import queue
import threading
import time

import pytest

from stepper import ArmError, EspLink, StepperArms, parse_line


class FakeEsp:
    """จำลอง ESP32 ฝั่งสาย USB: รับคำสั่งตามโปรโตคอล ตอบกลับเหมือนเฟิร์มแวร์จริง (แบบย่อ)"""

    def __init__(self, done_delay=0.0, silent=False, limit=180.0):
        self.rx = queue.Queue()          # สิ่งที่ ESP32 ส่งกลับมาให้ Pi
        self.sent = []                   # คำสั่งที่ Pi ส่งมา
        self.pos = {"L": 0.0, "R": 0.0, "N": 0.0}
        self.done_delay, self.silent, self.limit = done_delay, silent, limit
        self.parked = True

    # ---- หน้าตาแบบ pyserial ----
    def write(self, data: bytes):
        line = data.decode().strip()
        self.sent.append(line)
        if not line:                     # บรรทัดว่าง: เฟิร์มแวร์จริงข้ามไป
            return len(data)
        if self.silent:
            return len(data)
        tag, _, rest = line.partition(" ")
        cmd, *args = rest.split()
        if cmd == "PING":
            self._say(f"{tag} OK fw=1.0 parked={int(self.parked)} homed=1")
        elif cmd == "POS?":
            p = self.pos
            self._say(f"{tag} OK L={p['L']:.1f} R={p['R']:.1f} N={p['N']:.1f} busy=0")
        elif cmd == "MOVE":
            kv = dict(a.split("=") for a in args)
            for k in ("L", "R", "N"):
                if k in kv and abs(float(kv[k])) > self.limit:
                    self._say(f"{tag} ERR LIMIT {k}={kv[k]} max={self.limit:g}")
                    return len(data)
            for k in ("L", "R", "N"):
                if k in kv:
                    self.pos[k] = float(kv[k])
            self.parked = False
            self._say(f"{tag} OK")
            threading.Timer(self.done_delay, self._say, [f"{tag} DONE"]).start()
        elif cmd == "PARK":
            self.pos = {"L": 0.0, "R": 0.0, "N": 0.0}
            self._say(f"{tag} OK")
            threading.Timer(self.done_delay, lambda: (setattr(self, "parked", True), self._say(f"{tag} DONE"))).start()
        elif cmd in ("ZERO", "STOP", "EN"):
            self._say(f"{tag} OK")
        else:
            self._say(f"{tag} ERR BAD_CMD {cmd}")
        return len(data)

    def readline(self):
        try:
            return (self.rx.get(timeout=0.05) + "\n").encode()
        except queue.Empty:
            return b""

    def close(self):
        pass

    def _say(self, text):
        self.rx.put(text)


def arms(**kw):
    esp = FakeEsp(**kw)
    return StepperArms(EspLink(esp, heartbeat=0.1)), esp


# ---- อ่านคำตอบ ----
def test_parse_ok_with_fields():
    m = parse_line("#12 OK L=90.0 R=-30.5 N=0.0 busy=1")
    assert m["id"] == 12 and m["kind"] == "OK"
    assert m["fields"] == {"L": "90.0", "R": "-30.5", "N": "0.0", "busy": "1"}


def test_parse_err_and_event():
    e = parse_line("#3 ERR LIMIT L=200 max=180")
    assert e["kind"] == "ERR" and e["code"] == "LIMIT" and e["fields"]["max"] == "180"
    ev = parse_line("EVT WATCHDOG")
    assert ev["id"] is None and ev["kind"] == "EVT" and ev["code"] == "WATCHDOG"
    assert parse_line("garbage from boot log") is None


# ---- สั่งงาน ----
def test_move_waits_until_done_and_sends_degrees():
    a, esp = arms(done_delay=0.2)
    t = time.time()
    a.move(L=90, R=-30, speed=45)
    assert time.time() - t >= 0.2                       # รอจน ESP32 บอกว่า DONE
    assert any(s.endswith("MOVE L=90.0 R=-30.0 V=45") for s in esp.sent)


def test_move_over_limit_raises():
    a, _ = arms(limit=180)
    with pytest.raises(ArmError) as e:
        a.move(L=200)
    assert e.value.code == "LIMIT"


def test_position_read_back():
    a, _ = arms()
    a.move(L=45, N=-20)
    assert a.position() == {"L": 45.0, "R": 0.0, "N": -20.0}


def test_heartbeat_pings_while_moving():
    a, esp = arms(done_delay=0.45)
    a.move(R=120)
    assert sum(1 for s in esp.sent if s.endswith("PING")) >= 2   # กัน watchdog ของ ESP32 ตัดมอเตอร์


def test_no_reply_times_out():
    a, _ = arms(silent=True)
    a.link.timeout = 0.3
    with pytest.raises(ArmError) as e:
        a.position()
    assert e.value.code == "TIMEOUT"


def test_wave_ends_parked():
    """โบกจบด้วย PARK (กลับ 0 + ESP32 จดว่าจอดแล้ว) — เปิดพอร์ตใหม่ ESP32 รีเซ็ต ยังรู้ตำแหน่ง ไม่ติด NOT_PARKED"""
    a, esp = arms()
    a.wave()
    cmds = [s.split(" ", 1)[1] for s in esp.sent if s and "PING" not in s]
    assert len([c for c in cmds if c.startswith("MOVE")]) >= 4
    assert cmds[-1] == "PARK"
    assert esp.parked and esp.pos == {"L": 0.0, "R": 0.0, "N": 0.0}


def test_park_and_status():
    a, esp = arms()
    a.move(L=30)
    a.park()
    st = a.status()
    assert st["connected"] and not st["simulated"] and st["parked"] is True and st["homed"] is True
    assert esp.pos == {"L": 0.0, "R": 0.0, "N": 0.0}


def test_simulated_when_no_esp32():
    a = StepperArms(None)                 # ไม่มีบอร์ด: ทำงานต่อได้ แค่พิมพ์บอก
    a.move(L=90); a.wave(); a.park()
    assert a.status()["simulated"] is True


def test_sync_flushes_boot_junk_with_blank_line():
    """เปิดพอร์ตแล้ว ESP32 อาจมีเศษไบต์ค้างตอนรีเซ็ต — sync() ส่งบรรทัดว่างปิดท้ายเศษนั้นก่อนคำสั่งแรก"""
    a, esp = arms()
    a.link.sync()
    assert esp.sent[0] == ""
    assert a.status()["connected"] is True


# ---- เสียบ ESP32 ทีหลัง / สายหลุด: ต่อเองตอนจะโบก ไม่ต้องรีสตาร์ทเซิร์ฟเวอร์ ----
class Opener:
    """แทน EspLink.open: ครั้งแรก ๆ ยังไม่เสียบ (โยน error) จนกว่าจะตั้ง plugged=True"""

    def __init__(self):
        self.plugged, self.calls, self.esp = False, 0, None

    def __call__(self):
        self.calls += 1
        if not self.plugged:
            raise ArmError("NO_PORT", "ยังไม่เสียบ")
        self.esp = FakeEsp()
        return EspLink(self.esp, heartbeat=0.1)


def test_plug_in_later_connects_on_next_wave():
    op = Opener()
    a = StepperArms(None, opener=op)
    a.RETRY = 0
    a.wave()                                   # ยังไม่เสียบ: ข้ามท่า ไม่ค้าง ไม่โยน error
    assert a.link is None and op.calls == 1
    op.plugged = True
    a.wave()                                   # เสียบแล้ว: ต่อเองแล้วโบกจริง
    assert a.link is not None
    assert any(" MOVE " in s for s in op.esp.sent) and op.esp.sent[-1].endswith("PARK")


def test_retry_is_rate_limited():
    op = Opener()
    a = StepperArms(None, opener=op)           # RETRY ค่าเริ่มต้น: ไม่ลองเปิดพอร์ตรัว ๆ ทุกครั้งที่แตะจอ
    a.wave(); a.wave(); a.wave()
    assert op.calls == 1


def test_unplugged_mid_use_reconnects():
    op = Opener(); op.plugged = True
    a = StepperArms(None, opener=op)
    a.RETRY = 0
    a.wave()
    first = a.link

    def broken(_data):
        raise OSError("device disconnected")   # ถอดสาย: pyserial โยน SerialException (= OSError)
    first.ser.write = broken
    a.wave()                                   # โยนทิ้งการเชื่อมต่อเดิม ไม่ crash
    assert a.link is None
    a.wave()                                   # ครั้งต่อไปต่อใหม่เอง
    assert a.link is not None and a.link is not first


def test_silent_board_timeout_drops_link():
    """บอร์ดค้าง/สายหลวมแบบไม่มี error — ไม่ตอบจนหมดเวลา → ทิ้งการเชื่อมต่อ รอบหน้าต่อใหม่"""
    op = Opener(); op.plugged = True
    a = StepperArms(None, opener=op)
    a.RETRY = 0
    a._ensure_link()
    a.link.timeout = 0.2
    op.esp.silent = True
    with pytest.raises(ArmError):
        a.wave()
    assert a.link is None
