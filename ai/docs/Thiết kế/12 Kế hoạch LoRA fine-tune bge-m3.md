# 12 · Kế hoạch LoRA fine-tune bge-m3 cho BERTScore

> **Phiên bản:** 1.0 (13/11/2026). Bản kế hoạch, chưa chạy.
> **Mục tiêu:** dạy backbone của BERTScore ([[07 Rerank - BERTScore với bge-m3]]) hiểu tốt hơn cặp *trách nhiệm JD ↔ gạch CV* trong tuyển dụng IT tiếng Việt.
> **Ký hiệu:** **(ƯL)** = giá trị đề xuất, chưa đo.

---

## 0. Tóm tắt trong 5 dòng

1. Hiện tại BERTScore dùng bge-m3 **nguyên gốc**, nên trượt T19 (khái niệm trừu tượng), yếu với viết tắt (T06), học/làm (T04) và phủ định (T05) (file 10).
2. Ta **không train lại cả model** mà gắn thêm **LoRA**: vài lớp nhỏ (≈1% tham số) học thêm, model gốc giữ nguyên.
3. Dữ liệu train là các bộ **(trách nhiệm JD, gạch CV khớp, vài gạch CV "gần giống mà không khớp")**, phần lớn do LLM sinh rồi được kiểm lại.
4. Hàm loss dạy model một điều: **điểm BERTScore của gạch khớp phải cao hơn điểm của gạch không khớp**.
5. Thành công khi: golden test vẫn ≥ 25/26, AUC trên 300 cặp người gán tăng, nDCG@10 tăng (thí nghiệm **R-E15**).

---

## 1. Hiểu ý tưởng trong 1 phút

**BERTScore Recall** (đúng cách đang dùng ở 07 mục 4) với câu JD `q` và gạch CV `d`:

```
mỗi từ của q  → tìm từ giống nhất trong d (cosine)  → lấy trung bình
R(q, d) = mean_{từ của q} ( max_{từ của d} cos )
```

Model gốc học trên văn bản chung, nên nó không biết rằng "hệ thống phân tán" và "microservices + Kafka" là cùng một việc. Fine-tune nghĩa là cho model xem hàng nghìn ví dụ kiểu:

| Câu JD (q) | Gạch CV | Muốn điểm |
| --- | --- | --- |
| Xây dựng hệ thống phân tán chịu tải cao | Thiết kế microservices giao tiếp qua Kafka, xử lý N nghìn request/giây | **cao** |
| Xây dựng hệ thống phân tán chịu tải cao | Học môn Hệ thống phân tán, làm bài tập lớn về RPC | **thấp** |
| Xây dựng hệ thống phân tán chịu tải cao | Phát triển giao diện React cho trang quản trị | **thấp** |

Sau mỗi lô ví dụ, model chỉnh vector các từ một chút để hàng "cao" được điểm cao hơn hai hàng "thấp".

**Vì sao dùng LoRA:**

- bge-m3 có ≈568 triệu tham số. Train hết thì tốn bộ nhớ và dễ làm hỏng những gì model đã biết.
- LoRA chỉ thêm ma trận nhỏ vào các lớp attention. Số tham số cần train ≈ 5–10 triệu, chạy được trên GPU 16 GB miễn phí (Kaggle T4).
- Train xong có thể **gộp** LoRA vào model. Lúc chạy, tốc độ giống hệt bản gốc (116 ms/CV vẫn giữ).

**Đây vẫn là BERTScore.** Công thức chấm không đổi, chỉ có backbone được tối ưu cho miền tuyển dụng. Cách làm này chính là cách người ta train ColBERT, vì MaxSim của ColBERT = BERTScore Recall (file 01 mục 11).

---

## 2. Dataset cần có

### 2.1 Định dạng một mẫu (JSONL, mỗi dòng một mẫu)

```json
{
  "id": "syn-00123",
  "query": "Xây dựng hệ thống phân tán chịu tải cao",
  "pos": "Thiết kế microservices giao tiếp qua Kafka, xử lý N nghìn request/giây",
  "negs": [
    {"text": "Học môn Hệ thống phân tán, làm bài tập lớn về RPC", "type": "coursework"},
    {"text": "Chưa có kinh nghiệm với hệ thống phân tán", "type": "negation"},
    {"text": "Phát triển giao diện React cho trang quản trị", "type": "other_task"},
    {"text": "Cài đặt Kafka trên máy cá nhân để tìm hiểu", "type": "same_tech_shallow"}
  ],
  "teacher": {"pos": 0.93, "negs": [0.21, 0.08, 0.02, 0.35]},
  "source": "llm_synthetic",
  "role_group": "Backend",
  "lang": "vi"
}
```

