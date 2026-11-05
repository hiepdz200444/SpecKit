# Feature Specification: Legends Reel Studio (v2 — không dựng video)

**Feature Branch**: `arena/19d0d9ca-speckit`
**Created**: 2026-11-04 · **Revised**: 2026-11-05 (thêm nhập reel từ link page Facebook)
**Status**: Implemented (prototype)
**Input**: "Trang quản lý, cập nhật nội dung reels Facebook cho thị trường Mỹ, chủ đề âm nhạc của các cố nghệ sĩ mà khán giả 30–60 tuổi hâm mộ. Tìm sự kiện trong ngày + bài nhạc liên quan; viết bài báo tiếng Anh 700–900 từ kèm link nhạc; gom 1 ảnh banner + 20 ảnh nghệ sĩ từ Wikipedia/Commons (có license) hoặc từ link người dùng dán vào; sinh chữ trên video 9–15 từ, hook Facebook, caption + comment pin; tạo voice tiếng Anh để nghe thử và tải .mp3. Không dựng video."

## Phạm vi

**Trong phạm vi**: nhập reel từ link page đối thủ, tìm sự kiện, thư viện nghệ sĩ, bài báo, bộ ảnh nghệ sĩ + banner, text đăng bài, voice TTS, quản lý dự án, xuất markdown/JSON, **theo dõi reel đối thủ đã nổi + làm lại**, **tạo bài viết bằng tên nhân vật bất kỳ**.

**Ngoài phạm vi (đã bỏ hẳn)**: render MP4, ffmpeg/imageio-ffmpeg, tổng hợp nhạc nền, preview điện thoại 9:16, job render + polling tiến độ, mọi nút render/tải MP4. Studio không tạo video.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tìm sự kiện đúng ngày của huyền thoại (Priority: P1)

Người vận hành nội dung mở studio vào buổi sáng, chọn ngày hôm nay (hoặc một ngày cụ thể), thấy ngay những nghệ sĩ đã mất có sự kiện trong ngày — sinh nhật, ngày mất, kỷ niệm phát hành — kèm 3 bài nhạc liên quan và link nghe thử, rồi tạo dự án chỉ bằng một cú bấm.

**Why this priority**: Không có sự kiện đúng ngày thì toàn bộ chuỗi nội dung mất tính thời sự.

**Independent Test**: Mở tab Khám phá, chọn ngày 08/01 và khoảng "Đúng ngày" → thấy Elvis Presley (sinh nhật lần thứ 91) kèm 3 bài hát và link YouTube; bấm "Tạo dự án" → có dự án mới.

**Acceptance Scenarios**:

1. **Given** thư viện nghệ sĩ có dữ liệu ngày sinh/ngày mất, **When** chọn một ngày và khoảng ±0, **Then** chỉ sự kiện rơi đúng ngày đó được trả về, ưu tiên "hôm nay".
2. **Given** ngày được chọn không có sự kiện, **When** tìm kiếm, **Then** hệ thống gợi ý mở rộng khoảng ngày và hiển thị sự kiện gần nhất kèm nhãn "còn N ngày / N ngày trước".
3. **Given** người dùng gõ "Elvis", "rock", "Memphis" hoặc tên bài hát, **When** tìm kiếm, **Then** kết quả khớp theo nghệ sĩ, biệt danh, thể loại, quê quán hoặc tên bài hát.
4. **Given** ngày 29/02 trong thư viện, **When** tìm kiếm ở năm không nhuận, **Then** hệ thống không lỗi.

---

### User Story 2 - Bài báo 700–900 từ có kiểm soát độ dài (Priority: P1)

Từ một sự kiện, studio sinh bài báo tiếng Anh cho thị trường Mỹ: tiêu đề (<100 ký tự) + 3 biến thể, nội dung **700–900 từ**, 3 link nhạc. Tab Bài báo chỉ cần ba khối đó; mỗi khối có nút Copy. Khi người dùng sửa nội dung, số từ cập nhật ngay và hiện cảnh báo nếu ra ngoài khoảng.

**Why this priority**: Bài báo là thứ người xem nhận được sau khi bị kéo xuống comment; độ dài quyết định nhịp đọc trên Facebook.

**Independent Test**: Tạo dự án → tab Bài báo hiển thị tiêu đề, nội dung (đếm từ trong 700–900), 3 link nhạc, mỗi khối có Copy; xoá bớt nội dung xuống 500 từ → cảnh báo đỏ hiện ngay; lưu → tải lại trang, nội dung vẫn còn.

