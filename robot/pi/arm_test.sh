#!/bin/bash
# ทดสอบแขนด้วยมือบน Pi: หยุดเซิร์ฟเวอร์ (พอร์ต ESP32 ใช้ได้ทีละโปรแกรม) → พิมพ์สั่งแขน → ออกแล้วเปิดหุ่นกลับเอง
# ใช้:  bash ~/robot-briefing/robot/pi/arm_test.sh
APP=/home/pi/robot-briefing
echo "หยุดหุ่นชั่วคราว ..."
pkill -f "[r]obot/pi/start.sh"
pkill -f "[p]ython3 server.py"
sleep 2
cd "$APP/robot/web" && python3 arm_test.py "$@"
echo "เปิดหุ่นกลับ ... (ประมาณ 1 นาที)"
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0
cd "$HOME" && setsid nohup bash "$APP/robot/pi/start.sh" >/dev/null 2>&1 < /dev/null &
