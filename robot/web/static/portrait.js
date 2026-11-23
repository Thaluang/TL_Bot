// จอแนวตั้ง (screen_v.html): สคริปต์เชื่อมที่โหลดหลัง screen.js / news.js / extras.js / osk.js
// - สลับมุมมอง หน้าแรก (body.view-home) ↔ แชท (body.view-chat) และเปิด/ปิดแผงของหน้านี้ (#pvInfo #pvMore #pvQr)
// - ปุ่มระบบภายนอก (data-pv-sys): เปิดเว็บเต็มจอด้วย openTour เดิม หรือขึ้น QR ถ้าเว็บห้ามเปิดซ้อน (เซิร์ฟเวอร์เช็กให้ที่ /pv/systems)
// - ลบอีโมจิทุกข้อความบนจอ (ข้อความเดิมใน screen.js / คำตอบ AI มีอีโมจิ — หน้านี้ต้องดูทางการ)
// ใช้ฟังก์ชันส่วนกลางของ screen.js: newChat, openTour, closeTour, cancelMic, stopAnswer, applyLang, T, lang
(() => {
  const $ = (id) => document.getElementById(id);
  const body = document.body;
  const ICON = (id) => `<svg class="i"><use href="#${id}"/></svg>`;

  // ---------- ลบอีโมจิ ----------
  // ตารางข้อความของ screen.js (ทักทาย, ดูรูปทางซ้าย ฯลฯ) — ลบตั้งแต่ต้น แล้ววาดแชทเริ่มต้นใหม่
  (function cleanTable(o) {
    for (const k in o) {
      if (typeof o[k] === "string") o[k] = stripEmoji(o[k]);
      else if (o[k] && typeof o[k] === "object") cleanTable(o[k]);
    }
  })(T.th);
  T.th.seeLeft = "ดูรูปใหญ่ด้านบน";   // จอแนวตั้งรูปขึ้นด้านบนแชท ไม่ใช่ทางซ้าย
  T.th.intro = "สวัสดีครับ วันนี้มาติดต่อเรื่องอะไรครับ แตะปุ่มด้านล่างแล้วพูดได้เลย หรือพิมพ์คำถามก็ได้ครับ";
  T.th.mapMsg = "นี่คือแผนผังวิทยาลัยครับ ดูด้านบนได้เลย แตะที่รูปเพื่อขยาย\n\nเยี่ยมชมวิทยาลัยแบบ 3 มิติได้ด้วยนะครับ แตะปุ่มด้านล่างได้เลย";
  T.th.overviewMsg = "นี่คือภาพรวมการทำงานของผมครับ แตะรูปเพื่อขยายเต็มจอได้เลยครับ";
  T.th.guideMsg = "นี่คือคู่มือการใช้งานหุ่นครับ แตะรูปเพื่อขยายเต็มจอได้เลยครับ";

  function cleanNode(root) {
    if (root.nodeType === 3) { fix(root); return; }
    if (root.nodeType !== 1 || root.closest(".stars")) return;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) fix(n);
  }
  function fix(n) {
    if (n.parentElement && n.parentElement.closest(".stars")) return;
    const t = stripEmojiInline(n.data);
    if (t !== n.data) n.data = t;
  }
  new MutationObserver((list) => {
    for (const m of list) {
      if (m.type === "characterData") fix(m.target);
      else m.addedNodes.forEach(cleanNode);
    }
  }).observe($("app"), { childList: true, subtree: true, characterData: true });

  // ---------- มุมมอง ----------
  const layers = ["pvInfo", "pvMore", "pvQr"];
  function closeLayers() { layers.forEach((id) => $(id).classList.remove("on")); }
  function view(name) {
    body.classList.toggle("view-chat", name === "chat");
    body.classList.toggle("view-home", name !== "chat");
    closeLayers();
    if (name === "chat") requestAnimationFrame(() => { const s = $("scroll"); s.scrollTop = s.scrollHeight; });
  }
  // กลับหน้าแรก: ปิดเว็บ/แผงทั้งหมด หยุดฟัง/พูด — ไม่ล้างแชท (ล้างตอนหมดเวลาว่าง หรือกด "คุยใหม่")
  function home() {
    closeLayers();
    if (window.Board) Board.home();
    closeTour();
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    view("home");
  }

  // มีข้อความฝั่งผู้ใช้ใหม่ (พิมพ์ พูด แตะคำถาม แตะข่าว สแกน QR) → ไปหน้าแชทเอง
  new MutationObserver((list) => {
    for (const m of list) for (const n of m.addedNodes) {
      if (n.nodeType === 1 && n.classList.contains("msg") && n.classList.contains("user")) { view("chat"); return; }
    }
  }).observe($("chat"), { childList: true });

  // ล้างแชทตอนว่างนาน (screen.js เรียก newChat) / กด "คุยใหม่" → กลับหน้าแรกด้วย
  // ยกเว้นกดปุ่ม "คุยใหม่" ในหน้าแชทเอง → ล้างแชทแต่ยังอยู่หน้าแชท (ดักแบบ capture ก่อนตัวจัดการของ screen.js)
  let keepChat = false;
  document.addEventListener("click", (e) => { if (e.target.closest('#pvChat [data-action="newChat"]')) keepChat = true; }, true);
  const origNewChat = newChat;
  newChat = function () {
    origNewChat();
    if (keepChat) { keepChat = false; view("chat"); } else home();
  };

  // ---------- ระบบภายนอก (ปุ่ม 2–5) ----------
  let systems = {};
  const loadSystems = () => fetch("/pv/systems").then((r) => (r.ok ? r.json() : [])).then((rows) => {
    systems = {}; (rows || []).forEach((s) => { systems[s.key] = s; });
  }).catch(() => {});
  loadSystems(); setInterval(loadSystems, 5 * 60 * 1000);

  function setBar(title, sub, color, icon, qrUrl) {
    $("pvWebTitle").textContent = title; $("pvWebSub").textContent = sub;
    $("pvWebIcon").setAttribute("href", "#" + icon);
    $("tourView").style.setProperty("--c", color);
    const q = $("pvWebQr");
    q.classList.toggle("on", !!qrUrl);
    q.querySelector("i").innerHTML = qrUrl ? qrSvg(qrUrl) : "";
  }
  // แถบบนของหน้าเว็บเต็มจอ: ระบบของวิทยาลัย / ทัวร์ 3 มิติ / ลิงก์จากคำตอบ AI
  const origOpenTour = openTour;
  openTour = function (src) {
    const sys = src && Object.values(systems).find((s) => s.url === src);
    if (sys) setBar(sys.title, sys.sub, sys.color, sys.icon, sys.url);
    else if (!src || /campus_tour/.test(src)) setBar("ทัวร์วิทยาลัย 3 มิติ", "ชมวิทยาลัยแบบเสมือนจริง", "#d0356c", "i-cube");
    else { let host = src; try { host = new URL(src).host; } catch (e) {} setBar("เว็บไซต์", host, "#1d5fd6", "i-globe"); }
    closeLayers();
    return origOpenTour.apply(this, arguments);
  };

  function showQr(s) {
    const box = $("pvQr");
    box.style.setProperty("--c", s.color);
    $("pvQrTitle").textContent = s.title; $("pvQrSub").textContent = s.sub; $("pvQrUrl").textContent = s.url;
    $("pvQrBox").innerHTML = qrSvg(s.url);
    closeLayers(); box.classList.add("on");
  }
  function openSystem(key) {
    const go = () => { const s = systems[key]; if (!s) return; if (s.embed) openTour(s.url); else showQr(s); };
    if (systems[key]) go(); else loadSystems().then(go);
  }
  function qrSvg(url) {
    try { const q = qrcode(0, "M"); q.addData(url); q.make(); return q.createSvgTag({ cellSize: 4, margin: 1, scalable: true }); } catch (e) { return ""; }
  }

  // ---------- เมนูอื่นๆ (ใช้ทั้งแผงหน้าแรก และ "เมนูทั้งหมด" ที่ screen.js เปิดตอนกดย้อนกลับจากเมนูที่เที่ยว) ----------
  const MORE = [
    ["trips", "i-mount", "ที่เที่ยวสระบุรี", "วัด น้ำตก ธรรมชาติ", "สระบุรีมีที่เที่ยวที่ไหนบ้าง"],
    ["food", "i-food", "ร้านอาหาร", "ก๋วยเตี๋ยว หมูกระทะ ตามสั่ง", "ร้านอาหารใกล้วิทยาลัยมีที่ไหนบ้าง"],
    ["cafe", "i-coffee", "คาเฟ่แนะนำ", "กาแฟ ระบายสี", "คาเฟ่ใกล้วิทยาลัยมีที่ไหนบ้าง"],
    ["stay", "i-bed", "ที่พักใกล้วิทยาลัย", "รีสอร์ท ห้องพัก", "ที่พักใกล้วิทยาลัยมีที่ไหนบ้าง"],
    ["market", "i-store", "ตลาด", "ตลาดนัด ตลาดสด", "ตลาดใกล้วิทยาลัยมีที่ไหนบ้าง"],
    ["souvenirs", "i-gift", "ของฝากสระบุรี", "OTOP ของกินขึ้นชื่อ", "ของฝากขึ้นชื่อของสระบุรีมีอะไรบ้าง"],
  ];
  $("pvMoreTiles").innerHTML = MORE.map(([k, ic, name, , q]) =>
    `<button type="button" class="tile" data-menu="${k}" data-q="${q}"><span class="ti">${ICON(ic)}</span>${name}</button>`).join("");
  $("allMenuTpl").innerHTML = '<div class="menu-grid">' + MORE.map(([k, ic, name, sub, q]) =>
    `<button type="button" class="menu-btn" data-menu="${k}" data-q="${q}"><em>${ICON(ic)}</em><span>${name}<small>${sub}</small></span></button>`).join("") + "</div>";

  // ---------- ปุ่มของหน้านี้ ----------
  // ฟังหลังตัวจัดการของ screen.js (ลงทะเบียนทีหลัง) — ปุ่ม data-q / data-action / data-menu ให้ screen.js ทำงานไปก่อน แล้วค่อยปิดแผงของหน้านี้
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-pv], [data-pv-sys], .layer .tile, #newsGrid [data-news]");
    if (!b) return;
    const pv = b.dataset.pv;
    if (pv === "home") { if (typeof stopAnswer === "function") stopAnswer(); cancelMic(); home(); return; }
    if (pv === "close") { closeLayers(); return; }
    if (pv === "chat") { view("chat"); return; }
    if (pv === "info" || pv === "more") { closeLayers(); $(pv === "info" ? "pvInfo" : "pvMore").classList.add("on"); return; }
    if (b.dataset.pvSys) { openSystem(b.dataset.pvSys); return; }
    closeLayers();   // แตะปุ่มย่อยในแผง / การ์ดข่าว → screen.js จัดการแล้ว ปิดแผงให้เห็นผล
  });

  // ---------- QR เว็บวิทยาลัยท้ายจอ ----------
  $("siteQr").innerHTML = qrSvg("https://www.tl.ac.th");

  // วาดแชทเริ่มต้นใหม่ด้วยข้อความที่ลบอีโมจิแล้ว + ตั้งป้ายสถานะตามตารางใหม่
  applyLang(lang);
  newChat();

  window.Portrait = { view, home, openSystem };
  body.dataset.pvReady = "1";   // บอกว่าสคริปต์รันจบ (เทสต์ web/test_portrait.py เช็ก)

  // ?pv=chat|info|more|map|homemap|newchat|speaking|attract|sys:<key> — เปิดมุมมองนั้นทันที (ใช้จับภาพตรวจหน้าจอ)
  const want = (location.search.match(/[?&]pv=([\w:]+)/) || [])[1];
  if (want === "chat") view("chat");
  else if (want === "info" || want === "more") $(want === "info" ? "pvInfo" : "pvMore").classList.add("on");
  else if (want && want.startsWith("sys:")) openSystem(want.slice(4));
  else if (want === "map") { view("chat"); addMsg("user", "แผนผังวิทยาลัย"); showMap(); }
  else if (want === "homemap") showMap();
  else if (want === "speaking") { view("chat"); addMsg("user", "สมัครเรียนทำอย่างไร"); addMsg("bot", "สมัครออนไลน์ได้เลยครับ (ตัวอย่างคำตอบ)", { rateQ: "สมัครเรียนทำอย่างไร" }); body.classList.add("speaking"); }
  else if (want === "attract") { $("attract").classList.add("open"); fetch("/attract").then((r) => r.json()).then((d) => { const v = $("attract").querySelector("video"); if (d.videos && d.videos[0]) { v.src = d.videos[0]; v.muted = true; v.currentTime = 5; } }).catch(() => {}); }
  else if (want === "newchat") { view("chat"); document.querySelector('#pvChat [data-action="newChat"]').click(); }
})();
