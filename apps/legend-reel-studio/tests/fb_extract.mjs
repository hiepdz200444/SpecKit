/* Kiểm tra web/assets/fb-extract.js trên một DOM giả lập kiểu Facebook.
 * Chạy: node tests/fb_extract.mjs
 */
import { readFile } from "node:fs/promises";
import { JSDOM } from "jsdom";

const html = `<!doctype html><html><body>
  <div role="article">
    <div dir="auto">POV: you heard this voice in 1975 and never forgot it.
      Still the greatest to ever pick up a mic.</div>
    <div aria-label="84K reactions">84K</div>
    <div>3.2K comments</div><div>1.1K shares</div><div>2.4M views</div>
    <a href="https://www.facebook.com/OldSchoolMusicPage/posts/900?__cft__=1" role="link" aria-label="2 days ago">2 d</a>
  </div>
  <div role="article">
    <div dir="auto">Top 5 voices that still stop a room, and number one is not who you think.</div>
    <div aria-label="1.2K reactions">1.2K</div>
    <div>84 comments</div><div>12 shares</div>
    <a href="/OldSchoolMusicPage/posts/901" role="link">5 d</a>
  </div>
  <div role="article">
    <div dir="auto">Short</div>
  </div>
</body></html>`;

const dom = new JSDOM(html, {
  url: "https://www.facebook.com/OldSchoolMusicPage",
  runScripts: "outside-only",
  pretendToBeVisual: true,
});

const { window } = dom;
let sent = null;
let copied = "";
window.fetch = async (url, init) => {
  sent = { url, body: JSON.parse(init.body) };
  return { ok: true, json: async () => ({ added: 1 }) };
};
Object.defineProperty(window.navigator, "clipboard", {
  value: { writeText: async (text) => { copied = String(text); } },
  configurable: true,
});

const code = await readFile(new URL("../web/assets/fb-extract.js", import.meta.url), "utf8");
window.eval(code);

for (let i = 0; i < 80 && !(sent && copied); i += 1) {
  await new Promise((resolve) => setTimeout(resolve, 25));
}

let failures = 0;
let checks = 0;
const ok = (cond, label) => {
  checks += 1;
  console.log(`${cond ? "  ✓" : "  ✗"} ${label}`);
  if (!cond) failures += 1;
};

console.log("• fb-extract.js");
ok(!!sent, "script gửi kết quả về studio");
const posts = sent ? sent.body.posts : [];
ok(posts.length === 2, `bóc được 2 bài có nội dung (bỏ bài quá ngắn) — ${posts.length}`);
const [first, second] = posts;
ok(first.url.includes("/posts/900") && !first.url.includes("__cft__"), "giữ link bài gốc, bỏ query tracking");
ok(first.likes === 84000 && first.comments === 3200 && first.shares === 1100, "đọc reactions/comment/share từ aria-label + text");
ok(first.views === 2400000, "đọc views");
ok(/POV: you heard this voice/.test(first.hook), "lấy câu đầu làm hook");
ok(/2 days ago/.test(first.posted_at), "lấy được thời gian đăng");
ok(second.url.startsWith("https://www.facebook.com/OldSchoolMusicPage/posts/901"), "link tương đối được chuyển thành tuyệt đối");
ok(second.likes === 1200 && second.comments === 84, "bài thứ hai đọc đúng số");
ok(sent.url.includes("/api/rivals/from-page"), "gửi tới /api/rivals/from-page");
ok(sent.body.page_url === "https://www.facebook.com/OldSchoolMusicPage", "gửi kèm link page");
ok(JSON.parse(copied).posts.length === 2, "đồng thời copy JSON để dán tay");

if (failures) {
  console.error(`\nfb-extract FAILED: ${failures} check(s)`);
  process.exit(1);
}
console.log("\nfb-extract OK: " + checks + " checks");
