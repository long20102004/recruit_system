# 11 · Tham số cấu hình, lộ trình và điểm còn mở

> **Phiên bản:** 2.0 (09/11/2026). Gom bảng tham số, lộ trình và các câu hỏi mở của mọi tầng vào một chỗ.
> Tất cả tham số đặt trong **file cấu hình có phiên bản**, không viết cứng trong code. Mỗi `match_run` và `rerank_run` ghi lại cấu hình đã dùng.

---

## 1. Bảng tham số

Mọi giá trị là **(ƯL)** trừ khi ghi "đã test".

### 1.1 Tiền xử lý ([[04 Tiền xử lý - Luồng A (CV)]], [[05 Tiền xử lý - Luồng B (JD)]])

| Tham số | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `ev.in_description` | 1,0 | kỹ năng nằm trong mô tả kinh nghiệm/dự án |
| `ev.in_technologies` | 0,8 | chỉ nằm trong `technologies` |
| `ev.listed_only` | 0,6 | chỉ liệt kê (`skills`, `summary`, `certificates`) |
| `w_imp.core / medium / minor` | 1,0 / 0,7 / 0,4 | mức quan trọng kỹ năng JD; thiếu `importance` → 1,0 |
| `bullet.min_words` | 4 | bỏ gạch / trách nhiệm ngắn hơn |
| `no_diacritics.threshold` | 5% | tỉ lệ âm tiết có dấu tối thiểu với CV tiếng Việt |
| `negation_patterns`, `coursework_patterns`, `generic_resp_patterns` | danh sách | cần người duy trì |
| `jd.min_query_words` | 50 | dưới mức này cảnh báo HR |
| `unknown_skill.warn_ratio` | 30% | tỉ lệ kỹ năng JD không gắn được mã để cảnh báo |

### 1.2 Retrieve ([[06 Retrieve]])

| Tham số | Mặc định | Ghi chú |
| --- | --- | --- |
| `K` | 200 | chốt bằng đường Recall theo K |
| `views_enabled` | dense, bm25, skill, resp | `resp` là "thử" |
| `view_weights` | bằng nhau | chỉ đổi khi có bằng chứng rõ |
| `normalization` | `minmax` | thí nghiệm với `dbsf` |
| `fusion` | `score_sum` | `rrf` là dự phòng |
| `embed_model` | `bge-m3@5617a9f61b` | RT-E7 |
| `bm25.k1`, `bm25.b` | 1,2 / 0,75 | giữ mặc định |
| `bm25.query_mode` | `full_jd` | RT-E5 so với `title_skills` |
| `hard_filters` | tắt | chỉ khi HR bật; trường thiếu → cho qua |
| `reverse.only_open` | `true` | không tắt được |
| `reverse.K` | `min(50, số JD mở)` | |
| `reverse.bm25_query_mode` | `condensed_cv` | RT-R2 |
| `reverse.skill.min_imp_sum` | 3,0 | RT-R3 (tên cũ `min_rel_sum`) |
| `reverse.min_pool_minmax` | 10 | dưới ngưỡng dùng RRF (RT-R5) |

### 1.3 Rerank ([[07 Rerank - BERTScore với bge-m3]])

