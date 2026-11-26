# 01 · Kiến thức nền: các kỹ thuật dùng trong module

> Phần giải thích khái niệm, tách từ file Retrieve cũ và bổ sung BERTScore. Không chứa quyết định thiết kế; quyết định nằm ở [[06 Retrieve]] và [[07 Rerank - BERTScore với bge-m3]]. Quy ước tên: [[00 Tổng quan và quy ước]].

---

## 1. "Phễu" lọc thô → lọc tinh (retrieve → rerank)

Hãy hình dung tuyển dụng thủ công: HR có 10.000 CV, không thể đọc kỹ cả 10.000. Họ lướt nhanh tiêu đề và từ khoá để chọn ra 200 CV, rồi mới đọc kỹ 200 CV đó để chọn 30.

- **Retrieve** = lướt nhanh. Phải **rất nhanh**, và phải **hiếm khi bỏ sót** người phù hợp.
- **Rerank** = đọc kỹ. Chậm hơn, chính xác hơn, nhưng **chỉ làm được trên những CV mà retrieve đã giữ lại**.

> **Hệ quả quan trọng:** nếu retrieve bỏ sót một CV tốt, rerank có giỏi đến đâu cũng không cứu được. Vì vậy tiêu chí đo của tầng này là **Recall@K** (xem mục 9), và K = 200 được chọn khá rộng.

## 2. Chuẩn hoá văn bản

Máy so sánh chữ rất "máy móc": `ReactJS`, `React.js`, `react` là ba chuỗi khác nhau. Chuẩn hoá là làm sạch văn bản trước khi so sánh:

| Việc chuẩn hoá | Ví dụ | Vì sao |
|---|---|---|
| Chuẩn Unicode (NFC) | "á" gõ theo hai cách khác nhau → một cách duy nhất | tiếng Việt có hai kiểu mã hoá dấu, nếu không thống nhất thì cùng một từ bị coi là khác nhau |
| Chữ thường | `Python` → `python` | để không phân biệt hoa/thường |
| Dọn khoảng trắng, ký tự lạ | bullet "•", "●", xuống dòng thừa | tránh nhiễu |
| Gộp tên gọi cùng nghĩa của kỹ năng | `ReactJS`, `React.js`, `react` → mã `skill:react` | xem mục 6 |
| **Bỏ tên người và tên trường** | xoá "Nguyễn Văn A", "ĐH Bách Khoa" khỏi văn bản dùng để chấm | để điểm không bị lệch theo tên hay trường (giảm thiên vị) |
| Tách từ tiếng Việt cho BM25 | "lập trình viên" là một từ ghép, không phải ba từ | xem mục 3 |

Với tiếng Việt, người viết CV hay gõ **không dấu** hoặc **trộn Anh–Việt**. Thiết kế xử lý: giữ văn bản có dấu làm bản chính, và lập thêm một bản **không dấu** cho BM25 để khớp cả hai kiểu gõ.

## 3. BM25 — chấm điểm theo từ khoá

### BM25 là gì?

BM25 là một **công thức toán** (ra đời từ thập niên 1990, vẫn là nền tảng của hầu hết công cụ tìm kiếm như Elasticsearch) để trả lời: *"Văn bản này khớp với danh sách từ khoá này đến mức nào?"* Nó **không dùng AI**, không hiểu nghĩa, chỉ đếm từ một cách thông minh.

### Nó chấm ra cái gì?

Với mỗi CV, BM25 trả ra **một con số ≥ 0**. Số càng lớn, CV càng chứa nhiều từ khoá quan trọng của JD. Con số này **không có thang cố định** (không phải phần trăm, không giới hạn ở 1 hay 100): nó chỉ có ý nghĩa khi **so sánh giữa các CV với cùng một JD**. Điểm BM25 của JD này không so được với điểm BM25 của JD khác. Đây là lý do ta phải "chuẩn hoá theo từng JD" (mục 8).

### Ba ý tưởng bên trong công thức

**(1) Từ hiếm thì đáng giá hơn từ phổ biến — gọi là IDF.**
Nếu 600/1000 CV có chữ "excel" thì chữ này không giúp phân biệt ai với ai. Nếu chỉ 50/1000 CV có chữ "kubernetes" thì CV nào có chữ đó nổi bật hẳn. IDF cho từ hiếm điểm cao, từ phổ biến điểm thấp.

