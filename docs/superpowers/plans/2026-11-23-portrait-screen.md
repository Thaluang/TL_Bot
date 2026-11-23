# จอสัมผัสแนวตั้ง Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** หน้าใหม่ `/screen-v` แนวตั้ง 1080×1920 หน้าตาตามม็อกอัป ใช้ระบบแชท/เสียง/ข่าวเดิมทั้งหมด และสลับหน้าจอหลักด้วยค่าเดียว

**Architecture:** `screen_v.html` คง id ทุกตัวที่ `screen.js`/`news.js`/`extras.js`/`osk.js` อ้าง แล้วโหลดสคริปต์เดิมตามลำดับเดิม
ตามด้วย `portrait.js` ที่คุมการสลับมุมมอง (หน้าแรก/แชท/แผง), ปุ่มระบบภายนอก และล้างอีโมจิ
เซิร์ฟเวอร์เพิ่มเส้นทาง `/screen-v` และค่า `SCREEN_LAYOUT` ให้ `/` กับ `/screen` เลือกหน้า

**Tech Stack:** Flask (Python 3.14, pytest), HTML/CSS/JS ล้วน (ไม่มี build), Chromium kiosk บน Raspberry Pi 5 + labwc (Wayland)

**Spec:** `docs/superpowers/specs/2026-11-23-portrait-screen-design.md` · ม็อกอัป: `docs/superpowers/specs/portrait-mockup/index.html`

## Global Constraints

- กรอบออกแบบ 1080×1920 ย่อ/ขยายพอดีจอด้วย `transform: scale` แบบ `screen.html` (จัดกลาง)
- สี: `--navy:#0a2463 --navy2:#123a8c --royal:#1d5fd6 --gold:#e8b23a --gold2:#f7d77c`; ฟอนต์ Kanit + IBM Plex Sans Thai (ลิงก์ Google Fonts เดียวกับ `screen.html`)
- **ห้ามอีโมจิในหน้าใหม่** — ไอคอนเป็น SVG symbol แบบเส้น (stroke 1.9) เหมือนม็อกอัป
- ห้าม `backdrop-filter`; แอนิเมชันตกแต่งที่วนต้องผูกกับ `body.anim-on` (เล่นเป็นช่วง) ยกเว้นนาฬิกาโคลอน
- ไม่แก้ `screen.html` และไม่เปลี่ยนพฤติกรรมของ `screen.js`/`news.js`/`extras.js` ที่หน้าเดิมใช้
- ลิงก์ระบบ (ตรงตามสเปก):
  - สมัครเรียน `https://tctatc.github.io/thaluang-admission/`
  - TLMis `https://tl-mis.vercel.app/login` (`embed:false` — ห้ามเปิด iframe)
  - ทุน `https://thaluangcementhaianusorn.github.io/scholarship-system/`
  - จองห้อง `https://tctatc.github.io/nasakorn-thaluang-room-booking2/#/`
  - เว็บวิทยาลัย (QR ท้ายจอ) `https://www.tl.ac.th`
- รันเทสต์จากโฟลเดอร์ `robot/`: `py -m pytest web/test_server.py -v`
- รันเซิร์ฟเวอร์ทดสอบบนเครื่อง: `run_web.bat` (หรือ `py web/server.py` จาก `robot/`) แล้วเปิด `http://localhost:5000/screen-v`
- จับภาพตรวจ: `"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --hide-scrollbars --virtual-time-budget=6000 --window-size=1080,1920 --screenshot=<ไฟล์.png> <URL>`

## Review Focus

