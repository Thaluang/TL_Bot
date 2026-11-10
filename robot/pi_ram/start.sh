#!/bin/bash
# เปิดหุ่นจาก RAM — การ์ด SD ใบนี้เป็นของปลอม เขียนไฟล์ใหม่ลง rootfs แล้วพัง
# โค้ด/ค่าตั้งเก็บใน /boot/firmware/tlbot (พาร์ทิชัน FAT ช่วงต้นการ์ด ยังเขียนได้ปกติ)
# ทุกครั้งที่บูต: แตก app.tar.gz ลง /dev/shm (RAM) แล้วรันจากตรงนั้น
SRC=/boot/firmware/tlbot
APP=/dev/shm/tlbot
LOG=/dev/shm/tlbot.log
URL="http://localhost:5000"

exec >>"$LOG" 2>&1
echo "=== start $(date) ==="

if [ ! -f "$APP/robot/web/server.py" ]; then
  rm -rf "$APP"; mkdir -p "$APP"
  tar -xzf "$SRC/app.tar.gz" -C "$APP" || { echo "แตกไฟล์ไม่สำเร็จ"; exit 1; }
fi
cp "$SRC/env" "$APP/robot/.env" 2>/dev/null

# ข้อมูลที่ต้องอยู่รอดหลังรีบูต (ข่าว รูปข่าว สถิติ) เก็บบนแฟลชไดรฟ์ USB
# desktop เมานต์ให้เองที่ /media/<user>/<ชื่อไดรฟ์> แต่อาจช้ากว่าสคริปต์นี้ — รอไม่เกิน 30 วินาที
# ไม่เจอ = เซิร์ฟเวอร์เก็บใน RAM (หายเมื่อรีบูต) และหน้าครูจะขึ้นคำเตือน
ME="$(id -un)"
for _ in $(seq 1 30); do
  for d in /media/"$ME"/*/; do
    [ -d "$d" ] && [ -w "$d" ] && export TLBOT_DATA_DIR="${d}tlbot-data" && break 2
  done
  sleep 1
done
echo "data: ${TLBOT_DATA_DIR:-RAM (ไม่เจอแฟลชไดรฟ์)}"

# เซิร์ฟเวอร์ (ล้มเมื่อไรเปิดใหม่เอง)
# ปิดตัวเก่าที่ค้างอยู่ (กรณีรันซ้ำ)
for p in $(pgrep -f "[t]lbot/start.sh"); do [ "$p" != "$$" ] && kill "$p" 2>/dev/null; done
pkill -f "[p]ython3 server.py" 2>/dev/null
pkill -f "[k]iosk-screen|[k]iosk-face" 2>/dev/null
sleep 1
( cd "$APP/robot/web" && while true; do python3 server.py; echo "server exited $?"; sleep 3; done ) &

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
OUTS=$(wlr-randr 2>/dev/null | grep -c '^[A-Z]')
"$BROWSER" $FLAGS --class=tlbot-screen --user-data-dir=/dev/shm/kiosk-screen "$URL/screen" &
if [ "${OUTS:-1}" -ge 2 ]; then
  sleep 3
  "$BROWSER" $FLAGS --class=tlbot-face --user-data-dir=/dev/shm/kiosk-face "$URL/face" &
fi
wait
