const API = "";
const IDLE_MS = 15 * 60 * 1000;
let token = localStorage.getItem("ks_token");
let user = JSON.parse(localStorage.getItem("ks_user") || "null");
let lang = localStorage.getItem("ks_lang") || (user && user.language) || "mr";
let lastActive = Date.now();
let chartInst = null;
let route = "dash";
let going = false;
let queued = null;
let dashCrop = "tomato";
let meta = { commodities: ["tomato", "onion", "soybean", "cotton", "wheat", "grapes"], mandis: ["Nashik", "Pune", "Mumbai", "Nagpur", "Aurangabad"] };

const $ = (id) => document.getElementById(id);
const t = (k) => (I18N[lang] || I18N.en)[k] || I18N.en[k] || k;
const rupee = (n) => "₹ " + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "");

function toast(msg) {
  const el = $("toast");
  el.hidden = false;
  el.textContent = msg;
  setTimeout(() => (el.hidden = true), 2800);
}

function setShell(appOn) {
  document.body.classList.toggle("is-app", appOn);
  document.body.classList.toggle("is-login", !appOn);
  $("app").hidden = !appOn;
  $("login-screen").hidden = appOn;
  $("login-screen").inert = appOn;
  $("app").inert = !appOn;
}

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(API + path, { ...opts, headers });
  if (res.status === 401) {
    logout(false);
    throw new Error("Session expired");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg || x).join(", ") : res.statusText;
    throw new Error(msg);
  }
  return data;
}