- `query`: **một** trách nhiệm hoặc yêu cầu dạng chữ của JD (đúng đơn vị của S2).
- `pos`: **một** gạch CV thật sự đáp ứng câu đó.
- `negs`: 4–7 gạch **không** đáp ứng, có ghi loại (mục 2.3).
- `teacher`: điểm của cross-encoder `bge-reranker-v2-m3` cho từng cặp (mục 4.3), dùng để học thêm "mức độ".

### 2.2 Cần bao nhiêu

| Phần | Số lượng (ƯL) | Dùng để |
| --- | --- | --- |
| **Train** | ≈ 10.000–15.000 mẫu | train LoRA |
| **Dev** | ≈ 1.000 mẫu | chọn checkpoint, chỉnh tham số |
| **Test** | 300 cặp người gán (file 09 mục 2) + golden T01–T24, F01–F05 + bộ nhãn JD | **chỉ đo một lần, không bao giờ train** |

Mức 10k là đủ cho LoRA. Các bài về fine-tune embedding thường thấy cải thiện rõ ở cỡ vài nghìn đến vài chục nghìn mẫu. Ít hơn 3k thì nên giảm `r` của LoRA và train ít epoch hơn.

### 2.3 Các loại mẫu âm (quan trọng nhất)

Model học được nhiều nhất từ **mẫu âm khó**, tức những gạch trông giống nhưng không khớp. Mỗi loại nhắm vào một điểm yếu đã đo:

| Loại `type` | Ví dụ (với q = "Triển khai ứng dụng lên Kubernetes") | Nhắm vào |
| --- | --- | --- |
| `negation` | "Chưa từng triển khai ứng dụng lên Kubernetes" | T05 |
| `coursework` | "Học khoá Kubernetes cơ bản trên Udemy" | T04 |
| `same_tech_shallow` | "Cài minikube trên laptop để thử" | trùng từ mà không thật sự làm |
| `other_task` | "Viết unit test cho module thanh toán" | âm dễ, giữ cho cân bằng |
| `similar_role` | "Cấu hình CI/CD bằng Jenkins cho dự án" | cùng nhóm DevOps nhưng việc khác |

**Mẫu dương cũng cần đa dạng** để chữa đúng các điểm yếu:

| Kiểu dương | Ví dụ | Nhắm vào |
| --- | --- | --- |
| diễn đạt khác hẳn chữ | "Đóng gói service bằng Helm chart, chạy trên cụm EKS" | T19 trừu tượng |
| viết tắt / alias | "Deploy app lên K8s" | T06 |
| tiếng Anh | "Deployed microservices to a Kubernetes cluster" | T03, T18 |
| không dấu (tỉ lệ nhỏ, ≈10%) | "Trien khai ung dung len Kubernetes" | T11, F05 |

> **Lưu ý về phủ định và học/làm:** MaxSim yếu với phủ định *về cấu trúc*, vì từ "chưa" chỉ là một token. Train sẽ giúp phần nào, nhưng **vẫn giữ luật `m_neg`, `m_course`** ở A7/RR3. Thí nghiệm sẽ đo xem có bỏ được luật hay không.

---

## 3. Lấy mẫu: dữ liệu đến từ đâu

Có ba nguồn, trộn theo tỉ lệ (ƯL):

```
  Nguồn A  LLM sinh tổng hợp ........ ≈ 60%
  Nguồn B  gạch CV thật + đào âm khó  ≈ 30%
  Nguồn C  biến đổi tự động .......... ≈ 10%
```

### 3.1 Bước 1: gom câu JD "hạt giống"

- Lấy **≈ 300–500 JD IT** từ các tin tuyển dụng công khai (tuân thủ điều khoản trang) và JD có sẵn của đồ án, tách trách nhiệm bằng đúng B6 → khoảng **1.500–3.000 câu** `query`.
- Bỏ các câu `is_generic` ("làm việc nhóm"…).
- **Chia đều theo 8 nhóm vai trò** (00 mục 3.3), để model không chỉ giỏi Backend. Mỗi nhóm ≥ 150 câu.
- **Không** dùng JD nào nằm trong bộ nhãn test (file 09). Lọc trùng gần đúng bằng cosine > 0,95 với câu của bộ test, để tránh rò rỉ.

### 3.2 Nguồn A: LLM sinh gạch CV

