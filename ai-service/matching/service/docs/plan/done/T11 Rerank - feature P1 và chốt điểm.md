# T11 · Rerank: feature P1 (A1, B4, B1, B2), thiếu dữ liệu, cổng, điểm 0–100

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `07` mục 4, 5 (toàn bộ, đặc biệt 5.1–5.3, 5.5 dòng P1, 5.6 B1/B2, 5.8–5.10), 6, 8 · `08` mục 1 (`FinalItem`) · `11` mục 1.3.

## Mục tiêu

`rerank(request: RerankRequest) -> list[FinalItem]` chạy RR1–RR4, RR6 với bộ feature của P1. Feature P2 (A2, B5, B3, C1) có khung nhưng `enabled: false` trong config (làm ở T15).

## Làm

1. `rerank/run.py`
   - **RR1** tải theo lô cho ≈200 CV: `cv_bullet` (`text_raw`, cờ), `cv_skill`, `cv_experience`, `cv_education`, `cv.flags`, `cv_meta.n_bullets`; phía JD: `jd_responsibility` (bỏ `is_generic` theo `b4.generic_weight`), `jd_requirement_item`, `jd_skill`, `jd_meta`, ma trận `M`.
   - **RR2** gọi engine T10 **một lần** cho mọi câu JD × mọi gạch của pool (không lặp từng cặp CV).
   - **RR3** tính feature; **RR4** chốt điểm; **RR6** ghi `rerank_run`, `rerank_feature`, `rerank_result` + dựng `FinalItem`.
2. `rerank/features/sentence_match.py` — **B4** đúng công thức 07 mục 5.3:
   - `cal_ij = clip((R_ij − lo)/(hi − lo), 0, 1) × m_i`; `m_i` = `m_negation` (0,3) / `m_coursework` (0,6) / 1.
   - `c_j = max_i cal_ij`, `best_j`; `B4 = mean_j c_j`.
   - `level` theo `b4.level.met/partial`; `matched_words`/`missing_words` từ `align` của T10.
   - `null` phía JD khi không còn trách nhiệm; `null` phía CV khi `n_bullets = 0` hoặc cờ `no_diacritics`.
   - Trả `resp_detail` đúng dạng `FeatureRow`.
3. `rerank/features/skill_match.py` — **A1 ở P1** = `s_skill` của Retrieve (lấy từ `RerankRequest`); kèm `skill_facts` (met / missing) từ `cv_skill` × `jd_skill` để Explain dùng. Khung hàm `score_req` có `rel` (T15 bật).
4. `rerank/features/experience_fit.py`:
   - **B1** `Σ_g share_g × M[g, g_JD]`, mục kết thúc trong `b1.recent_months` nhân `recent_boost`; sinh viên chưa đi làm → dùng dự án; không có → `null` CV; JD không rõ nhóm → `null` JD.
   - **B2** gộp theo **tháng** với `w_t = max` các mục phủ tháng đó; `trọng_số_loại`; `fit(y)` có/không `max_years`; công tắc `overqual_penalty`.
5. `rerank/scoring.py`:
   - Thiếu dữ liệu (5.8): `jd_side` → bỏ feature cho mọi CV; `cv_side` → `missing.cv_side_policy` = trung vị pool (đối chứng: `drop`, `zero`); ≥ `low_data_quality.min_missing` → cờ `low_data_quality`.
   - Cổng must-have (5.9) theo `gate.thresholds/caps`.
   - `S_raw = Σ w_f f / Σ w_f` trên feature khả dụng; `score = round(min(100 × S_raw, gate_cap))`; xếp hạng `score` ↓ → `S_raw` ↓ → `A1` ↓ → `cv_id` ↑; cắt top N.
   - Cờ: địa điểm, ngoại ngữ, hình thức làm việc — chỉ cảnh báo, không cộng điểm.
6. `FinalItem` đầy đủ các trường thiết kế 08 mục 1 (`gaps`, `evidence` map `bullet_id → text_raw, section, item_idx`, `flags` gồm `cap_applied`, `has_negation_bullets`…).
7. CLI: `cvmatch rerank <retrieve_run_id> [--n 30]`.

## Tiêu chí xong

- **Test vàng công thức 07 mục 5.10**: với feature cho trước (A1 0,80 · A2 0,50 · B4 0,74 · B5 0,60 · B1 1 · B2 1 · B3 1 · C1 null) → `S_raw = 0,794`, `score = 79`; A1 = 0,6 → bị giới hạn 70, `cap_applied = true`.
- **Test B4 ví dụ 5.3**: ma trận R cho trước → `c_0 = 0,76`, `c_1 = 0,72`, `B4 = 0,74`, bằng chứng 90001 / 90002.
- Test B2: min 3, max 5: y = 2,4 → 0,80; 4 → 1,0; 7 → 0,80; 12 → 0,60; chỉ có min → không phạt thừa.
- Test thiếu dữ liệu: CV `no_diacritics` → B4 = trung vị pool, có cờ; JD không có trách nhiệm → B4 bị bỏ, trọng số chia lại.
- Tái lập: chạy lại cùng request → `rerank_result` giống hệt.
- Đo thời gian rerank 200 CV thật/tổng hợp (lạnh và ấm).

