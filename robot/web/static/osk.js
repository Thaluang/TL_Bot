// คีย์บอร์ดบนจอ (ไทย/อังกฤษ) ในหน้าเว็บเอง — หน้าแชทเปิดแบบเต็มจอ (kiosk) คีย์บอร์ดของระบบโดนบัง
// ขึ้นเมื่อแตะช่องพิมพ์ด้วยนิ้ว (คลิกเมาส์บนคอมไม่ขึ้น) หรือเปิดหน้าด้วย ?osk=1 ให้ขึ้นทุกครั้ง
// อยู่ใน .osk-host (แถวล่างสุดของจอ เต็มความกว้าง) → ตอนเปิด แชทกับฝั่งซ้ายหดขึ้นเอง ช่องพิมพ์ไม่โดนบัง
(() => {
  const input = document.getElementById("q");
  const composer = document.getElementById("composer");
  const stage = document.querySelector(".osk-host") || document.querySelector(".stage");
  if (!input || !composer || !stage) return;

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
    th: { space: "เว้นวรรค", send: "ส่ง", other: "ABC", hide: "ซ่อนคีย์บอร์ด" },
    en: { space: "space", send: "Send", other: "ไทย", hide: "Hide keyboard" },
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
    r.appendChild(keyBtn(w.send + " ↵", "send", { act: "enter" }));
    el.appendChild(r);
  }

  function changed() { input.dispatchEvent(new Event("input", { bubbles: true })); }

  function insert(text) {
    const s = input.selectionStart ?? input.value.length, e = input.selectionEnd ?? s;
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
    if (open) return;
    open = true;
    lang = document.documentElement.lang === "en" ? "en" : "th";
    shift = false;
    render();
    el.classList.add("open");
    el.setAttribute("aria-hidden", "false");
    document.body.classList.add("osk-open");
    requestAnimationFrame(() => input.scrollIntoView({ block: "nearest" }));
  }

  function hide() {
    if (!open) return;
    open = false;
    el.classList.remove("open");
    el.setAttribute("aria-hidden", "true");
    document.body.classList.remove("osk-open");
  }

  // แตะช่องพิมพ์ด้วยนิ้ว → เปิด และกันคีย์บอร์ดของระบบ (inputmode=none)
  input.addEventListener("pointerdown", (e) => {
    if (ALWAYS || e.pointerType === "touch" || e.pointerType === "pen") { input.inputMode = "none"; show(); }
  });
  input.addEventListener("focus", () => { if (ALWAYS) { input.inputMode = "none"; show(); } });
  input.addEventListener("blur", hide);   // แตะที่อื่น / เข้าโหมดรอ / เริ่มฟังไมค์ → ปิด
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
    else if (act === "hide") { input.blur(); }
    else if (act === "enter") { composer.requestSubmit(); }
  });
  ["pointerup", "pointercancel", "pointerleave"].forEach((ev) => el.addEventListener(ev, stopRepeat));
})();
