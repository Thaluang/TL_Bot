# Kiosk News Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** แทนหน้า `/screen` ด้วยดีไซน์ v3 (นาฬิกา/อากาศ/ข่าวเด่น + แชท) และให้ครูลงข่าวพร้อมรูปผ่านหน้า `/stats` โดยข้อมูลอยู่รอดหลังรีบูต (แฟลชไดรฟ์)

**Architecture:** Flask เดิม (`robot/web/server.py`) เพิ่มโมดูล `datadir.py` (หาโฟลเดอร์ข้อมูลถาวร) และ `news.py` (คลังข่าว JSON + รูป) กับ endpoint ข่าว/แอดมิน/อากาศ
หน้าจอเป็น HTML/CSS/JS ล้วนแบบเดิม (ไม่มี build step) — `screen.html` เขียนใหม่ทั้งหน้า, `screen.js` คงตรรกะเดิม (ถามตอบ เสียง ไมค์ QR เมนู ทัวร์ ประกาศ) แต่ย้ายจุดแสดงผลเข้าเลย์เอาต์ใหม่ และเพิ่ม `news.js` คุมฝั่งซ้าย

**Tech Stack:** Python 3 + Flask + sqlite3 (มีอยู่แล้ว), urllib (อากาศ), vanilla JS, pytest

**Spec:** `docs/superpowers/specs/2026-11-10-kiosk-news-design.md` · mockup: `.superpowers/brainstorm/kiosk-news-mockup-v3.html`

## Global Constraints

- ห้ามเพิ่ม dependency Python ใหม่ (ไม่มี Pillow บน Pi) — ย่อรูปที่เบราว์เซอร์ครู: ด้านยาว ≤ 1600px, JPEG quality 0.82
- เซิร์ฟเวอร์รับรูป ≤ 3 MB และต้องขึ้นต้นด้วย magic bytes ของ JPEG/PNG/WebP
- หมวดข่าวตายตัว: `admission` รับสมัคร, `event` กิจกรรม, `scholarship` ทุนการศึกษา, `award` ผลงาน, `general` ประกาศทั่วไป
- รหัสแอดมิน: `ADMIN_PASSWORD` ใน `.env`; ว่าง = แก้ข่าวไม่ได้เลย (ตอบ 403)
- โฟลเดอร์ข้อมูล: `TLBOT_DATA_DIR` → `/media/*/*/tlbot-data` (ไดรฟ์ที่เขียนได้ตัวแรก) → `robot/data`; เก็บ `news.json`, `news/`, `stats.db`
- อากาศ: Open-Meteo, พิกัดท่าหลวง สระบุรี lat 14.53 lon 100.93 (ค่าประมาณ — คนทำปรับได้), แคช 30 นาที, timeout 5 วิ
- `IDLE_VIDEO_SECONDS = 180`; วิดีโอเล่น 1 คลิปแล้วกลับหน้าข่าว
- ข่าวชุดละ 3 สลับทุก 10 วิ; ฝั่งซ้ายกลับหน้าข่าวเองเมื่อว่าง 60 วิ
- ห้ามแตะ `/face`; เดโม `web/demo` + `build_demo.py` ต้องผ่าน `test_demo.py`
- ข้อความบนจอมีทั้งไทย/อังกฤษผ่านตาราง `T` ใน `screen.js` เหมือนเดิม

## Review Focus

- ไม่ได้เสียบแฟลชไดรฟ์ / แฟลชไดรฟ์ถอดกลางทาง → เซิร์ฟเวอร์ต้องไม่ล้ม ใช้ `robot/data` และหน้าครูขึ้นคำเตือน (`storage.persistent=false`) — เทสต์ใน Task 1, 3
- `news.json` เสีย/ว่าง (ไฟดับกลางเขียน) → โหลดได้เป็นรายการว่าง ไม่ 500; เขียนแบบไฟล์ชั่วคราวแล้ว rename — เทสต์ใน Task 2
- ข่าวข้อความยาวมาก/มี HTML → จอต้อง escape และตัดบรรทัด (หัวข้อ ≤ 80 ตัว, บรรทัดล่าง ≤ 80, รายละเอียด ≤ 1000) — เทสต์ใน Task 2
- อัปโหลดไฟล์ที่ไม่ใช่รูป / ใหญ่เกิน / id ข่าวแปลก (`../`) → 400/413, ไม่มีไฟล์หลุดนอกโฟลเดอร์ — เทสต์ใน Task 2, 3
- เน็ตหลุดตอนดึงอากาศ → `/weather` ตอบ 503 เร็ว (≤ 5 วิ) ใช้ค่าแคชเก่าถ้าอายุ < 3 ชม. — เทสต์ใน Task 3