**(2) Lặp lại nhiều lần có ích, nhưng tăng dần chậm lại — gọi là bão hoà TF.**
CV nhắc "kubernetes" 3 lần đáng tin hơn 1 lần. Nhưng nhắc 30 lần không đáng tin gấp 30 lần (có thể là nhồi từ khoá). Công thức để điểm tăng nhanh lúc đầu rồi chững lại, tham số `k1` điều khiển độ chững.

**(3) Văn bản dài được "phạt" nhẹ — gọi là chuẩn hoá độ dài.**
CV dài 10 trang chứa nhiều từ hơn chỉ vì dài, không hẳn vì phù hợp hơn. Tham số `b` điều khiển mức phạt này.

### Công thức

```
Điểm_BM25(CV, JD) = Σ  IDF(từ) × [ f × (k1 + 1) ] / [ f + k1 × (1 − b + b × độ_dài_CV / độ_dài_trung_bình) ]
                  trên mọi từ khoá trong JD

IDF(từ) = ln( 1 + (N − n + 0.5) / (n + 0.5) )

  N  = tổng số CV trong kho
  n  = số CV có chứa từ đó
  f  = số lần từ đó xuất hiện trong CV đang chấm
  k1 = 1.2  (mặc định thông dụng)    b = 0.75  (mặc định thông dụng)
```

Bạn **không cần tự tính**, thư viện làm hết. Ví dụ dưới đây chỉ để thấy ý nghĩa.

### Ví dụ bằng số

Kho có N = 1000 CV. JD nhắc 2 từ khoá: `kubernetes` và `python`. CV đang xét có độ dài bằng mức trung bình.

| Từ | Số CV chứa (n) | IDF | Nhận xét |
|---|---|---|---|
| kubernetes | 50 | ln(1 + 950.5/50.5) ≈ **2,99** | hiếm → quý |
| python | 400 | ln(1 + 600.5/400.5) ≈ **0,92** | phổ biến → ít giá trị phân biệt |

Phần "bão hoà" khi độ dài CV bằng trung bình (hệ số = f×2,2 / (f+1,2)):

| Số lần xuất hiện f | 1 | 3 | 10 | 100 |
|---|---|---|---|---|
| Hệ số | 1,00 | 1,57 | 1,96 | 2,17 (gần trần 2,2) |

Nghĩa là: từ 1 lên 10 lần chỉ tăng gần gấp đôi, từ 10 lên 100 lần gần như không tăng.

Chấm một CV có `kubernetes` 3 lần và `python` 5 lần:
- kubernetes: 2,99 × 1,57 ≈ 4,69
- python: 0,92 × (5×2,2/(5+1,2) ≈ 1,77) ≈ 1,63
- **Tổng BM25 ≈ 6,32**

Con số 6,32 tự nó không nói gì; nó chỉ có nghĩa khi đặt cạnh điểm của các CV khác (ví dụ CV khác ra 14,2 thì CV kia khớp từ khoá tốt hơn nhiều).

### Điểm mạnh và điểm yếu

| Mạnh | Yếu |
|---|---|
| Khớp **chính xác** tên công nghệ (`Kubernetes`, `Terraform`, `Spring Boot`) | **Không hiểu nghĩa**: "lập trình backend" và "phát triển phía máy chủ" bị coi là khác nhau |
| Nhanh, rẻ, không cần GPU, không cần huấn luyện | Phụ thuộc cách viết (nên mới cần chuẩn hoá ở mục 2) |
| Giải thích được (biết từ nào khớp) | Có thể bị đánh lừa bởi CV nhồi từ khoá |
| Nghiên cứu cho thấy vẫn rất mạnh, đôi khi hơn cả vector, và bổ sung tốt cho vector | |

**Vì sao thiết kế dùng cả BM25 lẫn vector:** BM25 bắt được *từ khoá chính xác*, vector bắt được *ý nghĩa*. Cái này mạnh chỗ cái kia yếu.

### Cách dùng ở đây