1. **ข่าวว่าง/ข่าวไม่มีรูป** — แผงข้อมูลพื้นฐานต้องไม่ว่างโล่งหรือโชว์อีโมจิ (`news.js` ใส่ 🎓 ✦ ฿ ★ 📢 ในการ์ดไม่มีรูป) → Task 4 ตรวจด้วยภาพ + Task 3 ตัวล้างอีโมจิครอบ `#newsGrid`
2. **คำตอบ AI/ข้อความเดิมมีอีโมจิ** (`intro`, `seeLeft`, แบบประเมิน 🙏, ป้าย 🎤, ไอคอนแผง) → Task 3 เทสต์ `stripEmoji`
3. **หมดเวลาว่างตอนเปิดเว็บภายนอก/แผงอยู่** — ต้องกลับหน้าแรกสะอาด (ไม่มีแผงค้าง ไม่มีแชทเก่า) → Task 3 ห่อ `newChat`, ตรวจมือใน Task 5
4. **แตะรัวระหว่างหุ่นกำลังคิด/พูด** — ปุ่มเมนูหน้าแรกต้องไม่ทำให้แชทสองคำถามซ้อน (`screen.js` กันด้วย `busy()` อยู่แล้ว ปุ่มที่เป็น `data-q` ต้องผ่านตัวจัดการเดิม) → Task 3 ใช้ `data-q`/`data-action` เดิม ไม่เรียก `ask` ตรง
5. **คีย์บอร์ดบนจอเปิดอยู่ตอนสลับมุมมอง** — `osk.js` ต้องไม่ค้างทับหน้าแรก → Task 4 ตรวจมือ: เปิดคีย์บอร์ดแล้วกด "หน้าแรก"

---

### Task 1: เส้นทาง `/screen-v` + ค่า `SCREEN_LAYOUT`

**Files:**
- Modify: `robot/config.py` (ใกล้ `WEB_PORT`)
- Modify: `robot/web/server.py:125-128` (`screen_page`)
- Create: `robot/web/static/screen_v.html` (โครงว่างพอให้เทสต์ผ่าน — Task 2 เติม)
- Test: `robot/web/test_server.py`

**Interfaces:**
- Produces: `config.SCREEN_LAYOUT: str` = `"landscape"` (ค่าเริ่ม) หรือ `"portrait"`; `GET /screen-v` → `screen_v.html`; `GET /` และ `/screen` → `screen_v.html` เมื่อ `SCREEN_LAYOUT == "portrait"` นอกนั้น `screen.html`

- [ ] **Step 1: เขียนเทสต์ที่ล้ม**

```python
def test_screen_v_route_serves_portrait_page():
    c = make_client()
    r = c.get("/screen-v")
    assert r.status_code == 200
    assert b'data-layout="portrait"' in r.data

def test_screen_layout_switch(monkeypatch):
    c = make_client()
    monkeypatch.setattr(server.config, "SCREEN_LAYOUT", "portrait")
    assert b'data-layout="portrait"' in c.get("/screen").data
    assert b'data-layout="portrait"' in c.get("/").data
    monkeypatch.setattr(server.config, "SCREEN_LAYOUT", "landscape")
    assert b'data-layout="portrait"' not in c.get("/screen").data
```
(ถ้า `server.py` ไม่ได้ import `config` เป็นโมดูล ให้ปรับ monkeypatch ตามวิธีที่ server อ่านค่า — ต้องอ่านค่าตอนเรียก ไม่ใช่ตอน import)

- [ ] **Step 2:** `py -m pytest web/test_server.py -k "screen_v or layout_switch" -v` → FAIL (404 / ไม่มี marker)
- [ ] **Step 3:** เพิ่ม `SCREEN_LAYOUT = "landscape"` ใน `config.py` พร้อมคอมเมนต์ไทยบอกวิธีสลับ; เพิ่ม `@app.get("/screen-v")`; ให้ `screen_page()` เลือกไฟล์ตาม `SCREEN_LAYOUT` ณ ตอนเรียก; สร้าง `screen_v.html` ขั้นต่ำที่มี `<html lang="th" data-layout="portrait">`
- [ ] **Step 4:** รันเทสต์ทั้งไฟล์ `py -m pytest web/test_server.py -v` → ผ่านทั้งหมด (รวมเทสต์ `/screen` เดิม)
- [ ] **Step 5:** commit `feat: เส้นทาง /screen-v และค่า SCREEN_LAYOUT สลับหน้าจอหลัก`

---

### Task 2: `screen_v.html` — หน้าแรกตามม็อกอัป + id ที่สคริปต์เดิมต้องใช้

**Files:**
- Modify: `robot/web/static/screen_v.html`
- Test: `robot/web/test_server.py`