function speak(text) {
  if (!window.speechSynthesis) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" }[lang] || "en-IN";
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

function logout(callApi) {
  if (callApi) api("/auth/logout", { method: "POST" }).catch(() => {});
  token = null;
  user = null;
  localStorage.removeItem("ks_token");
  localStorage.removeItem("ks_user");
  setShell(false);
  applyLoginI18n();
}

function applyLoginI18n() {
  document.documentElement.lang = lang;
  $("login-tag").textContent = t("tag");
  $("login-title").textContent = t("login");
  $("login-sub").textContent = t("loginSub");
  $("btn-otp").textContent = t("sendOtp");
  $("btn-verify").textContent = t("verify");
  $("lbl-phone").textContent = t("phone");
  $("lbl-otp").textContent = t("otp");
  $("demo-hint").textContent = t("demoHint");
  $("login-gov").textContent = t("gov");
  $("login-problem").textContent = t("problem");
  $("feat1").textContent = t("feat1");
  $("feat2").textContent = t("feat2");
  $("feat3").textContent = t("feat3");
  $("step1-lbl").textContent = t("stepPhone");
  $("step2-lbl").textContent = t("stepOtp");
  $("modal-cancel").textContent = t("cancel");
  $("modal-ok").textContent = t("confirm");
  $("login-lang").querySelectorAll(".chip").forEach((b) => b.classList.toggle("active", b.dataset.l === lang));
  const phone = $("phone")?.value;
  $("demo-row").innerHTML = [
    ["9876543210", "Sunita", t("farmer")],
    ["9876543211", "Ramesh", t("fpo")],
    ["9876543212", "Priya", t("buyer")],
    ["9876543213", "MSInS", t("adminRole")],
  ]
    .map(
      ([p, n, r]) =>
        `<button type="button" class="chip${phone === p ? " active" : ""}" data-p="${p}"><b>${n}</b><span>${r} · ${p.slice(-4)}</span></button>`
    )
    .join("");
}

function roleLabel(r) {
  return { farmer: t("farmer"), fpo: t("fpo"), buyer: t("buyer"), admin: t("adminRole") }[r] || r;
}
function dashSub() {
  return { farmer: t("dashSubFarmer"), fpo: t("dashSubFpo"), buyer: t("dashSubBuyer"), admin: t("dashSubAdmin") }[user.role] || "";
}

const NAV = [
  { id: "dash", roles: ["farmer", "fpo", "buyer", "admin"], icon: "⌂" },
  { id: "create", roles: ["farmer", "fpo"], icon: "＋" },
  { id: "lots", roles: ["farmer", "fpo", "buyer", "admin"], icon: "▤" },
  { id: "match", roles: ["farmer", "fpo"], icon: "◎" },
  { id: "offers", roles: ["farmer", "fpo", "buyer"], icon: "₹" },
  { id: "deals", roles: ["farmer", "fpo", "buyer", "admin"], icon: "▣" },
  { id: "logistics", roles: ["farmer", "fpo", "buyer"], icon: "🚚" },
  { id: "alerts", roles: ["farmer", "fpo", "buyer"], icon: "🔔" },
  { id: "reports", roles: ["farmer", "fpo", "admin"], icon: "▦" },
  { id: "admin", roles: ["admin"], icon: "⚑" },
];

function renderNav() {
  $("nav").innerHTML = NAV.filter((n) => n.roles.includes(user.role))
    .map((n) => `<a href="#${n.id}" class="${route === n.id ? "active" : ""}"><span class="ico">${n.icon}</span><span>${t(n.id)}</span></a>`)
    .join("");
  $("btn-logout").textContent = t("logout");
  $("btn-speak-page").textContent = "🔊  " + t("speak");
}

function closeMenu() {
  $("sidebar")?.classList.remove("open");
  $("nav-scrim").hidden = true;
}

function askModal({ title, sub, value = "", type = "number", placeholder = "" }) {
  return new Promise((resolve) => {
    const box = $("modal");
    $("modal-title").textContent = title;
    $("modal-sub").textContent = sub || "";
    const input = $("modal-input");
    input.type = type === "text" ? "text" : "number";
    input.value = value;
    input.placeholder = placeholder;
    input.hidden = false;
    box.hidden = false;
    input.focus();
    const done = (val) => {
      box.hidden = true;
      $("modal-ok").onclick = null;
      $("modal-cancel").onclick = null;
      resolve(val);
    };
    $("modal-cancel").onclick = () => done(null);
    $("modal-ok").onclick = () => done(input.value);
    input.onkeydown = (e) => {
      if (e.key === "Enter") done(input.value);
      if (e.key === "Escape") done(null);
    };
  });
}

async function showApp() {
  setShell(true);
  $("who-name").textContent = user.name;
  $("who-role").textContent = roleLabel(user.role);
  $("who-name-side").textContent = user.name;
  $("who-role-side").textContent = roleLabel(user.role);
  $("lang-select").innerHTML = ["mr", "hi", "en"]
    .map((l) => `<option value="${l}" ${l === lang ? "selected" : ""}>${l.toUpperCase()}</option>`)
    .join("");
  renderNav();
  await go(location.hash.replace("#", "") || "dash");
}

async function go(id) {
  queued = (id || "dash").replace(/^#/, "") || "dash";
  if (going) return;
  going = true;
  try {
    while (queued) {
      route = queued;
      queued = null;
      if (location.hash.replace("#", "") !== route) location.hash = route;
      $("page-title").textContent = t(route);
      $("page-sub").textContent = route === "dash" ? dashSub() : "";
      renderNav();
      closeMenu();
      const view = $("view");
      view.innerHTML = `<p class="spinner">${t("loading")}</p>`;
      const fn = PAGES[route] || PAGES.dash;
      try {
        await fn(view);
      } catch (err) {
        view.innerHTML = `<div class="card empty"><p>${t("loadError")}</p><p class="muted">${err.message}</p><button class="btn primary" id="retry-page">${t("retry")}</button></div>`;
        $("retry-page").onclick = () => go(route);
      }
    }
  } finally {
    going = false;
    if (queued) go(queued);
  }
}

function drawChart(fc) {
  const ctx = document.getElementById("priceChart");
  if (!ctx || !window.Chart) return;
  if (chartInst) chartInst.destroy();
  const hist = fc.history_30 || [];
  const labels = hist.map((h) => h.date.slice(5)).concat(fc.forecast.map((f) => f.date.slice(5)));
  const histPad = (arr) => Array(hist.length).fill(null).concat(arr);
  chartInst = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "High",
          data: histPad(fc.forecast.map((f) => f.high)),
          borderColor: "transparent",
          backgroundColor: "rgba(201,162,39,0.16)",
          fill: "+1",
          pointRadius: 0,
          tension: 0.3,
        },
        {
          label: "Low",
          data: histPad(fc.forecast.map((f) => f.low)),
          borderColor: "transparent",
          pointRadius: 0,
          tension: 0.3,
        },
        {
          label: "Modal",
          data: hist.map((h) => h.modal).concat(Array(fc.forecast.length).fill(null)),
          borderColor: "#217a38",
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "Forecast",
          data: histPad(fc.forecast.map((f) => f.predicted)),
          borderColor: "#c9a227",
          borderDash: [5, 4],
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, maxRotation: 0, autoSkip: true } },
        y: { ticks: { callback: (v) => "₹" + v } },
      },
    },
  });
}

