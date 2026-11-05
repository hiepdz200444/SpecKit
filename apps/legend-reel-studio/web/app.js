/* Legends Reel Studio — SPA (bài báo · ảnh nghệ sĩ · text & voice) */
(() => {
  "use strict";

  // ------------------------------------------------------------------ utils
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad2 = (n) => String(n).padStart(2, "0");
  const isoToday = () => {
    const d = new Date();
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  };
  const fmtLong = (iso) => {
    if (!iso) return "—";
    const [y, m, d] = String(iso).split("-").map(Number);
    if (!y || !m || !d) return String(iso);
    return `${pad2(d)}/${pad2(m)}/${y}`;
  };
  const fmtDateTime = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  };
  const wordCount = (t) => (String(t || "").trim().match(/[A-Za-z0-9']+/g) || []).length;
  const clamp = (n, a, b) => Math.max(a, Math.min(b, n));

  const ICON = {
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>',
    save: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 3h11l3 3v15H5z"/><path d="M8 3v6h8V3"/><path d="M8 14h8v7H8z"/></svg>',
    refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 11a8 8 0 1 0-2.3 6"/><path d="M20 4v7h-7"/></svg>',
    download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M4 21h16"/></svg>',
    copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 14h10l1-14"/></svg>',
    back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M15 5l-7 7 7 7"/></svg>',
    image: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="m4 19 5-5 4 4 3-3 4 4"/></svg>',
    spark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"/></svg>',
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>',
    mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v3"/></svg>',
    zip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 3h12v18H6z"/><path d="M12 3v6M12 12v2M12 17v2"/></svg>',
    link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 13 4 4L19 7"/></svg>',
    globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 3 2.5 15 0 18M12 3c-2.5 3-2.5 15 0 18"/></svg>',
  };

  const state = {
    boot: null,
    route: { name: "dashboard", id: null },
    filters: { date: isoToday(), window: 7, q: "", kinds: [] },
    project: null,
    tab: "article",
    suggest: null,
    browserOnly: false,
    zipHint: false,
    saving: null,
    rivalFilters: { q: "", platform: "", sort: "score", page: "", onlyViral: false, onlyUnused: false },
    rivalReels: [],
    rivalPages: [],
  };

  // ------------------------------------------------------------------ api
  async function api(path, opts = {}) {
    const config = { ...opts, headers: { ...(opts.headers || {}) } };
    if (config.body && !(config.body instanceof FormData) && typeof config.body !== "string") {
      config.body = JSON.stringify(config.body);
      config.headers["Content-Type"] = "application/json";
    }
    const res = await fetch(path, config);
    if (!res.ok) {
      let msg = `Lỗi ${res.status}`;
      try {
        const data = await res.json();
        msg = data.detail || data.message || msg;
      } catch (_) { /* not json */ }
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    if (res.status === 204) return null;
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  }

  function toast(message, type = "") {
    const host = $("#toasts");
    if (!host) return;
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${type === "ok" ? "✓" : type === "err" ? "!" : "•"}</span><span>${esc(message)}</span>`;
    host.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(6px)";
      el.style.transition = "0.25s ease";
      setTimeout(() => el.remove(), 260);
    }, 3800);
  }

  function confirmDialog(title, text, confirmLabel = "Xoá") {
    return new Promise((resolve) => {
      const root = $("#modal-root");
      root.innerHTML = `
        <div class="modal-back">
          <div class="modal">
            <h3>${esc(title)}</h3>
            <p>${esc(text)}</p>
            <div class="modal-actions">
              <button class="btn btn-ghost" data-act="cancel">Huỷ</button>
              <button class="btn btn-danger" data-act="ok">${esc(confirmLabel)}</button>
            </div>
          </div>
        </div>`;
      const close = (val) => { root.innerHTML = ""; resolve(val); };
      $('[data-act="cancel"]', root).onclick = () => close(false);
      $('[data-act="ok"]', root).onclick = () => close(true);
      $(".modal-back", root).onclick = (e) => { if (e.target.classList.contains("modal-back")) close(false); };
    });
  }

  async function copyText(text, label = "Đã copy") {
    const value = String(text ?? "");
    try {
      await navigator.clipboard.writeText(value);
      toast(label, "ok");
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = value;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (_e) { /* ignore */ }
      ta.remove();
      toast(label, "ok");
    }
  }

  const STATUS_ORDER = ["draft", "article", "script", "ready", "scheduled", "published"];
  const STATUS_LABEL = {
    draft: "Nháp",
    article: "Đã có bài báo",
    script: "Đã có text & voice",
    ready: "Sẵn sàng đăng",
    scheduled: "Đã lên lịch",
    published: "Đã đăng",
  };
  const KIND_LABEL = { birthday: "Sinh nhật", memorial: "Ngày mất", release: "Kỷ niệm phát hành", milestone: "Cột mốc", custom: "Sự kiện" };
  const KIND_TAG = { birthday: "tag-accent", memorial: "tag-violet", release: "tag-ok", milestone: "tag-warn", custom: "tag-warn" };
  const statusChip = (s) => `<span class="status status-${esc(s || "draft")}">${esc(STATUS_LABEL[s] || s || "Nháp")}</span>`;
  const daysLabel = (n) => {
    if (n === 0) return "Hôm nay";
    if (n === 1) return "Ngày mai";
    if (n === -1) return "Hôm qua";
    return n > 0 ? `Còn ${n} ngày` : `${Math.abs(n)} ngày trước`;
  };

  function mdLite(text) {
    const lines = String(text || "").split("\n");
    const out = [];
    let list = [];
    const flush = () => {
      if (list.length) { out.push(`<ul class="md-list">${list.join("")}</ul>`); list = []; }
    };
    for (const raw of lines) {
      const line = raw.trimEnd();
      if (!line.trim()) { flush(); out.push('<div style="height:10px"></div>'); continue; }
      const safe = esc(line)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener" style="color:#a8731a">$1</a>');
      if (safe.startsWith("## ")) {
        flush();
        out.push(`<h4 class="md-h">${safe.slice(3)}</h4>`);
        continue;
      }
      if (safe.startsWith("- ")) { list.push(`<li>${safe.slice(2)}</li>`); continue; }
      flush();
      out.push(`<p class="md-p">${safe}</p>`);
    }
    flush();
    return out.join("");
  }

  // ------------------------------------------------------------------ routing
  const NAV_HASH = { dashboard: "#/", discover: "#/discover", projects: "#/projects", rivals: "#/rivals", howto: "#/howto" };
  const ROUTE_NAME = { dashboard: "Tổng quan", discover: "Khám phá sự kiện", projects: "Dự án reels", rivals: "Reels đối thủ", project: "Studio", howto: "Cách hoạt động" };
  const ROUTES = { "": "dashboard", "#/": "dashboard", "#/discover": "discover", "#/projects": "projects", "#/rivals": "rivals", "#/howto": "howto" };

  function parseHash() {
    const hash = location.hash || "#/";
    if (hash.startsWith("#/project/")) return { name: "project", id: hash.split("/")[2] };
    return { name: ROUTES[hash] || "dashboard", id: null };
  }

  function setActiveNav(name) {
    $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.nav === name));
  }

  // Một lần render tại một thời điểm: nếu người dùng bấm/nav sang màn khác khi
  // màn trước còn đang chờ API, lần render cũ không được ghi đè lên màn mới.
  let routeBusy = false;
  let routePending = false;

  async function route() {
    if (routeBusy) {
      routePending = true;
      return;
    }
    routeBusy = true;
    try {
      do {
        routePending = false;
        await renderRoute();
      } while (routePending);
    } finally {
      routeBusy = false;
    }
  }

  async function renderRoute() {
    state.route = parseHash();
    const view = $("#view");
    if (!view) return;
    view.classList.remove("fade-in");
    void view.offsetWidth;
    view.classList.add("fade-in");
    setActiveNav(state.route.name);
    $("#crumb").innerHTML =
      state.route.name === "project"
        ? `<span style="opacity:.6">Dự án</span> <span style="opacity:.4">/</span> <strong>Studio</strong>`
        : `<strong>${ROUTE_NAME[state.route.name] || "Tổng quan"}</strong>`;
    try {
      if (state.route.name === "dashboard") await viewDashboard();
      else if (state.route.name === "discover") await viewDiscover();
      else if (state.route.name === "projects") await viewProjects();
      else if (state.route.name === "rivals") await viewRivals();
      else if (state.route.name === "project") await viewProject(state.route.id);
      else viewHowto();
    } catch (err) {
      view.innerHTML = `<div class="empty"><h3>Không tải được màn hình</h3><p>${esc(err.message)}</p><button class="btn" id="btn-reload">Tải lại</button></div>`;
      const btn = $("#btn-reload");
      if (btn) btn.onclick = () => route();
    }
    updateSidebar();
    if (typeof window.scrollTo === "function") {
      try { window.scrollTo({ top: 0, behavior: "instant" }); } catch (_) { /* jsdom */ }
    }
  }

  function bindNav() {
    $$("[data-nav]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = NAV_HASH[btn.dataset.nav] || "#/";
        setActiveNav(btn.dataset.nav);
        if ((location.hash || "#/") === target) {
          // same route: re-render so a stale view can always be refreshed
          route();
          return;
        }
        location.hash = target;
      });
    });
  }

  function updateSidebar() {
    const stats = (state.boot && state.boot.stats) || { total: 0 };
    const projectCount = $("#nav-project-count");
    const eventCount = $("#nav-event-count");
    if (projectCount) projectCount.textContent = stats.total ?? 0;
    const sideDate = $("#side-date");
    if (sideDate) sideDate.textContent = fmtLong(state.filters.date);
    const todays = (state.boot?.upcoming || []).filter((e) => e.days_away === 0);
    const next = (state.boot?.upcoming || []).filter((e) => e.days_away > 0)[0];
    const el = $("#side-events");
    if (el) {
      if (todays.length) {
        el.innerHTML = todays.slice(0, 2).map((e) => `• ${esc(e.artist?.name || "")} — ${esc(e.label_vi || KIND_LABEL[e.kind])}`).join("<br>");
      } else if (next) {
        el.innerHTML = `Hôm nay chưa có sự kiện lớn.<br>Sắp tới: <b>${esc(next.artist?.name || "")}</b> (${esc(daysLabel(next.days_away))}).`;
      } else {
        el.textContent = "Chưa có sự kiện trong 3 tuần tới. Thử mở rộng khoảng ngày.";
      }
    }
    if (eventCount) eventCount.textContent = (state.boot?.upcoming || []).length || "0";
  }

  // ------------------------------------------------------------------ bootstrap
  function showVersion(info) {
    const el = $("#side-version");
    if (!el) return;
    if (!info) { el.textContent = "không rõ phiên bản"; return; }
    const commit = info.commit ? ` · ${info.commit}` : "";
    el.textContent = `Legends Studio v${info.version}${commit}`;
    el.title = `Phiên bản ${info.version}${commit ? ` (commit ${info.commit})` : ""}\nKiểm tra bằng: /api/version`;
  }

  async function boot() {
    try {
      state.boot = await api(`/api/bootstrap?day=${state.filters.date}`);
      state.boot.artists = state.boot.artists || [];
      $("#today-label").textContent = fmtLong(state.boot.today);
      showVersion(state.boot.version);
    } catch (err) {
      toast(`Không kết nối được API: ${err.message}`, "err");
    }
  }

  // ------------------------------------------------------------------ dashboard
  async function viewDashboard() {
    const [evt, projects] = await Promise.all([
      api(`/api/events?day=${state.filters.date}&window=7`),
      api("/api/projects"),
    ]);
    const stats = state.boot?.stats || {};
    const ready = projects.projects.filter((p) => ["ready", "scheduled", "published"].includes(p.status)).length;
    const imgTotal = projects.projects.reduce((sum, p) => sum + (p.image_count || 0), 0);
    const heroEvent = evt.events.find((e) => e.days_away === 0) || evt.events[0] || null;
    const heroCover = heroEvent?.artist?.cover || "bg-stage.jpg";

    $("#view").innerHTML = `
      <section class="hero">
        <div>
          <div class="eyebrow">${ICON.spark} quy trình 4 bước cho thị trường Mỹ</div>
          <h1>Biến ngày hôm nay thành bài đăng về huyền thoại âm nhạc.</h1>
          <p>Chọn một sự kiện (sinh nhật, ngày mất, kỷ niệm phát hành) của nghệ sĩ mà khán giả 30–60 tuổi vẫn hâm mộ. Studio viết bài báo 700–900 từ, gom ảnh nghệ sĩ kèm giấy phép, rồi tạo chữ trên video 9–15 từ, hook, caption, comment pin và voiceover tiếng Anh.</p>
          <div class="row" style="gap:10px;flex-wrap:wrap">
            <a class="btn btn-primary" href="#/discover">${ICON.search} Tìm sự kiện hôm nay</a>
            <a class="btn btn-ghost" href="#/projects">${ICON.image} Xem dự án</a>
          </div>
          <div class="hero-steps" style="margin-top:18px">
            <span class="hero-step"><b>1</b> Sự kiện + nhạc</span>
            <span class="hero-step"><b>2</b> Bài báo 700–900 từ</span>
            <span class="hero-step"><b>3</b> Ảnh + banner</span>
            <span class="hero-step"><b>4</b> Text &amp; voice</span>
          </div>
        </div>
        <div class="hero-preview">
          <div class="mini-reel">
            <img src="/assets/${esc(heroCover)}" alt="" />
            <div class="mini-overlay">
              <span class="mo-badge">ON THIS DAY</span>
              <div class="mo-line">${esc(heroEvent ? heroEvent.artist.name : "Elvis Presley")}</div>
              <div class="mo-line" style="color:#f0b04c">${esc(heroEvent ? (heroEvent.age ? `${heroEvent.age}` : `${heroEvent.years || ""}`) : "91")}</div>
              <div class="tiny" style="text-align:center;color:#e9e3d6;opacity:.75">full story in the first comment</div>
            </div>
          </div>
        </div>
      </section>

      <section class="stats">
        <div class="stat"><div class="k">Dự án</div><div class="v mono">${stats.total ?? projects.projects.length}</div><div class="d">bài đăng đang quản lý</div></div>
        <div class="stat"><div class="k">Ảnh nghệ sĩ</div><div class="v mono">${imgTotal}</div><div class="d">ảnh đã lưu kèm giấy phép</div></div>
        <div class="stat"><div class="k">Sự kiện 7 ngày</div><div class="v mono">${evt.count}</div><div class="d">sinh nhật · ngày mất · kỷ niệm</div></div>
        <div class="stat"><div class="k">Sẵn sàng đăng</div><div class="v mono">${ready}</div><div class="d">đã có bài + text + voice</div></div>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>Sự kiện quanh hôm nay</h2>
          <p>${esc(fmtLong(evt.date))} · ±7 ngày · ưu tiên đúng ngày rồi tới gần nhất</p>
          <div class="spacer"></div>
          <a class="btn btn-ghost btn-sm" href="#/discover">Xem tất cả</a>
        </div>
        ${
          evt.events.length
            ? (evt.events.some((e) => e.days_away === 0) ? "" : `<div class="card card-pad" style="margin-bottom:14px;border-color:rgba(240,176,76,.25);background:rgba(240,176,76,.05)"><div class="row" style="gap:10px;align-items:flex-start"><span class="tag tag-warn">hôm nay trống</span><span class="small">Hôm nay không có sự kiện lớn của thư viện. Đây là những ngày gần nhất — dùng để chuẩn bị trước.</span></div></div>`)
              + `<div class="event-grid">${evt.events.slice(0, 3).map(eventCard).join("")}</div>`
            : `<div class="empty"><h3>Tuần này chưa có sự kiện nào</h3><p>Thử mở rộng khoảng ngày trong mục Khám phá, hoặc thêm sự kiện riêng.</p><a class="btn btn-primary" href="#/discover">Mở Khám phá</a></div>`
        }
      </section>

      <section class="section">
        <div class="section-head">
          <h2>Dự án gần đây</h2>
          <p>Bấm vào một dòng để mở studio</p>
          <div class="spacer"></div>
          <a class="btn btn-ghost btn-sm" href="#/projects">Tất cả dự án</a>
        </div>
        ${
          projects.projects.length
            ? `<div class="rows">${projects.projects.slice(0, 6).map(projectRow).join("")}</div>`
            : `<div class="empty"><h3>Chưa có dự án nào</h3><p>Chọn một sự kiện và studio sẽ viết bài + chuẩn bị text cho bạn.</p><a class="btn btn-primary" href="#/discover">Tạo dự án đầu tiên</a></div>`
        }
      </section>`;

    bindRows();
  }

  function eventCard(ev) {
    const a = ev.artist || {};
    const songs = (a.songs || []).slice(0, 2).map((s) => `<a class="song-chip" href="${esc(s.youtube)}" target="_blank" rel="noopener" title="Nghe thử trên YouTube">♪ ${esc(s.title)}</a>`).join("");
    const label = ev.kind === "release" ? ev.title : ev.kind === "birthday" ? `Sinh nhật lần thứ ${ev.age}` : `${ev.years} năm ngày mất`;
    return `
      <article class="event-card">
        <div class="event-media">
          <img src="/assets/${esc(a.cover || "bg-stage.jpg")}" alt="${esc(a.name)}" loading="lazy" />
          <span class="ev-badge tag ${KIND_TAG[ev.kind] || "tag-accent"}">${esc(KIND_LABEL[ev.kind] || ev.kind)}</span>
          <span class="ev-days ${ev.days_away === 0 ? "today" : ""}">${esc(daysLabel(ev.days_away))}</span>
        </div>
        <div class="event-body">
          <div>
            <div class="event-name">${esc(a.name)}</div>
            <div class="event-sub">${esc(a.aka || "")} · ${esc(a.genre || "")}</div>
          </div>
          <div class="event-label">${esc(label)} · ${esc(ev.date_label)}</div>
          <div class="song-chips">${songs}</div>
          <div class="event-actions">
            <button class="btn btn-primary btn-sm" data-create='${esc(JSON.stringify({ artist_id: ev.artist_id, event: ev }))}'>${ICON.plus} Tạo dự án</button>
            <a class="btn btn-ghost btn-sm" href="https://en.wikipedia.org/wiki/${encodeURIComponent(a.wikipedia || a.name)}" target="_blank" rel="noopener">Wiki</a>
          </div>
        </div>
      </article>`;
  }

  function projectRow(p) {
    const a = p.artist || {};
    const ev = p.event || {};
    const flags = [
      p.article_body ? `<span class="tag tag-ok">bài ${esc(p.article_words || 0)} từ</span>` : `<span class="tag tag-danger">chưa có bài</span>`,
      `<span class="tag ${p.image_count >= 20 ? "tag-ok" : ""}">${esc(p.image_count || 0)}/20 ảnh</span>`,
      p.voice?.url ? `<span class="tag tag-violet">voice</span>` : "",
    ].filter(Boolean).join(" ");
    return `
      <div class="prow" data-open="${esc(p.id)}">
        <div class="thumb"><img src="${esc(p.banner_url)}" alt="" loading="lazy" /></div>
        <div>
          <div class="p-title">${esc(p.article_title || `${a.name} — bản nháp`)}</div>
          <div class="p-meta">${esc(a.name)} · ${esc(KIND_LABEL[ev.kind] || "")} ${esc(ev.date_label || "")}</div>
        </div>
        <div class="p-cell hide-sm">${esc((p.fb_hook || "").slice(0, 76)) || "<span class='muted'>chưa có hook</span>"}</div>
        <div class="p-cell">${statusChip(p.status)}</div>
        <div class="p-cell hide-sm">${flags}<div class="tiny muted" style="margin-top:4px">${esc(fmtDateTime(p.updated_at))}</div></div>
        <div class="p-actions"><a class="btn btn-sm btn-ghost" href="#/project/${esc(p.id)}">Mở</a></div>
      </div>`;
  }

  function bindRows() {
    $$("[data-open]").forEach((row) => {
      row.addEventListener("click", (e) => {
        if (e.target.closest("a,button")) return;
        location.hash = `#/project/${row.dataset.open}`;
      });
    });
    $$("[data-create]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        let payload = {};
        try { payload = JSON.parse(btn.dataset.create); } catch (_) { /* ignore */ }
        try {
          const project = await api("/api/projects", { method: "POST", body: payload });
          toast("Đã tạo dự án: bài báo + text & voice", "ok");
          await boot();
          location.hash = `#/project/${project.id}`;
        } catch (err) {
          toast(err.message, "err");
          btn.disabled = false;
        }
      });
    });
  }

  // ------------------------------------------------------------------ discover
  async function viewDiscover() {
    const f = state.filters;
    $("#view").innerHTML = `
      <div class="panel" style="margin-bottom:18px">
        <div class="panel-head">
          <h3>Tạo bài viết bằng tên nhân vật</h3>
          <span class="tiny muted">Không cần có trong thư viện 27 nghệ sĩ</span>
        </div>
        <div class="panel-body">
          <div class="row" style="gap:10px;flex-wrap:wrap;align-items:flex-end">
            <div class="field" style="flex:2;min-width:230px;margin:0">
              <label>Tên nhân vật / nghệ sĩ</label>
              <input class="input" id="cust-name" placeholder="VD: Michael Jackson, Selena, Charlie Chaplin…" />
            </div>
            <div class="field" style="min-width:160px;margin:0">
              <label>Dịp</label>
              <select class="select" id="cust-kind">
                <option value="birthday">Sinh nhật</option>
                <option value="memorial">Ngày mất</option>
                <option value="release">Kỷ niệm phát hành</option>
                <option value="custom">Sự kiện tự nhập</option>
              </select>
            </div>
            <div class="field" style="min-width:150px;margin:0">
              <label>Ngày</label>
              <input type="date" class="input" id="cust-date" value="${esc(isoToday())}" />
            </div>
            <button class="btn btn-primary" id="cust-create">${ICON.spark} Tạo bài viết</button>
          </div>
          <details style="margin-top:12px">
            <summary class="tiny muted" style="cursor:pointer">Thêm chi tiết để bài viết cụ thể hơn (tuỳ chọn)</summary>
            <div class="row" style="gap:10px;flex-wrap:wrap;margin-top:10px">
              <div class="field" style="min-width:180px;margin:0"><label>Nghệ danh</label><input class="input" id="cust-aka" placeholder="The King of Pop" /></div>
              <div class="field" style="min-width:150px;margin:0"><label>Thể loại</label><input class="input" id="cust-genre" placeholder="Pop / Soul" /></div>
              <div class="field" style="min-width:140px;margin:0"><label>Giai đoạn</label><input class="input" id="cust-era" placeholder="1970s-2000s" /></div>
              <div class="field" style="min-width:160px;margin:0"><label>Quê quán</label><input class="input" id="cust-hometown" placeholder="Gary, Indiana" /></div>
              <div class="field" style="min-width:120px;margin:0"><label>Năm sinh</label><input class="input" id="cust-birth" placeholder="1958" /></div>
              <div class="field" style="min-width:120px;margin:0"><label>Năm mất</label><input class="input" id="cust-death" placeholder="2009" /></div>
              <div class="field" style="min-width:150px;margin:0">
                <label>Giọng</label>
                <select class="select" id="cust-gender"><option value="">Không rõ</option><option value="male">Nam (he/his)</option><option value="female">Nữ (she/her)</option></select>
              </div>
              <div class="field" style="min-width:170px;margin:0"><label>Link nguồn</label><input class="input" id="cust-source" placeholder="https://en.wikipedia.org/wiki/…" /></div>
            </div>
            <div class="field" style="margin-top:10px">
              <label>Bài hát nổi bật <span class="hint">mỗi dòng: Tên bài | năm</span></label>
              <textarea class="textarea" id="cust-songs" style="min-height:74px" placeholder="Thriller | 1982&#10;Billie Jean | 1983"></textarea>
            </div>
            <div class="field">
              <label>Sự thật / ghi chú <span class="hint">mỗi dòng một ý — studio chỉ dùng những gì bạn nhập, không tự bịa</span></label>
              <textarea class="textarea" id="cust-facts" style="min-height:74px" placeholder="Anh ấy thu âm Thriller trong 8 tuần."></textarea>
            </div>
            <div class="field">
              <label>Tiêu đề sự kiện / ghi chú <span class="hint">cho “kỷ niệm phát hành” hoặc “tự nhập”</span></label>
              <input class="input" id="cust-title" placeholder="VD: the 'Thriller' video premiere" />
            </div>
          </details>
        </div>
      </div>
      <div class="toolbar">
        <div class="search">
          ${ICON.search}
          <input class="input" id="q" placeholder="Tìm nghệ sĩ, bài hát, thể loại, quê quán…" value="${esc(f.q)}" />
        </div>
        <input type="date" class="input" id="day" value="${esc(f.date)}" style="max-width:170px" />
        <select class="select" id="window" style="max-width:190px">
          ${[0, 3, 7, 14, 30, 365].map((w) => `<option value="${w}" ${f.window === w ? "selected" : ""}>${w === 0 ? "Đúng ngày" : w === 365 ? "Cả năm" : `± ${w} ngày`}</option>`).join("")}
        </select>
        <div class="chip-row" id="kinds">
          ${["birthday", "memorial", "release"].map((k) => `<button class="chip ${f.kinds.includes(k) ? "active" : ""}" data-kind="${k}">${KIND_LABEL[k]}</button>`).join("")}
        </div>
      </div>
      <div id="discover-results"></div>`;

    const load = async () => {
      const results = $("#discover-results");
      results.innerHTML = `<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(288px,1fr))">${'<div class="skeleton" style="height:330px"></div>'.repeat(6)}</div>`;
      try {
        const params = new URLSearchParams({ day: f.date, window: String(f.window), q: f.q, kinds: f.kinds.join(",") });
        const data = await api(`/api/events?${params}`);
        const navCount = $("#nav-event-count");
        if (navCount) navCount.textContent = data.count;
        results.innerHTML = `
          <div class="section-head">
            <h2>${data.count} sự kiện</h2>
            <p>${esc(f.q ? `khớp “${f.q}” · ` : "")}${f.window === 0 ? "đúng ngày" : `±${f.window} ngày`} quanh ${esc(fmtLong(f.date))}</p>
          </div>
          ${
            data.events.length
              ? `<div class="event-grid">${data.events.map(eventCard).join("")}</div>`
              : `<div class="empty">
                   <h3>Không có sự kiện nào</h3>
                   <p>Thử mở rộng khoảng ngày hoặc bỏ từ khoá tìm kiếm.</p>
                   <button class="btn btn-primary" id="widen">Mở rộng ±30 ngày</button>
                 </div>`
          }`;
        bindRows();
        const widen = $("#widen");
        if (widen) widen.onclick = () => { f.window = 30; $("#window").value = "30"; load(); };
      } catch (err) {
        results.innerHTML = `<div class="empty"><h3>Lỗi tải sự kiện</h3><p>${esc(err.message)}</p></div>`;
      }
    };

    const createBtn = $("#cust-create");
    if (createBtn) {
      createBtn.onclick = async () => {
        const name = ($("#cust-name").value || "").trim();
        if (!name) return toast("Nhập tên nhân vật trước", "err");
        const lines = (el) => (($(el).value || "").split(/\n+/).map((x) => x.trim()).filter(Boolean));
        const songs = lines("#cust-songs").map((line) => {
          const [title, year] = line.split("|");
          return { title: (title || "").trim(), year: (year || "").trim() };
        }).filter((s) => s.title);
        const profile = {
          aka: $("#cust-aka").value.trim(),
          genre: $("#cust-genre").value.trim(),
          era: $("#cust-era").value.trim(),
          hometown: $("#cust-hometown").value.trim(),
          birth: $("#cust-birth").value.trim(),
          death: $("#cust-death").value.trim(),
          gender: $("#cust-gender").value,
          source_url: $("#cust-source").value.trim(),
          songs,
          facts: lines("#cust-facts"),
        };
        const kind = $("#cust-kind").value;
        const event = { kind, date: $("#cust-date").value || isoToday(), title: $("#cust-title").value.trim() };
        createBtn.disabled = true;
        createBtn.innerHTML = "Đang viết bài…";
        try {
          const project = await api("/api/projects/custom", { method: "POST", body: { name, profile, event } });
          toast(`Đã tạo bài ${project.article_words} từ cho ${name}`, "ok");
          await boot();
          location.hash = `#/project/${project.id}`;
        } catch (err) {
          toast(err.message, "err");
          createBtn.disabled = false;
          createBtn.innerHTML = `${ICON.spark} Tạo bài viết`;
        }
      };
    }

    let debounce = null;
    $("#q").addEventListener("input", (e) => {
      f.q = e.target.value;
      clearTimeout(debounce);
      debounce = setTimeout(load, 280);
    });
    $("#day").addEventListener("change", async (e) => {
      f.date = e.target.value || isoToday();
      await boot();
      load();
      updateSidebar();
    });
    $("#window").addEventListener("change", (e) => { f.window = Number(e.target.value); load(); });
    $$("#kinds [data-kind]").forEach((chip) => {
      chip.addEventListener("click", () => {
        const k = chip.dataset.kind;
        f.kinds = f.kinds.includes(k) ? f.kinds.filter((x) => x !== k) : [...f.kinds, k];
        chip.classList.toggle("active");
        load();
      });
    });
    await load();
  }

  // ------------------------------------------------------------------ projects
  async function viewProjects() {
    const data = await api("/api/projects");
    const list = data.projects;
    $("#view").innerHTML = `
      <div class="toolbar">
        <div class="search">${ICON.search}<input class="input" id="pq" placeholder="Tìm theo tiêu đề, nghệ sĩ, hook…" /></div>
        <div class="chip-row" id="pstatus">
          <button class="chip active" data-s="">Tất cả (${list.length})</button>
          ${STATUS_ORDER.map((s) => {
            const n = list.filter((p) => p.status === s).length;
            return `<button class="chip" data-s="${s}">${STATUS_LABEL[s]} (${n})</button>`;
          }).join("")}
        </div>
      </div>
      <div id="plist"></div>`;

    const render = (filterStatus = "", q = "") => {
      const filtered = list.filter((p) => (!filterStatus || p.status === filterStatus)
        && (!q || `${p.article_title} ${p.fb_hook} ${p.artist?.name}`.toLowerCase().includes(q.toLowerCase())));
      $("#plist").innerHTML = filtered.length
        ? `<div class="rows">${filtered.map(projectRow).join("")}</div>`
        : `<div class="empty"><h3>Không có dự án phù hợp</h3><p>Đổi bộ lọc hoặc tạo dự án mới từ mục Khám phá.</p><a class="btn btn-primary" href="#/discover">Tạo dự án</a></div>`;
      bindRows();
    };
    let activeStatus = "";
    $$("#pstatus [data-s]").forEach((chip) => {
      chip.addEventListener("click", () => {
        $$("#pstatus .chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        activeStatus = chip.dataset.s;
        render(activeStatus, $("#pq").value);
      });
    });
    $("#pq").addEventListener("input", (e) => render(activeStatus, e.target.value));
    render();
  }

  // ------------------------------------------------------------------ rivals
  const PLATFORM_ICON = {
    facebook: "Facebook",
    instagram: "Instagram",
    tiktok: "TikTok",
    youtube: "YouTube",
  };

  function tierClass(score) {
    if (score >= 80) return "tier-hot";
    if (score >= 65) return "tier-good";
    if (score >= 50) return "tier-mid";
    return "tier-low";
  }

  const fmtNum = (n) => {
    const value = Number(n || 0);
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value >= 10_000_000 ? 0 : 1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(value >= 10_000 ? 0 : 1)}k`;
    return String(value);
  };

  async function viewRivals() {
    const f = state.rivalFilters;
    const platforms = state.boot?.rivals?.platforms || ["facebook", "instagram", "tiktok", "youtube"];
    $("#view").innerHTML = `
      <div class="toolbar">
        <div class="search">
          ${ICON.search}
          <input class="input" id="rq" placeholder="Tìm nghệ sĩ, hook, ghi chú…" value="${esc(f.q)}" />
        </div>
        <select class="select" id="rplatform" style="max-width:170px">
          <option value="">Mọi nền tảng</option>
          ${platforms.map((p) => `<option value="${esc(p)}" ${f.platform === p ? "selected" : ""}>${esc(PLATFORM_ICON[p] || p)}</option>`).join("")}
        </select>
        <select class="select" id="rsort" style="max-width:190px">
          <option value="score" ${f.sort === "score" ? "selected" : ""}>Sắp theo điểm nổi bật</option>
          <option value="views" ${f.sort === "views" ? "selected" : ""}>Nhiều views nhất</option>
          <option value="engagement" ${f.sort === "engagement" ? "selected" : ""}>Tương tác cao nhất</option>
          <option value="recent" ${f.sort === "recent" ? "selected" : ""}>Mới nhập gần đây</option>
        </select>
        <select class="select" id="rpage-filter" style="max-width:230px">
          <option value="">Mọi page đối thủ</option>
          ${(state.rivalPages || []).map((p) => `<option value="${esc(p.page)}" ${f.page === p.page ? "selected" : ""}>${esc(p.page)} (${p.count})</option>`).join("")}
        </select>
        <label class="chip ${f.onlyViral ? "active" : ""}" id="rviral" style="cursor:pointer">Chỉ bài đã nổi</label>
        <label class="chip ${f.onlyUnused ? "active" : ""}" id="runused" style="cursor:pointer">Chưa làm lại</label>
        <div class="spacer"></div>
        <button class="btn btn-sm btn-primary" id="btn-rimport">${ICON.plus} Nhập reel đối thủ</button>
      </div>
      <div id="rimport-panel"></div>
      <div id="rlist"><div class="skeleton" style="height:180px"></div></div>`;

    const load = async () => {
      const list = $("#rlist");
      list.innerHTML = `<div class="skeleton" style="height:180px"></div>`;
      const params = new URLSearchParams({
        q: f.q,
        platform: f.platform,
        sort: f.sort,
        page: f.page || "",
        only_viral: String(!!f.onlyViral),
        only_unused: String(f.onlyUnused),
      });
      try {
        const data = await api(`/api/rivals?${params}`);
        state.rivalReels = data.reels || [];
        state.rivalPages = data.pages || [];
        const pageSel = $("#rpage-filter");
        if (pageSel) {
          const current = f.page || "";
          pageSel.innerHTML = `<option value="">Mọi page đối thủ</option>${state.rivalPages
            .map((p) => `<option value="${esc(p.page)}" ${current === p.page ? "selected" : ""}>${esc(p.page)} (${p.count})</option>`)
            .join("")}`;
          pageSel.value = current;
        }
        const navCount = $("#nav-rival-count");
        if (navCount) navCount.textContent = data.count ?? state.rivalReels.length;
        if (!state.rivalReels.length) {
          list.innerHTML = `
            <div class="empty">
              <h3>Chưa có reel nào</h3>
              <p>Dán link page Facebook đối thủ — studio gọi thẳng facebook.com từ máy bạn, đọc bài công khai, chấm điểm rồi chỉ giữ những reel đã nổi. Không cần F12, không cần copy mã. Nếu Facebook đòi đăng nhập, dán cookie phiên một lần là xong.</p>
              <button class="btn btn-primary" id="empty-import">${ICON.plus} Nhập reel đầu tiên</button>
            </div>`;
          const emptyBtn = $("#empty-import");
          if (emptyBtn) emptyBtn.onclick = () => openImportRivals(load);
          return;
        }
        const hot = state.rivalReels.filter((r) => r.score >= 65).length;
        list.innerHTML = `
          <div class="section-head">
            <h2>${state.rivalReels.length} reel</h2>
            <p>${hot} reel đạt từ 65 điểm · điểm = độ phủ + tỉ lệ tương tác + độ mới</p>
          </div>
          <div class="rival-list">${state.rivalReels.map(rivalCard).join("")}</div>`;
        bindRivalList(load);
      } catch (err) {
        list.innerHTML = `<div class="empty"><h3>Không tải được danh sách</h3><p>${esc(err.message)}</p></div>`;
      }
    };

    let debounce = null;
    $("#rq").addEventListener("input", (e) => {
      f.q = e.target.value;
      clearTimeout(debounce);
      debounce = setTimeout(load, 260);
    });
    const pageSelect = $("#rpage-filter");
    if (pageSelect) {
      pageSelect.addEventListener("change", (e) => {
        f.page = e.target.value;
        load();
      });
    }
    const viralChip = $("#rviral");
    if (viralChip) {
      viralChip.onclick = () => {
        f.onlyViral = !f.onlyViral;
        viralChip.classList.toggle("active", f.onlyViral);
        load();
      };
    }
    $("#rplatform").addEventListener("change", (e) => { f.platform = e.target.value; load(); });
    $("#rsort").addEventListener("change", (e) => { f.sort = e.target.value; load(); });
    $("#runused").addEventListener("click", () => {
      f.onlyUnused = !f.onlyUnused;
      $("#runused").classList.toggle("active", f.onlyUnused);
      load();
    });
    $("#btn-rimport").onclick = () => openImportRivals(load);
    await load();
  }

  function rivalCard(reel) {
    const metrics = [
      `${fmtNum(reel.views)} views`,
      `${fmtNum(reel.likes)} like`,
      `${fmtNum(reel.comments)} cmt`,
      `${fmtNum(reel.shares)} share`,
      `ER ${reel.engagement}%`,
    ];
    const brief = reel.brief || {};
    return `
      <article class="rival-card" data-reel="${esc(reel.id)}">
        <div class="rival-score ${tierClass(reel.score)}">
          <b>${esc(reel.score)}</b>
          <span>${esc(reel.tier)}</span>
        </div>
        <div class="rival-body">
          <div class="rival-top">
            <span class="tag">${esc(reel.platform_label || reel.platform)}</span>
            <span class="tag">${esc(reel.format_label || reel.format)}</span>
            ${reel.remade_project_id ? `<span class="tag tag-ok">đã làm lại</span>` : ""}
            ${reel.source_page ? `<span class="tag tag-accent">${esc(reel.source_page)}</span>` : ""}
            <span class="tiny muted">${esc(reel.artist_name || "chưa rõ nghệ sĩ")}</span>
          </div>
          <div class="rival-hook">“${esc(reel.hook || "(chưa có hook)")}”</div>
          <div class="rival-metrics mono tiny">${metrics.map(esc).join(" · ")}</div>
          <div class="tiny muted">${esc(reel.verdict || "")}</div>
          <details class="rival-brief">
            <summary>Xem brief làm lại (${(brief.beats || []).length} nhịp)</summary>
            <div class="tiny" style="margin:8px 0 4px"><b>Hook:</b> ${esc(brief.hook_pattern || "")}</div>
            <ul class="rival-beats">${(brief.beats || []).map((b) => `<li>${esc(b)}</li>`).join("")}</ul>
            <div class="tiny muted">${esc(brief.pacing || "")}</div>
          </details>
        </div>
        <div class="rival-actions">
          ${reel.url ? `<a class="btn btn-sm btn-ghost" href="${esc(reel.url)}" target="_blank" rel="noopener">Mở reel</a>` : ""}
          ${reel.remade_project_id
            ? `<a class="btn btn-sm" href="#/project/${esc(reel.remade_project_id)}">Mở bài đã làm</a>`
            : `<button class="btn btn-sm btn-primary" data-remake="${esc(reel.id)}">${ICON.spark} Làm lại</button>`}
          <button class="btn btn-sm btn-danger" data-delrival="${esc(reel.id)}" title="Xoá reel">${ICON.trash}</button>
        </div>
      </article>`;
  }

  function bindRivalList(reload) {
    $$("[data-remake]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const reel = state.rivalReels.find((r) => r.id === btn.dataset.remake);
        if (reel) openRemakeModal(reel, reload);
      });
    });
    $$("[data-delrival]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!(await confirmDialog("Xoá reel này?", "Reel chỉ bị xoá khỏi danh sách theo dõi.", "Xoá reel"))) return;
        try {
          await api(`/api/rivals/${btn.dataset.delrival}`, { method: "DELETE" });
          toast("Đã xoá reel", "ok");
          reload();
        } catch (err) {
          toast(err.message, "err");
        }
      });
    });
  }

  const RIVAL_SCAN_STATUS = {
    ok: { label: "đọc được", cls: "tag-ok" },
    blocked: { label: "Facebook chặn", cls: "tag-warn" },
    denied: { label: "bị từ chối (HTTP 400)", cls: "tag-warn" },
    empty: { label: "không thấy bài", cls: "tag-warn" },
    error: { label: "lỗi mạng", cls: "tag-danger" },
  };

  function scanAttemptsHtml(attempts) {
    if (!attempts || !attempts.length) return "";
    return `
      <details class="rpage-attempts" style="margin-top:8px">
        <summary class="tiny muted">Nhật ký ${attempts.length} lần thử</summary>
        <ul class="rival-steps" style="margin-top:8px">
          ${attempts
            .map((a) => `<li><b>${esc(a.label)}</b> · ${esc(a.transport || a.ua)}${a.cookie ? " · có cookie" : ""} · HTTP ${esc(a.status || "—")} · ${fmtNum(a.size)} byte · ${esc(a.posts)} bài${a.note ? ` · <span class="muted">${esc(a.note)}</span>` : ""}${a.snippet ? `<div class="tiny muted" style="margin:2px 0 0 2px;opacity:.75">“${esc(String(a.snippet).slice(0, 130))}…”</div>` : ""}</li>`)
            .join("")}
        </ul>
      </details>`;
  }

  function renderScanResult(data, retry) {
    const box = $("#rpage-result");
    if (!box) return;
    const meta = RIVAL_SCAN_STATUS[data.status] || RIVAL_SCAN_STATUS.error;
    const bits = [];
    if (data.scanned) bits.push(`đọc được ${data.scanned} bài`);
    if (data.added) bits.push(`nhập ${data.added} bài đã nổi`);
    if (data.filtered_out) bits.push(`loại ${data.filtered_out} bài chưa đủ nổi`);
    if (data.skipped) bits.push(`bỏ ${data.skipped} bài đã có trong danh sách`);
    const session = data.session || {};
    const showCookie = data.needs_session || data.status === "blocked" || data.status === "denied";
    const cookieBox = showCookie
      ? `
      <div class="rpage-session" style="margin-top:12px;padding:12px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,0.02)">
        <div class="tiny" style="margin-bottom:6px">
          <b>Đọc bằng phiên đăng nhập của bạn</b> — Facebook chỉ trả nội dung cho phiên đã đăng nhập.
          Dán cookie <b>một lần</b>, từ đó mỗi lần chỉ cần dán link page.
        </div>
        <ol class="rival-steps">
          <li>Mở <a href="https://www.facebook.com" target="_blank" rel="noopener">facebook.com</a> khi đang đăng nhập → <b>F12</b> → tab <b>Network</b> → tải lại trang.</li>
          <li>Chọn request <code>facebook.com</code> đầu tiên → <b>Headers</b> → <b>Request Headers</b> → copy <b>toàn bộ</b> dòng <code>cookie:</code> (dài, có <code>datr</code>, <code>sb</code>, <code>c_user</code>, <code>xs</code>…).</li>
          <li>Dán vào ô dưới → studio lưu và đọc lại page ngay. (Chỉ copy <code>c_user</code> + <code>xs</code> cũng được, nhưng dễ bị Facebook coi là thiếu phiên.)</li>
        </ol>
        <div class="row" style="gap:8px;flex-wrap:wrap">
          <textarea class="textarea" id="rale-cookie" placeholder="datr=…; sb=…; c_user=615655…; xs=…" style="flex:1;min-width:240px;min-height:64px"></textarea>
          <button class="btn btn-primary btn-sm" id="rale-cookie-save">Lưu &amp; đọc lại</button>
          ${session.saved ? `<button class="btn btn-ghost btn-sm" id="rale-cookie-clear">Xoá cookie đã lưu</button>` : ""}
        </div>
        <div class="banner-tip">Cookie chỉ nằm trên máy bạn (<code>data/fb_session.json</code>, quyền 600) và chỉ gửi tới facebook.com.</div>
      </div>`
      : "";
    box.innerHTML = `
      <div class="rpage-result" style="margin-top:12px">
        <div class="row" style="gap:8px;flex-wrap:wrap">
          <span class="tag ${meta.cls}">${esc(meta.label)}</span>
          <span class="tiny">${esc(data.message || "")}</span>
        </div>
        ${bits.length ? `<div class="tiny muted" style="margin-top:6px">${esc(bits.join(" · "))}</div>` : ""}
        ${scanAttemptsHtml(data.attempts)}
        ${cookieBox}
      </div>`;

    const save = $("#rale-cookie-save");
    if (save) {
      save.onclick = async () => {
        const value = (($("#rale-cookie") || {}).value || "").trim();
        if (!value) return toast("Dán cookie dạng c_user=…; xs=…", "err");
        save.disabled = true;
        save.textContent = "Đang lưu…";
        try {
          await api("/api/rivals/session", { method: "POST", body: { cookie: value } });
          toast("Đã lưu cookie phiên — đang đọc lại page", "ok");
          await retry();
        } catch (err) {
          toast(err.message, "err");
          save.disabled = false;
          save.textContent = "Lưu & đọc lại";
        }
      };
    }
    const clear = $("#rale-cookie-clear");
    if (clear) {
      clear.onclick = async () => {
        try {
          await api("/api/rivals/session", { method: "DELETE" });
          toast("Đã xoá cookie phiên", "ok");
          await retry();
        } catch (err) {
          toast(err.message, "err");
        }
      };
    }
  }

  function openImportRivals(reload) {
    const panel = $("#rimport-panel");
    panel.innerHTML = `
      <div class="panel" style="margin-bottom:16px">
        <div class="panel-head">
          <h3>Nhập reel đối thủ</h3>
          <span class="tiny muted">Dán link page → studio tự đọc và chấm điểm</span>
          <div class="spacer"></div>
          <button class="btn btn-sm btn-ghost" id="rimport-close">Đóng</button>
        </div>
        <div class="panel-body">
          <div class="tabs" style="margin-bottom:12px">
            <button class="tab active" data-rmode="page">${ICON.globe} Từ link page Facebook</button>
            <button class="tab" data-rmode="manual">${ICON.plus} Dán tay nhiều dòng</button>
          </div>

          <div id="rmode-page">
            <div class="field">
              <label>Link page Facebook của đối thủ <span class="hint">chỉ cần dán link — không cần F12</span></label>
              <div class="row" style="gap:8px">
                <input class="input" id="rpage-url" placeholder="https://www.facebook.com/ten-page" style="flex:1" />
                <a class="btn btn-ghost" id="rpage-open" target="_blank" rel="noopener" hidden>Mở page</a>
                <button class="btn btn-primary" id="rpage-scan">${ICON.spark} Tìm reels nổi</button>
              </div>
            </div>
            <div class="banner-tip" style="margin:0 0 10px">
              Studio gọi thẳng facebook.com từ máy bạn, đọc phần công khai của page, chấm điểm rồi chỉ giữ bài đã nổi.
              Không gửi link hay nội dung cho bên thứ ba. Facebook có thể đòi phiên đăng nhập — khi đó dán cookie một lần là xong.
            </div>
            ${(() => {
              const t = state.boot?.rivals?.transports || {};
              if (t.curl_cffi !== false) return "";
              return `<div class="banner-tip" style="margin:0 0 10px;color:#ffb4b4">
                Thiếu <code>curl_cffi</code> nên máy chủ chưa giả lập được Chrome — Facebook sẽ trả HTTP 400.
                Chạy <code>pip install -r requirements.txt</code> (hoặc <code>pip install curl_cffi httpx[http2]</code>) rồi khởi động lại studio.
                Trong lúc chờ, dùng 2 cách bên dưới (tải HTML trang lên / nút bookmark).
              </div>`;
            })()}
            <div class="row" style="gap:10px;align-items:center;flex-wrap:wrap">
              <label class="tiny muted" style="display:flex;gap:6px;align-items:center">
                <input type="checkbox" id="rpage-only-viral" checked /> chỉ giữ bài đã nổi (điểm ≥ 65)
              </label>
              <span class="tiny muted" id="rpage-hint"></span>
            </div>
            <div id="rpage-result"></div>

            <div class="rpage-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px">
              <div style="padding:12px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,0.02)">
                <div class="tiny" style="font-weight:600;margin-bottom:4px">① Tải trang HTML lên — chắc chắn nhất</div>
                <div class="tiny muted" style="margin-bottom:8px">
                  Mở page đối thủ → cuộn vài lần → <b>Ctrl+S</b> (“Webpage, HTML only”) → chọn file ở đây.
                  Trang bạn lưu đã đăng nhập nên có đủ số liệu; studio bóc reel đã nổi từ đó.
                </div>
                <input class="input" type="file" id="rpage-html" accept=".html,.htm,text/html" />
                <div class="tiny muted" id="rpage-html-hint" style="margin-top:6px"></div>
              </div>
              <div style="padding:12px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,0.02)">
                <div class="tiny" style="font-weight:600;margin-bottom:4px">② Nút bookmark — một cú bấm trên page</div>
                <div class="tiny muted" style="margin-bottom:8px">
                  Kéo nút dưới lên thanh bookmark, mở page đối thủ rồi bấm nút. Không cần F12, không bị Facebook chặn dán mã.
                </div>
                <div class="row" style="gap:8px;flex-wrap:wrap">
                  <a class="btn btn-primary btn-sm" id="rpage-book" draggable="true" href="#">${ICON.link} Lấy reel page này</a>
                  <button class="btn btn-ghost btn-sm" id="rpage-book-copy">Copy mã</button>
                </div>
                <div class="tiny muted" id="rpage-book-hint" style="margin-top:6px"></div>
              </div>
            </div>

            <details style="margin-top:14px">
              <summary class="tiny muted" style="cursor:pointer">Facebook chặn hoặc bạn muốn tự dán số liệu</summary>
              <div style="margin-top:10px">
                <div class="field">
                  <label>JSON lấy được <span class="hint">dán vào đây nếu studio không tự đọc được</span></label>
                  <textarea class="textarea" id="rpage-json" style="min-height:96px" placeholder='{"page_url":"https://www.facebook.com/…","posts":[{"url":"…","text":"…","likes":1200,"comments":84,"shares":12}]}'></textarea>
                </div>
                <div class="row" style="gap:10px;align-items:center;flex-wrap:wrap">
                  <button class="btn btn-ghost" id="rpage-copy">${ICON.copy} Copy mã lấy bài</button>
                  <button class="btn btn-primary" id="rpage-import">${ICON.spark} Lọc bài đã nổi &amp; nhập</button>
                </div>
              </div>
            </details>
          </div>

          <div id="rmode-manual" hidden>
            <div class="banner-tip" style="margin-bottom:10px">
              Mỗi dòng: <code>url | nền tảng | views | likes | comments | shares | nghệ sĩ | hook | format</code><br />
              Chỉ cần <b>url</b> là đủ để bắt đầu; số liệu nhận <code>1.2M</code>, <code>84k</code>, <code>2.1 nghìn</code>.
              Format: story · pov · list · quote · countdown · tribute.
            </div>
            <textarea class="textarea" id="rimport-lines" style="min-height:130px" placeholder="https://www.tiktok.com/@user/video/123 | tiktok | 1.2M | 84k | 2.1k | 900 | Whitney Houston | The note nobody talks about | story"></textarea>
            <div class="row" style="gap:8px;margin-top:10px">
              <button class="btn btn-primary" id="rimport-save">${ICON.plus} Nhập vào danh sách</button>
              <span class="tiny muted" id="rimport-hint"></span>
            </div>
          </div>
        </div>
      </div>`;

    $("#rimport-close").onclick = () => { panel.innerHTML = ""; };
    $$("[data-rmode]").forEach((tab) => {
      tab.onclick = () => {
        $$("[data-rmode]").forEach((t) => t.classList.toggle("active", t === tab));
        $("#rmode-page").hidden = tab.dataset.rmode !== "page";
        $("#rmode-manual").hidden = tab.dataset.rmode !== "manual";
      };
    });

    const pageInput = $("#rpage-url");
    const openLink = $("#rpage-open");
    const syncOpen = () => {
      const url = (pageInput.value || "").trim();
      openLink.hidden = !url;
      if (url) openLink.href = /^https?:\/\//i.test(url) ? url : `https://${url}`;
    };
    pageInput.addEventListener("input", syncOpen);
    pageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") $("#rpage-scan").click();
    });

    const scan = async () => {
      const url = (pageInput.value || "").trim();
      if (!url) return toast("Dán link page Facebook của đối thủ trước đã", "err");
      const btn = $("#rpage-scan");
      const hint = $("#rpage-hint");
      btn.disabled = true;
      btn.innerHTML = `${ICON.refresh} Đang đọc page…`;
      hint.textContent = "Đang gọi facebook.com từ máy bạn — thường 5–20 giây…";
      $("#rpage-result").innerHTML = "";
      try {
        const res = await api("/api/rivals/scan-page", {
          method: "POST",
          body: { page_url: url, only_viral: $("#rpage-only-viral").checked },
        });
        const bits = [];
        if (res.scanned) bits.push(`đọc ${res.scanned} bài`);
        if (res.added) bits.push(`nhập ${res.added}`);
        if (res.filtered_out) bits.push(`loại ${res.filtered_out}`);
        if (res.skipped) bits.push(`bỏ ${res.skipped} bài đã có`);
        hint.textContent = bits.length ? bits.join(" · ") : "";
        renderScanResult(res, scan);
        if (res.added) {
          toast(`Đã nhập ${res.added} reel đã nổi từ ${res.page_label || "page"}`, "ok");
          if (reload) await reload();
        } else if (res.status === "ok") {
          toast(res.message || "Không có bài mới để thêm", "err");
        }
      } catch (err) {
        toast(err.message, "err");
        hint.textContent = "";
      } finally {
        btn.disabled = false;
        btn.innerHTML = `${ICON.spark} Tìm reels nổi`;
      }
    };
    $("#rpage-scan").onclick = scan;

    const fileInput = $("#rpage-html");
    if (fileInput) {
      fileInput.onchange = async () => {
        const file = (fileInput.files || [])[0];
        if (!file) return;
        const hint = $("#rpage-html-hint");
        hint.textContent = `Đang đọc ${file.name} (${fmtNum(file.size)} byte)…`;
        try {
          const html = await file.text();
          const res = await api("/api/rivals/from-html", {
            method: "POST",
            body: {
              html,
              page_url: (pageInput.value || "").trim(),
              only_viral: $("#rpage-only-viral").checked,
            },
          });
          hint.textContent = `đọc ${res.scanned} bài · nhập ${res.added}${res.filtered_out ? ` · loại ${res.filtered_out} bài chưa đủ nổi` : ""}`;
          toast(`Đã nhập ${res.added} reel từ HTML của trang`, res.added ? "ok" : "err");
          if (res.added && reload) await reload();
        } catch (err) {
          hint.textContent = "";
          toast(err.message, "err");
        }
      };
    }

    const bookLink = $("#rpage-book");
    if (bookLink) {
      api("/api/rivals/bookmarklet")
        .then((info) => {
          bookLink.href = info.href;
          const hint = $("#rpage-book-hint");
          if (hint) hint.textContent = `Trỏ về ${info.origin}`;
        })
        .catch((err) => {
          bookLink.onclick = (event) => {
            event.preventDefault();
            toast(`Không tạo được nút bookmark: ${err.message}`, "err");
          };
        });
      const copyBook = $("#rpage-book-copy");
      if (copyBook) {
        copyBook.onclick = () => {
          if (!bookLink.href || bookLink.href === "#") return toast("Nút bookmark chưa sẵn sàng", "err");
          copyText(bookLink.href, "Đã copy mã bookmark — tạo bookmark mới và dán vào ô URL");
        };
      }
    }

    $("#rpage-copy").onclick = async () => {
      try {
        const res = await fetch("/assets/fb-extract.js", { cache: "no-store" });
        const code = await res.text();
        await copyText(code, "Đã copy mã — dán vào Console của trang Facebook đối thủ");
        $("#rpage-hint").textContent = "Đã copy mã ✓";
      } catch (err) {
        toast(`Không copy được: ${err.message}`, "err");
      }
    };

    $("#rpage-import").onclick = async () => {
      const raw = ($("#rpage-json").value || "").trim();
      if (!raw) {
        return toast("Dán JSON lấy từ trang, hoặc bấm Tìm reels nổi để studio tự đọc", "err");
      }
      let body;
      try {
        body = JSON.parse(raw);
      } catch (err) {
        return toast("JSON không hợp lệ — copy lại nguyên khối trong Console", "err");
      }
      body.page_url = body.page_url || (pageInput.value || "").trim();
      body.only_viral = $("#rpage-only-viral").checked;
      const btn = $("#rpage-import");
      btn.disabled = true;
      btn.innerHTML = "Đang lọc…";
      try {
        const res = await api("/api/rivals/from-page", { method: "POST", body });
        const bits = [`Đã nhập ${res.added} bài đã nổi`];
        if (res.skipped) bits.push(`bỏ ${res.skipped} bài trùng/không đọc được`);
        if (res.filtered_out) bits.push(`loại ${res.filtered_out} bài chưa đủ nổi`);
        toast(bits.join(" · "), res.added ? "ok" : "err");
        $("#rpage-hint").textContent = bits.join(" · ");
        if (res.added) {
          $("#rpage-json").value = "";
          if (reload) await reload();
        }
      } catch (err) {
        toast(err.message, "err");
      } finally {
        btn.disabled = false;
        btn.innerHTML = `${ICON.spark} Lọc bài đã nổi &amp; nhập`;
      }
    };

    $("#rimport-save").onclick = async () => {
      const lines = ($("#rimport-lines").value || "").trim();
      if (!lines) return toast("Dán ít nhất một dòng", "err");
      const btn = $("#rimport-save");
      btn.disabled = true;
      btn.innerHTML = "Đang nhập…";
      try {
        const res = await api("/api/rivals", { method: "POST", body: { lines } });
        toast(`Đã nhập ${res.added} reel`, res.added ? "ok" : "err");
        (res.errors || []).slice(0, 2).forEach((e) => toast(e, "err"));
        $("#rimport-lines").value = "";
        panel.innerHTML = "";
        if (reload) await reload();
      } catch (err) {
        toast(err.message, "err");
      } finally {
        btn.disabled = false;
        btn.innerHTML = `${ICON.plus} Nhập vào danh sách`;
      }
    };
  }

  function openRemakeModal(reel, reload) {
    const root = $("#modal-root");
    const artists = (state.boot?.artists || []).map((a) => ({ id: a.id, name: a.name }))
      .concat((state.boot?.custom_artists || []).map((a) => ({ id: a.id, name: `${a.name} (tự tạo)` })));
    const guess = (state.boot?.artists || []).find(
      (a) => a.name && reel.artist_name && a.name.toLowerCase() === String(reel.artist_name).toLowerCase(),
    );
    root.innerHTML = `
      <div class="modal-back">
        <div class="modal" style="width:min(620px,100%)">
          <h3>Làm lại reel này</h3>
          <p>${esc(reel.platform_label || reel.platform)} · ${esc(reel.format_label || reel.format)} · điểm ${esc(reel.score)}/100</p>
          <div class="rival-hook" style="margin-bottom:14px">“${esc(reel.hook || "")}”</div>
          <div class="field">
            <label>Nghệ sĩ / nhân vật cho bản làm lại</label>
            <select class="select" id="rm-artist">
              ${artists.map((a) => `<option value="${esc(a.id)}" ${guess && guess.id === a.id ? "selected" : ""}>${esc(a.name)}</option>`).join("")}
              <option value="__new__">+ Nhập tên nhân vật mới…</option>
            </select>
          </div>
          <div class="field" id="rm-name-wrap" hidden>
            <label>Tên nhân vật mới</label>
            <input class="input" id="rm-name" placeholder="VD: Michael Jackson" value="${esc(reel.artist_name || "")}" />
          </div>
          <div class="row" style="gap:10px">
            <div class="field" style="flex:1">
              <label>Dịp</label>
              <select class="select" id="rm-kind">
                <option value="">Tự chọn (sự kiện gần nhất)</option>
                <option value="birthday">Sinh nhật</option>
                <option value="memorial">Ngày mất</option>
                <option value="release">Kỷ niệm phát hành</option>
                <option value="custom">Sự kiện tự nhập</option>
              </select>
            </div>
            <div class="field" style="flex:1">
              <label>Ngày</label>
              <input type="date" class="input" id="rm-date" value="${esc(isoToday())}" />
            </div>
          </div>
          <div class="field">
            <label>Tiêu đề sự kiện / ghi chú <span class="hint">cho “kỷ niệm phát hành” hoặc “tự nhập”</span></label>
            <input class="input" id="rm-title" placeholder="VD: the 'Bodyguard' soundtrack" value="${esc(reel.hook || "")}" />
          </div>
          <div class="modal-actions" style="margin-top:16px">
            <button class="btn btn-ghost" data-act="cancel">Huỷ</button>
            <button class="btn btn-primary" data-act="go">${ICON.spark} Tạo bản làm lại</button>
          </div>
        </div>
      </div>`;

    const close = () => { root.innerHTML = ""; };
    const select = $('[data-act="cancel"]', root);
    const go = $('[data-act="go"]', root);
    $("#rm-artist", root).onchange = (e) => {
      $("#rm-name-wrap", root).hidden = e.target.value !== "__new__";
    };
    select.onclick = close;
    $(".modal-back", root).onclick = (e) => { if (e.target.classList.contains("modal-back")) close(); };
    go.onclick = async () => {
      const artistId = $("#rm-artist", root).value;
      const payload = { create: true };
      if (artistId === "__new__") {
        const name = ($("#rm-name", root).value || "").trim();
        if (!name) return toast("Nhập tên nhân vật", "err");
        payload.artist_name = name;
      } else {
        payload.artist_id = artistId;
      }
      const kind = $("#rm-kind", root).value;
      if (kind) {
        payload.event = {
          kind,
          date: $("#rm-date", root).value || isoToday(),
          title: ($("#rm-title", root).value || "").trim(),
        };
      }
      go.disabled = true;
      go.innerHTML = "Đang tạo…";
      try {
        const res = await api(`/api/rivals/${reel.id}/remake`, { method: "POST", body: payload });
        toast(`Đã tạo bản làm lại: ${res.project.article_words} từ`, "ok");
        close();
        await boot();
        location.hash = `#/project/${res.project.id}`;
      } catch (err) {
        toast(err.message, "err");
        go.disabled = false;
        go.innerHTML = `${ICON.spark} Tạo bản làm lại`;
      }
    };
  }

  // ------------------------------------------------------------------ studio
  const TABS = [
    ["article", "1", "Bài báo"],
    ["images", "2", "Ảnh nghệ sĩ"],
    ["script", "3", "Text & Voice"],
    ["checks", "4", "Kiểm tra"],
  ];

  async function viewProject(id) {
    if (!id) return viewDashboard();
    const project = await api(`/api/projects/${id}`);
    state.project = project;
    state.suggest = null;
    renderStudioShell();
  }

  function renderStudioShell() {
    const p = state.project;
    const a = p.artist || {};
    const ev = p.event || {};
    const evLabel = ev.kind === "release" ? ev.title : ev.kind === "birthday" ? `Sinh nhật lần thứ ${ev.age}` : `${ev.years} năm ngày mất`;
    const done = {
      article: Boolean(p.article_title && p.article_in_range),
      images: (p.image_count || 0) >= 20,
      script: Boolean(p.caption && p.overlay_ok),
      checks: (p.checks || []).every((c) => c.ok),
    };
    const remake = p.remake || {};
    const remakeHtml = remake.rival_id
      ? `<div class="remake-card">
           <div class="remake-head">
             <span class="tag tag-accent">Làm lại từ reel đối thủ</span>
             <b>${esc(remake.platform_label || remake.platform || "")}</b>
             <span class="tiny muted">· ${esc(remake.format_label || remake.format || "")} · điểm ${esc(remake.score)}/100 (${esc(remake.tier || "")})</span>
             <div class="spacer"></div>
             ${remake.url ? `<a class="btn btn-sm btn-ghost" href="${esc(remake.url)}" target="_blank" rel="noopener">Mở reel gốc</a>` : ""}
             <a class="btn btn-sm btn-ghost" href="#/rivals">Danh sách reel</a>
           </div>
           ${remake.hook ? `<div class="rival-hook">“${esc(remake.hook)}”</div>` : ""}
           <details><summary class="tiny muted" style="cursor:pointer">Cấu trúc cần giữ khi dựng (${((remake.brief || {}).beats || []).length} nhịp)</summary>
             <ul class="rival-beats">${(((remake.brief || {}).beats) || []).map((b) => `<li>${esc(b)}</li>`).join("")}</ul>
             <div class="tiny muted">${esc(((remake.brief || {}).pacing) || "")}</div>
           </details>
         </div>`
      : "";
    $("#view").innerHTML = `
      <div class="studio-head">
        <a class="btn btn-icon btn-ghost" href="#/projects" title="Quay lại">${ICON.back}</a>
        <div class="studio-avatar"><img src="${esc(p.banner_url)}" alt="" /></div>
        <div class="studio-title">
          <h1>${esc(a.name)}</h1>
          <div class="sub">
            <span>${esc(evLabel || "")}</span><span class="dot">·</span>
            <span>${esc(ev.date ? fmtLong(ev.date) : "")}</span><span class="dot">·</span>
            <span>${esc(a.genre || "")}</span><span class="dot">·</span>
            <span>${esc(a.era || "")}</span>
          </div>
        </div>
        <div class="studio-actions">
          ${statusChip(p.status)}
          <select class="select" id="status-select" style="max-width:180px">
            ${STATUS_ORDER.map((s) => `<option value="${s}" ${p.status === s ? "selected" : ""}>${STATUS_LABEL[s]}</option>`).join("")}
          </select>
          <a class="btn btn-ghost btn-sm" id="btn-bundle" href="/api/projects/${esc(p.id)}/bundle.zip" download title="Tải bài báo + ảnh + voice về máy">${ICON.zip} Tải về máy</a>
          <button class="btn btn-ghost btn-sm" id="btn-export">${ICON.download} Xuất .md</button>
          <button class="btn btn-ghost btn-sm" id="btn-dup">${ICON.copy} Nhân bản</button>
          <button class="btn btn-danger btn-sm" id="btn-del" title="Xoá dự án">${ICON.trash}</button>
        </div>
      </div>
      ${remakeHtml}
      <div class="tabs">
        ${TABS.map(([key, num, label]) => `
          <button class="tab ${state.tab === key ? "active" : ""}" data-tab="${key}">
            <span class="num">${num}</span> ${label}
            ${done[key] ? '<span class="done">✓</span>' : ""}
          </button>`).join("")}
      </div>
      <div id="tab-body"></div>`;

    $$(".tab").forEach((t) => t.addEventListener("click", () => {
      state.tab = t.dataset.tab;
      $$(".tab").forEach((x) => x.classList.toggle("active", x === t));
      renderTab();
    }));
    $("#status-select").addEventListener("change", async (e) => {
      const updated = await api(`/api/projects/${p.id}`, { method: "PATCH", body: { status: e.target.value } });
      state.project = updated;
      renderStudioShell();
      toast(`Đã chuyển trạng thái: ${STATUS_LABEL[updated.status]}`, "ok");
    });
    $("#btn-export").onclick = () => window.open(`/api/projects/${p.id}/export?fmt=md`, "_blank");
    $("#btn-dup").onclick = async () => {
      const copy = await api(`/api/projects/${p.id}/duplicate`, { method: "POST" });
      toast("Đã nhân bản dự án", "ok");
      location.hash = `#/project/${copy.id}`;
    };
    $("#btn-del").onclick = async () => {
      if (!(await confirmDialog("Xoá dự án?", `Bài báo, ảnh và voice của ${a.name} sẽ bị xoá.`, "Xoá dự án"))) return;
      await api(`/api/projects/${p.id}`, { method: "DELETE" });
      toast("Đã xoá dự án", "ok");
      await boot();
      location.hash = "#/projects";
    };
    renderTab();
  }

  function renderTab() {
    const body = $("#tab-body");
    if (!body) return;
    if (state.tab === "article") { body.innerHTML = articleTab(); bindArticleTab(); }
    else if (state.tab === "images") { body.innerHTML = imagesTab(); bindImagesTab(); }
    else if (state.tab === "script") { body.innerHTML = scriptTab(); bindScriptTab(); }
    else { body.innerHTML = checksTab(); bindChecksTab(); }
    $$(".tab").forEach((x) => x.classList.toggle("active", x.dataset.tab === state.tab));
  }

  function copyMap() {
    const p = state.project || {};
    const links = (p.music_links || []).map((s) => `${s.title} (${s.year}): ${s.youtube}`).join("\n");
    return {
      title: p.article_title || "",
      body: p.article_body || "",
      links,
      overlay: p.video_overlay_text || "",
      hook: p.fb_hook || "",
      caption: p.caption || "",
      comment: p.first_comment || "",
      hashtags: p.hashtags || "",
      all: [
        p.article_title,
        "",
        p.article_body,
        "",
        "MUSIC",
        links,
        "",
        "ON-SCREEN TEXT",
        p.video_overlay_text,
        "",
        "HOOK",
        p.fb_hook,
        "",
        "CAPTION",
        p.caption,
        "",
        "HASHTAGS",
        p.hashtags,
        "",
        "FIRST COMMENT",
        p.first_comment,
      ].join("\n"),
    };
  }

  function bindCopyButtons(root) {
    $$("[data-copy]", root).forEach((btn) => {
      btn.addEventListener("click", () => {
        const map = copyMap();
        const key = btn.dataset.copy;
        copyText(map[key] ?? "", btn.dataset.copyLabel || "Đã copy");
      });
    });
  }

  const copyBtn = (key, label = "Copy", cls = "btn btn-sm btn-ghost") =>
    `<button class="${cls}" data-copy="${key}" data-copy-label="${esc(label)}" title="${esc(label)}">${ICON.copy} Copy</button>`;

  // ------------------------------------------------------------------ article tab
  function articleTab() {
    const p = state.project;
    const titles = p.article_titles || [];
    const links = p.music_links || [];
    const range = p.article_range || [700, 900];
    return `
      <div class="split">
        <div class="panel">
          <div class="panel-head">
            <h3>Bài báo</h3>
            <span class="tag tag-accent">tiếng Anh · thị trường Mỹ</span>
            <div class="spacer"></div>
            <button class="btn btn-sm" id="btn-regen-article">${ICON.refresh} Tạo lại</button>
            <button class="btn btn-sm btn-primary" id="btn-save-article">${ICON.save} Lưu</button>
          </div>
          <div class="panel-body">
            <div class="field">
              <div class="label-row">
                <label>Tiêu đề <span class="hint"><span id="title-count">${(p.article_title || "").length}</span>/100 ký tự</span></label>
                ${copyBtn("title", "Đã copy tiêu đề")}
              </div>
              <input class="input" id="f-title" value="${esc(p.article_title)}" maxlength="140" />
              <div class="chip-row" style="margin-top:8px">
                ${titles.filter((t) => t !== p.article_title).slice(0, 3).map((t) => `<button class="chip" data-title="${esc(t)}">${esc(t.slice(0, 58))}${t.length > 58 ? "…" : ""}</button>`).join("")}
              </div>
            </div>

            <div class="field">
              <div class="label-row">
                <label>Nội dung bài báo <span class="hint">bắt buộc ${range[0]}–${range[1]} từ</span></label>
                <div class="row" style="gap:8px">
                  <span class="counter ${p.article_in_range ? "good" : "bad"}" id="body-count">${p.article_words || 0} từ</span>
                  ${copyBtn("body", "Đã copy nội dung bài")}
                </div>
              </div>
              <textarea class="textarea serif" id="f-body" style="min-height:420px">${esc(p.article_body)}</textarea>
              <div class="warn-line ${p.article_in_range ? "ok" : "bad"}" id="body-warn">
                ${p.article_in_range
                  ? `✓ ${p.article_words} từ — nằm trong khoảng ${range[0]}–${range[1]} từ.`
                  : `! ${p.article_words} từ — cần nằm trong ${range[0]}–${range[1]} từ (${p.article_words < range[0] ? `thêm ${range[0] - p.article_words} từ` : `bớt ${p.article_words - range[1]} từ`}).`}
              </div>
            </div>

            <div class="field" style="margin-bottom:0">
              <div class="label-row">
                <label>Link nhạc <span class="hint">bấm để nghe thử</span></label>
                ${copyBtn("links", "Đã copy link nhạc")}
              </div>
              <div class="music-list" id="music-list">
                ${links.map((s, i) => `
                  <div class="music-item" data-i="${i}">
                    <div>
                      <div class="mi-title">${esc(s.title)}</div>
                      <div class="mi-year">${esc(s.year)} · ${esc(s.note || "")}</div>
                    </div>
                    <div class="row" style="gap:6px">
                      <a href="${esc(s.youtube)}" target="_blank" rel="noopener" class="tag">YouTube</a>
                      <a href="${esc(s.spotify)}" target="_blank" rel="noopener" class="tag">Spotify</a>
                    </div>
                  </div>`).join("")}
              </div>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h3>Xem trước bài báo</h3>
            <div class="spacer"></div>
            ${copyBtn("all", "Đã copy toàn bộ gói", "btn btn-sm btn-primary")}
          </div>
          <div class="panel-body">
            <div class="preview-paper">
              <h2 id="pv-title">${esc(p.article_title)}</h2>
              <img class="pp-img" src="${esc(p.banner_url)}" alt="" id="pv-img" />
              <div class="pp-body" id="pv-body">${mdLite(p.article_body)}</div>
            </div>
            <div class="card card-pad" style="margin-top:16px;background:rgba(255,255,255,0.03)">
              <div class="row-between" style="margin-bottom:8px">
                <b style="font-size:13px">Checklist bài báo</b>
                <span class="tag ${p.article_in_range && p.article_title ? "tag-ok" : "tag-warn"}">${p.article_in_range && p.article_title ? "ổn" : "cần sửa"}</span>
              </div>
              <div class="tiny muted">
                • Tiêu đề dưới 100 ký tự<br>
                • Nội dung ${range[0]}–${range[1]} từ (${p.article_words} từ)<br>
                • Có 3 link nhạc (YouTube + Spotify)<br>
                • Ảnh banner lấy từ tab Ảnh nghệ sĩ
              </div>
              <div class="row" style="margin-top:10px;gap:8px;flex-wrap:wrap">
                <button class="btn btn-sm btn-ghost" id="btn-go-images">${ICON.image} Mở ảnh nghệ sĩ</button>
                <button class="btn btn-sm btn-ghost" id="btn-go-script">${ICON.mic} Mở text &amp; voice</button>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  }

  function bindArticleTab() {
    const p = state.project;
    const autoSave = debounceSave();
    const [minW, maxW] = p.article_range || [700, 900];

    const syncCount = () => {
      const wc = wordCount(p.article_body);
      p.article_words = wc;
      p.article_in_range = wc >= minW && wc <= maxW;
      const counter = $("#body-count");
      const warn = $("#body-warn");
      if (counter) {
        counter.textContent = `${wc} từ`;
        counter.className = `counter ${p.article_in_range ? "good" : "bad"}`;
      }
      if (warn) {
        warn.className = `warn-line ${p.article_in_range ? "ok" : "bad"}`;
        warn.textContent = p.article_in_range
          ? `✓ ${wc} từ — nằm trong khoảng ${minW}–${maxW} từ.`
          : `! ${wc} từ — cần nằm trong ${minW}–${maxW} từ (${wc < minW ? `thêm ${minW - wc} từ` : `bớt ${wc - maxW} từ`}).`;
      }
    };

    const syncPreview = () => {
      $("#pv-title").textContent = p.article_title;
      $("#pv-body").innerHTML = mdLite(p.article_body);
      $("#title-count").textContent = (p.article_title || "").length;
    };

    $("#f-title").addEventListener("input", (e) => {
      p.article_title = e.target.value;
      syncPreview();
      autoSave({ article_title: e.target.value });
    });
    $("#f-body").addEventListener("input", (e) => {
      p.article_body = e.target.value;
      syncPreview();
      syncCount();
      autoSave({ article_body: e.target.value });
    });
    $$("[data-title]").forEach((chip) => chip.addEventListener("click", () => {
      p.article_title = chip.dataset.title;
      $("#f-title").value = p.article_title;
      syncPreview();
      autoSave({ article_title: p.article_title });
    }));

    $("#btn-save-article").onclick = async () => {
      state.project = await api(`/api/projects/${p.id}`, {
        method: "PATCH",
        body: { article_title: p.article_title, article_body: p.article_body },
      });
      toast(p.article_in_range ? "Đã lưu bài báo" : `Đã lưu — nhưng bài đang ${wordCount(p.article_body)} từ, cần ${minW}–${maxW} từ`, p.article_in_range ? "ok" : "err");
    };

    $("#btn-regen-article").onclick = async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        state.project = await api(`/api/projects/${p.id}/generate`, { method: "POST", body: { section: "article" } });
        renderStudioShell();
        toast("Đã tạo lại bài báo", "ok");
      } catch (err) {
        toast(err.message, "err");
        btn.disabled = false;
      }
    };

    $("#btn-go-images").onclick = () => { state.tab = "images"; renderTab(); };
    $("#btn-go-script").onclick = () => { state.tab = "script"; renderTab(); };
    bindCopyButtons();
    syncCount();
  }

  // ------------------------------------------------------------------ images tab
  function imagesTab() {
    const p = state.project;
    const imgs = p.images || [];
    const target = p.image_target || 20;
    const canZip = imgs.length > 0;
    const zipHot = canZip && state.zipHint;
    return `
      <div class="panel">
        <div class="panel-head">
          <h3>Ảnh nghệ sĩ</h3>
          <span class="tag ${imgs.length >= target ? "tag-ok" : "tag-warn"}" id="img-count">${imgs.length}/${target} ảnh</span>
          <span class="tiny muted">1 ảnh banner + ${target} ảnh nghệ sĩ</span>
          <div class="spacer"></div>
          <button class="btn btn-sm btn-primary" id="btn-auto">${ICON.spark} Tự động lấy ${Math.max(1, target - imgs.length)} ảnh</button>
          <button class="btn btn-sm" id="btn-suggest">${ICON.image} Chọn thủ công</button>
          <button class="btn btn-sm btn-ghost" id="btn-diag" title="Kiểm tra trình duyệt có gọi được Wikipedia/Commons không">${ICON.refresh} Kiểm tra mạng</button>
          <button class="btn btn-sm" id="btn-upload-images">${ICON.plus} Tải ảnh lên</button>
          <input type="file" id="img-files" accept="image/*" multiple hidden />
          <a class="btn btn-sm ${canZip ? "" : "is-disabled"} ${zipHot ? "is-hot" : ""}" ${canZip ? `href="/api/projects/${esc(p.id)}/images.zip"` : ""} id="btn-zip">${ICON.zip} Tải về máy (.zip)</a>
        </div>
        <div class="panel-body">
          <div id="img-status" class="img-status" hidden></div>
          <div class="banner-tip" style="margin-bottom:14px">
            Studio tự động lấy ảnh từ <b>Wikipedia + Wikimedia Commons</b>, lưu kèm giấy phép &amp; tác giả, rồi đóng gói tất cả vào
            <b>.zip</b> để bạn tải về máy. Nếu máy chủ không có Internet, trình duyệt của bạn sẽ tải ảnh hộ.
          </div>
          <div class="field">
            <label>Dán link ảnh từ nguồn khác <span class="hint">mỗi dòng một link ảnh trực tiếp (.jpg/.png/.webp)</span></label>
            <div class="row" style="gap:8px;align-items:flex-start">
              <textarea class="textarea" id="img-urls" style="min-height:74px;flex:1" placeholder="https://i.pinimg.com/736x/…jpg&#10;https://media.gettyimages.com/…jpg"></textarea>
              <button class="btn btn-primary" id="btn-import-urls">${ICON.link} Tải ảnh từ link</button>
            </div>
            <div class="banner-tip">
              Studio <b>không scrape Pinterest</b> và không vượt rào cản của Getty. Hãy mở ảnh bạn có quyền dùng →
              chuột phải → <i>Copy image address</i> → dán vào đây. Ảnh sẽ được tải về máy chủ và lưu kèm nguồn.
            </div>
          </div>

          <div id="suggest-panel"></div>

          <hr class="sep" />
          <div class="row-between" style="margin-bottom:10px">
            <b style="font-size:13px">Thư viện ảnh của dự án</b>
            <span class="tiny muted">Ảnh đầu tiên tự thành banner — có thể đổi bất cứ lúc nào</span>
          </div>
          <div id="img-grid" class="img-grid">
            ${imgs.length ? imgs.map(imageCard).join("") : `<div class="empty" style="grid-column:1/-1"><h3>Chưa có ảnh nào</h3><p>Bấm “Tự động lấy 20 ảnh” để studio gom ảnh từ Wikipedia + Commons, hoặc dán link ảnh / tải ảnh lên.</p></div>`}
          </div>
        </div>
      </div>`;
  }

  function imageCard(img) {
    const p = state.project;
    const lic = [img.license || "không rõ giấy phép", img.source].filter(Boolean).join(" · ");
    return `
      <figure class="img-card ${img.is_banner ? "is-banner" : ""}" data-img="${esc(img.id)}">
        <div class="img-thumb">
          <img src="${esc(img.file_url || "")}" alt="${esc(img.title || "")}" loading="lazy" />
          ${img.is_banner ? '<span class="img-flag">BANNER</span>' : ""}
        </div>
        <figcaption>
          <div class="img-title" title="${esc(img.title || "")}">${esc(img.title || "Ảnh nghệ sĩ")}</div>
          <div class="img-lic" title="${esc(lic)}">${esc(lic)}</div>
          ${img.attribution ? `<div class="img-attr" title="${esc(img.attribution)}">${esc(img.attribution)}</div>` : ""}
          <div class="img-actions">
            <button class="btn btn-sm ${img.is_banner ? "btn-primary" : "btn-ghost"}" data-set-banner="${esc(img.id)}">
              ${img.is_banner ? "Banner ✓" : "Đặt làm banner"}
            </button>
            <a class="btn btn-sm btn-ghost" href="/api/projects/${esc(p.id)}/images/${esc(img.id)}/download" download title="Tải ảnh">${ICON.download} Tải về</a>
            <button class="btn btn-sm btn-danger" data-del-img="${esc(img.id)}" title="Xoá ảnh">${ICON.trash}</button>
          </div>
        </figcaption>
      </figure>`;
  }

  // ---------------------------------------------- image sources (server + browser)
  const COMMONS_API = "https://commons.wikimedia.org/w/api.php";
  const WIKI_REST = "https://en.wikipedia.org/api/rest_v1/page/summary/";
  const IMAGE_MAX_BYTES = 15 * 1024 * 1024;

  const stripHtml = (value) => String(value || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

  function setImgStatus(text, kind = "") {
    const el = $("#img-status");
    if (!el) return;
    if (!text) { el.hidden = true; el.textContent = ""; return; }
    el.hidden = false;
    el.className = `img-status ${kind}`;
    el.innerHTML = `${kind === "busy" ? '<span class="spin"></span>' : ""}${esc(text)}`;
  }

  /** The browser tells the sandbox server what it could not reach (see /api/client-log). */
  async function reportClient(event, message, detail = "") {
    try {
      await fetch("/api/client-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event, message, detail }),
      });
    } catch (err) {
      /* diagnostics must never break the UI */
    }
  }

  async function diagnoseNetwork() {
    const checks = [
      ["Wikipedia API", "https://en.wikipedia.org/api/rest_v1/page/summary/Elvis_Presley"],
      ["Commons API", "https://commons.wikimedia.org/w/api.php?action=query&format=json&origin=*&meta=siteinfo&siprop=general"],
      ["Commons ảnh", "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Example.jpg/240px-Example.jpg"],
    ];
    const lines = [];
    for (const [label, url] of checks) {
      const started = Date.now();
      try {
        const res = await fetch(url, { mode: "cors" });
        await res.text();
        lines.push(`${label}: ${res.ok ? "OK" : `HTTP ${res.status}`} · ${Date.now() - started} ms`);
      } catch (err) {
        lines.push(`${label}: LỖI — ${err.message}`);
      }
    }
    const summary = lines.join(" | ");
    setImgStatus(`Trình duyệt: ${summary}`, "warn");
    await reportClient("network-test", summary, location.hostname);
    toast("Đã kiểm tra — xem dòng trạng thái phía trên", "ok");
    return summary;
  }

  async function wikipediaCandidatesInBrowser(artist) {
    const slug = encodeURIComponent(artist.wikipedia || artist.name || "");
    const res = await fetch(`${WIKI_REST}${slug}`, { headers: { Accept: "application/json" } });
    if (!res.ok) return [];
    const data = await res.json();
    const src = data?.originalimage?.source || data?.thumbnail?.source;
    if (!src) return [];
    return [{
      source: "wikipedia",
      title: `${data.title || artist.name} — ảnh chính Wikipedia`,
      url: src,
      thumb_url: data?.thumbnail?.source || src,
      page_url: `https://en.wikipedia.org/wiki/${slug}`,
      width: Number(data?.originalimage?.width || 0),
      height: Number(data?.originalimage?.height || 0),
      license: "Wikipedia (kiểm tra trang file)",
      license_url: "",
      attribution: `Nguồn: Wikipedia — ${artist.name || ""}`,
      description: String(data?.description || ""),
    }];
  }

  async function commonsCandidatesInBrowser(artist, limit) {
    const searches = [
      artist.wikipedia ? String(artist.wikipedia).replace(/_/g, " ") : "",
      `${artist.name} portrait`,
      `${artist.name} singer`,
      artist.name,
    ].filter(Boolean);
    const titles = [];
    for (const term of searches) {
      if (titles.length >= limit * 2) break;
      const params = new URLSearchParams({
        action: "query", format: "json", origin: "*", list: "search",
        srsearch: term, srnamespace: "6", srlimit: String(limit),
      });
      const res = await fetch(`${COMMONS_API}?${params}`);
      if (!res.ok) throw new Error(`Commons ${res.status}`);
      const data = await res.json();
      for (const item of data?.query?.search || []) {
        if (item.title && !titles.includes(item.title)) titles.push(item.title);
      }
    }
    const out = [];
    for (let i = 0; i < titles.length; i += 20) {
      const params = new URLSearchParams({
        action: "query", format: "json", origin: "*", titles: titles.slice(i, i + 20).join("|"),
        prop: "imageinfo", iiprop: "url|size|mime|extmetadata", iiurlwidth: "1200",
      });
      const data = await fetch(`${COMMONS_API}?${params}`).then((r) => r.json());
      for (const page of Object.values(data?.query?.pages || {})) {
        const info = (page.imageinfo || [])[0] || {};
        const mime = String(info.mime || "").toLowerCase();
        if (!mime.startsWith("image/") || mime.includes("svg")) continue;
        const width = Number(info.width || 0);
        const height = Number(info.height || 0);
        if (width < 400 || height < 400 || !info.url) continue;
        const meta = info.extmetadata || {};
        const val = (key) => stripHtml(meta[key]?.value || "");
        const title = String(page.title || "").replace(/^File:/, "");
        out.push({
          source: "wikimedia",
          title,
          url: info.url,
          thumb_url: info.thumburl || info.url,
          page_url: `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(title)}`,
          width, height,
          license: val("LicenseShortName") || "không rõ",
          license_url: val("LicenseUrl"),
          attribution: val("Artist") || val("Credit"),
          description: val("ImageDescription").slice(0, 280),
        });
      }
    }
    return out;
  }

  async function browserSuggest(artist, limit) {
    const errors = [];
    let images = [];
    try {
      images = images.concat(await wikipediaCandidatesInBrowser(artist || {}));
    } catch (err) {
      errors.push(`Wikipedia: ${err.message}`);
    }
    try {
      images = images.concat(await commonsCandidatesInBrowser(artist || {}, limit));
    } catch (err) {
      errors.push(`Commons: ${err.message}`);
    }
    const seen = new Set();
    const unique = images.filter((img) => img.url && !seen.has(img.url) && seen.add(img.url));
    if (!unique.length) throw new Error(errors.join(" · ") || "Trình duyệt không lấy được ảnh");
    return {
      images: unique,
      sources: ["Wikipedia", "Wikimedia Commons"],
      errors,
      existing: (state.project?.images || []).length,
      browser_fallback: true,
    };
  }

  /** Ask the server first; if it has no internet, pull the list in the browser. */
  async function fetchSuggestions(limit) {
    const p = state.project;
    try {
      const data = await api(`/api/projects/${p.id}/images/suggest?limit=${limit}`);
      if (!data.images?.length) throw new Error((data.errors || []).join(" · ") || "không có ảnh");
      state.browserOnly = false;
      return data;
    } catch (err) {
      let local;
      try {
        local = await browserSuggest(p.artist || {}, limit);
      } catch (fallbackErr) {
        await reportClient("browser-fallback-failed", `${err.message} → ${fallbackErr.message}`, navigator.userAgent);
        throw fallbackErr;
      }
      await reportClient("server-offline-browser-ok", err.message, `${(local.images || []).length} ảnh qua trình duyệt`);
      state.browserOnly = true;
      local.errors = [`Máy chủ chưa gọi được Wikipedia (${err.message}) → trình duyệt tự tải ảnh hộ.`, ...(local.errors || [])];
      return local;
    }
  }

  async function blobToDataUrl(blob) {
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return `data:${blob.type || "image/jpeg"};base64,${btoa(binary)}`;
  }

  async function fetchImageAsDataUrl(url) {
    const res = await fetch(url, { mode: "cors" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    if (!String(blob.type || "").startsWith("image/")) throw new Error("không phải file ảnh");
    if (blob.size > IMAGE_MAX_BYTES) throw new Error("ảnh lớn hơn 15 MB");
    return blobToDataUrl(blob);
  }

  /** Wikimedia blocks nothing, but thumbnails are smaller and always CORS-enabled. */
  async function fetchImageBytes(item) {
    const urls = [item.thumb_url, item.url].filter((v, i, arr) => v && arr.indexOf(v) === i);
    let lastErr = null;
    for (const url of urls) {
      try {
        return await fetchImageAsDataUrl(url);
      } catch (err) {
        lastErr = err;
      }
    }
    throw lastErr || new Error("không tải được ảnh");
  }

  const uploadShape = (item) => {
    const out = {};
    ["url", "source", "title", "page_url", "license", "license_url", "attribution", "description"].forEach((key) => {
      if (item[key]) out[key] = item[key];
    });
    return out;
  };

  /**
   * Add images: the server downloads them when it can, otherwise (offline /
   * blocked network) the browser downloads the bytes and posts them as data URLs.
   */
  async function addPickedImages(picked, onProgress) {
    const p = state.project;
    let added = 0;
    const errors = [];
    let pending = picked.slice();

    if (!state.browserOnly && pending.length) {
      try {
        const res = await api(`/api/projects/${p.id}/images`, {
          method: "POST",
          body: { images: pending.map(uploadShape) },
        });
        added += res.added || 0;
        errors.push(...(res.errors || []));
        state.project = res.project;
        const have = new Set((res.project.images || []).map((img) => img.url).filter(Boolean));
        pending = pending.filter((item) => !have.has(item.url));
      } catch (err) {
        errors.push(err.message);
      }
    }

    for (let i = 0; i < pending.length; i++) {
      const item = pending[i];
      if (onProgress) onProgress(i + 1, pending.length, item);
      try {
        const dataUrl = await fetchImageBytes(item);
        const res = await api(`/api/projects/${p.id}/images`, {
          method: "POST",
          body: { images: [{ ...uploadShape(item), data_url: dataUrl }] },
        });
        added += res.added || 0;
        errors.push(...(res.errors || []));
        state.project = res.project;
      } catch (err) {
        errors.push(`${item.title || item.url}: ${err.message}`);
      }
    }
    return { added, errors };
  }

  function renderSuggestions(data) {
    const images = data.images || [];
    if (!images.length) {
      return `<div class="warn-line">Không tìm thấy ảnh mới trên Wikipedia/Commons. Thử dán link ảnh hoặc tải ảnh lên.</div>`;
    }
    const errors = (data.errors || []).map((e) => `<div class="tiny muted">• ${esc(e)}</div>`).join("");
    const badge = data.browser_fallback
      ? `<span class="tag tag-warn">trình duyệt tải hộ</span>`
      : `<span class="tag tag-ok">máy chủ tải</span>`;
    return `
      <div class="suggest-head">
        <b style="font-size:13px">${images.length} ảnh gợi ý từ ${esc((data.sources || []).join(" + "))}</b>
        ${badge}
        <span class="tiny muted">đã có ${data.existing || 0} ảnh trong dự án</span>
        <div class="spacer"></div>
        <button class="btn btn-sm btn-ghost" id="cand-all">Chọn tất cả</button>
        <button class="btn btn-sm btn-primary" id="btn-add-cands" disabled>${ICON.plus} Thêm 0 ảnh đã chọn</button>
      </div>
      ${errors}
      <div class="cand-grid">
        ${images.map((img, i) => `
          <label class="cand">
            <input type="checkbox" data-cand="${i}" />
            <img src="${esc(img.thumb_url || img.url)}" alt="" loading="lazy" />
            <span class="cand-meta">
              <span class="cand-title" title="${esc(img.title || "")}">${esc(img.title || "Ảnh")}</span>
              <span class="cand-lic">${esc(img.license || "không rõ")}</span>
              ${img.attribution ? `<span class="cand-attr" title="${esc(img.attribution)}">${esc(img.attribution)}</span>` : ""}
            </span>
          </label>`).join("")}
      </div>
      <div class="banner-tip">Giấy phép và tác giả được lưu cùng ảnh và xuất kèm trong file .zip (ATTRIBUTION.txt).</div>`;
  }

  function bindSuggestions() {
    const all = $("#cand-all");
    if (all) {
      all.onclick = () => {
        const boxes = $$("#suggest-panel [data-cand]");
        const turnOn = boxes.some((b) => !b.checked);
        boxes.forEach((b) => { b.checked = turnOn; });
        updateSelected();
      };
    }
    $$("#suggest-panel [data-cand]").forEach((box) => box.addEventListener("change", updateSelected));
    const add = $("#btn-add-cands");
    if (add) add.onclick = () => addSelected();
    updateSelected();
  }

  function updateSelected() {
    const n = $$("#suggest-panel [data-cand]").filter((b) => b.checked).length;
    const btn = $("#btn-add-cands");
    if (btn) {
      btn.disabled = n === 0;
      btn.innerHTML = `${ICON.plus} Thêm ${n} ảnh đã chọn`;
    }
  }

  async function addSelected() {
    const chosen = $$("#suggest-panel [data-cand]").filter((b) => b.checked).map((b) => Number(b.dataset.cand));
    const picked = (state.suggest?.images || []).filter((_, i) => chosen.includes(i));
    if (!picked.length) return;
    const btn = $("#btn-add-cands");
    if (btn) { btn.disabled = true; btn.innerHTML = "Đang tải ảnh…"; }
    setImgStatus(`Đang thêm ${picked.length} ảnh…`, "busy");
    try {
      const { added, errors } = await addPickedImages(picked, (i, n) => setImgStatus(`Đang tải ảnh ${i}/${n} bằng trình duyệt…`, "busy"));
      toast(`Đã thêm ${added} ảnh`, added ? "ok" : "err");
      errors.slice(0, 3).forEach((err) => toast(err, "err"));
      state.suggest = null;
      await refreshProject("images");
    } catch (err) {
      toast(err.message, "err");
      setImgStatus(err.message, "bad");
      if (btn) { btn.disabled = false; updateSelected(); }
    }
  }

  async function refreshProject(tab) {
    state.project = await api(`/api/projects/${state.project.id}`);
    if (tab) state.tab = tab;
    renderStudioShell();
  }

  async function suggestManually() {
    const btn = $("#btn-suggest");
    const panel = $("#suggest-panel");
    btn.disabled = true;
    panel.innerHTML = `<div class="suggest-loading">${ICON.refresh} Đang hỏi Wikipedia + Wikimedia Commons…</div>`;
    try {
      const data = await fetchSuggestions(24);
      state.suggest = data;
      panel.innerHTML = renderSuggestions(data);
      bindSuggestions();
      setImgStatus(data.browser_fallback ? "Máy chủ không có Internet — trình duyệt sẽ tải ảnh khi bạn bấm Thêm." : "", data.browser_fallback ? "warn" : "");
    } catch (err) {
      await reportClient("suggest-failed", err.message, navigator.userAgent);
      state.suggest = null;
      panel.innerHTML = `<div class="warn-line bad">! ${esc(err.message)}</div>
        <div class="banner-tip">Không lấy được ảnh tự động (mạng bị chặn?). Bạn vẫn có thể dán link ảnh hoặc tải ảnh lên.</div>`;
      setImgStatus(err.message, "bad");
    } finally {
      btn.disabled = false;
    }
  }

  async function autoFetchImages() {
    const p = state.project;
    const target = p.image_target || 20;
    const remaining = Math.max(1, target - (p.images || []).length);
    const btn = $("#btn-auto");
    btn.disabled = true;
    setImgStatus(`Đang lấy ${remaining} ảnh từ Wikipedia + Commons…`, "busy");
    try {
      let added = 0;
      const errors = [];
      try {
        const res = await api(`/api/projects/${p.id}/images/auto`, { method: "POST", body: { count: remaining } });
        added += res.added || 0;
        errors.push(...(res.errors || []));
        state.project = res.project;
        if (added > 0) state.browserOnly = false;
        else throw new Error((res.errors || [])[0] || "máy chủ không tải được ảnh");
      } catch (err) {
        // server has no outbound Internet → let the browser do the downloading
        setImgStatus(`${err.message} → trình duyệt tự tải…`, "busy");
        const data = await fetchSuggestions(Math.max(remaining * 3, 24));
        const picked = (data.images || []).slice(0, remaining);
        if (!picked.length) throw new Error("Không tìm thấy ảnh cho nghệ sĩ này");
        const out = await addPickedImages(picked, (i, n) => setImgStatus(`Đang tải ảnh ${i}/${n} bằng trình duyệt…`, "busy"));
        added += out.added || 0;
        errors.push(...(out.errors || []));
      }
      if (added > 0) state.zipHint = true;
      await refreshProject("images");
      if (added > 0) {
        toast(`Đã lấy ${added} ảnh → bấm “Tải tất cả (.zip)” để lưu cả bộ vào máy (thư mục Downloads).`, "ok");
      } else {
        toast(errors[0] || "Không lấy được ảnh nào", "err");
      }
      errors.slice(0, 3).forEach((err) => toast(err, "err"));
    } catch (err) {
      toast(err.message, "err");
      setImgStatus(err.message, "bad");
    } finally {
      const again = $("#btn-auto");
      if (again) again.disabled = false;
    }
  }

  function bindImagesTab() {
    const p = state.project;
    if (!state.suggest) state.browserOnly = false;

    const zip = $("#btn-zip");
    if (zip) zip.addEventListener("click", () => { state.zipHint = false; });
    $("#btn-diag").onclick = () => diagnoseNetwork();
    $("#btn-auto").onclick = () => autoFetchImages();
    $("#btn-suggest").onclick = () => suggestManually();

    $("#btn-import-urls").onclick = async (e) => {
      const btn = e.currentTarget;
      const raw = ($("#img-urls").value || "").split(/\s*\n\s*/).map((x) => x.trim()).filter(Boolean);
      if (!raw.length) return toast("Dán ít nhất một link ảnh", "err");
      btn.disabled = true;
      btn.innerHTML = "Đang tải ảnh…";
      setImgStatus(`Đang tải ${raw.length} link…`, "busy");
      try {
        const res = await api(`/api/projects/${p.id}/images`, { method: "POST", body: { urls: raw } });
        let added = res.added || 0;
        const errors = [...(res.errors || [])];
        state.project = res.project;
        const have = new Set((res.project.images || []).map((img) => img.url).filter(Boolean));
        const pending = raw.filter((url) => !have.has(url));
        if (pending.length) {
          setImgStatus("Máy chủ không tải được — thử tải bằng trình duyệt…", "busy");
          const out = await addPickedImages(pending.map((url) => ({ url })), (i, n) => setImgStatus(`Đang tải ${i}/${n} bằng trình duyệt…`, "busy"));
          added += out.added || 0;
          errors.push(...out.errors);
        }
        toast(`Đã tải ${added}/${raw.length} ảnh`, added ? "ok" : "err");
        errors.slice(0, 3).forEach((err) => toast(err, "err"));
        await refreshProject("images");
      } catch (err) {
        toast(err.message, "err");
        setImgStatus(err.message, "bad");
      } finally {
        btn.disabled = false;
        btn.innerHTML = `${ICON.link} Tải ảnh từ link`;
      }
    };

    $("#btn-upload-images").onclick = () => $("#img-files").click();
    $("#img-files").onchange = async (e) => {
      const files = Array.from(e.target.files || []);
      if (!files.length) return;
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f, f.name));
      setImgStatus(`Đang tải ${files.length} ảnh lên…`, "busy");
      try {
        const res = await api(`/api/projects/${p.id}/images/upload`, { method: "POST", body: fd });
        toast(`Đã thêm ${res.added} ảnh`, "ok");
        (res.errors || []).slice(0, 2).forEach((err) => toast(err, "err"));
        await refreshProject("images");
      } catch (err) {
        toast(err.message, "err");
        setImgStatus(err.message, "bad");
      }
    };

    $$("[data-set-banner]").forEach((btn) => btn.addEventListener("click", async () => {
      try {
        const res = await api(`/api/projects/${p.id}/images/${btn.dataset.setBanner}`, { method: "PATCH", body: { is_banner: true } });
        state.project = res.project;
        toast("Đã đặt ảnh làm banner", "ok");
        renderStudioShell();
      } catch (err) {
        toast(err.message, "err");
      }
    }));

    $$("[data-del-img]").forEach((btn) => btn.addEventListener("click", async () => {
      if (!(await confirmDialog("Xoá ảnh này?", "Ảnh sẽ bị xoá khỏi dự án và khỏi ổ đĩa.", "Xoá ảnh"))) return;
      try {
        const res = await api(`/api/projects/${p.id}/images/${btn.dataset.delImg}`, { method: "DELETE" });
        state.project = res.project;
        toast("Đã xoá ảnh", "ok");
        renderStudioShell();
      } catch (err) {
        toast(err.message, "err");
      }
    }));

    if (state.suggest) {
      $("#suggest-panel").innerHTML = renderSuggestions(state.suggest);
      bindSuggestions();
    }
  }

  // ------------------------------------------------------------------ script tab
  function scriptTab() {
    const p = state.project;
    const voices = state.boot?.voices || [];
    const engines = state.boot?.tts_engines || {};
    const voice = p.voice || {};
    const defaultText = voice.text || p.script?.voice_script || p.video_overlay_text || "";
    const engineNote = engines.edge
      ? "edge-tts (neural en-US) — cần internet, xuất .mp3"
      : engines.pyttsx3
        ? "Chỉ có pyttsx3 (offline) — xuất .wav/.mp3 tuỳ máy"
        : "Chưa có engine TTS — cài edge-tts hoặc pyttsx3";
    return `
      <div class="split">
        <div class="panel">
          <div class="panel-head">
            <h3>Text đăng bài</h3>
            <span class="tag tag-accent">tiếng Anh · thị trường Mỹ</span>
            <div class="spacer"></div>
            <button class="btn btn-sm" id="btn-regen-script">${ICON.refresh} Viết lại</button>
            <button class="btn btn-sm btn-primary" id="btn-save-script">${ICON.save} Lưu</button>
          </div>
          <div class="panel-body">
            <div class="field">
              <div class="label-row">
                <label>Chữ trên video <span class="hint">bắt buộc 9–15 từ</span></label>
                <div class="row" style="gap:8px">
                  <span class="counter ${p.overlay_ok ? "good" : "bad"}" id="overlay-count">${p.overlay_words || 0} từ</span>
                  ${copyBtn("overlay", "Đã copy chữ trên video")}
                </div>
              </div>
              <textarea class="textarea" id="f-overlay" style="min-height:84px;font-weight:600">${esc(p.video_overlay_text)}</textarea>
              <div class="warn-line ${p.overlay_ok ? "ok" : "bad"}" id="overlay-warn">
                ${p.overlay_ok ? "✓ Đúng khoảng 9–15 từ." : "! Cần 9–15 từ — studio sẽ cảnh báo nhưng vẫn cho lưu."}
              </div>
              <div class="row" style="margin-top:8px">
                <button class="btn btn-sm btn-ghost" id="btn-suggest-overlay">${ICON.spark} Gợi ý khác</button>
              </div>
              <div id="overlay-options" style="margin-top:10px"></div>
            </div>

            <div class="field">
              <div class="label-row">
                <label>Hook Facebook <span class="hint">dòng đầu tiên, hiện trước “xem thêm”</span></label>
                ${copyBtn("hook", "Đã copy hook")}
              </div>
              <textarea class="textarea" id="f-hook" style="min-height:80px">${esc(p.fb_hook)}</textarea>
            </div>

            <div class="field">
              <div class="label-row">
                <label>Caption đầy đủ <span class="hint">${(p.caption || "").length} ký tự</span></label>
                ${copyBtn("caption", "Đã copy caption")}
              </div>
              <textarea class="textarea" id="f-caption" style="min-height:170px">${esc(p.caption)}</textarea>
            </div>

            <div class="field">
              <div class="label-row">
                <label>Hashtag <span class="hint">8–10 tag</span></label>
                ${copyBtn("hashtags", "Đã copy hashtag")}
              </div>
              <input class="input" id="f-tags" value="${esc(p.hashtags)}" />
            </div>

            <div class="field" style="margin-bottom:0">
              <div class="label-row">
                <label>Comment pin <span class="hint">pin ngay sau khi đăng</span></label>
                ${copyBtn("comment", "Đã copy comment pin")}
              </div>
              <textarea class="textarea" id="f-comment" style="min-height:160px">${esc(p.first_comment)}</textarea>
            </div>
          </div>
        </div>

        <div>
          <div class="panel" style="margin-bottom:16px">
            <div class="panel-head">
              <h3>${ICON.mic} Voice từ text</h3>
              <div class="spacer"></div>
              <span class="tiny muted">${esc(engineNote)}</span>
            </div>
            <div class="panel-body">
              <div class="field">
                <label>Text đọc <span class="hint">${esc("en-US")} · tối đa 4000 ký tự</span></label>
                <textarea class="textarea" id="voice-text" style="min-height:110px">${esc(defaultText)}</textarea>
              </div>
              <div class="field">
                <label>Giọng đọc</label>
                <select class="select" id="voice-select">
                  ${voices.map((v) => `<option value="${esc(v.id)}" ${voice.voice === v.id ? "selected" : ""}>${esc(v.label)}</option>`).join("")}
                </select>
              </div>
              <div class="row" style="gap:8px;flex-wrap:wrap">
                <button class="btn btn-primary" id="btn-voice">${ICON.mic} Tạo voice</button>
                ${voice.url ? `<a class="btn" href="${esc(voice.url)}" download>${ICON.download} Tải .${esc(voice.ext || "mp3")}</a>` : ""}
              </div>
              <div id="voice-status" class="banner-tip">${voice.url ? `Bản gần nhất: ${esc(voice.engine)} · ${esc(voice.applied === false ? "giọng hệ thống (chưa áp dụng en-US)" : voice.voice)} · ${Math.round((voice.bytes || 0) / 1024)} KB` : "Nghe thử ngay trong trình duyệt, sau đó tải file để ghép vào video bạn tự dựng."}</div>
              ${voice.url && voice.applied === false ? `<div class="warn-line" id="voice-warn">${ICON.warn || "!"} ${esc(voice.note || "Giọng en-US bạn chọn chưa áp dụng được — edge-tts cần Internet.")}</div>` : ""}
              <div id="voice-player" style="margin-top:12px">
                ${voice.url ? `<audio controls src="${esc(voice.url)}" style="width:100%"></audio>` : ""}
              </div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-head"><h3>Xem như trên Facebook</h3></div>
            <div class="panel-body">
              <div class="card" style="background:#14161f;padding:0;overflow:hidden">
                <div class="row" style="padding:12px 14px;gap:10px">
                  <div class="studio-avatar" style="width:38px;height:38px;border-radius:50%"><img src="/assets/${esc(p.artist?.cover || "bg-stage.jpg")}" alt=""></div>
                  <div><div style="font-size:13px;font-weight:600">Legends Reel Studio</div><div class="tiny muted">Vừa xong · 🌐</div></div>
                </div>
                <div style="padding:0 14px 12px;font-size:13px;white-space:pre-wrap;line-height:1.5" id="fb-preview">${esc(p.caption)}</div>
                <img src="${esc(p.banner_url)}" alt="" style="width:100%;display:block;max-height:420px;object-fit:cover" />
                <div class="row" style="padding:10px 14px;gap:18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)">
                  <span>👍 Thích</span><span>💬 Bình luận</span><span>↗ Chia sẻ</span>
                </div>
              </div>
              <div class="copy-box" style="margin-top:14px" id="comment-preview">${esc(p.first_comment)}</div>
            </div>
          </div>
        </div>
      </div>`;
  }

  function bindScriptTab() {
    const p = state.project;
    const autoSave = debounceSave();
    const overlayEl = $("#f-overlay");

    const syncOverlay = () => {
      const words = wordCount(overlayEl.value);
      p.video_overlay_text = overlayEl.value;
      p.overlay_words = words;
      p.overlay_ok = words >= 9 && words <= 15;
      const counter = $("#overlay-count");
      const warn = $("#overlay-warn");
      if (counter) {
        counter.textContent = `${words} từ`;
        counter.className = `counter ${p.overlay_ok ? "good" : "bad"}`;
      }
      if (warn) {
        warn.className = `warn-line ${p.overlay_ok ? "ok" : "bad"}`;
        warn.textContent = p.overlay_ok ? "✓ Đúng khoảng 9–15 từ." : `! Đang ${words} từ — cần 9–15 từ (${words < 9 ? `thêm ${9 - words} từ` : `bớt ${words - 15} từ`}).`;
      }
    };

    overlayEl.addEventListener("input", () => {
      syncOverlay();
      autoSave({ video_overlay_text: overlayEl.value });
    });
    overlayEl.addEventListener("blur", async () => {
      if (!overlayEl.value.trim()) return;
      try {
        const res = await api(`/api/projects/${p.id}/overlay`, { method: "POST", body: { text: overlayEl.value } });
        state.project = res.project;
        if (!res.ok) toast(`Chữ trên video đang ${res.words} từ — nên nằm trong 9–15 từ`, "err");
      } catch (err) { toast(err.message, "err"); }
    });

    $("#f-hook").addEventListener("input", (e) => { p.fb_hook = e.target.value; autoSave({ fb_hook: e.target.value }); });
    $("#f-caption").addEventListener("input", (e) => {
      p.caption = e.target.value;
      const pv = $("#fb-preview");
      if (pv) pv.textContent = e.target.value;
      autoSave({ caption: e.target.value });
    });
    $("#f-tags").addEventListener("input", (e) => { p.hashtags = e.target.value; autoSave({ hashtags: e.target.value }); });
    $("#f-comment").addEventListener("input", (e) => {
      p.first_comment = e.target.value;
      const pv = $("#comment-preview");
      if (pv) pv.textContent = e.target.value;
      autoSave({ first_comment: e.target.value });
    });

    $("#btn-save-script").onclick = async () => {
      state.project = await api(`/api/projects/${p.id}`, {
        method: "PATCH",
        body: {
          video_overlay_text: p.video_overlay_text,
          fb_hook: p.fb_hook,
          caption: p.caption,
          hashtags: p.hashtags,
          first_comment: p.first_comment,
        },
      });
      toast(p.overlay_ok ? "Đã lưu text đăng bài" : "Đã lưu — chữ trên video chưa đúng 9–15 từ", p.overlay_ok ? "ok" : "err");
    };

    $("#btn-regen-script").onclick = async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        state.project = await api(`/api/projects/${p.id}/generate`, { method: "POST", body: { section: "script" } });
        renderStudioShell();
        toast("Đã viết lại text đăng bài", "ok");
      } catch (err) {
        toast(err.message, "err");
        btn.disabled = false;
      }
    };

    $("#btn-suggest-overlay").onclick = async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        const data = await api(`/api/projects/${p.id}/overlay-options`);
        $("#overlay-options").innerHTML = `
          <div class="tiny muted" style="margin-bottom:6px">Chọn một dòng (tất cả 9–15 từ):</div>
          <div class="chip-row">
            ${data.options.map((o) => `<button class="chip" data-opt="${esc(o.text)}">${esc(o.text)}</button>`).join("")}
          </div>`;
        $$("[data-opt]").forEach((chip) => chip.addEventListener("click", () => {
          overlayEl.value = chip.dataset.opt;
          overlayEl.dispatchEvent(new Event("input"));
          $("#overlay-options").innerHTML = "";
          toast("Đã áp dụng chữ trên video", "ok");
        }));
      } catch (err) { toast(err.message, "err"); }
      finally { btn.disabled = false; }
    };

    const voiceSelect = $("#voice-select");
    if (voiceSelect) {
      voiceSelect.onchange = () => {
        const picked = (state.boot?.voices || []).find((v) => v.id === voiceSelect.value);
        const label = picked ? picked.label : voiceSelect.value;
        toast(`Đã chọn giọng: ${label} — bấm “Tạo voice” để ghi lại bằng giọng này`, "ok");
        const makeBtn = $("#btn-voice");
        if (makeBtn) makeBtn.classList.add("is-hot");
        const status = $("#voice-status");
        if (status) {
          status.innerHTML = `Đang chọn <b>${esc(label)}</b> — bản voice hiện tại vẫn là bản cũ cho tới khi bạn bấm “Tạo voice”.`;
        }
      };
    }

    $("#btn-voice").onclick = async (e) => {
      const btn = e.currentTarget;
      const text = ($("#voice-text").value || "").trim();
      if (!text) return toast("Nhập text cần đọc trước", "err");
      btn.disabled = true;
      btn.innerHTML = `${ICON.mic} Đang tạo…`;
      const status = $("#voice-status");
      if (status) status.textContent = "Đang gọi engine TTS (edge-tts có thể mất 5–15 giây)…";
      try {
        const res = await api(`/api/projects/${p.id}/voice`, {
          method: "POST",
          body: { text, voice: $("#voice-select").value },
        });
        state.project = res.project;
        const voice = res.voice || {};
        const applied = voice.applied !== false;
        toast(applied ? `Đã tạo voice · ${voice.voice}` : "Đã tạo voice bằng giọng hệ thống (edge-tts chưa dùng được)", applied ? "ok" : "warn");
        const player = $("#voice-player");
        if (player) {
          // the file name changes on every generation, so the old take can never
          // be replayed from cache after the user picks another voice
          player.innerHTML = `<audio controls src="${esc(voice.url)}" style="width:100%"></audio>`;
        }
        if (status) {
          status.innerHTML = `${esc(voice.engine)} · ${esc(applied ? voice.voice : "giọng hệ thống (chưa áp dụng en-US)")} · ${Math.round((voice.bytes || 0) / 1024)} KB`;
        }
        const warn = $("#voice-warn");
        if (warn) warn.remove();
        if (!applied && status && status.parentElement) {
          const note = document.createElement("div");
          note.className = "warn-line";
          note.id = "voice-warn";
          note.textContent = voice.note || "Giọng en-US bạn chọn chưa áp dụng được — edge-tts cần Internet.";
          status.parentElement.insertBefore(note, status.nextSibling);
        }
        const row = btn.parentElement;
        const existing = row.querySelector("a[download]");
        if (existing) existing.remove();
        const link = document.createElement("a");
        link.className = "btn";
        link.href = voice.url;
        link.setAttribute("download", "");
        link.innerHTML = `${ICON.download} Tải .${esc(voice.ext || "mp3")}`;
        row.appendChild(link);
      } catch (err) {
        toast(err.message, "err");
        if (status) status.textContent = err.message;
      } finally {
        btn.disabled = false;
        btn.classList.remove("is-hot");
        btn.innerHTML = `${ICON.mic} Tạo voice`;
      }
    };

    bindCopyButtons();
    syncOverlay();
  }

  // ------------------------------------------------------------------ checks tab
  function checksTab() {
    const p = state.project;
    const checks = p.checks || [];
    return `
      <div class="split">
        <div class="panel">
          <div class="panel-head">
            <h3>Điều kiện xuất bản</h3>
            <div class="spacer"></div>
            <span class="tag ${checks.every((c) => c.ok) ? "tag-ok" : "tag-warn"}">${checks.filter((c) => c.ok).length}/${checks.length} đạt</span>
          </div>
          <div class="panel-body">
            ${checks.map((c) => `
              <div class="check">
                <div class="dot ${c.ok ? "ok" : "no"}">${c.ok ? "✓" : "!"}</div>
                <div style="flex:1">
                  <div class="c-label">${esc(c.label)}</div>
                  <div class="c-detail">${esc(c.detail || "")}</div>
                </div>
                <span class="tag ${c.ok ? "tag-ok" : "tag-danger"}">${c.ok ? "đạt" : "sửa"}</span>
              </div>`).join("")}
            <hr class="sep" />
            <div class="row" style="gap:10px;flex-wrap:wrap">
              <button class="btn btn-sm" data-go="article">Sửa bài báo (${p.article_words || 0} từ)</button>
              <button class="btn btn-sm" data-go="images">Thêm ảnh (${p.image_count || 0}/20)</button>
              <button class="btn btn-sm" data-go="script">Text &amp; voice (${p.overlay_words || 0} từ)</button>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head"><h3>Checklist đăng bài (thị trường Mỹ)</h3></div>
          <div class="panel-body">
            <div class="tiny" style="line-height:1.85">
              <b>Nội dung</b><br>
              • Bài báo 700–900 từ, tiêu đề dưới 100 ký tự<br>
              • Chữ trên video 9–15 từ, một ý duy nhất<br>
              • Hook nêu cảm xúc hoặc câu hỏi, không clickbait rỗng<br>
              • Comment pin chứa câu chuyện + link nhạc<br>
              • Kêu gọi cụ thể: “đọc comment đầu tiên”, “nghe bài này”<br>
              <br>
              <b>Hình ảnh</b><br>
              • 1 ảnh banner dọc (3:4 hoặc 9:16) + 20 ảnh nghệ sĩ<br>
              • Ảnh có giấy phép rõ ràng, giữ file ATTRIBUTION.txt trong .zip<br>
              <br>
              <b>Voice</b><br>
              • Voice 25–40 giây, đọc đúng tên nghệ sĩ và tên bài<br>
              • Ghép voice với video bạn tự dựng (studio không render video)<br>
              <br>
              <b>Đăng bài</b><br>
              • Khung giờ tốt cho khán giả 30–60 (giờ Mỹ): 7–9h sáng, 12–13h, 19–21h<br>
              • Thêm 8–10 hashtag, trả lời comment trong 30 phút đầu
            </div>
          </div>
        </div>
      </div>`;
  }

  function bindChecksTab() {
    $$("[data-go]").forEach((btn) => btn.addEventListener("click", () => {
      state.tab = btn.dataset.go;
      renderTab();
    }));
  }

  // ------------------------------------------------------------------ howto
  function viewHowto() {
    const steps = [
      ["01", "Tìm sự kiện đúng ngày", "Chọn ngày và khoảng ± ngày. Studio quét sinh nhật, ngày mất và các kỷ niệm phát hành của những nghệ sĩ mà khán giả 30–60 tuổi vẫn nghe, kèm 3 bài nhạc và link nghe thử."],
      ["02", "Viết bài báo 700–900 từ", "Mỗi dự án sinh một bài báo tiếng Anh: tiêu đề + 3 biến thể, nội dung 700–900 từ (đếm từ ngay khi bạn sửa), 3 link nhạc. Mỗi khối đều có nút Copy."],
      ["03", "Gom ảnh nghệ sĩ", "Lấy tự động từ Wikipedia + Wikimedia Commons kèm giấy phép và tác giả, hoặc dán link ảnh bạn có quyền dùng để studio tải về. Chọn 1 ảnh làm banner, 20 ảnh còn lại tải về hoặc gói .zip."],
      ["04", "Text & voice", "Chữ trên video 9–15 từ, hook Facebook, caption + comment pin — mỗi khối có nút Copy. Tạo voice tiếng Anh bằng edge-tts (neural en-US), nghe thử trong trình duyệt và tải .mp3."],
    ];
    $("#view").innerHTML = `
      <section class="hero" style="grid-template-columns:1fr">
        <div>
          <div class="eyebrow">${ICON.spark} cách hoạt động</div>
          <h1>Một quy trình, bốn bước, ra thẳng bài đăng.</h1>
          <p>Studio lo phần nội dung: sự kiện, bài báo, ảnh có giấy phép, text đăng bài và voiceover. Bạn dựng video bằng công cụ quen tay rồi đăng — không cần render MP4 ở đây.</p>
        </div>
      </section>
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">
        ${steps.map(([n, t, d]) => `
          <div class="card card-pad">
            <div style="font-family:var(--font-display);font-size:40px;color:var(--accent);line-height:1">${n}</div>
            <h3 style="margin:8px 0 8px;font-size:16px">${t}</h3>
            <p class="muted" style="margin:0;font-size:13px;line-height:1.6">${d}</p>
          </div>`).join("")}
      </div>
      <div class="card card-pad" style="margin-top:20px">
        <h3 style="margin:0 0 10px;font-size:15px">Mẹo để bài đăng được đề xuất</h3>
        <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px">
          <div><b style="font-size:13px">3 giây quyết định</b><p class="muted tiny" style="margin:4px 0 0">Hook phải tự đứng một mình, không phụ thuộc ảnh. Đặt tên nghệ sĩ hoặc con số ngay câu đầu.</p></div>
          <div><b style="font-size:13px">Đừng kể hết</b><p class="muted tiny" style="margin:4px 0 0">Phần mở đầu chỉ gợi tò mò. Toàn bộ câu chuyện nằm ở comment pin — nơi giữ chân người đọc.</p></div>
          <div><b style="font-size:13px">Ảnh có nguồn</b><p class="muted tiny" style="margin:4px 0 0">Ưu tiên ảnh có giấy phép rõ ràng. Giữ ATTRIBUTION.txt để biết ghi công ai khi cần.</p></div>
          <div><b style="font-size:13px">Voice rõ tên</b><p class="muted tiny" style="margin:4px 0 0">Nghe thử trước khi ghép. Đọc đúng tên nghệ sĩ và tên bài hát là thứ giữ người xem lại.</p></div>
        </div>
      </div>`;
  }

  // ------------------------------------------------------------------ autosave
  function debounceSave() {
    let timer = null;
    let pending = {};
    return (patch) => {
      pending = { ...pending, ...patch };
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const payload = pending;
        pending = {};
        try {
          const updated = await api(`/api/projects/${state.project.id}`, { method: "PATCH", body: payload });
          state.project = { ...state.project, ...updated };
        } catch (err) {
          toast(`Không lưu được: ${err.message}`, "err");
        }
      }, 700);
    };
  }

  // ------------------------------------------------------------------ boot
  function bindGlobal() {
    const newBtn = $("#btn-new");
    if (newBtn) newBtn.addEventListener("click", () => { location.hash = "#/discover"; });
    bindNav();
    window.addEventListener("hashchange", route);
  }

  async function init() {
    bindGlobal();
    await boot();
    await route();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
