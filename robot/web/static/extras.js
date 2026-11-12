// แผงซ้ายเพิ่มเติม: ปฏิทินแนะแนวการศึกษา / คลังภาพกิจกรรม / แบบประเมินความพึงพอใจ
// ครูลงข้อมูลที่หน้า /stats — จอโหลดใหม่ทุกครั้งที่เปิดแผง (ข้อมูลไม่มาก)
// ใช้ของจาก screen.js: Board, addMsg, setState, speakAnswer, escapeHtml, busy
(() => {
  const TH_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"];
  const TH_MON = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];
  const DOW = ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"];
  const esc = (s) => escapeHtml(String(s == null ? "" : s));
  const getJson = (url) => fetch(url, { cache: "no-store" }).then((r) => (r.ok ? r.json() : Promise.reject(r.status)));
  const pad = (n) => String(n).padStart(2, "0");
  const iso = (y, m, d) => `${y}-${pad(m + 1)}-${pad(d)}`;
  const parts = (s) => s.split("-").map(Number);
  const thShort = (s) => { const [y, m, d] = parts(s); return `${d} ${TH_MON[m - 1]} ${y + 543}`; };
  const say = (msg, speech) => { addMsg("bot", msg); setState("answering"); speakAnswer(speech || msg, "th"); };

  // ================= ปฏิทินแนะแนว =================
  let cal = { items: [], today: "", y: 0, m: 0, sel: "" };
  const evEnd = (e) => e.end || e.date;
  const onDay = (day) => cal.items.filter((e) => e.date <= day && day <= evEnd(e));
  const whenText = (e) => thShort(e.date) + (e.end ? " – " + thShort(e.end) : "");
  const evSpeech = (e) => [whenText(e), e.time ? "เวลา " + e.time : "", e.title, e.place ? "ที่ " + e.place : ""].filter(Boolean).join(" ");

  function renderCal() {
    const { y, m, today } = cal;
    const first = new Date(y, m, 1).getDay(), days = new Date(y, m + 1, 0).getDate();
    let grid = DOW.map((d) => `<span class="dow">${d}</span>`).join("");
    for (let i = 0; i < first; i++) grid += '<span class="day out"></span>';
    for (let d = 1; d <= days; d++) {
      const day = iso(y, m, d), has = onDay(day).length;
      const cls = ["day", has ? "has" : "", day < today ? "past" : "", day === today ? "today" : "", day === cal.sel ? "sel" : ""].filter(Boolean).join(" ");
      grid += has ? `<button type="button" class="${cls}" data-action="calDay" data-day="${day}">${d}<i></i></button>` : `<span class="${cls}">${d}</span>`;
    }
    // รายการ: วันที่เลือก หรือ กำหนดการที่จะถึง (ไม่มีเลย → ที่ผ่านมาล่าสุด)
    let list = cal.sel ? onDay(cal.sel) : cal.items.filter((e) => evEnd(e) >= today);
    let head = cal.sel ? "กำหนดการวันที่ " + thShort(cal.sel) : "กำหนดการที่จะถึง";
    if (!cal.sel && !list.length && cal.items.length) { list = cal.items.slice(-5).reverse(); head = "กำหนดการที่ผ่านมา"; }
    const ev = (e) => {
      const [, mm, dd] = parts(e.date);
      return `<button type="button" class="ev${evEnd(e) < today ? " past" : ""}${cal.sel ? " sel" : ""}" data-action="calEvent" data-id="${esc(e.id)}">` +
        `<span class="dd"><b>${dd}</b><small>${TH_MON[mm - 1]}</small></span><span class="tx"><b>${esc(e.title)}</b>` +
        `<small>${esc([whenText(e), e.time, e.place].filter(Boolean).join(" · "))}</small>${e.detail ? `<p>${esc(e.detail)}</p>` : ""}</span></button>`;
    };
    const listHtml = list.length ? list.map(ev).join("") : '<p class="sv-note">ยังไม่มีกำหนดการแนะแนวครับ</p>';
    const back = cal.sel ? '<button type="button" class="back" data-action="calAll" style="margin-left:0;align-self:flex-start">← ดูทั้งหมด</button>' : "";
    Board.show("calendar", `<div class="cal"><div class="cal-month"><div class="cal-nav">` +
      `<button type="button" data-action="calPrev" aria-label="เดือนก่อน">‹</button><b>${TH_MONTHS[m]} ${y + 543}</b>` +
      `<button type="button" data-action="calNext" aria-label="เดือนถัดไป">›</button></div><div class="cal-grid">${grid}</div></div>` +
      `<div class="cal-list"><h4>${head}</h4>${back}${listHtml}</div></div>`, "ปฏิทินแนะแนวการศึกษา", "แตะวันที่มีสีเพื่อดูรายละเอียด", "📅");
  }

  function showCalendar() {
    getJson("/guidance").then((d) => {
      cal.items = d.items || []; cal.today = d.today || iso(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()); cal.sel = "";
      const next = cal.items.find((e) => evEnd(e) >= cal.today);
      const [y, m] = parts(next && next.date > cal.today ? next.date : cal.today);   // เปิดที่เดือนของกำหนดการถัดไป
      cal.y = y; cal.m = m - 1;
      renderCal();
      if (next) say(`นี่คือปฏิทินแนะแนวการศึกษาครับ 📅\n\nกำหนดการถัดไป: **${next.title}** ${whenText(next)}${next.time ? " เวลา " + next.time : ""}${next.place ? " ณ " + next.place : ""}`,
        "นี่คือปฏิทินแนะแนวการศึกษาครับ กำหนดการถัดไปคือ " + evSpeech(next));
      else say("นี่คือปฏิทินแนะแนวการศึกษาครับ 📅 ตอนนี้ยังไม่มีกำหนดการแนะแนวที่จะถึง สอบถามเพิ่มเติมได้ที่ 0-3628-1295 นะครับ");
    }).catch(() => say("ขออภัยครับ โหลดปฏิทินแนะแนวไม่ได้ ลองใหม่อีกครั้งนะครับ"));
  }
  function moveMonth(k) {
    cal.m += k;
    if (cal.m < 0) { cal.m = 11; cal.y--; } else if (cal.m > 11) { cal.m = 0; cal.y++; }
    cal.sel = ""; renderCal();
  }
  function pickDay(b) {
    cal.sel = b.dataset.day; renderCal();
    const evs = onDay(cal.sel);
    if (evs.length && !busy()) { setState("answering"); speakAnswer(evs.map(evSpeech).join(" และ "), "th"); }
  }
  function pickEvent(b) {
    const e = cal.items.find((x) => x.id === b.dataset.id);
    if (!e || busy()) return;
    setState("answering"); speakAnswer(evSpeech(e) + (e.detail ? " " + e.detail : ""), "th");
  }

  // ================= คลังภาพกิจกรรม =================
  function showGallery() {
    getJson("/gallery").then((d) => {
      const items = d.items || [];
      if (!items.length) {
        Board.show("photos", '<div class="empty-box"><b>🖼️ ยังไม่มีรูปกิจกรรม</b><span>ครูเพิ่มรูปได้ที่หน้าผู้ดูแลระบบครับ</span></div>', "คลังภาพกิจกรรม", "", "🖼️");
        say("คลังภาพกิจกรรมยังไม่มีรูปครับ 🖼️");
        return;
      }
      // จัดกลุ่มตามชื่อกิจกรรม (ลำดับตามรูปล่าสุดของแต่ละกิจกรรม)
      const albums = [];
      for (const p of items) {
        let a = albums.find((x) => x.title === p.title);
        if (!a) albums.push(a = { title: p.title, date: p.date, photos: [] });
        a.photos.push(p);
      }
      const html = albums.map((a) => `<section class="album"><h4>${esc(a.title)}<small>${a.date ? thShort(a.date) + " · " : ""}${a.photos.length} รูป</small></h4>` +
        `<div class="gallery">${a.photos.map((p) => `<figure><img class="place-photo" src="${esc(p.image_url)}" alt="${esc(p.title)}" loading="lazy"></figure>`).join("")}</div></section>`).join("");
      Board.show("photos", html, "คลังภาพกิจกรรมน้องทานตะวัน-Bot", `${albums.length} กิจกรรม · ${items.length} รูป · แตะรูปเพื่อขยาย`, "🖼️");
      say(`นี่คือคลังภาพกิจกรรมของน้องทานตะวัน-Bot ครับ 📸 มีทั้งหมด ${albums.length} กิจกรรม แตะรูปทางซ้ายเพื่อขยายได้เลยครับ`);
    }).catch(() => say("ขออภัยครับ โหลดคลังภาพไม่ได้ ลองใหม่อีกครั้งนะครับ"));
  }

  // ================= แบบประเมินความพึงพอใจ (ตามเอกสาร 3 ตอน) =================
  // วาดครั้งเดียว แล้วแตะเลือกเปลี่ยนแค่คลาส — ข้อความที่พิมพ์ในช่องข้อเสนอแนะไม่หาย
  const LEVELS = ["น้อยที่สุด", "น้อย", "ปานกลาง", "มาก", "มากที่สุด"];
  const FACES = ["😞", "🙁", "😐", "🙂", "😍"];
  let sv = null;   // {form, gender, role, usage:Set, scores:[]}
  const box = () => $("boardBody").querySelector(".survey");
  const chips = (act, list, multi) => list.map((o) =>
    `<button type="button" data-action="${act}" data-key="${o.key}"${multi ? ' aria-pressed="false"' : ""}>${multi ? "☐ " : ""}${esc(o.name)}</button>`).join("");

  function drawSurvey() {
    const f = sv.form, n = f.text_max || 300;
    const head = `<div class="sv-head"><span>ขั้น / รายการประเมิน</span>${[5, 4, 3, 2, 1].map((k) => `<span>${k}<br>${LEVELS[k - 1]}</span>`).join("")}</div>`;
    const rows = f.items.map((it, i) => `<div class="sv-row" data-row="${i}"><span class="q"><small>${esc(it.stage)}</small>${i + 1}. ${esc(it.text)}</span>` +
      [5, 4, 3, 2, 1].map((k) => `<button type="button" data-action="svScore" data-i="${i}" data-n="${k}">${FACES[k - 1]}<small>${k}</small></button>`).join("") + "</div>").join("");
    Board.show("survey", `<div class="survey">` +
      `<p class="sv-intro">ใช้เวลาประมาณ 2 นาที ข้อมูลของท่านใช้เพื่อการวิจัยและพัฒนาหุ่นยนต์เท่านั้น ไม่มีการเปิดเผยข้อมูลส่วนบุคคล</p>` +
      `<h4>ตอนที่ 1 ข้อมูลทั่วไป</h4>` +
      `<div class="sv-roles" data-group="gender"><span class="lb">เพศ</span>${chips("svGender", f.genders)}</div>` +
      `<div class="sv-roles" data-group="role"><span class="lb">สถานะ</span>${chips("svRole", f.roles)}</div>` +
      `<div class="sv-roles" data-group="usage"><span class="lb">สิ่งที่ใช้งาน <small>(ตอบได้มากกว่า 1 ข้อ)</small></span>${chips("svUsage", f.usages, true)}</div>` +
      `<h4>ตอนที่ 2 ความพึงพอใจต่อการใช้งาน</h4>${head}${rows}` +
      `<h4>ตอนที่ 3 ข้อเสนอแนะ <small>(ไม่บังคับ — แตะช่องเพื่อพิมพ์)</small></h4>` +
      `<label class="sv-text">สิ่งที่ชอบมากที่สุด<input id="svLiked" data-osk inputmode="none" maxlength="${n}" autocomplete="off"></label>` +
      `<label class="sv-text">สิ่งที่ควรปรับปรุง<input id="svImprove" data-osk inputmode="none" maxlength="${n}" autocomplete="off"></label>` +
      `<button type="button" class="sv-send" data-action="svSend">ส่งแบบประเมิน ✓</button><div class="sv-note" id="svNote"></div></div>`,
      "แบบประเมินความพึงพอใจการใช้งาน", "โปรดเลือกข้อที่ตรงกับความคิดเห็นของท่านมากที่สุด", "📝");
  }
  function mark(group, key, on) {   // ปุ่มตัวเลือกในตอนที่ 1
    const g = box().querySelector(`[data-group="${group}"]`);
    g.classList.remove("miss");
    g.querySelectorAll("button").forEach((b) => {
      const sel = on ? on(b.dataset.key) : b.dataset.key === key;
      b.classList.toggle("on", sel);
      if (b.hasAttribute("aria-pressed")) { b.setAttribute("aria-pressed", sel); b.textContent = (sel ? "☑ " : "☐ ") + b.textContent.slice(2); }
    });
  }
  function note(msg, bad) { const e = $("svNote"); if (e) { e.textContent = msg || ""; e.classList.toggle("bad", !!bad); } }

  function showSurvey() {
    getJson("/survey").then((f) => {
      sv = { form: f, gender: "", role: "", usage: new Set(), scores: f.items.map(() => 0) };
      drawSurvey();
      say("ขอบคุณที่สนใจทำแบบประเมินความพึงพอใจครับ 📝 ใช้เวลาประมาณ 2 นาที แตะเลือกคำตอบทางซ้ายให้ครบ แล้วกดส่งได้เลยครับ");
    }).catch(() => say("ขออภัยครับ เปิดแบบประเมินไม่ได้ ลองใหม่อีกครั้งนะครับ"));
  }
  function sendSurvey() {
    if (!sv || sv.sending || !box()) return;
    const missGroup = [["gender", !sv.gender], ["role", !sv.role], ["usage", !sv.usage.size]].filter((x) => x[1]).map((x) => x[0]);
    missGroup.forEach((g) => box().querySelector(`[data-group="${g}"]`).classList.add("miss"));
    const missRows = sv.scores.map((s, i) => (s ? -1 : i)).filter((i) => i >= 0);
    missRows.forEach((i) => box().querySelector(`[data-row="${i}"]`).classList.add("miss"));
    if (missGroup.length || missRows.length) {
      note(missGroup.length ? "ยังตอบตอนที่ 1 ไม่ครบครับ (ช่องขอบสีแดง)" : `ยังให้คะแนนไม่ครบครับ เหลือข้อ ${missRows.map((i) => i + 1).join(", ")}`, true);
      box().querySelector(".miss").scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    sv.sending = true; note("กำลังส่ง…");
    const body = { gender: sv.gender, role: sv.role, usage: [...sv.usage], scores: sv.scores,
      liked: $("svLiked").value.trim(), improve: $("svImprove").value.trim() };
    fetch("/survey", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(() => {
        sv = null;
        Board.show("survey", '<div class="empty-box"><b>🙏 ขอบคุณที่ใช้บริการน้องทานตะวัน-Bot</b><span>ความคิดเห็นของท่านช่วยให้หุ่นยนต์พัฒนาขึ้นทุกวันครับ</span></div>', "แบบประเมินความพึงพอใจการใช้งาน", "", "📝");
        say("ขอบคุณมากครับที่ช่วยทำแบบประเมิน 🙏 ความคิดเห็นของท่านช่วยให้ผมพัฒนาขึ้นทุกวันครับ");
      })
      .catch(() => { if (sv) sv.sending = false; note("ส่งไม่สำเร็จ ลองกดส่งอีกครั้งนะครับ", true); });
  }

  window.Extras = {
    showCalendar, showGallery, showSurvey,
    calPrev: () => moveMonth(-1), calNext: () => moveMonth(1), calDay: pickDay, calEvent: pickEvent,
    calAll: () => { cal.sel = ""; renderCal(); },
    svGender: (b) => { if (sv) { sv.gender = b.dataset.key; mark("gender", sv.gender); } },
    svRole: (b) => { if (sv) { sv.role = b.dataset.key; mark("role", sv.role); } },
    svUsage: (b) => {
      if (!sv) return;
      const k = b.dataset.key;
      if (sv.usage.has(k)) sv.usage.delete(k); else sv.usage.add(k);
      mark("usage", "", (key) => sv.usage.has(key));
    },
    svScore: (b) => {
      if (!sv) return;
      const i = Number(b.dataset.i), row = b.closest(".sv-row");
      sv.scores[i] = Number(b.dataset.n);
      row.classList.remove("miss");
      row.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    },
    svSend: sendSurvey,
  };
})();