function mandiForUser() {
  if (["Mumbai", "Pune", "Nagpur", "Aurangabad"].includes(user.district)) return user.district;
  return "Nashik";
}

function bindGo(el) {
  el.querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => go(b.dataset.go)));
}

async function farmerDash(el) {
  const mandi = mandiForUser();
  const [board, fc, lots, offers] = await Promise.all([
    api("/prices"),
    api(`/forecast/${dashCrop}?mandi=${encodeURIComponent(mandi)}&horizon=14&urgency=high`),
    api("/lots/mine"),
    api("/offers").catch(() => []),
  ]);
  const rec = fc.recommendation;
  const pending = offers.filter((o) => o.status === "pending").length;
  const last = fc.forecast.at(-1);
  el.innerHTML = `
    <div class="hero-banner">
      <div class="card">
        <p class="greet">${t("welcome")}, ${user.name.split(" ")[0]}</p>
        <p class="muted">${user.district} · ${roleLabel(user.role)}</p>
        <div class="crop-row">
          <label for="dash-crop">${t("cropSelect")}</label>
          <select id="dash-crop">${meta.commodities.map((c) => `<option value="${c}" ${c === dashCrop ? "selected" : ""}>${cap(c)}</option>`).join("")}</select>
        </div>
        <div class="actions">
          <button class="btn primary" data-go="create">${t("quickList")}</button>
          <button class="btn" data-go="offers">${t("viewOffers")} (${pending})</button>
        </div>
      </div>
      <div class="card">
        <p class="kpi-label">${t("rec")}</p>
        <span class="pill ${rec.action === "store" ? "store" : "sell"}">${rec.action === "store" ? t("store") : t("sellNow")}</span>
        <p style="margin-top:10px">${rec.reason}</p>
        <p class="muted">${t("confidence")} ${(rec.confidence * 100).toFixed(0)}%</p>
      </div>
    </div>
    <div class="grid kpis" style="margin-top:16px">
      <div class="card"><p class="kpi-label">${t("current")} · ${cap(dashCrop)} · ${mandi}</p><div class="stat">${rupee(fc.current_modal)} <small>${t("perQtl")}</small></div></div>
      <div class="card"><p class="kpi-label">${t("forecast")}</p><div class="stat">${rupee(last.predicted)}</div><p class="muted">${rupee(last.low)} – ${rupee(last.high)}</p></div>
      <div class="card"><p class="kpi-label">${t("lots")}</p><div class="stat">${lots.length}</div><p class="muted">${t("pending")} ${pending}</p></div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-head"><h3>${t("forecast")}</h3></div>
      <div class="chart-box"><canvas id="priceChart"></canvas></div>
    </div>
    <div class="card" style="margin-top:16px">
      <h3>${t("otherMandis")}</h3>
      <div class="table-wrap"><table class="table">
        <thead><tr><th>${t("mandi")}</th><th>Modal</th><th>${t("arrival")}</th></tr></thead>
        <tbody>${(board[dashCrop] || []).map((m) => `<tr><td>${m.mandi}</td><td>${rupee(m.modal)}</td><td>${m.arrival}</td></tr>`).join("")}</tbody>
      </table></div>
    </div>`;
  drawChart(fc);
  bindGo(el);
  $("dash-crop").onchange = () => {
    dashCrop = $("dash-crop").value;
    go("dash");
  };
}