- "Văn bản" = CV đã chuẩn hoá, **cộng thêm các mã kỹ năng chuẩn hoá** như một dạng từ (ví dụ thêm token `skill_react`), để CV viết "ReactJS" vẫn khớp JD viết "React".
- "Truy vấn" = nội dung **cả JD** (mặc định). Thí nghiệm RT-E5 ở [[09 Đánh giá và thí nghiệm]] so với phương án chỉ dùng tên chức danh + kỹ năng.

## 4. Embedding và tìm kiếm vector (dense)

### Embedding là gì?

Embedding biến một đoạn văn thành **một dãy số** (gọi là *vector*) sao cho **hai đoạn văn có nghĩa gần nhau thì hai dãy số gần nhau**. Mô hình AI làm việc này đã được huấn luyện trên lượng văn bản khổng lồ.

Ví dụ rút gọn (thực tế có 1024 số, đây chỉ dùng 2 số để dễ hình dung):

| Câu | Vector |
|---|---|
| "Xây dựng API cho hệ thống thanh toán" | (0,9 ; 0,3) |
| "Phát triển dịch vụ backend xử lý giao dịch" | (0,85 ; 0,35) |
| "Thiết kế banner quảng cáo" | (0,1 ; 0,9) |

Hai câu đầu khác chữ hoàn toàn nhưng vector gần nhau → máy hiểu chúng cùng chủ đề. Câu thứ ba ở xa. **Đây là thứ BM25 không làm được.**

### "Dense" nghĩa là gì?

"Dense" (đặc) chỉ loại vector mà *mọi vị trí đều có số* (1024 số, hầu hết khác 0). Trái với "sparse" (thưa, xem 2.5).

### Cosine similarity: đo độ gần nhau

Để so hai vector, ta dùng **cosine similarity**: đo góc giữa hai vector.

- Kết quả từ **−1 đến 1**; với văn bản thường nằm trong khoảng **0 đến 1**.
- **Càng gần 1 = nghĩa càng giống**. Ví dụ 0,71 giống hơn 0,50.
- Giống BM25, nên dùng để **xếp hạng tương đối giữa các CV**, không nên diễn giải tuyệt đối (0,6 không có nghĩa "phù hợp 60%").

### Điểm mạnh và yếu

| Mạnh | Yếu |
|---|---|
| Hiểu **ý nghĩa**, hiểu từ đồng nghĩa, hiểu khác ngôn ngữ (Anh/Việt) | Có thể **bỏ qua chi tiết cứng**: "yêu cầu 5 năm Java" với CV 1 năm Java vẫn có thể ra điểm cao |
| Tốt khi CV và JD diễn đạt khác nhau | Cần GPU để tạo vector (nhưng chỉ tạo một lần lúc nạp) |
| | Khó giải thích vì sao điểm cao |

Cho nên ta bổ sung bằng BM25 và góc nhìn kỹ năng (bắt chi tiết cứng).

## 5. BGE-M3 — mô hình tạo vector được chọn

**BGE-M3** là một mô hình embedding đa ngôn ngữ (có tiếng Việt), nhận văn bản dài (đến khoảng 8.000 token). Nó có thể tạo **ba loại biểu diễn** từ cùng một văn bản:

| Loại | Là gì | Ví dụ ý nghĩa | Dùng ở đây? |
|---|---|---|---|
| **Dense** | 1 vector 1024 số cho cả văn bản | "ý nghĩa tổng thể" | **Có**, góc nhìn 1 và 4 |
| **Sparse** (learned sparse) | danh sách *từ → trọng số* do AI học, một kiểu "BM25 thông minh hơn" biết từ nào quan trọng | `{python: 1.8, backend: 1.2, api: 0.9}` | **Lưu sẵn** lúc nạp để dùng thử ở thí nghiệm; mặc định góc nhìn 2 vẫn là BM25 |
| **Multi-vector** (kiểu ColBERT) | mỗi từ một vector, so từng từ với từng từ | rất chính xác nhưng tốn bộ nhớ và chậm | **Không dùng** ở Retrieve; ở Rerank dùng embedding từng token qua BERTScore (mục 11) |

