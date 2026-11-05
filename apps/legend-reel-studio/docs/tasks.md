# Tasks: Legends Reel Studio v2

**Input**: `docs/spec.md` · **Plan**: `plan.md`
**Path conventions**: backend `apps/legend-reel-studio/backend/`, frontend `apps/legend-reel-studio/web/`, tests `apps/legend-reel-studio/tests/`

## Phase 1: Sửa lỗi & đổi scope

- [x] T000 Sidebar `data-nav` không có handler → chỉ mở được Tổng quan
- [x] T001 Bỏ tab "Video & MP4", preview điện thoại 9:16, timeline, nút render/tải MP4
- [x] T002 Xoá `backend/render.py`, `backend/audio.py`, `tests/test_render.py`
- [x] T003 Bỏ `imageio-ffmpeg`, `numpy` khỏi `requirements.txt` và khỏi launcher
- [x] T004 Bỏ endpoint `/render`, `/api/jobs/{id}`, `/banner`, `/audio`, `/audio-choice`; bỏ job lock + thread render
- [x] T005 Migration DB: `status='video'` → `'script'`, thêm `images_json`, `script_json`, `voice_json`

## Phase 2: Bài báo 700–900 từ

- [x] T006 `content.article_for()` sinh bài luôn nằm trong 700–900 từ (bù đoạn + chặn trần)
- [x] T007 `content.article_stats()` + `article_words`/`article_in_range`/`article_range` trong API
- [x] T008 Tab Bài báo: tiêu đề (+3 biến thể), nội dung có đếm từ & cảnh báo ngoài khoảng, 3 link nhạc
- [x] T009 Nút Copy cho từng khối (tiêu đề / nội dung / link nhạc) + copy toàn bộ gói
- [x] T010 Test: 27 nghệ sĩ × 3 seed đều 700–900 từ; cảnh báo khi sửa ra ngoài

## Phase 3: Ảnh nghệ sĩ

- [x] T011 `images.py`: Wikipedia REST + Commons API, chuẩn hoá license/attribution (bóc HTML)
- [x] T012 `GET /api/projects/{id}/images/suggest` (lọc trùng, trả lỗi mạng thay vì crash)
- [x] T013 `POST /api/projects/{id}/images` nhận `{url}`, `{urls}`, `{images:[candidate]}`
- [x] T014 `POST /api/projects/{id}/images/upload` (nhiều file, multipart)
- [x] T015 Chuẩn hoá JPEG ≤ 2000×3000, xử lý EXIF/alpha, giới hạn 15 MB, chặn link nội bộ/HTML/Pinterest pin
- [x] T016 Banner: ảnh đầu tiên tự thành banner, `PATCH .../images/{id}` để đổi, nhãn BANNER trên UI
- [x] T017 Tải từng ảnh + `GET /images.zip` kèm `ATTRIBUTION.txt`
- [x] T018 UI tab Ảnh nghệ sĩ: đếm N/20, lấy tự động có checkbox + license, dán link, upload, banner, tải về
- [x] T019 Test: mock Wikipedia/Commons, dedupe, zip, đổi banner, xoá dự án xoá file, chặn link xấu

## Phase 4: Text & Voice

- [x] T020 `content.script_for()`: chữ trên video 9–15 từ, hook, caption, hashtag, comment pin, `voice_script`
- [x] T021 Tab Text & Voice với Copy từng khối + preview kiểu Facebook
- [x] T022 `voice.py`: edge-tts en-US neural → mp3, timeout, fallback pyttsx3 (+ ffmpeg tuỳ chọn)
- [x] T023 `GET /api/voices`, `POST/DELETE /api/projects/{id}/voice`
- [x] T024 UI: chọn giọng, tạo voice, `<audio>` nghe thử, nút tải `.mp3`, thông báo engine
- [x] T025 Test: edge-tts, fallback wav, fallback + ffmpeg, không có engine → 400, xoá voice, giới hạn 4000 ký tự

## Phase 5: Giữ nguyên & dọn dẹp

- [x] T026 Giữ tìm sự kiện theo ngày/khoảng/từ khoá/loại, thư viện nghệ sĩ, sự kiện riêng
- [x] T027 Giữ quản lý dự án: lọc trạng thái, tìm kiếm, đổi trạng thái, nhân bản (copy cả ảnh), xoá
- [x] T028 Giữ xuất markdown/JSON, bổ sung credits ảnh + voice vào file xuất
- [x] T029 Luồng trạng thái mới: Nháp → Đã có bài báo → Đã có text & voice → Sẵn sàng đăng → …
- [x] T030 Cập nhật dashboard, How-to, sidebar theo scope mới (không còn MP4)

## Phase 6: Kiểm thử & tài liệu

- [x] T031 `pytest -q` xanh toàn bộ (56 test)
- [x] T032 `tests/ui_smoke.mjs` (jsdom): sidebar 4 màn hình + render lại, 3 tab, đếm từ, cảnh báo, Copy, banner, zip, voice picker, không còn UI MP4 (47 check)
- [x] T033 Cập nhật `README.md`, `docs/spec.md`, `docs/plan.md`, `docs/tasks.md`

## Phase 7: Lấy ảnh tự động & tải về máy

