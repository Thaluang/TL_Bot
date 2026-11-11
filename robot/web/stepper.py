"""
แขน 2 ข้าง + คอ ของหุ่น — สเต็ปเปอร์ 17HS4401S ×3 ผ่าน TB6600 ×3 ที่ ESP32 คุม
Pi คุยกับ ESP32 ทางสาย USB (serial 115200) ด้วยโปรโตคอลข้อความทีละบรรทัด:

    Pi  → ESP32 :  #<id> <คำสั่ง> [อาร์กิวเมนต์]        เช่น  #7 MOVE L=90.0 R=-30.0 V=60
    ESP32 → Pi  :  #<id> OK [ค่า]  |  #<id> ERR <รหัส> [ข้อความ]  |  #<id> DONE  |  EVT <เหตุการณ์>

ดูสเปกเต็มที่ docs/superpowers/specs/2026-11-10-esp32-stepper-design.md และเฟิร์มแวร์ที่ robot/esp32/tl_arms/
ไม่มีบอร์ด/ไม่มี pyserial → โหมดจำลอง (พิมพ์บอกในหน้าต่างเซิร์ฟเวอร์ ใช้งานส่วนอื่นได้ตามปกติ)
"""
import glob
import itertools
import queue
import re
import threading
import time

BAUD = 115200
AXES = ("L", "R", "N")               # แขนซ้าย, แขนขวา, คอ
_LINE = re.compile(r"^(?:#(\d+)\s+)?(OK|ERR|DONE|EVT)\b\s*(.*)$")


class ArmError(Exception):
    """ESP32 ปฏิเสธคำสั่ง / ไม่ตอบ — code เป็นรหัสตามโปรโตคอล (LIMIT, NOT_PARKED, TIMEOUT, ...)"""

    def __init__(self, code: str, text: str = ""):
        super().__init__(f"{code} {text}".strip())
        self.code, self.text = code, text


def parse_line(line: str):
    """แปลงคำตอบ 1 บรรทัด → {"id", "kind", "code", "fields", "text"} / None ถ้าไม่ใช่โปรโตคอล (เช่น log ตอนบูต)"""
    m = _LINE.match((line or "").strip())
    if not m:
        return None
    rid, kind, rest = m.group(1), m.group(2), m.group(3)
    words = rest.split()
    code = ""
    if kind in ("ERR", "EVT") and words and "=" not in words[0]:
        code, words = words[0], words[1:]
    fields = dict(w.split("=", 1) for w in words if "=" in w)
    return {"id": int(rid) if rid else None, "kind": kind, "code": code, "fields": fields, "text": rest}


def find_port():
    """หาพอร์ต USB ของ ESP32 (ชื่ออาจเปลี่ยนหลังรีบูต) — คืน None ถ้าไม่เจอ"""
    ports = sorted(glob.glob("/dev/ttyUSB*")) + sorted(glob.glob("/dev/ttyACM*"))
    return ports[0] if ports else None


