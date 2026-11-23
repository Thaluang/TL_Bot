// ฟังก์ชันล้วนของหน้าแนวตั้ง (screen_v.html) — เทสต์ที่ portrait_selftest.html (web/test_portrait.py เปิดด้วย Chrome headless)
// stripEmoji: หน้าแนวตั้งห้ามมีอีโมจิ (ผู้ใช้: ดูไม่ทางการ) แต่ข้อความเดิมใน screen.js / คำตอบ AI มีอีโมจิปน → ลบทิ้งก่อนโชว์
(() => {
  // อีโมจิ + ตัวประกอบ (ตัวเลือกแบบ FE0F, ZWJ, สีผิว, ธง, keycap) — ★ (U+2605) ไม่ใช่ Extended_Pictographic จึงไม่โดน
  const EMOJI = /[\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}\u{1F3FB}-\u{1F3FF}\u{FE0F}\u{FE0E}\u{200D}\u{20E3}]/gu;
  function stripEmoji(text) {
    if (!text) return text;
    const out = String(text).replace(EMOJI, "");
    if (out === text) return text;
    // ยุบช่องว่างที่เหลือจากการลบ (ไม่แตะการขึ้นบรรทัด) แล้วตัดหัวท้ายแต่ละบรรทัด
    return out.split("\n").map((l) => l.replace(/[ \t ]{2,}/g, " ").trim()).join("\n").trim();
  }
  // ข้อความใน text node: ไม่ตัดหัวท้าย (ช่องว่างคั่นกับตัวหนา/ลิงก์ข้าง ๆ ต้องอยู่)
  function stripEmojiInline(text) {
    if (!text) return text;
    const out = String(text).replace(EMOJI, "");
    return out === text ? text : out.replace(/[ \t ]{2,}/g, " ");
  }
  window.stripEmoji = stripEmoji;
  window.stripEmojiInline = stripEmojiInline;
})();
