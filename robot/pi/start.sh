#!/bin/bash
# เปิดหุ่นตอนบูต (การ์ด SD ปกติ) — โค้ดอยู่ที่ /home/pi/robot-briefing, ค่าตั้ง/คีย์อยู่ใน robot/.env
# ถูกเรียกจาก ~/.config/autostart/robot.desktop · log อยู่ที่ /dev/shm/tlbot.log (RAM ไม่กินการ์ด)
# (การ์ดเสีย/ปลอม → ใช้ robot/pi_ram/start.sh ที่รันจาก RAM แทน)
APP=/home/pi/robot-briefing
LOG=/dev/shm/tlbot.log
URL="http://localhost:5000"

exec >>"$LOG" 2>&1
# เริ่มจากโฮมเสมอ — ถ้าถูกสั่งจากโฟลเดอร์ที่ถูกลบไปแล้ว Chromium โหลดค่าฟอนต์ไม่ได้ (อีโมจิกลายเป็นกล่องสี่เหลี่ยม)
cd "$HOME" || cd /
echo "=== start $(date) ==="

[ -f "$APP/robot/web/server.py" ] || { echo "ไม่เจอโค้ดที่ $APP"; exit 1; }

# ข้อมูลที่ต้องอยู่รอดหลังรีบูต (ข่าว รูปข่าว สถิติ) เก็บบนแฟลชไดรฟ์ USB
# desktop เมานต์ให้เองที่ /media/<user>/<ชื่อไดรฟ์> แต่อาจช้ากว่าสคริปต์นี้ — รอไม่เกิน 30 วินาที
# ไม่เจอ = เก็บที่ robot/data บนการ์ด SD
ME="$(id -un)"
for _ in $(seq 1 30); do
  for d in /media/"$ME"/*/; do
    [ -d "$d" ] && [ -w "$d" ] && export TLBOT_DATA_DIR="${d}tlbot-data" && break 2
  done
  sleep 1
done
# การ์ดปกติเก็บถาวรได้ → ไม่มีแฟลชไดรฟ์ก็ใช้โฟลเดอร์บนการ์ด (หน้าครูไม่ขึ้นเตือนว่า "หายเมื่อรีบูต")
if [ -z "$TLBOT_DATA_DIR" ]; then
  export TLBOT_DATA_DIR="$APP/robot/data"
  mkdir -p "$TLBOT_DATA_DIR"
fi
echo "data: $TLBOT_DATA_DIR"

# เซิร์ฟเวอร์ (ล้มเมื่อไรเปิดใหม่เอง)
# ปิดตัวเก่าที่ค้างอยู่ (กรณีรันซ้ำ)
for p in $(pgrep -f "[r]obot/pi/start.sh"); do [ "$p" != "$$" ] && kill "$p" 2>/dev/null; done
pkill -f "[p]ython3 server.py" 2>/dev/null
pkill -f "[k]iosk-screen|[k]iosk-face" 2>/dev/null
sleep 1
# PYTHONUNBUFFERED: log ของเซิร์ฟเวอร์ (เช่น [แขน] ...) ลงไฟล์ทันที ไม่ค้างในบัฟเฟอร์
( cd "$APP/robot/web" && while true; do PYTHONUNBUFFERED=1 python3 server.py; echo "server exited $?"; sleep 3; done ) &

for _ in $(seq 1 60); do
  curl -s -o /dev/null "$URL/state" && break
  sleep 1
done

BROWSER="$(command -v chromium-browser || command -v chromium)"
FLAGS="--kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble \
  --autoplay-policy=no-user-gesture-required --use-fake-ui-for-media-stream \
  --disk-cache-dir=/dev/shm/kiosk-cache --password-store=basic --ozone-platform=wayland --lang=th --disable-features=Translate,TranslateUI"

# รอ desktop (แถบ panel) ขึ้นก่อน — เปิดเร็วเกินไปหน้าต่างไม่โผล่
for _ in $(seq 1 60); do
  pgrep -x wf-panel-pi >/dev/null && break
  sleep 1
done
sleep 4

# คีย์บอร์ดบนจอ: ใช้ของในหน้าเว็บ (static/osk.js) — squeekboard ของระบบโดนหน้าต่าง kiosk เต็มจอบัง

# Wayland ไม่ฟัง --window-position → ใช้ --class เป็น app_id แล้วให้ labwc ย้ายจอ
# (กฎอยู่ใน /boot/firmware/tlbot/labwc/rc.xml: tlbot-screen → HDMI-A-2 จอสัมผัส 1920, tlbot-face → HDMI-A-1)
# รอจอหน้าหุ่นพร้อม (สูงสุด 30 วิ) — นับจอเร็วไปเจอจอเดียว หน้า face จะไม่ถูกเปิดเลย
for _ in $(seq 1 30); do
  OUTS=$(wlr-randr 2>/dev/null | grep -c '^[A-Z]')
  [ "${OUTS:-0}" -ge 2 ] && break
  sleep 1
done
echo "จอ: ${OUTS:-0}"
"$BROWSER" $FLAGS --class=tlbot-screen --user-data-dir=/dev/shm/kiosk-screen "$URL/screen" &
if [ "${OUTS:-1}" -ge 2 ]; then
  sleep 3
  "$BROWSER" $FLAGS --class=tlbot-face --user-data-dir=/dev/shm/kiosk-face "$URL/face" &
fi
wait
