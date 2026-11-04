# Implementation Plan: Legends Reel Studio

**Branch**: `arena/98aa16d2-speckit` | **Date**: 2026-11-04 | **Spec**: [`spec.md`](./spec.md)
**Input**: Đặc tả "trang quản lý – tạo reels Facebook về huyền thoại âm nhạc cho thị trường Mỹ"

## Summary

Một ứng dụng web chạy cục bộ gồm: FastAPI phục vụ REST + SPA tĩnh, SQLite lưu dự án, và một pipeline render MP4 dựng khung hình bằng Pillow rồi pipe raw frame vào ffmpeg. Nội dung (bài báo, chữ trên video 9–15 từ, hook, caption, comment pin) sinh bằng template có kiểm chứng dữ liệu, không gọi LLM, nên chạy offline và miễn phí.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, Uvicorn, Pillow, NumPy, imageio-ffmpeg (ffmpeg tĩnh có libx264 + AAC), python-multipart
**Storage**: SQLite (`data/studio.db`) + file (`data/banners`, `data/audio`, `data/renders`)
**Testing**: pytest + httpx (TestClient)
**Target Platform**: Linux/macOS/Windows, chạy localhost hoặc container; preview qua HTTP
**Project Type**: Web app (backend API + SPA thuần JS, không build step)
**Performance Goals**: tạo dự án < 1s; render 720 frame 1080×1920 < 90s; API p95 < 200ms
**Constraints**: offline (không gọi dịch vụ ngoài ở server), 1 render/lần, video dọc 9:16, chữ 9–15 từ
**Scale/Scope**: một người vận hành, thư viện 27 nghệ sĩ, hàng trăm dự án

## Constitution Check

| Nguyên tắc | Cách đáp ứng |
| --- | --- |
| Spec-first | Spec, plan, tasks nằm trong `apps/legend-reel-studio/docs/`, mỗi yêu cầu FR-001…FR-014 truy vết được sang code |
| Test đi kèm | `tests/` kiểm tra logic sự kiện, ràng buộc 9–15 từ, sinh nội dung, CRUD API, render |
| Đơn giản trước | Không React/Vite, không build step, không ORM — SPA thuần + sqlite3 |
| Dữ liệu có nguồn | Ngày sinh/mất và cột mốc là dữ kiện lịch sử, nằm gọn trong `seed_artists.py` |
| Nội dung có kiểm soát | Template nhiều biến thể + seed; không sinh khẳng định không kiểm chứng được; giới hạn từ kiểm tra hai lớp (UI + API) |

## Project Structure

### Documentation (this feature)

```
apps/legend-reel-studio/docs/
├── spec.md      # đặc tả người dùng + FR + tiêu chí đo được
├── plan.md      # kế hoạch kỹ thuật (file này)
└── tasks.md     # danh sách công việc theo giai đoạn
```

### Source Code

```
apps/legend-reel-studio/
├── backend/
│   ├── app.py            # FastAPI: endpoints, upload, job render, static
│   ├── db.py             # schema projects/custom_events + CRUD + duplicate
│   ├── library.py        # tính sự kiện theo ngày, tìm kiếm, artist card
│   ├── seed_artists.py   # 27 huyền thoại, 15 cột mốc phát hành
│   ├── content.py        # article / overlay / hook / caption / checks
│   ├── render.py         # Renderer: grade, ken burns, typography, ffmpeg
│   └── audio.py          # nhạc nền tổng hợp (pad, sub, kick, shaker, delay)
├── web/
│   ├── index.html        # shell: sidebar, topbar, view
│   ├── styles.css        # design tokens + component styles
│   ├── app.js            # router, 5 màn hình, preview, render polling
│   └── assets/           # font OFL (Anton, Barlow, DM Serif), ảnh nền
├── data/                 # sqlite + media (git-ignored)
├── tests/
├── requirements.txt
├── run.sh
└── README.md
```

## Phase 0 — Research & quyết định

| Vấn đề | Lựa chọn | Lý do |
| --- | --- | --- |
| Sinh MP4 ở đâu? | Server, Pillow → raw frame → ffmpeg | Kiểm soát chất lượng 1080×1920, H.264 thật, không phụ thuộc codec của trình duyệt (MediaRecorder thường chỉ ra webm) |
| Lấy ffmpeg thế nào? | `imageio-ffmpeg` (wheel có binary) | Không cần apt/root; binary có libx264 + AAC |
| Font | Anton + DM Serif Display + Barlow (OFL) | Anton cho hook dọc, serif cho tên bài hát, Barlow cho UI/UI nhỏ |
| Sinh nội dung | Template + seed cố định | Offline, miễn phí, không bịa số liệu; người dùng biên tập lại |
| Link nhạc | Link tìm kiếm YouTube/Spotify | Không chết link khi upload gốc bị gỡ |
| Lưu trữ | SQLite + file | Một người dùng, không cần server DB |
| Frontend | SPA thuần ES2020 | Không build step, tải tức thì, dễ đọc/sửa |
| Ảnh nghệ sĩ | Upload + Wikipedia REST (từ trình duyệt) | Tránh server phải gọi mạng; người dùng kiểm soát bản quyền |