**Acceptance Scenarios**:

1. **Given** một dự án mới, **When** tạo, **Then** bài báo được sinh với 700–900 từ và 3 link nhạc; trạng thái chuyển khỏi "Nháp".
2. **Given** người dùng sửa nội dung, **When** số từ ra ngoài 700–900, **Then** bộ đếm và dòng cảnh báo đổi màu đỏ, nêu rõ cần thêm/bớt bao nhiêu từ; vẫn cho lưu.
3. **Given** người dùng bấm Copy ở một khối, **When** dán ra ngoài, **Then** chỉ nội dung của khối đó được copy (tiêu đề / nội dung / link nhạc).
4. **Given** người dùng sửa nội dung nhưng chưa lưu, **When** chuyển tab rồi quay lại, **Then** nội dung đã nhập không bị mất (autosave ~0.7s).

---

### User Story 3 - Bộ ảnh nghệ sĩ: 1 banner + 20 ảnh, có giấy phép (Priority: P1)

Người dùng mở tab Ảnh nghệ sĩ, bấm "Lấy từ Wikipedia + Commons" để nhận danh sách ảnh gợi ý kèm giấy phép và tác giả, chọn những ảnh muốn lưu, hoặc dán link ảnh trực tiếp từ nguồn khác (Pinterest/Getty) để studio tải về, hoặc upload từ máy. Sau đó đánh dấu 1 ảnh làm banner, tải từng ảnh hoặc tải cả bộ `.zip`.

**Why this priority**: Không có ảnh nghệ sĩ thì reel mất cảm xúc; ảnh không rõ giấy phép là rủi ro pháp lý khi đăng công khai.

**Independent Test**: Trong tab Ảnh nghệ sĩ, bấm lấy ảnh tự động → thấy ≥10 ảnh kèm license; chọn 3 → lưu; dán 1 link ảnh trực tiếp → tải về thành công; đổi banner; bấm "Tải tất cả (.zip)" → file zip có ảnh + `ATTRIBUTION.txt`.

**Acceptance Scenarios**:

1. **Given** nghệ sĩ có trang Wikipedia, **When** bấm lấy ảnh tự động, **Then** studio trả về ảnh chính của Wikipedia và ảnh từ Commons, mỗi ảnh có giấy phép, URL giấy phép, tác giả và link trang file.
2. **Given** ảnh gợi ý đã hiển thị, **When** chọn N ảnh và bấm thêm, **Then** N ảnh được tải về, lưu vào dự án, giữ nguyên license/attribution; ảnh trùng không bị thêm hai lần.
3. **Given** người dùng dán link ảnh Pinterest/Getty, **When** bấm tải, **Then** ảnh được tải về máy chủ và lưu kèm nguồn; nếu là link trang (không phải link ảnh) hoặc link nội bộ/`localhost`, hệ thống từ chối với thông báo tiếng Việt hướng dẫn.
4. **Given** dự án đã có ảnh, **When** bấm "Đặt làm banner", **Then** đúng một ảnh được đánh dấu banner và ảnh bìa của dự án đổi theo.
5. **Given** dự án đã có ảnh, **When** bấm "Tải tất cả (.zip)", **Then** nhận file zip gồm toàn bộ ảnh JPEG và `ATTRIBUTION.txt` liệt kê nguồn + giấy phép + tác giả.

---

### User Story 4 - Text đăng bài + voice (Priority: P1)

Người dùng cần một dòng chữ trên video 9–15 từ, một hook Facebook, caption kèm comment pin — mỗi khối có Copy — và một voiceover tiếng Anh để ghép vào reel họ tự dựng.

**Why this priority**: Đây là toàn bộ phần "lời" của reel và là thứ kéo người xem xuống comment.

**Independent Test**: Mở tab Text & Voice → thấy chữ trên video kèm số từ (9–15), hook, caption, comment pin, mỗi khối có Copy; bấm "Tạo voice" → nghe được ngay trong trình duyệt và tải được file.

**Acceptance Scenarios**:

1. **Given** dự án mới, **When** mở tab, **Then** chữ trên video nằm trong 9–15 từ và hiển thị số từ; sửa ra ngoài khoảng thì cảnh báo ngay.
2. **Given** người dùng bấm Copy ở caption hoặc comment pin, **When** dán vào Facebook, **Then** nội dung gồm CTA "first comment" và 2 link nhạc trong comment pin.
3. **Given** máy có internet, **When** bấm "Tạo voice", **Then** edge-tts tạo file `.mp3` bằng giọng en-US neural đã chọn, phát được bằng `<audio>` trong trình duyệt và tải về được.
4. **Given** máy offline hoặc edge-tts lỗi, **When** bấm "Tạo voice", **Then** studio chuyển sang pyttsx3 và vẫn trả file nghe được (`.wav`, hoặc `.mp3` nếu có ffmpeg hệ thống).
5. **Given** không có engine TTS nào, **When** bấm "Tạo voice", **Then** API trả lỗi tiếng Việt rõ ràng và phần còn lại của studio vẫn hoạt động.

---

### User Story 5 - Quản lý, cập nhật, nhân bản, xuất (Priority: P2)

Người dùng xem toàn bộ dự án, lọc theo trạng thái, tìm kiếm, mở lại để sửa, đổi trạng thái, nhân bản (copy cả ảnh), xuất markdown/JSON, xoá.

**Independent Test**: Tạo 2 dự án → lọc theo trạng thái → nhân bản → xoá bản gốc → bản sao vẫn mở được và ảnh vẫn tải được.

**Acceptance Scenarios**:

1. **Given** danh sách dự án, **When** lọc theo trạng thái, **Then** chỉ dự án tương ứng hiển thị kèm số lượng.
2. **Given** một dự án, **When** nhân bản, **Then** bản mới ở trạng thái Nháp, giữ bài báo + ảnh, bỏ voice và banner.
3. **Given** một dự án, **When** xoá và xác nhận, **Then** dự án, ảnh và voice bị xoá khỏi hệ thống.
4. **Given** một dự án, **When** xuất markdown, **Then** file gồm bài báo, link nhạc, chữ trên video, hook, caption, hashtag, comment pin, credits ảnh và voice.

---

### UI Bug (đã sửa)

**Given** người dùng đang ở một màn hình bất kỳ, **When** bấm một mục ở sidebar, **Then** ứng dụng mở đúng màn hình tương ứng (Tổng quan `#/`, Khám phá `#/discover`, Dự án `#/projects`, Cách hoạt động `#/howto`); **When** bấm lại chính mục đang mở, **Then** màn hình được render lại (không bị "chết").

### Edge Cases

- Ngày không có sự kiện → empty state có hành động "mở rộng ±30 ngày".
- Nghệ sĩ không có ảnh trên Wikipedia → thông báo lỗi rõ ràng, vẫn cho dán link/upload; banner fallback về ảnh nền sân khấu.
- Nghệ sĩ không có trang Wikipedia hoặc Commons không có ảnh → `suggest` trả `502` + lý do, UI hiện hướng dẫn dán link/upload, không crash.
- Máy chủ không có Internet (firewall/container) → UI tự gọi API Wikipedia/Commons từ trình duyệt, tải bytes ảnh rồi gửi lên bằng `data_url`; ảnh vẫn vào dự án với license/attribution và vẫn tải về được bằng `.zip`.
- Ảnh rất dọc/rất ngang → chuẩn hoá về JPEG ≤ 2000×3000, không méo; ảnh PNG trong suốt được đặt trên nền tối.
- Link ảnh trả về HTML hoặc > 15 MB → từ chối kèm lý do.
- Bài báo dài quá 900 hoặc ngắn dưới 700 từ → cảnh báo nhưng không chặn lưu.
- Chữ trên video 20 từ → cảnh báo nhưng không chặn.
- Voice lỗi mạng giữa chừng → chuyển engine dự phòng; nếu cả hai lỗi, trả message chi tiết.
- Dữ liệu cũ trong `data/studio.db` (trạng thái `video`, cột render) → tự migrate sang trạng thái `script` và bỏ qua cột cũ, không mất dự án.

## Requirements *(mandatory)*

### User Story 5 - Lọc reel đối thủ đã nổi rồi làm lại (Priority: P1)

Người vận hành thấy một reel cùng ngách đang ăn view. Họ dán link + số liệu vào studio, studio chấm điểm "đã nổi", xếp hạng, lọc theo nền tảng/format/điểm, mở brief cấu trúc (mẫu hook, 5 nhịp, nhịp độ, lý do ăn view) rồi bấm **Làm lại** để có dự án mới cùng pipeline — nhưng bằng chữ của mình và ảnh có license.

**Why this priority**: Học cấu trúc từ cái đã thắng là cách nhanh nhất để lên view, mà vẫn không đụng bản quyền của đối thủ.

