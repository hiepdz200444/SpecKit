/* Legends Reel Studio — SPA */
(() => {
  "use strict";

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
    const [y, m, d] = iso.split("-").map(Number);
    return `${pad2(d)}/${pad2(m)}/${y}`;
  };
  const fmtDateTime = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  };
  const wordCount = (t) => (String(t || "").trim().match(/[A-Za-z0-9']+/g) || []).length;

  const ICON = {
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>',
    save: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 3h11l3 3v15H5z"/><path d="M8 3v6h8V3"/><path d="M8 14h8v7H8z"/></svg>',
    refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 11a8 8 0 1 0-2.3 6"/><path d="M20 4v7h-7"/></svg>',
    play: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>',
    download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M4 21h16"/></svg>',
    copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 14h10l1-14"/></svg>',
    back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M15 5l-7 7 7 7"/></svg>',
    image: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="m4 19 5-5 4 4 3-3 4 4"/></svg>',
    spark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"/></svg>',
    video: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="6" width="12" height="12" rx="3"/><path d="m15 11 6-3v8l-6-3z"/></svg>',
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>',
  };

  const state = {
    boot: null,
    route: { name: "dashboard", id: null },
    filters: { date: isoToday(), window: 7, q: "", kinds: [] },
    project: null,
    tab: "article",
    discoverEvents: [],
    jobs: {},
    previewTimer: null,
    previewIdx: 0,
    saving: null,
    overlayOptions: null,
  };

  // ------------------------------------------------------------------ utils
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
      } catch (_) { /* ignore */ }
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    if (res.status === 204) return null;
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  }

  function toast(message, type = "") {
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${type === "ok" ? "✓" : type === "err" ? "!" : "•"}</span><span>${esc(message)}</span>`;
    $("#toasts").appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(6px)";
      el.style.transition = "0.25s ease";
      setTimeout(() => el.remove(), 260);
    }, 3600);
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
    try {
      await navigator.clipboard.writeText(text);
      toast(label, "ok");
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      toast(label, "ok");
    }
  }

  const STATUS_ORDER = ["draft", "article", "video", "ready", "scheduled", "published"];
  const STATUS_LABEL = { draft: "Nháp", article: "Đã có bài", video: "Đã có kịch bản", ready: "Sẵn sàng đăng", scheduled: "Đã lên lịch", published: "Đã đăng" };
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
      if (list.length) { out.push(`<ul style="margin:0 0 12px;padding-left:18px">${list.join("")}</ul>`); list = []; }
    };
    for (const raw of lines) {
      const line = raw.trimEnd();
      if (!line.trim()) { flush(); out.push('<div style="height:10px"></div>'); continue; }
      let safe = esc(line)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener" style="color:#a8731a">$1</a>');
      if (safe.startsWith("## ")) { flush(); out.push(`<h4 style="font-family:var(--font-ui);font-size:13px;letter-spacing:.06em;text-transform:uppercase;margin:16px 0 6px;color:#8a7a5f">${safe.slice(3)}</h4>`); continue; }
      if (safe.startsWith("- ")) { list.push(`<li style="margin-bottom:4px">${safe.slice(2)}</li>`); continue; }
      flush();
      out.push(`<p style="margin:0 0 10px">${safe}</p>`);
    }
    flush();
    return out.join("");
  }

  // ------------------------------------------------------------------ routing
  const routes = {
    "": "dashboard",
    "#/": "dashboard",
    "#/discover": "discover",
    "#/projects": "projects",
    "#/howto": "howto",
  };

  function parseHash() {
    const hash = location.hash || "#/";
    if (hash.startsWith("#/project/")) {
      return { name: "project", id: hash.split("/")[2] };
    }
    return { name: routes[hash] || "dashboard", id: null };
  }

  function setActiveNav(name) {
    $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.nav === name));
  }

  async function route() {
    stopPreview();
    state.route = parseHash();
    const view = $("#view");
    view.classList.remove("fade-in");
    void view.offsetWidth;
    view.classList.add("fade-in");
    const names = { dashboard: "Tổng quan", discover: "Khám phá sự kiện", projects: "Dự án reels", project: "Studio", howto: "Cách hoạt động" };
    setActiveNav(state.route.name);
    $("#crumb").innerHTML =
      state.route.name === "project"
        ? `<span style="opacity:.6">Dự án</span> <span style="opacity:.4">/</span> <strong>Studio</strong>`
        : `<strong>${names[state.route.name]}</strong>`;
    try {
      if (state.route.name === "dashboard") await viewDashboard();
      else if (state.route.name === "discover") await viewDiscover();
      else if (state.route.name === "projects") await viewProjects();
      else if (state.route.name === "project") await viewProject(state.route.id);
      else viewHowto();
    } catch (err) {
      view.innerHTML = `<div class="empty"><h3>Không tải được màn hình</h3><p>${esc(err.message)}</p><button class="btn" onclick="location.reload()">Tải lại</button></div>`;
    }
    updateSidebar();
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function updateSidebar() {
    const stats = (state.boot && state.boot.stats) || { total: 0 };
    $("#nav-project-count").textContent = stats.total ?? 0;
    const today = state.filters.date;
    $("#side-date").textContent = fmtLong(today);
    const todays = (state.boot?.upcoming || []).filter((e) => e.days_away === 0);
    const next = (state.boot?.upcoming || []).filter((e) => e.days_away > 0)[0];
    const el = $("#side-events");
    if (todays.length) {
      el.innerHTML = todays.slice(0, 2).map((e) => `• ${esc(e.artist?.name || "")} — ${esc(e.label_vi || KIND_LABEL[e.kind])}`).join("<br>");
    } else if (next) {
      el.innerHTML = `Hôm nay chưa có sự kiện lớn.<br>Sắp tới: <b>${esc(next.artist?.name || "")}</b> (${esc(daysLabel(next.days_away))}).`;
    } else {
      el.textContent = "Chưa có sự kiện trong 3 tuần tới. Thử mở rộng khoảng ngày.";
    }
    const navCount = $("#nav-event-count");
    navCount.textContent = (state.boot?.upcoming || []).length || "0";
  }

  // ------------------------------------------------------------------ bootstrap
  async function boot() {
    try {
      state.boot = await api(`/api/bootstrap?day=${state.filters.date}`);
      state.boot.artists = state.boot.artists || [];
      $("#today-label").textContent = fmtLong(state.boot.today);
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
    state.discoverEvents = evt.events;
    const stats = state.boot?.stats || {};
    const ready = projects.projects.filter((p) => ["ready", "scheduled"].includes(p.status)).length;
    const rendered = projects.projects.filter((p) => p.render_url).length;
    const heroEvent = evt.events.find((e) => e.days_away === 0) || evt.events[0] || null;
    const heroArtist = heroEvent?.artist || state.boot?.artists?.[0];
    const heroCover = heroEvent?.artist?.cover || "bg-stage.jpg";

    $("#view").innerHTML = `
      <section class="hero">
        <div>
          <div class="eyebrow">${ICON.spark} quy trình 4 bước cho thị trường Mỹ</div>
          <h1>Biến ngày hôm nay thành một reel về huyền thoại âm nhạc.</h1>
          <p>Chọn một sự kiện (sinh nhật, ngày mất, kỷ niệm phát hành) của nghệ sĩ mà khán giả 30–60 tuổi vẫn hâm mộ. Studio viết bài báo, dựng MP4 9:16 có chữ 9–15 từ, rồi tạo hook + caption hướng người xem xuống comment đầu tiên.</p>
          <div class="row" style="gap:10px;flex-wrap:wrap">
            <a class="btn btn-primary" href="#/discover">${ICON.search} Tìm sự kiện hôm nay</a>
            <a class="btn btn-ghost" href="#/projects">${ICON.video} Xem dự án</a>
          </div>
          <div class="hero-steps" style="margin-top:18px">
            <span class="hero-step"><b>1</b> Sự kiện + nhạc</span>
            <span class="hero-step"><b>2</b> Bài báo</span>
            <span class="hero-step"><b>3</b> MP4 9:16</span>
            <span class="hero-step"><b>4</b> Hook + comment</span>
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
        <div class="stat"><div class="k">Dự án</div><div class="v mono">${stats.total ?? projects.projects.length}</div><div class="d">tổng số reels đã tạo</div></div>
        <div class="stat"><div class="k">Video MP4</div><div class="v mono">${rendered}</div><div class="d">đã render thành công</div></div>
        <div class="stat"><div class="k">Sự kiện 7 ngày</div><div class="v mono">${evt.count}</div><div class="d">sinh nhật · ngày mất · kỷ niệm</div></div>
        <div class="stat"><div class="k">Sẵn sàng đăng</div><div class="v mono">${ready}</div><div class="d">đã có video + caption</div></div>
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
            ? `${evt.events.some((e) => e.days_away === 0) ? "" : `<div class="card card-pad" style="margin-bottom:14px;border-color:rgba(240,176,76,.25);background:rgba(240,176,76,.05)"><div class="row" style="gap:10px;align-items:flex-start"><span class="tag tag-warn">hôm nay trống</span><span class="small">Hôm nay không có sự kiện lớn của thư viện. Đây là những ngày gần nhất — dùng để chuẩn bị trước và lên lịch đăng đúng ngày.</span></div></div>`}`
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
            : `<div class="empty"><h3>Chưa có dự án nào</h3><p>Chọn một sự kiện và studio sẽ viết bài + dựng video cho bạn.</p><a class="btn btn-primary" href="#/discover">Tạo reels đầu tiên</a></div>`
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
            <button class="btn btn-primary btn-sm" data-create='${esc(JSON.stringify({ artist_id: ev.artist_id, event: ev }))}'>${ICON.plus} Tạo reels</button>
            <a class="btn btn-ghost btn-sm" href="https://en.wikipedia.org/wiki/${encodeURIComponent(a.wikipedia || a.name)}" target="_blank" rel="noopener">Wiki</a>
          </div>
        </div>
      </article>`;
  }

  function projectRow(p) {
    const a = p.artist || {};
    const ev = p.event || {};
    return `
      <div class="prow" data-open="${esc(p.id)}">
        <div class="thumb"><img src="${esc(p.poster_url || p.banner_url)}" alt="" loading="lazy" /></div>
        <div>
          <div class="p-title">${esc(p.article_title || `${a.name} — bản nháp`)}</div>
          <div class="p-meta">${esc(a.name)} · ${esc(KIND_LABEL[ev.kind] || "")} ${esc(ev.date_label || "")}</div>
        </div>
        <div class="p-cell hide-sm">${esc((p.fb_hook || "").slice(0, 76)) || "<span class='muted'>chưa có hook</span>"}</div>
        <div class="p-cell">${statusChip(p.status)}</div>
        <div class="p-cell hide-sm">${p.render_url ? `<span class="tag tag-ok">MP4</span>` : `<span class="tag">chưa render</span>`}<div class="tiny muted" style="margin-top:4px">${esc(fmtDateTime(p.updated_at))}</div></div>
        <div class="p-actions">
          ${p.render_url ? `<a class="btn btn-sm btn-ghost" href="${esc(p.render_url)}" download>${ICON.download}</a>` : ""}
          <a class="btn btn-sm btn-ghost" href="#/project/${esc(p.id)}">Mở</a>
        </div>
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
        const payload = JSON.parse(btn.dataset.create);
        try {
          const project = await api("/api/projects", { method: "POST", body: payload });
          toast("Đã tạo dự án + bài báo + kịch bản video", "ok");
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
      <div class="toolbar">
        <div class="search">
          ${ICON.search}
          <input class="input" id="q" placeholder="Tìm nghệ sĩ, bài hát, thể loại, quê quán…" value="${esc(f.q)}" />
        </div>
        <input type="date" class="input" id="day" value="${esc(f.date)}" style="max-width:170px" />
        <select class="select" id="window" style="max-width:190px">
          <option value="0" ${f.window === 0 ? "selected" : ""}>Đúng ngày</option>
          <option value="3" ${f.window === 3 ? "selected" : ""}>± 3 ngày</option>
          <option value="7" ${f.window === 7 ? "selected" : ""}>± 7 ngày</option>
          <option value="14" ${f.window === 14 ? "selected" : ""}>± 14 ngày</option>
          <option value="30" ${f.window === 30 ? "selected" : ""}>± 30 ngày</option>
          <option value="365" ${f.window === 365 ? "selected" : ""}>Cả năm</option>
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
        state.discoverEvents = data.events;
        $("#nav-event-count").textContent = data.count;
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

    let debounce = null;
    $("#q").addEventListener("input", (e) => {
      f.q = e.target.value;
      clearTimeout(debounce);
      debounce = setTimeout(load, 280);
    });
    $("#day").addEventListener("change", (e) => {
      f.date = e.target.value || isoToday();
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
      const filtered = list.filter((p) => (!filterStatus || p.status === filterStatus) &&
        (!q || `${p.article_title} ${p.fb_hook} ${p.artist?.name}`.toLowerCase().includes(q.toLowerCase())));
      $("#plist").innerHTML = filtered.length
        ? `<div class="rows">${filtered.map(projectRow).join("")}</div>`
        : `<div class="empty"><h3>Không có dự án phù hợp</h3><p>Đổi bộ lọc hoặc tạo dự án mới từ mục Khám phá.</p><a class="btn btn-primary" href="#/discover">Tạo reels</a></div>`;
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

  // ------------------------------------------------------------------ project studio
  async function viewProject(id) {
    if (!id) return viewDashboard();
    const project = await api(`/api/projects/${id}`);
    state.project = project;
    state.tab = "article";
    state.overlayOptions = null;
    renderProjectShell();
  }

  function renderProjectShell() {
    const p = state.project;
    const a = p.artist || {};
    const ev = p.event || {};
    const evLabel = ev.kind === "release" ? ev.title : ev.kind === "birthday" ? `Sinh nhật lần thứ ${ev.age}` : `${ev.years} năm ngày mất`;
    const tabs = [
      ["article", "1", "Bài báo"],
      ["video", "2", "Video & MP4"],
      ["caption", "3", "Hook & Comment"],
      ["checks", "4", "Kiểm tra"],
    ];
    const done = {
      article: Boolean(p.article_title && p.article_body),
      video: Boolean(p.render_url),
      caption: Boolean(p.caption),
      checks: false,
    };
    $("#view").innerHTML = `
      <div class="studio-head">
        <a class="btn btn-icon btn-ghost" href="#/projects" title="Quay lại">${ICON.back}</a>
        <div class="studio-avatar"><img src="${esc(p.banner_url)}" alt="" /></div>
        <div class="studio-title">
          <h1>${esc(a.name)}</h1>
          <div class="sub">
            <span>${esc(evLabel || "")}</span><span style="opacity:.4;margin:0 4px">·</span>
            <span>${esc(ev.date ? fmtLong(ev.date) : "")}</span><span style="opacity:.4">·</span>
            <span>${esc(a.genre || "")}</span><span style="opacity:.4">·</span>
            <span>${esc(a.era || "")}</span>
          </div>
        </div>
        <div class="studio-actions">
          ${statusChip(p.status)}
          <select class="select" id="status-select" style="max-width:170px">
            ${STATUS_ORDER.map((s) => `<option value="${s}" ${p.status === s ? "selected" : ""}>${STATUS_LABEL[s]}</option>`).join("")}
          </select>
          <button class="btn btn-ghost btn-sm" id="btn-export">${ICON.download} Xuất .md</button>
          <button class="btn btn-ghost btn-sm" id="btn-dup">${ICON.copy} Nhân bản</button>
          <button class="btn btn-danger btn-sm" id="btn-del" title="Xoá dự án">${ICON.trash}</button>
        </div>
      </div>
      <div class="tabs">
        ${tabs.map(([key, num, label]) => `
          <button class="tab ${state.tab === key ? "active" : ""}" data-tab="${key}">
            <span class="num">${num}</span> ${label}
            ${done[key] ? '<span class="done">✓</span>' : ""}
          </button>`).join("")}
      </div>
      <div id="tab-body"></div>`;

    $$(".tab").forEach((t) => t.addEventListener("click", () => {
      state.tab = t.dataset.tab;
      stopPreview();
      $$(".tab").forEach((x) => x.classList.toggle("active", x === t));
      renderTab();
    }));
    $("#status-select").addEventListener("change", async (e) => {
      const updated = await api(`/api/projects/${p.id}`, { method: "PATCH", body: { status: e.target.value } });
      state.project = updated;
      renderProjectShell();
      toast(`Đã chuyển trạng thái: ${STATUS_LABEL[updated.status]}`, "ok");
    });
    $("#btn-export").onclick = () => window.open(`/api/projects/${p.id}/export?fmt=md`, "_blank");
    $("#btn-dup").onclick = async () => {
      const copy = await api(`/api/projects/${p.id}/duplicate`, { method: "POST" });
      toast("Đã nhân bản dự án", "ok");
      location.hash = `#/project/${copy.id}`;
    };
    $("#btn-del").onclick = async () => {
      if (!(await confirmDialog("Xoá dự án?", `Toàn bộ bài báo, kịch bản và video của ${a.name} sẽ bị xoá.`, "Xoá dự án"))) return;
      await api(`/api/projects/${p.id}`, { method: "DELETE" });
      toast("Đã xoá dự án", "ok");
      await boot();
      location.hash = "#/projects";
    };
    renderTab();
  }

  function renderTab() {
    stopPreview();
    const body = $("#tab-body");
    if (state.tab === "article") body.innerHTML = articleTab();
    if (state.tab === "video") body.innerHTML = videoTab();
    if (state.tab === "caption") body.innerHTML = captionTab();
    if (state.tab === "checks") body.innerHTML = checksTab();
    if (state.tab === "article") bindArticleTab();
    if (state.tab === "video") bindVideoTab();
    if (state.tab === "caption") bindCaptionTab();
    if (state.tab === "checks") bindChecksTab();
  }

  // ------------------------------------------------------------------ article tab
  function articleTab() {
    const p = state.project;
    const titles = p.article_titles || [];
    const links = p.music_links || [];
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
              <label>Ảnh banner nghệ sĩ <span class="hint">tỉ lệ đẹp nhất 3:4 hoặc 9:16</span></label>
              <div class="banner-drop" id="banner-drop">
                <img src="${esc(p.banner_url)}" alt="" id="banner-img" />
                <div class="bd-actions">
                  <button class="btn btn-sm" id="btn-wiki">${ICON.image} Lấy ảnh Wikipedia</button>
                  <button class="btn btn-sm btn-ghost" id="btn-upload">Tải ảnh lên</button>
                  <input type="file" accept="image/*" id="banner-file" hidden />
                </div>
              </div>
              <div class="banner-tip">Ảnh gốc của nghệ sĩ giúp reel có cảm xúc hơn ảnh nền. Nếu chưa có, studio dùng ảnh sân khấu/vinyl có sẵn.</div>
            </div>

            <div class="field">
              <label>Tiêu đề <span class="hint"><span id="title-count">${(p.article_title || "").length}</span>/100 ký tự</span></label>
              <input class="input" id="f-title" value="${esc(p.article_title)}" maxlength="140" />
              <div class="chip-row" style="margin-top:8px">
                ${titles.filter((t) => t !== p.article_title).slice(0, 3).map((t, i) => `<button class="chip" data-title="${esc(t)}">${esc(t.slice(0, 58))}${t.length > 58 ? "…" : ""}</button>`).join("")}
              </div>
            </div>

            <div class="field">
              <label>Mô tả ngắn (dek)</label>
              <textarea class="textarea" id="f-dek" style="min-height:70px">${esc(p.article_dek)}</textarea>
            </div>

            <div class="field">
              <label>Nội dung bài báo <span class="hint" id="body-count">${wordCount(p.article_body)} từ</span></label>
              <textarea class="textarea serif" id="f-body" style="min-height:360px">${esc(p.article_body)}</textarea>
            </div>

            <div class="field">
              <label>Link nhạc <span class="hint">bấm để nghe thử</span></label>
              <div class="music-list" id="music-list">
                ${links.map((s, i) => `
                  <div class="music-item" data-i="${i}">
                    <div>
                      <div class="mi-title">${esc(s.title)}</div>
                      <div class="mi-year">${esc(s.year)} · ${esc(s.note || "")}</div>
                    </div>
                    <div class="mi-year">${esc(s.year)}</div>
                    <div class="row" style="gap:6px">
                      <a href="${esc(s.youtube)}" target="_blank" rel="noopener" class="tag">YouTube</a>
                      <a href="${esc(s.spotify)}" target="_blank" rel="noopener" class="tag">Spotify</a>
                    </div>
                  </div>`).join("")}
              </div>
            </div>

            <div class="field" style="margin-bottom:0">
              <label>Comment đầu tiên (pin) <span class="hint">${(p.first_comment || "").length} ký tự</span></label>
              <textarea class="textarea" id="f-comment" style="min-height:150px">${esc(p.first_comment)}</textarea>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h3>Xem trước bài báo</h3>
            <div class="spacer"></div>
            <button class="btn btn-sm btn-ghost" id="btn-copy-article">${ICON.copy} Copy</button>
          </div>
          <div class="panel-body">
            <div class="preview-paper">
              <h2 id="pv-title">${esc(p.article_title)}</h2>
              <div class="pp-dek" id="pv-dek">${esc(p.article_dek)}</div>
              <img class="pp-img" src="${esc(p.banner_url)}" alt="" id="pv-img" />
              <div class="pp-body" id="pv-body">${mdLite(p.article_body)}</div>
            </div>
            <div class="card card-pad" style="margin-top:16px;background:rgba(255,255,255,0.03)">
              <div class="row-between" style="margin-bottom:8px">
                <b style="font-size:13px">Checklist bài báo</b>
                <span class="tag ${p.article_title && p.article_body ? "tag-ok" : "tag-warn"}">${p.article_title && p.article_body ? "ổn" : "cần bổ sung"}</span>
              </div>
              <div class="tiny muted">
                • Tiêu đề dưới 100 ký tự<br>
                • Có ít nhất 3 link nhạc<br>
                • Comment đầu tiên chứa link nhạc + lời dẫn<br>
                • Ảnh banner là ảnh dọc (3:4 hoặc 9:16)
              </div>
            </div>
          </div>
        </div>
      </div>`;
  }

  function bindArticleTab() {
    const p = state.project;
    const autoSave = debounceSave();

    const syncPreview = () => {
      $("#pv-title").textContent = p.article_title;
      $("#pv-dek").textContent = p.article_dek;
      $("#pv-body").innerHTML = mdLite(p.article_body);
      $("#title-count").textContent = (p.article_title || "").length;
      $("#body-count").textContent = `${wordCount(p.article_body)} từ`;
    };

    $("#f-title").addEventListener("input", (e) => { p.article_title = e.target.value; syncPreview(); autoSave({ article_title: e.target.value }); });
    $("#f-dek").addEventListener("input", (e) => { p.article_dek = e.target.value; syncPreview(); autoSave({ article_dek: e.target.value }); });
    $("#f-body").addEventListener("input", (e) => { p.article_body = e.target.value; syncPreview(); autoSave({ article_body: e.target.value }); });
    $("#f-comment").addEventListener("input", (e) => { p.first_comment = e.target.value; autoSave({ first_comment: e.target.value }); });
    $$("[data-title]").forEach((chip) => chip.addEventListener("click", () => {
      p.article_title = chip.dataset.title;
      $("#f-title").value = p.article_title;
      syncPreview();
      autoSave({ article_title: p.article_title });
    }));

    $("#btn-save-article").onclick = async () => {
      const updated = await api(`/api/projects/${p.id}`, {
        method: "PATCH",
        body: { article_title: p.article_title, article_dek: p.article_dek, article_body: p.article_body, first_comment: p.first_comment },
      });
      state.project = updated;
      toast("Đã lưu bài báo", "ok");
    };

    $("#btn-copy-article").onclick = () => {
      const text = `${p.article_title}\n\n${p.article_dek}\n\n${p.article_body}\n\n---\nFIRST COMMENT:\n${p.first_comment}`;
      copyText(text, "Đã copy bài báo");
    };

    $("#btn-regen-article").onclick = async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        const updated = await api(`/api/projects/${p.id}/generate`, { method: "POST", body: { section: "all" } });
        state.project = updated;
        renderProjectShell();
        toast("Đã tạo lại bài báo + kịch bản video", "ok");
      } catch (err) {
        toast(err.message, "err");
        btn.disabled = false;
      }
    };

    // banner
    $("#btn-upload").onclick = () => $("#banner-file").click();
    $("#banner-file").onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      await uploadBanner(file, "Đã cập nhật ảnh banner");
    };
    $("#btn-wiki").onclick = () => fetchWikiBanner();

    async function uploadBanner(blob, message) {
      const fd = new FormData();
      fd.append("file", blob, blob.name || "banner.jpg");
      try {
        const updated = await api(`/api/projects/${p.id}/banner`, { method: "POST", body: fd });
        state.project = updated;
        const img = $("#banner-img");
        const pv = $("#pv-img");
        const head = $(".studio-avatar img");
        const bust = `?v=${Date.now()}`;
        if (img) img.src = updated.banner_url + bust;
        if (pv) pv.src = updated.banner_url + bust;
        if (head) head.src = updated.banner_url + bust;
        toast(message, "ok");
      } catch (err) {
        toast(err.message, "err");
      }
    }

    async function fetchWikiBanner() {
      const wiki = p.artist?.wikipedia;
      if (!wiki) return toast("Nghệ sĩ này chưa có trang Wikipedia", "err");
      const btn = $("#btn-wiki");
      btn.disabled = true;
      btn.innerHTML = "Đang tải ảnh…";
      try {
        const summary = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(wiki)}`, { headers: { Accept: "application/json" } }).then((r) => r.json());
        const src = summary?.originalimage?.source || summary?.thumbnail?.source;
        if (!src) throw new Error("Trang Wikipedia không có ảnh cho nghệ sĩ này");
        const blob = await fetch(src, { mode: "cors" }).then((r) => {
          if (!r.ok) throw new Error("Không tải được ảnh từ Wikipedia");
          return r.blob();
        });
        await uploadBanner(new File([blob], "wiki.jpg", { type: blob.type || "image/jpeg" }), "Đã lấy ảnh từ Wikipedia");
      } catch (err) {
        toast(`${err.message}. Bạn có thể tải ảnh lên thủ công.`, "err");
      } finally {
        btn.disabled = false;
        btn.innerHTML = `${ICON.image} Lấy ảnh Wikipedia`;
      }
    }
  }

  // ------------------------------------------------------------------ video tab
  function videoTab() {
    const p = state.project;
    const plan = p.video_plan || {};
    const scenes = plan.scenes || [];
    const styles = state.boot?.styles || {};
    return `
      <div class="split">
        <div class="panel">
          <div class="panel-head">
            <h3>Kịch bản reel</h3>
            <span class="tag tag-violet">${esc(plan.duration || 24)}s · 1080×1920</span>
            <div class="spacer"></div>
            <button class="btn btn-sm" id="btn-regen-video">${ICON.refresh} Viết lại kịch bản</button>
          </div>
          <div class="panel-body">
            <div class="field">
              <label>Chữ trên video <span class="hint">bắt buộc 9–15 từ</span></label>
              <textarea class="textarea" id="f-overlay" style="min-height:88px;font-weight:600">${esc(p.video_overlay_text)}</textarea>
              <div class="row-between" style="margin-top:6px">
                <span class="counter ${wordCount(p.video_overlay_text) >= 9 && wordCount(p.video_overlay_text) <= 15 ? "good" : "bad"}" id="overlay-count">${wordCount(p.video_overlay_text)} từ</span>
                <button class="btn btn-sm btn-ghost" id="btn-suggest">${ICON.spark} Gợi ý khác</button>
              </div>
              <div id="overlay-options" style="margin-top:10px"></div>
            </div>

            <div class="field">
              <label>Hook Facebook (dòng đầu bài đăng)</label>
              <textarea class="textarea" id="f-hook" style="min-height:82px">${esc(p.fb_hook)}</textarea>
            </div>

            <div class="field">
              <label>Phong cách hình ảnh</label>
              <div class="chip-row" id="style-row">
                ${Object.entries(styles).map(([k, v]) => `<button class="chip ${((p.video_style || "noir") === k) ? "active" : ""}" data-style="${k}"><span style="width:9px;height:9px;border-radius:50%;background:${esc(v.accent)};display:inline-block"></span>${esc(v.label)}</button>`).join("")}
              </div>
            </div>

            <div class="field">
              <label>Nhạc nền</label>
              <div class="chip-row" id="audio-row">
                <button class="chip ${p.audio_choice === "bed" ? "active" : ""}" data-audio="bed">Nhạc nền có sẵn</button>
                <button class="chip ${p.audio_choice === "upload" ? "active" : ""}" data-audio="upload">Nhạc của tôi</button>
                <button class="chip ${p.audio_choice === "none" ? "active" : ""}" data-audio="none">Không nhạc</button>
              </div>
              <div class="row" style="margin-top:10px;gap:8px;flex-wrap:wrap">
                <button class="btn btn-sm btn-ghost" id="btn-audio-upload">Tải file nhạc (mp3/m4a/wav)</button>
                <input type="file" id="audio-file" accept="audio/*" hidden />
                ${p.audio_url ? `<audio controls src="${esc(p.audio_url)}" style="height:34px;max-width:240px"></audio>` : ""}
              </div>
              <div class="banner-tip">Dùng nhạc bạn có quyền sử dụng. Nhạc nền có sẵn là bản tổng hợp nhẹ để reel không bị im lặng.</div>
            </div>

            <hr class="sep" />

            <div class="row-between">
              <div>
                <b style="font-size:14px">Render MP4</b>
                <div class="tiny muted" id="render-hint">${p.render_url ? "Video đã có. Render lại nếu bạn đã sửa nội dung." : "Mất khoảng 40–60 giây cho reel 24s."}</div>
              </div>
              <button class="btn btn-primary" id="btn-render">${ICON.play} Render MP4</button>
            </div>
            <div id="render-progress" style="margin-top:14px;display:none">
              <div class="render-bar"><i id="render-fill"></i></div>
              <div class="tiny muted" id="render-msg" style="margin-top:8px">Đang chuẩn bị…</div>
            </div>
            <div id="video-result" style="margin-top:16px">
              ${p.render_url ? renderResultHtml(p) : ""}
            </div>
          </div>
        </div>

        <div>
          <div class="panel" style="margin-bottom:16px">
            <div class="panel-head">
              <h3>Preview dọc 9:16</h3>
              <div class="spacer"></div>
              <span class="tiny muted">chạy thử kịch bản</span>
            </div>
            <div class="panel-body phone-wrap">
              ${phonePreviewHtml(p)}
            </div>
          </div>
          <div class="panel">
            <div class="panel-head"><h3>Timeline</h3></div>
            <div class="panel-body tight">
              ${scenes.map((s) => `
                <div class="row" style="align-items:flex-start;gap:10px;padding:8px 6px;border-bottom:1px solid var(--line)">
                  <span class="tiny mono muted" style="width:74px;flex:0 0 auto">${s.start.toFixed(1)}–${s.end.toFixed(1)}s</span>
                  <div style="flex:1">
                    <div class="tiny" style="letter-spacing:.08em;text-transform:uppercase;color:var(--accent)">${esc(s.label)}</div>
                    <div style="font-size:12.5px;margin-top:2px">${esc(s.text)}${s.sub ? `<span class="muted"> · ${esc(s.sub)}</span>` : ""}</div>
                  </div>
                </div>`).join("")}
            </div>
          </div>
        </div>
      </div>`;
  }

  function renderResultHtml(p) {
    const size = p.render_path ? "" : "";
    return `
      <div class="video-box"><video src="${esc(p.render_url)}" controls playsinline poster="${esc(p.poster_url || "")}"></video></div>
      <div class="row-between" style="margin-top:10px">
        <span class="tiny muted">MP4 · H.264 · 1080×1920 · ${esc((p.video_plan || {}).duration || 24)}s ${p.render_seconds ? `· render ${Math.round(p.render_seconds)}s` : ""}</span>
        <div class="row" style="gap:8px">
          <a class="btn btn-sm" href="${esc(p.render_url)}" download>${ICON.download} Tải MP4</a>
          <button class="btn btn-sm btn-ghost" id="btn-copy-video-path">Copy link</button>
        </div>
      </div>`;
  }

  function phonePreviewHtml(p) {
    const plan = p.video_plan || {};
    const scenes = plan.scenes || [];
    return `
      <div class="phone" id="phone">
        <img class="ph-bg" src="${esc(p.banner_url)}" alt="" />
        <div class="ph-grad"></div>
        <div class="ph-hud-top">
          <span class="ph-badge">${esc(plan.badge || "ON THIS DAY")}</span>
          <div class="ph-progress"><i id="ph-fill"></i></div>
        </div>
        <div class="ph-stage" id="ph-stage">
          ${scenes.map((s, i) => phoneSceneHtml(s, i)).join("")}
        </div>
        <div class="ph-footer">
          <div class="ph-wave">${Array.from({ length: 18 }).map((_, i) => `<i style="animation-delay:${(i * 0.07).toFixed(2)}s"></i>`).join("")}</div>
          <div class="ph-name">${esc(p.artist?.name || "")}</div>
        </div>
      </div>`;
  }

  function phoneSceneHtml(s, i) {
    if (s.kind === "stat") return `<div class="ph-scene" data-scene="${i}"><div class="ph-big">${esc(s.text)}</div><div class="ph-sub">${esc(s.sub || "")}</div></div>`;
    if (s.kind === "song") return `<div class="ph-scene" data-scene="${i}"><div class="ph-script">now playing</div><div class="ph-song">“${esc(s.text)}”</div><div class="ph-sub">${esc(s.sub || "")}</div><div class="ph-note">${esc(s.note || "")}</div></div>`;
    if (s.kind === "curiosity") return `<div class="ph-scene" data-scene="${i}"><div class="ph-script">the part nobody tells you</div><div class="ph-say">${esc(s.text)}</div><div class="ph-sub">${esc(s.sub || "")}</div></div>`;
    if (s.kind === "cta") return `<div class="ph-scene" data-scene="${i}"><div class="ph-bubble"><small>top comment · pinned</small>${esc(s.text)}<span>${esc(s.sub || "")}</span></div><div class="ph-arrow"></div><div class="ph-cta">READ IT IN THE<br>FIRST COMMENT</div><div class="ph-script">follow for more legends</div></div>`;
    return `<div class="ph-scene" data-scene="${i}"><div class="ph-hook">${esc(s.text)}</div><div class="ph-script">full story in the first comment</div></div>`;
  }

  function startPreview() {
    stopPreview();
    const scenes = $$("#ph-stage .ph-scene");
    if (!scenes.length) return;
    let i = 0;
    const show = () => {
      scenes.forEach((s, idx) => s.classList.toggle("on", idx === i));
      const fill = $("#ph-fill");
      if (fill) fill.style.width = `${((i + 1) / scenes.length) * 100}%`;
      i = (i + 1) % scenes.length;
    };
    show();
    state.previewTimer = setInterval(show, 1700);
  }

  function stopPreview() {
    if (state.previewTimer) clearInterval(state.previewTimer);
    state.previewTimer = null;
  }

  function bindVideoTab() {
    const p = state.project;
    const autoSave = debounceSave();
    startPreview();

    const overlayEl = $("#f-overlay");
    overlayEl.addEventListener("input", (e) => {
      const words = wordCount(e.target.value);
      const counter = $("#overlay-count");
      counter.textContent = `${words} từ`;
      counter.className = `counter ${words >= 9 && words <= 15 ? "good" : "bad"}`;
      p.video_overlay_text = e.target.value;
      const hooks = $$("#ph-stage .ph-scene");
      if (hooks[0]) $(".ph-hook", hooks[0]).textContent = e.target.value;
      autoSave({ video_overlay_text: e.target.value });
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

    $("#btn-suggest").onclick = async (e) => {
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
          $("#f-overlay").value = chip.dataset.opt;
          $("#f-overlay").dispatchEvent(new Event("input"));
          $("#overlay-options").innerHTML = "";
          toast("Đã áp dụng chữ trên video", "ok");
        }));
      } catch (err) { toast(err.message, "err"); }
      finally { btn.disabled = false; }
    };

    $$("#style-row [data-style]").forEach((chip) => chip.addEventListener("click", async () => {
      $$("#style-row .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      p.video_style = chip.dataset.style;
      await api(`/api/projects/${p.id}`, { method: "PATCH", body: { video_style: chip.dataset.style } });
    }));

    $$("#audio-row [data-audio]").forEach((chip) => chip.addEventListener("click", async () => {
      $$("#audio-row .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      const updated = await api(`/api/projects/${p.id}/audio-choice`, { method: "POST", body: { choice: chip.dataset.audio } });
      state.project = updated;
    }));

    $("#btn-audio-upload").onclick = () => $("#audio-file").click();
    $("#audio-file").onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append("file", file);
      try {
        const updated = await api(`/api/projects/${p.id}/audio`, { method: "POST", body: fd });
        state.project = updated;
        toast("Đã tải nhạc lên", "ok");
        renderTab();
      } catch (err) { toast(err.message, "err"); }
    };

    $("#btn-render").onclick = async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      $("#render-progress").style.display = "block";
      $("#render-fill").style.width = "2%";
      $("#render-msg").textContent = "Đang khởi động…";
      try {
        const { job } = await api(`/api/projects/${p.id}/render`, { method: "POST", body: {} });
        pollJob(job.id, p.id);
      } catch (err) {
        toast(err.message, "err");
        btn.disabled = false;
        $("#render-progress").style.display = "none";
      }
    };

    const copyPath = $("#btn-copy-video-path");
    if (copyPath) copyPath.onclick = () => copyText(`${location.origin}${p.render_url}`, "Đã copy link video");
  }

  async function pollJob(jobId, projectId) {
    const tick = async () => {
      try {
        const job = await api(`/api/jobs/${jobId}`);
        $("#render-fill").style.width = `${Math.max(2, job.progress || 0)}%`;
        $("#render-msg").textContent = job.message || "Đang render…";
        if (job.status === "done") {
          const updated = await api(`/api/projects/${projectId}`);
          state.project = updated;
          $("#render-msg").textContent = `Xong! ${job.size_mb || ""} MB · ${job.seconds}s`;
          $("#video-result").innerHTML = renderResultHtml(updated);
          const copyPath = $("#btn-copy-video-path");
          if (copyPath) copyPath.onclick = () => copyText(`${location.origin}${updated.render_url}`, "Đã copy link video");
          $("#render-hint").textContent = "Video đã render. Bạn có thể tải về và đăng lên Facebook.";
          const chip = $(".studio-actions .status");
          if (chip) {
            chip.className = `status status-${updated.status}`;
            chip.textContent = STATUS_LABEL[updated.status] || updated.status;
          }
          const statusSelect = $("#status-select");
          if (statusSelect) statusSelect.value = updated.status;
          toast("Render MP4 xong", "ok");
          await boot();
          const btn = $("#btn-render");
          if (btn) btn.disabled = false;
          return;
        }
        if (job.status === "error") {
          $("#render-msg").textContent = `Lỗi: ${job.message}`;
          toast("Render thất bại", "err");
          const btn = $("#btn-render");
          if (btn) btn.disabled = false;
          return;
        }
        setTimeout(tick, 1200);
      } catch (err) {
        toast(err.message, "err");
      }
    };
    tick();
  }

  // ------------------------------------------------------------------ caption tab
  function captionTab() {
    const p = state.project;
    return `
      <div class="split">
        <div class="panel">
          <div class="panel-head"><h3>Bài đăng Facebook</h3><div class="spacer"></div><button class="btn btn-sm btn-primary" id="btn-save-caption">${ICON.save} Lưu</button></div>
          <div class="panel-body">
            <div class="field">
              <label>Hook (dòng đầu tiên) <span class="hint">quan trọng nhất — hiện trước khi bấm “xem thêm”</span></label>
              <textarea class="textarea" id="f-hook2" style="min-height:80px">${esc(p.fb_hook)}</textarea>
            </div>
            <div class="field">
              <label>Caption đầy đủ <span class="hint">${(p.caption || "").length} ký tự</span></label>
              <textarea class="textarea" id="f-caption" style="min-height:170px">${esc(p.caption)}</textarea>
            </div>
            <div class="field">
              <label>Hashtag <span class="hint">8–10 tag cho thị trường Mỹ</span></label>
              <input class="input" id="f-tags" value="${esc(p.hashtags)}" />
            </div>
            <div class="field" style="margin-bottom:0">
              <label>Comment đầu tiên <span class="hint">pin ngay sau khi đăng</span></label>
              <textarea class="textarea" id="f-comment2" style="min-height:150px">${esc(p.first_comment)}</textarea>
              <div class="row" style="margin-top:8px">
                <button class="btn btn-sm" id="btn-copy-comment">${ICON.copy} Copy comment</button>
                <button class="btn btn-sm btn-ghost" id="btn-copy-caption">${ICON.copy} Copy caption</button>
              </div>
            </div>
          </div>
        </div>

        <div>
          <div class="panel" style="margin-bottom:16px">
            <div class="panel-head"><h3>Xem như trên Facebook</h3></div>
            <div class="panel-body">
              <div class="card" style="background:#14161f;padding:0;overflow:hidden">
                <div class="row" style="padding:12px 14px;gap:10px">
                  <div class="studio-avatar" style="width:38px;height:38px;border-radius:50%"><img src="/assets/${esc(p.artist?.cover || "bg-stage.jpg")}" alt=""></div>
                  <div><div style="font-size:13px;font-weight:600">Legends Reel Studio</div><div class="tiny muted">Vừa xong · 🌐</div></div>
                </div>
                <div style="padding:0 14px 12px;font-size:13px;white-space:pre-wrap;line-height:1.5" id="fb-preview">${esc(p.caption)}</div>
                ${p.render_url ? `<video src="${esc(p.render_url)}" controls playsinline poster="${esc(p.poster_url || "")}" style="width:100%;background:#000;max-height:420px"></video>` : `<div style="aspect-ratio:4/5;background:#0d0f15;display:grid;place-items:center;color:#6c7383;font-size:12px">chưa render video</div>`}
                <div class="row" style="padding:10px 14px;gap:18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)">
                  <span>👍 Thích</span><span>💬 Bình luận</span><span>↗ Chia sẻ</span>
                </div>
              </div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-head"><h3>Comment sẽ pin</h3><div class="spacer"></div><button class="btn btn-sm btn-ghost" id="btn-copy-comment2">${ICON.copy}</button></div>
            <div class="panel-body">
              <div class="copy-box" id="comment-preview">${esc(p.first_comment)}</div>
            </div>
          </div>
        </div>
      </div>`;
  }

  function bindCaptionTab() {
    const p = state.project;
    const autoSave = debounceSave();
    const syncFb = () => { $("#fb-preview").textContent = p.caption; };
    $("#f-hook2").addEventListener("input", (e) => { p.fb_hook = e.target.value; autoSave({ fb_hook: e.target.value }); });
    $("#f-caption").addEventListener("input", (e) => { p.caption = e.target.value; syncFb(); autoSave({ caption: e.target.value }); });
    $("#f-tags").addEventListener("input", (e) => { p.hashtags = e.target.value; autoSave({ hashtags: e.target.value }); });
    $("#f-comment2").addEventListener("input", (e) => {
      p.first_comment = e.target.value;
      $("#comment-preview").textContent = e.target.value;
      autoSave({ first_comment: e.target.value });
    });
    $("#btn-save-caption").onclick = async () => {
      state.project = await api(`/api/projects/${p.id}`, {
        method: "PATCH",
        body: { fb_hook: p.fb_hook, caption: p.caption, hashtags: p.hashtags, first_comment: p.first_comment },
      });
      toast("Đã lưu bài đăng", "ok");
    };
    $("#btn-copy-comment").onclick = () => copyText(p.first_comment, "Đã copy comment");
    $("#btn-copy-comment2").onclick = () => copyText(p.first_comment, "Đã copy comment");
    $("#btn-copy-caption").onclick = () => copyText(`${p.caption}\n\n${p.hashtags}`, "Đã copy caption + hashtag");
  }

  // ------------------------------------------------------------------ checks tab
  function checksTab() {
    const p = state.project;
    const checks = p.checks || [];
    const overlayWords = wordCount(p.video_overlay_text);
    return `
      <div class="split">
        <div class="panel">
          <div class="panel-head"><h3>Điều kiện xuất bản</h3><div class="spacer"></div><span class="tag ${checks.every((c) => c.ok) ? "tag-ok" : "tag-warn"}">${checks.filter((c) => c.ok).length}/${checks.length} đạt</span></div>
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
              <button class="btn btn-sm" id="btn-fix-overlay">Sửa chữ trên video (${overlayWords} từ)</button>
              <button class="btn btn-sm btn-ghost" id="btn-go-caption">Mở hook & comment</button>
              ${p.render_url ? `<a class="btn btn-sm btn-primary" href="${esc(p.render_url)}" download>${ICON.download} Tải MP4</a>` : `<button class="btn btn-sm btn-primary" id="btn-go-render">Render video</button>`}
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head"><h3>Checklist đăng reels (thị trường Mỹ)</h3></div>
          <div class="panel-body">
            <div class="tiny" style="line-height:1.85">
              <b>Kỹ thuật</b><br>
              • 1080×1920, 9:16, H.264, có tiếng<br>
              • Chữ nằm trong vùng an toàn (tránh 250px trên và 420px dưới)<br>
              • 3 giây đầu phải có hook + chuyển động<br>
              <br>
              <b>Nội dung</b><br>
              • Chữ trên video 9–15 từ, một ý duy nhất<br>
              • Hook FB nêu cảm xúc hoặc câu hỏi, không clickbait rỗng<br>
              • Comment đầu tiên chứa câu chuyện + link nhạc, được pin<br>
              • Kêu gọi cụ thể: “đọc comment đầu tiên”, “nghe bài này”<br>
              <br>
              <b>Đăng bài</b><br>
              • Khung giờ tốt cho khán giả 30–60 (giờ Mỹ): 7–9h sáng, 12–13h, 19–21h<br>
              • Đăng reel dạng công khai, thêm 8–10 hashtag<br>
              • Trả lời comment trong 30 phút đầu để tăng phân phối
            </div>
          </div>
        </div>
      </div>`;
  }

  function bindChecksTab() {
    const p = state.project;
    const goOverlay = () => { state.tab = "video"; $$(".tab").forEach((x) => x.classList.toggle("active", x.dataset.tab === "video")); renderTab(); $("#f-overlay")?.focus(); };
    $("#btn-fix-overlay").onclick = goOverlay;
    $("#btn-go-caption").onclick = () => { state.tab = "caption"; $$(".tab").forEach((x) => x.classList.toggle("active", x.dataset.tab === "caption")); renderTab(); };
    const goRender = $("#btn-go-render");
    if (goRender) goRender.onclick = () => { state.tab = "video"; $$(".tab").forEach((x) => x.classList.toggle("active", x.dataset.tab === "video")); renderTab(); };
  }

  // ------------------------------------------------------------------ howto
  function viewHowto() {
    const steps = [
      ["01", "Tìm sự kiện đúng ngày", "Chọn ngày và khoảng ± ngày. Studio quét sinh nhật, ngày mất và các kỷ niệm phát hành của những nghệ sĩ mà khán giả 30–60 tuổi vẫn nghe, kèm 3 bài nhạc liên quan và link nghe thử."],
      ["02", "Viết bài báo", "Mỗi sự kiện sinh ra một bài báo tiếng Anh: tiêu đề, mô tả, nội dung dài, 3 link nhạc và ảnh banner nghệ sĩ (lấy từ Wikipedia hoặc tải lên). Mọi trường đều sửa được."],
      ["03", "Dựng MP4 9:16", "Video dọc 24 giây: hook 3 giây đầu, con số sự kiện, bài nhạc, câu gây tò mò và màn hình comment giả lập kéo người xem xuống. Render ngay trong studio."],
      ["04", "Hook + comment", "Sinh hook Facebook, caption, hashtag và comment đầu tiên (chứa câu chuyện + link nhạc) để bạn pin. Copy là đăng được."],
    ];
    $("#view").innerHTML = `
      <section class="hero" style="grid-template-columns:1fr">
        <div>
          <div class="eyebrow">${ICON.spark} cách hoạt động</div>
          <h1>Một quy trình, bốn bước, ra thẳng bài đăng.</h1>
          <p>Studio chia việc thành bốn bước rõ ràng để bạn không phải mở nhiều công cụ. Mỗi bước đều có công cụ kiểm tra trước khi đăng: chữ trên video 9–15 từ, CTA kéo xuống comment, và comment đầu tiên đã sẵn sàng để pin.</p>
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
        <h3 style="margin:0 0 10px;font-size:15px">Mẹo để reel được đề xuất</h3>
        <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px">
          <div><b style="font-size:13px">3 giây quyết định</b><p class="muted tiny" style="margin:4px 0 0">Hook phải tự đứng một mình, không phụ thuộc ảnh. Đặt tên nghệ sĩ hoặc con số ngay trong câu đầu.</p></div>
          <div><b style="font-size:13px">Đừng kể hết</b><p class="muted tiny" style="margin:4px 0 0">Video chỉ mở vòng tò mò. Toàn bộ câu chuyện nằm ở comment đầu tiên — đó là nơi bạn giữ chân và tăng tương tác.</p></div>
          <div><b style="font-size:13px">Comment pin sớm</b><p class="muted tiny" style="margin:4px 0 0">Đăng xong, pin comment trong vòng 1 phút. Người xem reel thường mở comment ngay sau khi video kết thúc.</p></div>
          <div><b style="font-size:13px">Nhạc hợp gu</b><p class="muted tiny" style="margin:4px 0 0">Ưu tiên đoạn nhạc của chính nghệ sĩ nếu bạn có quyền. Nhạc nền có sẵn chỉ để reel không bị im lặng.</p></div>
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
          $("#crumb").innerHTML = `<span style="opacity:.6">Dự án</span> <span style="opacity:.4">/</span> <strong>Studio</strong>`;
        } catch (err) {
          toast(`Không lưu được: ${err.message}`, "err");
        }
      }, 700);
    };
  }

  // ------------------------------------------------------------------ global events
  $("#btn-new").addEventListener("click", () => { location.hash = "#/discover"; });
  window.addEventListener("hashchange", route);
  window.addEventListener("beforeunload", stopPreview);

  (async () => {
    await boot();
    await route();
  })();
})();