class EspLink:
    """ส่งคำสั่ง/รอคำตอบตามเลขคำสั่ง + heartbeat ระหว่างมอเตอร์หมุน (กัน watchdog ของ ESP32 ตัด)"""

    def __init__(self, ser, heartbeat: float = 1.0, timeout: float = 3.0):
        self.ser, self.heartbeat, self.timeout = ser, heartbeat, timeout
        self._ids = itertools.count(1)
        self._pending = {}                 # id → Queue ของคำตอบ
        self._lock = threading.Lock()
        self._busy = 0                     # จำนวนคำสั่งที่รอ DONE อยู่
        self.events = []                   # EVT ล่าสุด (เช่น WATCHDOG, BOOT)
        self._alive = True
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._beat, daemon=True).start()

    @classmethod
    def open(cls, port=None, **kw):
        """เปิดพอร์ตจริง (ต้องมี pyserial) — ESP32 รีเซ็ตตอนเปิดพอร์ต รอบูตเสร็จก่อน"""
        import serial                      # pyserial มีบน Pi
        port = port or find_port()
        if not port:
            raise ArmError("NO_PORT", "ไม่เจอ ESP32 ที่ /dev/ttyUSB* หรือ /dev/ttyACM*")
        link = cls(serial.Serial(port, BAUD, timeout=0.1), **kw)
        time.sleep(1.5)
        link.sync()
        return link

    def sync(self):
        """ส่งบรรทัดว่างหลัง ESP32 บูตเสร็จ — ตอนรีเซ็ตอาจมีเศษไบต์ค้างในบัฟเฟอร์ของ ESP32
        ถ้าไม่ปิดบรรทัดไว้ก่อน เศษนั้นจะไปต่อหน้าคำสั่งแรก แล้วโดนตอบ #0 ERR BAD_CMD (คำสั่งแรกเลย TIMEOUT)"""
        with self._lock:
            self.ser.write(b"\n")
        time.sleep(0.05)

    def _next_id(self) -> int:
        n = next(self._ids)
        if n > 65535:
            self._ids = itertools.count(1)
            n = next(self._ids)
        return n

    def _write(self, rid: int, cmd: str):
        with self._lock:
            self.ser.write(f"#{rid} {cmd}\n".encode())

    def _reader(self):
        while self._alive:
            try:
                raw = self.ser.readline()
            except Exception:
                time.sleep(0.2)
                continue
            if not raw:
                continue
            msg = parse_line(raw.decode(errors="replace"))
            if not msg:
                continue
            if msg["kind"] == "EVT":
                self.events = (self.events + [msg["code"]])[-20:]
                print("[แขน] ESP32:", msg["text"], flush=True)
                continue
            q = self._pending.get(msg["id"])
            if q:
                q.put(msg)

    def _beat(self):
        while self._alive:
            time.sleep(self.heartbeat)
            if self._busy:
                try:
                    self._write(self._next_id(), "PING")   # ไม่รอคำตอบ แค่บอกว่า Pi ยังอยู่
                except Exception:
                    pass

    def request(self, cmd: str, wait_done: bool = False, done_timeout: float = 30.0) -> dict:
        """ส่งคำสั่ง รอ OK (ERR = ArmError) และถ้า wait_done รอจนได้ DONE"""
        rid = self._next_id()
        q = queue.Queue()
        self._pending[rid] = q
        if wait_done:
            self._busy += 1
        try:
            self._write(rid, cmd)
            first = self._get(q, self.timeout)
            if not wait_done:
                return first
            last = self._get(q, done_timeout)
            return last
        finally:
            if wait_done:
                self._busy -= 1
            self._pending.pop(rid, None)

    @staticmethod
    def _get(q, timeout):
        try:
            msg = q.get(timeout=timeout)
        except queue.Empty:
            raise ArmError("TIMEOUT", "ESP32 ไม่ตอบ")
        if msg["kind"] == "ERR":
            raise ArmError(msg["code"], msg["text"])
        return msg

    def close(self):
        self._alive = False
        try:
            self.ser.close()
        except Exception:
            pass


