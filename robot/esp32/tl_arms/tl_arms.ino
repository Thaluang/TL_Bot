/*
  น้องทานตะวัน-Bot — เฟิร์มแวร์ ESP32 คุมสเต็ปเปอร์ 3 ตัว (แขนซ้าย L, แขนขวา R, คอ N)
  ผ่านไดรเวอร์ TB6600 รับคำสั่งจาก Raspberry Pi ทางสาย USB (Serial 115200)

  ไลบรารีที่ต้องลง (Arduino IDE → Library Manager): "AccelStepper" ของ Mike McCauley
  บอร์ด: "ESP32 Dev Module" (ติดตั้ง esp32 by Espressif ใน Boards Manager)

  โปรโตคอล (ทีละบรรทัด ลงท้าย \n):
    Pi → ESP32   #<id> PING | POS? | MOVE L=<deg> R=<deg> N=<deg> [V=<deg/s>] | STOP | EN <0|1> | ZERO | PARK
    ESP32 → Pi   #<id> OK ... | #<id> ERR <รหัส> ... | #<id> DONE | EVT <เหตุการณ์>
  ดูรายละเอียด: docs/superpowers/specs/2026-11-10-esp32-stepper-design.md
*/
#include <AccelStepper.h>
#include <Preferences.h>

#define FW_VERSION "1.0"

// ---------------- ตั้งค่าฮาร์ดแวร์ ----------------
const int PIN_ENA = 13;               // ENA+ ของ TB6600 ทั้ง 3 ตัว (ต่อแบบ common-cathode: LOW = ล็อกแรงบิด)
const float MICROSTEP = 8;            // DIP switch บน TB6600 ตั้ง 1/8
const float STEPS_PER_REV = 200 * MICROSTEP;   // 17HS4401S = 200 สเต็ป/รอบ (1.8°)

struct Axis {
  char name;
  uint8_t stepPin, dirPin;
  float gear;          // อัตราทด (มอเตอร์หมุนกี่รอบ ต่อแขนหมุน 1 รอบ) — ต่อตรง = 1.0
  float minDeg, maxDeg;
  bool invertDir;      // แขนขวาติดกลับด้าน → กลับทิศ ให้ + เป็น "ยกขึ้น" เหมือนกันทั้งสองข้าง
};

Axis AX[3] = {
  {'L', 25, 26, 1.0, -10, 180, false},   // แขนซ้าย
  {'R', 27, 14, 1.0, -10, 180, true},    // แขนขวา
  {'N', 32, 33, 1.0, -60,  60, false},   // คอ
};

const float DEFAULT_SPEED = 60;     // องศา/วินาที (ไม่ระบุ V=)
const float MAX_SPEED     = 180;    // องศา/วินาที สูงสุดที่ยอม
const float ACCEL         = 240;    // องศา/วินาที² (ออกตัว/หยุดนุ่ม)
const unsigned long WATCHDOG_MS = 3000;   // ระหว่างหมุน Pi เงียบเกินนี้ → หยุด

// ---------------- สถานะ ----------------
AccelStepper motor[3] = {
  AccelStepper(AccelStepper::DRIVER, 25, 26),
  AccelStepper(AccelStepper::DRIVER, 27, 14),
  AccelStepper(AccelStepper::DRIVER, 32, 33),
};
Preferences prefs;
bool homed = false;        // รู้ตำแหน่งจริงไหม (จอดก่อนปิดเครื่อง หรือสั่ง ZERO แล้ว)
bool nvsParked = false;    // ค่าที่จดใน NVS ตอนนี้ (ลดการเขียนซ้ำ)
long pendingId = -1;       // id ของ MOVE/PARK ที่รอส่ง DONE
bool parking = false;
unsigned long lastRx = 0;
char buf[128];
size_t bufLen = 0;

float stepsPerDeg(int i) { return STEPS_PER_REV * AX[i].gear / 360.0; }
float posDeg(int i) { return motor[i].currentPosition() / stepsPerDeg(i); }
bool anyRunning() {
  for (int i = 0; i < 3; i++) if (motor[i].distanceToGo() != 0) return true;
  return false;
}
void setTorque(bool on) { digitalWrite(PIN_ENA, on ? LOW : HIGH); }
void saveParked(bool v) {
  if (nvsParked == v) return;
  prefs.putBool("parked", v);
  nvsParked = v;
}

