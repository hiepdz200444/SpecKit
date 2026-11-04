# Tasks: Legends Reel Studio

**Input**: `docs/spec.md` · **Plan**: `plan.md`
**Path conventions**: backend `apps/legend-reel-studio/backend/`, frontend `apps/legend-reel-studio/web/`, tests `apps/legend-reel-studio/tests/`

## Phase 1: Setup

- [x] T001 Tạo khung dự án `apps/legend-reel-studio/` + `requirements.txt` + `run.sh`
- [x] T002 Tải font OFL (Anton, Barlow, DM Serif Display) vào `web/assets/fonts`
- [x] T003 Tạo 3 ảnh nền dự phòng 1080×1920 (sân khấu, vinyl, khán giả) trong `web/assets`
- [x] T004 Cấu hình ffmpeg qua `imageio-ffmpeg` (libx264 + AAC), kiểm tra bằng `ffmpeg -encoders`
- [x] T005 `.gitignore` cho `data/`, `__pycache__`, `.venv`
- [x] T005b Launcher Windows `run.ps1` + `run.bat` (tự tạo venv, cài deps, mở server)

## Phase 2: Foundational

- [x] T006 `seed_artists.py`: 27 nghệ sĩ đã mất (ngày sinh/mất, quê quán, 3 bài hát + link, dữ kiện) và 15 cột mốc phát hành
- [x] T007 `library.py`: tính sự kiện sinh nhật/ngày mất/phát hành theo khoảng ±N ngày, xử lý 29/02, sắp xếp ưu tiên đúng ngày
- [x] T008 `library.search_events()`: tìm theo nghệ sĩ/biệt danh/thể loại/quê quán/tên bài hát, lọc theo loại
- [x] T009 `db.py`: schema `projects` + `custom_events`, CRUD, duplicate (reset media), thống kê
- [x] T010 `content.word_count()` + `_cap()` + bộ template dùng chung
- [x] T011 API khung: `/api/bootstrap`, `/api/events`, `/api/artists`, static mount

## Phase 3: User Story 1 — Khám phá sự kiện (P1) 🎯 MVP

- [x] T012 Sinh nhãn tiếng Việt + tiếng Anh cho từng loại sự kiện (`event_copy`)
- [x] T013 Trả về 3 bài nhạc + link YouTube/Spotify trong mỗi sự kiện
- [x] T014 Màn hình Khám phá: tìm kiếm debounce, chọn ngày, khoảng ±, chip loại sự kiện
- [x] T015 Event card: ảnh, badge loại, nhãn "hôm nay/còn N ngày", chip bài hát bấm nghe được, nút tạo reels
- [x] T016 Empty state + gợi ý mở rộng ±30 ngày
- [x] T017 Dashboard: thống kê, sự kiện quanh hôm nay, dự án gần đây

## Phase 4: User Story 2 — Bài báo (P1)

- [x] T018 `content.article_for()`: tiêu đề + 3 biến thể, dek, body ~500 từ, link nhạc, hashtag, comment pin
- [x] T019 API tạo dự án tự sinh bài + kịch bản, seed tái lập được
- [x] T020 Tab Bài báo: sửa tiêu đề/dek/body/comment, autosave, đổi biến thể tiêu đề
- [x] T021 Upload banner + lấy ảnh Wikipedia (client fetch → multipart)
- [x] T022 Xem trước bài báo kiểu báo giấy + đếm từ/ký tự
- [x] T023 Xuất `.md` / `.json` gói bài đăng

## Phase 5: User Story 3 — Video MP4 (P2)

- [x] T024 `content.video_for()`: 5 cảnh + hook + chữ trên video 9–15 từ
- [x] T025 Lọc/gợi ý overlay theo luật 9–15 từ; API `overlay-options`, `overlay`
- [x] T026 `render.py`: cover-crop, grade 3 phong cách, vignette/scanline, Ken Burns
- [x] T027 Typography từng cảnh (hook, số, bài hát, tò mò, CTA comment) + HUD (badge, progress, waveform)
- [x] T028 Pipe raw frame → ffmpeg H.264/AAC, `+faststart`, poster JPG
- [x] T029 Job render + polling tiến độ, khoá render song song, xử lý lỗi
- [x] T030 `audio.py`: nhạc nền tổng hợp; upload nhạc; chọn bed/upload/none; fade in/out
- [x] T031 Preview điện thoại 9:16 chạy 5 cảnh + timeline

## Phase 6: User Story 4 — Hook & comment (P2)

- [x] T032 `_fb_hook()`, `_caption()`, hashtag, comment pin
- [x] T033 Tab Hook & Comment: sửa, đếm ký tự, copy, xem trước kiểu Facebook
- [x] T034 Checklist 5 điều kiện (`engagement_checks`) + tab Kiểm tra + hướng dẫn đăng reels

## Phase 7: User Story 5 — Quản lý dự án (P3)

- [x] T035 Trang Dự án: lọc theo trạng thái, tìm kiếm, số lượng
- [x] T036 Đổi trạng thái, nhân bản, xoá (kèm dọn media), tải MP4
- [x] T037 Route hash 5 màn hình + sidebar + breadcrumb + toast/modal

## Phase 8: Polish & Cross-Cutting

- [x] T038 Rà lại copy tiếng Anh: bỏ khẳng định không kiểm chứng, sửa lỗi ghép câu sự kiện phát hành
- [x] T039 Thiết kế lại cảnh CTA (bong bóng comment + mũi tên + tag) và vị trí an toàn
- [x] T040 Viết `README.md`, `spec.md`, `plan.md`, `tasks.md`
- [x] T041 `tests/`: sự kiện, 9–15 từ, sinh nội dung, CRUD API, render ngắn
- [x] T042 Smoke test UI bằng jsdom (5 màn hình, tạo dự án qua UI, không lỗi runtime)
- [x] T043 Kiểm tra video thực tế: 1080×1920, 30fps, 24s, AAC, frame đúng layout

## Backlog (chưa làm)

- [ ] T044 Đăng trực tiếp qua Facebook Graph API (cần quyền Page)
- [ ] T045 Voiceover TTS + phụ đề tự động theo giọng đọc
- [ ] T046 Lên lịch đăng nhiều ngày + hàng đợi render song song
- [ ] T047 Import thêm nghệ sĩ từ MusicBrainz/Wikipedia (có kiểm duyệt)
- [ ] T048 A/B test tiêu đề/hook và theo dõi hiệu suất reel sau khi đăng
