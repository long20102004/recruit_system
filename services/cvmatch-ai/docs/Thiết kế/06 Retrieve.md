# 06 · Tầng 1 Retrieve (lọc thô)

> **Phiên bản:** 2.0 (09/11/2026). **Phạm vi:** từ dữ liệu đã tiền xử lý ([[03 Tiền xử lý - Lưu trữ và dữ liệu]]) đến danh sách ~200 CV gửi sang [[07 Rerank - BERTScore với bge-m3]] (Luồng C, JD → CV) và chiều ngược lại (Luồng D, CV → JD).
> **Khái niệm** (BM25, dense, min–max, RRF, Recall@K): [[01 Kiến thức nền]]. **Tham số:** [[11 Tham số, lộ trình và điểm còn mở]]. **Thí nghiệm:** [[09 Đánh giá và thí nghiệm]] mục 3.

---

## 1. Tóm tắt

**Mục tiêu duy nhất: không bỏ sót CV tốt** (Recall@K), chấp nhận lẫn CV chưa tốt. Rerank chỉ xếp lại được những gì Retrieve giữ lại.

Mỗi CV được chấm bằng **4 góc nhìn** rẻ, đều là phép tính trên dữ liệu đã có trong RAM:

| # | Góc nhìn | Trả lời câu hỏi | Dữ liệu dùng (tạo ở) |
| --- | --- | --- | --- |
| (a) | **Dense** (vector cả tài liệu, BGE-M3) | CV và JD có *cùng ý nghĩa tổng thể*? | `cv_vector`, `jd_vector` (A10, B7) |
| (b) | **BM25** | CV có *đúng từ khoá* JD nhắc? | `cv_bm25_doc`, `jd_vector.bm25_query_tokens` (A9, B7) |
| (c) | **Độ phủ kỹ năng** | CV đáp ứng bao nhiêu phần trăm kỹ năng bắt buộc, có bằng chứng? | `cv_skill.ev`, `jd_skill.w_imp` (A5, B4) |
| (d) | **Độ phủ trách nhiệm** (cosine mức câu) | Với từng việc JD yêu cầu, CV có gạch nào tương tự? | `cv_bullet_vector`, `jd_responsibility.dense` (A10, B7) |

Điểm 4 góc nhìn được **min–max theo từng JD**, **cộng trọng số bằng nhau**, lấy **K = 200** cao nhất, rồi gọi Rerank.

**Quan hệ với Rerank.** Góc nhìn (d) và feature B4 của Rerank hỏi cùng một câu ("CV đã làm việc JD yêu cầu chưa?") nhưng ở hai độ phân giải: (d) so **một vector mỗi câu** bằng cosine (đủ rẻ để quét toàn kho), còn B4 so **từng token** bằng BERTScore (chính xác hơn, chỉ chạy trên 200 CV). Điểm `s_resp` của (d) được giữ lại để làm mốc đối chứng cho B4 (thí nghiệm R-E2 ở [[09 Đánh giá và thí nghiệm]]).

**Mức chắc chắn.** Chưa có nghiên cứu nào đo trực tiếp trên CV–JD tiếng Việt ngành IT. Cấu hình này là **mặc định có cơ sở** (nghiên cứu tuyển dụng tiếng Anh/Trung/Tây Ban Nha, benchmark tiếng Việt lĩnh vực khác), phải chốt bằng thí nghiệm ở file 09.

## 2. Bức tranh tổng thể

```
 Dữ liệu đã tiền xử lý (PostgreSQL → RAM khi dịch vụ khởi động)
   ma trận vector tài liệu · ma trận vector gạch + bullet_cv_index · ma trận CV × kỹ năng (ev) · chỉ mục BM25
                                           ▼
 LUỒNG C: MATCH (mỗi lần HR yêu cầu)
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │ C1 tải dữ liệu JD (jd_vector, jd_skill, jd_responsibility)                     │
 │ C2 lọc cứng (chỉ khi HR bật): địa điểm, trạng thái…  — trường thiếu thì cho qua │
 │ C3 chấm TOÀN KHO bằng 4 góc nhìn: Dense | BM25 | Kỹ năng | Trách nhiệm          │
 │ C4 min–max từng góc nhìn theo JD này                                           │
 │ C5 cộng 4 điểm (trọng số bằng nhau) → top K = 200                              │
 │ C6 giải thích sơ bộ · C7 ghi log · C8 gửi RerankRequest sang Tầng 2            │
 └───────────────────────────────────────────────────────────────────────────────┘
```

