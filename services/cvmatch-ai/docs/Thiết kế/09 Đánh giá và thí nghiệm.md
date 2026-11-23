# 09 · Đánh giá và thí nghiệm (Chương 4)

> **Phiên bản:** 2.0 (09/11/2026). Gom phần đánh giá của file Retrieve (Phần 9), Rerank (Phần 6) và tiền xử lý.
> **Mã thí nghiệm:** `RT-E*`, `RT-R*` cho Retrieve · `R-E*`, `R-X*` cho Rerank · `G*` cho test hành vi BERTScore. Bộ golden và kết quả hiện có: [[10 Kết quả test BERTScore bge-m3]].

---

## 1. Mỗi tầng đo cái gì

| Tầng | Câu hỏi | Chỉ số chính | Phụ |
| --- | --- | --- | --- |
| 0 Tiền xử lý | trích xuất có đúng không? | precision/recall nhận diện kỹ năng | sai số `years_experience`, tỉ lệ đúng `role_group` (xem [[03 Tiền xử lý - Lưu trữ và dữ liệu]]) |
| 1 Retrieve | có bỏ sót CV tốt không? | **Recall@200** | Recall@50/100/300, JD tệ nhất |
| 2 Rerank | thứ tự có đúng không? | **nDCG@10** | Recall@N, AUC mức cặp của BERTScore, thời gian |
| 3 Explain | lời giải thích có đúng sự thật không? | tỉ lệ nhận định có bằng chứng đúng (kiểm tay) | tỉ lệ phải dùng mẫu dự phòng |
| Toàn hệ thống | có công bằng không? | Δ điểm khi đổi thuộc tính nhạy cảm | tỉ lệ vào/ra top N chỉ vì biến đổi |

Luôn báo **trung bình theo JD, JD tệ nhất**, và **tách theo nhóm vai trò, fresher/có kinh nghiệm**, vì trung bình che giấu thất bại.

## 2. Bộ nhãn chung

Một bộ nhãn dùng cho cả Retrieve và Rerank để không phải chấm hai lần.

- **Quy mô:** 30–50 JD đa dạng vai trò. Chia **dev/test 50/50, phân tầng theo vai trò**. Mọi việc tinh chỉnh (trọng số, `lo/hi`, ngưỡng) chỉ làm trên dev; kết quả test báo **một lần**.
- **Chọn CV để chấm bằng gộp (pooling):** hợp của **top-300 Retrieve** của mọi cấu hình RT-*, **top-60 Rerank** của mọi cấu hình R-*, và **20 CV ngẫu nhiên** từ phần còn lại. Cặp chưa chấm coi là 0, đồng thời **báo tỉ lệ chưa chấm**.
- **Thang:** 0 = không phù hợp, 1 = một phần, 2 = phù hợp. Định nghĩa "phù hợp" (≥ 1 hay = 2) chốt **trước khi chấm**. Mỗi cặp 2 người chấm; lệch thì thảo luận hoặc người thứ ba; báo κ giữa hai người.
- **Tập con mức cặp (≈300 cặp trách nhiệm × gạch):** 2 người gán `khớp / một phần / không`. Dùng để:
  - hiệu chuẩn `lo`, `hi` và ngưỡng mức khớp của B4 ([[07 Rerank - BERTScore với bge-m3]] mục 5.3);
  - đo **AUC** của `R_ij` (BERTScore) so với cosine câu, tức so trực tiếp hai độ phân giải.
- **Tiết kiệm công:** có thể để LLM chấm sơ bộ, người kiểm ít nhất 20%. LLM chấm nhãn **không được** là model dùng ở RR5 hay Explain, để tránh vòng tròn.

## 3. Retrieve

### 3.1 Chỉ số

Recall@K với K = 50, 100, 200, 300. Vẽ đường Recall theo K: nếu từ 200 lên 300 Recall vẫn tăng rõ thì cân nhắc tăng K (Rerank tốn hơn, nhưng BERTScore chỉ tăng tuyến tính).