// ---------------- ตอบกลับ ----------------
void ok(long id, const String &extra = "") {
  Serial.printf("#%ld OK%s%s\n", id, extra.length() ? " " : "", extra.c_str());
}
void err(long id, const char *code, const String &extra = "") {
  Serial.printf("#%ld ERR %s%s%s\n", id, code, extra.length() ? " " : "", extra.c_str());
}
void failPending(const char *why) {
  if (pendingId >= 0) err(pendingId, "STOPPED", why);
  pendingId = -1;
  parking = false;
}

// เริ่มขยับทุกแกนไปเป้าหมาย (องศา) ให้ถึงพร้อมกัน: แกนที่ไกลกว่าวิ่งเร็วกว่า
void startMove(const float target[3], float speedDeg) {
  long goal[3];
  long dist[3];
  long maxDist = 0;
  for (int i = 0; i < 3; i++) {
    goal[i] = lround(target[i] * stepsPerDeg(i));
    dist[i] = labs(goal[i] - motor[i].currentPosition());
    if (dist[i] > maxDist) maxDist = dist[i];
  }
  setTorque(true);
  for (int i = 0; i < 3; i++) {
    float share = maxDist ? (float)dist[i] / maxDist : 1.0;
    motor[i].setMaxSpeed(max(1.0f, speedDeg * stepsPerDeg(i) * share));
    motor[i].setAcceleration(max(1.0f, ACCEL * stepsPerDeg(i) * share));
    motor[i].moveTo(goal[i]);
  }
}

// ---------------- คำสั่ง ----------------
bool parseNumber(const char *s, float &out) {
  char *end;
  out = strtof(s, &end);
  return end != s && *end == '\0';
}

void cmdMove(long id, char *args) {
  if (!homed) { err(id, "NOT_PARKED", "จัดแขนห้อยตรง/คอตรงแล้วส่ง ZERO ก่อน"); return; }
  float target[3] = {posDeg(0), posDeg(1), posDeg(2)};
  float speed = DEFAULT_SPEED;
  bool any = false;
  for (char *tok = strtok(args, " "); tok; tok = strtok(NULL, " ")) {
    char *eq = strchr(tok, '=');
    float v;
    if (!eq || eq == tok || !parseNumber(eq + 1, v)) { err(id, "BAD_ARG", tok); return; }
    *eq = '\0';
    if (strcmp(tok, "V") == 0) { speed = constrain(v, 1, MAX_SPEED); continue; }
    int i = -1;
    for (int k = 0; k < 3; k++) if (tok[0] == AX[k].name && tok[1] == '\0') i = k;
    if (i < 0) { err(id, "BAD_ARG", tok); return; }
    if (v < AX[i].minDeg || v > AX[i].maxDeg) {
      err(id, "LIMIT", String(tok) + "=" + String(v, 1) + " min=" + String(AX[i].minDeg, 0) + " max=" + String(AX[i].maxDeg, 0));
      return;
    }
    target[i] = v;
    any = true;
  }
  if (!any) { err(id, "BAD_ARG", "ต้องมี L= R= หรือ N= อย่างน้อย 1 แกน"); return; }
  failPending("replaced");     // คำสั่งใหม่แทนที่ท่าเดิมที่ยังไม่จบ
  saveParked(false);           // เริ่มขยับ = ไม่ได้จอดแล้ว (ไฟดับตอนนี้ ต้อง ZERO ใหม่)
  startMove(target, speed);
  pendingId = id;
  ok(id);
}

void cmdPark(long id) {
  if (!homed) { err(id, "NOT_PARKED"); return; }
  failPending("replaced");
  const float zero[3] = {0, 0, 0};
  startMove(zero, DEFAULT_SPEED);
  pendingId = id;
  parking = true;
  ok(id);
}