**Nguyên tắc:**

1. **Chấm toàn kho, không cắt sớm.** Không lấy "top 200 của từng góc nhìn" rồi mới gộp: một CV khá đều ở cả bốn mà không đứng đầu ở góc nào sẽ bị mất.
2. **Mọi quyết định giải thích được.** Mỗi CV được chọn kèm điểm từng góc nhìn và bằng chứng (kỹ năng khớp, gạch khớp nhất).
3. **Trường thiếu thì cho qua.** Lọc cứng không được loại CV chỉ vì thiếu thông tin.

## 3. Bảng dữ liệu của Retrieve

Retrieve chỉ **đọc** các bảng của tiền xử lý và **ghi** hai bảng nhật ký:

```
match_run      -- mỗi lần match một dòng
  run_id, direction ('jd_to_cv' | 'cv_to_jd'), query_id (jd_id hoặc cv_id), query_version,
  config_json, K, ontology_version, pipeline_version, embed_model, created_at
match_result   -- mỗi CV (hoặc JD) trong top K một dòng
  run_id, item_id (cv_id hoặc jd_id tuỳ direction), rank,
  s_dense, s_bm25, s_skill, s_resp,     -- điểm GỐC (Rerank đọc các cột này)
  n_dense, n_bm25, n_skill, n_resp,     -- điểm đã min–max
  fused, explanation_json               -- kỹ năng khớp/thiếu, gạch khớp nhất
```

## 4. Luồng C: khi có yêu cầu match CV với JD

### 4.1 Đầu vào / đầu ra

- **Vào:** `jd_id`, tuỳ chọn: `K` (mặc định 200), lọc cứng (nếu HR bật), tập CV cần loại trừ (ví dụ đã phỏng vấn).
- **Ra:** danh sách tối đa K CV, mỗi CV có: điểm tổng, 4 điểm thành phần, và giải thích. Danh sách này đi tiếp sang rerank.

### 4.2 Các bước

**Bước C1. Tải dữ liệu JD đã chuẩn bị.** Nếu chưa có hoặc phiên bản cũ → chạy Luồng B trước.

**Bước C2. Lập "danh sách CV được chấm".** Gồm CV có `status = active` và `is_latest = true`. Nếu HR bật lọc cứng (địa điểm, trạng thái…) thì loại CV không thoả. **CV thiếu trường lọc thì được cho qua** (không loại).

**Bước C3. Chấm 4 góc nhìn trên toàn bộ danh sách ở C2** *(không cắt top-200 từng danh sách)*:

| View | Cách chấm | Kết quả |
|---|---|---|
| **(a) Dense** | cosine giữa vector JD và vector từng CV (nhân ma trận) | 1 số mỗi CV |
| **(b) BM25** | chạy BM25 với token truy vấn của JD trên chỉ mục | 1 số mỗi CV |
| **(c) Kỹ năng** | nhân vector trọng số `w_imp` của kỹ năng bắt buộc với ma trận CV×kỹ năng (giá trị `ev`), chia tổng `w_imp` | số 0–1 mỗi CV |
| **(d) Trách nhiệm** | với mỗi trách nhiệm, tính cosine với *mọi* gạch đầu dòng; lấy max theo từng CV; trung bình qua các trách nhiệm | số ~0–1 mỗi CV |

Cả 4 đều là phép tính trên mảng số trong bộ nhớ, nên nhanh. Riêng (d) nặng nhất (số trách nhiệm × số gạch) nhưng vẫn là một phép nhân ma trận; để lấy max theo từng CV, giữ sẵn mảng `bullet_cv_index` (gạch thứ i thuộc CV nào) rồi dùng phép "max theo nhóm".