**Interfaces:**
- Consumes: Task 1
- Produces (Task 3/4 ใช้):
  - มุมมอง: `body.view-home` / `body.view-chat`; แผงของหน้าใหม่ `#pvInfo` (ข้อมูลพื้นฐาน, มี `#newsGrid` + `#pager` + ปุ่มย่อย 8 อัน), `#pvMore` (เมนูอื่นๆ), `#pvWeb` (แถบบน `#pvWebTitle` `#pvWebSub` `#pvWebIcon` + ปุ่ม `data-pv="home"`), `#pvQr` (แผง QR สำหรับระบบ `embed:false`: `#pvQrTitle` `#pvQrSub` `#pvQrBox` `#pvQrUrl`)
  - ปุ่มหน้าแรก: `data-pv="info"`, `data-pv-sys="admit|mis|sch|room"`, `data-action="campusTour"`, `data-pv="chat"`, `data-pv="more"`, คู่มือ `data-action="showGuide" data-img="/static/guides/user-guide.jpg" data-msg="guideMsg"`, แบบประเมิน `data-action="showSurvey"`
  - ปุ่มย่อยข้อมูลพื้นฐาน: `data-action="showCalendar"`, `data-action="showGallery"`, `data-q="ประวัติความเป็นมาของวิทยาลัย"`, `data-q="เปิดสอนสาขาอะไรบ้าง"`, `data-q="วิทยาลัยมีผลงานและรางวัลอะไรบ้าง"`, `data-action="showMap"`, `data-action="showDirectors"`, `data-q="ติดต่อวิทยาลัยได้ช่องทางไหนบ้าง"`
  - ปุ่มเมนูอื่นๆ: `data-menu="trips|food|cafe|stay|market|souvenirs"` พร้อม `data-q` เดียวกับ `#allMenuTpl` ใน `screen.html`
  - ปุ่มกลับหน้าแรกทุกที่: `data-pv="home"`; หน้าแชทมีปุ่ม `data-action="newChat"` ด้วย

- [ ] **Step 1: เขียนเทสต์ที่ล้ม**

```python
REQUIRED_IDS = ["chat", "scroll", "composer", "q", "mic", "stopTalk", "allMenuTpl", "announce", "announceText",
    "attract", "vidProg", "tourView", "lightbox", "net", "clock", "hello", "today", "weather", "topRow", "wxIcon",
    "wxTemp", "wxText", "newsGrid", "pager", "home", "board", "boardIcon", "boardTitle", "boardSub", "boardBody",
    "boardAuto", "pvInfo", "pvMore", "pvWeb", "pvQr"]

def test_screen_v_has_all_ids_scripts_need():
    html = make_client().get("/screen-v").get_data(as_text=True)
    for i in REQUIRED_IDS:
        assert f'id="{i}"' in html, i
    assert 'class="led-text"' in html

def test_screen_v_script_order():
    html = make_client().get("/screen-v").get_data(as_text=True)
    order = ["/static/vendor/qrcode.js", "/static/news.js", "/static/screen.js", "/static/extras.js", "/static/osk.js",
             "/static/portrait_util.js", "/static/portrait.js"]
    pos = [html.index(s) for s in order]
    assert pos == sorted(pos)

def test_screen_v_has_no_emoji():
    import re
    html = make_client().get("/screen-v").get_data(as_text=True)
    assert not re.search(r"[\U0001F300-\U0001FAFF☀-➿]", html)
```
(ลำดับห้าตัวแรกตรงกับ `screen.html:558-562`; `screen.html` มีสคริปต์ inline ที่ `:547` ย่อ/ขยายกรอบ — หน้าใหม่ทำแบบเดียวกันกับกรอบ 1080×1920)

- [ ] **Step 2:** รันเทสต์ 3 ตัว → FAIL
- [ ] **Step 3:** เขียน `screen_v.html` จากม็อกอัป (`docs/superpowers/specs/portrait-mockup/index.html`):
  - คัด CSS/SVG sprite/หุ่น/หัวกรอบสี/ปุ่ม 8 ปุ่ม/ปุ่มคู่มือ-แบบประเมิน/ท้ายจอ มาตรงๆ เปลี่ยนเหตุการณ์คลิกจาก mock เป็น attribute ข้างบน
  - การ์ดเวลา: `#clock`, `#today` (และ `#hello` ซ่อนไว้หรือใช้เป็นบรรทัด kick); การ์ดอากาศ: `#weather` > `svg#wxIcon` (viewBox `0 0 120 120` แบบเดิม), `#wxTemp`, `#wxText`; ห่อทั้งสองด้วย `#topRow`
  - `#home` = ห่อเนื้อหาหน้าแรก; `#board` + ส่วนประกอบ `board*` ตามโครง `screen.html` (ปุ่มกลับ `data-action="boardHome"`)
  - ส่วนแชท (`#chat` ใน `#scroll`, `#composer`/`#q`, `#mic` พร้อม span `.when-idle/.when-listen`, `#stopTalk`, `#net` + `.led-text`, `.osk-host`) อยู่ในส่วน `#pvChat` ตามหน้าแชทของม็อกอัป
  - คง `#allMenuTpl`, `#lightbox`, `#tourView` (iframe + ปุ่ม `data-action="closeTour"`), `#attract`, `#announce` แบบเดียวกับ `screen.html` แต่ข้อความไม่มีอีโมจิ
  - QR ท้ายจอวาดด้วยสคริปต์ใน Task 3 (`#siteQr`)
