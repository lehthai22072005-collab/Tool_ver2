# Báo cáo Giai đoạn 2 — PhoBERT Legal NER

## Trạng thái

Pipeline đã hoàn thiện và chạy end-to-end với đầu vào `.doc`/`.docx`. Model
hiện tại là `vinai/phobert-base`, được fine-tune trên Colab Tesla T4. Đây là
baseline nghiên cứu, chưa đạt chất lượng production.

## Dữ liệu

- Tổng mẫu: 500 văn bản.
- Train: 300.
- Validation: 100.
- Test: 100.
- Split theo `document_id`, không có leakage.
- Dataset validation: pass, không có lỗi span/offset.

Ngoài tám thuộc tính từ `thuoc_tinh.json`, dataset có hai nhãn span từ
`luoc_do.json`:

- `VAN_BAN_LIEN_QUAN`: `schema_json.relations[].documents[].title`.
- `LOAI_QUAN_HE_VAN_BAN`: `schema_json.relations[].relation_type`.

ID, URL, direction và bảng lookup trong `luoc_do.json` được giữ là metadata vì
không phải lúc nào cũng xuất hiện dưới dạng span trong Word.

## Huấn luyện

- Epoch: 5.
- Max length/stride: 256/64.
- Learning rate: 3e-5.
- Batch size: 16.
- Entity class weight: 50.
- Train chunks: 1.490.
- Validation chunks: 914.
- Test chunks: 954.
- Train runtime: 323,21 giây; wall time: 387,30 giây.
- Checkpoint tốt nhất: epoch 5 (`checkpoint-470`).

Validation F1 theo epoch:

| Epoch | F1 |
|---:|---:|
| 1 | 0,23774 |
| 2 | 0,42631 |
| 3 | 0,42098 |
| 4 | 0,42173 |
| 5 | **0,48803** |

## Held-out test

- Loss: 0,19382.
- Precision: 0,36829.
- Recall: 0,85871.
- F1: 0,51549.

Recall cao nhưng precision còn thấp, nghĩa là model tìm được phần lớn span gold
nhưng vẫn dự đoán dư. Không sử dụng test để chọn epoch hay điều chỉnh config.

Hai kiểm tra Word end-to-end đều thành công. Một tài liệu nhận ba
`VAN_BAN_LIEN_QUAN`; tài liệu có cụm `văn bản dẫn chiếu` nhận đúng
`LOAI_QUAN_HE_VAN_BAN`. Do nhãn loại quan hệ chỉ có 23 span train, inference
dùng fallback exact-pattern cho các cụm quan hệ rõ ràng và ghi
`source=relation_rule`; các entity khác vẫn có `source=phobert`.

## Artefact và kiểm thử

- Dataset validation: `reports/dataset_500_validation.json`.
- Training history: `reports/training_history_500.json`.
- Config: `configs/stage2_500.yaml`.
- Unit/integration tests: 17 passed.
- Checkpoint, dataset, cache và output inference bị loại khỏi Git do dung lượng
  lớn; checkpoint cục bộ nằm tại
  `models/phobert_legal_ner_gpu_500docs/best`.
