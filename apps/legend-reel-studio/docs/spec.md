# Feature Specification: Legends Reel Studio

**Feature Branch**: `arena/98aa16d2-speckit`
**Created**: 2026-11-04
**Status**: Implemented (prototype)
**Input**: "Trang quản lý, cập nhật và tạo reels Facebook cho thị trường Mỹ, chủ đề âm nhạc của các cố nghệ sĩ mà khán giả 30–60 tuổi hâm mộ. Tìm được nghệ sĩ có sự kiện trong ngày + bài nhạc liên quan; viết bài báo (title, nội dung, link nhạc, ảnh banner); dựng MP4 reels kích thích tò mò kéo người xem xuống comment đọc comment đầu tiên để xem báo và nghe nhạc; sinh chữ trên video 9–15 từ và hook Facebook."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tìm sự kiện đúng ngày của huyền thoại (Priority: P1)

Người vận hành nội dung mở studio vào buổi sáng, chọn ngày hôm nay (hoặc một ngày cụ thể), thấy ngay những nghệ sĩ đã mất có sự kiện trong ngày — sinh nhật, ngày mất, kỷ niệm phát hành — kèm 3 bài nhạc liên quan và link nghe thử, rồi tạo dự án chỉ bằng một cú bấm.

**Why this priority**: Không có sự kiện đúng ngày thì toàn bộ chuỗi nội dung mất tính thời sự. Đây là điểm vào của mọi việc khác.

**Independent Test**: Mở tab Khám phá, chọn ngày 08/01 và khoảng "Đúng ngày" → thấy Elvis Presley (sinh nhật lần thứ 91) kèm 3 bài hát và link YouTube; bấm "Tạo reels" → có dự án mới.

**Acceptance Scenarios**:

1. **Given** thư viện nghệ sĩ có dữ liệu ngày sinh/ngày mất, **When** người dùng chọn một ngày và khoảng ±0, **Then** chỉ những sự kiện rơi đúng ngày đó được trả về, sắp xếp ưu tiên "hôm nay".
2. **Given** ngày được chọn không có sự kiện nào, **When** tìm kiếm, **Then** hệ thống gợi ý mở rộng khoảng ngày và hiển thị sự kiện gần nhất kèm nhãn "còn N ngày / N ngày trước".
3. **Given** người dùng gõ "Elvis", "rock", "Memphis" hoặc tên một bài hát, **When** tìm kiếm, **Then** kết quả khớp theo nghệ sĩ, biệt danh, thể loại, quê quán hoặc tên bài hát.
4. **Given** ngày 29/02 trong thư viện, **When** tìm kiếm ở năm không nhuận, **Then** hệ thống không lỗi và bỏ qua mốc không tồn tại.

---

### User Story 2 - Tạo và cập nhật bài báo (Priority: P1)

Từ một sự kiện, studio sinh bài báo tiếng Anh cho thị trường Mỹ: tiêu đề (<100 ký tự) + 3 biến thể, mô tả ngắn, nội dung ~500 từ, 3 link nhạc (YouTube/Spotify), ảnh banner nghệ sĩ, hashtag và comment đầu tiên chứa câu chuyện + link nhạc. Người dùng sửa mọi trường, thay ảnh, lưu lại và xuất file.

**Why this priority**: Bài báo là thứ người xem nhận được sau khi bị kéo xuống comment; không có bài thì reel không có đích đến.

**Independent Test**: Tạo dự án từ một sự kiện → tab Bài báo có tiêu đề, nội dung, 3 link nhạc, ảnh banner; sửa tiêu đề và body → tải lại trang, nội dung vẫn còn; xuất `.md` chứa bài báo + comment pin.

**Acceptance Scenarios**:

1. **Given** một dự án mới, **When** tạo dự án, **Then** bài báo và comment đầu tiên được sinh tự động, trạng thái chuyển khỏi "Nháp".
2. **Given** người dùng nhập tiêu đề, **When** gõ, **Then** bộ đếm ký tự cập nhật và bản xem trước đổi ngay; nội dung được lưu tự động.
3. **Given** người dùng bấm "Lấy ảnh Wikipedia", **When** trang Wikipedia có ảnh, **Then** ảnh được tải về, lưu cục bộ và dùng làm banner; nếu lỗi, hiện thông báo và vẫn cho tải ảnh thủ công.
4. **Given** người dùng sửa nội dung nhưng chưa lưu, **When** chuyển tab rồi quay lại, **Then** nội dung đã nhập không bị mất (autosave ~0.7s).

---

### User Story 3 - Dựng MP4 reels kéo người xem xuống comment (Priority: P2)

Người dùng chỉnh "chữ trên video" (bắt buộc 9–15 từ), chọn phong cách và nhạc, xem preview dọc 9:16, rồi render MP4 1080×1920. Video phải kích thích tò mò và kết thúc bằng lời kêu gọi đọc comment đầu tiên — nơi chứa bài báo và link nhạc.

