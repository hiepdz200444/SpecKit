"""Competitor reel tracking: import, score, filter and turn into a remake brief.

The studio never scrapes Facebook / Instagram / TikTok. The operator pastes the
numbers they can see (views, likes, comments, shares) and the studio ranks the
reels, explains why each one worked, and turns the winner into a remake brief
that feeds a new project.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Any

PLATFORMS = ["facebook", "instagram", "tiktok", "youtube"]
PLATFORM_LABEL = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "youtube": "YouTube Shorts",
}

FORMATS = ["story", "pov", "list", "quote", "countdown", "tribute"]
FORMAT_LABEL = {
    "story": "Kể chuyện (story)",
    "pov": "Góc nhìn POV",
    "list": "Danh sách (top 3/5)",
    "quote": "Câu nói / trích dẫn",
    "countdown": "Đếm ngược",
    "tribute": "Tưởng nhớ (tribute)",
}

HOST_PLATFORM = (
    ("tiktok", "tiktok"),
    ("instagram", "instagram"),
    ("facebook", "facebook"),
    ("fb.watch", "facebook"),
    ("youtube", "youtube"),
    ("youtu.be", "youtube"),
)

FORMAT_BRIEF: dict[str, dict[str, Any]] = {
    "story": {
        "hook_pattern": "Một câu mở đầu gây tò mò về phần bị bỏ lỡ, không phải về bài hát.",
        "beats": [
            "0–3s: câu móc (một chi tiết ít người biết) + ảnh nghệ sĩ",
            "3–12s: bối cảnh — thời điểm, bối cảnh ra đời của bản thu",
            "12–25s: bước ngoặt / chi tiết bị lãng quên",
            "25–40s: đoạn cao trào của bài hát + chữ trên hình",
            "40–55s: vì sao nó vẫn còn tác dụng tối nay + CTA comment",
        ],
        "pacing": "Cắt cảnh mỗi 3–4 giây, giữ nhạc dưới giọng đọc 12–15 dB.",
    },
    "pov": {
        "hook_pattern": "Đặt người xem vào một ký ức: “Bạn đang ở trong xe, đài phát bài này…”.",
        "beats": [
            "0–3s: câu POV ở ngôi thứ hai",
            "3–15s: chi tiết giác quan (mùi xe, tiếng radio, ánh đèn)",
            "15–30s: cắt sang câu chuyện thật của nghệ sĩ",
            "30–45s: cao trào bài hát",
            "45–55s: câu hỏi cho người xem + CTA",
        ],
        "pacing": "Một cảnh dài duy nhất hoặc 2–3 cảnh chậm, chữ ít, để cảm xúc dẫn.",
    },
    "list": {
        "hook_pattern": "“3 bản thu mà ai cũng quên, nhưng đây là lý do chúng quan trọng”.",
        "beats": [
            "0–3s: hứa hẹn danh sách (nêu số lượng)",
            "3–12s: mục 1 + một dòng lý do",
            "12–22s: mục 2 + chi tiết bất ngờ",
            "22–35s: mục 3 (mục mạnh nhất, để cuối)",
            "35–50s: tổng kết + CTA lưu bài",
        ],
        "pacing": "Mỗi mục một cảnh, chữ to ở giữa khung, đổi cảnh đúng nhịp nhạc.",
    },
    "quote": {
        "hook_pattern": "Một câu nói của nghệ sĩ đặt trên nền ảnh tĩnh, chữ xuất hiện dần.",
        "beats": [
            "0–3s: câu nói (9–15 từ) hiện từng cụm",
            "3–15s: bối cảnh của câu nói",
            "15–30s: bản thu tương ứng",
            "30–45s: ý nghĩa với khán giả hôm nay",
            "45–55s: CTA comment",
        ],
        "pacing": "Chuyển động chậm, zoom nhẹ 3–5%, tránh hiệu ứng mạnh.",
    },
    "countdown": {
        "hook_pattern": "“Chờ đến mục số 1” — tạo lý do xem hết.",
        "beats": [
            "0–3s: nêu chủ đề đếm ngược",
            "3–30s: các mục 3 → 2, mỗi mục 8–10s",
            "30–45s: mục 1 (bản thu mạnh nhất)",
            "45–55s: CTA lưu + comment",
        ],
        "pacing": "Số đếm lớn trên khung, cắt cảnh theo từng mục.",
    },
    "tribute": {
        "hook_pattern": "Một mốc thời gian + lời nhắc rằng giọng hát vẫn còn.",
        "beats": [
            "0–3s: mốc thời gian / ngày tưởng nhớ",
            "3–20s: dấu mốc sự nghiệp, ảnh tư liệu",
            "20–40s: bản thu tưởng nhớ, chữ 9–15 từ",
            "40–55s: lời mời chơi lại bài hát tối nay",
        ],
        "pacing": "Tông màu trầm, chữ ít, nhạc gốc dẫn dắt.",
    },
}

TIER_LABEL = (
    (80, "đột phá"),
    (65, "nổi bật"),
    (50, "khá"),
    (35, "trung bình"),
    (0, "yếu"),
)


# --------------------------------------------------------------------------- #
# numbers                                                                    #
# --------------------------------------------------------------------------- #
_NUM_RE = re.compile(r"(\d[\d.,]*)\s*(nghìn|triệu|tr|k|m)?")


def parse_number(value: Any) -> int:
    """'1.2M', '12k', '1,234', '2.1 nghìn' → int."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    text = str(value or "").strip().lower()
    match = _NUM_RE.search(text)
    if not match:
        return 0
    raw, suffix = match.group(1), match.group(2) or ""
    if suffix:
        try:
            number = float(raw.replace(",", ""))
        except ValueError:
            return 0
        multiplier = 1_000 if suffix in ("k", "nghìn") else 1_000_000
        return max(0, int(round(number * multiplier)))
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else 0


