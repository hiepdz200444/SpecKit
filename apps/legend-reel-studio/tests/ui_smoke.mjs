/**
 * jsdom smoke test for the Legend Reel Studio UI.
 *
 * Boots the real FastAPI app on a random port, loads the real SPA in jsdom,
 * then walks the sidebar (the nav bug), the three studio tabs, the copy
 * buttons and the voice panel. Run with:
 *
 *   npm install --no-save jsdom
 *   node tests/ui_smoke.mjs
 */
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync } from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM, VirtualConsole } from "jsdom";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP_DIR = path.resolve(HERE, "..");
const nodeFetch = globalThis.fetch;

const clipboard = { text: "" };
const pageErrors = [];
let checks = 0;

function ok(condition, message) {
  if (!condition) throw new Error(`FAIL: ${message}`);
  checks += 1;
  console.log(`  \u2713 ${message}`);
}

function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitFor(fn, message, timeout = 8000) {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    try {
      const value = await fn();
      if (value) return value;
    } catch (_) { /* keep polling */ }
    await sleep(60);
  }
  throw new Error(`timeout waiting for ${message}`);
}

async function startServer(port, dataDir) {
  const bin = existsSync(path.join(APP_DIR, ".venv", "bin", "python"))
    ? path.join(APP_DIR, ".venv", "bin", "python")
    : "python3";
  const child = spawn(
    bin,
    ["-m", "uvicorn", "app:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", String(port)],
    { cwd: APP_DIR, env: { ...process.env, LRS_DATA_DIR: dataDir }, stdio: ["ignore", "pipe", "pipe"] },
  );
  let log = "";
  child.stdout.on("data", (d) => { log += d.toString(); });
  child.stderr.on("data", (d) => { log += d.toString(); });
  await waitFor(async () => {
    const res = await nodeFetch(`http://127.0.0.1:${port}/api/bootstrap`);
    return res.ok;
  }, "uvicorn to answer /api/bootstrap", 30000).catch((err) => {
    child.kill("SIGKILL");
    throw new Error(`${err.message}\n${log}`);
  });
  return child;
}

