# Implementation Plan: Legends Reel Studio v2 (bài báo · ảnh nghệ sĩ · text & voice)

**Branch**: `arena/19d0d9ca-speckit` | **Date**: 2026-11-04 | **Spec**: [`spec.md`](./spec.md)
**Input**: Đặc tả "trang quản lý – tạo nội dung reels Facebook về huyền thoại âm nhạc cho thị trường Mỹ", phạm vi đã bỏ phần dựng video.

## Summary

Ứng dụng web chạy cục bộ: FastAPI phục vụ REST + SPA tĩnh, SQLite lưu dự án, và ba module nội dung:

- `content.py` — sinh bài báo tiếng Anh **700–900 từ** (bù đoạn cho tới khi vào khoảng), chữ trên video **9–15 từ**, hook, caption, comment pin, bộ kiểm tra trước khi đăng.
- `images.py` — lấy ảnh nghệ sĩ từ **Wikipedia + Wikimedia Commons** kèm license/attribution, tải ảnh từ link người dùng dán (không scrape Pinterest), chuẩn hoá JPEG, xuất `.zip` + `ATTRIBUTION.txt`.
- `voice.py` — TTS ưu tiên **edge-tts** (en-US neural, mp3), fallback **pyttsx3** (offline).

Không còn render MP4, ffmpeg, job render hay preview điện thoại.

## Technical Context

**Language/Version**: Python 3.11+ (backend), ES2020 (SPA, không build step)
**Primary Dependencies**: FastAPI, Uvicorn, Pillow, python-multipart, edge-tts, pyttsx3
**Storage**: SQLite (`data/studio.db`) + file (`data/images/<project>/`, `data/voice/<project>/`)
**Testing**: pytest + httpx (TestClient/TestClient), jsdom cho UI
**Target Platform**: Linux/macOS/Windows, chạy localhost
**Performance Goals**: tạo dự án < 1s; sinh bài báo 800 từ < 50ms; tải 20 ảnh < 30s tuỳ mạng
**Constraints**: offline trừ ảnh + edge-tts; chữ 9–15 từ; bài 700–900 từ; 1 banner + 20 ảnh
**Scale/Scope**: một người vận hành, 27 nghệ sĩ, hàng trăm dự án

## Constitution Check

| Nguyên tắc | Cách đáp ứng |
| --- | --- |
| Spec-first | Spec, plan, tasks trong `docs/`, mỗi FR truy vết được sang code/test |
| Test đi kèm | `tests/` phủ sự kiện, 9–15 từ, 700–900 từ cho cả 27 nghệ sĩ, ảnh (mock HTTP), voice (mock engine), API; `ui_smoke.mjs` phủ UI |
| Đơn giản trước | Không React/Vite, không ORM, không queue — SPA thuần + sqlite3 |
| Dữ liệu có nguồn | Ngày sinh/mất và cột mốc nằm trong `seed_artists.py`; ảnh lưu license/attribution |
| Nội dung có kiểm soát | Template + seed; không sinh khẳng định không kiểm chứng; giới hạn từ kiểm tra hai lớp (UI + API) |

## Project Structure

```text
apps/legend-reel-studio/
├── backend/
│   ├── app.py            # FastAPI: projects, images, voice, export, static
│   ├── db.py             # schema + migration + CRUD + duplicate
│   ├── library.py        # sự kiện theo ngày, tìm kiếm, artist card
│   ├── seed_artists.py   # 27 huyền thoại, 15 cột mốc phát hành
│   ├── content.py        # article 700–900, overlay 9–15, hook/caption/comment, checks
│   ├── images.py         # Wikipedia/Commons + import URL + normalize + attribution
│   └── voice.py          # edge-tts → pyttsx3 (+ ffmpeg tuỳ chọn)
├── web/
│   ├── index.html        # shell: sidebar, topbar, view
│   ├── styles.css        # design tokens + component styles
│   └── app.js            # router 5 màn hình, 4 tab studio, copy, ảnh, voice
├── tests/
│   ├── test_events.py · test_content.py · test_api.py
│   ├── test_images.py · test_voice.py
│   └── ui_smoke.mjs      # jsdom
├── data/                 # sqlite + media (git-ignored)
├── requirements.txt · package.json · run.sh / run.ps1 / run.bat
└── README.md
```