- [x] T040 `POST /api/projects/{id}/images/auto` — lấy + lưu ảnh trong một lần bấm (nút “Tự động lấy 20 ảnh”)
- [x] T041 Fallback khi máy chủ không có Internet: trình duyệt gọi API Wikipedia/Commons, tải bytes, gửi `data_url` (backend giải mã base64, giữ license/attribution)
- [x] T042 UI: thanh tiến trình “Đang tải i/n”, nhãn “trình duyệt tải hộ”, nút `.zip` nổi bật + test jsdom mock Wikipedia → zip JPEG thật

- [x] T043 `GET /api/projects/{id}/bundle.zip` + nút “Tải về máy” (bài báo, JSON, ảnh, voice, `HUONG-DAN.txt`)
- [x] T044 Nút “Kiểm tra mạng” + `POST/GET /api/client-log` để chẩn đoán lỗi mạng phía trình duyệt
- [x] T045 `pytest` 58 test, jsdom 50 check
- [x] T046 Sửa lỗi “đổi voice vẫn nghe bản cũ”: tên file voice mới mỗi lần tạo, `Cache-Control: no-store` cho `/media/voice/`, cảnh báo khi phải dùng pyttsx3 thay edge-tts, nhắc bấm “Tạo voice” khi đổi dropdown (61 pytest, 52 jsdom check)

- [x] T047 `/api/version` + nhãn phiên bản ở sidebar; README mục 2.1 hướng dẫn lấy commit mới cho bản clone cũ / bản ZIP (62 pytest, 53 jsdom check)

- [x] T048 `backend/rivals.py`: chấm điểm “đã nổi” 0–100 (độ phủ/tương tác/độ mới), brief làm lại theo format (mẫu hook + 5 nhịp + nhịp độ), đọc dòng nhập tay; parse số `1.2M/84k/2.1 nghìn/1.5 triệu/1,234` bằng một regex + bảng hậu tố
- [x] T049 `backend/db.py` + API reel đối thủ: `rival_reels` (kèm `remade_project_id`), `GET/POST /api/rivals`, `PATCH/DELETE /api/rivals/{id}`, lọc theo nền tảng/format/trạng thái/điểm tối thiểu/chưa làm lại, sắp theo điểm/view/tương tác/mới
- [x] T050 `POST /api/rivals/{id}/remake`: tạo dự án mới cùng pipeline (nghệ sĩ thư viện, tên mới, hoặc không chọn), gắn `project["remake"]`, brief vào `article.md` + `bundle.zip`, reel chuyển “đang làm lại”
- [x] T051 UI “Reels đối thủ”: nhập hàng loạt, bảng xếp hạng có điểm + nhãn, bộ lọc/sắp xếp, brief mở tại chỗ, nút “Làm lại” mở hộp thoại chọn nghệ sĩ; banner “Làm lại từ reel đối thủ” ở đầu trang Studio
- [x] T052 “Tạo bài viết bằng tên nhân vật”: `backend/profiles.py` + `custom_artists` + `GET/POST /api/artists/custom`, `PATCH/DELETE /api/artists/custom/{id}`, `POST /api/projects/custom`; panel ở Khám phá (tên + dịp + ngày, mở rộng để nhập chi tiết); link nhạc dạng tìm kiếm, giữ đúng đại từ, không in “0 years”
- [x] T054 `POST /api/rivals/from-page` + `GET /api/rivals/pages` + cột `source_page`: chuẩn hoá `1,2 N` / `1.234` / `2,4 Tr`, bóc khối `role="article"` từ HTML lưu trang, bỏ trùng theo link/hook, chọn "đã nổi" (≥60 điểm, hoặc top 40% khi page nhỏ)
- [x] T055 `web/assets/fb-extract.js`: script chạy trong Console của trang Facebook (đọc DOM, gửi thẳng về studio, dự phòng copy JSON); UI tab "Từ link page Facebook" (link page + copy mã + dán JSON + checkbox chỉ bài đã nổi), lọc theo page, chip "chỉ bài đã nổi"; README §5, `spec.md` FR-031…FR-033 + user story 7, `plan.md`, version 2.3.0 (91 pytest, 79 jsdom check UI + 12 check cho fb-extract)
- [x] T053 CSS cho `rival-*`/`tier-*`/`remake-card` (desktop + mobile); bump `APP_VERSION` 2.2.0 + `features` (`rivals-ranking`, `rivals-remake`, `article-by-name`); cập nhật README mục 5–6, `docs/spec.md` FR-026…FR-030, jsdom smoke lên 69 check (77 pytest)

## Backlog (chưa làm)

- [ ] T034 Đăng trực tiếp qua Facebook Graph API (cần quyền Page)
- [ ] T035 Ghép voice + ảnh thành video ngắn bằng công cụ ngoài (CapCut/Canva) — studio chỉ xuất nguyên liệu
- [ ] T036 Lên lịch đăng nhiều ngày + nhắc việc
- [ ] T037 Import thêm nghệ sĩ từ MusicBrainz/Wikipedia (có kiểm duyệt)
- [ ] T038 A/B test tiêu đề/hook và theo dõi hiệu suất sau khi đăng
- [ ] T039 Lưu nhiều bộ ảnh (variants) cho một nghệ sĩ để tái dùng giữa các dự án
