# Vấn đề tồn tại và cần tối ưu

> Những chỗ cvmatch **còn chưa đúng ý**, **chưa tối ưu** hoặc **chưa được kiểm chứng**. Cập nhật lần cuối: 26/11/2026.
>
> Cách dùng: mỗi mục có mã `V-xx` (giữ nguyên mã cũ, không đánh lại). Sửa xong thì **xoá mục khỏi file này**; việc đã
> làm ghi ở "Ghi chú bàn giao" của file kế hoạch tương ứng (`plan/Sxx`) và lịch sử git. Mục mới thêm vào cuối nhóm phù hợp.
>
> Đã sửa trong đợt S01–S07 (26/11/2026), xem [[S00 Tổng quan sửa và tối ưu]]: V-02, V-04, V-05, V-06, V-07, V-09, V-10,
> V-13, V-20.

**Mức độ:** 🔴 sai kết quả người dùng thấy · 🟠 ảnh hưởng chất lượng / vận hành · 🟡 nên làm, chưa gấp.
**Trạng thái:** ⬜ chưa làm · ◐ làm một phần · ❓ cần chốt hướng.
**Ai làm:** cvmatch · backend · dữ liệu (cần người ngoài cung cấp / chấm) · kb-builder.

## Tóm tắt

| Mã | Vấn đề | Mức | Trạng thái | Ai làm |
| --- | --- | --- | --- | --- |
| [V-01](#v-01) | Thứ hạng giữa các JD ở Luồng D còn lệch khi JD thiếu `min_years` | 🔴 | ◐ | backend, dữ liệu |
| [V-03](#v-03) | Trọng số, ngưỡng rerank và giá trị điền thiếu chưa hiệu chuẩn trên nhãn thật | 🟠 | ⬜ | dữ liệu, cvmatch |
| [V-08](#v-08) | CV không có địa điểm → lọc cứng theo địa điểm luôn cho qua | 🟡 | ⬜ | backend / Module 1 |
| [V-11](#v-11) | Nhiều request match cùng lúc không nhanh hơn chạy tuần tự (GIL) | 🟠 | ◐ | cvmatch |
| [V-12](#v-12) | Chạy CPU vẫn chậm khi nạp CV (~2,2 s/CV) | 🟡 | ◐ | cvmatch |
| [V-14](#v-14) | KB đang ở chính sách `provisional` (tri thức AI sinh được nhận tạm) | 🟠 | ❓ | kb-builder, dữ liệu |
| [V-15](#v-15) | Chưa có CV / JD thật: mọi số đo chất lượng là trên dữ liệu tổng hợp | 🔴 | ⬜ | dữ liệu |
| [V-16](#v-16) | Chưa chạy thật: container cvmatch, GPU, compose trên máy Linux, giao diện | 🟠 | ⬜ | cvmatch, backend |
| [V-17](#v-17) | Không có luồng xoá CV / tài khoản gọi `DELETE /cv` | 🟡 | ⬜ | backend |
| [V-18](#v-18) | Gợi ý cho recruiter khi JD ngắn / thiếu chưa hiện trên giao diện | 🟡 | ◐ | backend |
| [V-19](#v-19) | 31 kỹ năng technology còn tên viết thường | 🟡 | ⬜ | kb-builder |
| [V-21](#v-21) | Gợi ý việc làm khi có tin mới: phía backend chưa nối, chưa đo trên kho lớn | 🟡 | ◐ | backend, cvmatch |
| [V-22](#v-22) | CV đã nạp trước `prep-1.2` vẫn tính "đang làm" theo quy ước cũ | 🟡 | ⬜ | backend (vận hành) |

---

## A. Chất lượng xếp hạng

### V-01

**Thứ hạng giữa các JD ở Luồng D còn lệch khi JD thiếu `min_years`** · 🔴 · ◐

- **Hiện tượng** (24/11/2026, Luồng D, một CV Java): "Full-stack Developer" (thiếu 3/4 kỹ năng bắt buộc, 44 điểm) đứng
  trên "Senior Java Engineer" (thiếu 1/2, 33 điểm).

  | JD | A1 | B4 | B1 | B2 | Điểm `rr-1.0` | Điểm `rr-1.2` |
  | --- | --- | --- | --- | --- | --- | --- |
  | job-3 Full-stack | 0,20 | 0,33 | 0,8 | 1,0 | 44 | 44 |
  | job-5 Senior Java | 0,33 | 0,09 | 1,0 | *(thiếu)* | 33 | 35 |

- `rr-1.2` (S02) đã cho feature thiếu phía JD giá trị trung tính, mọi JD cùng tập feature. Phần còn lại:
  1. **backend:** job tạo qua form có `experience_required = 0`, `CvMatchPayloads.jdPayload` bỏ `min_years` khi ≤ 0. Nên
     tách "không yêu cầu" (gửi `min_years: 0` → B2 = 1, job-5 lên 42) với "không nhập" (bỏ trường) trên form.
  2. **trọng số:** job-3 vẫn trên vì hơn thật ở B4 (0,33 so với 0,09). Muốn kỹ năng bắt buộc nặng hơn thì hiệu chuẩn
     (V-03), không sửa tay.

### V-03

**Trọng số, ngưỡng rerank và giá trị điền thiếu chưa hiệu chuẩn trên nhãn thật** · 🟠 · ⬜

- Trọng số `rr-1.x` là giả thuyết (thiết kế 07, 11); `b4.calib lo/hi` lấy từ golden; `align.word_sim_min = 0,90` đặt
  tay; ngưỡng cổng `[0,5; 0,7]` và cap `[50; 70]` chưa đo.
- `missing.cv_side_fixed` của `rr-1.2` (A1 0,200 · B1 0,400 · B2 0,000 · B4 0,207) đo trên DB demo tổng hợp; giá trị
  trung tính phía JD (0,5) là giả thuyết.
- `rr-1.1` (đủ 8 feature) đã code nhưng chưa bật; bật thì cần thêm `cv_side_fixed` cho A2, B5, B3, C1.
- **Cần:** nhãn thật (V-15) → `eval calibrate`, `eval ablation` (so `rr-1.2` với `rr-1.1`), `eval missing-defaults` trên
  dữ liệu thật → chốt `rr-1.x` mới (kế hoạch S08).

## B. Dữ liệu vào (Module 1, backend)

### V-08

**CV không có địa điểm → lọc cứng theo địa điểm luôn cho qua** · 🟡 · ⬜

- Module 1 không trích `location`; backend lấy `candidate_profiles.address` (thường trống). Thiết kế cho CV thiếu địa điểm
  đi qua bộ lọc, nên lọc địa điểm gần như không có tác dụng.
- **Hướng:** thêm trường địa điểm vào form hồ sơ; hoặc Module 1 trích từ phần thông tin cá nhân.

### V-18

**Gợi ý cho recruiter khi JD ngắn / thiếu chưa hiện trên giao diện** · 🟡 · ◐

- cvmatch đã trả `warnings[].hint` tiếng Việt khi nạp JD (`short_query`, `no_responsibility`, `no_required_skill`,
  `many_unmapped_skills`) — S04.
- **Còn:** backend lưu cảnh báo từ `POST /jd` và frontend hiện trên form đăng / sửa tin.

### V-22

**CV đã nạp trước `prep-1.2` vẫn tính "đang làm" theo quy ước cũ** · 🟡 · ⬜

- `prep-1.2` chỉ coi mục kinh nghiệm có `start` mới nhất là đang làm khi `end_date = null` (V-06 cũ). `reprocess` đọc
  `cv.raw_json` đã qua adapter (đã gắn `is_current`), nên CV nạp trước đó giữ cách tính cũ (số năm có thể dư).
- **Cần:** sau khi deploy `prep-1.2`, backend chạy `POST /internal/cvmatch/backfill?scope=cv` để gửi lại CV từ MySQL.
  Việc backfill này cũng cần cho mọi CV vì đổi `prep` làm dữ liệu cũ khác bộ khoá phiên bản.

## C. Vận hành, hiệu năng

### V-11

**Nhiều request match cùng lúc không nhanh hơn chạy tuần tự** · 🟠 · ◐

- Đã có khoá đọc–ghi (S05): match / explain không còn xếp hàng sau nhau. Nhưng đo 8 `match_jd` song song trên DB demo:
  ×1,0 — phần lớn thời gian là code Python (tính feature, ghép ma trận) giữ GIL.
- `JobRegistry` giữ việc chạy nền trong RAM; mất khi khởi động lại (backend đã tự thử lại theo `match_*_link`, nên không
  mất dữ liệu).
- **Hướng:** chạy nhiều process (`uvicorn --workers N` hoặc nhiều bản sao `cvmatch-ai`), mỗi process nạp model và chỉ mục
  riêng (~1,5 GB RAM mỗi process); chỉ mục RAM của các process cần nghe sự kiện nạp / xoá của nhau (hiện là sự kiện trong
  process) → cần cơ chế đồng bộ (vd LISTEN/NOTIFY của Postgres). Chỉ làm khi số request thật cần.

### V-12

**Chạy CPU vẫn chậm khi nạp CV** · 🟡 · ◐

- S05 đã chuyển việc tính token BERTScore sang lúc nạp + làm nóng khi khởi động: match trên CPU 300 CV ~1,6 s
  (`research/reports/bench_cpu.md`). Đổi lại nạp CV trên CPU ~1,9 s → ~2,2 s/CV; backfill 300 CV ~11 phút.
- **Hướng:** int8 (dynamic quantization) cho encoder trên CPU, đo lệch như `eval fp16`; hoặc chạy cvmatch trên máy có GPU
  (`CVMATCH_URL`).

### V-17

**Không có luồng xoá CV / tài khoản gọi `DELETE /cv`** · 🟡 · ⬜

- API và `CvMatchSync.deleteCandidate` đã có nhưng hệ thống chưa có chức năng xoá CV / tài khoản để gọi tới
  (quyền riêng tư, thiết kế 03).

### V-21

**Gợi ý việc làm khi có tin mới: phía backend chưa nối, chưa đo trên kho lớn** · 🟡 · ◐

- cvmatch đã có (S07): cờ `cv.recommendable` theo người, `PATCH /cv/{id}`, `POST /match/jd/{id}` với
  `only_recommendable`, `min_score`, `exclude_cv_ids`.
- **Còn (backend):** listener `JobPublished` → gọi match → lưu gợi ý → notification; đồng bộ cờ theo cài đặt "đang tìm
  việc" của ứng viên; giới hạn số thông báo / ứng viên / tuần (RS-01 trong `docs/PLAN_chuc_nang_he_thong.md`).
- **Còn (cvmatch):** đo Luồng C trên kho 5k–20k CV (Retrieve tăng tuyến tính theo kho, Rerank cố định K = 200) để biết
  có cần chạy nền / giới hạn tần suất.

## D. Knowledge Base

### V-14

**KB đang ở chính sách `provisional`** · 🟠 · ❓ cần chốt (Q-E)

- Tri thức KB3 do AI sinh được nhận tạm (`accepted_by = provisional`); mọi quan hệ cấu trúc chưa qua luật.
- **Hướng:** có nguồn độc lập thứ hai (ESCO…) hoặc duyệt tay, rồi so bản `--policy rule` với bản provisional bằng
  ablation trên nhãn thật.

### V-19

**31 kỹ năng technology còn tên viết thường** · 🟡 · ⬜

- Phần lớn cố ý (`npm`, `curl`, `pandas`, `pytest`). Danh sách ở `ai-service/matching/kb-builder/out/snapshot/kb-2026-11-24/release_check.md`;
  muốn đổi thì thêm dòng `display` ở `ai-service/matching/kb-builder/kb3/data/skill_fixes.csv`.

## E. Kiểm chứng còn thiếu

### V-15

**Chưa có CV / JD thật** · 🔴 · ⬜

- Mọi số đo (P@10, độ phủ, ví dụ thứ hạng, `cv_side_fixed`, bench) là trên dữ liệu tổng hợp hoặc seed. Độ phủ Module 1
  (`research/reports/coverage_module1_fixture.md`) không đại diện.
- **Cần:** 5–10 `extracted_profile` thật đã ẩn danh → `eval coverage`; ≥ 20 JD × ~15 CV có nhãn (2 người chấm) cho V-03.

### V-16

**Chưa chạy thật ở môi trường đích** · 🟠 · ⬜

- Image `cvmatch-ai` build được nhưng chưa chạy container (lần đầu tải bge-m3 ~4 GB vào volume), chưa chạy image GPU
  (`docker-compose.gpu.yml`), chưa chạy toàn bộ stack bằng compose trên máy Linux của nhóm, chưa xem giao diện (nhãn mức
  khớp, "Vì sao?") trên trình duyệt.