## Phase 0 — Quyết định kỹ thuật

| Vấn đề | Lựa chọn | Lý do |
| --- | --- | --- |
| Bỏ dựng video | Xoá `render.py`, `audio.py`, job render, preview 9:16 | Người dùng tự dựng reel; giảm phụ thuộc ffmpeg/numpy, giảm thời gian cài |
| Độ dài bài báo | Template + "bù đoạn" tới ~800 từ, chặn trần 900 | Luôn vào khoảng 700–900 mà không cần LLM |
| Nguồn ảnh | Wikipedia REST + Commons API, gọi **từ server** | Cần lưu file + license vào dự án; trình duyệt không tải được cross-origin ổn định |
| Ảnh từ nguồn khác | Người dùng dán link ảnh trực tiếp, server tải | Không scrape Pinterest; người dùng kiểm soát bản quyền |
| Chuẩn hoá ảnh | Pillow → JPEG ≤ 2000×3000, q88 | Nhẹ, không méo, tự xử lý EXIF/alpha |
| TTS | edge-tts trước, pyttsx3 sau | Chất lượng neural khi có mạng, vẫn dùng được offline |
| Lưu voice | File trong `data/voice/<pid>/` + metadata trong DB | Nghe lại/tải lại không cần sinh lại |
| Ảnh trong DB | `images_json` (mảng record) + `banner_image` = image id | Không cần bảng phụ, dễ nhân bản |
| Frontend | SPA thuần ES2020, hash router | Không build step; test được bằng jsdom |

## Data model

`projects` (thêm cột `remake_json`: reel gốc + brief khi dự án được tạo từ “Làm lại”)

| Cột | Kiểu | Ý nghĩa |
| --- | --- | --- |
| id | TEXT PK | 12 hex |
| artist_id | TEXT | khoá tới thư viện |
| event_json | TEXT | sự kiện đã chọn |
| status | TEXT | draft/article/script/ready/scheduled/published |
| seed | INTEGER | tái lập nội dung |
| article_title, article_body | TEXT | bài báo 700–900 từ |
| article_titles_json | TEXT | biến thể tiêu đề |
| music_links_json | TEXT | 3 bài hát + link |
| images_json | TEXT | mảng `Image` (xem dưới) |
| banner_image | TEXT | id ảnh đang là banner |
| video_overlay_text | TEXT | chữ trên video (9–15 từ) |
| fb_hook, caption, hashtags, first_comment | TEXT | bài đăng |
| script_json | TEXT | script gốc + `voice_script` gợi ý |
| voice_json | TEXT | `Voice` của dự án |
| notes, scheduled_for, created_at, updated_at | TEXT | |

`Image` (trong `images_json`): `id`, `file`, `source` (wikipedia/wikimedia/user/upload), `title`, `url`, `page_url`, `license`, `license_url`, `attribution`, `description`, `width`, `height`, `bytes`.

`Voice`: `file`, `engine`, `voice`, `ext`, `bytes`, `duration`, `text`, `created_at`.

`custom_events`: id, artist_id, date, kind, title, note, created_at.

`custom_artists` (profile tạo bằng tên): id, name, data_json (aka, genre, era, hometown, birth, death, gender, source_url, songs, facts), created_at, updated_at. `library.get_artist` không thấy id thì `resolve_artist()` rơi xuống bảng này, nên mọi endpoint dự án dùng chung một đường.

`rival_reels` (reel đối thủ): id, url, platform, fmt, artist_name, hook, views, likes, comments, shares, posted_at, **source_page**, score, tier, status (moi/dang-lam/da-lam), remade_project_id, note, created_at, updated_at. Điểm không lưu cứng khi đọc — `with_score()` tính lại theo ngày hôm nay để độ mới luôn đúng.

**Migration**: `init_db()` tạo bảng nếu thiếu, `ALTER TABLE` thêm `images_json`, `script_json`, `voice_json` cho DB cũ, và đổi `status='video'` → `'script'`. Cột cũ (`render_path`, `audio_path`, `video_plan_json`…) bị bỏ qua khi đọc.

## API contract