**Independent Test**: Nhập 2 reel (TikTok 1.2M view, Instagram 320k) → bảng xếp hạng hiện điểm/nhãn; lọc `instagram` còn 1 card; mở brief thấy 5 nhịp; bấm "Làm lại" → dự án mới, đầu trang Studio có banner "Làm lại từ reel đối thủ", brief nằm trong `article.md` và `bundle.zip`.

**Acceptance Scenarios**:

1. **Given** chuỗi số viết kiểu `1.2M`, `84k`, `2.1 nghìn`, `1.5 triệu`, `1,234`, **When** nhập reel, **Then** mọi giá trị được parse đúng (view/like/comment/share).
2. **Given** reel đã nhập, **When** xem danh sách, **Then** mỗi reel có điểm 0–100 + nhãn (`Đột phá / Nổi / Khá / Mới`), tách rõ điểm độ phủ, tương tác và độ mới.
3. **Given** bộ lọc, **When** chọn nền tảng/format/điểm tối thiểu/"chưa làm lại"/sắp xếp, **Then** danh sách lọc và sắp đúng.
4. **Given** một reel, **When** bấm "Làm lại" và chọn nghệ sĩ trong thư viện — hoặc gõ tên mới — hoặc để trống, **Then** tạo dự án mới với bài 700–900 từ và reel được đánh dấu đang làm lại, có `remade_project_id`.
5. **Given** dự án đã làm lại, **When** mở xuất `.md`/`bundle.zip`, **Then** có mục "Remake brief" ghi reel gốc + cấu trúc cần giữ.
6. **Given** yêu cầu bản quyền, **When** làm lại, **Then** studio KHÔNG tải video/audio/ảnh của đối thủ và KHÔNG copy chữ của họ.

---

### User Story 6 - Tạo bài viết bằng tên nhân vật (Priority: P2)

Người vận hành muốn viết về một người không có trong thư viện 27 nghệ sĩ. Họ gõ tên vào ô "Tạo bài viết bằng tên nhân vật" ở Khám phá, có thể thêm chi tiết (nghệ danh, thể loại, quê quán, năm sinh/mất, bài hát, ghi chú), bấm một nút và nhận dự án đầy đủ.

**Why this priority**: Mở rộng nội dung ra ngoài 27 người mà không phải sửa code, không cần LLM.

**Independent Test**: Gõ "Michael Jackson", thêm thể loại + 2 bài hát → dự án mới có 700–900 từ, tiêu đề, chữ trên video 9–15 từ, hook, caption, hashtag, comment pin, voice script; gõ lại đúng tên đó → dùng lại profile, không tạo trùng.

**Acceptance Scenarios**:

1. **Given** chỉ có tên, **When** tạo, **Then** bài vẫn 700–900 từ và không in số liệu bịa (không "0 years", không tuổi sai).
2. **Given** có thêm chi tiết, **When** tạo, **Then** bài nhắc đúng nghệ danh/thể loại/quê quán/bài hát/ghi chú đã nhập.
3. **Given** bài hát không có mã video hoặc chưa nhập bài nào, **When** xem link nhạc, **Then** link là YouTube *search* (không phải video id bịa); profile chỉ có tên vẫn nhận 3 link tìm kiếm để có nhạc phát ngay.
4. **Given** giới tính được chọn, **When** sinh bài, **Then** đại từ đúng (he/his hoặc she/her).
5. **Given** tên trống, **When** bấm tạo, **Then** API trả 400 với thông báo tiếng Việt.
6. **Given** profile đang có dự án, **When** xoá profile, **Then** API chặn bằng 400.

---

### User Story 7 - Đưa link page Facebook, studio tự lọc bài đã nổi (Priority: P1)

Người vận hành có một page đối thủ cùng ngách. Họ **dán link page rồi bấm một nút**: máy chủ studio gọi thẳng facebook.com, đọc phần công khai của page, bóc số liệu từng bài và **chỉ giữ những bài đã nổi** — sẵn sàng bấm "Làm lại". Không phải mở DevTools, không phải copy mã (Console của Facebook chặn dán mã bằng cảnh báo self-XSS). Nếu Facebook đòi phiên đăng nhập, người dùng dán cookie **một lần** rồi từ đó chỉ cần dán link.

**Why this priority**: Nhập tay từng reel rất chậm; đọc cả page một lần rồi lọc mới là cách dùng thật.