**Bước C4. Chuẩn hoá từng view** (min–max trên các CV ở C2): `(điểm − min)/(max − min)`. Nếu max = min (mọi CV bằng nhau) → đặt toàn bộ 0 cho view đó.

**Bước C5. Hợp nhất.** `điểm_tổng = trung bình của các view khả dụng` (mỗi view trọng số bằng nhau). Sắp giảm dần, lấy **top K = 200**. Hoà điểm thì ưu tiên điểm kỹ năng cao hơn, rồi theo `cv_id` để kết quả ổn định (cùng JD, cùng dữ liệu → cùng kết quả).

**Bước C6. Tạo giải thích** cho từng CV trong top-K:
- kỹ năng bắt buộc khớp / còn thiếu;
- 2–3 gạch đầu dòng khớp nhất với trách nhiệm JD (kèm trách nhiệm tương ứng);
- điểm của cả 4 view.

**Bước C7. Ghi log** vào `match_run` và `match_result` (JD, phiên bản, cấu hình, danh sách, điểm). Đây là dữ liệu quý để đánh giá và để HR phản hồi sau này.

**Bước C8. Bàn giao Rerank:** ghi `RerankRequest` (gồm `run_id`, `jd_id`, `jd_version`, `N`, và với mỗi CV: `cv_id`, `rank`, `s_*`, `n_*`, `fused`) rồi gọi Tầng 2. Không gửi văn bản CV: Rerank tự đọc `cv_bullet.text_raw` và các bảng khác theo `cv_id`. Rerank trả top N (mặc định 30). Định dạng: [[07 Rerank - BERTScore với bge-m3]] mục 6.

### 4.3 Các trường hợp đặc biệt

| Tình huống | Xử lý |
|---|---|
| JD không có kỹ năng bắt buộc | bỏ view (c); trung bình trên 3 view còn lại |
| JD không có trách nhiệm | bỏ view (d); trung bình trên 3 view còn lại |
| Số CV phù hợp lọc cứng < K | trả hết, không độn thêm |
| Lọc cứng loại quá nhiều (ví dụ còn < 20 CV) | vẫn trả, kèm cảnh báo cho HR để xem lại điều kiện lọc |
| CV thiếu trường lọc | cho qua |
| Kỹ năng JD không có trong ontology | không tính ở view (c) nhưng vẫn góp ở BM25 và dense |
| Hai lần match cùng JD cho kết quả khác | không được xảy ra nếu kho không đổi; nếu có, kiểm tra tính ổn định ở bước hoà điểm |

### 4.4 Độ phức tạp tính toán

Không phụ thuộc "mẹo" nào: mỗi view là một lượt quét toàn kho. Thời gian thực tế phụ thuộc phần cứng, nên **cần đo** với kho thật; kỳ vọng là rất nhanh so với bước rerank.

### 4.5 Ví dụ chạy bằng số

JD cần backend Python/API thanh toán. Kho thu nhỏ còn 5 CV. Điểm thô của 4 view:

| CV | Dense (cosine) | BM25 | Kỹ năng | Trách nhiệm |
|---|---|---|---|---|
| CV1 | 0,71 | 14,2 | 0,80 | 0,66 |
| CV2 | 0,64 | 21,0 | 0,55 | 0,60 |
| CV3 | 0,58 | 6,5 | 0,20 | 0,48 |
| CV4 | 0,69 | 9,8 | 0,75 | 0,70 |
| CV5 | 0,50 | 3,1 | 0,10 | 0,40 |

**Chuẩn hoá min–max** (mỗi cột kéo về 0–1):

| CV | Dense | BM25 | Kỹ năng | Trách nhiệm | **Tổng (trung bình)** | Hạng |
|---|---|---|---|---|---|---|
| CV1 | 1,00 | 0,62 | 1,00 | 0,87 | **0,87** | 1 |
| CV4 | 0,90 | 0,37 | 0,93 | 1,00 | **0,80** | 2 |
| CV2 | 0,67 | 1,00 | 0,64 | 0,67 | **0,74** | 3 |
| CV3 | 0,38 | 0,19 | 0,14 | 0,27 | **0,25** | 4 |
| CV5 | 0,00 | 0,00 | 0,00 | 0,00 | **0,00** | 5 |

