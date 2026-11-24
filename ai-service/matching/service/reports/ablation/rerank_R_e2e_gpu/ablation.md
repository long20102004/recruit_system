# Ablation `R-E` (jd_to_cv, rerank)

- 3 truy vấn · chỉ số chính **ndcg@10** · phù hợp = nhãn ≥ 1 · mốc bootstrap: `P1` (CI 95%, ghép cặp theo truy vấn)

| Cấu hình | Mô tả | ndcg@10 | recall@30 | recall@30_norm | Δ vs mốc [CI 95%] | tệ nhất | ms/truy vấn | chưa chấm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-A0 | top 30 theo fused cua Retrieve (khong rerank) | 0.942 | 1.000 | 1.000 | -0.028 [-0.052; +0.000] | 0.879 (E2E-DATA) | 16 | 0.00 |
| P1 | rr-1.0 (A1=s_skill, B4, B1, B2) | 0.971 | 1.000 | 1.000 | mốc | 0.912 (E2E-DATA) | 329 | 0.00 |
| R-E1 | + A1, A2 qua KB | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 85 | 0.00 |
| R-E2-cos | B4 = cosine cau hieu chuan (thay BERTScore) | 0.949 | 1.000 | 1.000 | -0.022 [-0.065; +0.000] | 0.847 (E2E-DATA) | 45 | 0.00 |
| R-E3 | chia S1/S3; Precision/F1 | – | – | – | todo: engine Rerank chi co S2 + Recall; S1/S3, P/F1 moi co o golden (eval golden) | – | – | – |
| R-E4-L16 | BERTScore layer 16 | 0.960 | 1.000 | 1.000 | -0.011 [-0.033; +0.000] | 0.879 (E2E-DATA) | 238 | 0.00 |
| R-E4-L20 | BERTScore layer 20 | 0.960 | 1.000 | 1.000 | -0.011 [-0.033; +0.000] | 0.879 (E2E-DATA) | 254 | 0.00 |
| R-E5-label | lo/hi theo nhan (cvmatch eval calibrate) | – | – | – | todo: chay eval calibrate tren tap 300 cap roi dien lo/hi vao day | – | – | – |
| R-E6-off | tat he so phu dinh / hoc tap | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 76 | 0.00 |
| R-E6-drop | loai han gach phu dinh / hoc tap | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 79 | 0.00 |
| R-E7 | trach nhiem chung chung trong so 0,3 | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 99 | 0.00 |
| R-E8-nomask | tat che so | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 269 | 0.00 |
| R-E8-noalias | tat doi alias | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 258 | 0.00 |
| R-E9 | + B5 (yeu cau dang chu) | 0.960 | 1.000 | 1.000 | -0.010 [-0.030; +0.000] | 0.881 (E2E-DATA) | 173 | 0.00 |
| R-E10 | c_j = max(BERTScore, cosine cau) | 0.960 | 1.000 | 1.000 | -0.011 [-0.033; +0.000] | 0.879 (E2E-DATA) | 81 | 0.00 |
| R-E11-noB1 | bo B1 | 0.960 | 1.000 | 1.000 | -0.011 [-0.033; +0.000] | 0.879 (E2E-DATA) | 78 | 0.00 |
| R-E11-noB2 | bo B2 | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 76 | 0.00 |
| R-E11-nopen | B2 tat phat thua | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 89 | 0.00 |
| R-E11-B3 | + B3 (xem rho(B2, B3) trong log) | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 87 | 0.00 |
| R-E11-C1 | + C1 | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 74 | 0.00 |
| R-E12-nogate | khong cong must-have | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 77 | 0.00 |
| R-E12-hard | cong cung (loai CV thieu ky nang bat buoc) | – | – | – | todo: gate_cap chi nhan 50/70/100 trong hop dong; cong cung can them muc 0 | – | – | – |
| R-E12-drop | thieu phia CV -> bo feature | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 77 | 0.00 |
| R-E12-zero | thieu phia CV -> 0 | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 78 | 0.00 |
| R-E13-equal | trong so bang nhau | 0.971 | 1.000 | 1.000 | +0.000 [+0.000; +0.000] | 0.912 (E2E-DATA) | 75 | 0.00 |
| R-E14 | IDF bat | – | – | – | todo: engine BERTScore chua co IDF (bertscore.idf chi la khoa cache) | – | – | – |
| P2-full | rr-1.1 du 8 feature (T15) | 0.960 | 1.000 | 1.000 | -0.010 [-0.030; +0.000] | 0.881 (E2E-DATA) | 107 | 0.00 |
| R-X1 | cross-encoder bge-reranker-v2-m3 | – | – | – | todo: backend thay recall_matrix chua lam (T17) | – | – | – |
| R-X4 | + RR5 LLM kiem chung vung bien | – | – | – | todo: RR5 chua lam (T17) | – | – | – |

## ndcg@10 theo nhóm

| Cấu hình | Backend | Data | Frontend |
| --- | --- | --- | --- |
| R-A0 | 0.948 | 0.879 | 1.000 |
| P1 | 1.000 | 0.912 | 1.000 |
| R-E1 | 1.000 | 0.912 | 1.000 |
| R-E2-cos | 1.000 | 0.847 | 1.000 |
| R-E4-L16 | 1.000 | 0.879 | 1.000 |
| R-E4-L20 | 1.000 | 0.879 | 1.000 |
| R-E6-off | 1.000 | 0.912 | 1.000 |
| R-E6-drop | 1.000 | 0.912 | 1.000 |
| R-E7 | 1.000 | 0.912 | 1.000 |
| R-E8-nomask | 1.000 | 0.912 | 1.000 |
| R-E8-noalias | 1.000 | 0.912 | 1.000 |
| R-E9 | 1.000 | 0.881 | 1.000 |
| R-E10 | 1.000 | 0.879 | 1.000 |
| R-E11-noB1 | 1.000 | 0.879 | 1.000 |
| R-E11-noB2 | 1.000 | 0.912 | 1.000 |
| R-E11-nopen | 1.000 | 0.912 | 1.000 |
| R-E11-B3 | 1.000 | 0.912 | 1.000 |
| R-E11-C1 | 1.000 | 0.912 | 1.000 |
| R-E12-nogate | 1.000 | 0.912 | 1.000 |
| R-E12-drop | 1.000 | 0.912 | 1.000 |
| R-E12-zero | 1.000 | 0.912 | 1.000 |
| R-E13-equal | 1.000 | 0.912 | 1.000 |
| P2-full | 1.000 | 0.881 | 1.000 |

`*`: khoảng tin cậy không chứa 0. Chênh nhỏ hơn khoảng tin cậy là nhiễu (thiết kế 09 mục 4.5).
Quy tắc chọn: cấu hình đơn giản nhất có chỉ số chính kém tốt nhất ≤ 1–2 điểm; thành phần chỉ giữ khi cải thiện vượt ngưỡng đặt trước.

Biểu đồ chi phí – chất lượng: `cost_quality.svg`.
