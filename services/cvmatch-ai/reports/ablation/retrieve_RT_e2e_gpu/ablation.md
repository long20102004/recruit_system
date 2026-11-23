# Ablation `RT-E` (jd_to_cv, retrieve)

- 3 truy vấn · chỉ số chính **recall@200** · phù hợp = nhãn ≥ 1 · mốc bootstrap: `RT-E4` (CI 95%, ghép cặp theo truy vấn)

| Cấu hình | Mô tả | recall@200 | recall@50 | recall@100 | recall@300 | Δ vs mốc [CI 95%] | tệ nhất | ms/truy vấn | chưa chấm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RT-E1-bm25 | BM25 mot minh | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (E2E-DATA) | 14 | 0.00 |
| RT-E1-dense | Dense mot minh | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (E2E-DATA) | 14 | 0.00 |
| RT-E2-sum | BM25 + Dense, cong diem minmax | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (E2E-DATA) | 10 | 0.00 |
| RT-E2-rrf | BM25 + Dense, RRF | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (E2E-DATA) | 10 | 0.00 |
| RT-E2-rrfw | BM25 + Dense, RRF co trong so (dense 1,5) | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (E2E-DATA) | 10 | 0.00 |
| RT-E3 | RT-E2 + view ky nang | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (E2E-DATA) | 12 | 0.00 |
| RT-E4 | RT-E3 + view trach nhiem (cau hinh mac dinh) | 1.000 | 1.000 | 1.000 | 1.000 | mốc | 1.000 (E2E-DATA) | 13 | 0.00 |
| RT-E4-cal | RT-E4, view trach nhiem hieu chuan lo/hi (T15) | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (E2E-DATA) | 13 | 0.00 |
| RT-E5 | BM25 truy van chi chuc danh + ky nang | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (E2E-DATA) | 37 | 0.00 |
| RT-E6 | DBSF thay min-max | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 1.000 (E2E-DATA) | 14 | 0.00 |
| RT-E7 | model dense khac (multilingual-e5, Qwen3-Embedding, Vietnamese_Embedding_v2) | – | – | – | – | todo: doi models.embed -> phai nap lai kho (cvmatch reprocess cv --from A10) vao DB rieng roi chay ke hoach tren DB do | – | – | – |
| RT-E8 | them bge-m3 sparse vao view BM25 | – | – | – | – | todo: view sparse chua lam (cv_vector.sparse da luu) | – | – | – |

`*`: khoảng tin cậy không chứa 0. Chênh nhỏ hơn khoảng tin cậy là nhiễu (thiết kế 09 mục 4.5).
Quy tắc chọn: cấu hình đơn giản nhất có chỉ số chính kém tốt nhất ≤ 1–2 điểm; thành phần chỉ giữ khi cải thiện vượt ngưỡng đặt trước.

Biểu đồ chi phí – chất lượng: `cost_quality.svg`.