**Điều ví dụ này cho thấy:**
- CV2 đứng đầu về BM25 (nhắc nhiều từ khoá) nhưng chỉ hạng 3 vì kỹ năng và trách nhiệm yếu hơn → có thể là CV "nhồi từ khoá".
- CV4 có BM25 thấp (có thể viết bằng từ khác) nhưng làm đúng việc và đủ kỹ năng → vẫn lên hạng 2. Nếu chỉ dùng BM25, CV4 đã bị đẩy xuống. **Đây chính là lý do dùng nhiều góc nhìn.**
- Min–max làm CV thấp nhất luôn bằng 0; điều đó chỉ có ý nghĩa *tương đối* trong kho hiện tại.


## 5. Luồng D: chiều ngược lại (từ một CV tìm các JD phù hợp)

### 5.1 Trả lời ngắn

- **Khung giống Luồng C:** vẫn 4 góc nhìn (dense, BM25, kỹ năng, trách nhiệm) → chuẩn hoá → cộng bằng nhau → lấy top K → rerank.
- **Nhưng không chạy được bằng cách "đảo tham số" của Luồng C.** Có 6 điểm khác (bảng 5.3), quan trọng nhất là: kho cần quét giờ là **kho JD** (nhỏ hơn nhiều), truy vấn BM25 là **một CV dài** (nhiễu hơn), và góc nhìn kỹ năng bị **thiên lệch về những JD đòi hỏi ít kỹ năng**.
- **Mức chắc chắn thấp hơn Luồng C:** các nghiên cứu tôi dựa vào chủ yếu đo chiều JD → CV. Thiết kế này suy ra theo tính đối xứng, **chưa có bằng chứng trực tiếp** cho chiều CV → JD, nên phải đo riêng ([[09 Đánh giá và thí nghiệm]] mục 3.3).

### 5.2 Dùng khi nào

- Ứng viên nộp CV và được gợi ý các JD đang mở phù hợp.
- HR có sẵn một CV và muốn biết nên đưa vào JD nào.
- CV vừa nạp xong thì hệ thống tự gợi ý JD.

### 5.3 Giống và khác so với Luồng C

| Điểm | Luồng C (JD → CV) | Luồng D (CV → JD) |
|---|---|---|
| **Kho được quét** | CV: hàng nghìn đến vài chục nghìn | **JD đang mở**: thường ít hơn nhiều (giả định của tôi: vài chục đến vài trăm; bạn xác nhận số thực) |
| **Truy vấn** | một JD (ngắn, có cấu trúc) | một CV (dài, nhiều thông tin không liên quan đến từng JD) |
| **Chuẩn hoá min–max** | trên các CV, cho *một JD* | trên các JD, cho *một CV*. Nếu số JD quá ít thì min–max không ổn định (xem D4) |
| **BM25** | truy vấn = cả JD; IDF tính trên kho CV | truy vấn = CV *rút gọn*; IDF tính trên **kho JD** nên cần **một chỉ mục BM25 riêng** cho JD |
| **Góc nhìn kỹ năng** | mẫu số cố định (một JD, so mọi CV) | **mẫu số đổi theo từng JD**, dễ thiên lệch (xem D3c) |
| **Lọc cứng** | tuỳ chọn, tắt mặc định | **bắt buộc loại JD đã đóng/hết hạn**; các lọc khác (địa điểm, hình thức làm việc…) tuỳ chọn, trường thiếu vẫn cho qua |
| **K và rerank** | K = 200, Rerank → N = 30 | K nhỏ hơn: đề xuất `K = min(50, số JD đang mở)`, Rerank → N = 10 (đề xuất của tôi, chưa có bằng chứng; chốt bằng số liệu) |

### 5.4 Cần chuẩn bị gì thêm (không có luồng nạp mới)

