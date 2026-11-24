# Kịch bản API trên DB demo `cvmatch_demo` (http://127.0.0.1:8090)

- 14/14 kịch bản đạt · KB `kb-2026-11-21-4` · encoder bge-m3 · 300 CV gốc, 30 JD

| Kịch bản | Kết quả | Thời gian (s) | Chi tiết |
| --- | --- | --- | --- |
| health | ✅ | 0.01 | 300 CV · 27 JD mở · bge-m3@5617a9f61b |
| match_all_open_jds | ✅ | 18.74 | 27 JD · P@10 cùng/lân cận nhóm TB 0.95 · tệ nhất DEMO-015 0.70 |
| match_params | ✅ | 3.54 | pool 300 · lọc Hà Nội 118 · ≥5 năm 102 · loại top1 OK · dense-only OK |
| explain_hr | ✅ | 1.87 | top 3 + cache + force + CV hạng 40 ngoài top 5 · 806 ký tự |
| background_job | ✅ | 0.94 | job done sau 0.9s |
| reverse_match | ✅ | 4.86 | 18 CV · top 1 JD cùng/lân cận nhóm 18/18 · JD đóng/nháp không xuất hiện |
| reverse_filters | ✅ | 0.64 | pool 27 JD · remote 6 · loại top 1 OK |
| jd_close_reopen | ✅ | 0.97 | đóng DEMO-009 -> biến mất khỏi gợi ý; mở lại -> xuất hiện lại |
| preview_no_trace | ✅ | 0.92 | top 1 DEMO-018 (Senior Data Engineer) · kho không đổi |
| cv_lifecycle | ✅ | 3.37 | nạp mới → trùng → vào chỉ mục → bản 2 thay bản 1 → xoá → biến mất · CV sai schema 422 |
| jd_lifecycle | ✅ | 1.65 | v1 → unchanged → top 10 Backend/Fullstack 10/10 → v2 → đóng |
| batch_ingest | ✅ | 8.57 | 20 CV chạy nền trong 8.6s · chỉ mục 300 → 320 |
| errors | ✅ | 0.22 | 9 lỗi trả đúng mã |
| concurrent_requests | ✅ | 5.73 | 8 request song song OK trong 5.7s (khoá chung -> chạy tuần tự) |

## Độ trễ theo endpoint

| Endpoint | Số lần | p50 (ms) | p95 (ms) | max (ms) |
| --- | --- | --- | --- | --- |
| DELETE /cv | 1 | 48 | 48 | 48 |
| GET /health | 6 | 3 | 4 | 7 |
| GET /jobs | 22 | 3 | 5 | 20 |
| GET explain | 8 | 54 | 67 | 71 |
| GET explain (ứng viên) | 1 | 56 | 56 | 56 |
| PATCH /jd/status | 3 | 64 | 64 | 98 |
| POST /cv | 4 | 161 | 271 | 277 |
| POST /cv/batch | 1 | 4 | 4 | 4 |
| POST /jd | 4 | 100 | 173 | 181 |
| POST /match/cv | 24 | 256 | 291 | 329 |
| POST /match/cv:preview | 1 | 862 | 862 | 862 |
| POST /match/jd | 49 | 720 | 3582 | 5717 |
| lỗi | 9 | 27 | 47 | 50 |