def platform_from_url(url: str) -> str:
    lowered = (url or "").lower()
    for needle, platform in HOST_PLATFORM:
        if needle in lowered:
            return platform
    return "facebook"


# --------------------------------------------------------------------------- #
# scoring                                                                    #
# --------------------------------------------------------------------------- #
def _age_days(posted_at: str) -> int | None:
    if not posted_at:
        return None
    try:
        posted = date.fromisoformat(posted_at[:10])
    except ValueError:
        return None
    return max(0, (date.today() - posted).days)


def score_reel(reel: dict) -> dict:
    """0-100 virality score + the numbers that explain it."""
    views = max(0, int(reel.get("views") or 0))
    likes = max(0, int(reel.get("likes") or 0))
    comments = max(0, int(reel.get("comments") or 0))
    shares = max(0, int(reel.get("shares") or 0))

    weighted = likes + 2 * comments + 3 * shares
    engagement = round(weighted / views * 100, 2) if views else 0.0
    reach = min(50.0, 8 * math.log10(views)) if views else 0.0
    engagement_points = min(40.0, engagement * 3)
    days = _age_days(reel.get("posted_at", ""))
    recency = 10.0 if days is None or days <= 30 else 7.0 if days <= 90 else 3.0 if days <= 365 else 0.0
    total = round(min(100.0, reach + engagement_points + recency))
    tier = next(label for threshold, label in TIER_LABEL if total >= threshold)

    verdict = []
    if views and likes / views >= 0.08:
        verdict.append("tỉ lệ like/views rất cao")
    if views and comments / views >= 0.004:
        verdict.append("nhiều comment — chủ đề gây tranh luận")
    if views and shares / views >= 0.001:
        verdict.append("được chia sẻ nhiều — nội dung chạm cảm xúc")
    if views >= 1_000_000:
        verdict.append("đã vượt ngưỡng triệu views")
    if not verdict:
        verdict.append("chưa có tín hiệu nổi bật, theo dõi thêm")

    return {
        "score": total,
        "tier": tier,
        "engagement": engagement,
        "reach_points": round(reach, 1),
        "engagement_points": round(engagement_points, 1),
        "recency_points": recency,
        "age_days": days,
        "verdict": "; ".join(verdict),
    }