Dữ liệu đã có từ Luồng A và B được dùng lại: vector và kỹ năng của CV, gạch đầu dòng của CV; vector JD, kỹ năng JD, vector trách nhiệm JD. **Không phải tính embedding lại**. Chỉ cần dựng thêm 3 cấu trúc trong bộ nhớ, tất cả chỉ trên các JD có `status = 'open'`:

1. **Chỉ mục BM25 trên kho JD** (cùng hàm chuẩn hoá A4/B2; IDF tính trên kho JD).
2. **Ma trận JD × kỹ năng:** mỗi hàng là một JD, ô = `w_imp` của kỹ năng *bắt buộc* (ô trống = 0), kèm mảng `tổng_w_imp` của mỗi JD.
3. **Mảng `resp_jd_index`:** trách nhiệm thứ i thuộc JD nào (tương tự `bullet_cv_index` ở Luồng C).

Vì số JD nhỏ, dựng lại các cấu trúc này mỗi khi có JD mở/đóng/sửa nhiều khả năng rất nhanh (ước lượng, cần đo).

**Nếu CV chưa có trong kho** (ví dụ ứng viên tải lên để xem gợi ý): chạy Luồng A (A1–A10, [[04 Tiền xử lý - Luồng A (CV)]]) để có biểu diễn của CV. Có ghi vào kho hay không là quyết định về chính sách dữ liệu; nếu không ghi, phải xoá dữ liệu tạm sau khi trả kết quả.

### 5.5 Các bước

```
 CV (đã có biểu diễn từ Luồng A)
   ↓ D1  tải vector, kỹ năng, gạch đầu dòng của CV
   ↓ D2  lập danh sách JD được chấm: chỉ JD 'open' (+ lọc cứng nếu bật)
   ↓ D3  chấm 4 góc nhìn trên TOÀN BỘ JD ở D2
   ↓ D4  chuẩn hoá từng view (trên các JD, cho CV này)
   ↓ D5  cộng bằng nhau → top K
   ↓ D6  tạo giải thích   ↓ D7 ghi log   ↓ D8 rerank
```

**D1. Tải biểu diễn của CV.** Nếu CV chưa có thì chạy Luồng A (xem 5.4).

**D2. Lập danh sách JD được chấm.** `status = 'open'` và là phiên bản mới nhất. Lọc cứng khác chỉ áp dụng khi được bật; trường thiếu thì cho qua.

> **Trường hợp đặc biệt:** nếu số JD ở D2 **không lớn hơn K** thì bước "cắt top K" không còn tác dụng. Vẫn tính điểm để sắp xếp và để tạo giải thích, rồi chuyển *toàn bộ* sang rerank.

**D3. Chấm 4 góc nhìn:**

| View | Cách chấm |
|---|---|
| **(a) Dense** | cosine giữa vector CV và vector từng JD. Giống Luồng C (BGE-M3 đối xứng, không cần tiền tố truy vấn/tài liệu) |
| **(b) BM25** | truy vấn = **CV rút gọn**, chạy trên chỉ mục BM25 của kho JD |
| **(c) Kỹ năng** | với mỗi JD j: `Σ w_imp(j,s) × ev(s, CV) / max(Σ w_imp(j,s), min_imp_sum)` |
| **(d) Trách nhiệm** | giữ nguyên *chiều* của định nghĩa: với mỗi trách nhiệm của JD, tìm gạch CV giống nhất, rồi trung bình theo JD |

**(b) BM25: vì sao phải rút gọn CV.** Một CV dài là một truy vấn rất nhiễu: chứa nhiều từ không liên quan đến JD cụ thể nào (tên công ty cũ, sở thích, mô tả dài dòng). Cách xử lý đề xuất (`condensed_cv`):
- chức danh gần nhất và các chức danh trước đó,
- toàn bộ token kỹ năng (`skill_react`…),
- từ khoá trong các kinh nghiệm gần nhất,
- **loại từ trùng lặp** trong truy vấn, để một từ lặp 20 lần không áp đảo.

