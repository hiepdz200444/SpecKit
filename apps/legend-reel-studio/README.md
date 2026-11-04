# Legends Reel Studio

Trang quản lý – cập nhật – sáng tạo **nội dung reels Facebook về các huyền thoại âm nhạc đã mất**, hướng tới khán giả Mỹ 30–60 tuổi.

Một sự kiện (sinh nhật, ngày mất, kỷ niệm phát hành) → **bài báo 700–900 từ** → **bộ ảnh nghệ sĩ (1 banner + 20 ảnh)** → **text đăng bài + voiceover**. Studio **không dựng video** nữa: bạn lo phần hình, studio lo phần chữ, ảnh và giọng đọc.

> Đây là prototype chạy thật: API FastAPI + SQLite + SPA thuần JS, không cần khoá API của bên thứ ba và không gọi LLM.

---

## 1. Quy trình 4 bước

| Bước | Bạn làm gì | Studio làm gì |
| --- | --- | --- |
| **1. Khám phá** | Chọn ngày + khoảng ± ngày, lọc theo loại sự kiện, tìm theo nghệ sĩ/bài hát/thể loại | Quét thư viện 27 huyền thoại, trả về sự kiện đúng ngày kèm 3 bài nhạc và link nghe thử |
| **2. Bài báo** | Sửa tiêu đề và nội dung, chọn biến thể tiêu đề, copy từng khối | Sinh bài báo tiếng Anh **700–900 từ** (đếm từ trực tiếp, cảnh báo khi ra ngoài khoảng), 3 biến thể tiêu đề, 3 link nhạc; mỗi khối có nút Copy |
| **3. Ảnh nghệ sĩ** | Bấm lấy ảnh tự động, dán link ảnh nguồn khác, chọn ảnh banner, tải về hoặc tải cả bộ `.zip` | Lấy ảnh từ **Wikipedia + Wikimedia Commons** kèm **giấy phép + tác giả + link trang gốc**; tải link ảnh bạn dán (Pinterest/Getty — **không scrape**), upload ảnh; mục tiêu **1 banner + 20 ảnh** |
| **4. Text & Voice** | Sửa chữ trên video, hook, caption, comment pin; chọn giọng và bấm tạo voice | Sinh **chữ trên video 9–15 từ**, hook Facebook, caption + comment pin, hashtag (mỗi khối có Copy); tạo voice **edge-tts en-US neural**, nghe thử trong trình duyệt và tải `.mp3` |

Giữ nguyên từ bản cũ: **tìm sự kiện theo ngày**, **thư viện nghệ sĩ**, **quản lý dự án** (trạng thái, nhân bản, xoá) và **xuất markdown**.

## 2. Chạy thử

**Cần trước:** Python 3.11+ và Git (Windows: `winget install --id Git.Git -e --source winget` và `winget install --id Python.Python.3.12 -e --source winget`, sau đó mở lại Terminal).

### Windows — PowerShell (khuyến nghị)

```powershell
git clone -b arena/19d0d9ca-speckit https://github.com/hiepdz200444/SpecKit.git
cd SpecKit\apps\legend-reel-studio
.\run.ps1
```

Nếu PowerShell chặn script: `powershell -ExecutionPolicy Bypass -File .\run.ps1`.
Hoặc đơn giản nhất: **nháy đúp `run.bat`** trong thư mục `apps\legend-reel-studio`.

### macOS / Linux

```bash
git clone -b arena/19d0d9ca-speckit https://github.com/hiepdz200444/SpecKit.git
cd SpecKit/apps/legend-reel-studio
./run.sh                 # tạo .venv, cài deps, chạy http://localhost:8000
```

### Thủ công (mọi hệ điều hành)

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

Mở `http://localhost:8000`. Dữ liệu nằm trong `data/` (`studio.db`, `images/`, `voice/`) và không được commit. Đổi cổng: `PORT=8081 ./run.sh` (PowerShell: `$env:PORT=8081; .\run.ps1`).

## 3. Tài liệu đặc tả

Dự án làm theo quy trình Spec-Driven của Spec Kit: [`spec.md`](./docs/spec.md) (người dùng + yêu cầu + tiêu chí đo được) → [`plan.md`](./docs/plan.md) (kỹ thuật, data model, API) → [`tasks.md`](./docs/tasks.md) (tiến độ từng giai đoạn).

## 4. Cấu trúc