def with_score(reel: dict) -> dict:
    out = dict(reel)
    out.update(score_reel(reel))
    out["platform_label"] = PLATFORM_LABEL.get(out.get("platform", ""), out.get("platform", ""))
    out["format_label"] = FORMAT_LABEL.get(out.get("format", ""), out.get("format", ""))
    out["brief"] = brief(out)
    return out


def brief(reel: dict) -> dict:
    fmt = reel.get("format") or "story"
    data = FORMAT_BRIEF.get(fmt, FORMAT_BRIEF["story"])
    stats = score_reel(reel)
    return {
        "format": fmt,
        "format_label": FORMAT_LABEL.get(fmt, fmt),
        "hook_pattern": data["hook_pattern"],
        "beats": data["beats"],
        "pacing": data["pacing"],
        "why_it_worked": stats["verdict"],
        "remake_rules": [
            "Viết lại toàn bộ lời bằng tiếng Anh của studio — không copy câu chữ của reel gốc.",
            "Dùng ảnh có giấy phép từ tab Ảnh nghệ sĩ, không tải lại ảnh của reel gốc.",
            "Giữ nhịp và cấu trúc, đổi nghệ sĩ/bản thu nếu cần để không trùng nội dung.",
            "Kết thúc bằng CTA comment như reel gốc — đó là phần tạo comment.",
        ],
    }


# --------------------------------------------------------------------------- #
# import                                                                     #
# --------------------------------------------------------------------------- #
BULK_HELP = (
    "Mỗi dòng: url | nền tảng | views | likes | comments | shares | nghệ sĩ | hook | format\n"
    "Ví dụ: https://tiktok.com/@x/video/1 | tiktok | 1.2M | 84k | 2.1k | 900 | Whitney Houston | "
    "The note nobody talks about | story"
)


def parse_line(line: str) -> dict | None:
    text = (line or "").strip()
    if not text or text.startswith("#"):
        return None
    parts = [p.strip() for p in re.split(r"[|\t;]", text)]
    parts = [p for p in parts if p != ""] if len(parts) > 1 else parts
    if not parts:
        return None

    url = parts[0] if parts[0].lower().startswith("http") else ""
    rest = parts[1:] if url else parts
    platform = platform_from_url(url) if url else "facebook"
    numbers: list[int] = []
    fields: list[str] = []
    for token in rest:
        if re.fullmatch(r"[\d.,]+\s*(k|m|tr|triệu|nghìn)?", token.strip().lower()):
            numbers.append(parse_number(token))
        elif token.lower() in PLATFORMS:
            platform = token.lower()
        elif token.lower() in FORMATS:
            fields.append(f"__format__:{token.lower()}")
        else:
            fields.append(token)

    views = numbers[0] if len(numbers) > 0 else 0
    likes = numbers[1] if len(numbers) > 1 else 0
    comments = numbers[2] if len(numbers) > 2 else 0
    shares = numbers[3] if len(numbers) > 3 else 0

    fmt = next((f.split(":", 1)[1] for f in fields if f.startswith("__format__:")), "")
    texts = [f for f in fields if not f.startswith("__format__:")]
    artist_name = texts[0] if texts else ""
    hook = texts[1] if len(texts) > 1 else ""

    if not url and not artist_name and not hook:
        return None
    return {
        "url": url,
        "platform": platform,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "artist_name": artist_name,
        "hook": hook,
        "format": fmt or "story",
        "posted_at": "",
        "notes": "",
    }


def parse_bulk(text: str) -> list[dict]:
    out = []
    for line in (text or "").splitlines():
        item = parse_line(line)
        if item:
            out.append(item)
    return out