Phương án so sánh: dùng cả CV (`full_cv`). Cần thí nghiệm RT-R2 ([[09 Đánh giá và thí nghiệm]] mục 3.3) để chọn.

**(c) Kỹ năng: vì sao phải sửa công thức.** Về ý nghĩa, công thức không đổi: *"CV đáp ứng bao nhiêu phần trăm yêu cầu kỹ năng bắt buộc của JD này"*. Về cài đặt, ta nhân ma trận JD×kỹ năng với vector `ev` của CV rồi chia cho tổng `w_imp` của từng JD, ra điểm cho mọi JD cùng lúc.

Nhưng có **một thiên lệch mới**: một JD chỉ đòi 1 kỹ năng bắt buộc (mà CV có) sẽ đạt 1,0 rất dễ, cao hơn cả JD đòi 8 kỹ năng mà CV có 7. Ở Luồng C điều này không xảy ra vì mẫu số là *của chính JD đang xét*, còn ở đây so sánh *giữa các JD có mẫu số khác nhau*.

Cách giảm (đề xuất của tôi): **đặt mẫu số tối thiểu** `min_imp_sum = 3,0`, tức coi như mọi JD đều đòi ít nhất tương đương 3 kỹ năng cốt lõi. JD chỉ đòi 1 kỹ năng (mà CV có) khi đó đạt 1/3 ≈ 0,33 thay vì 1,0. Giá trị 3,0 là điểm khởi đầu, cần chỉnh theo thí nghiệm RT-R3.

**(d) Trách nhiệm.** Không đảo ngược định nghĩa (không lấy trung bình theo các gạch CV), vì câu hỏi vẫn là *"CV có bằng chứng đã làm các việc mà JD yêu cầu không"*. Cài đặt: ghép mọi trách nhiệm của các JD ở D2 thành một ma trận, nhân với ma trận gạch của CV, lấy max theo từng hàng, rồi trung bình theo nhóm (dùng `resp_jd_index`). View này vẫn mang nhãn "Thử".

**D4. Chuẩn hoá từng view** bằng min–max trên các JD ở D2, cho CV này. Hai lưu ý:
- Nếu max = min thì đặt cả view bằng 0.
- Nếu số JD ở D2 **dưới `min_pool_minmax` (mặc định 10)** thì min–max trên nhóm quá nhỏ rất dễ lệch (một JD ngoại lệ kéo cả nhóm). Khi đó dùng **RRF** làm cách hợp nhất thay thế. Ngưỡng 10 là đề xuất của tôi, chưa kiểm chứng.

**D5. Hợp nhất.** Trung bình các view khả dụng (trọng số bằng nhau). Lấy top K. Hoà điểm thì ưu tiên điểm kỹ năng cao hơn, rồi theo `jd_id` để kết quả ổn định.

**D6. Giải thích.** Với mỗi JD gợi ý: kỹ năng bắt buộc đã đáp ứng và **kỹ năng còn thiếu** (thông tin rất hữu ích cho ứng viên: "để hợp JD này bạn còn thiếu X, Y"), các gạch đầu dòng của CV khớp với từng trách nhiệm của JD, và điểm cả 4 view.

**D7. Ghi log** vào `match_run` (`direction = 'cv_to_jd'`) và `match_result`.

**D8. Rerank.** Gọi Tầng 2 với `direction = cv_to_jd`, `N = 10` (`reverse.rerank.N`). Rerank dùng cùng feature và BERTScore, chỉ đổi vai trò hai bên; các điểm khác nằm ở [[07 Rerank - BERTScore với bge-m3]] mục 8.

**Kiểm tra lúc trả kết quả:** kết quả có thể được lưu đệm một lúc; trước khi hiển thị, kiểm tra lại `jd.status`, vì JD có thể vừa đóng.

### 5.6 Ví dụ chạy bằng số

Một CV, 4 JD đang mở. JD-D chỉ yêu cầu duy nhất 1 kỹ năng (mà CV có, nên điểm kỹ năng thô là 1,00). Với `min_imp_sum = 3`, điểm kỹ năng của JD-D thành 0,33.