```text
GET    /api/bootstrap?day=YYYY-MM-DD        → artists, stats, upcoming, limits, voices, engines
GET    /api/events?day=&window=&q=&kinds=
GET    /api/artists, /api/artists/{id}
POST   /api/events/custom
GET    /api/projects?status=&q=
POST   /api/projects                        {artist_id, event, seed?, generate?}
GET    /api/projects/{id}
PATCH  /api/projects/{id}                   {article_title, article_body, caption, status, …}
DELETE /api/projects/{id}
POST   /api/projects/{id}/duplicate
POST   /api/projects/{id}/generate          {section: article|script|all, seed?}
GET    /api/projects/{id}/overlay-options   → tất cả 9–15 từ
POST   /api/projects/{id}/overlay           {text} → {words, ok, range}
GET    /api/projects/{id}/images/suggest    → candidates + license + errors
GET    /api/projects/{id}/images
POST   /api/projects/{id}/images            {url} | {urls} | {images:[candidate]}
POST   /api/projects/{id}/images/upload     multipart
PATCH  /api/projects/{id}/images/{image_id} {is_banner}
DELETE /api/projects/{id}/images/{image_id}
GET    /api/projects/{id}/images/{image_id}/download
GET    /api/projects/{id}/images.zip        → ảnh + ATTRIBUTION.txt
GET    /api/artists/custom                  → profile tạo bằng tên
POST   /api/artists/custom                  {name, aka, genre, era, hometown, birth, death, gender, source_url, songs, facts}
PATCH/DELETE /api/artists/custom/{id}       xoá bị chặn 400 khi còn dự án
POST   /api/projects/custom                 {name, profile?, event?, seed?, generate?} → project
GET    /api/rivals?q=&platform=&fmt=&status=&sort=&min_score=&only_unused=
POST   /api/rivals                          {lines?} | {items?} | {url, ...} → {reels, added, errors}
PATCH/DELETE /api/rivals/{id}
POST   /api/rivals/{id}/remake              {artist_id?|artist_name?, event?, seed?, generate?} → {project, reel}
POST   /api/rivals/from-page                {page_url, posts?|html?|items?, only_viral?, min_score?} → {reels, added, skipped, filtered_out}
GET    /api/rivals/pages                    → [{page, count}]
GET    /api/voices
POST   /api/projects/{id}/voice             {text, voice}
DELETE /api/projects/{id}/voice
GET    /api/projects/{id}/export?fmt=md|json
GET    /media/*, /assets/*                  static
```

## Article generator (700–900 từ)

```text
article_for(artist, event, seed)
 ├─ lede + "Why X still matters" + 3 link nhạc (3 mục)
 ├─ "What the headlines left out" (4 dữ kiện)
 ├─ "Why people are still listening" (2 đoạn bối cảnh)
 ├─ bù đoạn từ _filler_pool(): thêm từng đoạn khi tổng < 800 từ
 │    và bỏ qua đoạn nào làm tổng vượt 892 từ
 └─ closing "Listen tonight" + credit nghệ sĩ
```

`content.article_stats()` trả `{words, min: 700, max: 900, in_range}`; API serialize kèm số từ để UI hiện cảnh báo. Test quét cả 27 nghệ sĩ × 3 seed để đảm bảo luôn trong khoảng.

## Image pipeline

```text
suggest_for_artist(artist)
 ├─ wikipedia_candidates(wiki_title)     REST summary → originalimage + thumbnail
 ├─ commons_candidates(wiki_title, name)  list=search (ns 6) → imageinfo(url,size,mime,extmetadata)
 │    lọc theo mime/kích thước, lấy LicenseShortName, LicenseUrl, Artist (bóc HTML), ImageDescription
 └─ dedupe theo URL → tối đa 24 gợi ý

import_from_url(url, meta) → http_bytes (≤15MB, timeout 15s)
 ├─ chặn localhost/dải nội bộ, link trang web, link pin Pinterest
 ├─ normalize(): Pillow verify → EXIF transpose → RGB/alpha → JPEG ≤2000×3000 q88
 └─ lưu data/images/<pid>/<image_id>.jpg + record license/attribution

GET /images.zip → zipfile gồm ảnh JPEG + ATTRIBUTION.txt
```

