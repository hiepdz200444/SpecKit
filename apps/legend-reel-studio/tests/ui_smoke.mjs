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

  const assetBytes = new Uint8Array(await (await nodeFetch(`${base}/assets/bg-stage.jpg`)).arrayBuffer());
  const CANNED = [
    { title: "File:Elvis Presley 1970.jpg", url: "https://upload.wikimedia.org/canned/elvis-1970.jpg", width: 1200, height: 1500, license: "Public domain", artist: "Metro-Goldwyn-Mayer" },
    { title: "File:Elvis Presley 1956.jpg", url: "https://upload.wikimedia.org/canned/elvis-1956.jpg", width: 1000, height: 1250, license: "CC BY-SA 4.0", artist: "Unknown photographer" },
    { title: "File:Elvis Presley performing.jpg", url: "https://upload.wikimedia.org/canned/elvis-live.jpg", width: 1600, height: 900, license: "Public domain", artist: "RCA Records" },
    { title: "File:Elvis Presley 1973.jpg", url: "https://upload.wikimedia.org/canned/elvis-1973.jpg", width: 1400, height: 1400, license: "CC BY 2.0", artist: "Fan collection" },
  ];
  const jsonRes = (obj) => new Response(JSON.stringify(obj), { status: 200, headers: { "content-type": "application/json" } });
  const jpegRes = () => new Response(assetBytes, { status: 200, headers: { "content-type": "image/jpeg" } });

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
          const raw = String(input);
          if (raw.includes("commons.wikimedia.org/w/api.php")) {
            apiCalls.wiki = (apiCalls.wiki || 0) + 1;
            const params = new URL(raw).searchParams;
            if (params.get("list") === "search") {
              return Promise.resolve(jsonRes({ query: { search: CANNED.map((c) => ({ title: c.title })) } }));
            }
            const pages = {};
            CANNED.forEach((c, i) => {
              pages[String(i + 1)] = {
                title: c.title,
                imageinfo: [{
                  url: c.url, thumburl: c.url, width: c.width, height: c.height, mime: "image/jpeg",
                  extmetadata: {
                    LicenseShortName: { value: c.license },
                    Artist: { value: c.artist },
                    LicenseUrl: { value: "https://creativecommons.org/publicdomain/mark/1.0/" },
                    ImageDescription: { value: "Ảnh thử nghiệm cho kiểm thử UI" },
                  },
                }],
              };
            });
            return Promise.resolve(jsonRes({ query: { pages } }));
          }
          if (raw.includes("en.wikipedia.org/api/rest_v1/page/summary/")) {
            apiCalls.wiki = (apiCalls.wiki || 0) + 1;
            return Promise.resolve(jsonRes({
              title: "Elvis Presley",
              description: "American singer",
              originalimage: { source: "https://upload.wikimedia.org/canned/elvis-lead.jpg", width: 1200, height: 1500 },
              thumbnail: { source: "https://upload.wikimedia.org/canned/elvis-lead.jpg" },
            }));
          }
          if (raw.startsWith("https://upload.wikimedia.org/")) {
            apiCalls.images = (apiCalls.images || 0) + 1;
            return Promise.resolve(jpegRes());
          }
          const url = raw.startsWith("http") ? raw : new URL(raw, base).toString();
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
    const bundleHref = ($("#btn-bundle") || {}).getAttribute ? $("#btn-bundle").getAttribute("href") : "";
    ok((bundleHref || "").endsWith("bundle.zip"), "nút “Tải về máy” trỏ tới gói tải đầy đủ");

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

    console.log("• Tự động lấy ảnh (máy chủ không có Internet → trình duyệt tải hộ)");
    const beforeAuto = $$(".img-card").length;
    click("#btn-auto");
    await waitFor(() => $$(".img-card").length > beforeAuto, "auto-fetch adds photos", 40000);
    const afterAuto = $$(".img-card").length;
    ok(afterAuto > beforeAuto, `“Tự động lấy ảnh” thêm ${afterAuto - beforeAuto} ảnh dù máy chủ bị chặn mạng`);
    ok(apiCalls.images >= afterAuto - beforeAuto, `trình duyệt đã tải ${apiCalls.images} file ảnh thật`);
    ok($("#btn-zip").classList.contains("is-hot"), "nút “Tải tất cả (.zip)” được làm nổi bật sau khi lấy ảnh");
    const licLines = $$(".img-card .img-lic").map((el) => el.textContent.trim());
    ok(licLines.length === afterAuto && licLines.some((t) => /CC BY|Public domain/.test(t)), "ảnh tự lấy vẫn giữ dòng giấy phép");
    const attrLines = $$(".img-card .img-attr").map((el) => el.textContent.trim()).filter(Boolean);
    ok(attrLines.length >= 1, "ảnh tự lấy vẫn giữ tác giả / nguồn");

    const dl = $$(".img-card a[download]").map((a) => a.getAttribute("href")).find((h) => /\/download$/.test(h || ""));
    const dlRes = await nodeFetch(`${base}${dl}`);
    const dlBuf = new Uint8Array(await dlRes.arrayBuffer());
    ok(dlRes.ok && dlBuf[0] === 0xff && dlBuf[1] === 0xd8 && dlBuf.length > 1000, "bấm “Tải về” trả về file JPEG thật");

    const zipRes = await nodeFetch(`${base}/api/projects/${project.id}/images.zip`);
    const zipBuf = Buffer.from(await zipRes.arrayBuffer());
    ok(zipRes.ok && /zip/.test(zipRes.headers.get("content-type") || ""), "images.zip trả về file nén");
    ok(zipBuf.includes(Buffer.from("ATTRIBUTION.txt")), "zip có kèm ATTRIBUTION.txt");
    ok(($("#btn-zip").getAttribute("href") || "").endsWith("images.zip"), "nút “Tải tất cả (.zip)” trỏ đúng file nén");

    console.log("• Chọn thủ công");
    click('[data-tab="article"]');
    await waitFor(() => $(".tabs"), "tabs");
    click('[data-tab="images"]');
    await waitFor(() => $("[data-cand], #btn-suggest"), "images tab again");
    click("#btn-suggest");
    await waitFor(() => $$("#suggest-panel [data-cand]").length > 0, "suggestion candidates render", 40000);
    ok($$("#suggest-panel [data-cand]").length >= 3, "panel “Chọn thủ công” liệt kê ảnh gợi ý");
    ok(/trình duyệt tải hộ/.test($("#suggest-panel").textContent), "panel ghi rõ đang tải bằng trình duyệt");

    console.log("• Kiểm tra mạng trình duyệt");
    click("#btn-diag");
    await waitFor(() => /Trình duyệt:/.test($("#img-status").textContent), "network self-test output", 20000);
    ok(/Wikipedia API: OK/.test($("#img-status").textContent), "self-test báo được trạng thái Wikipedia từ trình duyệt");
    const logs = await nodeFetch(`${base}/api/client-log?limit=10`).then((r) => r.json());
    ok((logs.entries || []).some((e) => e.event === "network-test"), "kết quả kiểm tra được gửi về máy chủ để chẩn đoán");

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
