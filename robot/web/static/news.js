// จอ 1920 ฝั่งซ้าย: นาฬิกา + อากาศ + ข่าวเด่น (ครูลงผ่านหน้า /stats) และแผงแสดงผล (Board)
// screen.js เรียก Board.show(...) เมื่อคำตอบมีแผนผัง/รูป/เมนู — ขึ้นแทนข่าวชั่วคราว ว่าง 60 วิ กลับหน้าข่าวเอง
// แตะการ์ดข่าว → ส่งเหตุการณ์ "news-read" ให้ screen.js อ่านออกเสียง
(() => {
  const $ = (id) => document.getElementById(id);
  const isEn = () => document.documentElement.lang === "en";
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const W = {
    th: { morning: "สวัสดีตอนเช้าครับ", noon: "สวัสดีตอนกลางวันครับ", afternoon: "สวัสดีตอนบ่ายครับ", evening: "สวัสดีตอนเย็นครับ",
      cats: { admission: "รับสมัคร", event: "กิจกรรม", scholarship: "ทุนการศึกษา", award: "ผลงาน", general: "ประกาศ" },
      scan: "สแกนเปิดลิงก์", set: "ชุดที่", inviteA: "อยากรู้อะไรเกี่ยวกับ<br><em>ท่าหลวงฯ</em> ถามน้องทานตะวันได้เลย",
      inviteB: "แตะปุ่ม 🎤 ด้านขวาแล้วพูด หรือพิมพ์คำถามก็ได้ครับ", back: (n) => `กลับหน้าข่าวใน ${n} วินาที`, rainy: "โอกาสฝน" },
    en: { morning: "Good morning", noon: "Good day", afternoon: "Good afternoon", evening: "Good evening",
      cats: { admission: "Admission", event: "Event", scholarship: "Scholarship", award: "Achievement", general: "Notice" },
      scan: "Scan to open", set: "Set", inviteA: "Curious about <em>Tha Luang</em>?<br>Ask Nong Tantawan anything",
      inviteB: "Tap 🎤 on the right and speak, or type your question", back: (n) => `Back to news in ${n}s`, rainy: "Rain chance" },
  };
  const w = () => W[isEn() ? "en" : "th"];
  const CAL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>';
  const SPEAKER = '<span class="tapme"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M4 9v6h4l5 5V4L8 9H4zm12.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4z"/></svg></span>';

  // ---------------- นาฬิกา ----------------
  function tick() {
    const d = new Date(), h = d.getHours();
    $("clock").innerHTML = String(h).padStart(2, "0") + "<span>:</span>" + String(d.getMinutes()).padStart(2, "0");
    $("hello").textContent = h < 11 ? w().morning : h < 13 ? w().noon : h < 17 ? w().afternoon : w().evening;
    $("today").textContent = d.toLocaleDateString(isEn() ? "en-GB" : "th-TH", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  }

  // ---------------- อากาศ (เซิร์ฟเวอร์ถาม Open-Meteo ให้) ----------------
  const SUN = '<circle cx="48" cy="44" r="24" fill="#fff7c2"/><g stroke="#fff7c2" stroke-width="5" stroke-linecap="round"><path d="M48 6v8M48 74v8M10 44h8M78 44h8M21 17l6 6M69 65l6 6M21 71l6-6M69 23l6-6"/></g>';
  const CLOUD = '<path d="M40 98h52a18 18 0 0 0 0-36 26 26 0 0 0-50 6 15 15 0 0 0-2 30z" fill="#fff"/>';
  const RAIN = '<g stroke="#fff" stroke-width="5" stroke-linecap="round" opacity=".9"><path d="M50 106l-5 10M68 106l-5 10M86 106l-5 10"/></g>';
  const BOLT = '<path d="M70 96l-12 18h10l-6 14 18-22H70l6-10z" fill="#fde047"/>';
  function wxIcon(code) {
    if (code === 0 || code === 1) return SUN;
    if (code === 2) return SUN + CLOUD;
    if (code >= 95) return CLOUD.replace('d="M40 98', 'transform="translate(0,-14)" d="M40 98') + BOLT;
    if (code >= 51) return CLOUD.replace('d="M40 98', 'transform="translate(0,-14)" d="M40 98') + RAIN;
    return CLOUD.replace('d="M40 98', 'transform="translate(-8,-18) scale(1.1)" d="M40 98');
  }
  let wx = null;
  function renderWeather() {
    const box = $("weather"), ok = !!(wx && wx.temp != null);
    box.hidden = !ok;
    $("topRow").classList.toggle("no-weather", !ok);
    if (!ok) return;
    $("wxTemp").textContent = wx.temp;
    const text = isEn() ? wx.text_en : wx.text_th;
    const extra = [wx.high != null && wx.low != null ? `${wx.low}°–${wx.high}°` : "", wx.rain >= 30 ? `${w().rainy} ${wx.rain}%` : ""].filter(Boolean).join(" · ");
    $("wxText").textContent = [text, extra].filter(Boolean).join(" · ");
    $("wxIcon").innerHTML = wxIcon(wx.code);
    box.classList.toggle("rain", wx.code >= 51);
  }
  function loadWeather() {
    fetch("/weather").then((r) => (r.ok ? r.json() : null)).then((d) => { wx = d; renderWeather(); }).catch(() => { wx = null; renderWeather(); });
  }

  // ---------------- ข่าว ----------------
  const PER_PAGE = 3, ROTATE_MS = 10000;
  let items = [], version = "", page = 0;
  function qr(url) {
    if (typeof qrcode !== "function" || !url) return "";
    try { const q = qrcode(0, "M"); q.addData(url); q.make(); return q.createSvgTag({ cellSize: 4, margin: 2, scalable: true }); } catch (e) { return ""; }
  }
  function card(n, kind) {
    const tag = `<span class="tag k-${esc(n.category)}">${esc(w().cats[n.category] || "")}</span>`;
    const when = n.subtitle ? `<div class="when">${CAL}<span>${esc(n.subtitle)}</span></div>` : "";
    const data = `data-news="${esc(n.id)}"`;
    if (kind === "feat") {
      const code = qr(n.link);
      return `<button type="button" class="nc feat${n.image_url ? "" : " noimg"}" ${data}` +
        (n.image_url ? ` style="--img:url('${esc(n.image_url)}')"` : "") + ">" +
        (code ? `<span class="qr">${code}${esc(w().scan)}</span>` : "") +
        `${tag}<h4>${esc(n.title)}</h4>${n.detail ? `<p>${esc(n.detail)}</p>` : ""}${when}</button>`;
    }
    if (n.image_url) {
      return `<button type="button" class="nc side glass" ${data} style="--img:url('${esc(n.image_url)}')"><span class="ph"></span>` +
        `<span class="tx">${tag}<h4>${esc(n.title)}</h4>${when}</span>${SPEAKER}</button>`;
    }
    const big = { admission: "🎓", event: "✦", scholarship: "฿", award: "★", general: "📢" }[n.category] || "✦";
    return `<button type="button" class="nc textonly glass k-${esc(n.category)}" ${data} style="background:var(--glass)">` +
      `<span class="tx">${tag}<h4>${esc(n.title)}</h4>${when}</span><span class="big">${big}</span>${SPEAKER}</button>`;
  }
  function renderNews(animate) {
    const grid = $("newsGrid"), pages = Math.max(1, Math.ceil(items.length / PER_PAGE));
    page = page % pages;
    const show = items.slice(page * PER_PAGE, page * PER_PAGE + PER_PAGE);
    grid.className = "news n" + Math.max(1, show.length) + (animate ? " fade" : "");
    grid.innerHTML = show.length ? show.map((n, i) => card(n, i === 0 ? "feat" : "side")).join("")
      : `<div class="nc invite glass"><b>${w().inviteA}</b><p>${w().inviteB}</p></div>`;
    $("pager").innerHTML = pages > 1 ? `${w().set} ${page + 1}/${pages} ` + Array.from({ length: pages }, (_, i) => `<i class="${i === page ? "on" : ""}"></i>`).join("") : "";
  }
  function loadNews() {
    return fetch("/news").then((r) => (r.ok ? r.json() : null)).then((d) => {
      if (!d || d.version === version) return;
      version = d.version; items = d.items || [];
      renderNews(true);
    }).catch(() => {});
  }
  $("newsGrid").addEventListener("click", (e) => {
    const c = e.target.closest("[data-news]");
    if (!c) return;
    const n = items.find((x) => x.id === c.dataset.news);
    if (n) window.dispatchEvent(new CustomEvent("news-read", { detail: n }));
  });
  setInterval(() => {
    if (items.length > PER_PAGE && Board.isHome() && !document.body.classList.contains("osk-open")) { page++; renderNews(true); }
  }, ROTATE_MS);

  // ---------------- แผงแสดงผล (แทนข่าวชั่วคราว) ----------------
  const BOARD_IDLE_MS = 60 * 1000;
  let boardAt = 0;
  const Board = {
    show(kind, html, title, sub, icon) {
      $("boardIcon").textContent = icon || { map: "🗺️", photos: "📷", menu: "☰" }[kind] || "✦";
      $("boardTitle").textContent = title || "";
      $("boardSub").textContent = sub || "";
      $("boardBody").innerHTML = html;
      $("boardBody").scrollTop = 0;
      $("board").hidden = false; $("home").hidden = true;
      boardAt = Date.now();
    },
    home() { $("board").hidden = true; $("home").hidden = false; $("boardBody").innerHTML = ""; },
    isHome() { return $("board").hidden; },
    touch() { boardAt = Date.now(); },
  };
  window.Board = Board;
  document.addEventListener("pointerdown", () => { if (!Board.isHome()) boardAt = Date.now(); }, true);
  setInterval(() => {
    if (Board.isHome()) return;
    const left = Math.ceil((BOARD_IDLE_MS - (Date.now() - boardAt)) / 1000);
    if (left <= 0) { Board.home(); return; }
    $("boardAuto").textContent = left <= 20 ? w().back(left) : "";
  }, 1000);

  // ภาษาเปลี่ยน (screen.js) / หน้าครูเพิ่งแก้ข่าว (จอตัวอย่าง) → วาดใหม่
  window.addEventListener("lang-change", () => { tick(); renderWeather(); renderNews(false); });
  window.addEventListener("message", (e) => { if (e.data === "news-refresh") { version = ""; loadNews(); } });

  tick(); setInterval(tick, 10000);
  renderNews(false); loadNews(); setInterval(loadNews, 60000);
  loadWeather(); setInterval(loadWeather, 30 * 60 * 1000);
})();