```text
apps/legend-reel-studio/
├── backend/
│   ├── app.py            # FastAPI: REST cho dự án, ảnh, voice, export, static
│   ├── db.py             # SQLite: projects + custom_events, migration cột mới
│   ├── library.py        # tính sự kiện theo ngày, tìm kiếm
│   ├── seed_artists.py   # 27 huyền thoại + 15 cột mốc phát hành
│   ├── content.py        # bài báo 700–900 từ, chữ 9–15 từ, hook, caption, checks
│   ├── images.py         # Wikipedia + Wikimedia Commons (license), tải link, lưu JPEG
│   └── voice.py          # edge-tts (en-US neural) → fallback pyttsx3
├── web/                  # SPA thuần JS + CSS, font OFL
│   ├── index.html · styles.css · app.js
│   └── assets/           # font, ảnh nền sân khấu/vinyl/khán giả
├── docs/                 # spec.md, plan.md, tasks.md (Spec-Driven Development)
├── tests/                # pytest (sự kiện, nội dung, API, ảnh, voice) + ui_smoke.mjs
├── package.json          # chỉ để chạy test UI bằng jsdom
└── data/                 # studio.db, images/, voice/  (git-ignored)
```

## 5. Nội dung được sinh như thế nào

Không gọi LLM, nên chạy offline và không tốn phí:

- **Sự kiện**: tính từ ngày sinh/ngày mất + danh sách cột mốc phát hành có thật trong `seed_artists.py`. Ngày `29/02` và các trường hợp thiếu năm đều được xử lý.
- **Bài báo**: template có biến thể + `seed` cố định, ghép từ dữ liệu đã tuyển (nghệ sĩ, quê quán, 3 bài hát kèm ghi chú, 3–4 sự kiện có thật) rồi bù đoạn để **luôn rơi vào 700–900 từ**. Bài viết **không tự bịa số liệu** — muốn thêm chi tiết, sửa trực tiếp trong tab Bài báo.
- **Chữ trên video**: bắt buộc **9–15 từ**, kiểm tra bằng `word_count()` cả ở UI và API; sửa ra ngoài khoảng thì cảnh báo ngay (vẫn cho lưu).
- **Hook/caption/comment**: mỗi loại có nhiều biến thể, ưu tiên câu hỏi/cảm xúc và CTA “đọc comment đầu tiên”, tránh khẳng định không kiểm chứng được.
- **Link nhạc**: dùng link *tìm kiếm* YouTube/Spotify (`results?search_query=…`) để không bị chết link khi video gốc bị gỡ.

## 6. Ảnh nghệ sĩ

- **Một nút “Tự động lấy 20 ảnh”**: gom ảnh từ Wikipedia (ảnh chính của trang nghệ sĩ) + Wikimedia Commons (tìm theo tên nghệ sĩ và tên trang), thêm thẳng vào dự án. Mỗi ảnh trả về kèm **giấy phép, URL giấy phép, tác giả** (đã bóc HTML) và **link trang file**. Muốn xem trước rồi mới chọn thì dùng “Chọn thủ công”.
- **Máy chủ không có Internet thì trình duyệt tải hộ**: nếu `POST …/images/auto` hoặc `…/images/suggest` không gọi được Wikipedia (mạng công ty chặn, firewall, container không có egress…), studio tự chuyển sang gọi API Wikipedia/Commons **từ trình duyệt của bạn**, tải bytes ảnh bằng `fetch`, rồi gửi lên máy chủ dưới dạng `data_url`. Ảnh vẫn vào đúng thư viện dự án, vẫn giữ license/attribution, và vẫn tải về được bằng `.zip`.
- **Nguồn do bạn dán**: link ảnh trực tiếp (`.jpg/.png/.webp`) từ bất kỳ host công khai nào — dùng khi bạn có ảnh Pinterest/Getty hợp lệ. Studio **không scrape Pinterest**: nếu bạn dán link trang `pinterest.com/pin/…`, API trả lỗi kèm hướng dẫn *Copy image address*.
- **Chặn an toàn**: chỉ nhận `http/https`, chặn localhost/dải IP nội bộ, giới hạn 15 MB, kiểm tra content-type và bytes thật bằng Pillow rồi re-encode JPEG (≤ 2000×3000).
- **Banner + tải về máy**: ảnh đầu tiên tự thành banner, đổi bất cứ lúc nào; mỗi ảnh có nút **Tải về**, cả bộ có **Tải tất cả (.zip)** kèm `ATTRIBUTION.txt` — đây là đường đưa ảnh về máy tính của bạn (thư mục Downloads), không phải chỉ xem trong trình duyệt.
- Hạn mức mềm: mục tiêu **1 banner + 20 ảnh** (tối đa 60 ảnh/dự án).

## 7. Voice

| | Engine | Ghi chú |
| --- | --- | --- |
| Ưu tiên | **edge-tts** | Giọng neural en-US (Aria, Guy, Jenny, Christopher, Michelle, Eric), xuất `.mp3`, cần internet |
| Dự phòng | **pyttsx3** | Dùng giọng hệ thống (Windows SAPI5 / macOS `say` / Linux espeak), xuất `.wav`; nếu máy có `ffmpeg` thì tự chuyển `.mp3` |
| Không có gì | — | API trả lỗi tiếng Việt rõ ràng, phần còn lại của studio vẫn chạy |

API lưu voice vào `data/voice/<project>/`, trả URL để **nghe thử trong trình duyệt** (`<audio>`) và tải file. Text tối đa 4000 ký tự.