**Independent Test**: Dán `facebook.com/OldSchoolMusicPage` → bấm "Tìm reels nổi" → studio báo đã đọc N bài, nhập đúng các bài đạt ngưỡng, gắn nhãn page, bỏ bài trùng; khi Facebook trả trang đăng nhập, studio hiện nhật ký từng lần thử + ô dán cookie phiên và đọc lại được ngay; lọc theo page còn đúng số bài; mỗi bài bấm "Làm lại" được.

**Acceptance Scenarios**:

1. **Given** một page có cả bài nổi và bài thường, **When** nhập với `only_viral`, **Then** chỉ bài ≥ 60 điểm được thêm; nếu cả page chưa bài nào đạt 60 thì giữ top 40% của page đó.
2. **Given** bài đã có trong studio, **When** nhập lại cùng page, **Then** bài trùng (theo link hoặc hook) bị bỏ qua và báo số bài bỏ qua.
3. **Given** số liệu viết `1,2 N`, `1.234`, `1.2K`, `2,4 Tr`, **When** nhập, **Then** quy đổi đúng.
4. **Given** HTML lưu từ trang (`Ctrl+S`), **When** gửi vào `POST /api/rivals/from-page` với `html`, **Then** studio bóc được các khối `role="article"` kèm số liệu và link bài.
5. **Given** nhiều page đối thủ, **When** mở danh sách, **Then** lọc được theo page và thấy số bài của từng page.
6. **Given** link page hợp lệ, **When** bấm "Tìm reels nổi", **Then** máy chủ tự thử trang reels → videos → tường page bằng UA trình duyệt và UA crawler, và trả về `status` (`ok`/`blocked`/`empty`/`error`) kèm nhật ký từng lần thử (URL, UA, HTTP, số byte, số bài).
7. **Given** Facebook trả trang đăng nhập, **When** người dùng dán cookie phiên (`c_user`, `xs`) một lần, **Then** studio lưu cục bộ (`data/fb_session.json`, quyền 600), chỉ gửi cookie tới facebook.com, và đọc lại page ngay mà không cần thao tác gì thêm.
8. **Given** người dùng dán link một reel/video (`/reel/<id>`, `/videos/<id>`, `watch/?v=`) hoặc link page dạng id số (`profile.php?id=…`), **When** bấm tìm, **Then** studio đọc đúng bài đó / đúng page đó.

---

### Functional Requirements