## Phase 1 — Thiết kế

### Data model

`projects`

| Cột | Kiểu | Ý nghĩa |
| --- | --- | --- |
| id | TEXT PK | 12 hex |
| artist_id | TEXT | khoá tới thư viện |
| event_json | TEXT | sự kiện đã chọn (kind, date, years/age, label) |
| status | TEXT | draft/article/video/ready/scheduled/published |
| seed | INTEGER | tái lập nội dung |
| article_title, article_dek, article_body | TEXT | bài báo |
| article_titles_json | TEXT | biến thể tiêu đề |
| first_comment, hashtags | TEXT | comment pin + hashtag |
| banner_image | TEXT | đường dẫn tuyệt đối trong `data/banners` |
| music_links_json | TEXT | 3 bài hát + link |
| video_overlay_text, video_plan_json | TEXT | chữ trên video + 5 cảnh |
| fb_hook, caption | TEXT | bài đăng |
| video_style, audio_choice, audio_path | TEXT | noir/vhs/gold; bed/upload/none |
| render_path, render_status, render_seconds | TEXT/REAL | kết quả render |
| created_at, updated_at | TEXT | ISO UTC |

`custom_events`: id, artist_id, date, kind, title, note, created_at.

### API contract

```
GET    /api/bootstrap?day=YYYY-MM-DD
GET    /api/events?day=&window=&q=&kinds=birthday,memorial,release
GET    /api/artists/{id}
POST   /api/projects                      {artist_id, event, seed?, generate?}
GET    /api/projects?status=&q=
GET    /api/projects/{id}                 → project + artist + checks + urls
PATCH  /api/projects/{id}                 {article_title, caption, video_style, status, …}
DELETE /api/projects/{id}
POST   /api/projects/{id}/duplicate
POST   /api/projects/{id}/generate        {section: article|video|all, seed?}
GET    /api/projects/{id}/overlay-options → 6 gợi ý, tất cả 9–15 từ
POST   /api/projects/{id}/overlay         {text} → {words, ok}
POST   /api/projects/{id}/banner          multipart file | {data_url}
POST   /api/projects/{id}/audio           multipart file
POST   /api/projects/{id}/audio-choice    {choice: bed|upload|none}
POST   /api/projects/{id}/render          → {job}
GET    /api/jobs/{job_id}                 → {status, progress, message, url}
GET    /api/projects/{id}/export?fmt=md|json
GET    /media/*, /assets/*                static
```

### Render pipeline

```
Renderer(project, artist, style)
 ├─ source = cover(ảnh banner | ảnh nền) → grade(style)
 ├─ overlay tĩnh mỗi cảnh: hook / số / bài hát / tò mò / CTA (alpha + vị trí)
 ├─ HUD mỗi frame: badge, progress bar, tên nghệ sĩ, waveform động
 └─ for frame in 0..720:
       crop(ken burns) → vignette → text fade/slide → HUD → stdin ffmpeg
    ffmpeg: libx264 veryfast crf20 + aac 192k + faststart
```

Giới hạn từ: `content.word_count()` dùng chung cho UI (đếm ký tự client) và API; `overlay_candidates()` lọc 9–15 từ trước khi trả về.

## Complexity Tracking

Không có vi phạm constitution. Hai điểm đánh đổi có chủ đích:

- **Render bằng CPU (Pillow) thay vì GPU/compositor** → chậm hơn (~45s/reel) nhưng không cần GPU, ít phụ thuộc.
- **Template thay vì LLM** → giọng văn ít đa dạng hơn, nhưng offline, tất định, không bịa dữ kiện.

## Kết quả kiểm chứng

- `pytest -q` → 14 test (sự kiện, 9–15 từ, sinh nội dung, API, render ngắn).
- Render thực tế: 24s / 720 frame / 1080×1920 / H.264 High / AAC 192k / ~4 MB / ~42s.
- UI smoke test bằng jsdom: 5 màn hình render không lỗi runtime.