**Why this priority**: Đây là định dạng phân phối chính; nhưng nếu thiếu, bài báo + caption vẫn có thể dùng thủ công.

**Independent Test**: Vào tab Video, thấy chữ trên video kèm số từ (9–15), bấm Render → thanh tiến độ chạy → có video phát được, tải được, đúng 1080×1920, có audio.

**Acceptance Scenarios**:

1. **Given** chữ trên video 9–15 từ, **When** render, **Then** MP4 H.264/AAC 1080×1920 được tạo và gắn vào dự án; trạng thái chuyển "Sẵn sàng đăng".
2. **Given** chữ trên video ngoài khoảng 9–15 từ, **When** lưu hoặc render, **Then** hệ thống cảnh báo rõ số từ hiện tại và vẫn cho render sau khi người dùng xác nhận.
3. **Given** đang render một video, **When** bấm render dự án khác, **Then** yêu cầu bị từ chối với thông báo "đang có video khác được render".
4. **Given** người dùng chọn "Nhạc của tôi" và tải file, **When** render, **Then** file được cắt/loop đúng 24s, fade in/out, encode AAC.
5. **Given** video đã render, **When** mở dự án, **Then** video và poster hiển thị, có nút tải MP4.

---

### User Story 4 - Hook, caption và comment pin (Priority: P2)

Studio sinh hook Facebook, caption, hashtag và comment đầu tiên (chứa câu chuyện + 2 link nhạc) để người dùng copy/pin, kèm checklist trước khi đăng.

**Why this priority**: Quyết định tỉ lệ người xem mở comment; nhưng có thể viết tay nếu thiếu.

**Independent Test**: Tab Hook & Comment hiển thị hook, caption, hashtag, comment pin; bấm Copy → clipboard có nội dung; checklist đạt 5/5 khi đủ điều kiện.

**Acceptance Scenarios**:

1. **Given** dự án đã có kịch bản, **When** mở tab, **Then** caption chứa CTA "first comment" và hashtag 8–10 tag.
2. **Given** người dùng sửa caption, **When** gõ, **Then** bản xem trước kiểu Facebook cập nhật và nội dung được lưu.
3. **Given** người dùng bấm Copy comment, **When** dán vào Facebook, **Then** nội dung gồm 2 link nhạc và lời dẫn.

---

### User Story 5 - Quản lý, cập nhật, nhân bản, xuất (Priority: P3)

Người dùng xem toàn bộ dự án, lọc theo trạng thái, tìm kiếm, mở lại để sửa, đổi trạng thái, nhân bản, tải MP4, xuất markdown/JSON, xoá.

**Why this priority**: Cần cho vận hành hằng ngày nhưng không chặn lần đăng đầu tiên.

**Independent Test**: Tạo 2 dự án → lọc theo trạng thái → nhân bản → xoá bản gốc → bản sao vẫn mở được.

**Acceptance Scenarios**:

1. **Given** danh sách dự án, **When** lọc theo trạng thái, **Then** chỉ dự án tương ứng hiển thị, kèm số lượng.
2. **Given** một dự án, **When** nhân bản, **Then** bản mới ở trạng thái Nháp, giữ bài báo/kịch bản, không giữ video đã render.
3. **Given** một dự án, **When** xoá và xác nhận, **Then** dự án, MP4, poster và ảnh banner bị xoá khỏi hệ thống.

---

### Edge Cases