- **FR-001**: Hệ thống PHẢI có thư viện nghệ sĩ đã mất, mỗi nghệ sĩ gồm ngày sinh, ngày mất, quê quán, thể loại, thời kỳ, 3 bài hát kèm năm và link nghe, 3–4 dữ kiện có thật.
- **FR-002**: Hệ thống PHẢI tính được sự kiện theo ngày (sinh nhật, ngày mất, kỷ niệm phát hành) trong khoảng ±N ngày, có nhãn tiếng Việt và số năm/số tuổi chính xác.
- **FR-003**: Hệ thống PHẢI tìm kiếm sự kiện theo từ khoá (nghệ sĩ, biệt danh, thể loại, quê quán, tên bài hát) và theo loại sự kiện.
- **FR-004**: Hệ thống PHẢI sinh bài báo tiếng Anh gồm tiêu đề + 3 biến thể, nội dung **700–900 từ**, 3 link nhạc; bài sinh tự động phải luôn nằm trong khoảng này.
- **FR-005**: API và UI PHẢI đếm từ và cảnh báo khi nội dung bài báo ra ngoài 700–900 từ (không chặn lưu).
- **FR-006**: Tab Bài báo chỉ gồm ba khối (tiêu đề, nội dung, link nhạc) và mỗi khối PHẢI có nút Copy (thêm nút copy toàn bộ gói).
- **FR-007**: Hệ thống PHẢI lấy ảnh nghệ sĩ từ Wikipedia + Wikimedia Commons qua API công khai, lưu **giấy phép, URL giấy phép, tác giả, link trang file** cho mỗi ảnh.
- **FR-008**: Hệ thống PHẢI cho phép thêm ảnh bằng (a) chọn từ gợi ý, (b) dán link ảnh trực tiếp, (c) upload file; PHẢI chặn/không scrape trang Pinterest và từ chối link không phải ảnh.
- **FR-009**: Hệ thống PHẢI đánh dấu được ảnh banner (đúng một ảnh), mục tiêu 1 banner + 20 ảnh/dự án.
- **FR-010**: Mỗi ảnh PHẢI có nút tải riêng; cả bộ PHẢI tải được dưới dạng `.zip` kèm `ATTRIBUTION.txt`.
- **FR-011**: Hệ thống PHẢI sinh chữ trên video 9–15 từ, hook Facebook, caption, hashtag, comment pin; mỗi khối có Copy.
- **FR-012**: Hệ thống PHẢI tạo voice từ text: ưu tiên edge-tts với giọng en-US neural, fallback pyttsx3 khi offline/không có mạng; trả file để nghe thử trong trình duyệt và tải về.
- **FR-013**: Hệ thống PHẢI quản lý dự án: danh sách, lọc trạng thái, tìm kiếm, cập nhật, nhân bản, xoá, xuất markdown/JSON.
- **FR-014**: Hệ thống PHẢI giữ trạng thái dự án theo luồng Nháp → Đã có bài báo → Đã có text & voice → Sẵn sàng đăng → Đã lên lịch → Đã đăng.
- **FR-015**: Hệ thống KHÔNG được chứa render video, ffmpeg, job render hay nút tải MP4.
- **FR-016**: Sidebar PHẢI điều hướng được cả 5 màn hình (Khám phá, Dự án, Reels đối thủ, Cách hoạt động, …) và render lại khi bấm lại mục đang mở.
- **FR-017**: Hệ thống PHẢI chạy offline (trừ hai tính năng cần mạng: lấy ảnh và edge-tts), không phụ thuộc LLM hay API trả phí.
- **FR-018**: Giao diện PHẢI là tiếng Việt, nội dung xuất bản là tiếng Anh (thị trường Mỹ).
- **FR-023**: Đổi giọng đọc PHẢI tạo file voice mới (tên khác) và trả URL mới, phục vụ với `Cache-Control: no-store`, để trình duyệt không phát lại bản ghi cũ.
- **FR-024**: Khi engine dự phòng (pyttsx3) được dùng thay edge-tts, UI PHẢI cảnh báo rằng giọng en-US đã chọn chưa được áp dụng.
- **FR-025**: Studio PHẢI cho biết phiên bản đang chạy: `GET /api/version` trả `version`, `commit` và `features`; sidebar hiện `Legends Studio vX · commit`.
- **FR-019**: Nút “Tự động lấy 20 ảnh” PHẢI lấy và lưu ảnh trong một lần bấm (`POST /images/auto`); khi máy chủ không có Internet, studio PHẢI tự chuyển sang tải ảnh bằng trình duyệt và upload qua `data_url`, kèm tiến trình “Đang tải i/n”.
- **FR-021**: Studio PHẢI có nút “Tải về máy” xuất một `.zip` gồm `article.md`, `project.json`, ảnh JPEG + `ATTRIBUTION.txt`, voice và `HUONG-DAN.txt`.
- **FR-022**: UI PHẢI có công cụ “Kiểm tra mạng” gọi thử Wikipedia/Commons từ trình duyệt và gửi kết quả về `POST /api/client-log` để chẩn đoán khi máy chủ bị chặn mạng.
- **FR-026**: Hệ thống PHẢI cho nhập reel đối thủ bằng dán tay (`url | nền tảng | views | likes | comments | shares | nghệ sĩ | hook | format`), hiểu số viết tắt `1.2M`, `84k`, `2.1 nghìn`, `1.5 triệu`, `1,234`; chỉ đọc đúng URL người dùng đưa vào — không có scraper chạy nền, không token, không gửi dữ liệu cho bên thứ ba.
- **FR-027**: Mỗi reel PHẢI được chấm điểm "đã nổi" 0–100 (độ phủ ≤50 + tương tác ≤40 + độ mới ≤10) kèm nhãn, và PHẢI lọc/sắp xếp được theo điểm, view, tương tác, mới nhất, nền tảng, format, trạng thái, "chưa làm lại".
- **FR-028**: Mỗi reel PHẢI có brief làm lại: mẫu hook theo format, timeline từng nhịp, nhịp độ, lý do reel ăn view, quy tắc làm lại.
- **FR-029**: PHẢI làm lại reel bằng một nút: tạo dự án mới qua đúng pipeline (bài 700–900 từ, ảnh có license, text & voice), gắn brief vào dự án và vào `article.md`/`bundle.zip`, đánh dấu reel đang làm lại. Bản làm lại PHẢI dùng chữ do studio sinh và ảnh có license — KHÔNG dùng video/audio/ảnh/chữ của đối thủ.
- **FR-030**: PHẢI tạo được bài viết từ tên nhân vật bất kỳ (`POST /api/projects/custom`), có trường tuỳ chọn (nghệ danh, thể loại, giai đoạn, quê quán, năm sinh/mất, giọng, link nguồn, bài hát, ghi chú); profile lưu lại để tái dùng, không tạo trùng, xoá được khi chưa có dự án; link nhạc cho profile tự tạo PHẢI là link tìm kiếm.
- **FR-031**: Hệ thống PHẢI nhập được reel từ **link page đối thủ**: `POST /api/rivals/from-page` nhận `posts` (JSON do script trong trình duyệt người dùng trích), `html` (trang đã lưu) hoặc `items`; mỗi reel lưu `source_page`; PHẢI bỏ bài trùng theo link/hook và trả về số bài thêm/bỏ qua/loại.
- **FR-032**: Khi nhập từ page, PHẢI có chế độ **chỉ giữ bài đã nổi** (≥ 60 điểm; nếu cả page chưa đạt 60 thì giữ top 40% của page đó), và danh sách PHẢI lọc được theo `source_page` + `only_viral`.
- **FR-033**: Studio PHẢI giữ đường dự phòng đọc page bằng chính trang người dùng đang mở: `/assets/fb-extract.js` (chạy trong Console hoặc dán vào ô JSON) và `POST /api/rivals/from-page` nhận `posts` / `html` / `items`.
- **FR-034**: `POST /api/rivals/scan-page` PHẢI cho phép **chỉ dán link page** là studio tự đọc: gọi `/<page>/reels/`, `/<page>/videos/`, `/<page>` (và `profile.php?id=…&sk=reels|videos` cho page dạng id số), thử lần lượt UA trình duyệt / Googlebot / facebookexternalhit, bóc `video_id`/`play_count`/`reaction_count`/`comment_count`/`share_count`/`creation_time`/`permalink_url` trong JSON nhúng và khối `role="article"`, gộp + khử trùng, chấm điểm, rồi chỉ nhập bài đã nổi. Phản hồi PHẢI có `status` (`ok|blocked|empty|error`), `attempts` (URL, UA, HTTP, số byte, số bài, ghi chú), `needs_session` và `message` giải thích bằng tiếng Việt. Tổng thời gian PHẢI có ngân sách (mặc định ≤ 30 giây) để giao diện không treo.
- **FR-036**: Studio PHẢI vượt qua việc Facebook trả **HTTP 400** cho client máy chủ: mỗi URL được thử bằng ba kiểu client (Chrome giả lập TLS+HTTP/2 qua `curl_cffi`, HTTP/2 qua `httpx`, HTTP/1.1) và ba UA (Chrome, Googlebot, facebookexternalhit); nhật ký từng lần thử PHẢI ghi kiểu client, HTTP, số byte, số bài và **đoạn HTML Facebook trả về**; trạng thái `denied` PHẢI được giải thích riêng.
- **FR-037**: PHẢI có hai đường nhập **không cần DevTools** khi máy chủ bị chặn: (a) `POST /api/rivals/from-html` nhận HTML lưu bằng `Ctrl+S` (bóc cả JSON nhúng lẫn DOM), (b) `GET /api/rivals/bookmarklet` trả một dòng `javascript:` (lấy từ `fb-extract.js`, trỏ về origin studio đang mở) để kéo lên thanh bookmark và bấm trên page đang mở.
- **FR-038**: UI PHẢI cảnh báo khi thiếu `curl_cffi` (kèm lệnh cài) và giữ cookie phiên dạng **toàn bộ chuỗi cookie** (không chỉ `c_user`/`xs`).
- **FR-035**: Khi Facebook đòi đăng nhập, studio PHẢI cho lưu **cookie phiên một lần** qua `POST /api/rivals/session` (đọc/xoá qua `GET`/`DELETE`), lưu ở `data/fb_session.json` với quyền `600`, chỉ gửi tới facebook.com, và PHẢI tự đọc lại page ngay sau khi lưu.
- **FR-020**: Sau khi lấy ảnh, người dùng PHẢI tải được ảnh về máy: từng ảnh qua nút “Tải về”, cả bộ qua `images.zip` (JPEG + `ATTRIBUTION.txt`).

