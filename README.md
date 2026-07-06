# 🏛️ Tool Cào Dữ Liệu Văn Bản Pháp Luật (vbpl.vn)

Công cụ Python chuyên nghiệp giúp tự động thu thập thông tin, nội dung toàn văn, thuộc tính và lược đồ quan hệ của các Văn bản Pháp luật từ trang web chính thức `vbpl.vn`.

## ✨ Tính năng nổi bật
- **Gom nhóm dữ liệu thông minh**: Tự động phân loại văn bản theo Loại văn bản và Số hiệu văn bản dưới dạng thư mục cha - con trực quan (Ví dụ: `output/documents/Nghi_dinh/139_2026_ND-CP/`).
- **Đóng gói chuẩn cấu trúc**: Bên trong mỗi thư mục văn bản chứa chính xác các file:
  - `noi_dung.docx`: Toàn văn nội dung văn bản gốc định dạng Word sạch sẽ (Times New Roman, cỡ chữ 13).
  - `thuoc_tinh.json`: Chứa dữ liệu thuộc tính (Ngày ban hành, Cơ quan ban hành, Người ký, Tình trạng hiệu lực...).
  - `luoc_do.json`: Sơ đồ mối quan hệ, các văn bản liên quan, thay thế hoặc bổ sung.
- **Tải file thông minh**: Nếu văn bản trống tab Nội dung, hệ thống tự động chuyển sang tải các file đính kèm gốc ở tab Tải về (Loại bỏ file rác Template.pdf và file PDF trùng lặp nội dung với file Word).
- **Xử lý trùng lặp nâng cao**: Tự động nhận diện và gán mã ID định danh duy nhất cho các văn bản cổ/văn bản đặc thù bị trùng tiêu đề "Không số", chặn đứng hoàn toàn tình trạng ghi đè mất file.
- **Cơ chế chạy tiếp sức (Resume)**: Ghi nhớ tiến trình thông minh. Nếu rớt mạng hoặc dừng đột ngột, lần sau chạy lại sẽ tự động bỏ qua các văn bản đã tải thành công.

---

## 🐳 Hướng dẫn vận hành với Docker Desktop (Khuyên dùng)

Vì đây là một công cụ tương tác yêu cầu người dùng nhập số và chữ từ bàn phím (chọn hình thức văn bản, số trang, xác nhận tải...), chúng ta cần chạy Docker dưới chế độ tương tác terminal.

### Bước 1: Biên dịch Image (Chỉ làm lần đầu)
Mở Terminal tại thư mục gốc của dự án (`Tool_VBPL`) và chạy lệnh:

```bash
docker compose build
```

### Bước 2: Khởi chạy Tool ở chế độ tương tác Menu
Chạy lệnh sau để bật màn hình nhập liệu:

```bash
docker compose run --rm vbpl-crawler
```

(Tham số --rm đảm bảo container sẽ tự động được dọn dẹp sạch sẽ sau khi bạn tắt tool, không gây nặng máy).

### Bước 3: Hướng dẫn các bước nhập liệu (Sau khi chạy lệnh trên)
Ngay sau khi chạy lệnh ở Bước 2, một menu Hỏi - Đáp tiếng Việt sẽ hiện ra. Bạn hãy hoàn thành các câu hỏi theo trình tự sau bằng bàn phím:

1. Chọn hình thức văn bản: Nhập số tương ứng với loại văn bản bạn cần tải (Ví dụ: Nhập 3 nếu muốn chọn Bộ luật, nhập 6 cho Nghị định, 7 cho Thông tư...) rồi ấn Enter.

2. Từ khóa tìm kiếm: Nếu muốn tải toàn bộ, hãy bỏ trống và ấn trực tiếp phím Enter.

3. Số item mỗi page: Để mặc định là 10, ấn phím Enter.

4. Tải tất cả các trang? (y/N):

   - Gõ y rồi ấn Enter nếu muốn tải sạch toàn bộ danh mục đã chọn.

   - Ấn Enter trực tiếp (chọn No) nếu chỉ muốn tải thử trang đầu tiên.

5. Giới hạn số văn bản xử lý: Để mặc định là 0 (không giới hạn), ấn phím Enter.

6. Tiếp tục từ dữ liệu đã tải trước đó nếu có? (Y/n):

   - Ấn phím Enter trực tiếp (chọn Yes): Tool sẽ tự bỏ qua các file đã có sẵn, chỉ cào file mới (Khuyên dùng khi mất mạng chạy lại).

   - Gõ n rồi ấn Enter: Tool sẽ quét và ghi đè/tải lại từ đầu.

### Bước 4: Chờ hoàn tất và lấy dữ liệu
- Hệ thống sẽ hiển thị thanh tiến trình tải ([===...===]). Khi chạy xong 100%, dòng chữ Pipeline finished sẽ xuất hiện.

- Ấn Enter một lần cuối để đóng cửa sổ.

- Dữ liệu cào được sẽ nằm ngay tại thư mục output/documents/ trên máy thật của bạn.