Với mỗi câu `query`, gọi LLM **một lần** để sinh 2 gạch dương và 5 gạch âm theo đúng các loại ở 2.3. Khung prompt:

```
Bạn là chuyên gia tuyển dụng IT Việt Nam.
Câu trách nhiệm trong JD: "<query>"
Viết các gạch đầu dòng kinh nghiệm như trong CV thật (tiếng Việt, 8–25 từ, có thể chen
tên công nghệ tiếng Anh). Trả JSON:
- pos_1: đáp ứng câu trên, dùng từ ngữ GẦN với câu JD
- pos_2: đáp ứng câu trên nhưng diễn đạt KHÁC HẲN (dùng công nghệ cụ thể, không lặp từ JD)
- neg_negation: nói rõ CHƯA làm việc này
- neg_coursework: chỉ HỌC / làm bài tập về chủ đề này
- neg_shallow: có nhắc cùng công nghệ nhưng chỉ dùng hời hợt
- neg_similar_role: việc khác nhưng cùng nhóm vai trò
- neg_other: việc không liên quan
Không đưa tên người, tên công ty thật, số điện thoại.
```

- LLM sinh dữ liệu **không được** là model dùng cho RR5 hay chấm nhãn (quy tắc file 09 mục 2), để tránh vòng tròn.
- Chạy với nhiệt độ ≈ 0,8 để câu đa dạng. Lưu `prompt_version`, `model_id`.

### 3.3 Nguồn B: gạch CV thật + đào mẫu âm khó

Mục đích: model không chỉ quen văn phong của LLM.

1. Lấy gạch CV thật **đã ẩn danh** (A3, A7) từ kho, **trừ** CV thuộc bộ test.
2. Với mỗi `query`, dùng **bge-m3 gốc** chấm BERTScore với các gạch, lấy **top 30**.
3. Cho cross-encoder `bge-reranker-v2-m3` chấm 30 cặp đó:
   - điểm teacher ≥ 0,8 (ƯL) → ứng viên **dương**
   - điểm teacher ≤ 0,3 nhưng BERTScore gốc cao → **âm khó**. Đây là chỗ model gốc đang nhầm, quý nhất.
   - ở giữa → bỏ, vì không chắc.
4. **Lọc âm giả:** một gạch bị coi là âm nhưng teacher cho điểm cao thì bỏ khỏi `negs`. Âm giả là lỗi hay gặp nhất khi đào âm khó.

> **Quyền riêng tư:** gạch CV thật chỉ chạy qua model **cục bộ** (bge-m3, cross-encoder). Không gửi lên API LLM bên ngoài (07 Phụ lục).

### 3.4 Nguồn C: biến đổi tự động (không tốn tiền)

Áp lên một phần mẫu đã có, tạo bản **mới** chứ không thay bản gốc:

- đổi tên chuẩn ↔ alias theo KB: "Kubernetes" → "K8s", "React" → "ReactJS";
- bỏ dấu tiếng Việt (≈10% số mẫu);
- dịch câu dương sang tiếng Anh (≈10%).

### 3.5 Kiểm chất lượng (bắt buộc)

- Rút ngẫu nhiên **200 mẫu**, người xem: dương có đúng là dương, âm có đúng là âm không. Tỉ lệ sai > 10% thì sửa prompt hoặc ngưỡng rồi sinh lại.
- Loại mẫu trùng hoặc gần trùng (cosine > 0,95).
- Báo thống kê: số mẫu theo nguồn, theo nhóm vai trò, theo loại âm, độ dài trung bình.

---

## 4. Train như thế nào

### 4.1 Chuẩn bị đầu vào: giống hệt lúc chạy thật

Áp **đúng** chuẩn bị đầu vào ở 07 mục 2.1 cho cả `query` lẫn gạch: `text_raw` (giữ dấu, hoa/thường), đổi alias về tên chuẩn, che số → `N`. Nếu train và chạy thật chuẩn bị khác nhau, model học xong sẽ lệch.

> Riêng các bản alias ở Nguồn C thì **không** đổi alias, để model tự học nối K8s ↔ Kubernetes. Thí nghiệm R-E8 sẽ cho biết sau khi train còn cần bước đổi alias không.

### 4.2 Cấu hình LoRA (ƯL)