---

### Task 1: โฟลเดอร์ข้อมูลถาวร + ย้าย stats.db

**Files:**
- Create: `robot/datadir.py`, `robot/test_datadir.py`
- Modify: `robot/config.py` (เพิ่ม `ADMIN_PASSWORD`, `IDLE_VIDEO_SECONDS = 180`), `robot/web/server.py` (stats ใช้ `DATA.path("stats.db")`), `.gitignore` (`robot/data/`)

**Interfaces:**
- Produces: `resolve_data_dir(env: dict, media_roots: list[Path], fallback: Path) -> tuple[Path, bool]` (path, persistent); `class DataDir(path: Path, persistent: bool)` มี `.path(name) -> Path`, `.persistent`; module global `DATA = DataDir(*resolve_data_dir(os.environ, [Path("/media")], ROBOT_DIR/"data"))` ใน server.py

- [ ] Step 1: เทสต์ `test_env_wins`, `test_first_writable_usb`, `test_fallback_not_persistent`, `test_skips_readonly_usb` (ใช้ tmp_path จำลอง `/media/pi/USB1`; env `TLBOT_DATA_DIR` ชนะ; fallback คืน persistent False; สร้างโฟลเดอร์ `tlbot-data` ให้)
- [ ] Step 2: รัน `python -m pytest test_datadir.py -q` → FAIL (ไม่มีโมดูล)
- [ ] Step 3: เขียน `datadir.py` (เช็กเขียนได้ด้วยการสร้าง/ลบไฟล์ทดสอบ, จับ OSError ทุกจุด)
- [ ] Step 4: เทสต์ผ่าน + `python -m pytest web -q` ยังผ่าน (fixture `temp_stats` เดิมยังใช้ได้)
- [ ] Step 5: commit

### Task 2: คลังข่าว `news.py`

**Files:**
- Create: `robot/web/news.py`, `robot/web/test_news.py`

**Interfaces:**
- Produces: `CATEGORIES: tuple[str, ...]`; `class NewsStore(folder: Path)` —
  `all() -> list[dict]`, `active(today: date) -> list[dict]`, `get(id) -> dict|None`,
  `add(fields: dict, image: bytes|None) -> dict`, `update(id, fields: dict, image: bytes|None, remove_image=False) -> dict`,
  `delete(id) -> bool`, `reorder(ids: list[str]) -> None`, `image_path(name: str) -> Path|None`, `version -> str` (เปลี่ยนทุกครั้งที่เขียน),
  `ai_text(today: date, lang: str) -> str`; ข้อผิดพลาดของข้อมูล = `NewsError(ValueError)`
- รูปแบบข่าว (JSON): `{"id","category","title","subtitle","detail","link","image","start","end","hidden","order"}` — `start/end` เป็น `"YYYY-MM-DD"` หรือ `""`, `image` เป็นชื่อไฟล์ใน `news/` หรือ `""`

- [ ] Step 1: เทสต์: เพิ่มแล้วโหลดใหม่ได้ครบ; `active` ตัดข่าวซ่อน/ยังไม่ถึง/หมดอายุ และเรียงตาม order; หมวดผิด/หัวข้อว่าง → NewsError; ตัดความยาว 80/80/1000; ลิงก์ต้องขึ้นด้วย http(s)://; รูปที่ไม่ใช่ JPEG/PNG/WebP หรือ > 3 MB → NewsError; ลบข่าวแล้วไฟล์รูปหาย; `news.json` เสีย → `all()==[]`; `image_path("../x")` → None; `reorder` เปลี่ยนลำดับ; `ai_text` มีหัวข้อ+รายละเอียดของข่าวที่ active เท่านั้น
- [ ] Step 2: รัน → FAIL
- [ ] Step 3: เขียน `news.py` (id = `uuid4().hex[:12]`, เขียน json แบบ tmp+`os.replace`, lock ด้วย threading.Lock)
- [ ] Step 4: ผ่าน
- [ ] Step 5: commit

### Task 3: endpoint ข่าว แอดมิน อากาศ + ให้ AI รู้ข่าว