| Tham số | Mặc định | Ghi chú |
| --- | --- | --- |
| `rerank.N` | 30 (chiều CV → JD: 10) | HR đổi được |
| `bertscore.model` | `BAAI/bge-m3@5617a9f61b` | **đã test** |
| `bertscore.layer` | 24 | **đã test**; R-E4 |
| `bertscore.idf` | false | **đã test**; R-E14 |
| `bertscore.rescale_baseline` | false | **đã test** |
| `bertscore.score` | `recall` (JD là tham chiếu) | **đã test**; R-E3 |
| `bertscore.split` | `S2` | **đã test**; R-E3 |
| `bertscore.max_len` | 2048 | **đã test** |
| `bertscore.dtype` | fp32 | fp16 sau khi kiểm lệch < 0,001 |
| `bertscore.input` | `text_raw` | giữ dấu, hoa/thường |
| `bertscore.canonicalize_aliases` | true | R-E8 |
| `bertscore.mask_numbers` | true | R-E8 |
| `b4.calib.lo / hi` | 0,65 / 0,90 | từ golden; thay bằng giá trị theo nhãn (R-E5) |
| `b4.level.met / partial` | 0,6 / 0,3 | ngưỡng mức khớp cho Explain |
| `b4.m_negation / m_coursework` | 0,3 / 0,6 | R-E6 |
| `b4.generic_weight` | 0 | R-E7 |
| `align.word_sim_min` | 0,75 | ngưỡng từ được tính là "đã phủ" |
| `weights` | A1 0,25 · A2 0,05 · B4 0,28 · B5 0,12 · B1 0,10 · B2 0,10 · B3 0,05 · C1 0,05 | tổng 1,00; R-E13 |
| `rel.same / parent_child / sibling` | 1,0 / 0,7 / 0,4 | kiểm độ nhạy sibling 0,5 |
| `b1.recent_months / recent_boost` | 36 / ×2 | |
| `b2.project_personal_weight` | 0,3 | |
| `b2.overqual_penalty` | bật (JD → CV), tắt (CV → JD) | R-E11 |
| `gate.thresholds / caps` | (0,5; 0,7) / (50; 70) | R-E12 |
| `missing.cv_side_policy` | `pool_median` | R-E12 |
| `low_data_quality.min_missing` | 3 | |
| `score.bands` | 80 / 60 | dải nhãn hiển thị |
| `rr5.enabled` | false | R-X4 |
| `cache.token_lru_gb` | 20 | |

### 1.4 Explain ([[08 Explain]])

| Tham số | Mặc định |
| --- | --- |
| `explain.mode` | `template` (P1); `llm` là tuỳ chọn P2 |
| `explain.lazy` | true (chỉ tạo khi HR mở chi tiết) |
| `explain.max_questions` | 3 (mẫu), 2–4 (LLM) |

---

## 2. Lộ trình

| Giai đoạn | Nội dung | Tiêu chí hoàn thành |
| --- | --- | --- |
| **P0 Chuẩn bị** | chốt schema thật CV/JD JSON; cấp `skill_id` cho KB; chạy **script độ phủ Module 1** (mục 2.1); dựng bộ nhãn graded; golden test bge-m3 (**đã xong**, file 10) | tài liệu nhất quán (bản 2.0 này); báo cáo độ phủ; ≥ 20 JD có nhãn |
| **P1 Bản chạy tối thiểu** | Luồng A, B; Retrieve với dense + BM25 + view kỹ năng; Rerank: A1 = `s_skill`, **B4 BERTScore**, B1, B2, cổng; Explain bằng mẫu xác định | chạy trọn một JD từ JSON đến giải thích; log đủ; so với R-A0 |
| **P2 Hoàn thiện và đo** | KB có quan hệ cha/con → A1, A2; B5, B3, C1; view trách nhiệm ở Retrieve; tập 300 cặp → hiệu chuẩn `lo/hi`; G2; ablation RT-E*, R-E1–R-E14; Explain LLM (tuỳ chọn) | bảng ablation, đường cong chi phí–chất lượng, cấu hình chốt theo quy tắc 09 mục 4.5 |
| **P3 Mở rộng** | Luồng D + RT-R*; mốc đối chứng R-X1–R-X4; thử nghiệm bất biến đầy đủ; HyDE ngược; phục hồi dấu tiếng Việt | báo cáo công bằng; kết luận về cross-encoder và LLM |
| **P4 Tuỳ chọn** | phản hồi HR → nhãn; hiệu chuẩn điểm (isotonic); fine-tune embedding | ngoài phạm vi nếu hết thời gian |

Lịch theo tuần ước lượng sau P0, khi đã biết độ phủ Module 1 và công chấm nhãn.

### 2.1 Script độ phủ Module 1 (P0)

Chạy trên 100 CV và 20 JD thật, đếm tỉ lệ có từng trường. Feature chưa đạt ngưỡng thì **tắt** và ghi vào báo cáo, không đoán bù.