- [ ] **Step 4:** รัน `py -m pytest web/test_server.py -v` → ผ่านทั้งหมด
- [ ] **Step 5:** เปิดเซิร์ฟเวอร์แล้วจับภาพ `http://localhost:5000/screen-v` → เทียบกับ `docs/superpowers/specs/portrait-mockup/home.png`: ไม่มีข้อความถูกตัด ไม่ล้นจอ เวลา/อากาศจริงขึ้น (อากาศไม่มีเน็ต = ซ่อนได้)
- [ ] **Step 6:** commit `feat: หน้าแนวตั้ง screen_v.html ตามม็อกอัป`

---

### Task 3: `portrait.js` — สลับมุมมอง, ระบบภายนอก, ล้างอีโมจิ

**Files:**
- Create: `robot/web/static/portrait.js`
- Create: `robot/web/static/portrait_util.js` (ฟังก์ชันล้วน โหลดก่อน `portrait.js`)
- Create: `robot/web/static/portrait_selftest.html` (โหลด `portrait_util.js` แล้วเขียนผล `PASS`/`FAIL: ...` ลง `<body>`)
- Test: `robot/web/test_portrait.py` — เครื่องนี้ไม่มี Node; เทสต์ Python เรียก Chrome headless `--dump-dom` เปิด `portrait_selftest.html` แบบ `file://` แล้วตรวจว่ามี `PASS` (ข้ามด้วย `pytest.skip` ถ้าไม่พบ Chrome ที่ `C:/Program Files/Google/Chrome/Application/chrome.exe` หรือ `chromium` ใน PATH)

**Interfaces:**
- Consumes: id/attribute จาก Task 2; ฟังก์ชันส่วนกลางของ `screen.js`: `openTour(src)`, `closeTour()`, `newChat()`, `stopSpeech()`, `cancelMic()`, ตาราง `T`; `window.Board` (`show/home/isHome`) จาก `news.js`; `qrcode()` จาก vendor
- Produces:
  - `portrait_util.js`: `window.stripEmoji(text: string) -> string` (ลบ Extended_Pictographic, ตัวแปร FE0F, ZWJ, สีผิว, ธง และยุบช่องว่างซ้อน/ตัดหัวท้าย; ไม่แตะตัวอักษรไทย/ตัวเลข/★ ที่ใช้เป็นดาว — ★ U+2605 ไม่ใช่ Extended_Pictographic แต่ให้มีเทสต์กันไว้)
  - `window.Portrait = { view(name: "home"|"chat"), openSystem(key: string), home() }`
  - `SYSTEMS` (ใน `portrait.js`): `{ admit, mis, sch, room }` แต่ละตัว `{ title, sub, url, color, icon, embed }` ค่าตาม Global Constraints

- [ ] **Step 1: เขียนเทสต์ที่ล้ม** — `portrait_selftest.html` ตรวจคู่ค่าเหล่านี้ (เข้า → ต้องได้):

| เข้า | ได้ |
|---|---|
| `"สวัสดีครับ 👋 วันนี้"` | `"สวัสดีครับ วันนี้"` |
| `"🎤 พูด"` | `"พูด"` |
| `"ขอบคุณ 🙏🏽"` | `"ขอบคุณ"` |
| `"ดูทางซ้าย 👈"` | `"ดูทางซ้าย"` |
| `"⚙️ ภาพรวม"` | `"ภาพรวม"` |
| `"โทร 0-3628-1295"` | `"โทร 0-3628-1295"` |
| `"★★★"` | `"★★★"` |

