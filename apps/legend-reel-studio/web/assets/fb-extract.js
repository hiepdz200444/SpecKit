/* Legends Studio — bộ lấy bài từ page Facebook đối thủ (ĐƯỜNG DỰ PHÒNG).
 *
 * Từ v2.4.0, studio tự đọc page ở phía máy chủ: bạn chỉ cần dán link page và
 * bấm "Tìm reels nổi". File này chỉ dùng khi Facebook chặn máy chủ (đòi đăng
 * nhập) và bạn không muốn dán cookie phiên.
 *
 * CÁCH DÙNG (trên máy bạn, trình duyệt đang đăng nhập Facebook):
 *   1. Mở page đối thủ: https://www.facebook.com/<ten-page>
 *   2. Cuộn xuống vài lần để Facebook tải thêm bài (mỗi lần cuộn ~3-5 bài).
 *   3. Mở Console (F12 → Console). Facebook có thể chặn dán mã lần đầu: gõ
 *      "allow pasting" rồi Enter, sau đó dán toàn bộ file này → Enter.
 *   4. Studio tự nhận bài (nếu mở cùng máy); nếu không, JSON đã được copy —
 *      quay lại studio, mục "Facebook chặn hoặc bạn muốn tự dán số liệu",
 *      dán JSON rồi bấm Nhập.
 *
 * Script chỉ ĐỌC trang bạn đang xem (không đăng nhập hộ, không gọi API ẩn,
 * không gửi dữ liệu đi đâu ngoài máy chủ studio của bạn).
 */
(async () => {
  const STUDIO = window.__LRS_STUDIO__ || "http://127.0.0.1:8000";
  const PAGE_URL = location.origin + location.pathname;

  const ARTICLES = 'div[role="article"], [data-ad-preview="message"]';

  const num = (raw) => {
    if (!raw) return 0;
    const m = String(raw).replace(/\s/g, "").match(/^([\d.,]+)(k|m|b|n|tr|triệu|nghìn)?$/i);
    if (!m) return 0;
    let n = parseFloat(m[1].replace(/,(?=\d{3}\b)/g, "").replace(",", "."));
    const unit = (m[2] || "").toLowerCase();
    if (["k", "n", "nghìn"].includes(unit)) n *= 1e3;
    else if (["m", "tr", "triệu"].includes(unit)) n *= 1e6;
    else if (unit === "b") n *= 1e9;
    return Math.round(n || 0);
  };

  const grab = (blob, words) => {
    const re = new RegExp("([\\d][\\d.,]*\\s*(?:k|m|b|n|tr|triệu|nghìn)?)\\s*(?:" + words + ")", "i");
    const m = blob.match(re);
    return m ? num(m[1]) : 0;
  };

  const VIEWS = "views?|lượt xem|plays?|lượt phát";
  const LIKES = "reactions?|likes?|cảm xúc|lượt thích|thích";
  const COMMENTS = "comments?|bình luận|lượt bình luận";
  const SHARES = "shares?|chia sẻ|lượt chia sẻ";

  const nodes = [...document.querySelectorAll(ARTICLES)]
    .filter((el) => el.closest('[role="article"]') === el || el.getAttribute("data-ad-preview"));

  const strip = (raw) => {
    if (!raw) return "";
    try {
      const url = new URL(raw);
      if (!url.searchParams.has("story_fbid") && !url.searchParams.has("id")) url.search = "";
      return url.toString();
    } catch (err) {
      return raw;
    }
  };

  const seen = new Set();
  const posts = [];

  for (const node of nodes) {
    const article = node.closest('[role="article"]') || node;
    const rawText = article.innerText ?? article.textContent ?? "";
    const text = String(rawText).replace(/\u00a0/g, " ").replace(/[ \t]+/g, " ").trim();
    if (text.length < 30) continue;

    const aria = [...article.querySelectorAll("[aria-label]")]
      .map((el) => el.getAttribute("aria-label") || "")
      .join(" ");
    const blob = `${text} ${aria}`;

    const linkEl = article.querySelector(
      'a[href*="/posts/"], a[href*="/videos/"], a[href*="/reel/"], a[href*="story_fbid="], a[href*="permalink.php"]'
    );
    let url = linkEl ? strip(linkEl.href) : "";
    if (!url) {
      const anyLink = article.querySelector('a[href*="facebook.com/"]');
      url = anyLink ? strip(anyLink.href) : "";
    }
    const key = (url || text.slice(0, 120)).toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);

    // thời gian: ưu tiên aria-label của link thời gian ("2 ngày trước")
    const timeEl = article.querySelector('a[aria-label][role="link"], abbr, time');
    const postedAt = timeEl
      ? (timeEl.getAttribute("aria-label") || timeEl.innerText || timeEl.textContent || "").trim()
      : "";

    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
    const hookLine =
      lines.find((l) => l.length >= 20 && !/^\d+([.,]\d+)?\s*(k|m|b)?$/i.test(l)) || lines[0] || "";

    posts.push({
      url,
      text: text.slice(0, 1500),
      hook: hookLine.slice(0, 160),
      views: grab(blob, VIEWS),
      likes: grab(blob, LIKES),
      comments: grab(blob, COMMENTS),
      shares: grab(blob, SHARES),
      posted_at: postedAt,
    });
  }

  if (!posts.length) {
    console.warn(
      "Không thấy bài nào. Hãy cuộn page để Facebook tải bài, đợi một chút rồi chạy lại."
    );
    return;
  }

  const payload = JSON.stringify({ page_url: PAGE_URL, posts });
  let sent = false;
  try {
    // gửi thẳng về studio (cùng máy). Nếu trình duyệt chặn thì bỏ qua.
    await fetch(`${STUDIO}/api/rivals/from-page?only_viral=1`, {
      method: "POST",
      mode: "cors",
      headers: { "content-type": "application/json" },
      body: payload,
    });
    sent = true;
  } catch (err) {
    sent = false;
  }

  try {
    await navigator.clipboard.writeText(payload);
  } catch (err) {
    console.log("Không copy được tự động — JSON ở dưới, copy tay:");
    console.log(payload);
  }

  console.log(
    sent
      ? `✅ Đã gửi ${posts.length} bài về studio (chỉ giữ bài đã nổi). Mở studio → Reels đối thủ.`
      : `📋 Đã copy ${posts.length} bài. Mở studio → Reels đối thủ → "Facebook chặn" → dán JSON.`
  );
  try {
    alert(
      sent
        ? `Studio đã nhận ${posts.length} bài từ page này.\nQuay lại tab studio → Reels đối thủ để xem bài đã nổi.`
        : `Đã copy ${posts.length} bài vào clipboard.\nDán vào studio → Reels đối thủ → ô JSON.`
    );
  } catch (err) {
    /* bỏ qua khi trình duyệt chặn alert */
  }
  return posts;
})();