### Key Entities

- **Artist**: nghệ sĩ đã mất — tên, biệt danh, thể loại, thời kỳ, ngày sinh/mất, quê quán, trang Wikipedia, bảng màu, 3 bài hát, dữ kiện, câu legacy.
- **Event**: sự kiện gắn nghệ sĩ — loại (sinh nhật/ngày mất/phát hành/cột mốc), ngày, số năm/tuổi, nhãn hiển thị, khoảng cách tới ngày tham chiếu.
- **Project**: dự án — nghệ sĩ, sự kiện, seed, bài báo (tiêu đề/biến thể/nội dung), link nhạc, trạng thái, thời điểm.
- **Image**: ảnh nghệ sĩ — id, file JPEG, nguồn (wikipedia/wikimedia/user/upload), tiêu đề, URL gốc, link trang, giấy phép, URL giấy phép, tác giả/ghi công, kích thước, cờ banner.
- **Script**: text đăng bài — chữ trên video, số từ, hook, caption, hashtag, comment pin, "voice_script" gợi ý.
- **Voice**: voiceover — file, engine (edge-tts/pyttsx3/…), giọng, định dạng, dung lượng, thời lượng, text nguồn.
- **Custom Event**: sự kiện người dùng thêm — nghệ sĩ, ngày, tiêu đề, ghi chú.
- **Custom Artist**: profile tạo từ tên — tên, nghệ danh, thể loại, giai đoạn, quê quán, năm sinh/mất, giọng, link nguồn, bài hát, ghi chú.
- **Rival Reel**: reel đối thủ — url, nền tảng, format, views/likes/comments/shares, nghệ sĩ, hook, ngày đăng, **page nguồn**, điểm + tier, trạng thái (mới/đang làm/đã làm), `remade_project_id`, ghi chú.

