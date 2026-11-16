#!/bin/bash
# ทดสอบแขนด้วยมือบน Pi: หยุดหุ่น (พอร์ต ESP32 ใช้ได้ทีละโปรแกรม) → พิมพ์สั่งแขน → ออกแล้วเปิดหุ่นกลับเอง
# เปิดได้ 3 ทาง: กด Ctrl+Alt+A บนคีย์บอร์ดที่ต่อ Pi · ไอคอน "ทดสอบแขน" บน taskbar · หรือพิมพ์
#   bash ~/robot-briefing/robot/pi/arm_test.sh
APP=/home/pi/robot-briefing
echo "หยุดหุ่นชั่วคราว ..."
pkill -f "[r]obot/pi/start.sh"
pkill -f "[p]ython3 server.py"
pkill -f "[k]iosk-screen|[k]iosk-face"     # ปิดหน้าจอหุ่นที่เต็มจอ จะได้เห็นหน้าต่างนี้
sleep 2
cd "$APP/robot/web" && python3 arm_test.py "$@"
echo "เปิดหุ่นกลับ ... (ประมาณ 1 นาที)"
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0
cd "$HOME" && setsid nohup bash "$APP/robot/pi/start.sh" >/dev/null 2>&1 < /dev/null &
# เปิดจากไอคอน/ปุ่มลัด: ค้างหน้าต่างไว้ให้อ่านผลก่อน (เปิดจาก ssh ไม่ต้องรอ)
if [ -n "$ARM_TEST_WINDOW" ]; then
  read -r -p "กด Enter เพื่อปิดหน้าต่าง " _
fi
