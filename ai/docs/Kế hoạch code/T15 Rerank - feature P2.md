# T15 · Rerank và Retrieve: feature P2

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `07` mục 5.4, 5.5, 5.6 (B3), 5.7 · `02` mục 7 · `06` view (d) · `11` lộ trình P2.

**Điều kiện:** KB snapshot đã có `PARENT_OF` / `sibling_ok` đáng kể (T01); đã có tập 300 cặp để hiệu chuẩn (T14) — nếu chưa thì vẫn code, giữ `lo/hi` mặc định.

## Làm

1. **A1/A2 qua KB**: `score_req(r) = max_{s ∈ CV, s ∈ options(r)} rel(s, r) × ev(s)`; nhóm "A hoặc B" là một yêu cầu, `w_imp` = max nhóm; kỹ năng JD không có trong KB → loại khỏi tử/mẫu + cờ `unmapped_req`; A2 cùng công thức trên kỹ năng không bắt buộc (`null` nếu không có). `skill_facts.partial` ghi quan hệ `parent|child|sibling`.
2. **B5**: như B4 nhưng câu JD = `jd_requirement_item` `kind = text`; phía CV = gạch + câu của `summary` (tách câu, giữ `text_raw` — cần thêm `summary_sentences` vào dữ liệu CV: nếu T04 chưa lưu thì bổ sung cột/bảng qua migration mới và tăng `pipeline_version`).
3. **B3** cấp bậc: `level_cv` theo thứ tự (chức danh → tín hiệu phạm vi trong gạch +1 → số năm B2 → trần Fresher cho sinh viên); `fit(Δ)` hai nhánh; tính Spearman ρ(B2, B3) trong pool và log ra.
4. **C1** học vấn: `0,6 × major_rel + 0,4 × degree_status`; người đã tốt nghiệp luôn 1,0; `null` JD khi `edu_required` ∈ {none, NULL}; không dùng tên trường/GPA.
5. Bật view **trách nhiệm** đầy đủ ở Retrieve (nếu P1 đã tắt) và cho R-E10 (`c_j = max(BERTScore, cosine câu)`) dưới dạng tuỳ chọn config.
6. Cập nhật `FinalItem` (`req_facts`, `experience_facts.level_*`) và mẫu Explain cho các feature mới.
7. Tạo `config/rr-1.1.yaml` bật đủ 8 feature; giữ `rr-1.0` để so.

## Tiêu chí xong

- Test `rel`: CV có Spring Boot, JD cần Java → score_req = 0,7 × ev.
- Test C1: tốt nghiệp `it` → 1,0; đang học, còn 8 tháng, ngành `related` → 0,6×0,7 + 0,4×0,7.
- Test B3: Δ = −1 → 0,70; +2 → 0,70.
- Test 5.10 chạy lại với đủ feature → 79.
- Chạy ablation R-E1, R-E9, R-E11 bằng T14 (trên dữ liệu có sẵn).

## Ghi chú bàn giao

_(agent điền)_
