# Chạy trọn JD → giải thích (run-e2e)

- Phiên bản: `kb-2026-11-21-4` · `prep-1.1` · `bge-m3@5617a9f61b` · `bge-m3@5617a9f61b/L24/noidf/norescale/2048/mask1/alias1/text_raw/fp32` · `rr-1.0`
- CV: {'ok': 34} · JD: E2E-DATA ok, E2E-FE ok, E2E-JAVA ok
- Thời gian (s): migrate_s 0.2925, kb_import_s 0.2189, services.load_encoder_s 16.2002, services.index_build_s 0.0088, services.jd_index_build_s 0.0075, ingest_cv_s 7.0151, ingest_jd_s 0.681
- Bộ nhớ: {'rss_mb': 1465.9, 'gpu_max_allocated_mb': 2299.3, 'index_mb': {'doc': 0.06640625, 'bullet': 0.263671875, 'skill': 0.001888275146484375, 'bm25': 0.010906219482421875}}
- Log: `D:\MyProjects\recruit_system\ai\cvmatch\reports\e2e\20261123-152218\run.jsonl`

## E2E-DATA v1

rerank run `8fb3e178-d6e1-4d1b-8878-89de0d7b4866` · retrieve run `9a06bc37-9056-499e-86b0-e4a0bd05a8d8` · pool 34 CV · retrieve 0.0437s · rerank 0.5887s (BERTScore 0s) · explain top 5 0.2144s
- cảnh báo: Văn bản truy vấn chỉ 47 từ: chất lượng match thấp

### Top sau Rerank

| Hạng | Điểm | Dải | Trần | CV | Cờ |
| --- | --- | --- | --- | --- | --- |
| 1 | 94 | high |  | cv_22_data.json |  |
| 2 | 94 | high |  | cv_25_data.json |  |
| 3 | 92 | high |  | cv_23_data.json |  |
| 4 | 79 | mid |  | cv_24_data.json |  |
| 5 | 25 | low |  | cv_02_java.json |  |
| 6 | 25 | low |  | cv_00_java.json |  |
| 7 | 25 | low |  | cv_03_java.json |  |
| 8 | 25 | low |  | cv_04_java.json |  |
| 9 | 22 | low |  | cv_07_python.json |  |
| 10 | 22 | low |  | cv_08_python.json |  |
| 11 | 21 | low |  | cv_27_devops.json |  |
| 12 | 20 | low |  | cv_26_devops.json |  |
| 13 | 20 | low |  | cv_28_devops.json |  |
| 14 | 20 | low |  | cv_09_python.json |  |
| 15 | 20 | low |  | cv_10_python.json |  |
| 16 | 18 | low |  | cv_05_java.json |  |
| 17 | 18 | low |  | cv_29_qa.json |  |
| 18 | 18 | low |  | cv_31_qa.json |  |
| 19 | 18 | low |  | cv_30_qa.json |  |
| 20 | 18 | low |  | cv_06_java.json |  |
| 21 | 15 | low |  | cv_01_java.json |  |
| 22 | 15 | low |  | cv_17_fullstack.json |  |
| 23 | 15 | low |  | cv_16_fullstack.json |  |
| 24 | 8 | low |  | cv_15_frontend.json |  |
| 25 | 8 | low |  | cv_13_frontend.json |  |
| 26 | 8 | low |  | cv_12_frontend.json |  |
| 27 | 8 | low |  | cv_14_frontend.json |  |
| 28 | 8 | low |  | cv_11_frontend.json |  |
| 29 | 8 | low |  | cv_18_fullstack.json |  |
| 30 | 7 | low |  | cv_20_mobile.json |  |

### R-A0: top theo `fused` của Retrieve (không rerank)