async function fpoDash(el) {
  const [lots, offers, admin, logistics] = await Promise.all([
    api("/lots/mine"),
    api("/offers"),
    api("/reports/admin").catch(() => null),
    api("/logistics"),
  ]);
  const pending = offers.filter((o) => o.status === "pending");
  el.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <p class="greet">${t("welcome")}, ${user.name.split(" ")[0]}</p>
      <p class="muted">Godavari Agro FPO · ${user.district}</p>
      <div class="actions">
        <button class="btn primary" data-go="lots">${t("lots")}</button>
        <button class="btn" data-go="offers">${t("viewOffers")}</button>
        <button class="btn" data-go="logistics">${t("logistics")}</button>
      </div>
    </div>
    <div class="grid kpis">
      <div class="card"><p class="kpi-label">${t("lots")}</p><div class="stat">${lots.length}</div></div>
      <div class="card"><p class="kpi-label">${t("pending")}</p><div class="stat">${pending.length}</div></div>
      <div class="card"><p class="kpi-label">${t("gmv")}</p><div class="stat">${admin ? rupee(admin.gmv) : "—"}</div></div>
      <div class="card"><p class="kpi-label">${t("logistics")}</p><div class="stat">${logistics.pools.length}</div></div>
    </div>
    <div class="card" style="margin-top:16px">
      <h3>${t("lots")}</h3>
      <div class="table-wrap"><table class="table">
        <thead><tr><th>${t("farmerName")}</th><th>${t("crop")}</th><th>${t("qty")}</th><th>${t("status")}</th></tr></thead>
        <tbody>${
          lots.map((l) => `<tr><td>${l.farmer_name}</td><td>${cap(l.commodity)}</td><td>${l.quantity_kg} kg</td><td><span class="pill ok">${l.status}</span></td></tr>`).join("") ||
          `<tr><td colspan="4">${t("emptyLots")}</td></tr>`
        }</tbody>
      </table></div>
    </div>`;
  bindGo(el);
}

async function buyerDash(el) {
  const mandi = mandiForUser();
  const [lots, offers, fc] = await Promise.all([
    api("/lots/mine"),
    api("/offers"),
    api(`/forecast/onion?mandi=${encodeURIComponent(mandi)}&horizon=14`),
  ]);
  const open = lots.filter((l) => l.status === "listed" || l.status === "offered");
  el.innerHTML = `
    <div class="hero-banner">
      <div class="card">
        <p class="greet">${t("welcome")}, ${user.name.split(" ")[0]}</p>
        <p class="muted">${roleLabel("buyer")} · ${user.district} · ${t("trust")} ${user.trust_score || "—"}</p>
        <div class="actions">
          <button class="btn primary" data-go="lots">${t("openLots")}</button>
          <button class="btn" data-go="offers">${t("offers")}</button>
        </div>
      </div>
      <div class="card">
        <p class="kpi-label">Onion · ${mandi}</p>
        <div class="stat">${rupee(fc.current_modal)} <small>${t("perQtl")}</small></div>
        <p class="muted">${t("forecast")} ${rupee(fc.forecast.at(-1).predicted)}</p>
      </div>
    </div>
    <div class="grid kpis" style="margin-top:16px">
      <div class="card"><p class="kpi-label">${t("openLots")}</p><div class="stat">${open.length}</div></div>
      <div class="card"><p class="kpi-label">${t("offers")}</p><div class="stat">${offers.length}</div></div>
    </div>
    <div class="grid cards" style="margin-top:16px">
      ${
        open
          .map(
            (l) => `<div class="card">
          <div class="card-head"><h3>${cap(l.commodity)}</h3><span class="pill ok">${l.status}</span></div>
          <p>${l.quantity_kg} kg · Grade ${l.grade}</p>
          <p class="muted">${l.farmer_name} · ${l.location_name}</p>
          <div class="actions"><button class="btn primary offer" data-id="${l.id}">${t("placeOffer")}</button></div>
        </div>`
          )
          .join("") || `<div class="card empty">${t("emptyLots")}</div>`
      }
    </div>`;
  bindGo(el);
  wireOffers(el);
}

async function adminDash(el) {
  const a = await api("/reports/admin");
  el.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <p class="greet">${t("welcome")}, ${user.name.split(" ")[0]}</p>
      <p class="muted">${t("gov")}</p>
    </div>
    <div class="grid kpis">
      <div class="card"><p class="kpi-label">${t("users")}</p><div class="stat">${a.adoption.active_users}</div>
        <p class="muted">F ${a.adoption.farmers} · FPO ${a.adoption.fpos} · B ${a.adoption.buyers}</p></div>
      <div class="card"><p class="kpi-label">${t("gmv")}</p><div class="stat">${rupee(a.gmv)}</div></div>
      <div class="card"><p class="kpi-label">${t("disputes")}</p><div class="stat">${a.dispute_rate_pct}%</div></div>
      <div class="card"><p class="kpi-label">${t("voicePct")}</p><div class="stat">${a.voice_listing_pct}%</div></div>
      <div class="card"><p class="kpi-label">${t("forecastOk")}</p><div class="stat">${a.forecast_validated_pct}%</div></div>
      <div class="card"><p class="kpi-label">${t("pipeline")}</p><p>${a.pipeline}</p></div>
    </div>`;
}

