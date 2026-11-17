# 00 · Tổng quan module Match CV ↔ JD và quy ước chung

> **Phiên bản bộ tài liệu:** 2.0 (09/11/2026). Thay cho 5 file thiết kế cũ (đã chuyển vào `_Lưu trữ bản cũ/`).
> **Đề tài:** Hệ thống tuyển dụng thông minh dựa trên BERTScore để phân tích và đánh giá CV cho ứng viên ngành Công nghệ thông tin.
> **Ký hiệu:** **(ƯL)** = giá trị đề xuất hoặc ước lượng, chưa đo. Ngay cạnh luôn có cách đo hoặc thí nghiệm để chốt.

File này là **điểm vào** của bộ tài liệu: kiến trúc chung, bản đồ các file, quy ước đặt tên và các quyết định đã chốt. Mọi file khác dùng đúng tên gọi định nghĩa ở đây.

---

## 1. Bài toán và kiến trúc

Đầu vào của module là **CV dạng JSON** và **JD dạng JSON** (đã được module đọc file và Module 1 tách trường). Đầu ra: với một JD, danh sách **top N CV** (mặc định 30) có **điểm 0–100** và **lời giải thích có dẫn chứng**. Chiều ngược lại (một CV → các JD phù hợp) dùng lại cùng các thành phần.

```
            ┌────────────── TẦNG 0: TIỀN XỬ LÝ (chạy 1 lần lúc nạp) ──────────────┐
 CV JSON ──►│ Luồng A (A1–A11): ẩn danh, chuẩn hoá, gắn kỹ năng (KB), tách gạch,     │
 JD JSON ──►│ Luồng B (B1–B8): metadata, token BM25, vector BGE-M3 → PostgreSQL     │
            └───────────────────────────────┬──────────────────────────────────────┘
                                            ▼  (đọc bản chụp KB, xem file 02)
 TẦNG 1: RETRIEVE (mỗi lần match)    toàn kho ──4 góc nhìn rẻ──► ~200 CV       Recall@K
   dense · BM25 · độ phủ kỹ năng · độ phủ trách nhiệm (cosine câu)
                                            ▼  RerankRequest
 TẦNG 2: RERANK                      200 CV ──BERTScore(bge-m3) + feature luật──► top N   nDCG@10
   B4/B5 = BERTScore mức token (trách nhiệm/yêu cầu × gạch CV); A1, A2 qua KB; B1–B3, C1 luật; cổng must-have
                                            ▼  FinalItem (bộ sự thật)
 TẦNG 3: EXPLAIN                     top N ──mẫu xác định (mặc định) / LLM có chỗ trống──► lời giải thích
   bằng chứng = gạch CV khớp nhất + các từ được BERTScore căn khớp
```

**Hai nguyên tắc xuyên suốt:**

1. **Làm nặng lúc nạp, làm nhẹ lúc match.** Gọi model tạo vector, dò kỹ năng chỉ làm một lần ở Tầng 0. Lúc match chỉ còn phép tính trên dữ liệu có sẵn, trừ BERTScore ở Tầng 2 (chạy GPU trên ≤200 CV, có cache).
2. **Mỗi tầng đo bằng thước riêng.** Retrieve tối ưu "không bỏ sót" (Recall@K). Rerank tối ưu "thứ tự đúng" (nDCG@10). Explain tối ưu "đúng sự thật" (tỉ lệ câu có bằng chứng, tỉ lệ phải dùng mẫu dự phòng).

**Một model, hai độ phân giải.** Cả Retrieve và Rerank đều dùng **BGE-M3**:

| Tầng | BGE-M3 dùng ở dạng | So khớp ở mức | Vì sao |
| --- | --- | --- | --- |
| Retrieve | vector dense (1 vector / đoạn) | câu, đoạn → cosine | rẻ, quét được toàn kho bằng nhân ma trận |
| Rerank | **embedding từng token (layer 24)** → **BERTScore** | **token ↔ token** | chính xác hơn, cho biết *từ nào* khớp *từ nào* (dùng làm bằng chứng); chỉ chạy trên ≤200 CV |

Đây là chỗ BERTScore nằm ở **trung tâm** của module: nó là cơ chế so khớp ngữ nghĩa duy nhất ở tầng quyết định thứ hạng, chiếm 40% trọng số prior, và là nguồn bằng chứng cho tầng Explain (xem [[07 Rerank - BERTScore với bge-m3]]).

---

## 2. Bản đồ tài liệu