Lý do chọn BGE-M3 làm mặc định: trong benchmark tiếng Việt (tuy là hỏi–đáp, không phải CV–JD), BGE-M3 và multilingual-e5-large là hai model mạnh và ổn định nhất; Qwen3-Embedding-0.6B đứng giữa bảng. Thí nghiệm RT-E7 ở [[09 Đánh giá và thí nghiệm]] so sánh trên dữ liệu thật.

> **Lưu ý kỹ thuật:** BGE-M3 không cần thêm tiền tố vào câu. Nhưng nếu thử `multilingual-e5-large` ở thí nghiệm, model đó yêu cầu đặt tiền tố `query: ` / `passage: ` trước văn bản; quên là kết quả tệ đi.

## 6. Ontology kỹ năng, chỉ mục ngược và "độ phủ kỹ năng"

### Vấn đề cần giải

Cùng một kỹ năng, người ta viết rất nhiều kiểu: `ReactJS`, `React.js`, `React`, `react js`. Nếu chỉ so chuỗi, máy bỏ sót.

### Ontology kỹ năng là gì?

Là **một danh mục kỹ năng chuẩn**, mỗi kỹ năng có:
- một **mã duy nhất** (ví dụ `S0123`),
- **tên chuẩn** (`React`),
- danh sách **tên gọi khác** (alias: `ReactJS`, `React.js`…),
- (tuỳ chọn) **quan hệ** với kỹ năng khác (`Spring Boot` thuộc hệ sinh thái `Java`).

Có thể lấy **ESCO** (danh mục kỹ năng/nghề nghiệp của châu Âu) làm nền, rồi bổ sung bảng alias riêng cho công nghệ IT phổ biến ở Việt Nam, vì danh mục chung thường chưa phủ hết công cụ mới. (Đây là nhận định của tôi, cần bạn kiểm tra danh mục thực tế.)

Từ giờ, cả CV và JD đều được **dịch sang mã kỹ năng**. So sánh mã với mã thì chính xác và rẻ.

### Chỉ mục ngược là gì?

Thay vì với mỗi CV hỏi "CV này có kỹ năng nào", ta lập sẵn bảng ngược: **với mỗi kỹ năng, những CV nào có nó**. Giống mục lục tra cứu cuối sách.

```
skill:react       → [CV12 (ev 1.0), CV40 (ev 0.6), CV77 (ev 1.0), ...]
skill:kubernetes  → [CV05 (ev 1.0), CV12 (ev 0.6), ...]
```

Khi JD cần `react` và `kubernetes`, ta tra đúng 2 dòng thay vì quét mọi CV. Về mặt cài đặt, ta lưu cả bảng này dưới dạng một **ma trận thưa** (hàng = CV, cột = kỹ năng, ô = mức bằng chứng) để nhân với trọng số JD ra điểm cho mọi CV cùng lúc.

### Công thức độ phủ kỹ năng

```
Điểm_kỹ_năng(CV) =  Σ  w_imp(s) × ev(s, CV)  /  Σ w_imp(s)
                  s ∈ kỹ năng BẮT BUỘC của JD       s ∈ kỹ năng BẮT BUỘC của JD
```

Hai đại lượng (định nghĩa chuẩn ở [[00 Tổng quan và quy ước]] mục 3.2):

- **`w_imp`** (mức quan trọng của kỹ năng trong JD): cốt lõi = 1,0; vừa = 0,7; phụ = 0,4 (lấy từ `importance` của Module 1; không có thì đặt bằng 1). Bản cũ gọi là `rel`; tên `rel` nay dành cho mức liên quan giữa hai kỹ năng trong KB.
- **`ev`** (evidence = mức bằng chứng trong CV), gán ở bước A5:

| Tình huống trong CV | ev (đề xuất mặc định) |
|---|---|
| Kỹ năng nằm trong mô tả (`description`) của một kinh nghiệm/dự án ("Triển khai dịch vụ lên Kubernetes…") | **1,0** |
| Chỉ nằm trong `technologies` của kinh nghiệm/dự án | **0,8** |
| Chỉ liệt kê trong mục "Kỹ năng", tóm tắt hoặc chứng chỉ | **0,6** |
| Không có | **0** |

