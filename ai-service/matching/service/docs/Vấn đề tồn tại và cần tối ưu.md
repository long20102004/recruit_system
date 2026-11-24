# Vấn đề tồn tại và cần tối ưu

> Danh sách những chỗ cvmatch đang chạy **chưa đúng ý**, **chưa tối ưu** hoặc **chưa được kiểm chứng**, phát hiện
> trong lúc ghép vào HireLens (plan `plan/` I01–I08) và các phần T00–T17. Cập nhật lần cuối: 24/11/2026.
>
> Cách dùng: mỗi mục có mã `V-xx`. Sửa xong thì chuyển trạng thái sang ✅ kèm ngày và nơi sửa, **không xoá dòng**.
> Mục mới thêm vào cuối nhóm phù hợp.

**Mức độ:** 🔴 sai kết quả người dùng thấy · 🟠 ảnh hưởng chất lượng / vận hành · 🟡 nên làm, chưa gấp.
**Trạng thái:** ⬜ chưa làm · ◐ đang làm · ✅ xong · ❓ cần chốt hướng.

## Tóm tắt

| Mã | Vấn đề | Mức | Trạng thái |
| --- | --- | --- | --- |
| [V-01](#v-01) | Feature thiếu ở phía JD bị bỏ và chia lại trọng số → thứ hạng giữa các JD lệch | 🔴 | ❓ |
| [V-02](#v-02) | B1 (vai trò) không suy ra được với một số JD (vd "Java Intern") | 🟠 | ⬜ |
| [V-03](#v-03) | Trọng số, ngưỡng rerank chưa hiệu chuẩn trên nhãn thật | 🟠 | ⬜ |
| [V-04](#v-04) | Chấm một cặp (pool 1) có thể lệch điểm so với khi xếp trong danh sách | 🟡 | ⬜ |
| [V-05](#v-05) | JD từ form chỉ có đoạn mô tả, không tách gạch → B4 yếu | 🟠 | ◐ |
| [V-06](#v-06) | `end_date = null` của Module 1 luôn coi là "đang làm" | 🟡 | ⬜ |
| [V-07](#v-07) | Sinh viên đang học: `end_year = null` → trạng thái học vấn `unknown` | 🟡 | ⬜ |
| [V-08](#v-08) | CV không có địa điểm → lọc cứng theo địa điểm luôn cho qua | 🟡 | ⬜ |
| [V-09](#v-09) | Gửi lại nội dung CV cũ → trả `cv_id` của bản cũ, không phải bản mới nhất | 🟠 | ⬜ |
| [V-10](#v-10) | Đổi KB / model / khoá HMAC → dữ liệu cũ "biến mất" cho tới khi nạp lại | 🟠 | ✅ có quy trình |
| [V-11](#v-11) | Xử lý tuần tự (một khoá chung), việc chạy nền mất khi khởi động lại | 🟠 | ⬜ |
| [V-12](#v-12) | Chạy CPU chậm: nạp CV ~1,9 s, rerank lần đầu ~5 s | 🟠 | ⬜ |
| [V-13](#v-13) | BM25 thêm tăng dần dùng IDF cũ tới lần dựng lại | 🟡 | ⬜ |
| [V-14](#v-14) | KB đang ở chính sách `provisional` (tri thức AI sinh được nhận tạm) | 🟠 | ❓ |
| [V-15](#v-15) | Chưa có CV / JD thật: độ phủ Module 1 và mọi số đo chất lượng là trên dữ liệu tổng hợp | 🔴 | ⬜ |
| [V-16](#v-16) | Chưa chạy thật: GPU trong container, compose đầy đủ trên máy Linux, giao diện | 🟠 | ⬜ |
| [V-17](#v-17) | Không có luồng xoá CV / tài khoản gọi `DELETE /cv` | 🟡 | ⬜ |
| [V-18](#v-18) | Cảnh báo "văn bản truy vấn < 50 từ" với JD ngắn | 🟡 | ⬜ |
| [V-19](#v-19) | 31 kỹ năng technology còn tên viết thường | 🟡 | ⬜ |

---

## A. Chất lượng xếp hạng

### V-01

**Feature thiếu ở phía JD bị bỏ và chia lại trọng số → thứ hạng giữa các JD lệch** · 🔴 · ❓ cần chốt

- **Hiện tượng** (24/11/2026, bge-m3 thật, dữ liệu seed + 1 CV Java giả, Luồng D): "Full-stack Developer" (thiếu 3/4
  kỹ năng bắt buộc, điểm 44) đứng trên "Senior Java Engineer" (thiếu 1/2, điểm 33).

  | JD | A1 | B4 | B1 | B2 | Điểm |
  | --- | --- | --- | --- | --- | --- |
  | job-3 Full-stack | 0,20 | 0,33 | 0,8 | **1,0** | 44 |
  | job-5 Senior Java | 0,33 | 0,09 | 1,0 | *(thiếu)* | 33 |
  | job-4 Java Intern | 0,33 | 0,21 | *(thiếu)* | *(thiếu)* | 27 |

- **Nguyên nhân:** job tạo qua form có `experience_required = 0` (backend coi "không nhập" và "0 năm" là một), nên
  backend không gửi `min_years` → B2 không tính được. Feature thiếu **phía JD** bị bỏ và trọng số các feature còn lại
  được chia lại, trong khi job seed có `min_years` nên được B2 = 1,0 kéo điểm lên. Ở Luồng D (một CV so với nhiều JD),
  mỗi JD có tập feature khác nhau nên điểm không so được với nhau.
- **Hướng xử lý (cần chốt):**
  1. Backend gửi `min_years: 0` khi job không yêu cầu kinh nghiệm → B2 = 1 cho mọi CV. Đơn giản, nhưng không phân biệt
     được "không yêu cầu" với "quên nhập".
  2. Đổi chính sách thiếu phía JD trong `rr-1.x`: thay vì bỏ feature, gán giá trị trung tính (vd 0,5) hoặc phạt nhẹ, để
     mọi JD có cùng tập feature khi so ở Luồng D.
  3. Luồng D chuẩn hoá điểm theo tập feature chung của cả pool JD.
- **Nơi liên quan:** `rerank/scoring.py` (missing policy), `config/rr-1.0.yaml` (`missing`),
  `backend/.../CvMatchPayloads.jdPayload` (bỏ `min_years` khi ≤ 0).

### V-02

**B1 (vai trò) không suy ra được với một số JD** · 🟠 · ⬜

- **Hiện tượng:** "Java Intern" có `B1 = null` (cùng bảng V-01), trong khi "Senior Java Engineer" có B1.
- **Nghi ngờ:** chức danh chứa cấp bậc ("Intern") không khớp `role_title_map` của KB, hoặc luật tách cấp bậc khỏi chức
  danh trước khi tra chưa bao trường hợp này. Cần kiểm `core/kb/lookup.py` và B-flow (`b06_b07.py`) với vài chức danh
  "X Intern", "Thực tập sinh X", "Fresher X".

### V-03

**Trọng số, ngưỡng rerank chưa hiệu chuẩn trên nhãn thật** · 🟠 · ⬜

- `rr-1.0` dùng trọng số giả thuyết (thiết kế 07/11); `b4.calib lo/hi` lấy từ golden; `align.word_sim_min = 0,90` đặt
  tay; ngưỡng cổng `[0,5; 0,7]` và cap `[50; 70]` chưa đo.
- `rr-1.1` (đủ 8 feature) đã code nhưng chưa bật.
- **Cần:** nhãn thật (Q-8) → `eval ablation`, `eval calibrate` (T14) → chọn `rr-1.x`.

### V-04

**Chấm một cặp (pool 1) có thể lệch điểm so với khi xếp trong danh sách** · 🟡 · ⬜

- Backend chấm một cặp bằng `include_cv_ids=[cv]` / `include_jd_ids=[jd]`. Điểm rerank phần lớn là tuyệt đối, nhưng
  dữ liệu thiếu **phía CV** dùng `pool_median` → với pool 1 thì median là chính nó.
- **Hướng:** khi pool nhỏ, dùng median của toàn kho (hoặc của lần chạy gần nhất) thay vì của pool; hoặc ghi rõ trong
  giao diện rằng điểm chấm lẻ là ước lượng.

### V-05

**JD từ form chỉ có đoạn mô tả, không tách gạch → B4 yếu** · 🟠 · ◐

- B4 so từng câu trách nhiệm của JD với gạch đầu dòng của CV. JD chỉ có một đoạn `description` dài → ít câu, khớp kém.
- **Đã làm (I07):** form recruiter thêm ô "Trách nhiệm" và "Yêu cầu", mỗi dòng một ý.
- **Còn lại:** job cũ / job nhập đoạn văn — cân nhắc tách câu ở B-flow khi `responsibilities` chỉ có 1 phần tử dài.

## B. Dữ liệu vào (Module 1, backend)

### V-06

**`end_date = null` của Module 1 luôn coi là "đang làm"** · 🟡 · ⬜

- Adapter (`ingest/cv/adapter.py`) theo quy ước prompt Module 1: có `start_date` mà `end_date = null` → `is_current`.
  Nếu model để `null` vì **không đọc được** ngày kết thúc, số năm kinh nghiệm bị tính dư tới tháng hiện tại.
- **Hướng:** đo trên CV thật (V-15) tỉ lệ sai; nếu cao, chỉ coi là đang làm khi là mục kinh nghiệm mới nhất.

### V-07

**Sinh viên đang học: `end_year = null` → trạng thái học vấn `unknown`** · 🟡 · ⬜

- Module 1 không có trường "đang học". A6 không suy ra được `status = studying` → C1 (P2) và giải thích thiếu ý.
- **Hướng:** `start_year` gần (≤ 4–5 năm) và `end_year = null` → `studying`; hoặc đề nghị Module 1 thêm trường.

### V-08

**CV không có địa điểm → lọc cứng theo địa điểm luôn cho qua** · 🟡 · ⬜

- Module 1 không trích `location`; backend lấy `candidate_profiles.address` (thường trống). Thiết kế cho CV thiếu địa điểm
  đi qua bộ lọc, nên lọc địa điểm gần như không có tác dụng.
- **Hướng:** thêm trường địa điểm vào form hồ sơ; hoặc Module 1 trích từ phần thông tin cá nhân.

### V-09

**Gửi lại nội dung CV cũ → trả `cv_id` của bản cũ** · 🟠 · ⬜

- A2 tìm trùng theo `content_hash` (`dedup_pg.find_by_hash`) **không lọc `is_latest`**. Ứng viên sửa CV (version 2)
  rồi sửa về đúng nội dung cũ → `POST /cv` trả `duplicate` với `cv_id` của version 1, nhưng version 1 đã
  `is_latest = false` nên không có trong chỉ mục → backend lưu `cv_id` không match được (Luồng D báo CV chưa sẵn sàng).
- **Hướng:** khi trùng hash với bản không còn mới nhất → đánh dấu bản đó lại là `is_latest` (và gỡ bản đang mới nhất),
  hoặc tạo version mới.

## C. Vận hành, hiệu năng

### V-10

**Đổi KB / model / khoá HMAC → dữ liệu cũ "biến mất" cho tới khi nạp lại** · 🟠 · ✅ có quy trình

- Đúng thiết kế (bản ghi mang bộ khoá phiên bản), nhưng dễ gây hiểu nhầm là mất dữ liệu.
- **Quy trình:** `reprocess cv --from A5` + `reprocess jd` (đổi KB), hoặc từ backend
  `POST /internal/cvmatch/backfill?scope=all` (README backend, mục "Matching CV ↔ JD").

### V-11

**Xử lý tuần tự, việc chạy nền mất khi khởi động lại** · 🟠 · ⬜

- `Services` dùng một khoá chung cho mọi thao tác dùng chỉ mục / encoder → request đồng thời xếp hàng (demo: 8 request
  song song chạy tuần tự). `JobRegistry` giữ việc chạy nền trong RAM.
- Backend đã tự thử lại theo `match_cv_link` / `match_jd_link`, nên mất việc nền không mất dữ liệu.
- **Hướng:** tách khoá đọc (match) và ghi (nạp); lưu job nền vào Postgres nếu cần backfill lớn.

### V-12

**Chạy CPU chậm** · 🟠 · ⬜

| Mục | CPU (4 nhân) | GPU GTX 1650 |
| --- | --- | --- |
| nạp CV | ~1,9 s/CV | ~0,2 s/CV |
| match JD đầu (cache token lạnh) | ~5,0 s | ~0,6 s |
| match JD sau | ~0,7 s | ~0,12 s |

- Backfill 300 CV trên CPU ~10 phút.
- **Hướng:** fp16 / int8 trên CPU (đo lệch như `eval fp16`), làm nóng cache token khi khởi động, hoặc chạy cvmatch trên
  máy có GPU (`CVMATCH_URL`).

### V-13

**BM25 thêm tăng dần dùng IDF cũ** · 🟡 · ⬜

- CV mới dùng từ vựng / IDF của lần dựng trước; chỉ dựng lại khi kho tăng > 10 %. Chưa có lịch dựng lại định kỳ.

### V-17

**Không có luồng xoá CV / tài khoản gọi `DELETE /cv`** · 🟡 · ⬜

- API và `CvMatchSync.deleteCandidate` đã có nhưng hệ thống chưa có chức năng xoá CV / tài khoản để gọi tới
  (quyền riêng tư, thiết kế 03).

## D. Knowledge Base

### V-14

**KB đang ở chính sách `provisional`** · 🟠 · ❓ cần chốt (Q-E)

- Tri thức KB3 do AI sinh được nhận tạm (`accepted_by = provisional`); mọi quan hệ cấu trúc chưa qua luật.
- **Hướng:** có nguồn độc lập thứ hai (ESCO…) hoặc duyệt tay, rồi so bản `--policy rule` với bản provisional bằng
  ablation trên nhãn thật.

### V-19

**31 kỹ năng technology còn tên viết thường** · 🟡 · ⬜

- Phần lớn cố ý (`npm`, `curl`, `pandas`, `pytest`). Danh sách ở `tools/build_kb/out/snapshot/kb-2026-11-24/release_check.md`;
  muốn đổi thì thêm dòng `display` ở `tools/build_kb/kb3/data/skill_fixes.csv`.

## E. Kiểm chứng còn thiếu

### V-15

**Chưa có CV / JD thật** · 🔴 · ⬜

- Mọi số đo (P@10, độ phủ, ví dụ thứ hạng) là trên dữ liệu tổng hợp hoặc seed. Độ phủ Module 1
  (`reports/coverage_module1_fixture.md`) không đại diện.
- **Cần:** 5–10 `extracted_profile` thật đã ẩn danh → `eval coverage`; bộ nhãn thật → T14.

### V-16

**Chưa chạy thật ở môi trường đích** · 🟠 · ⬜

- Chưa chạy image GPU (`docker-compose.gpu.yml`), chưa chạy toàn bộ stack bằng compose trên máy Linux của nhóm, chưa
  xem giao diện (nhãn mức khớp, "Vì sao?") trên trình duyệt.

### V-18

**Cảnh báo "văn bản truy vấn < 50 từ" với JD ngắn** · 🟡 · ⬜

- Đúng thiết kế (06), nhưng JD tạo nhanh trên form thường ngắn → cảnh báo xuất hiện thường xuyên. Cân nhắc hiện gợi ý
  "viết thêm trách nhiệm" cho recruiter thay vì chỉ ghi log.