### 3.2 Thí nghiệm Luồng C (JD → CV)

| Mã | Thí nghiệm | Mục đích |
| --- | --- | --- |
| RT-E1 | BM25 một mình; Dense một mình | mốc cơ sở |
| RT-E2 | BM25 + Dense hợp nhất bằng RRF / RRF có trọng số / cộng điểm chuẩn hoá | chọn cách hợp nhất |
| RT-E3 | RT-E2 + view kỹ năng | view kỹ năng có đáng giữ? |
| RT-E4 | RT-E3 + view trách nhiệm | view "thử" có giúp? |
| RT-E5 | BM25 trên cả JD so với chỉ chức danh + kỹ năng | chọn truy vấn BM25 |
| RT-E6 | min–max so với DBSF | chống ngoại lệ |
| RT-E7 | BGE-M3 vs multilingual-e5-large vs Qwen3-Embedding-0.6B vs Vietnamese_Embedding_v2 | chọn model dense (đổi model ở đây **không** đổi backbone BERTScore) |
| RT-E8 | (tuỳ chọn) thêm BGE-M3 sparse vào view BM25 | có đáng không |

### 3.3 Thí nghiệm Luồng D (CV → JD)

Bộ nhãn riêng: 30–50 CV (có cả CV chung chung, rất ngắn). Với mỗi CV, gán nhãn các JD đang mở: kho ≤ 30 JD thì chấm hết, lớn hơn thì gộp như mục 2. Chỉ số: Recall@10/20/50, CV tệ nhất, kiểm tra **thiên lệch** (các JD đầu có toàn JD ngắn hay JD đòi ít kỹ năng không).

| Mã | Thí nghiệm | Mục đích |
| --- | --- | --- |
| RT-R1 | Dense một mình; BM25 một mình | mốc cơ sở |
| RT-R2 | BM25 với `full_cv` so với `condensed_cv` | CV dài làm truy vấn có nhiễu không |
| RT-R3 | view kỹ năng có/không `min_imp_sum`; thử 2, 3, 5 | kiểm chứng thiên lệch mẫu số |
| RT-R4 | thêm view trách nhiệm | có giúp ở chiều này không |
| RT-R5 | min–max so với RRF khi kho JD nhỏ | kiểm ngưỡng `min_pool_minmax` |

## 4. Rerank

### 4.1 Chỉ số

Đều tính trong số CV phù hợp **có mặt trong pool 200**:

| Chỉ số | Định nghĩa | Ghi chú |
| --- | --- | --- |
| **nDCG@10** | gain = 2^nhãn − 1, chiết khấu log2 | chỉ số chính |
| Recall@30 | tỉ lệ CV phù hợp trong pool nằm trong top N | báo thêm Recall@30 / min(30, số phù hợp) |
| AUC mức cặp | trên tập 300 cặp: `R_ij` phân biệt `khớp` với `không` tốt đến đâu | so BERTScore với cosine câu và cross-encoder |
| Thời gian | RR2 lần lạnh / lần ấm, phân vị 95, đỉnh GPU | trục x của đường cong chi phí–chất lượng |

### 4.2 Test hành vi BERTScore (golden pairs) — test hồi quy

Bộ T01–T24, F01–F05 (file 10) là **test đơn vị cho tầng ngữ nghĩa**, không đo chất lượng xếp hạng.

- **G1: chạy lại mỗi khi đổi `bertscore_config`** (model, layer, IDF, chuẩn bị đầu vào). Điều kiện giữ cấu hình: đạt ≥ 25/26 và không test nào từ ✅ chuyển ❌.
- **G2: chạy lại qua *cả pipeline*** (có `text_raw`, đổi alias, che số, cờ A7) cho các test mà file 10 ghi nhận điểm yếu. Kỳ vọng đặt trước:

| Test | Hiện tại (mô hình trần) | Kỳ vọng sau khi qua pipeline |
| --- | --- | --- |
| T05 phủ định | `negation` cao hơn `neg` +56% span | `c_j` của gạch phủ định ≤ 0,3 nhờ `m_neg` |
| T04 học/làm | +28% span, chủ yếu nhờ trùng từ | khoảng cách tăng nhờ `m_course` |
| T06 viết tắt | +19% span | tăng rõ sau khi đổi "K8s" → "Kubernetes" |
| T08 số năm | 5y − 1y = +29% span | ≈ 0 sau khi che số (đúng ý đồ: số năm do B2 chấm) |
| T11, F05 không dấu | −97% / −25 đến −45% span | CV có cờ `no_diacritics` được xử lý như thiếu dữ liệu, không bị điểm thấp |
| T19 trừu tượng | ❌ −9% span | ghi nhận; xem R-E10 |

- **G3: mở rộng bộ golden** với các cặp lấy từ CV/JD thật đã ẩn danh: thêm 2–3 cặp mỗi loại điểm yếu, nhất là khái niệm trừu tượng và phủ định nhiều dạng.

### 4.3 Ablation

Chạy **cộng dồn** theo thứ tự, kèm bản **bỏ từng feature** khỏi cấu hình đầy đủ để thấy đóng góp biên. Mốc **R-A0 = top 30 theo `fused` của Retrieve** (không rerank).

| Mã | Cấu hình | Câu hỏi |
| --- | --- | --- |
| R-A0 | top 30 của Retrieve | mốc cơ sở |
| R-E1 | + A1 (và A2) qua KB | KB có hơn `s_skill` thô? |
| **R-E2** | + B4: **cosine câu hiệu chuẩn** so với **BERTScore S2** | **BERTScore có hơn cosine câu không? (thí nghiệm trung tâm của đề tài)** |
| R-E3 | B4 với cách chia S1 / S2 / S3; Recall / Precision / F1 | khẳng định S2 + Recall trên dữ liệu thật |
| R-E4 | layer 16 / 20 / 24 của bge-m3 (ƯL) | chọn layer |
| R-E5 | hiệu chuẩn: `lo/hi` cố định / min–max theo pool / theo nhãn | |
| R-E6 | hệ số phủ định–học tập: tắt / (0,3; 0,6) / loại hẳn gạch | |
| R-E7 | trách nhiệm chung chung: trọng số 0 / 0,3 | |
| R-E8 | che số bật/tắt; đổi alias bật/tắt | |
| R-E9 | + B5 (yêu cầu dạng chữ) | B5 có thêm tín hiệu? |
| R-E10 | `c_j = max(BERTScore, cosine câu)` | bù điểm yếu khái niệm trừu tượng (T19)? |
| R-E11 | + B1; + B2 (bật/tắt `overqual_penalty`); + B3 (đo ρ(B2, B3)); + C1 | |
| R-E12 | cổng: không / cứng / mềm; thiếu phía CV: trung vị / bỏ ra / 0 | |
| R-E13 | trọng số: prior / bằng nhau / lưới thô theo nhóm {A, B4+B5, B1–B3, C} × {0; 0,5; 1; 1,5} | prior có đủ? |
| R-E14 | IDF bật/tắt | |

### 4.4 Mốc đối chứng (trả lời "sao không dùng X?")

| Mã | So với | Câu hỏi |
| --- | --- | --- |
| R-X1 | **cross-encoder** `bge-reranker-v2-m3`: (a) thay BERTScore trong B4 (cùng S2); (b) chấm thẳng cặp (JD, CV) 200 → 30 | BERTScore có thật sự "gần cross-encoder" về nDCG@10 và nhanh hơn bao nhiêu? |
| R-X2 | điểm **multi-vector (ColBERT) của bge-m3** thay BERTScore | công thức BERTScore so với MaxSim có lớp chiếu |
| R-X3 | BERTScore với **backbone khác** (ví dụ model mặc định đa ngôn ngữ của thư viện BERTScore; một model tiếng Việt nếu giấy phép và độ dài phù hợp) | bge-m3 có phải lựa chọn tốt nhất? |
| R-X4 | + RR5 (LLM kiểm chứng vùng biên) | LLM có đáng chi phí? |