| Trường | Dùng cho | Ngưỡng để bật (ƯL) |
| --- | --- | --- |
| `title`, `start`, `end`, `is_current` của mỗi mục kinh nghiệm | B1, B2, B3 | ≥ 80% CV có ít nhất một mục đủ ngày |
| `description` dạng gạch (mảng hoặc tách được) | **B4, B5** | ≥ 80% CV có ≥ 1 gạch |
| `major`, `end` học vấn | C1, B3 (trần Fresher) | ≥ 70% CV |
| JD: `responsibilities` | **B4** | ≥ 90% JD (thiếu → `null` phía JD, không phải lỗi) |
| JD: `skills` kèm `required` / `importance` | A1, A2 | ghi nhận; thiếu thì `w_imp = 1`, mọi kỹ năng là bắt buộc |
| JD: `min_years`, `level`, `role_group`, yêu cầu học vấn | B1–B3, C1 | thiếu → `null` phía JD |
| Loại mục (job / dự án) | B2 | ≥ 70% |

---

## 3. Điểm còn mở

### 3.1 Dữ liệu đầu vào

1. **Schema thật của CV JSON và JD JSON.** Tên trường trong tài liệu là giả định. Đặc biệt cần biết: `description` là mảng hay đoạn văn; có `technologies` riêng không; định dạng ngày tháng.
2. **Module 1 có trả `required` và `importance` cho từng kỹ năng không?** Nếu không, mọi kỹ năng coi là bắt buộc với `w_imp = 1`, hoặc thêm bước phân loại.
3. **Nhóm vai trò:** KB có 8 nhóm. Module 1 có dùng nhóm khác không (AI/ML, BA, PM…)?
4. **Số JD đang mở thực tế** (giả định vài chục đến vài trăm) và **người dùng của Luồng D** (ứng viên hay HR). Hai điều này ảnh hưởng chính sách dữ liệu và cách giải thích.

### 3.2 Knowledge Base

5. Cấp `skill_id` (KB đang dùng khoá `key`).
6. Ai duyệt `candidate`, bật `sibling_ok`, duyệt `unknown_skill`, và bao lâu một lần.
7. Có thêm quan hệ bất đối xứng hay không (để sau, chỉ khi ablation cho thấy có ích).

### 3.3 Tiền xử lý

8. Alias dễ nhầm trong mảng `skills`: có cho khớp khi alias là nguyên một phần tử không (đề xuất ở A5).
9. Quy tắc suy `level_rank` từ số năm khi chức danh không có từ cấp bậc.
10. Công cụ tách từ tiếng Việt (pyvi, underthesea hay VnCoreNLP) và cách nó xử lý token được bảo vệ.
11. Ai lập và duy trì các danh sách mẫu: trách nhiệm chung chung, phủ định, học tập.
12. Ngưỡng và cách phát hiện `no_diacritics`; có làm phục hồi dấu không, bằng công cụ nào.

### 3.4 BERTScore và Rerank

13. **Ảnh hưởng của chỉ chữ thường** (không bỏ dấu) lên BERTScore chưa được test riêng; F05 trộn cả hai. Chạy thêm một biến thể của F05.
14. **Chi phí trên CV thật** (≈30 gạch, gạch dài hơn) và lợi ích của cache. Golden test đo trên CV ngắn.
15. **"Gần cross-encoder"** mới là ghi nhận từ test hành vi. Phải xác nhận bằng R-X1 trước khi viết vào báo cáo.
16. Giá trị `lo/hi`, ngưỡng mức khớp, `m_negation`, `m_coursework`, ngưỡng `align.word_sim_min` cần tập 300 cặp có nhãn.
17. Cách đọc "tình trạng bằng" trong C1 (đã chọn: thời gian **còn lại** đến lúc tốt nghiệp của sinh viên).
18. Nếu bật RR5 hoặc Explain bằng LLM: dùng model cục bộ hay API, và chính sách dữ liệu CV.

### 3.5 Đánh giá

19. Số CV và JD thật cho bộ nhãn. Dưới 30 JD thì kết luận ablation chỉ nên trình bày như xu hướng.
20. Ai chấm nhãn (2 người), và định nghĩa "phù hợp" (≥ 1 hay = 2).

### 3.6 Giả định nền (để nhớ khi viết báo cáo)

- Bằng chứng nghiên cứu cho Retrieve đến từ tuyển dụng tiếng Anh/Trung/Tây Ban Nha và benchmark tiếng Việt lĩnh vực khác; không có nghiên cứu nào đo trực tiếp CV–JD tiếng Việt ngành IT.
- View trách nhiệm ở Retrieve và toàn bộ chiều CV → JD là suy luận, chưa có bằng chứng trực tiếp.
- Mọi con số (ƯL) chưa được đo.
