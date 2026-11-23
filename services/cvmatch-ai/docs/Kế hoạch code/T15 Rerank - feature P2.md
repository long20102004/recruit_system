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

**Trạng thái: xong code (23/11/2026). `rr-1.1.yaml` bật đủ 8 feature nhưng `active.yaml` vẫn dùng `rr-1.0`** — theo quy tắc 09 mục 4.5 chỉ bật khi ablation trên nhãn thật cho thấy có ích.

- **A1/A2 qua KB** (`a1.use_kb_rel: true`): đã có công thức `rel × ev`, nhóm "A hoặc B"; thêm A2 (null phía JD khi không có kỹ năng ưu tiên), cờ `unmapped_req` (kỹ năng bắt buộc của Module 1 không gắn được mã), `min_den` cho chiều ngược.
- **B5**: câu JD = `jd_requirement_item.kind = text`; phía CV = gạch + câu `summary`. Câu summary lưu ở bảng mới `cv_summary_sentence` (migration 007) → **`prep-1.1`** (đã đặt trong `active.yaml`; kho cũ chạy `cvmatch reprocess cv --from A8`). Bằng chứng summary có `evidence_id = "summary[k]"` (thêm `SentenceDetail.evidence_id`).
- **B3**: `cv_level` theo thứ tự chức danh → +1 nếu có tín hiệu phạm vi (`config/patterns/scope_signals.txt`) → số năm B2 qua `prep.level_from_years` → trần Fresher (đang học, < 2 năm). Bậc suy từ tổng năm của A6 (`level_source = inferred`) bị bỏ, dùng số năm liên quan B2. ρ(B2, B3) ghi ở `rerank_run.config_json.stats`, cảnh báo khi > 0,7.
- **C1**: `status = unknown` coi như đã tốt nghiệp (không phạt vì thiếu ngày); lấy mục học vấn tốt nhất; `edu_required` ∈ {none, NULL} → null phía JD.
- **Retrieve**: view trách nhiệm đã bật từ P1; thêm `retrieve.resp_calib` (lo/hi, mặc định tắt). **R-E10/R-E2**: `rerank.b4.engine: bertscore | cosine | max` + `cos_calib`.
- **FinalItem**: `req_facts`, `experience_facts.level_source`, `edu_fit`; Explain `tpl-1.1` (`explain-1.1.yaml`, đã bật) thêm dòng yêu cầu chuyên môn, cấp bậc, lưu ý `unmapped_req`. `tpl-1.0` giữ nguyên (snapshot test cả hai).
- **Tiêu chí**: test `rel` (0,7 × ev), C1 (1,0; 0,6×0,7 + 0,4×0,7), B3 (−1 → 0,70; +2 → 0,70), 5.10 đủ feature → 79 (`tests/unit/test_rerank_p2.py`); tích hợp `tests/integration/test_rerank_p2_db.py`. Ablation R-E1, R-E9, R-E11 đã chạy bằng T14 (nhãn tổng hợp, xem T14).