และ `web/test_portrait.py::test_strip_emoji_selftest` เปิดหน้านั้นด้วย Chrome headless แล้ว `assert "PASS" in dom`

- [ ] **Step 2:** `py -m pytest web/test_portrait.py -v` → FAIL (ยังไม่มี `stripEmoji`)
- [ ] **Step 3:** เขียน `stripEmoji` → เทสต์ผ่าน
- [ ] **Step 4:** เขียน `portrait.js`:
  - `view(name)`: สลับ `body.view-home/view-chat`; ปิด `#pvInfo/#pvMore/#pvQr/#pvWeb`
  - MutationObserver บน `#chat`: มี `.msg.user` เพิ่ม → `view("chat")`; ข้อความ/โหนดที่เพิ่มใน `#chat`, `#board`, `#newsGrid`, `#announce` → ล้างอีโมจิในโหนดข้อความด้วย `stripEmoji` (ข้าม `.stars`)
  - เขียนทับ `T.th` ที่มีอีโมจิเป็นข้อความเดิมผ่าน `stripEmoji` ทั้งตาราง ตอนโหลด (ก่อนผู้ใช้แตะอะไร) แล้วเรียก `applyLang("th")` ซ้ำ
  - ห่อ `newChat`: `const orig = window.newChat; window.newChat = function () { orig(); Portrait.home(); }` — `home()` = ปิดแผงทั้งหมด, `closeTour()`, `view("home")`
  - คลิก `data-pv="info|more"` → เปิดแผงนั้น; `data-pv="chat"` → `view("chat")`; `data-pv="home"` → `stopSpeech(); cancelMic(); home()` (ไม่ล้างแชท)
  - คลิก `data-pv-sys` → `openSystem(key)`: `embed` จริง → ตั้งแถบ `#pvWeb` (ชื่อ/สี/ไอคอน) แล้ว `openTour(url)`; `embed:false` → วาด QR ลง `#pvQrBox` และเปิด `#pvQr`
  - แผงข้อมูลพื้นฐาน/เมนูอื่นๆ: ปุ่มย่อยที่เป็น `data-q`/`data-action`/`data-menu` ปล่อยให้ตัวจัดการของ `screen.js` ทำ แล้วปิดแผงของหน้าใหม่ (ฟังคลิกแบบ bubble ที่ `document` หลังตัวของ `screen.js`)
  - `Board.show` ตอน `view-home` → `#board` เป็นแผงซ้อนเต็มจอ; ตอน `view-chat` → ครึ่งบนหน้าแชท (ทำด้วย CSS ใน Task 4 — สคริปต์ไม่ต้องทำอะไรเพิ่ม)
  - วาด QR เว็บวิทยาลัยลง `#siteQr`
- [ ] **Step 5:** เปิด `/screen-v` ใน Chrome ปกติ แล้วไล่กดตามตาราง:

| กด | ต้องเห็น |
|---|---|
| ปุ่ม 7 | หน้าแชท มีข้อความทักทายไม่มีอีโมจิ |
| พิมพ์ "สมัครเรียนยังไง" ส่ง | คำตอบไหล ไม่มีอีโมจิ ปุ่ม "หน้าแรก" กลับได้ |
| ปุ่ม 1 → ข่าว | หน้าแชท + หุ่นอ่านข่าว + รูปข่าวที่ครึ่งบน |
| ปุ่ม 1 → แผนผัง | แผนผังในแผง + ข้อความในแชท |
| ปุ่ม 2 | เว็บสมัครเรียนเต็มจอ แถบบนสีส้ม ปุ่มกลับหน้าแรกใช้ได้ |
| ปุ่ม 3 | แผง QR ของ TLMis (ไม่มี iframe) |
| ปุ่ม 8 → ที่เที่ยว | เมนูที่เที่ยวในแผง เลือกถึงรายละเอียดได้ |
| คู่มือ / แบบประเมิน | รูปคู่มือ / ฟอร์มประเมินในแผง |
| รอเกินเวลา `IDLE_VIDEO_SECONDS` | กลับหน้าแรก แชทว่าง แล้ววิดีโอหน้ารอ |

- [ ] **Step 6:** commit `feat: portrait.js สลับมุมมอง เปิดระบบภายนอก และล้างอีโมจิ`

