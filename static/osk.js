// คีย์บอร์ดบนจอ (ไทย/อังกฤษ) ในหน้าเว็บเอง — หน้าแชทเปิดแบบเต็มจอ (kiosk) คีย์บอร์ดของระบบโดนบัง
// ขึ้นเมื่อแตะช่องพิมพ์ด้วยนิ้ว (คลิกเมาส์บนคอมไม่ขึ้น) หรือเปิดหน้าด้วย ?osk=1 ให้ขึ้นทุกครั้ง
// อยู่ใน .osk-host (แถวล่างสุดของจอ เต็มความกว้าง) → ตอนเปิด แชทกับฝั่งซ้ายหดขึ้นเอง ช่องพิมพ์ไม่โดนบัง
// ช่องพิมพ์อื่นที่ใส่ data-osk (เช่น ข้อเสนอแนะในแบบประเมิน) ใช้คีย์บอร์ดนี้ได้ด้วย — ปุ่ม "ส่ง" ของช่องพวกนั้น = ซ่อนคีย์บอร์ด
(() => {
  const main = document.getElementById("q");
  const composer = document.getElementById("composer");
  const stage = document.querySelector(".osk-host") || document.querySelector(".stage");
  if (!main || !composer || !stage) return;
  let input = main;   // ช่องที่กำลังพิมพ์อยู่
  const TARGET = "#q, [data-osk]";

  const ALWAYS = /[?&]osk=1/.test(location.search);
  const MARK = /[ัิ-ฺ็-๎]/;   // สระบน/ล่าง วรรณยุกต์ — ป้ายปุ่มใส่ ◌ ให้อ่านออก

  // แป้นไทยแบบเกษมณี (ตัดตัวเลิกใช้ ฃ ฅ) / แป้นอังกฤษ QWERTY — [ปกติ, กด Shift]
  const LAYOUTS = {
    th: [
      ["ๅ/-ภถุึคตจขช", "+๑๒๓๔ู฿๕๖๗๘๙"],
      ["ๆไำพะัีรนยบล", '๐"ฎฑธํ๊ณฯญฐ,'],
      ["ฟหกดเ้่าสวง", "ฤฆฏโฌ็๋ษศซ."],
      ["ผปแอิืทมใฝ", "()ฉฮฺ์?ฒฬฦ"],
    ],
    en: [
      ["1234567890", "!@#$%&*()?"],
      ["qwertyuiop", "QWERTYUIOP"],
      ["asdfghjkl", "ASDFGHJKL"],
      ["zxcvbnm", "ZXCVBNM"],
    ],
  };
  const WORDS = {
    th: { space: "เว้นวรรค", send: "ส่ง", done: "เสร็จ", other: "ABC", hide: "ซ่อนคีย์บอร์ด" },
    en: { space: "space", send: "Send", done: "Done", other: "ไทย", hide: "Hide keyboard" },
  };

  let lang = document.documentElement.lang === "en" ? "en" : "th";
  let shift = false, open = false;

  const el = document.createElement("div");
  el.id = "osk";
  el.className = "osk";
  el.setAttribute("aria-hidden", "true");
  stage.appendChild(el);

  function keyBtn(label, cls, data) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "k" + (cls ? " " + cls : "");
    b.textContent = label;
    Object.assign(b.dataset, data);
    return b;
  }

  function render() {
    const w = WORDS[lang];
    el.innerHTML = "";
    LAYOUTS[lang].forEach((row, i) => {
      const r = document.createElement("div");
      r.className = "osk-row";
      if (i === 3) r.appendChild(keyBtn("⇧", "fn ico" + (shift ? " on" : ""), { act: "shift" }));
      for (const ch of row[shift ? 1 : 0]) r.appendChild(keyBtn(MARK.test(ch) ? "◌" + ch : ch, "", { ch }));
      if (i === 3) r.appendChild(keyBtn("⌫", "fn ico", { act: "back" }));
      el.appendChild(r);
    });
    const r = document.createElement("div");
    r.className = "osk-row";
    r.appendChild(keyBtn(w.other, "fn", { act: "lang" }));
    r.appendChild(keyBtn(w.space, "space", { ch: " " }));
    r.appendChild(keyBtn("⌄", "fn ico", { act: "hide", label: w.hide }));
    r.appendChild(keyBtn((input === main ? w.send : w.done) + " ↵", "send", { act: "enter" }));   // ช่องอื่น (ข้อเสนอแนะ) = ปิดคีย์บอร์ด
    el.appendChild(r);
  }

  function changed() { input.dispatchEvent(new Event("input", { bubbles: true })); }

  function insert(text) {
    const s = input.selectionStart ?? input.value.length, e = input.selectionEnd ?? s;
    if (input.maxLength > 0 && input.value.length - (e - s) + text.length > input.maxLength) return;   // เต็มแล้ว
    input.value = input.value.slice(0, s) + text + input.value.slice(e);
    input.setSelectionRange(s + text.length, s + text.length);
    changed();
  }

  function backspace() {
    const s = input.selectionStart ?? input.value.length, e = input.selectionEnd ?? s;
    if (s !== e) { input.value = input.value.slice(0, s) + input.value.slice(e); input.setSelectionRange(s, s); }
    else if (s > 0) {
      const before = Array.from(input.value.slice(0, s));   // ลบทีละตัวอักษร (ไม่ตัดกลาง surrogate pair)
      before.pop();
      const ns = before.join("").length;
      input.value = before.join("") + input.value.slice(s);
      input.setSelectionRange(ns, ns);
    }
    changed();
  }

  function show() {
    const reveal = () => requestAnimationFrame(() => input.scrollIntoView({ block: input === main ? "nearest" : "center" }));
    if (open) { render(); reveal(); return; }   // ย้ายไปอีกช่อง → ป้ายปุ่ม ส่ง/เสร็จ ตามช่องนั้น
    open = true;
    lang = document.documentElement.lang === "en" ? "en" : "th";
    shift = false;
    render();
    el.classList.add("open");
    el.setAttribute("aria-hidden", "false");
    document.body.classList.add("osk-open");
    reveal();
  }

  function hide() {
    if (!open) return;
    open = false;
    el.classList.remove("open");
    el.setAttribute("aria-hidden", "true");
    document.body.classList.remove("osk-open");
  }

  // แตะช่องพิมพ์ด้วยนิ้ว → เปิด และกันคีย์บอร์ดของระบบ (inputmode=none)
  document.addEventListener("pointerdown", (e) => {
    const t = e.target.closest && e.target.closest(TARGET);
    if (!t) return;
    if (ALWAYS || e.pointerType === "touch" || e.pointerType === "pen") { input = t; t.inputMode = "none"; show(); }
  }, true);
  document.addEventListener("focusin", (e) => {
    const t = e.target.closest && e.target.closest(TARGET);
    if (t && ALWAYS) { input = t; t.inputMode = "none"; show(); }
  });
  // แตะที่อื่น / เข้าโหมดรอ / เริ่มฟังไมค์ → ปิด (ย้ายไปอีกช่อง: input เปลี่ยนก่อนแล้ว ไม่ปิด)
  document.addEventListener("focusout", (e) => { if (e.target === input) hide(); });
  composer.addEventListener("submit", () => { input.blur(); });

  // กดปุ่มบนคีย์บอร์ดไม่ให้ช่องพิมพ์หลุดโฟกัส (preventDefault ที่ pointerdown)
  let repeat = null;
  const stopRepeat = () => { clearTimeout(repeat); clearInterval(repeat); repeat = null; };
  el.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    const b = e.target.closest("button.k");
    if (!b) return;
    if (document.activeElement !== input) input.focus();
    const { ch, act } = b.dataset;
    if (ch !== undefined) {
      insert(ch);
      if (shift) { shift = false; render(); }
    } else if (act === "back") {
      backspace();
      repeat = setTimeout(() => { repeat = setInterval(backspace, 70); }, 450);   // กดค้างลบต่อเนื่อง
    } else if (act === "shift") { shift = !shift; render(); }
    else if (act === "lang") { lang = lang === "th" ? "en" : "th"; shift = false; render(); }
    else if (act === "hide") { swallowTap(); input.blur(); }
    else if (act === "enter") { swallowTap(); if (input === main) composer.requestSubmit(); else input.blur(); }
  });

  // ซ่อนคีย์บอร์ดตอนนิ้วแตะลง → ปุ่มไมค์ (ซ่อนอยู่ตอนคีย์บอร์ดเปิด) โผล่ใต้นิ้วพอดี ยกนิ้วแล้วเลยกลายเป็นกดไมค์
  // กันไว้: ทิ้งการยกนิ้ว/คลิกของการแตะครั้งนั้น (ไม่เกิน 700 มิลลิวินาที)
  let swallowUntil = 0;
  function swallowTap() { swallowUntil = Date.now() + 700; }
  ["pointerup", "click"].forEach((ev) => window.addEventListener(ev, (e) => {
    if (Date.now() > swallowUntil) return;
    if (ev === "click") swallowUntil = 0;   // ทิ้งคลิกเดียวพอ
    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
  }, true));
  ["pointerup", "pointercancel", "pointerleave"].forEach((ev) => el.addEventListener(ev, stopRepeat));
})();