| Hạng fused | fused | dense | bm25 | skill | resp | CV | Hạng rerank | Điểm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.000 | 0.881 | 44.488 | 0.900 | 0.860 | cv_22_data.json | 1 | 94 |
| 2 | 0.966 | 0.866 | 44.494 | 0.850 | 0.845 | cv_23_data.json | 3 | 92 |
| 3 | 0.919 | 0.832 | 42.950 | 0.900 | 0.802 | cv_25_data.json | 2 | 94 |
| 4 | 0.862 | 0.844 | 40.911 | 0.700 | 0.806 | cv_24_data.json | 4 | 79 |
| 5 | 0.309 | 0.667 | 15.096 | 0.250 | 0.575 | cv_27_devops.json | 11 | 21 |
| 6 | 0.294 | 0.665 | 10.198 | 0.250 | 0.596 | cv_31_qa.json | 18 | 18 |
| 7 | 0.284 | 0.649 | 10.237 | 0.250 | 0.596 | cv_30_qa.json | 19 | 18 |
| 8 | 0.281 | 0.650 | 12.048 | 0.250 | 0.577 | cv_26_devops.json | 12 | 20 |
| 9 | 0.249 | 0.643 | 9.840 | 0.250 | 0.555 | cv_29_qa.json | 17 | 18 |
| 10 | 0.246 | 0.643 | 10.029 | 0.200 | 0.569 | cv_07_python.json | 9 | 22 |
| 11 | 0.239 | 0.597 | 10.985 | 0.250 | 0.576 | cv_03_java.json | 7 | 25 |
| 12 | 0.237 | 0.624 | 10.980 | 0.250 | 0.546 | cv_28_devops.json | 13 | 20 |
| 13 | 0.233 | 0.610 | 6.396 | 0.250 | 0.593 | cv_02_java.json | 5 | 25 |
| 14 | 0.220 | 0.630 | 10.274 | 0.150 | 0.563 | cv_10_python.json | 15 | 20 |
| 15 | 0.216 | 0.628 | 9.843 | 0.200 | 0.542 | cv_08_python.json | 10 | 22 |
| 16 | 0.200 | 0.616 | 9.404 | 0.150 | 0.554 | cv_09_python.json | 14 | 20 |
| 17 | 0.199 | 0.581 | 9.549 | 0.250 | 0.545 | cv_00_java.json | 6 | 25 |
| 18 | 0.176 | 0.570 | 6.901 | 0.250 | 0.545 | cv_04_java.json | 8 | 25 |
| 19 | 0.173 | 0.588 | 5.732 | 0.200 | 0.553 | cv_06_java.json | 20 | 18 |
| 20 | 0.166 | 0.620 | 2.861 | 0.150 | – | cv_05_java.json | 16 | 18 |
| 21 | 0.147 | 0.574 | 8.268 | 0.000 | 0.588 | cv_17_fullstack.json | 22 | 15 |
| 22 | 0.125 | 0.578 | 6.365 | 0.150 | 0.508 | cv_01_java.json | 21 | 15 |
| 23 | 0.118 | 0.564 | 3.429 | 0.000 | 0.597 | cv_18_fullstack.json | 29 | 8 |
| 24 | 0.084 | 0.572 | 3.602 | 0.000 | 0.538 | cv_11_frontend.json | 28 | 8 |
| 25 | 0.063 | 0.539 | 4.473 | 0.000 | 0.532 | cv_16_fullstack.json | 23 | 15 |
| 26 | 0.062 | 0.532 | 3.490 | 0.000 | 0.547 | cv_14_frontend.json | 27 | 8 |
| 27 | 0.053 | 0.534 | 1.695 | 0.000 | 0.547 | cv_15_frontend.json | 24 | 8 |
| 28 | 0.042 | 0.532 | 2.997 | 0.000 | 0.522 | cv_13_frontend.json | 25 | 8 |
| 29 | 0.038 | 0.530 | 1.329 | 0.000 | 0.532 | cv_19_mobile.json | – | – |
| 30 | 0.029 | 0.530 | 2.013 | 0.000 | 0.513 | cv_12_frontend.json | 26 | 8 |

### Giải thích top 5

#### cv_22_data.json · 94 (high)