---

### Task 4: CSS หน้าแชท แผง board และการ์ดข่าวในแนวตั้ง

**Files:**
- Modify: `robot/web/static/screen_v.html` (บล็อก `<style>`)

**Interfaces:**
- Consumes: Task 2–3 (class `view-*`, แผง `pv*`), class ที่สคริปต์เดิมสร้าง: `.msg.user/.bot`, `.a-body`, `.md-*`, `.link-card`, `.rate`, `.typing`, `.live`, `.tools .replay`, `.see-left`, `.nc` (`.portrait/.landscape/.textonly/.invite`), `.menu-grid/.menu-btn/.menu-list/.menu-item/.place-card/.gallery/.board-img`, ส่วนของ `extras.js` (ปฏิทิน/คลังภาพ/แบบประเมิน), `.osk*` ของ `osk.js`, สถานะ `body.state-*`, `body.osk-open`

- [ ] **Step 1:** คัดสไตล์ที่จำเป็นของคลาสข้างบนจาก `screen.html` มาปรับสี/ฟอนต์ให้เข้าธีมน้ำเงิน-ทอง ขนาดอ่านง่ายบนจอตั้ง (ข้อความแชท ≥ 28px) ซ่อน `#boardIcon` (เป็นอีโมจิ) แทนด้วยไอคอน SVG คงที่
- [ ] **Step 2:** `#board` ตอน `body.view-chat` = ส่วนบนของหน้าแชท สูงราว 45% (แชทหดลง); ตอน `body.view-home` = แผงซ้อนเต็มจอมีพื้นหรี่
- [ ] **Step 3:** การ์ดข่าวใน `#newsGrid` 2×2 ตามม็อกอัป ซ่อน `.nc .big` (อีโมจิ) และ `.tapme`; การ์ด `invite` (ไม่มีข่าว) ดูเรียบร้อย
- [ ] **Step 4:** คีย์บอร์ด `osk.js` อยู่ล่างจอเต็มกว้าง ตอน `body.osk-open` ช่องพิมพ์ไม่ถูกบัง; กดกลับหน้าแรกตอนคีย์บอร์ดเปิด → คีย์บอร์ดปิด (ถ้าไม่ปิดเอง ให้ `home()` ใน `portrait.js` เอา focus ออกจาก `#q`)
- [ ] **Step 5:** จับภาพ 4 สถานะด้วย Chrome headless (หน้าแรก, แชทมีคำตอบ+รูป, แผงข้อมูลพื้นฐาน, แผงเมนูอื่นๆ) + ไล่ตาราง Task 3 Step 5 ซ้ำ → ไม่มีอะไรล้น ไม่มีอีโมจิ
- [ ] **Step 6:** `py -m pytest web/test_server.py -v` ผ่าน → commit `style: หน้าแชท แผง และการ์ดข่าวแนวตั้ง`

---

### Task 5: บน Pi — หมุนจอสัมผัส, สัมผัสตรงจุด, เปิดหน้าแนวตั้ง

**Files:**
- Modify: `robot/pi/start.sh` (ก่อนเปิดเบราว์เซอร์)
- Modify: `/boot/firmware/tlbot/labwc/rc.xml` บน Pi (สำเนาในโปรเจกต์: `robot/pi_ram/labwc-rc.xml` ถ้ายังใช้ — ตรวจก่อนว่าไฟล์ไหนคือของจริง)
- Modify: `robot/config.py` → `SCREEN_LAYOUT = "portrait"` (เฉพาะตอน deploy วันซ้อม/วันแข่ง)

**Interfaces:**
- Consumes: Task 1–4 deploy แล้ว
- Produces: ตัวแปร `SCREEN_ROTATE` ใน `start.sh` (ค่า `90`/`270`/`normal`, ค่าเริ่ม `normal`) หมุน HDMI-A-2 ด้วย `wlr-randr --output HDMI-A-2 --transform $SCREEN_ROTATE`