function wireOffers(el) {
  el.querySelectorAll(".offer").forEach((b) => (b.onclick = async () => {
    const price = await askModal({ title: t("offerTitle"), sub: t("offerSub"), value: "1800" });
    if (!price) return;
    await api("/offers", { method: "POST", body: JSON.stringify({ lot_id: Number(b.dataset.id), price_offered: Number(price) }) });
    toast(t("offers"));
    go("offers");
  }));
}

const PAGES = {
  async dash(el) {
    if (user.role === "buyer") return buyerDash(el);
    if (user.role === "admin") return adminDash(el);
    if (user.role === "fpo") return fpoDash(el);
    return farmerDash(el);
  },

  async create(el) {
    el.innerHTML = `
      <div class="grid cols-2">
        <div class="card voice-box">
          <p>${t("voiceHint")}</p>
          <button class="mic" id="mic" type="button" aria-label="Mic">🎤</button>
          <p id="voice-status" class="muted"></p>
          <textarea id="voice-text" rows="3" placeholder="420 किलो ग्रेड ए टोमॅटो नाशिक"></textarea>
          <button class="btn" id="parse" type="button">${t("parseVoice")}</button>
        </div>
        <form class="card form-grid" id="lot-form">
          <label for="commodity">${t("crop")}</label>
          <select id="commodity">${meta.commodities.map((c) => `<option value="${c}">${cap(c)}</option>`).join("")}</select>
          <label for="qty">${t("qty")}</label><input id="qty" type="number" min="1" value="100" />
          <label for="grade">${t("grade")}</label><select id="grade"><option>A</option><option selected>B</option><option>C</option></select>
          <label for="hdate">${t("harvest")}</label><input id="hdate" type="date" />
          <label for="urg">${t("urgency")}</label>
          <select id="urg"><option value="high">High</option><option value="medium" selected>Medium</option><option value="low">Low</option></select>
          <button class="btn primary big" type="submit">${t("createLot")}</button>
        </form>
      </div>`;
    $("hdate").value = new Date().toISOString().slice(0, 10);
    const Recog = window.SpeechRecognition || window.webkitSpeechRecognition;
    $("mic").onclick = () => {
      if (!Recog) {
        toast("Type in the box, or use Chrome/Edge for voice");
        return;
      }
      const r = new Recog();
      r.lang = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" }[lang];
      r.onstart = () => {
        $("mic").classList.add("live");
        $("voice-status").textContent = t("listening");
      };
      r.onend = () => $("mic").classList.remove("live");
      r.onresult = (e) => {
        $("voice-text").value = e.results[0][0].transcript;
      };
      r.start();
    };
    $("parse").onclick = async () => {
      const parsed = await api("/lots/transcribe", {
        method: "POST",
        body: JSON.stringify({ voice_text: $("voice-text").value, language: lang }),
      });
      $("commodity").value = parsed.commodity;
      $("qty").value = parsed.quantity_kg;
      $("grade").value = parsed.grade;
      $("hdate").value = parsed.harvest_date;
      $("urg").value = parsed.liquidity_urgency;
      toast(t("parseVoice"));
    };
    $("lot-form").onsubmit = async (e) => {
      e.preventDefault();
      const lot = await api("/lots", {
        method: "POST",
        body: JSON.stringify({
          commodity: $("commodity").value,
          quantity_kg: Number($("qty").value),
          grade: $("grade").value,
          harvest_date: $("hdate").value,
          voice_text: $("voice-text").value || null,
          language: lang,
          liquidity_urgency: $("urg").value,
          location_name: user.district,
        }),
      });
      toast("Lot #" + lot.id);
      go("lots");
    };
  },

  async lots(el) {
    const lots = await api("/lots/mine");
    if (!lots.length) {
      el.innerHTML = `<div class="card empty"><p>${t("emptyLots")}</p>${user.role !== "buyer" ? `<button class="btn primary" data-go="create">${t("create")}</button>` : ""}</div>`;
      bindGo(el);
      return;
    }
    el.innerHTML = `<div class="grid cards">${lots
      .map(
        (l) => `<div class="card lot-card">
        <div class="card-head">
          <h3>${cap(l.commodity)}</h3>
          <span class="pill ok">${l.status}</span>
        </div>
        <p>${l.quantity_kg} kg · Grade ${l.grade}${l.created_via_voice ? " · 🎤" : ""}</p>
        <p class="muted">${l.farmer_name || ""} · ${l.location_name} · ${l.harvest_date}</p>
        <div class="qr">${l.qr_code ? `<img alt="Lot QR" src="${l.qr_code}" />` : ""}</div>
        ${
          user.role === "buyer"
            ? `<button class="btn primary offer" data-id="${l.id}">${t("placeOffer")}</button>`
            : `<button class="btn match" data-id="${l.id}">${t("findBuyers")}</button>`
        }
      </div>`
      )
      .join("")}</div>`;
    el.querySelectorAll(".match").forEach((b) => (b.onclick = () => {
      sessionStorage.setItem("lot_id", b.dataset.id);
      go("match");
    }));
    wireOffers(el);
  },

  async match(el) {
    const lots = await api("/lots/mine");
    const listed = lots.filter((l) => l.status === "listed" || l.status === "offered");
    const pick = Number(sessionStorage.getItem("lot_id")) || (listed[0] && listed[0].id);
    if (!pick) {
      el.innerHTML = `<div class="card empty"><p>${t("emptyLots")}</p><button class="btn primary" data-go="create">${t("create")}</button></div>`;
      bindGo(el);
      return;
    }
    const buyers = await api(`/buyers/matches?lot_id=${pick}`);
    el.innerHTML = `<p class="muted" style="margin-bottom:12px">Lot #${pick}</p><div class="grid cards">${buyers
      .map(
        (b) => `<div class="card">
        <div class="card-head"><h3>${b.name}</h3>${b.verified ? `<span class="pill store">${t("verified")}</span>` : ""}</div>
        <p>${t("trust")} ${b.trust_score} · ${b.distance_km} km · ${b.district}</p>
        <div class="trust"><i style="width:${Math.min(100, b.trust_score)}%"></i></div>
        <p class="muted">On-time ${b.on_time_payment_pct}% · Quality ${b.quality_accept_pct}% · ${t("disputes")} ${b.dispute_count}</p>
      </div>`
      )
      .join("")}</div>`;
  },

  async offers(el) {
    const rows = await api("/offers");
    el.innerHTML = `<div class="card table-wrap"><table class="table"><thead><tr><th>ID</th><th>${t("crop")}</th><th>${t("buyer")}</th><th>₹/qtl</th><th>${t("status")}</th><th></th></tr></thead>
      <tbody>${
        rows
          .map(
            (o) => `<tr>
        <td>${o.id}</td><td>${cap(o.commodity)} (${o.quantity_kg}kg)</td><td>${o.buyer_name}</td>
        <td>${o.price_offered}</td><td><span class="pill held">${o.status}</span></td>
        <td class="row-actions">${
          ["farmer", "fpo"].includes(user.role) && o.status === "pending"
            ? `<button class="btn primary acc" data-id="${o.id}">${t("accept")}</button>
               <button class="btn rej" data-id="${o.id}">${t("reject")}</button>
               <button class="btn ctr" data-id="${o.id}">${t("counter")}</button>`
            : ""
        }</td></tr>`
          )
          .join("") || `<tr><td colspan="6">${t("emptyOffers")}</td></tr>`
      }</tbody></table></div>`;
    el.querySelectorAll(".acc").forEach((b) => (b.onclick = async () => {
      await api(`/offers/${b.dataset.id}/accept`, { method: "POST" });
      toast(t("deals"));
      go("deals");
    }));
    el.querySelectorAll(".rej").forEach((b) => (b.onclick = async () => {
      await api(`/offers/${b.dataset.id}/reject`, { method: "POST" });
      go("offers");
    }));
    el.querySelectorAll(".ctr").forEach((b) => (b.onclick = async () => {
      const p = await askModal({ title: t("counterTitle"), sub: t("offerSub") });
      if (!p) return;
      await api(`/offers/${b.dataset.id}/counter`, { method: "POST", body: JSON.stringify({ price_offered: Number(p) }) });
      go("offers");
    }));
  },

  async deals(el) {
    const rows = await api("/transactions");
    el.innerHTML = `<div class="grid cards">${
      rows
        .map(
          (row) => `<div class="card">
        <div class="card-head"><h3>${cap(row.commodity) || "Deal"}</h3>
          <span class="pill ${row.escrow_status === "released" ? "ok" : "held"}">${row.escrow_status}</span></div>
        <div class="stat">${rupee(row.amount)}</div>
        <p>${row.farmer_name || ""} → ${row.buyer_name || ""}</p>
        <p class="muted">${row.payment_ref}</p>
        <div class="actions">
        ${row.escrow_status === "held" ? `<button class="btn primary conf" data-id="${row.id}">${t("confirmDelivery")}</button>` : ""}
        ${row.escrow_status !== "disputed" ? `<button class="btn danger disp" data-id="${row.id}">${t("flagDispute")}</button>` : ""}
        </div>
      </div>`
        )
        .join("") || `<div class="card empty">${t("emptyDeals")}</div>`
    }</div>`;
    el.querySelectorAll(".conf").forEach((b) => (b.onclick = async () => {
      await api(`/transactions/${b.dataset.id}/confirm-delivery`, { method: "POST" });
      go("deals");
    }));
    el.querySelectorAll(".disp").forEach((b) => (b.onclick = async () => {
      const reason = await askModal({ title: t("disputeTitle"), sub: t("disputeSub"), type: "text" });
      if (!reason) return;
      await api("/disputes", { method: "POST", body: JSON.stringify({ transaction_id: Number(b.dataset.id), reason, evidence_url: "" }) });
      toast(t("flagDispute"));
      go("deals");
    }));
  },

  async logistics(el) {
    const data = await api("/logistics");
    el.innerHTML = `<div class="grid cols-2">
      <div class="card"><h3>${t("pooled")}</h3>
        ${data.pools.map((p) => `<p><strong>${cap(p.commodity)}</strong> · ${p.hub} · ${p.total_kg} kg<br/><span class="muted">${p.suggested_vehicle} · ${rupee(p.est_cost_share_inr)} · ${p.lots.length} lots</span></p>`).join("") || `<p class="muted">${t("noneYet")}</p>`}
      </div>
      <div class="card"><h3>${t("cold")}</h3>
        ${data.cold_storage.map((s) => `<p>${s.name}<br/><span class="muted">${s.available_mt} MT · ${rupee(s.cost_per_kg_day)}/kg/day</span></p>`).join("")}
      </div></div>`;
  },

  async alerts(el) {
    const rows = await api("/alerts");
    el.innerHTML = `
      <form class="card form-grid" id="alert-form" style="margin-bottom:16px">
        <div class="grid cols-3">
          <select id="ac">${meta.commodities.map((c) => `<option value="${c}">${cap(c)}</option>`).join("")}</select>
          <select id="am">${meta.mandis.map((m) => `<option>${m}</option>`).join("")}</select>
          <input id="ath" type="number" placeholder="₹ / qtl" />
        </div>
        <button class="btn primary" type="submit">${t("armAlert")}</button>
      </form>
      <div class="card">${rows.map((a) => `<p>${cap(a.commodity)} @ ${a.mandi} ${a.direction} ${rupee(a.threshold)} · ${a.current ? rupee(a.current) : "—"} ${a.triggered ? "<span class='pill sell'>!</span>" : ""}</p>`).join("") || t("noneYet")}</div>`;
    $("alert-form").onsubmit = async (e) => {
      e.preventDefault();
      await api("/alerts", { method: "POST", body: JSON.stringify({ commodity: $("ac").value, mandi: $("am").value, threshold: Number($("ath").value), direction: "above" }) });
      go("alerts");
    };
  },

  async reports(el) {
    if (user.role === "admin") return adminDash(el);
    let farmerId = user.id;
    if (user.role === "fpo") {
      const lots = await api("/lots/mine");
      farmerId = lots[0]?.farmer_id || user.id;
    }
    const data = await api(`/reports/farmer/${farmerId}`);
    el.innerHTML = `
      <div class="grid kpis">
        <div class="card"><p class="kpi-label">${t("income")}</p><div class="stat">${rupee(data.income_realized)}</div></div>
        <div class="card"><p class="kpi-label">${t("vsMandi")}</p><div class="stat">${data.uplift_pct}%</div></div>
        <div class="card"><p class="kpi-label">${t("lots")}</p><div class="stat">${data.lots}</div></div>
      </div>
      <div class="actions" style="margin:16px 0">
        <button class="btn" id="csv" type="button">${t("downloadCsv")}</button>
        <button class="btn" id="pdf" type="button">${t("printPdf")}</button>
      </div>
      <div class="card table-wrap"><table class="table"><thead><tr><th>${t("crop")}</th><th>${t("income")}</th><th>${t("mandi")}</th><th>%</th></tr></thead>
      <tbody>${data.transactions.map((r) => `<tr><td>${cap(r.commodity)}</td><td>${rupee(r.realized)}</td><td>${rupee(r.mandi_equiv)}</td><td>${r.uplift_pct}%</td></tr>`).join("") || `<tr><td colspan="4">${t("noneYet")}</td></tr>`}</tbody></table></div>`;
    $("pdf").onclick = () => window.print();
    $("csv").onclick = async () => {
      const res = await fetch(`/reports/farmer/${data.farmer.id}/csv`, { headers: { Authorization: `Bearer ${token}` } });
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `kisansetu-farmer-${data.farmer.id}.csv`;
      a.click();
    };
  },

  async admin(el) {
    return adminDash(el);
  },
};