## Ghi chú bàn giao

**Trạng thái: xong (16/11/2026).** 13 test đơn vị + 3 test tích hợp (Postgres, FakeEncoder); toàn bộ 172 test thường qua.

- **Dùng:**
  - `Reranker(cfg, scorer: BertScorer, snapshot).rerank(conn, request, ref_ym=None, write=True) -> RerankOutput(run_id, items: list[FinalItem] (top N), rows: list[FeatureRow] (cả pool, theo hạng), timings, warnings)`.
  - `request_from_run(conn, cfg, retrieve_run_id, N=None)` dựng lại `RerankRequest` từ `match_run`/`match_result`.
  - `rerank.cli.build_reranker(conn, cfg)` (KB từ DB, cache token RAM + bảng `bertscore_token_cache`). CLI: `cvmatch rerank <retrieve_run_id> [--n 30] [--ref-ym YYYY-MM] [--no-db-cache]`.
  - Hàm thuần: `features/sentence_match.py` (`sentence_scores`, `aggregate`, `level_of`), `features/experience_fit.py` (`b1_role`, `b2_years`, `relevant_years`, `years_fit`), `features/skill_match.py` (`coverage`, `skill_facts`, `score_req` có `rel` cho T15), `scoring.py` (`finalize`, `gate_cap`, `fill_missing`, `band`).
- **Tiêu chí:** công thức 5.10 → S_raw 0,794, score 79; A1 0,6 → 70, `cap_applied` · ví dụ B4 5.3 → c = 0,76 / 0,72, B4 0,74, bằng chứng 90001/90002 · B2 min 3 max 5 → 0,80 / 1,0 / 0,80 / 0,60, chỉ có min không phạt thừa · CV `no_diacritics` và CV không gạch → B4 = trung vị pool + cờ · JD chỉ có trách nhiệm chung chung → B4 `jd_side`, trọng số chia lại · chạy lại cùng request (kể cả request dựng lại từ DB) → `rerank_result` giống hệt.
- **Chi phí** (bge-m3 thật, GTX 1650, 200 CV tổng hợp × 8 gạch, 2 trách nhiệm): **lạnh 7,6 s** (RR2 7,4 s ≈ 37 ms/CV), **ấm 0,3–0,4 s**, đỉnh GPU 2,2 GB. Căn khớp từ cho cả pool ≈ 0,08 s. Nạp 200 CV thật bằng bge-m3: 48 s.
- **Quyết định (chỗ thiết kế chưa nói rõ):**
  - `ref_ym` (tháng tham chiếu cho "36 tháng gần nhất" của B1) mặc định là tháng hiện tại, ghi vào `rerank_run.config_json`; muốn tái lập tuyệt đối thì truyền lại cùng `ref_ym`.
  - Mọi feature làm tròn 6 chữ số trước khi chấm (`s_skill` đọc từ cột `real` và từ RAM phải ra cùng điểm).
  - B1: mục có ngày nhưng **không rõ nhóm** (vd "Designer") vẫn vào mẫu số với M = 0. Chỉ khi không có mục nào có ngày mới là `cv_side`. Nếu coi là thiếu dữ liệu thì CV ngoài IT được điền trung vị pool (thấy trên dữ liệu thật: Designer được B1 = 1).
  - B2: dự án nhóm dùng cùng trọng số với `project_personal` (0,3); JD không rõ nhóm → m_g = 1 (số năm làm việc nói chung); CV không có mục nào → y = 0 (không phải thiếu dữ liệu).
  - B4: gạch vừa phủ định vừa là học → `m_negation`. Không có gạch nào vượt `lo` → `bullet_id = null`, `level = not_evidenced`, mọi từ vào `missing_words`. Câu generic chỉ được chấm khi `generic_weight > 0`.
  - Điểm làm tròn nửa lên (round half up), không dùng round-half-even của Python.
  - `rerank_feature` ghi cho cả pool (kèm giá trị thô trước khi điền), `rerank_result` chỉ ghi top N.
  - `gaps` = tên kỹ năng bắt buộc thiếu + câu trách nhiệm `not_evidenced` + tối đa 10 `missing_words` của trách nhiệm `partial`.
  - Cờ: `no_diacritics`, `has_negation_bullets`, `has_coursework_bullets`, `location_mismatch` (khác địa điểm, JD không remote), `check_language` (JD có yêu cầu ngoại ngữ), `low_data_quality`, `cap_applied`. Không ảnh hưởng điểm.
- **Quan sát trên DB thật (5 CV):** CV Python có B4 0,95 (gạch "Phát triển API thanh toán bằng Django") nhưng A1 = 0 nên bị cổng giới hạn 50. Đúng thiết kế. A1 tối đa chỉ 0,76 vì KB chưa có Spring Boot (xem T01).
- **Đổi ở T12 (căn khớp từ):** `align.word_sim_min` 0,75 → **0,90** + `align.literal_match: true`, và gộp âm tiết thành từ bằng pyvi. Lý do và số đo: xem bàn giao T12.
- **Chưa làm:** A2, B5, B3, C1 (T15; nếu bật trong config thì chạy và có cảnh báo `feature_not_implemented`), RR5, chiều cv_to_jd (T16), `bertscore_pair_cache`.