**Ý nghĩa của kết quả:** số từ 0 đến 1 = "CV này đáp ứng bao nhiêu phần trăm yêu cầu kỹ năng bắt buộc, có tính độ tin cậy của bằng chứng". Ví dụ JD cần React (w_imp 1), Docker (w_imp 1), Kafka (w_imp 0,5). CV có React có dự án (1,0), Docker chỉ liệt kê (0,6), không có Kafka (0):
`(1×1,0 + 1×0,6 + 0,5×0) / (1 + 1 + 0,5) = 1,6 / 2,5 = 0,64`.

Các giá trị 1,0 / 0,8 / 0,6 là điểm khởi đầu (ƯL), có thể chỉnh sau khi đo.

## 7. Độ phủ trách nhiệm mức gạch đầu dòng

### Vấn đề cần giải

Có kỹ năng chưa chắc đã làm đúng việc. CV ghi "Python" nhưng chỉ làm phân tích dữ liệu, trong khi JD cần "xây dựng API cho hệ thống thanh toán". Góc nhìn này kiểm tra **công việc đã làm** thay vì **danh sách kỹ năng**.

### Cách làm

1. JD đã được Module 1 tách thành danh sách **trách nhiệm** (ví dụ 6–10 dòng: "Thiết kế và phát triển API…", "Tối ưu hiệu năng truy vấn…").
2. CV được tách thành từng **gạch đầu dòng** trong mục kinh nghiệm/dự án.
3. Mỗi gạch và mỗi trách nhiệm đều có vector (mục 4).
4. Với **từng trách nhiệm của JD**: tìm trong CV gạch đầu dòng **giống nhất** (cosine lớn nhất) → gọi là *điểm khớp tốt nhất* của trách nhiệm đó.
5. **Điểm trách nhiệm của CV = trung bình** các điểm khớp tốt nhất qua mọi trách nhiệm của JD.

```
Điểm_trách_nhiệm(CV) = trung bình theo j của [ max theo i của cosine( trách_nhiệm_j , gạch_i ) ]
```

**Vì sao lấy max trong CV chứ không lấy trung bình?** CV có thể có 30 gạch, phần lớn không liên quan đến JD này. Ta chỉ cần *có ít nhất một bằng chứng* cho mỗi việc, không cần mọi dòng đều liên quan.

**Vì sao lấy trung bình qua các trách nhiệm?** Để thưởng cho CV *đáp ứng nhiều* việc, không chỉ một việc.

**Ý nghĩa của kết quả:** số khoảng 0–1, càng cao = CV càng có nhiều bằng chứng đã làm các việc giống JD yêu cầu.

> **Trạng thái: "Thử".** Chưa có nghiên cứu nào kiểm chứng trực tiếp góc nhìn này, nên hệ thống phải có **cờ bật/tắt** và [[09 Đánh giá và thí nghiệm]] có thí nghiệm bỏ-bớt (ablation) để xem nó có thật sự giúp không. Nếu không giúp, bỏ nó và dùng 3 góc nhìn còn lại.

## 8. Chuẩn hoá điểm và hợp nhất

### Vì sao phải chuẩn hoá?

4 góc nhìn cho điểm ở **thang khác nhau**: BM25 có thể ra 3 đến 21, cosine ra 0,5 đến 0,71, độ phủ kỹ năng ra 0 đến 1. Cộng thẳng thì BM25 áp đảo chỉ vì số to hơn. Phải đưa chúng về cùng thang trước.

### Min–max (mặc định)

Với mỗi góc nhìn, **cho JD đang xét**, kéo điểm thấp nhất về 0 và cao nhất về 1:

```
điểm_mới = (điểm − điểm_thấp_nhất) / (điểm_cao_nhất − điểm_thấp_nhất)
```

Nhược điểm: một CV cực cao bất thường (ngoại lệ) sẽ kéo mọi CV còn lại xuống gần 0. Phương án thay thế **DBSF** (dùng trung bình ± 3 độ lệch chuẩn thay cho min/max) chống ngoại lệ tốt hơn, và là một thí nghiệm ở [[09 Đánh giá và thí nghiệm]].

### Hợp nhất bằng cộng điểm có chuẩn hoá (mặc định) so với RRF

