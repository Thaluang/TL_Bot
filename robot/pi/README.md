# ติดตั้งหุ่นบน Raspberry Pi (การ์ด SD ปกติ)

> การ์ดเสีย/ปลอม (`dmesg` มี `EXT4-fs error`, ชื่อการ์ดแปลก ๆ) → ใช้โหมดรันจาก RAM ที่ [`../pi_ram/`](../pi_ram/README.md)

## ลง OS

Raspberry Pi Imager → Raspberry Pi OS (64-bit) แบบมี desktop · hostname `pi` · ผู้ใช้ `pi` · Wi-Fi · เปิด SSH

## ติดตั้ง (รันบน Pi)

```bash
# โค้ด: แตกโปรเจกต์ไว้ที่ ~/robot-briefing (บนคอมสร้างด้วย  git ls-files -z | tar --force-local --null -T - -czf app.tar.gz)
mkdir -p ~/robot-briefing && tar -xzf app.tar.gz -C ~/robot-briefing
# คีย์: ~/robot-briefing/robot/.env  (GEMINI key + ADMIN_PASSWORD — ไม่อยู่ใน git)

sudo apt-get install -y python3-flask python3-dotenv python3-serial python3-pil python3-rpi-lgpio fonts-noto-color-emoji
pip install --break-system-packages google-genai edge-tts
```

## ค่าตั้งหน้าจอ (ไฟล์ในโฟลเดอร์นี้ + ../pi_ram/)

| ไฟล์ | วางที่ Pi | ทำอะไร |
|---|---|---|
| `start.sh` | ใช้จากที่เดิม | เปิดเซิร์ฟเวอร์ + Chromium 2 จอ (รอจอครบก่อนเปิดหน้า face) |
| `robot.desktop` | `~/.config/autostart/robot.desktop` | เปิด `start.sh` ตอนบูต |
| `wf-panel-pi.ini` | `~/.config/wf-panel-pi/wf-panel-pi.ini` | taskbar อยู่จอ 1920 (HDMI-A-1) |
| `../pi_ram/labwc-rc.xml` | `~/.config/labwc/rc.xml` | ทัชไปจอ 1920, หน้าแชท → HDMI-A-1, หน้าหุ่น → HDMI-A-2 |

คีย์บอร์ดไทย (Alt+Shift): ใน `~/.config/labwc/environment` ตั้ง `XKB_DEFAULT_LAYOUT=us,th` และ `XKB_DEFAULT_OPTIONS=grp:alt_shift_toggle`

## หลังติดตั้ง

- log: `/dev/shm/tlbot.log` · ข่าว/สถิติ: แฟลชไดรฟ์ USB ถ้าเสียบ ไม่งั้น `robot/data` บนการ์ด
- อัปเดตโค้ด: แตก `app.tar.gz` ใหม่ทับ `~/robot-briefing` (ไม่ทับ `.env`) แล้ว `bash ~/robot-briefing/robot/pi/start.sh`
- ESP32 (แขน): เสียบเมื่อไรก็ได้ หุ่นต่อเองตอนจะโบก