Điểm 94/100 (phù hợp cao, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 4/4 (AWS, Kafka, Python, SQL).
• Việc đã làm: 3/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Xây dựng pipeline ETL xử lý dữ liệu lớn" ← "Xây dựng pipeline ETL xử lý hàng triệu bản ghi mỗi ngày bằng Python"  (khớp: Xây dựng, pipeline, ETL, xử lý; chưa thấy phần: dữ liệu lớn, dữ liệu lớn)
  – "Xử lý dữ liệu luồng thời gian thực" ← "Xử lý dữ liệu luồng thời gian thực với Kafka"  (khớp: Xử lý, dữ liệu, luồng, thời gian, thực)
  – "Thiết kế kho dữ liệu phục vụ báo cáo" ← "Thiết kế kho dữ liệu và các bảng tổng hợp phục vụ báo cáo"  (khớp: Thiết kế, kho dữ liệu, kho dữ liệu, phục vụ, báo cáo)
• Kinh nghiệm liên quan: 8,3 năm, nhóm Data.

Chưa thấy bằng chứng
• Không có mục nào nổi bật.


#### cv_25_data.json · 94 (high)

Điểm 94/100 (phù hợp cao, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 4/4 (AWS, Kafka, Python, SQL).
• Việc đã làm: 3/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Xây dựng pipeline ETL xử lý dữ liệu lớn" ← "Xây dựng pipeline ETL xử lý hàng triệu bản ghi mỗi ngày bằng Python"  (khớp: Xây dựng, pipeline, ETL, xử lý; chưa thấy phần: dữ liệu lớn, dữ liệu lớn)
  – "Xử lý dữ liệu luồng thời gian thực" ← "Xử lý dữ liệu luồng thời gian thực với Kafka"  (khớp: Xử lý, dữ liệu, luồng, thời gian, thực)
  – "Thiết kế kho dữ liệu phục vụ báo cáo" ← "Thiết kế kho dữ liệu và các bảng tổng hợp phục vụ báo cáo"  (khớp: Thiết kế, kho dữ liệu, kho dữ liệu, phục vụ, báo cáo)
• Kinh nghiệm liên quan: 3,2 năm, nhóm Data.

Chưa thấy bằng chứng
• Không có mục nào nổi bật.


#### cv_23_data.json · 92 (high)

Điểm 92/100 (phù hợp cao, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 4/4 (AWS, Kafka, Python, SQL).
• Việc đã làm: 3/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Xây dựng pipeline ETL xử lý dữ liệu lớn" ← "Xây dựng pipeline ETL xử lý hàng triệu bản ghi mỗi ngày bằng Python"  (khớp: Xây dựng, pipeline, ETL, xử lý; chưa thấy phần: dữ liệu lớn, dữ liệu lớn)
  – "Xử lý dữ liệu luồng thời gian thực" ← "Xử lý dữ liệu luồng thời gian thực với Kafka"  (khớp: Xử lý, dữ liệu, luồng, thời gian, thực)
  – "Thiết kế kho dữ liệu phục vụ báo cáo" ← "Thiết kế kho dữ liệu và các bảng tổng hợp phục vụ báo cáo"  (khớp: Thiết kế, kho dữ liệu, kho dữ liệu, phục vụ, báo cáo)
• Kinh nghiệm liên quan: 12,2 năm, nhóm Data.

Chưa thấy bằng chứng
• Không có mục nào nổi bật.


#### cv_24_data.json · 79 (mid)

Điểm 79/100 (cân nhắc, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/4 (Kafka, Python, SQL).
• Việc đã làm: 3/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Xây dựng pipeline ETL xử lý dữ liệu lớn" ← "Xây dựng pipeline ETL xử lý hàng triệu bản ghi mỗi ngày bằng Python"  (khớp: Xây dựng, pipeline, ETL, xử lý; chưa thấy phần: dữ liệu lớn, dữ liệu lớn)
  – "Xử lý dữ liệu luồng thời gian thực" ← "Xử lý dữ liệu luồng thời gian thực với Kafka"  (khớp: Xử lý, dữ liệu, luồng, thời gian, thực)
  – "Thiết kế kho dữ liệu phục vụ báo cáo" ← "Thiết kế kho dữ liệu và các bảng tổng hợp phục vụ báo cáo"  (khớp: Thiết kế, kho dữ liệu, kho dữ liệu, phục vụ, báo cáo)
• Kinh nghiệm liên quan: 1,3 năm, nhóm Data.

Chưa thấy bằng chứng
• Kỹ năng: chưa thấy bằng chứng về AWS trong CV.

Gợi ý câu hỏi phỏng vấn
• Anh/chị đã từng làm việc với AWS chưa? Hãy kể một ví dụ cụ thể.


#### cv_02_java.json · 25 (low)

Điểm 25/100 (thấp, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 1/4 (Kafka).
• Kỹ năng liên quan: PostgreSQL (gần với SQL).
• Việc đã làm: 0/3 trách nhiệm có bằng chứng.
• Kinh nghiệm liên quan: 0 năm, nhóm Backend.

Chưa thấy bằng chứng
• Kỹ năng: chưa thấy bằng chứng về AWS, Python trong CV.
• Trách nhiệm: chưa thấy bằng chứng về "Xây dựng pipeline ETL xử lý dữ liệu lớn" trong CV.
• Trách nhiệm: "Xử lý dữ liệu luồng thời gian thực" mới có bằng chứng một phần (chưa thấy phần: dữ liệu, thời gian, thực).
• Trách nhiệm: "Thiết kế kho dữ liệu phục vụ báo cáo" mới có bằng chứng một phần (chưa thấy phần: kho dữ liệu, kho dữ liệu, phục vụ, báo cáo).

Gợi ý câu hỏi phỏng vấn
• Anh/chị đã từng xử lý dữ liệu luồng thời gian thực chưa? Hãy kể một ví dụ cụ thể.
• Anh/chị đã từng thiết kế kho dữ liệu phục vụ báo cáo chưa? Hãy kể một ví dụ cụ thể.
• Anh/chị đã từng xây dựng pipeline ETL xử lý dữ liệu lớn chưa? Hãy kể một ví dụ cụ thể.



## E2E-FE v1

rerank run `bdb9f97e-4d7f-48ba-a0d0-e10c141a35c0` · retrieve run `c7ce4e5c-b8bc-4c04-80f0-6adb99e4ed3e` · pool 34 CV · retrieve 0.0258s · rerank 0.1364s (BERTScore 0s) · explain top 5 0.2025s
- cảnh báo: Văn bản truy vấn chỉ 47 từ: chất lượng match thấp

### Top sau Rerank

| Hạng | Điểm | Dải | Trần | CV | Cờ |
| --- | --- | --- | --- | --- | --- |
| 1 | 92 | high |  | cv_13_frontend.json |  |
| 2 | 92 | high |  | cv_14_frontend.json | location_mismatch |
| 3 | 90 | high |  | cv_11_frontend.json | location_mismatch |
| 4 | 81 | high |  | cv_15_frontend.json | location_mismatch |
| 5 | 72 | mid |  | cv_12_frontend.json | location_mismatch |
| 6 | 68 | mid |  | cv_18_fullstack.json | location_mismatch |
| 7 | 56 | low |  | cv_16_fullstack.json |  |
| 8 | 49 | low |  | cv_17_fullstack.json | location_mismatch |
| 9 | 17 | low |  | cv_19_mobile.json |  |
| 10 | 17 | low |  | cv_21_mobile.json | location_mismatch |
| 11 | 17 | low |  | cv_04_java.json |  |
| 12 | 16 | low |  | cv_20_mobile.json | location_mismatch |
| 13 | 16 | low |  | cv_02_java.json | location_mismatch |
| 14 | 15 | low |  | cv_06_java.json | location_mismatch |
| 15 | 13 | low |  | cv_05_java.json | location_mismatch |
| 16 | 13 | low |  | cv_07_python.json |  |
| 17 | 13 | low |  | cv_09_python.json | location_mismatch |
| 18 | 13 | low |  | cv_08_python.json | location_mismatch |
| 19 | 13 | low |  | cv_10_python.json |  |
| 20 | 13 | low |  | cv_00_java.json | location_mismatch |
| 21 | 13 | low |  | cv_29_qa.json | location_mismatch |
| 22 | 13 | low |  | cv_31_qa.json |  |
| 23 | 13 | low |  | cv_30_qa.json | location_mismatch |
| 24 | 13 | low |  | cv_03_java.json | location_mismatch |
| 25 | 11 | low |  | cv_01_java.json |  |
| 26 | 11 | low |  | cv_27_devops.json | location_mismatch |
| 27 | 10 | low |  | cv_32_designer.json | location_mismatch |
| 28 | 10 | low |  | cv_33_designer.json | location_mismatch |
| 29 | 8 | low |  | cv_26_devops.json | location_mismatch |
| 30 | 8 | low |  | cv_28_devops.json |  |

### R-A0: top theo `fused` của Retrieve (không rerank)

| Hạng fused | fused | dense | bm25 | skill | resp | CV | Hạng rerank | Điểm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.987 | 0.856 | 40.680 | 0.926 | 0.807 | cv_14_frontend.json | 2 | 92 |
| 2 | 0.962 | 0.844 | 42.835 | 0.926 | 0.769 | cv_13_frontend.json | 1 | 92 |
| 3 | 0.939 | 0.832 | 41.863 | 0.852 | 0.784 | cv_11_frontend.json | 3 | 90 |
| 4 | 0.825 | 0.789 | 37.468 | 0.748 | 0.749 | cv_15_frontend.json | 4 | 81 |
| 5 | 0.802 | 0.839 | 33.059 | 0.726 | 0.709 | cv_12_frontend.json | 5 | 72 |
| 6 | 0.594 | 0.739 | 17.896 | 0.667 | 0.676 | cv_18_fullstack.json | 6 | 68 |
| 7 | 0.548 | 0.717 | 18.674 | 0.593 | 0.658 | cv_16_fullstack.json | 7 | 56 |
| 8 | 0.398 | 0.695 | 12.913 | 0.519 | 0.554 | cv_17_fullstack.json | 8 | 49 |
| 9 | 0.289 | 0.696 | 9.096 | 0.000 | 0.624 | cv_02_java.json | 13 | 16 |
| 10 | 0.255 | 0.678 | 9.440 | 0.000 | 0.595 | cv_04_java.json | 11 | 17 |
| 11 | 0.226 | 0.639 | 5.049 | 0.000 | 0.631 | cv_19_mobile.json | 9 | 17 |
| 12 | 0.222 | 0.674 | 5.567 | 0.000 | 0.586 | cv_10_python.json | 19 | 13 |
| 13 | 0.219 | 0.682 | 5.248 | 0.000 | 0.576 | cv_08_python.json | 18 | 13 |
| 14 | 0.218 | 0.654 | 5.425 | 0.000 | 0.602 | cv_20_mobile.json | 12 | 16 |
| 15 | 0.216 | 0.652 | 5.260 | 0.000 | 0.603 | cv_21_mobile.json | 10 | 17 |
| 16 | 0.200 | 0.621 | 8.950 | 0.000 | 0.585 | cv_03_java.json | 24 | 13 |
| 17 | 0.197 | 0.646 | 5.078 | 0.000 | 0.584 | cv_09_python.json | 17 | 13 |
| 18 | 0.192 | 0.641 | 7.356 | 0.000 | 0.566 | cv_00_java.json | 20 | 13 |
| 19 | 0.191 | 0.664 | 5.447 | 0.000 | 0.555 | cv_06_java.json | 14 | 15 |
| 20 | 0.178 | 0.625 | 4.637 | 0.000 | 0.584 | cv_07_python.json | 16 | 13 |
| 21 | 0.148 | 0.593 | 3.530 | 0.000 | 0.586 | cv_27_devops.json | 26 | 11 |
| 22 | 0.132 | 0.633 | 1.660 | 0.000 | 0.539 | cv_01_java.json | 25 | 11 |
| 23 | 0.124 | 0.576 | 3.080 | 0.000 | 0.575 | cv_22_data.json | – | – |
| 24 | 0.118 | 0.588 | 2.994 | 0.000 | 0.556 | cv_25_data.json | – | – |
| 25 | 0.117 | 0.646 | 0.725 | 0.000 | – | cv_05_java.json | 15 | 13 |
| 26 | 0.110 | 0.593 | 0.871 | 0.000 | 0.557 | cv_31_qa.json | 22 | 13 |
| 27 | 0.108 | 0.590 | 0.869 | 0.000 | 0.557 | cv_30_qa.json | 23 | 13 |
| 28 | 0.102 | 0.593 | 2.418 | 0.000 | 0.535 | cv_32_designer.json | 27 | 10 |
| 29 | 0.102 | 0.586 | 0.750 | 0.000 | 0.555 | cv_29_qa.json | 21 | 13 |
| 30 | 0.102 | 0.586 | 2.418 | 0.000 | 0.541 | cv_33_designer.json | 28 | 10 |

### Giải thích top 5

#### cv_13_frontend.json · 92 (high)

Điểm 92/100 (phù hợp cao, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (javascript, React, TypeScript).
• Việc đã làm: 3/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Xây dựng giao diện quản trị bằng React" ← "Xây dựng giao diện trang quản trị bằng React và TypeScript"  (khớp: Xây dựng, giao diện, quản trị, React)
  – "Tối ưu tốc độ tải trang và trải nghiệm người dùng" ← "Tối ưu tốc độ tải trang, cải thiện điểm Lighthouse từ 60 lên 90"  (khớp: Tối ưu, tốc độ, tải, trang; chưa thấy phần: trải, nghiệm, người, dùng)
  – "Phát triển các component dùng chung" ← "Phát triển thư viện component dùng chung cho nhiều dự án"  (khớp: Phát triển, component, dùng, chung)
• Kinh nghiệm liên quan: 3,5 năm, nhóm Frontend.

Chưa thấy bằng chứng
• Không có mục nào nổi bật.


#### cv_14_frontend.json · 92 (high)

Điểm 92/100 (phù hợp cao, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (javascript, React, TypeScript).
• Việc đã làm: 3/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Xây dựng giao diện quản trị bằng React" ← "Xây dựng giao diện trang quản trị bằng React và TypeScript"  (khớp: Xây dựng, giao diện, quản trị, React)
  – "Tối ưu tốc độ tải trang và trải nghiệm người dùng" ← "Tối ưu tốc độ tải trang, cải thiện điểm Lighthouse từ 60 lên 90"  (khớp: Tối ưu, tốc độ, tải, trang; chưa thấy phần: trải, nghiệm, người, dùng)
  – "Phát triển các component dùng chung" ← "Phát triển thư viện component dùng chung cho nhiều dự án"  (khớp: Phát triển, component, dùng, chung)
• Kinh nghiệm liên quan: 8,2 năm, nhóm Frontend.

Chưa thấy bằng chứng
• Không có mục nào nổi bật.

Lưu ý
• Địa điểm làm việc khác với JD.


#### cv_11_frontend.json · 90 (high)

Điểm 90/100 (phù hợp cao, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (javascript, React, TypeScript).
• Việc đã làm: 3/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Xây dựng giao diện quản trị bằng React" ← "Xây dựng giao diện trang quản trị bằng React và TypeScript"  (khớp: Xây dựng, giao diện, quản trị, React)
  – "Tối ưu tốc độ tải trang và trải nghiệm người dùng" ← "Tối ưu tốc độ tải trang, cải thiện điểm Lighthouse từ 60 lên 90"  (khớp: Tối ưu, tốc độ, tải, trang; chưa thấy phần: trải, nghiệm, người, dùng)
  – "Phát triển các component dùng chung" ← "Phát triển thư viện component dùng chung cho nhiều dự án"  (khớp: Phát triển, component, dùng, chung)
• Kinh nghiệm liên quan: 12,5 năm, nhóm Frontend.

Chưa thấy bằng chứng
• Không có mục nào nổi bật.

Lưu ý
• Địa điểm làm việc khác với JD.


#### cv_15_frontend.json · 81 (high)

Điểm 81/100 (phù hợp cao, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (javascript, React, TypeScript).
• Việc đã làm: 2/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Tối ưu tốc độ tải trang và trải nghiệm người dùng" ← "Tối ưu tốc độ tải trang, cải thiện điểm Lighthouse từ 60 lên 90"  (khớp: Tối ưu, tốc độ, tải, trang; chưa thấy phần: trải, nghiệm, người, dùng)
  – "Phát triển các component dùng chung" ← "Phát triển thư viện component dùng chung cho nhiều dự án"  (khớp: Phát triển, component, dùng, chung)
• Kinh nghiệm liên quan: 12,2 năm, nhóm Frontend.

Chưa thấy bằng chứng
• Trách nhiệm: "Xây dựng giao diện quản trị bằng React" mới có bằng chứng một phần (chưa thấy phần: Xây dựng, quản trị, React).

Lưu ý
• Địa điểm làm việc khác với JD.

Gợi ý câu hỏi phỏng vấn
• Anh/chị đã từng xây dựng giao diện quản trị bằng React chưa? Hãy kể một ví dụ cụ thể.


#### cv_12_frontend.json · 72 (mid)

Điểm 72/100 (cân nhắc, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (javascript, React, TypeScript).
• Việc đã làm: 1/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Phát triển các component dùng chung" ← "Phát triển thư viện component dùng chung cho nhiều dự án"  (khớp: Phát triển, component, dùng, chung)
• Kinh nghiệm liên quan: 1,6 năm, nhóm Frontend.

Chưa thấy bằng chứng
• Trách nhiệm: "Xây dựng giao diện quản trị bằng React" mới có bằng chứng một phần (chưa thấy phần: Xây dựng, quản trị, React).
• Trách nhiệm: "Tối ưu tốc độ tải trang và trải nghiệm người dùng" mới có bằng chứng một phần (chưa thấy phần: Tối ưu, tốc độ, tải, trang, trải, nghiệm, người, dùng).

Lưu ý
• Địa điểm làm việc khác với JD.

Gợi ý câu hỏi phỏng vấn
• Anh/chị đã từng xây dựng giao diện quản trị bằng React chưa? Hãy kể một ví dụ cụ thể.
• Anh/chị đã từng tối ưu tốc độ tải trang và trải nghiệm người dùng chưa? Hãy kể một ví dụ cụ thể.



## E2E-JAVA v1

rerank run `45ad329f-2c0f-48f2-bb3f-82d3d2559ddc` · retrieve run `ffc83ead-47eb-4457-8a0c-6d1e27bcda3e` · pool 34 CV · retrieve 0.0288s · rerank 0.1366s (BERTScore 0s) · explain top 5 0.1632s

### Top sau Rerank

| Hạng | Điểm | Dải | Trần | CV | Cờ |
| --- | --- | --- | --- | --- | --- |
| 1 | 85 | high |  | cv_02_java.json | location_mismatch |
| 2 | 82 | high |  | cv_03_java.json |  |
| 3 | 78 | mid |  | cv_00_java.json |  |
| 4 | 74 | mid |  | cv_06_java.json |  |
| 5 | 74 | mid |  | cv_04_java.json | location_mismatch |
| 6 | 67 | mid |  | cv_01_java.json | location_mismatch |
| 7 | 62 | mid |  | cv_05_java.json | location_mismatch |
| 8 | 48 | low |  | cv_07_python.json | location_mismatch |
| 9 | 48 | low |  | cv_10_python.json | location_mismatch |
| 10 | 48 | low |  | cv_09_python.json |  |
| 11 | 45 | low |  | cv_18_fullstack.json |  |
| 12 | 39 | low |  | cv_08_python.json | location_mismatch |
| 13 | 34 | low |  | cv_17_fullstack.json | location_mismatch |
| 14 | 29 | low |  | cv_27_devops.json |  |
| 15 | 28 | low |  | cv_16_fullstack.json | location_mismatch |
| 16 | 27 | low |  | cv_19_mobile.json | location_mismatch |
| 17 | 27 | low |  | cv_21_mobile.json |  |
| 18 | 25 | low |  | cv_29_qa.json | location_mismatch |
| 19 | 25 | low |  | cv_31_qa.json | location_mismatch |
| 20 | 25 | low |  | cv_30_qa.json |  |
| 21 | 21 | low |  | cv_25_data.json | location_mismatch |
| 22 | 21 | low |  | cv_20_mobile.json | location_mismatch |
| 23 | 19 | low |  | cv_23_data.json | location_mismatch |
| 24 | 15 | low |  | cv_15_frontend.json |  |
| 25 | 15 | low |  | cv_13_frontend.json | location_mismatch |
| 26 | 15 | low |  | cv_14_frontend.json | location_mismatch |
| 27 | 15 | low |  | cv_11_frontend.json | location_mismatch |
| 28 | 14 | low |  | cv_22_data.json | location_mismatch |
| 29 | 14 | low |  | cv_24_data.json |  |
| 30 | 12 | low |  | cv_26_devops.json | location_mismatch |

### R-A0: top theo `fused` của Retrieve (không rerank)

| Hạng fused | fused | dense | bm25 | skill | resp | CV | Hạng rerank | Điểm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.958 | 0.772 | 38.884 | 0.874 | 0.740 | cv_02_java.json | 1 | 85 |
| 2 | 0.920 | 0.744 | 38.763 | 0.704 | 0.791 | cv_03_java.json | 2 | 82 |
| 3 | 0.859 | 0.727 | 37.326 | 0.778 | 0.724 | cv_00_java.json | 3 | 78 |
| 4 | 0.858 | 0.734 | 36.426 | 0.800 | 0.714 | cv_04_java.json | 5 | 74 |
| 5 | 0.743 | 0.736 | 27.759 | 0.852 | 0.626 | cv_06_java.json | 4 | 74 |
| 6 | 0.723 | 0.742 | 19.475 | 0.726 | – | cv_05_java.json | 7 | 62 |
| 7 | 0.714 | 0.738 | 27.629 | 0.778 | 0.615 | cv_01_java.json | 6 | 67 |
| 8 | 0.498 | 0.701 | 13.574 | 0.296 | 0.685 | cv_19_mobile.json | 16 | 27 |
| 9 | 0.442 | 0.701 | 10.717 | 0.296 | 0.641 | cv_31_qa.json | 19 | 25 |
| 10 | 0.428 | 0.686 | 15.010 | 0.000 | 0.710 | cv_07_python.json | 8 | 48 |
| 11 | 0.426 | 0.753 | 8.853 | 0.000 | 0.675 | cv_11_frontend.json | 27 | 15 |
| 12 | 0.403 | 0.754 | 7.446 | 0.000 | 0.656 | cv_15_frontend.json | 24 | 15 |
| 13 | 0.396 | 0.664 | 15.290 | 0.156 | 0.643 | cv_23_data.json | 23 | 19 |
| 14 | 0.388 | 0.654 | 10.334 | 0.296 | 0.639 | cv_21_mobile.json | 17 | 27 |
| 15 | 0.387 | 0.684 | 9.631 | 0.259 | 0.617 | cv_17_fullstack.json | 13 | 34 |
| 16 | 0.373 | 0.673 | 12.756 | 0.000 | 0.679 | cv_09_python.json | 10 | 48 |
| 17 | 0.370 | 0.678 | 9.950 | 0.259 | 0.603 | cv_18_fullstack.json | 11 | 45 |
| 18 | 0.366 | 0.665 | 8.451 | 0.296 | 0.613 | cv_29_qa.json | 18 | 25 |
| 19 | 0.351 | 0.660 | 11.405 | 0.207 | 0.608 | cv_25_data.json | 21 | 21 |
| 20 | 0.343 | 0.723 | 5.211 | 0.000 | 0.642 | cv_13_frontend.json | 25 | 15 |
| 21 | 0.322 | 0.633 | 13.117 | 0.000 | 0.665 | cv_10_python.json | 9 | 48 |
| 22 | 0.319 | 0.637 | 8.067 | 0.296 | 0.596 | cv_30_qa.json | 20 | 25 |
| 23 | 0.306 | 0.691 | 5.530 | 0.000 | 0.635 | cv_14_frontend.json | 26 | 15 |
| 24 | 0.281 | 0.634 | 12.338 | 0.000 | 0.622 | cv_08_python.json | 12 | 39 |
| 25 | 0.278 | 0.661 | 12.288 | 0.000 | 0.582 | cv_27_devops.json | 14 | 29 |
| 26 | 0.265 | 0.700 | 3.598 | 0.000 | 0.591 | cv_12_frontend.json | – | – |
| 27 | 0.249 | 0.637 | 5.721 | 0.207 | 0.561 | cv_16_fullstack.json | 15 | 28 |
| 28 | 0.246 | 0.618 | 9.286 | 0.222 | 0.546 | cv_20_mobile.json | 22 | 21 |
| 29 | 0.213 | 0.607 | 9.815 | 0.000 | 0.594 | cv_22_data.json | 28 | 14 |
| 30 | 0.190 | 0.608 | 9.451 | 0.000 | 0.567 | cv_24_data.json | 29 | 14 |

### Giải thích top 5

#### cv_02_java.json · 85 (high)

Điểm 85/100 (phù hợp cao, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (java, Spring Boot, PostgreSQL).
• Việc đã làm: 2/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Thiết kế và phát triển API cho hệ thống thanh toán" ← "Thiết kế và phát triển REST API cho hệ thống thanh toán bằng Spring Boot."  (khớp: Thiết kế, phát triển, API, hệ thống, thanh toán)
  – "Xây dựng luồng xử lý sự kiện bất đồng bộ cho đơn hàng" ← "Xây dựng luồng xử lý sự kiện bất đồng bộ với Kafka cho đơn hàng"  (khớp: Xây dựng, luồng, xử lý sự kiện, bất đồng bộ, đơn, hàng)
• Kinh nghiệm liên quan: 8,5 năm, nhóm Backend.

Chưa thấy bằng chứng
• Trách nhiệm: chưa thấy bằng chứng về "Tối ưu hiệu năng truy vấn cơ sở dữ liệu" trong CV.

Lưu ý
• Địa điểm làm việc khác với JD.

Gợi ý câu hỏi phỏng vấn
• Anh/chị đã từng tối ưu hiệu năng truy vấn cơ sở dữ liệu chưa? Hãy kể một ví dụ cụ thể.


#### cv_03_java.json · 82 (high)

Điểm 82/100 (phù hợp cao, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (java, Spring Boot, PostgreSQL).
• Việc đã làm: 2/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Tối ưu hiệu năng truy vấn cơ sở dữ liệu" ← "Tối ưu hiệu năng truy vấn cơ sở dữ liệu PostgreSQL, giảm 40% thời gian phản hồi"  (khớp: Tối ưu, hiệu năng, truy, vấn, cơ sở dữ liệu)
  – "Xây dựng luồng xử lý sự kiện bất đồng bộ cho đơn hàng" ← "Xây dựng luồng xử lý sự kiện bất đồng bộ với Kafka cho đơn hàng"  (khớp: Xây dựng, luồng, xử lý sự kiện, bất đồng bộ, đơn, hàng)
• Kinh nghiệm liên quan: 12,4 năm, nhóm Backend.

Chưa thấy bằng chứng
• Trách nhiệm: "Thiết kế và phát triển API cho hệ thống thanh toán" mới có bằng chứng một phần (chưa thấy phần: phát triển, hệ thống, thanh toán).

Gợi ý câu hỏi phỏng vấn
• Anh/chị đã từng thiết kế và phát triển API cho hệ thống thanh toán chưa? Hãy kể một ví dụ cụ thể.


#### cv_00_java.json · 78 (mid)

Điểm 78/100 (cân nhắc, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (java, Spring Boot, PostgreSQL).
• Việc đã làm: 2/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Tối ưu hiệu năng truy vấn cơ sở dữ liệu" ← "Tối ưu hiệu năng truy vấn cơ sở dữ liệu PostgreSQL, giảm 40% thời gian phản hồi"  (khớp: Tối ưu, hiệu năng, truy, vấn, cơ sở dữ liệu)
  – "Xây dựng luồng xử lý sự kiện bất đồng bộ cho đơn hàng" ← "Xây dựng luồng xử lý sự kiện bất đồng bộ với Kafka cho đơn hàng"  (khớp: Xây dựng, luồng, xử lý sự kiện, bất đồng bộ, đơn, hàng)
• Kinh nghiệm liên quan: 1,8 năm, nhóm Backend.

Chưa thấy bằng chứng
• Trách nhiệm: "Thiết kế và phát triển API cho hệ thống thanh toán" mới có bằng chứng một phần (chưa thấy phần: phát triển, hệ thống, thanh toán).

Gợi ý câu hỏi phỏng vấn
• Anh/chị đã từng thiết kế và phát triển API cho hệ thống thanh toán chưa? Hãy kể một ví dụ cụ thể.


#### cv_06_java.json · 74 (mid)

Điểm 74/100 (cân nhắc, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (java, Spring Boot, PostgreSQL).
• Việc đã làm: 1/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Tối ưu hiệu năng truy vấn cơ sở dữ liệu" ← "Tối ưu hiệu năng truy vấn cơ sở dữ liệu PostgreSQL, giảm 40% thời gian phản hồi"  (khớp: Tối ưu, hiệu năng, truy, vấn, cơ sở dữ liệu)
• Kinh nghiệm liên quan: 8,2 năm, nhóm Backend.

Chưa thấy bằng chứng
• Trách nhiệm: chưa thấy bằng chứng về "Thiết kế và phát triển API cho hệ thống thanh toán" trong CV.
• Trách nhiệm: chưa thấy bằng chứng về "Xây dựng luồng xử lý sự kiện bất đồng bộ cho đơn hàng" trong CV.

Gợi ý câu hỏi phỏng vấn
• Anh/chị đã từng thiết kế và phát triển API cho hệ thống thanh toán chưa? Hãy kể một ví dụ cụ thể.
• Anh/chị đã từng xây dựng luồng xử lý sự kiện bất đồng bộ cho đơn hàng chưa? Hãy kể một ví dụ cụ thể.


#### cv_04_java.json · 74 (mid)

Điểm 74/100 (cân nhắc, điểm xếp hạng tương đối).

Điểm mạnh
• Kỹ năng bắt buộc: có 3/3 (java, Spring Boot, PostgreSQL).
• Việc đã làm: 2/3 trách nhiệm có bằng chứng. Ví dụ:
  – "Thiết kế và phát triển API cho hệ thống thanh toán" ← "Thiết kế và phát triển REST API cho hệ thống thanh toán bằng Spring Boot"  (khớp: Thiết kế, phát triển, API, hệ thống, thanh toán)
  – "Xây dựng luồng xử lý sự kiện bất đồng bộ cho đơn hàng" ← "Xây dựng luồng xử lý sự kiện bất đồng bộ với Kafka cho đơn hàng"  (khớp: Xây dựng, luồng, xử lý sự kiện, bất đồng bộ, đơn, hàng)
• Kinh nghiệm liên quan: 1,5 năm, nhóm Backend.

Chưa thấy bằng chứng
• Trách nhiệm: chưa thấy bằng chứng về "Tối ưu hiệu năng truy vấn cơ sở dữ liệu" trong CV.

Lưu ý
• Địa điểm làm việc khác với JD.

Gợi ý câu hỏi phỏng vấn
• Anh/chị đã từng tối ưu hiệu năng truy vấn cơ sở dữ liệu chưa? Hãy kể một ví dụ cụ thể.