class StepperArms:
    """สั่งแขน/คอเป็นองศา + ท่าทางสำเร็จรูป
    link=None + opener=None คือโหมดจำลอง (เทสต์/คอม) · มี opener = ยังไม่เจอบอร์ด แต่จะลองต่อเองตอนจะโบก"""

    WAVE_UP, WAVE_A, WAVE_B, WAVE_TIMES = 150, 120, 165, 3   # แขนทั้งสองข้าง: ยกขึ้นพร้อมกัน แล้วโบกไปมา
    SPEED, WAVE_SPEED = 60, 120                               # องศา/วินาที
    RETRY = 5.0                                               # ไม่เจอบอร์ด: ลองหาใหม่ห่างกันอย่างน้อยกี่วินาที

    def __init__(self, link, opener=None):
        self.link = link
        self._opener = opener               # ฟังก์ชันเปิดพอร์ต → EspLink (None = ไม่ลองต่อเอง)
        self._next_try = 0.0
        self._gesture = threading.Lock()    # ทีละท่า (ทักทายซ้อนกันไม่ได้)

    @classmethod
    def connect(cls, port=None):
        """ต่อ ESP32 ตอนเปิดเซิร์ฟเวอร์ — ไม่เจอก็ไม่เป็นไร: เสียบทีหลัง/สายหลุด จะต่อเองตอนจะโบกครั้งถัดไป"""
        arms = cls(None, opener=lambda: EspLink.open(port))
        arms._ensure_link()
        return arms

    def _ensure_link(self):
        """คืน link ที่ใช้ได้ — ยังไม่มีแล้วมี opener: ลองเปิดพอร์ต (ไม่ถี่กว่า RETRY วินาที)"""
        if self.link is not None or self._opener is None:
            return self.link
        now = time.monotonic()
        if now < self._next_try:
            return None
        self._next_try = now + self.RETRY
        try:
            self.link = self._opener()
        except Exception as e:
            print(f"[แขน] ยังไม่เจอ ESP32 ({e}) — เสียบเมื่อไรจะต่อเองตอนโบกครั้งถัดไป", flush=True)
            return None
        st = self.status()
        print(f"[แขน] ต่อ ESP32 แล้ว: {st}", flush=True)
        if st.get("connected") and not st.get("homed"):
            print("[แขน] ⚠ ESP32 ไม่รู้ตำแหน่งแขน (ไม่ได้ PARK ก่อนปิด) — โบกไม่ได้จนกว่าจะจัดแขนห้อยตรงแล้วส่ง ZERO", flush=True)
        return self.link

    def _drop_link(self, err):
        """สายหลุด/บอร์ดหาย: ปิดการเชื่อมต่อเดิม รอบหน้าค่อยลองต่อใหม่"""
        print(f"[แขน] ESP32 หลุด ({err}) — จะลองต่อใหม่ตอนโบกครั้งถัดไป", flush=True)
        link, self.link, self._next_try = self.link, None, 0.0
        try:
            link.close()
        except Exception:
            pass

    # ---- คำสั่งพื้นฐาน ----
    def move(self, L=None, R=None, N=None, speed=None, wait=True):
        targets = {k: v for k, v in (("L", L), ("R", R), ("N", N)) if v is not None}
        if not targets:
            return
        args = " ".join(f"{k}={float(v):.1f}" for k, v in targets.items())
        cmd = f"MOVE {args} V={int(speed or self.SPEED)}"
        if self.link is None:
            print(f"[แขน] (จำลอง) {cmd}")
            return
        self.link.request(cmd, wait_done=wait)

    def position(self) -> dict:
        if self.link is None:
            return {k: 0.0 for k in AXES}
        f = self.link.request("POS?")["fields"]
        return {k: float(f[k]) for k in AXES}

    def zero(self):
        """ตั้งตำแหน่งตอนนี้เป็นมุม 0 (ใช้หลังจัดแขนห้อยตรง/คอหันตรงด้วยมือ)"""
        if self.link:
            self.link.request("ZERO")

    def park(self):
        """กลับมุม 0 → ปลดแรงบิด → ESP32 จดว่าจอดแล้ว (เรียกก่อนปิดเครื่อง)"""
        if self.link is None:
            print("[แขน] (จำลอง) PARK")
            return
        self.link.request("PARK", wait_done=True)

    def stop(self):
        if self.link:
            self.link.request("STOP")

    def enable(self, on: bool):
        if self.link:
            self.link.request(f"EN {1 if on else 0}")

    def status(self) -> dict:
        if self.link is None:
            return {"connected": False, "simulated": True, "parked": None, "homed": None}
        try:
            f = self.link.request("PING")["fields"]
            return {"connected": True, "simulated": False, "parked": f.get("parked") == "1",
                    "homed": f.get("homed") == "1", "fw": f.get("fw")}
        except ArmError:
            return {"connected": False, "simulated": False, "parked": None, "homed": None}

    # ---- ท่าทาง ----
    def wave(self):
        """ทักทายด้วยแขนทั้งสองข้าง: ยกขึ้นพร้อมกัน → โบกไปมา → จอด
        (+ = ยกขึ้นทั้งสองข้าง เพราะเฟิร์มแวร์กลับทิศแขนขวาไว้แล้ว)"""
        with self._gesture:
            if self._ensure_link() is None and self._opener is not None:
                return                      # ยังไม่ได้เสียบบอร์ด: ข้ามท่า (หน้าจอทักทายต่อได้ตามปกติ)
            try:
                self.move(L=self.WAVE_UP, R=self.WAVE_UP, speed=self.SPEED)
                for _ in range(self.WAVE_TIMES):
                    self.move(L=self.WAVE_A, R=self.WAVE_A, speed=self.WAVE_SPEED)
                    self.move(L=self.WAVE_B, R=self.WAVE_B, speed=self.WAVE_SPEED)
                # จบด้วย PARK (กลับ 0 + ESP32 จดว่าจอดแล้ว) ไม่ใช่แค่ MOVE R=0:
                # เซิร์ฟเวอร์เปิดพอร์ตใหม่เมื่อไร ESP32 รีเซ็ต ถ้าไม่ได้จอดไว้จะลืมตำแหน่ง แล้วตอบ NOT_PARKED ทุกท่า
                self.park()
            except OSError as e:            # ถอดสาย USB ระหว่างใช้ (pyserial โยน SerialException = OSError)
                self._drop_link(e)
            except ArmError as e:
                if e.code == "TIMEOUT":     # บอร์ดเงียบ (ค้าง/สายหลวม) → ต่อใหม่รอบหน้า
                    self._drop_link(e)
                raise

    def look(self, deg: float):
        """หันคอ (+ ซ้าย / − ขวา ตามทิศที่ติดตั้ง)"""
        self.move(N=deg, speed=45)

    def wave_async(self) -> bool:
        """โบกมือใน thread แยก (ไม่ให้หน้าเว็บรอ) — กำลังโบกอยู่คืน False"""
        if self._gesture.locked():
            return False

        def run():
            try:
                self.wave()
            except ArmError as e:
                print("[แขน] โบกไม่ได้:", e, flush=True)
        threading.Thread(target=run, daemon=True).start()
        return True
