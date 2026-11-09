# โหมดรันจาก RAM (Pi ที่ SD card เขียนไม่ได้)

ใช้ตอน SD card ของ Pi เสีย/ปลอม — เขียนไฟล์ใหม่ลง rootfs แล้วข้อมูลพัง
(อาการ: `ls` ขึ้น `Bad message`, `dmesg` มี `EXT4-fs error ... checksum`,
`cat /sys/block/mmcblk0/device/name` ได้ชื่อแปลกๆ เช่น `asdfg`)

แนวคิด: พาร์ทิชันบูต `/boot/firmware` (FAT ช่วงต้นการ์ด) ยังเขียนได้ปกติ
→ เก็บทุกอย่างไว้ที่ `/boot/firmware/tlbot/` แล้วให้ rootfs มีแค่ symlink ชี้มา
→ ตอนบูต `start.sh` แตกโปรเจกต์ลง `/dev/shm` (RAM) แล้วรันจากตรงนั้น

> ทางแก้ถาวรคือเปลี่ยน SD card ของแท้แล้วลง OS ใหม่ — โหมดนี้เป็นทางชั่วคราว
> ข้อมูลที่หุ่นบันทึกระหว่างใช้ (สถิติ ฯลฯ) หายเมื่อปิดเครื่อง

## ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | วางที่ Pi | symlink จาก |
|---|---|---|
| `start.sh` | `/boot/firmware/tlbot/start.sh` | — |
| `robot.desktop` | `/boot/firmware/tlbot/autostart/robot.desktop` | `~/.config/autostart` → `/boot/firmware/tlbot/autostart` |
| `labwc-rc.xml` | `/boot/firmware/tlbot/labwc/rc.xml` | `~/.config/labwc/rc.xml` |
| `wf-panel-pi.ini` | `/boot/firmware/tlbot/wf-panel-pi/wf-panel-pi.ini` | `~/.config/wf-panel-pi/wf-panel-pi.ini` |
| `hosts` | `/boot/firmware/tlbot/hosts` | `/etc/hosts` |

ไฟล์ที่ไม่อยู่ใน git ต้องใส่เอง:
- `/boot/firmware/tlbot/env` — เนื้อหาเหมือน `robot/.env` (Gemini key)
- `/boot/firmware/tlbot/app.tar.gz` — โปรเจกต์ทั้งก้อน สร้างบนคอม:
  `git ls-files -z | tar --force-local --null -T - -czf app.tar.gz`
- `/boot/firmware/tlbot/fonts/NotoColorEmoji.ttf` — ฟอนต์ emoji
  (`apt-get download fonts-noto-color-emoji` แล้ว `dpkg-deb -x` เอาไฟล์ .ttf ออกมา) + symlink `~/.fonts` → `/boot/firmware/tlbot/fonts`
- `/etc/resolv.conf` → `/run/NetworkManager/resolv.conf` (symlink)

## จอ

- `HDMI-A-2` = จอสัมผัส 1920×1080 (body) → หน้า `/screen` + taskbar
- `HDMI-A-1` = จอ 1024×600 (face) → หน้า `/face`

Wayland ไม่ฟัง `--window-position` จึงตั้ง `--class=tlbot-screen` / `--class=tlbot-face`
แล้วให้ `windowRules` ใน `labwc-rc.xml` ย้ายหน้าต่างไปจอที่ถูก
จอสัมผัส ILITEK map ไป `HDMI-A-2` ไว้ทุกพอร์ต USB (ชื่ออุปกรณ์เปลี่ยนตามพอร์ตที่เสียบ)
แก้ rc.xml แล้วโหลดใหม่: `kill -HUP $(pidof labwc)`

## อัปเดตโค้ดบน Pi

1. สร้าง `app.tar.gz` ใหม่ (คำสั่งด้านบน) แล้ว `scp` ไปที่ Pi
2. `sudo cp app.tar.gz /boot/firmware/tlbot/ && sync`
3. ตรวจว่าเขียนลงการ์ดถูก: `sudo sh -c "echo 3 > /proc/sys/vm/drop_caches"` แล้ว `cmp` กับต้นฉบับ
4. `rm -rf /dev/shm/tlbot` แล้วรีบูต (หรือรัน `start.sh` ใหม่)

log อยู่ที่ `/dev/shm/tlbot.log`