| Cách | Cách làm | Khi nào dùng |
|---|---|---|
| **Cộng điểm đã chuẩn hoá** (mặc định) | chuẩn hoá → cộng (trọng số bằng nhau) | Mặc định; nghiên cứu nghiêng về cách này, nó giữ được *độ chênh lệch* điểm |
| **RRF** (Reciprocal Rank Fusion) | bỏ điểm, chỉ dùng *thứ hạng*: mỗi danh sách cho CV hạng r một điểm `1/(60+r)`, rồi cộng | **Dự phòng** khi chưa có nhãn để đánh giá; không nhạy với thang điểm nhưng mất thông tin độ chênh |

**Vì sao trọng số bằng nhau?** Nghiên cứu cho thấy chỉnh trọng số cải thiện rất ít, còn *chọn góc nhìn nào* mới quan trọng; và với ít dữ liệu nhãn, chỉnh trọng số dễ quá khớp. Giữ đơn giản.

## 9. Các chỉ số đo chất lượng

- **Recall@K** *(chỉ số chính của tầng này)*: trong tất cả CV **thật sự phù hợp** với một JD, bao nhiêu phần trăm nằm trong top K mà hệ thống trả ra?
  Ví dụ: có 10 CV phù hợp, top-200 chứa 8 → Recall@200 = 80%.
  Đây là thứ cần tối đa hoá, vì CV bị bỏ sót ở đây sẽ mất vĩnh viễn.
- **JD tệ nhất:** ngoài trung bình, luôn xem Recall của JD khó nhất, vì trung bình che giấu thất bại.
- **nDCG@10** *(dùng ở tầng rerank, nhắc để bạn biết)*: đo xem CV phù hợp có nằm ở **thứ hạng cao** trong 10 người đầu không.
- **nDCG@10** công thức: với nhãn graded 0/1/2, `gain = 2^nhãn − 1`, chiết khấu `1/log2(hạng + 1)`, chia cho giá trị của thứ tự lý tưởng. Bằng 1 khi 10 CV đầu được xếp đúng thứ tự tốt nhất có thể.

## 10. Ba cách so hai đoạn văn: bi-encoder, cross-encoder, so khớp mức token

| Cách | Hoạt động | Tốc độ | Độ chính xác | Giải thích được? | Dùng ở đâu |
| --- | --- | --- | --- | --- | --- |
| **Bi-encoder** (vector dense, mục 4) | mã hoá JD và CV **riêng rẽ** thành 1 vector mỗi bên, so bằng cosine | rất nhanh; vector CV tính sẵn lúc nạp | "nhìn từ xa", mất chi tiết | không | Retrieve |
| **Cross-encoder** (ví dụ bge-reranker-v2-m3) | đọc **cặp (JD, CV) cùng lúc**, trả 1 điểm | chậm: mỗi cặp một lượt chạy model, không cache được phía CV | cao | không (chỉ 1 con số) | **mốc đối chứng** trong thí nghiệm |
| **So khớp mức token** (BERTScore, ColBERT) | mã hoá mỗi bên thành **một vector cho mỗi token**, rồi ghép từng token bên này với token giống nhất bên kia | trung bình: embedding token của mỗi câu tính một lần, ghép bằng nhân ma trận nhỏ | gần cross-encoder trên test của mình (xem file 10) | **có**: biết từ nào khớp từ nào | **Rerank** |

## 11. BERTScore

### Từ đâu ra?

BERTScore (Zhang và cộng sự, 2020) vốn được đề xuất để **đánh giá văn bản sinh**: so câu máy dịch (ứng viên) với câu người dịch (tham chiếu) theo nghĩa, thay cho đếm từ trùng như BLEU. Ý tưởng tổng quát hơn thế: nó là một cách **đo một đoạn văn "phủ" ý nghĩa của đoạn kia đến đâu**, ở mức từng từ. Đây chính là câu hỏi của bài toán match: *gạch kinh nghiệm này của CV phủ được bao nhiêu ý của trách nhiệm JD?*

### Cách tính