- [ ] **Step 1:** ต้องเสียบจอสัมผัสก่อน — `ssh pi@pi.local 'WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000 wlr-randr'` ต้องเห็น HDMI-A-2
- [ ] **Step 2:** ลองหมุนสดด้วย `wlr-randr --output HDMI-A-2 --transform 90` ดูด้วยตาว่าทิศถูก (ไม่ถูกลอง `270`)
- [ ] **Step 3:** ใน `rc.xml` เพิ่ม `<touch deviceName="<ชื่อจากlibinput list-devices>" mapToOutput="HDMI-A-2" />` แล้ว `labwc --reconfigure` → แตะมุมทั้ง 4 ของจอตรงจุด
- [ ] **Step 4:** ใส่ `SCREEN_ROTATE` ใน `start.sh` + deploy โค้ดไป `~/robot-briefing` (ตามความจำ: deploy ตรง, sudo ไม่ต้องใส่รหัส) + ตั้ง `SCREEN_LAYOUT = "portrait"` → รีบูต → จอขึ้นหน้าแนวตั้งเองหลังบูต
- [ ] **Step 5:** ไล่ตาราง Task 3 Step 5 บนจอจริงด้วยนิ้ว + ไมค์จริง + วัด CPU ตอนว่าง (`top`) ไม่ควรเกินราว 15%
- [ ] **Step 6:** commit `feat(pi): หมุนจอสัมผัสเป็นแนวตั้ง`

---

### Task 6 (ตรวจสอบ): คีย์บอร์ดในเว็บที่ฝัง + ล้างข้อมูลล็อกอิน

ทำบน Pi หลัง Task 5 — ผลลัพธ์คือข้อสรุปและการแก้ที่เล็กที่สุดที่ใช้ได้จริง ถ้าไม่ได้ในเวลาที่มี ใช้ทางสำรองท้ายข้อ

- [ ] **Step 1 คีย์บอร์ด:** ลอง `wvkbd-mobintl` (ติดตั้ง `sudo apt install wvkbd`) ให้ลอยทับ kiosk ตอนแตะช่องพิมพ์ใน iframe (ดูว่าตอบสนอง text-input ของ Wayland ไหม — Chromium ต้องมี `--enable-wayland-ime`) หรือ squeekboard ที่ตั้งเป็น layer overlay
  - **ทางสำรอง:** ระบบที่ต้องพิมพ์ (สมัครเรียน, จองห้อง) แสดง QR คู่กับเว็บบนแถบบน "สแกนกรอกในมือถือสะดวกกว่า" — ตั้ง `embed:true` แต่มี QR ในแถบ `#pvWeb` เสมอ
- [ ] **Step 2 ล้างข้อมูลล็อกอิน:** ลองเปิด Chromium ด้วย `--remote-debugging-port=9222` (ผูก localhost) แล้วให้เซิร์ฟเวอร์เรียก CDP `Storage.clearDataForOrigin` ของ 4 โดเมนตอน `home()`/หมดเวลา (เพิ่ม `POST /kiosk/clear` ที่ `portrait.js` เรียก)
  - **ทางสำรอง:** ตอนหมดเวลาว่าง ให้ `start.sh`/เซิร์ฟเวอร์รีสตาร์ตหน้าต่าง kiosk (`--user-data-dir` อยู่ใน `/dev/shm` ลบแล้วเปิดใหม่ = สะอาด)
- [ ] **Step 3:** ทดสอบ: ล็อกอินระบบจองห้อง → กดหน้าแรก → เปิดใหม่ ต้องไม่ล็อกอินค้าง
- [ ] **Step 4:** commit สิ่งที่เลือก + บันทึกผลลงสเปก (หัวข้อ "งานตรวจสอบบน Pi")

---

### Task 7: ซ้อมแบบกรรมการ + ล็อกโค้ด

- [ ] **Step 1:** ไล่ตาราง Task 3 Step 5 ครบบนหุ่นจริง 3 รอบ (เน็ตดี, เน็ตช้า/ปิด Wi-Fi ระหว่างตอบ, ปล่อยว่างจนเข้าวิดีโอ)
- [ ] **Step 2:** ทดสอบสลับกลับ `SCREEN_LAYOUT = "landscape"` → หน้าเดิมทำงานปกติ (แผนสำรองวันแข่ง) แล้วสลับกลับ portrait
- [ ] **Step 3:** `py -m pytest web -q` ผ่านทั้งหมด → merge `feat/portrait-screen` เข้า `main`
- [ ] **Step 4:** หลังจากนี้ถึงวันแข่ง แก้เฉพาะบั๊ก