void handleLine(char *line) {
  if (line[0] != '#') { Serial.println("#0 ERR BAD_CMD ต้องขึ้นต้นด้วย #<id>"); return; }
  char *sp = strchr(line, ' ');
  if (!sp) { Serial.println("#0 ERR BAD_CMD"); return; }
  *sp = '\0';
  long id = atol(line + 1);
  char *cmd = sp + 1;
  char *args = strchr(cmd, ' ');
  if (args) { *args = '\0'; args++; } else { args = (char *)""; }

  if (strcmp(cmd, "PING") == 0) {
    ok(id, String("fw=") + FW_VERSION + " parked=" + (nvsParked ? 1 : 0) + " homed=" + (homed ? 1 : 0));
  } else if (strcmp(cmd, "POS?") == 0) {
    ok(id, "L=" + String(posDeg(0), 1) + " R=" + String(posDeg(1), 1) + " N=" + String(posDeg(2), 1) +
             " busy=" + (anyRunning() ? 1 : 0));
  } else if (strcmp(cmd, "MOVE") == 0) {
    cmdMove(id, args);
  } else if (strcmp(cmd, "STOP") == 0) {
    for (int i = 0; i < 3; i++) motor[i].stop();     // ชะลอแล้วหยุด
    failPending("stop");
    ok(id);
  } else if (strcmp(cmd, "EN") == 0) {
    if (strcmp(args, "0") == 0) {
      if (anyRunning()) { err(id, "BUSY"); return; }
      setTorque(false);
      ok(id);
    } else if (strcmp(args, "1") == 0) {
      setTorque(true);
      ok(id);
    } else err(id, "BAD_ARG", "EN 0 หรือ EN 1");
  } else if (strcmp(cmd, "ZERO") == 0) {
    if (anyRunning()) { err(id, "BUSY"); return; }
    for (int i = 0; i < 3; i++) motor[i].setCurrentPosition(0);
    homed = true;
    ok(id);
  } else if (strcmp(cmd, "PARK") == 0) {
    cmdPark(id);
  } else {
    err(id, "BAD_CMD", cmd);
  }
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    lastRx = millis();
    if (c == '\r') continue;
    if (c == '\n') {
      buf[bufLen] = '\0';
      if (bufLen) handleLine(buf);
      bufLen = 0;
    } else if (bufLen < sizeof(buf) - 1) {
      buf[bufLen++] = c;
    } else {
      bufLen = 0;                                    // บรรทัดยาวเกิน ทิ้ง
      Serial.println("#0 ERR BAD_CMD line too long");
    }
  }
}

// ---------------- เริ่มต้น / วนรอบ ----------------
void setup() {
  Serial.begin(115200);
  pinMode(PIN_ENA, OUTPUT);
  setTorque(false);                                  // เปิดเครื่องมา ปลดแรงบิดไว้ก่อน
  for (int i = 0; i < 3; i++) {
    motor[i].setPinsInverted(AX[i].invertDir, false, false);
    motor[i].setMinPulseWidth(5);                    // TB6600 ต้องการพัลส์ ≥ 2.5 µs
    motor[i].setCurrentPosition(0);
  }
  prefs.begin("tlarms", false);
  nvsParked = prefs.getBool("parked", false);
  homed = nvsParked;                                 // จอดไว้ก่อนปิด = รู้ตำแหน่ง (มุม 0)
  if (homed) setTorque(true);                        // ล็อกท่าจอดไว้
  lastRx = millis();
  Serial.printf("EVT BOOT fw=%s parked=%d\n", FW_VERSION, nvsParked ? 1 : 0);
}

void loop() {
  readSerial();
  for (int i = 0; i < 3; i++) motor[i].run();

  // ขยับครบทุกแกน → แจ้ง DONE (PARK: ปลดแรงบิด + จดว่าจอดแล้ว)
  if (pendingId >= 0 && !anyRunning()) {
    if (parking) {
      setTorque(false);
      saveParked(true);
      parking = false;
    }
    Serial.printf("#%ld DONE\n", pendingId);
    pendingId = -1;
  }

  // Pi เงียบระหว่างหมุน (สายหลุด/Pi ค้าง) → หยุด
  if (anyRunning() && millis() - lastRx > WATCHDOG_MS) {
    for (int i = 0; i < 3; i++) motor[i].stop();
    failPending("watchdog");
    Serial.println("EVT WATCHDOG");
    lastRx = millis();                               // แจ้งครั้งเดียว
  }
}