- Ngày không có sự kiện nào → empty state có hành động "mở rộng ±30 ngày".
- Nghệ sĩ không có ảnh trên Wikipedia → thông báo lỗi rõ ràng, fallback ảnh nền sân khấu/vinyl, vẫn cho upload.
- Ảnh banner rất dọc hoặc rất ngang → hệ thống cover-crop về 1080×1920 ở bước render, không méo.
- Render thất bại (ffmpeg lỗi, hết chỗ) → job trả `status=error` + message, dự án giữ nguyên dữ liệu.
- Upload audio sai định dạng → 400 kèm danh sách định dạng hỗ trợ.
- Sửa chữ trên video thành 20 từ → cảnh báo nhưng không chặn (người dùng có thể cố ý).
- Tải lại trang giữa lúc render → tiến độ vẫn theo được qua `job.id` (job lưu trong bộ nhớ tiến trình).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI có thư viện nghệ sĩ đã mất, mỗi nghệ sĩ gồm ngày sinh, ngày mất, quê quán, thể loại, thời kỳ, 3 bài hát kèm năm và link nghe, 3–4 dữ kiện có thật.
- **FR-002**: Hệ thống PHẢI tính được sự kiện theo ngày (sinh nhật, ngày mất, kỷ niệm phát hành) trong khoảng ±N ngày, có nhãn tiếng Việt và số năm/số tuổi chính xác.
- **FR-003**: Hệ thống PHẢI tìm kiếm sự kiện theo từ khoá (nghệ sĩ, biệt danh, thể loại, quê quán, tên bài hát) và theo loại sự kiện.
- **FR-004**: Hệ thống PHẢI sinh bài báo tiếng Anh gồm tiêu đề + biến thể, mô tả, nội dung, danh sách link nhạc, hashtag, comment đầu tiên; mọi trường sửa được và lưu tự động.
- **FR-005**: Hệ thống PHẢI cho phép gắn ảnh banner bằng upload hoặc lấy từ Wikipedia (gọi từ trình duyệt), lưu cục bộ.
- **FR-006**: Hệ thống PHẢI sinh kịch bản video 5 cảnh và một dòng "chữ trên video" 9–15 từ, hiển thị số từ và cảnh báo khi ngoài khoảng.
- **FR-007**: Hệ thống PHẢI render MP4 1080×1920, 30fps, 24s, H.264 + AAC, có Ken Burns, typography, waveform, progress bar, CTA comment và màn hình comment giả lập; xuất poster JPG.
- **FR-008**: Hệ thống PHẢI hỗ trợ 3 lựa chọn audio: nhạc nền tổng hợp, nhạc người dùng tải lên, hoặc không nhạc; fade in/out và cắt đúng thời lượng.
- **FR-009**: Hệ thống PHẢI theo dõi tiến độ render theo job và chặn render song song.
- **FR-010**: Hệ thống PHẢI sinh hook, caption, hashtag, comment pin và checklist xuất bản trước khi đăng.
- **FR-011**: Hệ thống PHẢI quản lý dự án: danh sách, lọc theo trạng thái, tìm kiếm, cập nhật, nhân bản, xoá, xuất markdown/JSON, tải MP4.
- **FR-012**: Hệ thống PHẢI giữ trạng thái dự án theo luồng: Nháp → Đã có bài → Đã có kịch bản → Sẵn sàng đăng → Đã lên lịch → Đã đăng.
- **FR-013**: Hệ thống PHẢI chạy offline, không phụ thuộc API trả phí hay LLM bên ngoài.
- **FR-014**: Hệ thống PHẢI hiển thị giao diện tiếng Việt, nội dung xuất bản tiếng Anh (thị trường Mỹ).

### Key Entities

- **Artist**: nghệ sĩ đã mất — tên, biệt danh, thể loại, thời kỳ, ngày sinh/mất, quê quán, trang Wikipedia, bảng màu, danh sách bài hát, dữ kiện, câu legacy.
- **Event**: sự kiện gắn nghệ sĩ — loại (sinh nhật/ngày mất/phát hành/cột mốc), ngày, số năm hoặc tuổi, nhãn hiển thị, khoảng cách tới ngày tham chiếu.
- **Project**: dự án reel — nghệ sĩ, sự kiện, seed, bài báo (tiêu đề/biến thể/mô tả/nội dung/comment/hashtag), banner, link nhạc, kịch bản video, chữ trên video, hook, caption, audio, trạng thái, đường dẫn MP4/poster, thời điểm tạo/cập nhật.
- **Custom Event**: sự kiện do người dùng thêm — nghệ sĩ, ngày, tiêu đề, ghi chú.
- **Render Job**: phiên render — id, dự án, trạng thái, phần trăm, thông điệp, thời lượng, kích thước file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Từ lúc mở studio đến khi có dự án đầu tiên (bài báo + kịch bản) dưới 30 giây, không quá 3 cú bấm.
- **SC-002**: 100% sự kiện trả về có đúng ngày, đúng số năm/tuổi và 3 bài nhạc kèm link.
- **SC-003**: 100% dòng "chữ trên video" do studio sinh ra nằm trong 9–15 từ; số từ hiển thị trực tiếp khi người dùng sửa.
- **SC-004**: Render một reel 24s hoàn tất dưới 90 giây trên máy 2 vCPU, file < 6 MB, phát được trong trình duyệt và trên Facebook.
- **SC-005**: 100% video có CTA "comment đầu tiên" ở cả cảnh cuối, caption và comment pin.
- **SC-006**: Người vận hành có thể chỉnh sửa và lưu lại bài báo/caption mà không mất dữ liệu khi chuyển tab hoặc tải lại trang.

## Assumptions

- Nội dung xuất bản bằng tiếng Anh cho khán giả Mỹ; giao diện vận hành tiếng Việt.
- Người dùng tự chịu trách nhiệm về quyền sử dụng ảnh nghệ sĩ và bản nhạc; nhạc nền mặc định là bản tổng hợp thuật toán.
- Chưa tích hợp đăng bài trực tiếp qua Facebook Graph API (cần quyền Page + app review) — bản này xuất file và copy nội dung.
- Thư viện nghệ sĩ là dữ liệu tuyển chọn (27 nghệ sĩ), có thể mở rộng bằng cách sửa `seed_artists.py`.
- Render chạy cục bộ, tuần tự, phù hợp cho một người vận hành.
