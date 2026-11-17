# T12 · Explain: mẫu xác định (P1)

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `08` mục 0–3, 4 (phần "Kiểm tra bằng code" — áp được cho cả template), 6 · `07` mục 5.3 (mức khớp), 5.10 (dải điểm).

## Mục tiêu

Từ `FinalItem` sinh lời giải thích tiếng Việt **không dùng LLM**, mọi số và trích dẫn do code điền, bằng chứng là `text_raw` thật.

## Làm

1. `explain/facts.py` — **EX1**: dựng/hoàn thiện `FinalItem` từ `rerank_feature` + `cv_skill` + `cv_bullet` (khi chỉ có `run_id`, `cv_id`).
2. `explain/template.py` — **EX2, EX3**: đúng khung mẫu ở thiết kế 08 mục 3:
   - Điểm + `band` (≥ 80 "phù hợp cao", 60–79 "cân nhắc", < 60 "thấp", đọc từ config) + ghi chú "điểm xếp hạng tương đối"; câu giới hạn khi `cap_applied`.
   - Điểm mạnh: kỹ năng bắt buộc có / tổng; trách nhiệm có bằng chứng (ví dụ "resp" ← "text_raw" + matched_words); số năm liên quan, nhóm vai trò.
   - Chưa thấy bằng chứng: kỹ năng thiếu, trách nhiệm `not_evidenced` / `partial` kèm `missing_words`.
   - Gợi ý ≤ `explain.max_questions` câu phỏng vấn từ mục `partial`/gap.
   - Nhãn "(mô tả học tập)" / "(câu có phủ định, cần xác minh)" cho gạch có cờ.
   - Cố định câu chữ: "chưa thấy bằng chứng về X trong CV", không viết "ứng viên không có X".
   - Đầu ra hai dạng: `explanation_json` có cấu trúc (cho frontend tô đậm `matched_words` theo vị trí) và chuỗi văn bản.
   - Mẫu đặt trong file (Jinja2 hoặc mustache), có `template_version`.
3. `explain/checks.py` — **EX4**: kiểm (1) mọi `evidence_id` thuộc CV này; (2) mọi tên công nghệ xuất hiện thuộc {kỹ năng JD ∪ CV}; (3) không có từ nhạy cảm/lời khuyên tuyển–loại; (4) có câu giới hạn khi `cap_applied`. Với template, lỗi kiểm = bug → raise, có test.
4. `explain/service.py`: chạy **lười** (chỉ khi được gọi cho một `cv_id`), cache theo `hash(facts, template_version)`, ghi `rerank_result.explanation_json`.
5. Chừa interface `Explainer` để T17 thêm bản LLM (`mode: template | llm`).

## Tiêu chí xong

- Test với `FinalItem` của CV mẫu × JD mẫu → văn bản có "79/100", "3/3 kỹ năng bắt buộc" (theo dữ liệu), trích đúng "Xây dựng API thanh toán bằng Spring Boot", không có chữ số nào ngoài số do code điền.
- Test `cap_applied` → có câu giới hạn.
- Test gạch phủ định được chọn làm bằng chứng → có nhãn cần xác minh.
- Snapshot test (so với file mong đợi) để phát hiện thay đổi câu chữ ngoài ý muốn.

## Ghi chú bàn giao

**Trạng thái: xong (16/11/2026).** 8 test đơn vị + 1 test tích hợp (lười, cache, CV ngoài top N) + snapshot `tests/fixtures/explain/sample_79.txt` (cập nhật có chủ đích: `CVMATCH_UPDATE_SNAPSHOT=1`). Toàn bộ 182 test thường + 6 test GPU qua.

- **Dùng:**
  - `ExplainService(cfg, snapshot).explain(conn, rerank_run_id, cv_id, force=False) -> explanation_json` (lười; cache theo `sha256(template_version + facts)` trong `rerank_result.explanation_json`; CV ngoài top N không có dòng `rerank_result` nên không cache DB).
  - `TemplateExplainer(cfg, snapshot).explain(item: FinalItem, cv_evidence=None, allowed_skills=None)`; interface `Explainer` (thuộc tính `version`, hàm `explain`) để T17 thêm bản LLM.
  - `explain.facts.load_final_item(conn, run_id, cv_id)` (EX1): đọc `facts_json`, hoặc dựng lại từ `rerank_feature` + `cv_skill` + `cv_bullet` + bảng JD. Có test: kết quả dựng lại trùng FinalItem do RR6 dựng.
  - CLI: `cvmatch explain <rerank_run_id> <cv_id> [--json] [--force]`.
  - `explanation_json` = `{mode, template_version, cache_key, cv_id, score, band, band_label, cap_applied, text, sections}`. `sections.resp.examples[].highlight` là vị trí `(start, end)` của `matched_words` trong `resp_text` để frontend tô đậm.
- **Mẫu:** `config/templates/explain-tpl-1.0.j2` (Jinja2, thêm `jinja2` vào dependencies). **Mọi câu chữ nằm trong mẫu**, code chỉ truyền số, chuỗi lấy từ facts và mã cờ. Mẫu không được chứa chữ số (cả thang "/100" cũng do code điền).
- **EX4** (`explain/checks.py`, lỗi → `ExplainCheckError`): bằng chứng thuộc CV; tên công nghệ (chỉ loại `technology`, bỏ phần trích trong ngoặc kép) ⊂ kỹ năng JD ∪ CV; từ cấm trong `config/patterns/explain_forbidden.txt`; câu giới hạn khi `cap_applied`; không chữ số. Kiểm từ cấm và chữ số chạy trên **bản render đã che dữ liệu** (mọi giá trị code điền → "§"), nên số trong gạch CV ("giảm 40%") hay chữ "gia đình" trong JD không làm hỏng kiểm tra.
- **Thay đổi so với thiết kế, cần người dùng biết:**
  - **Căn khớp từ (07 mục 5.3):** đo trên bge-m3 thật thấy embedding layer 24 mang ngữ cảnh mạnh. Trong một cặp có liên quan, từ **vắng mặt** vẫn đạt 0,78–0,89 (vd "Thiết kế" 0,894 với gạch "Phát triển API thanh toán bằng Django"), từ có mặt 0,86–0,98, cặp không liên quan ≤ 0,72. Ngưỡng 0,75 biến mọi từ thành "khớp". Đã đổi: **khớp nếu từ xuất hiện nguyên văn trong gạch (văn bản đã chuẩn bị, nên K8s ↔ Kubernetes vẫn khớp) hoặc cosine ≥ 0,90**. Tiếp tục hiệu chuẩn ở T14.
  - Từ của trách nhiệm được gộp từ âm tiết bằng pyvi ("thiết kế", "thanh toán"), trước đây tách từng âm tiết. pyvi đôi khi vẫn tách sai ("truy", "vấn").
  - Mục "Điểm mạnh" chỉ có dòng kỹ năng khi đáp ứng ≥ 1 kỹ năng (không viết "có 0/2"). Ví dụ trách nhiệm đã khớp hiện thêm "chưa thấy phần: …" như ví dụ ở 07 mục 5.3.
  - Câu hỏi phỏng vấn: trách nhiệm `partial` trước, rồi `not_evidenced`, rồi kỹ năng thiếu; tối đa `max_questions`.
- **Quan sát trên DB thật:** tên chuẩn chữ thường ("java") lộ ra trong lời giải thích. Cần sửa tên chuẩn trong KB (đã ghi ở T01).