**Files:**
- Modify: `robot/web/server.py`, `robot/ai.py` (`_system_text` รับข้อความข่าวเพิ่ม), `robot/web/test_server.py`

**Interfaces:**
- Consumes: Task 1 `DATA`, Task 2 `NewsStore`
- Produces (HTTP):
  - `GET /news` → `{"version", "items":[{id,category,title,subtitle,detail,link,image_url}]}` (active วันนี้)
  - `GET /news/img/<name>` → รูป (404 ถ้าไม่มี/ชื่อแปลก)
  - `POST /admin/login` `{"password"}` → 200 + cookie `tlbot_admin` (token สุ่มเก็บในหน่วยความจำ) / 401 / 403 ถ้าไม่ได้ตั้งรหัส
  - `POST /admin/logout`
  - `GET /admin/news` → `{"items": all(), "storage": {"persistent", "path"}}` (ต้อง login)
  - `POST /admin/news` (multipart: ฟิลด์ข่าว + `image`) → 201 ข่าวใหม่
  - `POST /admin/news/<id>` (multipart, `remove_image=1` ได้) → แก้ / `DELETE /admin/news/<id>` / `POST /admin/news/order` `{"ids":[...]}`
  - ไม่ login → 401; NewsError → 400; รูปใหญ่เกิน → 413
  - `GET /weather` → `{"temp","code","text_th","text_en","high","low","rain"}` / 503
- AI: ข่าวที่ active ต่อท้าย system text; คีย์แคชคำตอบรวม `news.version` (ข่าวเปลี่ยน = คำตอบเก่าใช้ไม่ได้)

- [ ] Step 1: เทสต์ (ใช้ fixture ที่ monkeypatch `server.news = NewsStore(tmp_path)` และ `config.ADMIN_PASSWORD`): login ผิด 401 / ถูกได้ cookie; ไม่มีรหัส 403; เพิ่มข่าวพร้อมรูปแล้ว `/news` เห็นและ `/news/img/...` ได้ไฟล์; ไม่ login แก้ไม่ได้ 401; ไฟล์ไม่ใช่รูป 400; ลบแล้วหาย; order ใช้ได้; `/admin/news` บอก storage; `/weather` mock `urlopen` → แปลงรหัสอากาศ 2 → "แดดสลับเมฆ"; เน็ตพัง + ไม่มีแคช → 503; แคชเก่า < 3 ชม. ยังตอบได้; คำถามหลังเพิ่มข่าวไม่ใช้คำตอบที่แคชไว้
- [ ] Step 2: FAIL
- [ ] Step 3: เขียนโค้ด (ตาราง WMO code → ข้อความไทย/อังกฤษ อย่างน้อย 0,1,2,3,45,51,61,63,65,80,95)
- [ ] Step 4: `python -m pytest web -q` ผ่านทั้งหมด
- [ ] Step 5: commit

### Task 4: หน้าครูใน `/stats`

**Files:**
- Modify: `robot/web/static/stats.html` (แถบซ้าย: สถิติ / ข่าวประชาสัมพันธ์), `robot/web/test_server.py`, `robot/web/demo/demo.js` (mock `/admin/*` ให้เดโมโชว์ได้แบบอ่านอย่างเดียว)

- [ ] Step 1: เทสต์: `/stats` มี `id="newsTab"`, `id="newsForm"`, `id="newsList"`, ฟังก์ชันย่อรูป `shrinkImage` ใน HTML
- [ ] Step 2: FAIL
- [ ] Step 3: เขียน UI ตาม mockup ภาพ 4: ฟอร์มเพิ่ม/แก้ (หมวด 5 ปุ่ม, หัวข้อ, บรรทัดล่าง, รายละเอียด, ลิงก์, รูป, วันเริ่ม/หมด), รายการพร้อมสถานะ (ขึ้นจออยู่/รอขึ้น/หมดอายุ/ซ่อน), ปุ่ม ✏️/🙈/🗑️, เรียงลำดับด้วยปุ่ม ↑↓ (แทนการลาก — แตะง่ายกว่า, คนทำเลือกเอง), จอตัวอย่างย่อ = iframe `/screen?preview=1` ย่อ 0.37, กล่อง login, แถบเตือนเมื่อ `storage.persistent=false`
- [ ] Step 4: ผ่าน
- [ ] Step 5: commit

### Task 5: จอ 1920 แบบใหม่

