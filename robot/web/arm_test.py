"""
ทดสอบแขน/คอทีละแกนด้วยมือ — พิมพ์คำสั่งแล้ว ESP32 ขยับทันที
บน Pi ใช้ผ่าน  bash ~/robot-briefing/robot/pi/arm_test.sh  (หยุดเซิร์ฟเวอร์ให้ก่อน แล้วเปิดหุ่นกลับตอนออก)
บนคอม:        python arm_test.py COM5

คำสั่ง (องศานับจากท่าแขนห้อยตรง/คอหันตรง = 0):
  L 30      แขนซ้ายไป 30°        R 30   แขนขวาไป 30°        N 20   คอไป 20° (ติดลบ = อีกทาง)
  all 30    ทุกแกนไป 30° พร้อมกัน (คอไม่เกิน 60)
  test      ไล่ทีละแกน ซ้าย → ขวา → คอ (30° แล้วกลับ)
  wave      ท่าทักทายจริง (สองแขนยก + โบก + จอด)
  pos       ดูตำแหน่งที่ ESP32 นับได้      zero   ท่าตอนนี้ = 0 (จัดแขนห้อยตรงก่อน)
  lock      ล็อกตำแหน่ง (มอเตอร์ค้างแรงบิด แขนไม่ตก)          พิมพ์ ล็อก ก็ได้
  free      ปลดแรงบิด (หมุนแขนด้วยมือได้ — ขยับแล้วต้อง zero ใหม่)  พิมพ์ ปลด ก็ได้
  park      กลับ 0 แล้วจอด                 q      จอดแล้วออก
"""
import sys
import time

from stepper import ArmError, EspLink, StepperArms, find_port

AXES = {"L": "แขนซ้าย", "R": "แขนขวา", "N": "คอ"}
SPEED = 30   # องศา/วินาที — ช้า ๆ ดูง่าย


def run(arms: StepperArms, line: str) -> bool:
    """ทำตามคำสั่ง 1 บรรทัด — คืน False เมื่อสั่งออก"""
    parts = line.strip().split()
    if not parts:
        return True
    cmd = {"ล็อก": "LOCK", "ล็อค": "LOCK", "ปลด": "FREE"}.get(parts[0], parts[0].upper())
    if cmd == "Q":
        arms.park()
        return False
    if cmd in AXES and len(parts) == 2:
        deg = float(parts[1])
        print(f"  {AXES[cmd]} → {deg:g}° ...", flush=True)
        arms.move(**{cmd: deg}, speed=SPEED)
    elif cmd == "ALL" and len(parts) == 2:
        deg = float(parts[1])
        arms.move(L=deg, R=deg, N=max(-60.0, min(60.0, deg)), speed=SPEED)
    elif cmd == "TEST":
        for ax, name in AXES.items():
            print(f"  {time.strftime('%H:%M:%S')} {name} ({ax}) ไป 30° แล้วกลับ", flush=True)
            arms.move(**{ax: 30}, speed=SPEED)
            arms.move(**{ax: 0}, speed=SPEED)
            time.sleep(2)
    elif cmd == "WAVE":
        arms.wave()
    elif cmd == "ZERO":
        arms.zero()
    elif cmd == "LOCK":
        arms.enable(True)
        print("  ล็อกแล้ว — มอเตอร์ค้างแรงบิดไว้ที่ตำแหน่งนี้")
    elif cmd == "FREE":
        arms.enable(False)
        print("  ปลดแรงบิดแล้ว — หมุนแขนด้วยมือได้ ถ้าขยับไปจากเดิม จัดห้อยตรงแล้วพิมพ์ zero ก่อนสั่งต่อ")
    elif cmd == "PARK":
        arms.park()
    elif cmd != "POS":
        print("  ไม่รู้จักคำสั่ง — ดูรายการด้านบน")
        return True
    print("  ตำแหน่ง:", arms.position())
    return True


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()
    if not port:
        print("ไม่เจอ ESP32 — เสียบสาย USB แล้วลองใหม่")
        return
    print(f"เปิดพอร์ต {port} ...")
    link = EspLink.open(port)
    arms = StepperArms(link)
    st = arms.status()
    print("สถานะ:", st)
    if not st.get("homed"):
        print("⚠ ESP32 ไม่รู้ตำแหน่งแขน — จัดแขนห้อยตรง/คอตรง แล้วพิมพ์ zero ก่อน")
    print(__doc__.split("คำสั่ง", 1)[1])
    try:
        while True:
            try:
                line = input("แขน> ")
            except EOFError:
                line = "q"
            try:
                if not run(arms, line):
                    break
            except ArmError as e:
                print("  ESP32 ปฏิเสธ:", e)
            except ValueError:
                print("  องศาต้องเป็นตัวเลข เช่น  L 30")
    finally:
        link.close()
        print("ออกแล้ว — แขนจอดเรียบร้อย")


if __name__ == "__main__":
    main()