Trình bày bằng **đường cong chi phí–chất lượng**: trục x là thời gian (hoặc tiền) mỗi JD, trục y là nDCG@10. Cấu hình nằm trên biên Pareto là cấu hình đáng chọn.

### 4.5 Quy tắc chọn (viết trước khi chạy)

- Chọn cấu hình **đơn giản nhất** có nDCG@10 chỉ kém cấu hình tốt nhất ≤ 1–2 điểm, và Recall@N không giảm quá 1 điểm.
- Một thành phần chỉ được **giữ** nếu cải thiện nDCG@10 hoặc Recall vượt ngưỡng đặt trước (ví dụ 2 điểm, ƯL).
- Với 30–50 JD, báo khoảng tin cậy 95% bằng **bootstrap ghép cặp theo JD**. Chênh nhỏ hơn khoảng tin cậy thì coi là nhiễu, trình bày như xu hướng.
- Nếu R-E2 cho thấy BERTScore **không** hơn cosine câu: vẫn báo trung thực. Khi đó lập luận giữ BERTScore dựa trên khả năng giải thích (căn khớp token) và độ bền (T13, T16, F01–F04), không dựa trên nDCG.

## 5. Explain

| Chỉ số | Cách đo |
| --- | --- |
| Tỉ lệ nhận định có bằng chứng **đúng** | kiểm tay 50 lời giải thích: mỗi nhận định, bằng chứng có thật sự ủng hộ không |
| Tỉ lệ `matched_words` hợp lý | kiểm tay trên cùng mẫu |
| Tỉ lệ phải dùng mẫu xác định (khi bật LLM) | log EX4 |
| Vi phạm quy tắc (chữ số lạ, công nghệ lạ, từ nhạy cảm) | log EX4 |

## 6. Thử nghiệm bất biến công bằng

Tạo bản đối chứng cho ≈50 CV bằng các biến đổi *chỉ đổi thuộc tính nhạy cảm*, rồi chạy **cả pipeline từ JSON gốc**:

| Biến đổi | Kỳ vọng |
| --- | --- |
| Đổi họ tên | Δ = 0 |
| Đổi dấu hiệu giới tính (đại từ, danh xưng) | Δ = 0 |
| Đổi tên trường | Δ = 0 |
| Đổi/xoá năm sinh, năm tốt nghiệp (không đổi ngày làm việc) | Δ = 0 (kiểm tín hiệu tuổi lọt vào C1/B2) |
| Đổi thứ tự mục và thứ tự gạch | Δ = 0 (S2 không phụ thuộc thứ tự, F04) |
| Đổi hoa/thường, bỏ dấu | ghi lại; CV bỏ dấu phải được gắn `no_diacritics` |

Vì mọi tầng trên đường chính đều là code tất định (kể cả BERTScore), **Δ phải bằng đúng 0** nếu thuộc tính đã bị loại lúc nạp. Khác 0 là rò rỉ cần sửa. Golden F01–F04 đã cho Δ = 0 ở S2 với CV **chưa** ẩn danh. Nếu bật RR5 (LLM) thì đo thêm tỉ lệ đổi phán quyết so với mức nhiễu do chỉ xáo thứ tự.

Giới hạn cần nêu: kiểm tra bất biến phản thực tế không thay được phân tích tác động theo nhóm trên dữ liệu thật, mà đồ án không có nhãn nhóm.

## 7. Ghi chép bắt buộc khi báo cáo

- Mọi model: tên, commit, giấy phép, ngày kiểm tra. BGE-M3: MIT (đã ghi trong file 10, commit `5617a9f61b`). bge-reranker-v2-m3 và các model khác: **phải mở model card kiểm tra lại** trước khi ghi.
- Phần cứng, kiểu số (fp32/fp16), seed.
- Mọi con số (ƯL) đã dùng, và con số nào đã được thay bằng giá trị đo.