| JD | Dense | BM25 | Kỹ năng (đã áp mẫu số tối thiểu) | Trách nhiệm |
|---|---|---|---|---|
| JD-A | 0,72 | 9,0 | 0,85 | 0,70 |
| JD-B | 0,66 | 12,5 | 0,60 | 0,62 |
| JD-C | 0,52 | 2,0 | 0,15 | 0,45 |
| JD-D | 0,70 | 5,5 | 0,33 *(thô: 1,00)* | 0,50 |

**Chuẩn hoá min–max (trên 4 JD):**

| JD | Dense | BM25 | Kỹ năng | Trách nhiệm | **Tổng** | Hạng |
|---|---|---|---|---|---|---|
| JD-A | 1,00 | 0,67 | 1,00 | 1,00 | **0,92** | 1 |
| JD-B | 0,70 | 1,00 | 0,64 | 0,68 | **0,76** | 2 |
| JD-D | 0,90 | 0,33 | 0,26 | 0,20 | **0,42** | 3 |
| JD-C | 0,00 | 0,00 | 0,00 | 0,00 | **0,00** | 4 |

**Điều ví dụ này cho thấy:** nếu không áp mẫu số tối thiểu, điểm kỹ năng thô 1,00 của JD-D sẽ đẩy tổng của JD-D từ 0,42 lên khoảng 0,61, kéo nó sát JD-B (0,73 khi tính lại cùng cách) dù JD-D chỉ "dễ khớp" vì đòi hỏi quá ít. Trong ví dụ nhỏ này thứ hạng chưa đổi, nhưng với nhiều JD hơn, thiên lệch này có thể đẩy sai thứ hạng.

### 5.7 Các trường hợp đặc biệt

| Tình huống | Xử lý |
|---|---|
| CV không nhận diện được kỹ năng nào | view (c) bằng 0 cho mọi JD → sau chuẩn hoá còn 0; ba view còn lại vẫn chấm |
| CV rất ngắn hoặc chung chung (liệt kê quá nhiều kỹ năng, không mô tả việc) | điểm dense thấp đều, kỹ năng khớp nhiều JD: kết quả kém phân biệt; nên cảnh báo "CV thiếu thông tin" |
| JD không có kỹ năng bắt buộc | bỏ view (c) cho riêng JD đó khi chuẩn hoá: đặt điểm kỹ năng bằng trung bình các view còn lại để không bị phạt oan *(đề xuất, cần kiểm tra khi làm thật)* |
| JD không có trách nhiệm | tương tự: view (d) không tính cho JD đó |
| Số JD mở ≤ K | không cắt, chuyển toàn bộ sang rerank (xem D2) |
| Số JD mở < 10 | dùng RRF thay min–max (xem D4) |
| JD vừa đóng sau khi tính | kiểm tra lại `status` lúc trả kết quả |
| CV "quá giỏi" so với JD (over-qualified) | **chưa xử lý ở tầng này** (cả hai chiều); để rerank hoặc luật nghiệp vụ |

### 5.8 Điều cần nhớ

- Chiều này **chưa có bằng chứng nghiên cứu trực tiếp** như chiều JD → CV; các lựa chọn riêng (CV rút gọn, mẫu số tối thiểu, ngưỡng 10 JD, K nhỏ) đều là đề xuất của tôi.
- Phải có **bộ nhãn và thí nghiệm riêng** ([[09 Đánh giá và thí nghiệm]] mục 3.3). Không dùng kết quả đo của Luồng C để kết luận cho Luồng D.

## 6. Những thứ cố tình KHÔNG làm

Mỗi mục kèm lý do, để bạn không phải thắc mắc "sao không dùng X?".