| Tham số | Giá trị | Ghi chú |
| --- | --- | --- |
| Model gốc | `BAAI/bge-m3@5617a9f61b` | lấy hidden state layer 24, chuẩn hoá L2 từng token |
| `r` / `lora_alpha` / `dropout` | 16 / 32 / 0,1 | ít dữ liệu (< 3k) thì `r = 8` |
| `target_modules` | `query`, `key`, `value`, `dense` | các lớp tuyến tính của XLM-R |
| `max_len` | 128 token | một gạch thường < 100 token |
| Learning rate | 1e-4, warmup 10%, giảm tuyến tính | |
| Batch | 32 câu JD (mỗi câu kèm 1 dương + 4–7 âm) | |
| Epoch | 1–3 | chọn theo dev |
| Kiểu số | fp16 (autocast) + gradient checkpointing | |
| Phần cứng | Kaggle T4 16 GB (miễn phí ≈30 giờ/tuần) | GTX 1650 4 GB chỉ chạy thử được với batch rất nhỏ |
| Seed | cố định, ghi vào log | |

Thời gian ước lượng: 10k mẫu × 3 epoch trên T4 ≈ 1–3 giờ (ƯL).

### 4.3 Hàm loss

Gồm hai phần cộng lại:

**(1) Contrastive (InfoNCE):** "trong một nhóm gạch, gạch dương phải đứng đầu".

```
s_k = R(q, d_k) / τ           với d_k chạy trên: pos, các negs, và gạch của mẫu khác trong batch
L_nce = − log( exp(s_pos) / Σ_k exp(s_k) )         τ = 0,05 (ƯL)
```

Gạch của mẫu khác trong batch (*in-batch negatives*) là âm miễn phí, nên batch càng lớn càng tốt.

**(2) Chưng cất từ cross-encoder (KL):** "học cả *mức độ*, không chỉ đúng/sai". Cross-encoder đọc cả cặp cùng lúc nên phán chính xác hơn, nhưng chậm. Ta để BERTScore học bắt chước thứ tự điểm của nó:

```
p_teacher = softmax(teacher_scores / τ_t)    (trên pos + negs)
p_student = softmax(R(q, ·) / τ)
L_kd = KL(p_teacher ‖ p_student)
```

**Tổng:** `L = L_nce + λ × L_kd`, với λ = 0,5 (ƯL). Thí nghiệm λ = 0 để biết chưng cất có giúp không.

### 4.4 Code khung (PyTorch + `peft`)

```python
from transformers import AutoModel, AutoTokenizer
from peft import LoraConfig, get_peft_model
import torch, torch.nn.functional as F

tok = AutoTokenizer.from_pretrained("BAAI/bge-m3", revision="5617a9f61b")
base = AutoModel.from_pretrained("BAAI/bge-m3", revision="5617a9f61b")
model = get_peft_model(base, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.1,
                       target_modules=["query", "key", "value", "dense"]))
model.gradient_checkpointing_enable()

def token_emb(texts):
    b = tok(texts, padding=True, truncation=True, max_length=128, return_tensors="pt").to("cuda")
    h = model(**b).last_hidden_state                       # layer 24
    mask = b["attention_mask"].clone()
    mask[:, 0] = 0                                         # bỏ <s>
    mask[torch.arange(len(texts)), b["attention_mask"].sum(1) - 1] = 0   # bỏ </s>
    return F.normalize(h, dim=-1), mask

def bertscore_recall(q, qm, d, dm):
    # q: [B, Lq, H] ; d: [N, Ld, H]  →  R: [B, N]
    sim = torch.einsum("bqh,ndh->bnqd", q, d)
    sim = sim.masked_fill(dm[None, :, None, :] == 0, -1e4)
    best = sim.max(-1).values                              # max theo từ của gạch
    return (best * qm[:, None, :]).sum(-1) / qm.sum(-1, keepdim=True)   # mean theo từ của q

# mỗi bước: q = B câu JD; docs = B dương + tất cả âm của batch
# R = bertscore_recall(...);  L = CE(R/τ, nhãn = vị trí dương) + λ·KL(teacher ‖ R/τ)
```

Giữ mọi thứ khác **giống hệt** RR2 ở 07: cùng layer, bỏ `<s>`/`</s>`, không IDF, Recall. Nhờ vậy model train xong cắm vào là chạy.

### 4.5 Theo dõi trong lúc train

Mỗi ≈ 500 bước tính trên **dev**:

- **AUC** của `R` (dương vs âm), tách theo loại âm (`negation`, `coursework`…);
- **MRR**: dương có đứng đầu nhóm không;
- golden T01–T24 (chạy nhanh, < 1 phút).

Lưu checkpoint có AUC dev cao nhất. AUC dev tăng mà golden tụt → dấu hiệu model "học vẹt" văn phong LLM, nên dừng sớm.

