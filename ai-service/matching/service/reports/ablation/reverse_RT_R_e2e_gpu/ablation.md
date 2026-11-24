# Ablation `RT-R` (cv_to_jd, retrieve)

- 34 truy vấn · chỉ số chính **recall@10** · phù hợp = nhãn ≥ 1 · mốc bootstrap: `RT-R-base` (CI 95%, ghép cặp theo truy vấn)

| Cấu hình | Mô tả | recall@10 | recall@20 | recall@50 | Δ vs mốc [CI 95%] | tệ nhất | ms/truy vấn | chưa chấm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RT-R-base | mac dinh (4 view, condensed_cv, min_imp_sum 3, RRF khi < 10 JD) | 1.000 | 1.000 | 1.000 | mốc | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 10 | 0.00 |
| RT-R1-dense | Dense mot minh | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 7 | 0.00 |
| RT-R1-bm25 | BM25 mot minh | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 11 | 0.00 |
| RT-R2-full | BM25 voi full_cv | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 7 | 0.00 |
| RT-R3-0 | view ky nang khong co mau so toi thieu | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 10 | 0.00 |
| RT-R3-2 | min_imp_sum = 2 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 8 | 0.00 |
| RT-R3-5 | min_imp_sum = 5 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 8 | 0.00 |
| RT-R4-noresp | bo view trach nhiem | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 8 | 0.00 |
| RT-R5-minmax | luon min-max (khong doi sang RRF khi kho nho) | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 8 | 0.00 |
| RT-R5-rrf | luon RRF | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (0a788183-e4bc-4001-b239-46dab8e01a5f) | 9 | 0.00 |

`*`: khoảng tin cậy không chứa 0. Chênh nhỏ hơn khoảng tin cậy là nhiễu (thiết kế 09 mục 4.5).
Quy tắc chọn: cấu hình đơn giản nhất có chỉ số chính kém tốt nhất ≤ 1–2 điểm; thành phần chỉ giữ khi cải thiện vượt ngưỡng đặt trước.

Biểu đồ chi phí – chất lượng: `cost_quality.svg`.