1. Cho tham chiếu `x` (ở đây: một trách nhiệm JD) và ứng viên `x̂` (một gạch CV) qua cùng một model Transformer, lấy **embedding của từng token** ở một layer chọn trước (ở đây: layer 24 của bge-m3). Mỗi token có một vector, và vector này **phụ thuộc ngữ cảnh** ("spring" trong "Spring Boot" khác "spring" trong "mùa xuân").
2. Tính cosine giữa **mọi cặp** (token của `x`, token của `x̂`) → một ma trận nhỏ, ví dụ 12 × 18.
3. **Ghép tham lam (greedy matching):** mỗi token chỉ lấy cặp có cosine lớn nhất.

```
Recall    R = (1/|x|)  Σ_{token t ∈ x}  max_{t̂ ∈ x̂} cos(t, t̂)     ← mỗi token JD tìm token CV giống nhất
Precision P = (1/|x̂|) Σ_{token t̂ ∈ x̂} max_{t ∈ x}  cos(t, t̂)     ← mỗi token CV tìm token JD giống nhất
F1        = 2PR / (P + R)
```

Tuỳ chọn: **IDF** (token hiếm nặng hơn) và **rescale baseline** (kéo điểm về thang dễ đọc). Cấu hình của hệ thống **tắt cả hai** (xem [[07 Rerank - BERTScore với bge-m3]]).

### Ví dụ nhỏ

JD: "Xây dựng **API** cho hệ thống **thanh toán**". CV: "Phát triển **dịch vụ backend** xử lý **giao dịch tài chính**".

- Token "thanh toán" của JD không có token trùng chữ trong CV, nhưng vector của nó gần vector "giao dịch", "tài chính" → cosine cao.
- Token "API" gần "dịch vụ", "backend".
- Recall đo được: **0,74**; với một CV không liên quan ("Thiết kế banner quảng cáo…"): **0,61** (test T01, file 10).

### Đọc điểm thế nào?

- Điểm thô **không bắt đầu từ 0**: hai câu không liên quan vẫn thường được 0,55–0,70, vì token nào cũng có "hàng xóm" hơi gần. Trùng hệt = 1,0.
- Vì vậy luôn đọc điểm theo **span** = điểm "trùng hệt" − điểm "không liên quan", và **hiệu chuẩn** trước khi cộng với feature khác (07, mục 4).
- **Recall khi JD là tham chiếu** = "JD được CV phủ đến đâu". CV viết dài thêm không bị phạt (khác Precision), CV nhồi một từ lặp lại cũng không lợi (test T14): mỗi token JD chỉ được tính một lần.

### Điểm mạnh và điểm yếu (đo trên bge-m3, file 10)

| Mạnh | Yếu |
| --- | --- |
| hiểu diễn đạt khác, khác ngôn ngữ Anh ↔ Việt (T01–T03, T18) | **không hiểu phủ định**: "chưa từng triển khai Kubernetes" vẫn cao (T05) |
| bền với nhồi từ khoá (T14) và chuỗi lệnh chèn vào CV (T22) | **không hiểu số**: không biết 5 năm > 1 năm (T08) |
| chấm từng gạch thì không bị pha loãng, không bị cắt token (T13, T16) | **rất nhạy với dấu tiếng Việt** (T11, F05) |
| cho biết token nào khớp → làm bằng chứng giải thích | **yếu với khái niệm trừu tượng**: "hệ thống phân tán" ↔ "microservices với Kafka" thất bại (T19); viết tắt yếu (T06) |

Cách hệ thống bù từng điểm yếu nằm ở [[07 Rerank - BERTScore với bge-m3]] mục 3.

### Quan hệ với ColBERT

ColBERT (và chế độ multi-vector của bge-m3) tính **MaxSim**: với mỗi token truy vấn, lấy cosine lớn nhất với token tài liệu, rồi cộng lại. Về toán học đây **chính là BERTScore Recall** (chưa chia độ dài), khác ở chỗ ColBERT dùng thêm một lớp chiếu được huấn luyện cho truy hồi. Nói cách khác, so khớp mức token kiểu BERTScore là một kỹ thuật được ngành truy hồi dùng thật, không chỉ là thước đo văn bản sinh. Thí nghiệm R-X2 ở [[09 Đánh giá và thí nghiệm]] so trực tiếp hai cách.
