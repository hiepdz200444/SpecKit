# Legends Reel Studio

Trang quản lý – cập nhật – sáng tạo **reels Facebook về các huyền thoại âm nhạc đã mất**, hướng tới khán giả Mỹ 30–60 tuổi.

Một sự kiện (sinh nhật, ngày mất, kỷ niệm phát hành) → **bài báo** → **MP4 dọc 9:16** → **hook + caption + comment pin**, tất cả trong một studio. Mọi nội dung đều được thiết kế để kéo người xem **xuống phần comment** đọc bài báo và nghe nhạc.

> Đây là prototype chạy thật: API + SQLite + render MP4 bằng ffmpeg, không cần khoá API của bên thứ ba.

---

## 1. Quy trình 4 bước

| Bước | Bạn làm gì | Studio làm gì |
| --- | --- | --- |
| **1. Khám phá** | Chọn ngày + khoảng ± ngày, lọc theo loại sự kiện, tìm theo nghệ sĩ/bài hát/thể loại | Quét thư viện 27 huyền thoại, trả về sự kiện đúng ngày kèm 3 bài nhạc và link nghe thử |
| **2. Bài báo** | Sửa tiêu đề, mô tả, nội dung, link nhạc, comment pin, thay ảnh banner | Sinh bài báo tiếng Anh (~500 từ, 3 biến thể tiêu đề), comment đầu tiên có link nhạc, hashtag |
| **3. Video** | Chọn chữ trên video (9–15 từ), phong cách, nhạc nền | Dựng MP4 1080×1920 24s: hook 3.6s, con số sự kiện, bài nhạc, câu gây tò mò, khung comment “đọc ở comment đầu tiên” |
| **4. Hook & comment** | Copy, chỉnh, dán lên Facebook | Sinh hook, caption, hashtag, comment pin + checklist kiểm tra trước khi đăng |

## 2. Chạy thử

```bash
cd apps/legend-reel-studio
./run.sh                 # tạo .venv, cài deps, chạy http://0.0.0.0:8000
```

Hoặc thủ công:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --app-dir backend --host 0.0.0.0 --port 8000
```

Mở `http://localhost:8000`. Lần render đầu mất ~40–60 giây (720 frame Pillow → H.264). Ảnh/audio/video được lưu trong `data/` (không commit).

## 3. Tài liệu đặc tả

Dự án làm theo quy trình Spec-Driven của Spec Kit: [`spec.md`](./docs/spec.md) (người dùng + yêu cầu + tiêu chí đo được) → [`plan.md`](./docs/plan.md) (kỹ thuật, data model, API) → [`tasks.md`](./docs/tasks.md) (tiến độ từng giai đoạn).

## 4. Cấu trúc

```
apps/legend-reel-studio/
├── backend/
│   ├── app.py            # FastAPI: REST + static + job render
│   ├── db.py             # SQLite: projects
│   ├── library.py        # tính sự kiện theo ngày, tìm kiếm
│   ├── seed_artists.py   # 27 huyền thoại + 15 cột mốc phát hành
│   ├── content.py        # sinh bài báo / chữ trên video / hook / caption
│   ├── render.py         # Pillow frame → ffmpeg (H.264 + AAC)
│   └── audio.py          # nhạc nền tổng hợp (pad + sub + pulse + shaker)
├── web/                  # SPA thuần JS + CSS, font OFL
│   ├── index.html · styles.css · app.js
│   └── assets/           # font, ảnh nền sân khấu/vinyl/khán giả
├── docs/                 # spec.md, plan.md, tasks.md (Spec-Driven Development)
├── data/                 # studio.db, banners/, audio/, renders/  (git-ignored)
└── tests/                # pytest: sự kiện, sinh nội dung, API
```

## 5. Nội dung được sinh như thế nào

Không gọi LLM, nên chạy offline và không tốn phí:

- **Sự kiện**: tính từ ngày sinh/ngày mất + danh sách cột mốc phát hành có thật trong `seed_artists.py`. Ngày `29/02` và các trường hợp thiếu năm đều được xử lý.
- **Bài báo**: template có biến thể + `seed` ngẫu nhiên cố định, ghép từ dữ liệu đã tuyển (nghệ sĩ, quê quán, 3 bài hát kèm ghi chú, 3–4 sự kiện có thật). Bài viết **không tự bịa số liệu** — muốn thêm chi tiết, sửa trực tiếp trong tab Bài báo.
- **Chữ trên video**: bắt buộc **9–15 từ**, kiểm tra bằng `word_count()` cả ở UI và API. Nếu tự sửa ra ngoài khoảng, studio cảnh báo ngay.
- **Hook/caption/comment**: mỗi loại có nhiều biến thể, ưu tiên câu hỏi/cảm xúc và CTA “đọc comment đầu tiên”, tránh khẳng định không kiểm chứng được.
- **Link nhạc**: dùng link *tìm kiếm* YouTube/Spotify (`results?search_query=…`) để không bị chết link khi video gốc bị gỡ.