**Files:**
- Rewrite: `robot/web/static/screen.html`
- Create: `robot/web/static/news.js` (นาฬิกา อากาศ การ์ดข่าว แผงซ้าย)
- Modify: `robot/web/static/screen.js`, `robot/web/static/osk.js` (ผูกกับ `.chat-panel` แทน `.stage`), `robot/web/test_server.py` (เทสต์ที่อ้างโครงเก่า), `robot/web/demo/demo.js` + `build_demo.py` (mock `/news`, `/weather`; ใส่ `news.js`)

**Interfaces:**
- `news.js` เปิด `window.Board = { show(kind, html, title), home(), isHome() }` — `screen.js` เรียก `Board.show("map"|"photos"|"menu", ...)` แทนการยัดรูป/เมนูลงแชท; แตะการ์ดข่าว → `window.dispatchEvent(new CustomEvent("news-read", {detail:{text}}))` ให้ `screen.js` พูด
- คงไว้ id ที่ `screen.js`/`osk.js` ใช้: `composer`, `q`, `mic`, `chat`, `scroll`, `dockQs`, `langSeg`, `lightbox`, `tourView`, `attract`, `stopTalk`, `announce`, `announceText`; ลบ `sideQs`, `welcomeSlot`, `welcomeSub`, `themeBtn`, `quickQs` (ชิปอยู่ใน `dockQs` ตรง ๆ)

- [ ] Step 1: เทสต์: `/screen` มี `id="board"`, `id="newsGrid"`, `id="clock"`, `id="weather"`, `id="chat"`, `/static/news.js` โหลดก่อน `screen.js`, `osk.js` หลัง `screen.js`; ไม่มี `id="themeBtn"`; ชิปสมัครเรียน/หลักสูตร/แผนผัง/ที่เที่ยว + ปุ่มเมนูทั้งหมด; แก้เทสต์เก่าที่อ้าง `quickQs`
- [ ] Step 2: FAIL
- [ ] Step 3: เขียนหน้าใหม่ตาม mockup v3 (ภาพ 1–3): เลย์เอาต์ออกแบบที่ 1920×1080 แล้วย่อ/ขยายพอดีจอด้วย `transform: scale()` (เปิดบนจอเล็กยังใช้ได้); ฟอนต์สำรองเป็น system-ui; แชท: ข้อความผู้ใช้/หุ่น, ดาว, ปุ่มฟังซ้ำ, QR ลิงก์ เหมือนเดิม; คำตอบที่มี `image`/`photos` → `Board.show`; เมนูทั้งหมด = แผงซ้ายรวม แผนผัง, ทัวร์ 3 มิติ, ที่เที่ยว, ของฝาก, สาขา, คุณสมบัติ, ติดต่อ; วิดีโอ: ว่าง `after` วิ → เล่น 1 คลิป จบ/แตะ → กลับ + `newChat()`
- [ ] Step 4: `python -m pytest web -q` ผ่าน (รวม `test_demo.py`) และเปิด `http://127.0.0.1:5000/screen` บนเครื่องนี้ เช็กด้วยตา: ข่าว อากาศ ถามตอบ แผนผัง เมนู ไมค์ คีย์บอร์ดบนจอ
- [ ] Step 5: commit

### Task 6: ติดตั้งบน Pi

**Files:**
- Modify: `robot/pi_ram/start.sh` (หาแฟลชไดรฟ์ → `export TLBOT_DATA_DIR`), `robot/pi_ram/README.md`

- [ ] Step 1: เสียบแฟลชไดรฟ์ → ดูว่าเมานต์ที่ไหน (`lsblk`, `/media/pi/*`) และเขียนได้ในชื่อ pi
- [ ] Step 2: ใส่ `ADMIN_PASSWORD` ใน `/boot/firmware/tlbot/env` (เจ้าของกำหนดรหัส)
- [ ] Step 3: แพ็ก `app.tar.gz` ใหม่จาก repo (สำรองตัวเก่า), อัป `start.sh`, รีสตาร์ทแอป
- [ ] Step 4: เช็กบนเครื่องจริง: จอ 1920 ขึ้นหน้าใหม่, ลงข่าวจากคอมนี้ผ่าน `http://pi.local:5000/stats` แล้วขึ้นจอใน 1 นาที, รีบูตแล้วข่าว+สถิติยังอยู่, ไมค์/คีย์บอร์ด/QR ยังใช้ได้
- [ ] Step 5: commit