| File | Nội dung | Đọc khi |
| --- | --- | --- |
| **00 Tổng quan và quy ước** (file này) | kiến trúc, quy ước tên, quyết định đã chốt | luôn đọc trước |
| [[01 Kiến thức nền]] | giải thích BM25, embedding, BGE-M3, BERTScore, chuẩn hoá điểm, chỉ số đo | chưa quen IR/NLP |
| [[02 Knowledge Base kỹ năng IT]] | KB trên Neo4j: nút, quan hệ, alias, `rel`, bản chụp xuất ra | làm KB, tính A1/A2 |
| [[03 Tiền xử lý - Lưu trữ và dữ liệu]] | PostgreSQL, danh sách bảng, `cv_record`, cách dùng KB, khi có thay đổi, lỗi, quyền riêng tư | dựng DB |
| [[04 Tiền xử lý - Luồng A (CV)]] | A1–A11: CV JSON → dữ liệu sẵn sàng | code nạp CV |
| [[05 Tiền xử lý - Luồng B (JD)]] | B1–B8: JD JSON → dữ liệu sẵn sàng | code nạp JD |
| [[06 Retrieve]] | Luồng C (JD → CV) và Luồng D (CV → JD): 4 góc nhìn, hợp nhất, top K | code Tầng 1 |
| [[07 Rerank - BERTScore với bge-m3]] | cấu hình BERTScore, feature, công thức chốt điểm, hợp đồng dữ liệu, chi phí | code Tầng 2 |
| [[08 Explain]] | bộ sự thật, mẫu giải thích xác định, prompt LLM có chỗ trống, kiểm tra bằng code | code Tầng 3 |
| [[09 Đánh giá và thí nghiệm]] | bộ nhãn chung, chỉ số, ablation từng tầng, test bất biến | chạy thực nghiệm (Chương 4) |
| [[10 Kết quả test BERTScore bge-m3]] | số liệu golden pairs T01–T24, F01–F05 của cấu hình `A_bgem3` | căn cứ cho quyết định ở 07 |
| [[11 Tham số, lộ trình và điểm còn mở]] | toàn bộ tham số cấu hình, lộ trình P0–P4, câu hỏi cần chốt | lập kế hoạch |

---

## 3. Quy ước đặt tên (bắt buộc dùng thống nhất)

### 3.1 Mã bước

| Tiền tố | Thuộc | Ví dụ |
| --- | --- | --- |
| `A1`–`A11` | Luồng A: nạp CV | A5 = nhận diện kỹ năng |
| `B1`–`B8` | Luồng B: nạp JD | B4 = gắn mã kỹ năng JD |
| `C1`–`C8` | Retrieve chiều JD → CV | C3 = chấm 4 góc nhìn |
| `D1`–`D8` | Retrieve chiều CV → JD | D3 = chấm 4 góc nhìn |
| `RR1`–`RR6` | các bước của Rerank | RR2 = tính BERTScore |
| `EX1`–`EX4` | các bước của Explain | EX2 = ráp câu |

Các mã **feature** của Rerank (`A1`, `B4`…) trùng chữ với mã bước Luồng A/B. Để tránh nhầm, khi nói về feature luôn viết **"feature A1"** hoặc dùng ký hiệu `f_A1`.

### 3.2 Đại lượng

| Ký hiệu | Nghĩa | Giá trị | Nơi tạo | Lưu ý |
| --- | --- | --- | --- | --- |
| `ev` | mức **bằng chứng** một kỹ năng trong CV | 1,0 trong mô tả · 0,8 chỉ ở `technologies` · 0,6 chỉ liệt kê · 0 (ƯL) | A5 | dùng ở Retrieve (view kỹ năng) và Rerank (feature A1, A2) |
| `w_imp` | mức **quan trọng** của kỹ năng trong JD | core 1,0 · medium 0,7 · minor 0,4 (ƯL) | B4 | **thay hẳn** tên cũ `rel`/`imp` ở các bản trước |
| `rel(a,b)` | mức **liên quan** giữa hai kỹ năng trong KB | cùng 1,0 · cha/con 0,7 · anh em 0,4 · khác 0 (ƯL) | KB mục 7 | chỉ dùng ở Rerank (A1, A2) |
| `M[g,g']` | khoảng cách giữa hai nhóm vai trò | 0–1, đối xứng | KB `NEAR` | Rerank B1, B2 |
| `level_rank` | cấp bậc dạng số | Intern 0 · Fresher 1 · Junior 2 · Mid 3 · Senior 4 · Lead 5 | A6, B5 | |
| `s_*` / `n_*` | điểm gốc / điểm đã min–max của từng góc nhìn Retrieve | `s_dense`, `s_bm25`, `s_skill`, `s_resp` | C3, C4 | Rerank chỉ đọc `s_*` |
| `R_ij` | BERTScore **Recall** giữa câu JD `j` (tham chiếu) và gạch CV `i` | ~0,5–1,0 | RR2 | xem 07 |
| `c_j` | điểm đã hiệu chuẩn của câu JD `j` với gạch khớp nhất | 0–1 | RR3 | |

### 3.3 Nhóm vai trò

KB có **8 nhóm vai trò**: Backend, Frontend, Fullstack, Mobile, Data, DevOps, QA, Security. (Bản tiền xử lý cũ ghi "9 nhóm" là sai; nếu Module 1 dùng thêm nhóm khác, ví dụ AI/ML hay BA, thì thêm vào KB và sửa ở đây. Xem điểm mở ở file 11.)