async function main() {
  const dataDir = mkdtempSync(path.join(os.tmpdir(), "lrs-ui-"));
  const port = await freePort();
  const base = `http://127.0.0.1:${port}`;
  const server = await startServer(port, dataDir);
  let dom = null;
  let apiCalls = { events: 0, total: 0 };

  try {
    const virtualConsole = new VirtualConsole();
    virtualConsole.on("jsdomError", (err) => {
      if (String(err.message || "").includes("Not implemented")) return;
      pageErrors.push(err.message);
      if (process.env.UI_DEBUG) console.log("JSDOM ERROR:", err.message);
    });
    virtualConsole.on("error", (msg) => {
      pageErrors.push(String(msg));
      if (process.env.UI_DEBUG) console.log("CONSOLE ERROR:", msg);
    });

    dom = await JSDOM.fromURL(`${base}/`, {
      runScripts: "dangerously",
      resources: "usable",
      pretendToBeVisual: true,
      virtualConsole,
      beforeParse(window) {
        window.scrollTo = () => {};
        window.fetch = (input, init) => {
          const url = String(input).startsWith("http") ? String(input) : new URL(String(input), base).toString();
          apiCalls.total += 1;
          if (url.includes("/api/events")) apiCalls.events += 1;
          return nodeFetch(url, init);
        };
        Object.defineProperty(window.navigator, "clipboard", {
          value: { writeText: async (text) => { clipboard.text = String(text); } },
          configurable: true,
        });
        window.HTMLMediaElement.prototype.play = () => Promise.resolve();
        window.HTMLMediaElement.prototype.pause = () => {};
        window.confirm = () => true;
      },
    });

    const { window } = dom;
    const doc = window.document;
    const $ = (sel) => doc.querySelector(sel);
    const $$ = (sel) => Array.from(doc.querySelectorAll(sel));
    const click = (sel) => {
      const el = typeof sel === "string" ? $(sel) : sel;
      if (!el) throw new Error(`missing element: ${sel}`);
      el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
      return el;
    };
    const crumb = () => ($("#crumb") ? $("#crumb").textContent.replace(/\s+/g, " ").trim() : "");

    await waitFor(() => $("#view .hero") && $("[data-nav]"), "dashboard to render");

    console.log("• Sidebar navigation");
    ok($$("[data-nav]").length === 4, "4 sidebar items found");

    click('[data-nav="discover"]');
    await waitFor(() => window.location.hash === "#/discover" && $("#discover-results .section-head"), "discover view");
    ok(crumb().includes("Khám phá sự kiện"), "sidebar opens Khám phá sự kiện");
    ok($$("[data-nav]").find((b) => b.dataset.nav === "discover").classList.contains("active"), "active nav updated");

    click('[data-nav="projects"]');
    await waitFor(() => window.location.hash === "#/projects" && $("#plist"), "projects view");
    ok(crumb().includes("Dự án reels"), "sidebar opens Dự án reels");

    click('[data-nav="howto"]');
    await waitFor(() => window.location.hash === "#/howto" && /Bốn bước|bốn bước/.test($("#view").textContent), "howto view");
    ok(crumb().includes("Cách hoạt động"), "sidebar opens Cách hoạt động");

    click('[data-nav="dashboard"]');
    await waitFor(() => window.location.hash === "#/" && $("#view .hero"), "dashboard again");
    const before = apiCalls.events;
    click('[data-nav="dashboard"]');
    await waitFor(() => apiCalls.events > before && $("#view .hero"), "re-render on second click");
    ok(apiCalls.events > before, "clicking the active sidebar item re-renders the view");

    console.log("• Seed a project (article + script + images)");
    const events = await nodeFetch(`${base}/api/events?day=2026-11-04&window=400&q=elvis`).then((r) => r.json());
    const ev = events.events[0];
    const project = await nodeFetch(`${base}/api/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artist_id: ev.artist_id, event: ev }),
    }).then((r) => r.json());
    ok(project.id && project.article_words >= 700, `project created with a 700–900 word article (${project.article_words})`);

    const asset = await nodeFetch(`${base}/assets/bg-stage.jpg`);
    const bytes = await asset.arrayBuffer();
    for (const name of ["a.jpg", "b.jpg"]) {
      const fd = new FormData();
      fd.append("files", new Blob([bytes], { type: "image/jpeg" }), name);
      const res = await nodeFetch(`${base}/api/projects/${project.id}/images/upload`, { method: "POST", body: fd }).then((r) => r.json());
      if (res.added !== 1) throw new Error(`image upload failed: ${JSON.stringify(res.errors)}`);
    }

    console.log("• Studio shell");
    window.location.hash = `#/project/${project.id}`;
    await waitFor(() => $(".studio-title h1") && $(".tabs"), "studio shell");
    const tabs = $$(".tab").map((t) => t.textContent.replace(/\s+/g, " ").trim());
    ok(tabs.some((t) => t.includes("Bài báo")), "tab Bài báo present");
    ok(tabs.some((t) => t.includes("Ảnh nghệ sĩ")), "tab Ảnh nghệ sĩ present");
    ok(tabs.some((t) => t.includes("Text & Voice")), "tab Text & Voice present");
    ok(!tabs.some((t) => /video|mp4/i.test(t)), "no Video/MP4 tab");

    console.log("• Tab Bài báo");
    await waitFor(() => $("#f-title") && $("#f-body"), "article tab");
    const wc = Number(($("#body-count").textContent.match(/\d+/) || [0])[0]);
    ok(wc >= 700 && wc <= 900, `word counter shows the 700–900 range (${wc})`);
    ok($("#body-warn").textContent.includes("700–900") || /nằm trong/.test($("#body-warn").textContent), "range warning/hint rendered");
    ok($('[data-copy="title"]') && $('[data-copy="body"]') && $('[data-copy="links"]'), "each article block has a Copy button");
    click('[data-copy="title"]');
    await waitFor(() => clipboard.text === $("#f-title").value, "clipboard holds the title");
    ok(clipboard.text === $("#f-title").value, "Copy tiêu đề writes the title to the clipboard");

    // typing an out-of-range body must warn instead of silently failing
    const bodyEl = $("#f-body");
    bodyEl.value = "only six words in this short body";
    bodyEl.dispatchEvent(new window.Event("input", { bubbles: true }));
    await waitFor(() => $(".counter.bad") && $("#body-warn").classList.contains("bad"), "out-of-range warning");
    ok($("#body-warn").textContent.includes("cần nằm trong"), "editing below 700 words shows a warning");
    bodyEl.value = project.article_body;
    bodyEl.dispatchEvent(new window.Event("input", { bubbles: true }));

    console.log("• Tab Ảnh nghệ sĩ");
    click('[data-tab="images"]');
    await waitFor(() => $("#img-grid") && $$(".img-card").length === 2, "image grid");
    ok($("#img-count").textContent.includes("2/20"), "image counter shows 2/20");
    ok($$(".img-card.is-banner").length === 1, "exactly one image is marked as banner");
    ok($$('.img-card a[download]').length === 2, "every image has a download button");
    ok(($("#btn-zip").getAttribute("href") || "").endsWith("images.zip"), "Tải tất cả (.zip) points at the archive");
    ok(!!$("#img-urls") && !!$("#btn-import-urls"), "paste-a-link import box available");
    const bannerTarget = $$(".img-card").find((c) => !c.classList.contains("is-banner"));
    const bannerId = bannerTarget.dataset.img;
    click(bannerTarget.querySelector("[data-set-banner]"));
    const isBanner = () => {
      const card = $$(".img-card").find((c) => c.dataset.img === bannerId);
      return Boolean(card && card.classList.contains("is-banner"));
    };
    await waitFor(isBanner, "banner switch");
    ok(isBanner(), "Đặt làm banner switches the banner");
    ok($$(".img-card.is-banner").length === 1, "still exactly one banner after the switch");
    ok(/Pinterest/i.test($("#view").textContent), "UI explains the no-Pinterest-scraping policy");
    ok(/Wikipedia/.test($("#view").textContent), "UI offers Wikipedia + Commons import");

    console.log("• Tab Text & Voice");
    click('[data-tab="script"]');
    await waitFor(() => $("#f-overlay") && $("#voice-select"), "script tab");
    const overlayWords = Number(($("#overlay-count").textContent.match(/\d+/) || [0])[0]);
    ok(overlayWords >= 9 && overlayWords <= 15, `on-screen text is 9–15 words (${overlayWords})`);
    ok($('[data-copy="overlay"]') && $('[data-copy="hook"]') && $('[data-copy="caption"]') && $('[data-copy="comment"]'), "every text block has a Copy button");
    const voiceOptions = Array.from($("#voice-select").options).map((o) => o.value);
    ok(voiceOptions.length >= 4 && voiceOptions.every((v) => v.startsWith("en-US-")), "voice picker lists en-US neural voices");
    ok(!!$("#btn-voice") && !!$("#voice-text"), "voice generator + text box available");
    click('[data-copy="overlay"]');
    await waitFor(() => clipboard.text === $("#f-overlay").value, "clipboard holds on-screen text");
    ok(clipboard.text === $("#f-overlay").value, "Copy chữ trên video works");
    const overlayEl = $("#f-overlay");
    overlayEl.value = "too short";
    overlayEl.dispatchEvent(new window.Event("input", { bubbles: true }));
    await waitFor(() => $("#overlay-warn").classList.contains("bad"), "overlay warning");
    ok($("#overlay-warn").textContent.includes("9–15"), "editing outside 9–15 words warns");

    console.log("• Tab Kiểm tra");
    click('[data-tab="checks"]');
    await waitFor(() => $$(".check").length >= 5, "checks tab");
    ok($$(".check").length >= 5, "checks tab lists the publishing gates");

    console.log("• No MP4 / video UI anywhere");
    window.location.hash = "#/howto";
    await waitFor(() => crumb().includes("Cách hoạt động"), "howto again");
    const visible = doc.body.textContent;
    ok(!/\.mp4|Tải MP4|Render MP4|Render video/.test(visible), "no render/MP4 download controls left in the UI");
    ok(!/<video|<audio[^>]*poster=/i.test(doc.body.innerHTML), "no video preview element");
    ok(!/ffmpeg|imageio/i.test(visible), "no ffmpeg references in the UI");

    if (pageErrors.length) {
      throw new Error(`page errors: ${pageErrors.join(" | ")}`);
    }
    ok(true, "no uncaught page errors");

    console.log(`\nUI smoke test passed: ${checks} checks, ${apiCalls.total} API calls.`);
  } finally {
    if (dom) dom.window.close();
    server.kill("SIGTERM");
  }
}

main().catch((err) => {
  console.error(`\n${err.stack || err.message}`);
  process.exit(1);
});