| Phương pháp | Là gì (giải thích ngắn) | Quyết định và lý do |
|---|---|---|
| **Multi-vector (ColBERT) / SPLADE zero-shot** | mô hình so từng từ với từng từ / bản BM25 học bằng AI | **Bỏ.** ở Retrieve. Benchmark tiếng Việt cho thấy khi chưa thích nghi cho tiếng Việt, chúng kém baseline từ vựng mạnh; lại tốn bộ nhớ. Gộp cả 3 loại của BGE-M3 chỉ hơn dense+sparse chút ít  Lưu ý: so khớp mức token (cùng họ với ColBERT) **có** dùng ở Rerank dưới dạng BERTScore, vì ở đó chỉ chấm ≤200 CV nên chi phí chấp nhận được. |
| **LLM viết lại JD trước khi tìm** | nhờ AI tóm tắt/diễn đạt lại JD rồi mới tìm | **Bỏ.** Một benchmark lớn thấy việc này làm kết quả *tệ đi* (mất ràng buộc cụ thể); Module 1 đã cho JD có cấu trúc rồi |
| **HyDE xuôi** | nhờ AI *bịa ra một CV mẫu* từ JD rồi tìm CV giống CV bịa | **Thử sau cùng.** Lợi ích chưa rõ khi không huấn luyện thêm |
| **HyDE ngược (offline)** | nhờ AI *bịa ra JD mẫu từ mỗi CV* (làm một lần lúc nạp), rồi so JD thật với JD bịa | **Thử ở giai đoạn 2.** Có kết quả tốt ở một cuộc thi (tiếng Anh) |
| **ANN/HNSW** | chỉ mục vector "tìm gần đúng" để tăng tốc khi kho cực lớn | **Không cần.** Vài chục nghìn CV thì quét toàn kho đã nhanh và cho kết quả *chính xác*, không phải "gần đúng" |
| **Tinh chỉnh (fine-tune) embedding** | huấn luyện thêm model trên dữ liệu tuyển dụng của bạn | **Để sau.** Có thể cải thiện đáng kể nhưng cần dữ liệu nhãn; làm khi vòng phản hồi HR đã tích luỹ nhãn. Nghiên cứu còn cho thấy bước chuẩn hoá văn bản và đổi model nền thường tạo bước nhảy lớn hơn |
| **Embedding đồ thị tri thức (R-GCN trên ESCO)** | học vector từ mạng quan hệ giữa các kỹ năng | **Chưa đáng đầu tư.** Chưa thấy thí nghiệm bỏ-bớt rõ ràng |
| **Two-tower huấn luyện trên dữ liệu tương tác (kiểu LinkedIn)** | huấn luyện hai mạng AI từ hàng triệu lượt nhấp/ứng tuyển | **Chưa phù hợp.** Cần dữ liệu tương tác lớn mà bạn chưa có |
| **Cross-encoder trên đường chính** | đọc cặp (JD, CV) cùng lúc | **Không ở Retrieve** (quá chậm cho toàn kho). Ở Rerank chỉ là mốc đối chứng X1 (file 09). |
| **Lọc cứng mặc định** | loại CV theo điều kiện cứng | **Tắt mặc định**, chỉ khi HR bật. Lọc cứng sai sẽ loại oan người tốt; CV thiếu trường thì cho qua |

## 7. Vận hành riêng của Retrieve

Quy tắc cập nhật, xoá, đổi model, đổi KB và xử lý lỗi chung nằm ở [[03 Tiền xử lý - Lưu trữ và dữ liệu]] (mục *Khi có thay đổi*, *Lỗi thường gặp*). Riêng Retrieve:

| Sự kiện | Hành động |
| --- | --- |
| CV mới được ghi (sau A11 commit) | thêm hàng vào ma trận vector tài liệu, ma trận vector gạch + `bullet_cv_index`, ma trận CV × kỹ năng; bỏ bản cũ khỏi danh sách được chấm |
| Đến lịch dựng lại BM25 (ví dụ mỗi đêm) | dựng lại chỉ mục từ `cv_bm25_doc`; CV mới trong ngày dùng IDF của lần dựng trước, ba góc nhìn còn lại không ảnh hưởng |
| JD mở / đóng / sửa | dựng lại các cấu trúc phía JD của Luồng D (5.4) |
| Bộ nhớ lệch PostgreSQL | lệnh "dựng lại từ Postgres"; Postgres là nguồn sự thật |
