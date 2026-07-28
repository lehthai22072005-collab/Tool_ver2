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

## Giai đoạn 2 — PhoBERT Legal NER

Pipeline trong `src/` xây dựng tập NER weak-supervision từ Word,
`thuoc_tinh.json` và `luoc_do.json`, fine-tune `vinai/phobert-base`, suy luận
văn bản dài bằng sliding window, đánh giá trên tập test theo cấp tài liệu và
kiểm tra toàn bộ output. Dữ liệu thô trong `output/documents` chỉ được đọc.

### Cài đặt

Python 3.10–3.12 được hỗ trợ. Khuyến nghị môi trường ảo:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Máy chỉ có CPU nên cài wheel CPU của PyTorch để tiết kiệm dung lượng:

```bash
.venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch
```

### Chạy toàn bộ

```bash
.venv/bin/python -m src.run_stage2 \
  --data-dir output/documents --work-dir . \
  --auto-train --run-inference --run-evaluation --validate-outputs
```

Thêm `--limit 20 --max-steps 2` chỉ dành cho smoke test, không phải kết quả
nghiệm thu. Pipeline mặc định chia theo cấu hình. Baseline 500 tài liệu dùng tỷ
lệ 300/100/100 theo `document_id`; không chia chunk trước khi split.

### Các lệnh độc lập

```bash
# Huấn luyện lại
.venv/bin/python -m src.train --dataset-dir artifacts/dataset_500 \
  --output-dir models/phobert_legal_ner_gpu_500docs \
  --config configs/stage2_500.yaml

# Suy luận một file hoặc cả thư mục
.venv/bin/python -m src.infer --input path/to/file.docx \
  --model models/phobert_legal_ner_gpu_500docs/best \
  --output outputs/entities --config configs/stage2_500.yaml

# Đánh giá held-out test
.venv/bin/python -m src.evaluate --predictions outputs/entities \
  --ground-truth artifacts/dataset/test.jsonl --output reports/evaluation

# Kiểm tra schema, SHA-256, offset, span và độ phủ input
.venv/bin/python -m src.validate_outputs --input-dir outputs/entities \
  --source-dir output/documents --report reports/output_validation.json

# Unit + integration tests
.venv/bin/python -m pytest
```

Output theo tài liệu nằm tại `outputs/entities/<document_id>.json`; các bản tổng
hợp là `outputs/entities.jsonl`, `outputs/entities.csv`,
`outputs/entity_summary.csv` và `outputs/processing_failures.csv`. Mỗi entity
có nhãn, text, offset toàn cục, block/paragraph, confidence và các chunk nguồn.
File `.doc` và `.docx` đều được hỗ trợ; với một file upload đơn lẻ,
`document_id` là tên file không có phần mở rộng.

Checkpoint GPU hiện tại được fine-tune đủ 5 epoch trên Colab Tesla T4 với 300
train, 100 validation và 100 test. Checkpoint tốt nhất là epoch 5; validation
F1 đạt 0,48803. Trên test, precision/recall/F1 lần lượt là
0,36829/0,85871/0,51549. Model và dataset sinh ra không được commit vì dung
lượng lớn; xem `reports/training_history_500.json` và làm theo lệnh ở trên để
tái hiện.

Ngoài các thuộc tính từ `thuoc_tinh.json`, schema hiện có hai nhãn span từ
`luoc_do.json`: `VAN_BAN_LIEN_QUAN` cho tên văn bản liên quan và
`LOAI_QUAN_HE_VAN_BAN` cho loại quan hệ. Vì loại quan hệ rất hiếm trong tập
500 tài liệu, inference dùng PhoBERT làm bộ trích xuất chính và một fallback
exact-pattern cho các cụm quan hệ pháp lý rõ ràng.

### Giới hạn hiện tại

Ground truth được tạo bằng exact/normalized matching từ JSON nên chỉ học được
những trường thực sự xuất hiện trong Word. JSON của test không được dùng khi suy
luận. PhoBERT được thiết kế cho text đã tách từ tiếng Việt; cấu hình mặc định
hiện giữ nguyên text để bảo toàn offset, và lựa chọn segmentation phải được so
sánh bằng validation trước khi thay đổi. Fine-tuning/inference đầy đủ trên hơn
44 nghìn Word cần GPU hoặc thời gian CPU đáng kể.