function bootLogin() {
  $("login-lang").innerHTML = ["mr", "hi", "en"]
    .map((l) => `<button type="button" class="chip" data-l="${l}">${l.toUpperCase()}</button>`)
    .join("");
  applyLoginI18n();
  $("login-lang").onclick = (e) => {
    const l = e.target.dataset.l;
    if (!l) return;
    lang = l;
    localStorage.setItem("ks_lang", lang);
    applyLoginI18n();
  };
  $("phone").addEventListener("input", () => {
    $("phone").value = $("phone").value.replace(/\D/g, "").slice(0, 10);
  });
  $("demo-row").onclick = (e) => {
    const btn = e.target.closest("[data-p]");
    if (!btn) return;
    $("phone").value = btn.dataset.p;
    $("demo-row").querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === btn));
  };
  $("btn-otp").onclick = async () => {
    $("login-msg").classList.remove("err");
    try {
      const r = await api("/auth/otp/request", { method: "POST", body: JSON.stringify({ phone: $("phone").value }) });
      $("otp-block").hidden = false;
      $("step-otp").classList.add("on");
      $("login-msg").textContent = r.message;
      $("otp").value = r.demo_otp;
      $("otp").focus();
    } catch (err) {
      $("login-msg").classList.add("err");
      $("login-msg").textContent = err.message;
    }
  };
  $("login-form").onsubmit = async (e) => {
    e.preventDefault();
    $("login-msg").classList.remove("err");
    try {
      const r = await api("/auth/otp/verify", {
        method: "POST",
        body: JSON.stringify({ phone: $("phone").value, code: $("otp").value }),
      });
      token = r.access_token;
      user = r.user;
      lang = localStorage.getItem("ks_lang") || user.language || lang;
      localStorage.setItem("ks_token", token);
      localStorage.setItem("ks_user", JSON.stringify(user));
      localStorage.setItem("ks_lang", lang);
      await showApp();
    } catch (err) {
      $("login-msg").classList.add("err");
      $("login-msg").textContent = err.message;
    }
  };
}

