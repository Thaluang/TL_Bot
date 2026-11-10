# แขน 2 ข้าง + คอ (สเต็ปเปอร์) ผ่าน ESP32

Raspberry Pi ตัดสินใจท่าทาง → ส่งคำสั่งทางสาย USB → ESP32 สร้างพัลส์ → TB6600 ขับ 17HS4401S
เฟิร์มแวร์: [`tl_arms/tl_arms.ino`](tl_arms/tl_arms.ino) · ฝั่ง Pi: [`../web/stepper.py`](../web/stepper.py)
สเปก: [`docs/superpowers/specs/2026-11-10-esp32-stepper-design.md`](../../docs/superpowers/specs/2026-11-10-esp32-stepper-design.md)

## ต่อสาย

```
Raspberry Pi ──USB──► ESP32 ──PUL/DIR/ENA──► TB6600 ×3 ──A+ A- B+ B-──► 17HS4401S ×3
                                               ↑ ไฟ 24V ≥5A (แยกจาก Pi)
```

| แกน | PUL+ | DIR+ | ENA+ |
|---|---|---|---|
| แขนซ้าย `L` | GPIO 25 | GPIO 26 | GPIO 13 (ร่วม 3 ตัว) |
| แขนขวา `R` | GPIO 27 | GPIO 14 | GPIO 13 |
| คอ `N` | GPIO 32 | GPIO 33 | GPIO 13 |

- `PUL-` `DIR-` `ENA-` ของ TB6600 **ทั้ง 3 ตัว** → GND ของ ESP32
- TB6600 `VCC/GND` → ไฟ 24V · `A+ A- B+ B-` → สายมอเตอร์ตามเอกสาร 17HS4401S (คู่ขดลวดเดียวกันอยู่ A หรือ B)
- DIP switch TB6600: **microstep 1/8**, **กระแส 1.5A** (ทุกตัวตั้งเหมือนกัน)
- มอเตอร์สั่น/ข้ามสเต็ป ทั้งที่สายถูก → สัญญาณ 3.3V ไม่พอ ให้เพิ่ม 74HCT245 แปลงเป็น 5V
- ถ้า ENA ทำงานกลับด้าน (สั่งล็อกแล้วมอเตอร์หลวม) → แก้ `setTorque()` ใน .ino สลับ LOW/HIGH

## แฟลชเฟิร์มแวร์

1. Arduino IDE → Boards Manager ติดตั้ง **esp32 by Espressif** → เลือกบอร์ด **ESP32 Dev Module**
2. Library Manager ติดตั้ง **AccelStepper** (Mike McCauley)
3. เปิด `tl_arms/tl_arms.ino` → ตั้งอัตราทดใน `AX[...]` ถ้ามีเฟือง/สายพาน (ต่อตรง = 1.0) → Upload
4. เปิด Serial Monitor (115200, ลงท้าย "Newline") จะเห็น `EVT BOOT fw=1.0 parked=0`

## ลองสั่งด้วยมือ (Serial Monitor)

ครั้งแรกจัดแขนห้อยตรง คอหันตรง แล้วพิมพ์ทีละบรรทัด:

```
#1 ZERO                 → #1 OK                (ท่านี้ = มุม 0)
#2 MOVE R=90 V=45       → #2 OK ... #2 DONE    (ยกแขนขวา 90°)
#3 POS?                 → #3 OK L=0.0 R=90.0 N=0.0 busy=0
#4 MOVE L=30 R=0 N=20   → ขยับ 3 ตัวพร้อมกัน ถึงพร้อมกัน
#5 PARK                 → กลับ 0 แล้วจอด (ปิดเครื่องได้)
```

> พิมพ์ช้า ๆ ระหว่างแขนหมุน ถ้าไม่มีอะไรส่งเข้าไปเกิน 3 วินาที ESP32 จะหยุดเอง (`EVT WATCHDOG`) — ปกติ Pi ส่ง `PING` ให้ทุก 1 วินาที

## ใช้จาก Pi

```python
from stepper import StepperArms
arms = StepperArms.connect()     # หา /dev/ttyUSB* เอง ไม่เจอ = โหมดจำลอง
arms.wave()                      # โบกมือขวา
arms.look(30)                    # หันคอ 30°
arms.park()                      # ก่อนปิดเครื่อง
```

## ไม่มีลิมิตสวิตช์ — หุ่นรู้มุมได้ยังไง

- `PARK` (กลับ 0 → ปลดแรงบิด) จดว่า "จอดแล้ว" ลงหน่วยความจำถาวรของ ESP32 → เปิดเครื่องครั้งหน้าใช้ได้ทันที
- ไฟดับ/ถอดปลั๊กกลางท่า → เปิดมาได้ `parked=0` ทุก `MOVE` ตอบ `ERR NOT_PARKED`
  → จัดแขนห้อยตรง คอตรง แล้วส่ง `ZERO` (หรือกดปุ่มในหน้าครู เมื่อต่อระบบแล้ว)
- ถ้ามีคนดึงแขน/แขนชน มอเตอร์อาจข้ามสเต็ป มุมจะเพี้ยนเงียบ ๆ — แก้ด้วย `PARK` แล้วจัดใหม่ + `ZERO`
