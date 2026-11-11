"""
ลองคุยกับ ESP32 (แขน + คอ) จาก Windows แล้วดูทุกบรรทัดที่วิ่งไปมาตามโปรโตคอล
รันจาก robot/web:   python try_arms.py          (พอร์ตเริ่มต้น COM5)
                    python try_arms.py COM3     (ระบุพอร์ตอื่น)
ก่อนรัน: ปิด Arduino Serial Monitor (พอร์ตเปิดได้ทีละโปรแกรม) และจัดแขนห้อยตรง คอหันตรง
"""
import sys
import time

import serial                         # pip install pyserial

from stepper import ArmError, EspLink, StepperArms

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM5"

try:
    sys.stdout.reconfigure(encoding="utf-8")   # กันภาษาไทย/ลูกศรพังเวลาส่งออกไฟล์
except Exception:
    pass


class Spy(serial.Serial):
    """serial ปกติ แต่พิมพ์ทุกบรรทัดที่ส่งและรับ"""

    def write(self, b):
        print("Pi  → ESP:", b.decode().strip())
        return super().write(b)

    def readline(self):
        r = super().readline()
        if r:
            print("ESP → Pi :", r.decode(errors="replace").strip())
        return r


def main():
    print(f"เปิดพอร์ต {PORT} ...")
    link = EspLink(Spy(PORT, 115200, timeout=0.1))
    arms = StepperArms(link)
    time.sleep(1.5)                   # ESP32 รีเซ็ตตอนเปิดพอร์ต รอบูตเสร็จ
    link.sync()                       # ปิดท้ายเศษไบต์ตอนรีเซ็ต ไม่ให้ไปต่อหน้าคำสั่งแรก
    try:
        print("สถานะ:", arms.status())
        arms.zero()                   # ท่าตอนนี้ = มุม 0
        arms.move(R=30)               # ยกแขนขวา 30°
        print("ตำแหน่ง:", arms.position())
        arms.park()                   # กลับ 0 แล้วจอด
        print("เสร็จ — โปรโตคอลทำงานครบ")
    except ArmError as e:
        print("ผิดพลาด:", e)
    finally:
        link.close()


if __name__ == "__main__":
    main()
