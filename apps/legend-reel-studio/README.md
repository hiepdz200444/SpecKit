# Legends Reel Studio

Trang quản lý – cập nhật – sáng tạo **nội dung reels Facebook về các huyền thoại âm nhạc đã mất**, hướng tới khán giả Mỹ 30–60 tuổi.

Một sự kiện (sinh nhật, ngày mất, kỷ niệm phát hành) → **bài báo 700–900 từ** → **bộ ảnh nghệ sĩ (1 banner + 20 ảnh)** → **text đăng bài + voiceover**. Studio **không dựng video** nữa: bạn lo phần hình, studio lo phần chữ, ảnh và giọng đọc.

Hai đường vào mới: **xem reel của đối thủ đã nổi** rồi **làm lại** bằng nội dung của mình, và **tạo bài viết bằng tên nhân vật** (không cần có trong thư viện 27 nghệ sĩ).

> Đây là prototype chạy thật: API FastAPI + SQLite + SPA thuần JS, không cần khoá API của bên thứ ba và không gọi LLM.

---

## 1. Quy trình 4 bước

| Bước | Bạn làm gì | Studio làm gì |
| --- | --- | --- |
| **0. Nghiên cứu** | Dán link page Facebook đối thủ | Studio gọi thẳng facebook.com từ máy bạn, đọc bài công khai, chấm điểm và chỉ giữ những bài đã nổi, kèm brief cấu trúc để làm lại — **không cần F12/Console** |
| **1. Khám phá** | Chọn ngày + khoảng ± ngày, lọc theo loại sự kiện, tìm theo nghệ sĩ/bài hát/thể loại | Quét thư viện 27 huyền thoại, trả về sự kiện đúng ngày kèm 3 bài nhạc và link nghe thử |
| **2. Bài báo** | Sửa tiêu đề và nội dung, chọn biến thể tiêu đề, copy từng khối | Sinh bài báo tiếng Anh **700–900 từ** (đếm từ trực tiếp, cảnh báo khi ra ngoài khoảng), 3 biến thể tiêu đề, 3 link nhạc; mỗi khối có nút Copy |
| **3. Ảnh nghệ sĩ** | Bấm lấy ảnh tự động, dán link ảnh nguồn khác, chọn ảnh banner, tải về hoặc tải cả bộ `.zip` | Lấy ảnh từ **Wikipedia + Wikimedia Commons** kèm **giấy phép + tác giả + link trang gốc**; tải link ảnh bạn dán (Pinterest/Getty — **không scrape**), upload ảnh; mục tiêu **1 banner + 20 ảnh** |
| **4. Text & Voice** | Sửa chữ trên video, hook, caption, comment pin; chọn giọng và bấm tạo voice | Sinh **chữ trên video 9–15 từ**, hook Facebook, caption + comment pin, hashtag (mỗi khối có Copy); tạo voice **edge-tts en-US neural**, nghe thử trong trình duyệt và tải `.mp3` |

Giữ nguyên từ bản cũ: **tìm sự kiện theo ngày**, **thư viện nghệ sĩ**, **quản lý dự án** (trạng thái, nhân bản, xoá) và **xuất markdown**.

## 2. Chạy trên máy của bạn

**Cần trước:** Python 3.11+ (bắt buộc), Git (chỉ cần nếu bạn clone). Windows cài nhanh:

```powershell
winget install --id Python.Python.3.12 -e --source winget
winget install --id Git.Git -e --source winget
```

Cài xong **mở lại** Terminal/PowerShell để nhận `python`. Khi cài từ python.org nhớ tick **“Add python.exe to PATH”**.

### Windows — nháy đúp `run.bat` (dễ nhất)

1. Tải code: `git clone https://github.com/hiepdz200444/SpecKit.git` **hoặc** vào GitHub → **Code → Download ZIP** → giải nén.
2. Mở thư mục `SpecKit\apps\legend-reel-studio`.
3. Nháy đúp **`run.bat`**. Lần đầu script tự tạo `.venv` và cài thư viện (1–2 phút), sau đó in ra `http://localhost:8000`.
4. Mở trình duyệt tới **`http://localhost:8000`**. Nếu Windows hỏi *Firewall* → chọn **Allow** (chỉ cần khi bạn muốn máy khác trong LAN truy cập).

Dùng PowerShell thay cho `.bat`:

```powershell
cd SpecKit\apps\legend-reel-studio
.\run.ps1
```

Nếu PowerShell chặn script: `powershell -ExecutionPolicy Bypass -File .\run.ps1`.

### macOS / Linux

```bash
git clone -b arena/19d0d9ca-speckit https://github.com/hiepdz200444/SpecKit.git
cd SpecKit/apps/legend-reel-studio
./run.sh          # nếu báo Permission denied: chmod +x run.sh  rồi chạy lại
```

`run.sh` kiểm tra Python ≥ 3.11, tạo `.venv`, cài `requirements.txt` và mở **`http://localhost:8000`**.

### Thủ công (mọi hệ điều hành)

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

### Đổi cổng / cho máy khác truy cập

```bash
PORT=8081 ./run.sh                 # macOS/Linux
```

```powershell
$env:PORT=8081; .\run.ps1          # Windows PowerShell
```

Muốn máy khác trong LAN vào được (điện thoại, máy tính bảng): `HOST=0.0.0.0 PORT=8000 ./run.sh`, rồi mở `http://<IP-máy-bạn>:8000` và cho phép qua firewall.

### Dữ liệu, sao lưu, cập nhật

- Toàn bộ dự án, ảnh, voice nằm trong `apps/legend-reel-studio/data/` (`studio.db`, `images/`, `voice/`). **Sao lưu = copy thư mục `data/`**. Thư mục này không bị commit.
- Nút **“Tải về máy”** trong studio xuất một file `.zip` (bài báo + JSON + ảnh + `ATTRIBUTION.txt` + voice) để mang sang máy khác.
- Cập nhật code: xem mục **2.1** bên dưới rồi chạy lại `run.sh`/`run.bat`. Giữ nguyên `.venv` và `data/`; nếu `requirements.txt` đổi thì xoá `.venv` để cài lại.
- Tắt server: `Ctrl + C`. Lần sau chỉ cần chạy lại `run.sh`/`run.bat` (vài giây, không cài lại gì).

### 2.1. Lấy commit mới khi đã có bản cũ trên máy

**Có Git** — chạy trong thư mục `SpecKit`:

```bash
git fetch origin
git status                       # xem đang ở nhánh nào, có sửa file gì không
git checkout arena/19d0d9ca-speckit   # chỉ cần nếu đang ở nhánh khác (bản cũ)
git pull origin arena/19d0d9ca-speckit
git log --oneline -1             # commit mới nhất, ví dụ: eeb4d17 fix(voice): …
```

Rồi chạy lại `run.sh` / `run.bat`. Gặp vài tình huống thường gặp:

| Tình huống | Cách xử lý |
| --- | --- |
| `Your local changes would be overwritten` | `git stash` → `git pull origin arena/19d0d9ca-speckit` → `git stash pop` |
| Muốn bỏ hết sửa đổi code ở máy, lấy đúng bản trên GitHub | `git reset --hard origin/arena/19d0d9ca-speckit` (không đụng tới `data/`) |
| `fatal: not a git repository` | Bạn đang dùng bản tải ZIP → làm theo cách dưới |
| `git pull` báo có thay đổi `requirements.txt` | Xoá thư mục `.venv` rồi chạy lại `run.sh`/`run.bat` để cài lại thư viện |
| Đang ở nhánh mặc định (bản cũ, có render video) | `git checkout arena/19d0d9ca-speckit` — bản mới nằm ở nhánh này cho tới khi PR #7 được merge |

**Không dùng Git (tải ZIP)**: vào GitHub → chọn branch **`arena/19d0d9ca-speckit`** → **Code → Download ZIP** → giải nén ra thư mục mới, sau đó **copy thư mục `data/` của bản cũ sang** (dự án, ảnh, voice nằm ở đó), rồi chạy `run.bat`/`run.sh` trong thư mục mới. Chỉ muốn cập nhật tại chỗ thì chép đè các thư mục `backend/`, `web/`, `docs/`, `tests/` + các file `requirements.txt`, `run.sh`, `run.ps1`, `run.bat`, `README.md`.