---

## 5. Đánh giá sau train (thí nghiệm R-E15)

| Bước | Đo | Điều kiện giữ model fine-tune (ƯL) |
| --- | --- | --- |
| 1 | **Golden G1** (T01–T24, F01–F05) | ≥ 25/26, không test nào ✅ → ❌; F01–F04 vẫn lệch 0 |
| 2 | **AUC trên 300 cặp người gán** | tăng ≥ 0,03 so với bge-m3 gốc |
| 3 | **nDCG@10** trên bộ nhãn JD (file 09), bootstrap 95% | tăng ≥ 2 điểm, hoặc ngang nhưng sửa được T19 |
| 4 | So với cross-encoder R-X1 | báo khoảng cách còn lại và chênh tốc độ |
| 5 | Tốc độ RR2 | không đổi (đã gộp LoRA) |

Bảng kết quả gợi ý cho Chương 4:

| Cấu hình | Golden | AUC 300 cặp | nDCG@10 | ms/CV |
| --- | --- | --- | --- | --- |
| cosine câu (R-E2) | | | | |
| BERTScore bge-m3 gốc | 25/26 | | | 116 |
| **BERTScore bge-m3 + LoRA** | | | | ≈116 |
| + LoRA, bỏ luật `m_neg`, `m_course` | | | | |
| cross-encoder (R-X1, mốc trên) | | | | |

**Báo trung thực:** fine-tune không hơn bản gốc thì vẫn ghi kết quả và giữ bản gốc trên đường chính (quy tắc file 09 mục 4.5).

---

## 6. Gắn vào hệ thống

- Gộp LoRA vào model (`merge_and_unload`), lưu kèm hash. Khoá mới: `bertscore_config = bge-m3-lora-v1@<hash>/L24/noidf/norescale/2048/mask1`.
- **Đổi khoá thì cache token cũ không dùng được** (07 mục 6). Phải tính lại embedding gạch.
- **Retrieve vẫn dùng bge-m3 gốc**, để tách riêng tác dụng của fine-tune ở Rerank. Có thể thử dùng chung sau.
- **Hiệu chuẩn lại** `b4.calib.lo / hi`, ngưỡng mức khớp và `align.word_sim_min`, vì phân bố điểm sẽ đổi.
- Cập nhật Q4, Q5 (file 00), lộ trình P2/P3 (file 11) và thêm R-E15 vào file 09 khi bắt đầu làm.

---

## 7. Lộ trình (ƯL)

| Tuần | Việc | Đầu ra |
| --- | --- | --- |
| 1 | Gom JD hạt giống, viết prompt, sinh thử 200 mẫu, kiểm tay | prompt chốt, tỉ lệ lỗi < 10% |
| 2 | Sinh đủ Nguồn A, làm Nguồn B (đào âm khó), Nguồn C; chia train/dev | `train.jsonl`, `dev.jsonl`, bảng thống kê |
| 3 | Chạy thử trên 1k mẫu (kiểm code, loss giảm), rồi train đầy đủ + thử λ, `r` | checkpoint tốt nhất theo dev |
| 4 | Đánh giá R-E15, hiệu chuẩn lại, viết kết quả | bảng mục 5, quyết định giữ / bỏ |

Điều kiện trước: đã có bộ 300 cặp người gán và bộ nhãn JD (P2 ở file 11). Chưa có thì vẫn train được, nhưng chỉ đánh giá được bằng golden và dev.

---

## 8. Rủi ro và cách xử lý

| Rủi ro | Xử lý |
| --- | --- |
| Model học văn phong LLM thay vì nghĩa | trộn Nguồn B (gạch thật); theo dõi golden; dev có gạch thật |
| Âm giả (gạch thật ra khớp nhưng bị gán âm) | lọc bằng điểm teacher; kiểm tay 200 mẫu |
| Rò rỉ dữ liệu test vào train | loại JD/CV của bộ test; lọc trùng cosine > 0,95 |
| Train làm hỏng điểm mạnh cũ (đa ngôn ngữ, bất biến F01–F04) | giữ 10% mẫu tiếng Anh; G1 là điều kiện bắt buộc |
| Phủ định vẫn yếu | giữ luật `m_neg`; báo đây là giới hạn của MaxSim |
| Không đủ GPU | Kaggle T4; giảm `max_len` 96, batch 16, tăng số âm mỗi mẫu |
| Kết quả không hơn bản gốc | báo trung thực; vẫn là đóng góp: bộ dữ liệu + phân tích theo loại âm |