## 8. API

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| GET | `/api/bootstrap?day=` | Thư viện nghệ sĩ, thống kê, sự kiện 21 ngày tới, giới hạn từ, danh sách voice |
| GET | `/api/events?day=&window=&q=&kinds=` | Tìm sự kiện theo ngày/khoảng/từ khoá/loại |
| GET | `/api/artists`, `/api/artists/{id}` | Danh sách/chi tiết nghệ sĩ |
| POST | `/api/events/custom` | Thêm sự kiện riêng |
| GET/POST | `/api/projects` | Danh sách/tạo dự án (tạo là sinh luôn bài báo + text/voice script) |
| GET/PATCH/DELETE | `/api/projects/{id}` | Đọc/cập nhật/xoá |
| POST | `/api/projects/{id}/duplicate` | Nhân bản (copy cả ảnh, bỏ voice/banner) |
| POST | `/api/projects/{id}/generate` | Sinh lại `section=article\|script\|all` với seed mới |
| POST | `/api/projects/{id}/overlay` | Đặt chữ trên video, trả về số từ + hợp lệ |
| GET | `/api/projects/{id}/overlay-options` | Gợi ý chữ trên video (tất cả 9–15 từ) |
| GET | `/api/projects/{id}/images/suggest` | Ảnh gợi ý từ Wikipedia + Commons (license/attribution); trả `502` khi máy chủ không có mạng để UI chuyển sang tải bằng trình duyệt |
| POST | `/api/projects/{id}/images/auto` | Tự lấy + lưu ảnh trong một lần (`{count}`), dùng cho nút “Tự động lấy 20 ảnh” |
| GET | `/api/projects/{id}/images` | Ảnh đã lưu trong dự án |
| POST | `/api/projects/{id}/images` | Thêm ảnh từ `{url}`, `{urls}` hoặc `{images:[…candidate]}` — candidate có thể kèm `data_url` (ảnh do trình duyệt tải hộ) |
| POST | `/api/projects/{id}/images/upload` | Upload nhiều file (multipart) |
| PATCH/DELETE | `/api/projects/{id}/images/{image_id}` | Đặt làm banner / xoá ảnh |
| GET | `/api/projects/{id}/images/{image_id}/download` | Tải 1 ảnh |
| GET | `/api/projects/{id}/images.zip` | Tải cả bộ + `ATTRIBUTION.txt` |
| GET | `/api/voices` | Danh sách giọng + engine đang có |
| POST/DELETE | `/api/projects/{id}/voice` | Tạo/xoá voiceover |
| GET | `/api/projects/{id}/export?fmt=md\|json` | Xuất gói bài đăng (bài báo, ảnh credits, text, voice) |

## 9. Ghi chú bản quyền & dữ liệu

- **Ảnh**: ảnh từ Wikimedia có giấy phép mở nhưng **vẫn phải kiểm tra từng file** trước khi dùng thương mại; studio lưu license/attribution và xuất kèm `ATTRIBUTION.txt`. Ảnh từ Pinterest/Getty do bạn tự chịu trách nhiệm về quyền sử dụng.
- **Nhạc**: chỉ dùng bản bạn có quyền — studio chỉ đưa link tìm kiếm, không tải nhạc.
- **Voice**: chỉ dùng text do bạn viết; giọng neural của edge-tts tuân theo điều khoản của Microsoft.
- Dữ liệu ngày sinh/ngày mất và cột mốc phát hành là dữ liệu lịch sử; sửa trong `backend/seed_artists.py`.

## 10. Kiểm thử

```bash
cd apps/legend-reel-studio
. .venv/bin/activate
pytest -q                              # API, nội dung, ảnh (mock mạng), voice (mock engine)
npm install                            # chỉ cần cho test UI (jsdom)
node tests/ui_smoke.mjs               # jsdom: sidebar, 3 tab, copy, banner, voice panel
```

`pytest` bao gồm: tính sự kiện theo ngày (kể cả 29/02), tìm kiếm, ràng buộc 9–15 từ, **bài báo luôn 700–900 từ cho cả 27 nghệ sĩ**, import ảnh từ Wikipedia/Commons với license, chặn link Pinterest/`localhost`/HTML, zip + `ATTRIBUTION.txt`, và voice với cả ba nhánh (edge-tts, pyttsx3, không có engine).

## 11. Giới hạn đã biết

- Nội dung sinh theo template, chưa phải văn phong tự do như LLM — phù hợp để duyệt nhanh rồi biên tập.
- Studio **không dựng video** và không upload lên Facebook: bạn tự dựng reel bằng công cụ quen tay rồi đăng (chưa có Graph API).
- Voice dự phòng pyttsx3 chỉ ra `.wav` nếu máy không có `ffmpeg`.
- Lấy ảnh tự động cần internet; khi offline, dùng dán link hoặc upload.