**Kiểm tra đang chạy bản nào**: nhìn góc dưới thanh bên (**`Legends Studio v2.1.0 · eeb4d17`**) hoặc mở [`/api/version`](http://localhost:8000/api/version) — trả về `version`, `commit` (commit của bản clone) và danh sách `features` của bản đang chạy.

### Cần Internet ở đâu?

Studio chạy offline được gần như toàn bộ. Chỉ 2 tính năng cần mạng: **lấy ảnh từ Wikipedia/Commons** và **voice edge-tts**. Không có mạng thì vẫn dùng được: tạo dự án, bài báo, text/voice script, upload ảnh từ máy, đổi banner, tải `.zip`, voice dự phòng bằng `pyttsx3` (giọng hệ thống).

### Nếu gặp lỗi

| Hiện tượng | Cách xử lý |
| --- | --- |
| `python: command not found` / “Chua co Python” | Cài Python 3.11+ rồi **mở lại** Terminal; kiểm tra `python -V` |
| PowerShell: “running scripts is disabled” | `powershell -ExecutionPolicy Bypass -File .\run.ps1` |
| `No module named venv` (Ubuntu/Debian) | `sudo apt install python3-venv` rồi chạy lại `./run.sh` |
| `Address already in use` / cổng 8000 bận | Đổi cổng: `PORT=8081 ./run.sh` hoặc `$env:PORT=8081; .\run.ps1` |
| `pip install` lỗi hoặc treo | Kiểm tra mạng/proxy, chạy lại; hoặc `pip install -r requirements.txt` thủ công để xem lỗi |
| Không mở được `localhost:8000` | Thử `127.0.0.1:8000`; tắt VPN/proxy; kiểm tra cửa sổ terminal còn chạy |
| Bấm lấy ảnh báo “Không gọi được API ảnh” | Máy/mạng đang chặn Wikipedia: thử mạng khác, hoặc dán link ảnh / **Tải ảnh lên**, hoặc bấm **“Kiểm tra mạng”** trong tab Ảnh nghệ sĩ để xem lỗi cụ thể |
| Voice báo lỗi | `edge-tts` cần Internet; `pyttsx3` cần giọng hệ thống — Linux: `sudo apt install espeak-ng`; muốn `.mp3` thì cài thêm `ffmpeg` |
| Trình duyệt vẫn hiện giao diện cũ | `Ctrl + F5` (máy chủ đã đặt `Cache-Control: no-cache` cho `html/js/css`) |

## 3. Tài liệu đặc tả

Dự án làm theo quy trình Spec-Driven của Spec Kit: [`spec.md`](./docs/spec.md) (người dùng + yêu cầu + tiêu chí đo được) → [`plan.md`](./docs/plan.md) (kỹ thuật, data model, API) → [`tasks.md`](./docs/tasks.md) (tiến độ từng giai đoạn).

## 4. Cấu trúc

```text
apps/legend-reel-studio/
├── backend/
│   ├── app.py            # FastAPI: REST cho dự án, ảnh, voice, export, static
│   ├── db.py             # SQLite: projects + custom_events + custom_artists + rival_reels
│   ├── library.py        # tính sự kiện theo ngày, tìm kiếm
│   ├── seed_artists.py   # 27 huyền thoại + 15 cột mốc phát hành
│   ├── content.py        # bài báo 700–900 từ, chữ 9–15 từ, hook, caption, checks
│   ├── profiles.py       # profile sinh từ đúng cái tên (bài 700–900 từ, link nhạc dạng tìm kiếm)
│   ├── rivals.py         # chấm điểm reel đối thủ, brief làm lại, đọc dòng nhập tay, bóc HTML/JSON từ page
│   ├── fb_fetch.py       # dán link page → tự gọi facebook.com, bóc số liệu, nhật ký từng lần thử, cookie phiên
│   ├── images.py         # Wikipedia + Wikimedia Commons (license), tải link, lưu JPEG
│   └── voice.py          # edge-tts (en-US neural) → fallback pyttsx3
├── web/                  # SPA thuần JS + CSS, font OFL
│   ├── index.html · styles.css · app.js
│   └── assets/           # font, ảnh nền sân khấu/vinyl/khán giả, fb-extract.js (mã lấy bài từ page)
├── docs/                 # spec.md, plan.md, tasks.md (Spec-Driven Development)
├── tests/                # pytest (sự kiện, nội dung, API, ảnh, voice) + ui_smoke.mjs
├── package.json          # chỉ để chạy test UI bằng jsdom
└── data/                 # studio.db, images/, voice/  (git-ignored)
```

## 5. Reels đối thủ — lọc bài đã nổi rồi làm lại

Mục **Reels đối thủ** (sidebar) để bạn ghi lại những reel cùng ngách đang ăn view, rồi rút cấu trúc của chúng cho bài của mình.

- **Đưa link page Facebook, studio lọc bài đã nổi**: dán `facebook.com/<ten-page>` (hoặc link dạng `profile.php?id=…`, hoặc link một reel) vào ô “Từ link page Facebook” rồi bấm **Tìm reels nổi**. Máy chủ studio tự gọi facebook.com, thử lần lượt trang **reels → videos → tường page** bằng UA trình duyệt và UA crawler, bóc `play_count` / `reaction_count` / `comment_count` / `share_count` / `creation_time` trong JSON nhúng (và cả khối `role="article"` nếu Facebook trả HTML), rồi chấm điểm và chỉ nhập bài đã nổi. **Không cần mở DevTools, không cần copy mã.**
  - Facebook thường chỉ trả nội dung cho phiên đã đăng nhập. Khi đó studio báo `status=blocked` cùng **nhật ký từng lần thử** (URL · UA · HTTP · số byte · số bài) và hiện ô **dán cookie phiên một lần** (`c_user=…; xs=…`, lấy ở F12 → Application → Cookies). Cookie lưu cục bộ ở `data/fb_session.json` (quyền 600), chỉ gửi tới facebook.com — từ lần sau chỉ cần dán link page.
  - Đường dự phòng vẫn còn khi Facebook chặn hẳn: nút **Copy mã lấy bài** (dán vào Console của trang đang mở) hoặc dán **JSON/HTML** lưu từ trang vào `POST /api/rivals/from-page`.
- **Nhập tay**: mỗi dòng `url | nền tảng | views | likes | comments | shares | nghệ sĩ | hook | format`. Số viết kiểu `1.2M`, `84k`, `2.1 nghìn`, `1.5 triệu` hay `1,234` đều hiểu đúng. Nền tảng để trống thì studio đoán từ link.
- **Chấm “đã nổi”**: điểm 0–100 = độ phủ (≤50) + tỉ lệ tương tác (≤40) + độ mới (≤10), kèm nhãn `Đột phá / Nổi / Khá / Mới`. Reel ít view nhưng tương tác cao vẫn có thể vượt reel triệu view — đúng ý “đã nổi”, không chỉ “nhiều view”.
- **Lọc & xếp hạng**: tìm theo hook/nghệ sĩ, lọc theo **page đối thủ**, nền tảng, format, trạng thái, `chỉ bài đã nổi`, `điểm tối thiểu`, `chưa làm lại`, xếp theo điểm / view / tương tác / mới nhất.
- **“Chỉ bài đã nổi” khi nhập**: giữ bài **≥ 60 điểm**; nếu cả page chưa bài nào đạt 60 (page nhỏ) thì giữ nhóm nổi nhất của chính page đó (top 40%) để bạn không bị danh sách rỗng. Bài trùng link/hook được tự bỏ qua.
- **Brief làm lại** (mở ngay trên card): mẫu hook của format, 5 nhịp thời lượng, nhịp độ, lý do reel ăn view, và **quy tắc làm lại**.
- **Một nút “Làm lại”**: chọn nghệ sĩ trong thư viện, hoặc gõ tên mới, hoặc để trống — studio tạo dự án mới bằng đúng pipeline cũ (bài 700–900 từ, ảnh có license, text & voice) và gắn brief vào dự án (hiện ở đầu trang Studio, có trong `article.md` và `bundle.zip`).

**Sạch về bản quyền**: bản làm lại chỉ lấy *cấu trúc*, không lấy tài sản. Studio không tải video/audio của đối thủ, không dùng ảnh của họ, không copy chữ — toàn bộ bài viết là câu tiếng Anh do template của bạn sinh, ảnh lấy từ Wikipedia/Commons hoặc do bạn dán.

## 6. Tạo bài viết bằng tên nhân vật

Ở **Khám phá** có ô “Tạo bài viết bằng tên nhân vật”: gõ bất kỳ tên người/nhân vật nào (không cần có trong thư viện), chọn dịp + ngày, rồi bấm **Tạo bài viết**.

- Không nhập gì thêm: studio sinh profile tối thiểu từ đúng cái tên, bài vẫn **700–900 từ**, vẫn có tiêu đề, chữ trên video 9–15 từ, hook, caption, hashtag, comment pin và voice script.
- Muốn bài sát thật hơn, mở “Thêm chi tiết”: nghệ danh, thể loại, giai đoạn, quê quán, năm sinh/mất, giọng (he/she), link nguồn Wikipedia, danh sách bài hát `Tên | năm`, và các ghi chú/sự thật.
- **Không tự bịa**: studio chỉ dùng đúng những gì bạn nhập cho phần profile. Bài hát không có mã video thì link nhạc là link *tìm kiếm* YouTube (không chết link); chưa nhập bài nào thì vẫn có 3 link tìm kiếm (greatest hits / live / interview) để bạn có nhạc phát ngay.
- Nhân vật được lưu lại thành profile riêng: gõ lại đúng tên đó lần sau sẽ dùng lại profile (không tạo trùng), sửa/xoá được qua `/api/artists/custom`; profile đang có dự án thì không xoá được.
- Bài viết này dùng lại toàn bộ phần sau: ảnh, text & voice, kiểm tra, xuất `.md` / `bundle.zip`.

## 7. Nội dung được sinh như thế nào

Không gọi LLM, nên chạy offline và không tốn phí:

- **Sự kiện**: tính từ ngày sinh/ngày mất + danh sách cột mốc phát hành có thật trong `seed_artists.py`. Ngày `29/02` và các trường hợp thiếu năm đều được xử lý.
- **Bài báo**: template có biến thể + `seed` cố định, ghép từ dữ liệu đã tuyển (nghệ sĩ, quê quán, 3 bài hát kèm ghi chú, 3–4 sự kiện có thật) rồi bù đoạn để **luôn rơi vào 700–900 từ**. Bài viết **không tự bịa số liệu** — muốn thêm chi tiết, sửa trực tiếp trong tab Bài báo.
- **Chữ trên video**: bắt buộc **9–15 từ**, kiểm tra bằng `word_count()` cả ở UI và API; sửa ra ngoài khoảng thì cảnh báo ngay (vẫn cho lưu).
- **Hook/caption/comment**: mỗi loại có nhiều biến thể, ưu tiên câu hỏi/cảm xúc và CTA “đọc comment đầu tiên”, tránh khẳng định không kiểm chứng được.
- **Link nhạc**: dùng link *tìm kiếm* YouTube/Spotify (`results?search_query=…`) để không bị chết link khi video gốc bị gỡ.

## 8. Ảnh nghệ sĩ

- **Một nút “Tự động lấy 20 ảnh”**: gom ảnh từ Wikipedia (ảnh chính của trang nghệ sĩ) + Wikimedia Commons (tìm theo tên nghệ sĩ và tên trang), thêm thẳng vào dự án. Mỗi ảnh trả về kèm **giấy phép, URL giấy phép, tác giả** (đã bóc HTML) và **link trang file**. Muốn xem trước rồi mới chọn thì dùng “Chọn thủ công”.
- **Chẩn đoán khi vẫn lỗi**: nút **“Kiểm tra mạng”** trong tab Ảnh nghệ sĩ gọi thử Wikipedia API, Commons API và ảnh Commons ngay từ trình duyệt, in kết quả (OK / HTTP / lỗi + số ms) vào dòng trạng thái và gửi về `POST /api/client-log` để xem lại trong `data/client.log`.
- **Máy chủ không có Internet thì trình duyệt tải hộ**: nếu `POST …/images/auto` hoặc `…/images/suggest` không gọi được Wikipedia (mạng công ty chặn, firewall, container không có egress…), studio tự chuyển sang gọi API Wikipedia/Commons **từ trình duyệt của bạn**, tải bytes ảnh bằng `fetch`, rồi gửi lên máy chủ dưới dạng `data_url`. Ảnh vẫn vào đúng thư viện dự án, vẫn giữ license/attribution, và vẫn tải về được bằng `.zip`.
- **Nguồn do bạn dán**: link ảnh trực tiếp (`.jpg/.png/.webp`) từ bất kỳ host công khai nào — dùng khi bạn có ảnh Pinterest/Getty hợp lệ. Studio **không scrape Pinterest**: nếu bạn dán link trang `pinterest.com/pin/…`, API trả lỗi kèm hướng dẫn *Copy image address*.
- **Chặn an toàn**: chỉ nhận `http/https`, chặn localhost/dải IP nội bộ, giới hạn 15 MB, kiểm tra content-type và bytes thật bằng Pillow rồi re-encode JPEG (≤ 2000×3000).
- **Tải về máy**: nút **“Tải về máy”** ở đầu trang dự án tải một file `.zip` gồm bài báo (`.md`), `project.json`, toàn bộ ảnh JPEG kèm `ATTRIBUTION.txt`, file voice và `HUONG-DAN.txt`. Riêng ảnh có **Tải về máy (.zip)** trong tab Ảnh nghệ sĩ.
- **Banner + tải về máy**: ảnh đầu tiên tự thành banner, đổi bất cứ lúc nào; mỗi ảnh có nút **Tải về**, cả bộ có **Tải tất cả (.zip)** kèm `ATTRIBUTION.txt` — đây là đường đưa ảnh về máy tính của bạn (thư mục Downloads), không phải chỉ xem trong trình duyệt.
- Hạn mức mềm: mục tiêu **1 banner + 20 ảnh** (tối đa 60 ảnh/dự án).

## 9. Voice

| | Engine | Ghi chú |
| --- | --- | --- |
| Ưu tiên | **edge-tts** | Giọng neural en-US (Aria, Guy, Jenny, Christopher, Michelle, Eric), xuất `.mp3`, cần internet |
| Dự phòng | **pyttsx3** | Dùng giọng hệ thống (Windows SAPI5 / macOS `say` / Linux espeak), xuất `.wav`; nếu máy có `ffmpeg` thì tự chuyển `.mp3` |
| Không có gì | — | API trả lỗi tiếng Việt rõ ràng, phần còn lại của studio vẫn chạy |

API lưu voice vào `data/voice/<project>/`, trả URL để **nghe thử trong trình duyệt** (`<audio>`) và tải file. Text tối đa 4000 ký tự.

**Đổi giọng đọc:** mỗi lần bấm “Tạo voice”, studio ghi ra **file mới** (`voiceover-<mã>.mp3`) và xoá bản cũ, nên trình duyệt không bao giờ phát lại bản ghi cũ từ cache (`/media/voice/*` trả `Cache-Control: no-store`). Chọn giọng khác trong dropdown → nút “Tạo voice” sáng lên → bấm để ghi lại; nếu `edge-tts` không chạy được (không có Internet, hoặc bị chặn `speech.platform.bing.com`), studio dùng giọng hệ thống `pyttsx3` và **hiện cảnh báo rõ** rằng giọng en-US bạn chọn chưa được áp dụng — vì vậy mọi lựa chọn sẽ nghe giống nhau cho tới khi có mạng.

## 10. API

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| GET | `/api/bootstrap?day=` | Thư viện nghệ sĩ, thống kê, sự kiện 21 ngày tới, giới hạn từ, danh sách voice |
| GET | `/api/events?day=&window=&q=&kinds=` | Tìm sự kiện theo ngày/khoảng/từ khoá/loại |
| GET | `/api/artists`, `/api/artists/{id}` | Danh sách/chi tiết nghệ sĩ |
| POST | `/api/events/custom` | Thêm sự kiện riêng |
| GET/POST | `/api/rivals` | Danh sách/nhập reel đối thủ (`lines` hoặc `items`), lọc (`page`, `only_viral`, …) + xếp theo điểm đã nổi |
| POST | `/api/rivals/scan-page` | **Dán link page → tự đọc và nhập reel đã nổi**: `{page_url, only_viral?, min_score?, limit?}`; trả `status` (`ok\|blocked\|empty\|error`), `attempts`, `needs_session`, số bài đã đọc/đã nhập |
| GET/POST/DELETE | `/api/rivals/session` | Trạng thái/lưu/xoá cookie phiên Facebook (một lần) để máy chủ đọc được page |
| POST | `/api/rivals/from-page` | Nhập từ page đối thủ: `{page_url, posts?, html?, only_viral?}` — JSON do `web/assets/fb-extract.js` trích trong trình duyệt, hoặc HTML lưu từ trang |
| GET | `/api/rivals/pages` | Các page đã có reel trong studio (cho bộ lọc) |
| PATCH/DELETE | `/api/rivals/{id}` | Sửa/xoá reel (ghi chú, trạng thái `moi\|dang-lam\|da-lam`) |
| POST | `/api/rivals/{id}/remake` | Làm lại reel: tạo dự án mới cùng pipeline, gắn brief + link reel gốc |
| GET/POST | `/api/artists/custom` | Profile tạo bằng tên; `PATCH/DELETE /api/artists/custom/{id}` |
| POST | `/api/projects/custom` | Tạo dự án từ tên nhân vật (`{name, profile?, event?, seed?, generate?}`) |
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
| GET | `/api/projects/{id}/images.zip` | Tải cả bộ ảnh về máy + `ATTRIBUTION.txt` |
| GET | `/api/projects/{id}/bundle.zip` | **Tải về máy cả gói**: `article.md`, `project.json`, `images/` + `ATTRIBUTION.txt`, `voice/`, `HUONG-DAN.txt` |
| POST/GET | `/api/client-log` | Trình duyệt gửi lỗi mạng lên máy chủ để chẩn đoán (xem `data/client.log`) |
| GET | `/api/voices` | Danh sách giọng + engine đang có |
| POST/DELETE | `/api/projects/{id}/voice` | Tạo/xoá voiceover |
| GET | `/api/projects/{id}/export?fmt=md\|json` | Xuất gói bài đăng (bài báo, ảnh credits, text, voice) |

## 11. Ghi chú bản quyền & dữ liệu

- **Ảnh**: ảnh từ Wikimedia có giấy phép mở nhưng **vẫn phải kiểm tra từng file** trước khi dùng thương mại; studio lưu license/attribution và xuất kèm `ATTRIBUTION.txt`. Ảnh từ Pinterest/Getty do bạn tự chịu trách nhiệm về quyền sử dụng.
- **Nhạc**: chỉ dùng bản bạn có quyền — studio chỉ đưa link tìm kiếm, không tải nhạc.
- **Voice**: chỉ dùng text do bạn viết; giọng neural của edge-tts tuân theo điều khoản của Microsoft.
- Dữ liệu ngày sinh/ngày mất và cột mốc phát hành là dữ liệu lịch sử; sửa trong `backend/seed_artists.py`.

## 12. Kiểm thử

```bash
cd apps/legend-reel-studio
. .venv/bin/activate
pytest -q                              # API, nội dung, ảnh (mock mạng), voice (mock engine)
npm install                            # chỉ cần cho test UI (jsdom)
node tests/ui_smoke.mjs               # jsdom: sidebar 5 mục, 3 tab, copy, banner, voice, reels đối thủ, quét page bằng link, nhập từ page, bài theo tên
node tests/fb_extract.mjs             # jsdom: mã lấy bài đọc đúng DOM kiểu Facebook
```

`pytest` bao gồm: tính sự kiện theo ngày (kể cả 29/02), tìm kiếm, ràng buộc 9–15 từ, **bài báo luôn 700–900 từ cho cả 27 nghệ sĩ**, import ảnh từ Wikipedia/Commons với license, chặn link Pinterest/`localhost`/HTML, zip + `ATTRIBUTION.txt`, voice với cả ba nhánh (edge-tts, pyttsx3, không có engine), **profile tạo bằng tên** (700–900 từ, không in “0 years”, link nhạc dạng tìm kiếm), **reel đối thủ** (đọc số `1.2M/84k/1,5 triệu`, chấm điểm, lọc, làm lại, brief nằm trong `.md`/`bundle.zip`) và **nhập từ page** (chuẩn hoá `1,2 N` / `1.234`, bóc khối `role="article"` từ HTML, lọc bài đã nổi, bỏ trùng, lọc theo page) và **quét page bằng link** (`fb_fetch`: đọc JSON nhúng `video_id`/`play_count`/`reaction_count`, gộp bài trùng, nhận diện tường đăng nhập, cookie phiên, HTTP thật qua server nội bộ).

## 13. Giới hạn đã biết

- Nội dung sinh theo template, chưa phải văn phong tự do như LLM — phù hợp để duyệt nhanh rồi biên tập.
- Studio **không dựng video** và không upload lên Facebook: bạn tự dựng reel bằng công cụ quen tay rồi đăng (chưa có Graph API).
- Voice dự phòng pyttsx3 chỉ ra `.wav` nếu máy không có `ffmpeg`.
- Lấy ảnh tự động cần internet; khi offline, dùng dán link hoặc upload.