### 3.4 Bộ khoá phiên bản

Mọi kết quả phải tái lập được, nên mỗi bản ghi mang các khoá sau:

| Khoá | Ý nghĩa | Ví dụ |
| --- | --- | --- |
| `ontology_version` | bản chụp KB đã dùng | `kb-2026-11-06` |
| `pipeline_version` | phiên bản code tiền xử lý (chuẩn hoá, mẫu ghép văn bản, quy tắc `ev`) | `prep-1.0` |
| `embed_model` | model tạo vector dense | `bge-m3@5617a9f61b` |
| `bertscore_config` | model + layer + IDF + rescale + độ dài tối đa + chuẩn hoá đầu vào | `bge-m3@5617a9f61b/L24/noidf/norescale/2048/mask1` |
| `rerank_config_version` | file trọng số, ngưỡng, cổng của Rerank | `rr-1.0` |
| `prompt_version`, `model_id` | chỉ khi bật LLM (Explain hoặc kiểm chứng tuỳ chọn) | |

Hai CV/JD chỉ được so với nhau khi cùng `ontology_version`, `pipeline_version` và `embed_model`.

### 3.5 Tên module

"**profile-indexer**" trong các bản cũ chính là **Tầng 0 Tiền xử lý** (Luồng A + B). Các mã cũ đổi như sau: I7 → A5, I8 → A6, J4 → B4.

---

## 4. Các quyết định đã chốt

| # | Quyết định | Lý do ngắn | Chi tiết |
| --- | --- | --- | --- |
| Q1 | Đầu vào là JSON, không đọc PDF/DOCX trong module này | đã có module khác lo phần đọc file | 03 |
| Q2 | Một cơ sở dữ liệu: PostgreSQL + pgvector; chỉ mục BM25 và ma trận trong RAM | quy mô ≤100.000 CV nhỏ, quét toàn kho cho kết quả chính xác | 03 |
| Q3 | Retrieve = 4 góc nhìn, min–max theo JD, cộng trọng số bằng nhau, K = 200 | nghiên cứu nghiêng về hybrid; ít nhãn nên giữ đơn giản | 06 |
| Q4 | **Rerank dùng BERTScore với backbone `BAAI/bge-m3`, layer 24, không IDF, không rescale, điểm chính = Recall (JD là tham chiếu), cách chia S2** | test golden: đạt 25/26, S2 bền với pha loãng, cắt token và bất biến tên/trường (F01–F04 lệch 0); gần cross-encoder nhưng nhanh hơn, và cho căn khớp token để giải thích | 07, 10 |
| Q5 | Cross-encoder và giám khảo LLM **không** nằm trên đường chính; chỉ là mốc đối chứng hoặc tuỳ chọn bật bằng ablation | Q4 đã đủ tốt; giảm chi phí và rủi ro bịa | 07, 09 |
| Q6 | Số năm, cấp bậc, học vấn chấm bằng **luật** trên trường có cấu trúc, không bằng BERTScore | test T08: BERTScore không hiểu 5 > 1 | 07 |
| Q7 | Tổng trọng số prior của Rerank = **1,00**; feature tắt hoặc thiếu phía JD thì chuẩn hoá lại | bản cũ cộng ra 0,77 gây hiểu nhầm | 07 |
| Q8 | Explain mặc định dùng **mẫu xác định** (không LLM); LLM chỉ chọn câu và mã bằng chứng, code điền số | không thể bịa số hay bằng chứng | 08 |
| Q9 | Văn bản đưa vào BERTScore **giữ dấu tiếng Việt và hoa/thường gốc** (`text_raw`) | test F05, T11: bỏ dấu làm tụt 25–97% span | 04, 07 |

---

## 5. Lịch sử thay đổi so với các bản cũ

| Chủ đề | Bản cũ | Bản 2.0 |
| --- | --- | --- |
| Rerank | 7 feature bằng code + giám khảo LLM kiểm chứng từng trách nhiệm; cross-encoder là thí nghiệm | BERTScore (bge-m3) cho feature ngữ nghĩa B4, B5; LLM tắt mặc định |
| Lọc 200 → 60 trước LLM | có (Bước 1 + lưới an toàn) | bỏ: BERTScore đủ rẻ để chấm cả 200 |
| `bertScore.md` (thư mục cha) | BERTScore toàn văn (A4) + 12 feature, mục tiêu ≥50% trọng số | bỏ A4 toàn văn vì test T13, T16 cho thấy S1 bị pha loãng và cắt token; giữ ý tưởng che số và cache |
| Mức quan trọng kỹ năng JD | `rel` (Retrieve), `imp` (Rerank) | `w_imp` ở mọi nơi; `rel` chỉ cho KB |
| `ev` | 2 mức (1,0 / 0,6) | 3 mức (1,0 / 0,8 / 0,6) |
| Luồng A/B trong file Retrieve | đọc PDF, OCR | bỏ, thay bằng file 04, 05 |
| Đánh giá | rải ở 3 file | gom vào file 09 |