## Success Criteria *(mandatory)*

- **SC-001**: Từ lúc mở studio đến khi có dự án đầu tiên (bài báo + text/voice) dưới 30 giây, không quá 3 cú bấm.
- **SC-002**: 100% sự kiện trả về đúng ngày, đúng số năm/tuổi và 3 bài nhạc kèm link.
- **SC-003**: 100% bài báo do studio sinh ra nằm trong 700–900 từ, cho cả 27 nghệ sĩ và mọi seed được kiểm thử.
- **SC-004**: 100% dòng "chữ trên video" do studio sinh ra nằm trong 9–15 từ; số từ hiển thị trực tiếp khi người dùng sửa.
- **SC-005**: 100% ảnh lưu vào dự án có trường giấy phép (kể cả giá trị "không rõ") và nguồn; file `.zip` luôn kèm `ATTRIBUTION.txt`.
- **SC-006**: Voice tạo được bằng ít nhất một engine khi máy có mạng **hoặc** pyttsx3; khi không có engine, lỗi trả về đọc được bằng tiếng Việt.
- **SC-007**: Sidebar mở đúng 4 màn hình; bấm lại mục đang mở vẫn render (kiểm tra bằng jsdom).
- **SC-011**: Với một page có ít nhất một bài đạt 60 điểm, nhập từ link page chỉ thêm đúng những bài đạt ngưỡng; nhập lại lần hai không tạo bản trùng.
- **SC-009**: 100% reel nhập vào có điểm 0–100 và brief đủ 5 nhịp; mọi bản làm lại nằm trong 700–900 từ và mở được từ Studio về reel gốc.
- **SC-010**: Tạo bài từ tên nhân vật chỉ cần 1 ô nhập + 1 cú bấm; 100% bài sinh ra (kể cả chỉ có tên) nằm trong 700–900 từ và không chứa số liệu bịa.
- **SC-008**: Người vận hành có thể chỉnh sửa và lưu lại bài báo/text mà không mất dữ liệu khi chuyển tab hoặc tải lại trang.

## Assumptions

- Nội dung xuất bản bằng tiếng Anh cho khán giả Mỹ; giao diện vận hành tiếng Việt.
- Người dùng tự chịu trách nhiệm về quyền sử dụng ảnh và bản nhạc.
- Studio không dựng video và chưa tích hợp đăng bài qua Facebook Graph API.
- Thư viện nghệ sĩ là dữ liệu tuyển chọn (27 nghệ sĩ), mở rộng bằng cách sửa `seed_artists.py` hoặc tạo profile bằng tên.
- Số liệu reel đối thủ đến từ trình duyệt của người dùng (script đọc trang họ đang mở) hoặc do họ nhập — studio không cào dữ liệu nền tảng, không giữ token Facebook.
- Số liệu đọc từ DOM là con số hiển thị (đã làm tròn kiểu `1.2K`); người dùng sửa lại được từng reel.
- edge-tts cần internet; pyttsx3 cần giọng hệ thống (SAPI5/say/espeak).