## 6. Thông số video

| Thuộc tính | Giá trị |
| --- | --- |
| Khung hình | 1080 × 1920 (9:16), 30 fps |
| Thời lượng | 24 giây (5 cảnh: hook 3.6s · sự kiện 4.8s · bài nhạc 5.4s · tò mò 5.6s · CTA 4.6s) |
| Codec | H.264 High, yuv420p, `+faststart` (phát web/Reels) |
| Audio | AAC 192 kbps (nhạc tải lên, nhạc nền có sẵn, hoặc không nhạc) |
| Chuyển động | Ken Burns zoom/pan xen kẽ, chữ fade + trượt, waveform động, progress bar |
| Vùng an toàn | Nội dung chính nằm trong 250–1450px, tránh UI của Reels |
| Phong cách | `noir` (mặc định), `vhs` (scanline, hồng), `gold` (vintage ấm) |

## 7. API

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| GET | `/api/bootstrap?day=` | Thư viện nghệ sĩ, thống kê, sự kiện 21 ngày tới |
| GET | `/api/events?day=&window=&q=&kinds=` | Tìm sự kiện theo ngày/khoảng/từ khoá/loại |
| GET | `/api/artists`, `/api/artists/{id}` | Danh sách/chi tiết nghệ sĩ |
| POST | `/api/events/custom` | Thêm sự kiện riêng |
| GET/POST | `/api/projects` | Danh sách/tạo dự án (tạo là sinh luôn bài + kịch bản) |
| GET/PATCH/DELETE | `/api/projects/{id}` | Đọc/cập nhật/xoá |
| POST | `/api/projects/{id}/duplicate` | Nhân bản (không copy video đã render) |
| POST | `/api/projects/{id}/generate` | Sinh lại bài báo / kịch bản với seed mới |
| POST | `/api/projects/{id}/overlay` | Đặt chữ trên video, trả về số từ + hợp lệ |
| POST | `/api/projects/{id}/banner` | Upload ảnh (multipart hoặc `data_url`) |
| POST | `/api/projects/{id}/audio` | Upload nhạc |
| POST | `/api/projects/{id}/render` | Bắt đầu render → trả `job.id` |
| GET | `/api/jobs/{id}` | Tiến độ render (0–100, frame, lỗi) |
| GET | `/api/projects/{id}/export?fmt=md\|json` | Xuất gói bài đăng |

## 8. Ghi chú bản quyền & dữ liệu

- **Ảnh nghệ sĩ**: studio có nút lấy ảnh từ Wikipedia (API công khai, gọi từ trình duyệt của bạn). Ảnh chân dung nghệ sĩ thường vẫn thuộc bản quyền — hãy kiểm tra giấy phép từng ảnh trước khi dùng cho mục đích thương mại, hoặc dùng ảnh bạn có quyền.
- **Nhạc**: chỉ dùng bản bạn có quyền (nhạc mua, nhạc tự thu, hoặc nhạc nền có sẵn trong studio). Nhạc nền mặc định là bản tổng hợp thuật toán, không phải bản thu của nghệ sĩ.
- Dữ liệu ngày sinh/ngày mất và các cột mốc phát hành là dữ liệu lịch sử; nếu bạn sửa, sửa trong `backend/seed_artists.py`.

## 9. Kiểm thử

```bash
cd apps/legend-reel-studio
. .venv/bin/activate
pytest -q
```

Test bao gồm: tính sự kiện theo ngày (kể cả 29/02), tìm kiếm, giới hạn 9–15 từ, sinh bài báo/kịch bản, CRUD dự án qua API và render thử 1 video ngắn (tuỳ chọn, bỏ qua nếu không có ffmpeg).

## 10. Giới hạn đã biết

- Nội dung sinh theo template, chưa phải văn phong tự do như LLM — phù hợp để duyệt nhanh rồi biên tập.
- Chưa có đăng bài trực tiếp qua Graph API (cần quyền Page + app review).
- Render tuần tự (1 video/lần), khoảng 40–60s mỗi reel.
- Chưa có phụ đề tự động theo giọng đọc (voiceover) — có thể thêm bằng TTS ở bước 3.
