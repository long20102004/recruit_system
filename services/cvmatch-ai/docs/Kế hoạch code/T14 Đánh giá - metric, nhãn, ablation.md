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

**Trạng thái: xong công cụ (23/11/2026); chưa có nhãn thật (Q-8) nên mọi số đo dưới đây là trên nhãn TỔNG HỢP.**

- **Module** (`evaluation/`): `labels/` (định dạng `graded.csv`, `pairs.csv`, κ Cohen + κ trọng số, giải quyết lệch: `final` > trùng > làm tròn xuống, chia dev/test phân tầng), `labels/pooling.py`, `metrics.py` (Recall@K, nDCG@10 gain 2^l−1, Recall@N + bản chuẩn hoá, AUC, tổng hợp theo truy vấn / tệ nhất / nhóm, tỉ lệ chưa chấm), `bootstrap.py` (ghép cặp theo JD, CI 95%), `ablation.py` (kế hoạch YAML = phần ghi đè config, cả Luồng C và D, lưới trọng số R-E13, báo cáo MD + CSV + SVG chi phí–chất lượng có biên Pareto), `calibrate.py`, `invariance.py`, `g2.py`, `prep_quality.py`, `fp16_check.py` (T17).
- **Lệnh** `cvmatch eval …`: `ablation`, `split`, `kappa`, `pool`, `calibrate`, `invariance`, `g2`, `prep-sample`, `prep-score`, `fp16` (thêm `--kb-version`, `--fake-encoder`).
- **Kế hoạch** `services/cvmatch-ai/experiments/`: `retrieve_RT.yaml` (RT-E1…E6, RT-E2 RRF có trọng số — thêm `retrieve.rrf_weighted`), `rerank_R.yaml` (R-A0, P1, R-E1…E14, P2-full, R-X*), `reverse_RT_R.yaml` (RT-R1…R5, T16). Mục `todo` ghi lý do: R-E3 (engine Rerank chỉ có S2 + Recall), R-E5-label (chờ `eval calibrate`), R-E12 cổng cứng (hợp đồng chỉ có trần 50/70/100), R-E14 (engine chưa có IDF), RT-E7 (đổi model → reprocess `--from A10` vào DB riêng), RT-E8 (view sparse chưa làm), R-X1/R-X4 (T17).
- **Đã chạy trên GPU (bge-m3 thật, KB `kb-2026-11-21-4`, 34 CV / 3 JD tổng hợp)**: `reports/ablation/*_e2e_gpu/`. R-A0 nDCG@10 0,942 · P1 0,971 · P2-full 0,960 · R-E2 cosine 0,949. Nhãn suy từ vai trò, chỉ 3 JD → CI rất rộng, **không dùng để kết luận**. Retrieve / Luồng D: Recall = 1 ở mọi cấu hình (kho quá nhỏ).
- **G2** (`reports/g2_gpu.md`): T04, T05, T06, T08, F05 đạt; T11, T19 ghi nhận. Bản trần tái tạo đúng file 10 (T04 +28,7%, T08 +29,1% span).
- **Bất biến** (`reports/invariance_gpu.md`): họ tên, giới tính, trường, năm sinh/tốt nghiệp, thứ tự → Δ = 0 trên 102 cặp mỗi loại. Bỏ dấu: 97% có cờ `no_diacritics` — CV còn lại không có gạch (4 âm tiết < `min_syllables` 20), B4 vốn đã thiếu phía CV.
- **Giả định**: "fresher/có kinh nghiệm" tách bằng file nhóm (`--groups`) do người dùng cấp; pooling không kèm mô tả cho người chấm (cột `note` để trống); mẫu kiểm tiền xử lý dùng `anon_json` / `norm_json` (đã ẩn danh).
- **Test:** `tests/unit/test_eval_metrics.py` (tính tay), `tests/integration/test_evaluation_db.py`.
