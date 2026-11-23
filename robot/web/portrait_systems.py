"""
ระบบภายนอกของวิทยาลัยที่ปุ่ม 2–5 บนจอแนวตั้งเปิด (screen_v.html / portrait.js อ่านจาก GET /pv/systems)

แต่ละเว็บอาจห้ามเปิดซ้อนในหน้าอื่น (X-Frame-Options / CSP frame-ancestors) — ถ้าห้าม จอต้องขึ้น QR ให้สแกน
แทนการเปิด iframe ที่จะกลายเป็นจอว่าง เซิร์ฟเวอร์จึงเช็กหัวข้อตอบกลับของแต่ละเว็บให้ (จำผลไว้ CACHE_SECONDS)
เจ้าของเว็บแก้ให้ยอมแล้ว จอเปลี่ยนเป็นเปิดในจอเองภายในรอบแคชถัดไป ไม่ต้องแก้โค้ด
แก้ลิงก์/ชื่อระบบ: แก้ SYSTEMS ด้านล่าง
"""
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen

SYSTEMS = [
    {"key": "admit", "title": "ระบบรับสมัครเรียน", "sub": "สมัครเรียน ปวช. และ ปวส. ออนไลน์",
     "url": "https://tctatc.github.io/thaluang-admission/", "color": "#e07b00", "icon": "i-clip"},
    {"key": "mis", "title": "TLMis ระบบบริการนักเรียน นักศึกษา", "sub": "ยื่นคำร้องและดูผลการเรียน ครบในที่เดียว",
     "url": "https://tl-mis.vercel.app/login", "color": "#16924a", "icon": "i-users"},
    {"key": "sch", "title": "TL Scholarship", "sub": "ระบบบริหารจัดการและสรุปผลทุนการศึกษา",
     "url": "https://thaluangcementhaianusorn.github.io/scholarship-system/", "color": "#6b3fd1", "icon": "i-award"},
    {"key": "room", "title": "ระบบจองห้องประชุม", "sub": "จองห้อง ส่งคำขอ และอนุมัติ ครบในที่เดียว",
     "url": "https://tctatc.github.io/nasakorn-thaluang-room-booking2/#/", "color": "#0a8fb0", "icon": "i-board"},
]
CACHE_SECONDS = 10 * 60
RETRY_SECONDS = 60
FETCH_TIMEOUT = 5
_cache = {}   # (url, origin) -> (หมดอายุเมื่อ, ผล)


def clear_cache():
    _cache.clear()


def fetch_headers(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (kiosk frame check)"})
    with urlopen(req, timeout=FETCH_TIMEOUT) as r:
        return dict(r.headers.items())


def _source_allows(src: str, origin: str) -> bool:
    src = src.strip().rstrip("/")
    scheme, _, hostport = origin.partition("://")
    host = hostport.split(":")[0]
    if src == "*":
        return True
    if src.endswith(":") and "//" not in src:              # แบบ scheme อย่างเดียว เช่น https: / http:
        return src[:-1].lower() == scheme.lower()
    if "://" not in src:
        return False                                         # 'self' 'none' ฯลฯ — หน้าเราเป็นคนละ origin เสมอ
    s_scheme, _, s_hostport = src.partition("://")
    if s_scheme.lower() != scheme.lower():
        return False
    if s_hostport.endswith(":*"):
        return s_hostport[:-2].lower() == host.lower()
    return s_hostport.lower() == hostport.lower()   # ต้องตรงทั้งชื่อเครื่องและพอร์ต เช่น http://localhost:5000


def frameable(headers: dict, origin: str) -> bool:
    """หน้าที่ origin นี้ฝังเว็บที่ส่งหัวข้อ headers มาได้ไหม"""
    h = {k.lower(): v for k, v in headers.items()}
    if h.get("x-frame-options", "").strip():
        return False
    for part in h.get("content-security-policy", "").split(";"):
        words = part.split()
        if words and words[0].lower() == "frame-ancestors":
            return any(_source_allows(w, origin) for w in words[1:])
    return True


def _check(url: str, origin: str) -> bool:
    now = time.time()
    hit = _cache.get((url, origin))
    if hit and now < hit[0]:
        return hit[1]
    try:
        ok = frameable(fetch_headers(url), origin)
        _cache[(url, origin)] = (now + CACHE_SECONDS, ok)
    except Exception:
        ok = False   # เช็กไม่ได้ (เน็ตหลุด/เพิ่งบูต) → ขึ้น QR ปลอดภัยกว่าจอว่าง แล้วลองใหม่เร็ว ๆ
        _cache[(url, origin)] = (now + RETRY_SECONDS, ok)
    return ok


def systems(origin: str) -> list:
    # เช็กทุกเว็บพร้อมกัน — รอนานสุดเท่าเว็บที่ช้าที่สุด (FETCH_TIMEOUT) ไม่ใช่รวมกัน
    with ThreadPoolExecutor(max_workers=len(SYSTEMS)) as pool:
        oks = list(pool.map(lambda s: _check(s["url"], origin), SYSTEMS))
    return [{**s, "embed": ok} for s, ok in zip(SYSTEMS, oks)]