## Rivals pipeline

```text
parse_bulk(lines) → items
score_reel(item)  → score 0–100, tier, engagement, reach/engagement/recency points, verdict
brief(fmt)        → hook_pattern, beats[5], pacing, why_it_worked, remake_rules
POST /api/rivals/{id}/remake → artist (library | custom | mới từ tên | không) → event → apply_generation
                             → project["remake"] = {rival_id, url, hook, score, tier, brief, remade_at}
```

Điểm = độ phủ (log10 views, ≤50) + tương tác (ER%, ≤40) + độ mới (≤10). Brief chỉ mô tả **cấu trúc**; bản làm lại sinh chữ mới và dùng ảnh Wikipedia/Commons nên không tái sử dụng tài sản của đối thủ.

## Page import pipeline

```text
web/assets/fb-extract.js  (chạy trong Console của trang Facebook người dùng mở)
  → đọc div[role="article"], lấy hook/url/thời gian + số trong aria-label & text
  → POST /api/rivals/from-page {page_url, posts}   (dự phòng: copy JSON, dán tay)
    hoặc dán HTML đã lưu (Ctrl+S) → posts_from_html()

rivals.from_posts()  → count_from_text (1.2K / 1,2 N / 1.234 / 2,4 Tr), guess_format, hook_from_text
app.import_from_page → chuẩn hoá, bỏ trùng (url hoặc hook+page), chọn bài "đã nổi"
                     → db.create_rival(source_page=…)
```

Máy chủ không gọi Facebook: mọi bytes đến từ trình duyệt của người dùng hoặc do họ dán. Chọn "đã nổi": giữ bài ≥ 60 điểm; nếu cả batch dưới 60 thì giữ top 40% (luôn ≥ 1 bài) để page nhỏ vẫn dùng được.

## Name-based profile pipeline

```text
profiles.normalize(name) → profile tối thiểu (không bịa ngày sinh/năm mất)
profiles.make_event(profile, kind, date) → event có label_vi, years (0 nếu thiếu dữ liệu → câu văn tránh in “0 years”)
profiles.article_for / script_for / hashtags / first_comment / fb_hook / caption
profiles.song_links(profile) → YouTube search URL (không bịa video id)
```

## Voice pipeline

```text
synthesize(text, voice)
 ├─ edge_tts.Communicate(text, voice).save(mp3)  (timeout 45s, asyncio)
 ├─ nếu lỗi/không có mạng → pyttsx3 save_to_file(wav)
 │    └─ nếu shutil.which("ffmpeg") → chuyển libmp3lame → mp3
 └─ trả {file, engine, voice, ext, bytes, duration, text}
```

## UI

Hash router 5 màn hình; sidebar `data-nav` → `#/`, `#/discover`, `#/projects`, `#/howto`, bấm lại mục đang mở thì gọi `route()` để render lại.

Studio 4 tab: **Bài báo** (tiêu đề / nội dung có đếm từ 700–900 / link nhạc, mỗi khối Copy), **Ảnh nghệ sĩ** (lấy tự động, dán link, upload, banner, tải từng ảnh, `.zip`), **Text & Voice** (chữ 9–15 từ, hook, caption, comment pin, voice + `<audio>`), **Kiểm tra** (8 điều kiện + checklist đăng bài).

## Complexity Tracking

Hai điểm đánh đổi có chủ đích:

- **Template thay vì LLM** → giọng văn ít đa dạng hơn, nhưng offline, tất định, không bịa dữ kiện.
- **Gọi Wikipedia/Commons từ server** → cần mạng ở server, nhưng giữ được file + license trong dự án và cho phép tải `.zip`.

## Kết quả kiểm chứng

- `pytest -q` → **49 passed** (sự kiện, 700–900 từ, 9–15 từ, API, ảnh có mock HTTP, voice mock 3 nhánh).
- `node tests/ui_smoke.mjs` → **36 checks**: sidebar 4 màn hình + render lại, 3 tab studio, đếm từ, cảnh báo, Copy, banner, `.zip`, voice picker, không còn UI MP4.
- Bài báo: 453 mẫu (27 nghệ sĩ × 3 seed × mọi sự kiện) đều nằm trong 800–840 từ.
