// จอใบหน้า: ดึงสถานะจากเซิร์ฟเวอร์มาแสดงอารมณ์ (อ่านอย่างเดียว ไม่ยุ่งเสียง/สมอง)
// ภาษาของป้ายสถานะตามที่จอเนื้อหาเลือก (เซิร์ฟเวอร์ส่ง lang มากับ /state)
const LABELS = {
  th: {
    idle: "พร้อมรับคำถาม", greeting: "สวัสดีครับ 👋", listening: "กำลังฟัง…", thinking: "กำลังคิด…",
    answering: "กำลังตอบ", error: "ขออภัย เกิดข้อผิดพลาด",
  },
  en: {
    idle: "Ready for your question", greeting: "Hello! 👋", listening: "Listening…", thinking: "Thinking…",
    answering: "Answering", error: "Sorry, something went wrong",
  },
};
const txt = document.querySelector(".status-text");
let current = null, currentLang = null;

function apply(state, lang) {
  lang = LABELS[lang] ? lang : "th";
  if (state === current && lang === currentLang) return;
  current = state; currentLang = lang;
  document.body.className = "page-face state-" + state;
  document.documentElement.lang = lang;
  if (txt) txt.textContent = LABELS[lang][state] || state;
}

async function poll() {
  try {
    const r = await fetch("/state");
    const d = await r.json();
    if (d && d.state) apply(d.state, d.lang);
  } catch (e) {
    /* เซิร์ฟเวอร์ยังไม่พร้อม ค่อยลองใหม่รอบหน้า */
  }
}

apply("idle", "th");
setInterval(poll, 250);

// ขยายหน้าหุ่นทั้งชุดให้พอดีจอ: ออกแบบไว้ราว 900×560 px → จอ 1920×1080 ขยาย ~1.9 เท่า, จอ 7" (1024×600) ~1.07 เท่า
const stage = document.querySelector(".stage");
function fit() {
  if (!stage) return;
  const k = Math.max(1, Math.min(innerWidth / 900, innerHeight / 560));
  stage.style.scale = k.toFixed(3);
}
addEventListener("resize", fit);
fit();

// กระพริบตา/ลอยเป็นพักๆ ด้วย JS แทน CSS animation วนไม่หยุด — ระหว่างนั้นหน้านิ่ง จอไม่ต้องวาดใหม่ (ประหยัด CPU/GPU ของ Pi)
const faceEl = document.querySelector(".face");
function pulseClass(cls, ms) {
  if (!faceEl) return;
  faceEl.classList.remove(cls);
  void faceEl.offsetWidth;            // รีสตาร์ท animation
  faceEl.classList.add(cls);
  setTimeout(() => faceEl.classList.remove(cls), ms);
}
function scheduleBlink() {
  setTimeout(() => {
    if (["idle", "listening", "thinking"].includes(current)) pulseClass("blink", 260);
    scheduleBlink();
  }, 3000 + Math.random() * 3000);
}
function scheduleBob() {
  setTimeout(() => {
    if (current === "idle") pulseClass("bob", 3300);
    scheduleBob();
  }, 9000 + Math.random() * 5000);
}
scheduleBlink();
scheduleBob();