window.addEventListener("hashchange", () => {
  const next = location.hash.replace("#", "") || "dash";
  if (next !== route) go(next);
});
document.addEventListener("click", () => (lastActive = Date.now()));
setInterval(() => {
  if (token && Date.now() - lastActive > IDLE_MS) logout(true);
}, 30000);

$("lang-select").onchange = async () => {
  lang = $("lang-select").value;
  localStorage.setItem("ks_lang", lang);
  try {
    await api("/auth/language", { method: "POST", body: JSON.stringify({ language: lang }) });
  } catch (_) {}
  applyLoginI18n();
  renderNav();
  $("who-role").textContent = roleLabel(user.role);
  $("who-role-side").textContent = roleLabel(user.role);
  go(route);
};
$("btn-logout").onclick = () => logout(true);
$("menu-btn").onclick = () => {
  $("sidebar").classList.toggle("open");
  $("nav-scrim").hidden = !$("sidebar").classList.contains("open");
};
$("nav-scrim").onclick = closeMenu;
$("btn-speak-page").onclick = () => speak($("page-title").textContent + ". " + $("page-sub").textContent);

(async function init() {
  bootLogin();
  try {
    meta = await fetch("/meta").then((r) => r.json());
  } catch (_) {}
  if (token && user) {
    try {
      user = await api("/auth/me");
      await showApp();
    } catch (_) {
      logout(false);
    }
  }
})();
