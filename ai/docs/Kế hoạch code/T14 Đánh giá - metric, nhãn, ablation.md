# T14 · Đánh giá: metric, bộ nhãn, ablation, test bất biến, G2

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `09` (toàn bộ) · `03` mục "Đo chất lượng tiền xử lý" · `01` mục 9.

## Mục tiêu

Công cụ để chạy Chương 4: đo từng tầng, chạy ablation chỉ bằng **đổi file config**, báo khoảng tin cậy.

## Làm

1. `evaluation/labels/`: định dạng file nhãn
   - mức (JD, CV): thang 0/1/2, 2 người chấm, cột người chấm; tính κ;
   - mức cặp (trách nhiệm, gạch): `khớp / một phần / không` (≈300 cặp);
   - chia dev/test 50/50 phân tầng theo vai trò (seed cố định).
   - Công cụ **pooling**: hợp top-300 Retrieve của mọi cấu hình RT-*, top-60 Rerank của mọi R-*, + 20 CV ngẫu nhiên → xuất danh sách cần chấm (CSV/JSON cho người chấm).
2. `evaluation/metrics.py`: Recall@K (50/100/200/300), nDCG@10 (gain 2^nhãn − 1), Recall@30 và Recall@30 / min(30, #phù hợp), AUC mức cặp; báo trung bình theo JD, JD tệ nhất, tách theo vai trò và fresher/có kinh nghiệm; tỉ lệ cặp chưa chấm.
3. `evaluation/bootstrap.py`: bootstrap ghép cặp theo JD, khoảng tin cậy 95% cho chênh lệch giữa hai cấu hình.
4. `evaluation/ablation.py`: đọc file "kế hoạch thí nghiệm" (YAML: danh sách cấu hình, mỗi cấu hình là phần ghi đè config) → chạy Retrieve/Rerank trên tập dev → bảng kết quả + đường cong chi phí–chất lượng (thời gian/JD vs nDCG@10). Viết sẵn file kế hoạch cho RT-E1…E6 và R-A0, R-E1…R-E14 (những gì code hiện hỗ trợ; còn lại để `todo`).
5. `evaluation/calibrate.py`: từ tập 300 cặp → `lo` = trung vị R của cặp `không`, `hi` = trung vị R của cặp `khớp`; đề xuất ngưỡng mức khớp; in giá trị để người dùng đưa vào config mới (`rr-1.1.yaml`), không tự sửa.
6. `evaluation/invariance.py` (thiết kế 09 mục 6): từ ~50 CV sinh biến đổi (đổi tên, giới tính, trường, năm sinh/tốt nghiệp, thứ tự mục/gạch, bỏ dấu) → chạy **cả pipeline từ JSON** → Δ điểm phải = 0 (trừ bỏ dấu: phải có cờ `no_diacritics`).
7. **G2** (09 mục 4.2): chạy lại T05, T04, T06, T08, T11/F05, T19 qua cả pipeline, so với kỳ vọng trong bảng.
8. Đo chất lượng tiền xử lý: công cụ lấy mẫu 50 CV + 30 JD, xuất file cho người kiểm tay; script tính precision/recall kỹ năng, sai số `years_experience`, tỉ lệ đúng `role_group`/`level_rank`.

## Tiêu chí xong

- Test metric trên ví dụ tính tay (nDCG, Recall@K, AUC).
- Ablation chạy được trên dữ liệu fixture với nhãn tổng hợp, ra bảng + biểu đồ.
- Test bất biến trên fixture: Δ = 0 cho mọi biến đổi trừ bỏ dấu.

## Ghi chú bàn giao

_(agent điền)_
