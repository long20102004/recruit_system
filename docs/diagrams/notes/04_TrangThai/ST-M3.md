# Biểu đồ trạng thái chức năng M3: Đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển

## Bước 1: Xác định các trạng thái giao diện
Căn cứ theo kịch bản chuẩn và ngoại lệ của chức năng M3 (`diagrams/notes/02_KichBan/KB-M3.md`) cùng mã nguồn frontend thực tế trong `source/recruit_system/frontend/src/pages/candidate/`, mỗi màn hình giao diện chính, hộp thông báo hoặc thông báo kết quả (toast) được xác định là một trạng thái trong biểu đồ trạng thái:

1. **Hiện giao diện Trang chủ ứng viên (`state_home`):**
   - Màn hình hiển thị danh sách tin tuyển dụng công khai/theo khu vực, thanh tìm kiếm từ khóa, lựa chọn thành phố, các chip lọc chế độ và khung `SidePanel` hiển thị tóm tắt tin việc được chọn, nút "Xem xếp hạng", nút "Ứng tuyển" và nút "Ôn tập phỏng vấn" (`CandidateHomePage.tsx:36`).
2. **Hiện thông báo yêu cầu tải CV (`state_empty_cv`):**
   - Hộp thông báo rỗng (`EmptyNote`) trên Trang việc làm phù hợp khi ứng viên chưa tải CV hoặc CV chưa hoàn tất phân tích (`form.analyzed == false`), hiển thị hướng dẫn cùng nút "Tải CV" dẫn sang `/candidate/cv` (`CandidateMatchingPage.tsx:104-114`).
3. **Hiện giao diện Việc làm phù hợp (đã xếp hạng) (`state_matching`):**
   - Màn hình kết xuất danh sách thẻ công việc (`MatchItem`) đã được dịch vụ AI đối sánh và xếp hạng theo tỷ lệ phù hợp giảm dần (`overallScore`), hiển thị điểm chi tiết (kỹ năng, kinh nghiệm, bối cảnh), kỹ năng khớp/thiếu, giải thích từ AI, nút "Cập nhật theo CV" và nút "Xem chi tiết" (`CandidateMatchingPage.tsx:147-163`).
4. **Hiện giao diện Việc làm phù hợp (chế độ dự phòng) (`state_matching_fallback`):**
   - Màn hình khi dịch vụ AI gặp sự cố (HTTP 502/503/timeout), hệ thống chuyển sang chế độ dự phòng hiển thị các tin tuyển dụng đang mở kèm thông báo lỗi chấm điểm hoặc giữ lại điểm đối sánh đã lưu trước đó (`CandidateMatchingPage.tsx:120-145`).
5. **Hiện thông báo lỗi tải việc phù hợp (`state_error_matching`):**
   - Thông báo toast lỗi khi yêu cầu đối sánh gặp lỗi nghiêm trọng (chưa xác thực 401, không đúng vai trò 403, không tìm thấy hồ sơ ứng viên 400 hoặc không có cả dữ liệu điểm lưu lẫn tin tuyển dụng) (`CandidateMatchingPage.tsx:63`).
6. **Hiện giao diện Chi tiết việc làm (`state_job_detail`):**
   - Màn hình kết xuất đầy đủ thông tin chi tiết của một tin tuyển dụng (mô tả, yêu cầu, trách nhiệm, đãi ngộ, kỹ năng bắt buộc, kỹ năng ưu tiên), nút "Quay lại" và nút "Ôn tập phỏng vấn" (`CandidateJobDetailPage.tsx:88-160`).
7. **Hiện thông báo không tìm thấy tin tuyển dụng (`state_job_not_found`):**
   - Hộp thông báo rỗng (`EmptyNote`) khi mã tin tuyển dụng trên URL không hợp lệ hoặc không tồn tại trong CSDL (lỗi 404), kèm nút "Quay lại" (`CandidateJobDetailPage.tsx:86`).
8. **Hiện thông báo nộp hồ sơ thành công (`state_apply_success`):**
   - Thông báo toast "Đã nộp hồ sơ ứng tuyển" khi bản ghi đơn ứng tuyển mới được lưu thành công vào CSDL với trạng thái `SUBMITTED` (`CandidateHomePage.tsx:94`).
9. **Hiện thông báo lỗi ứng tuyển (`state_apply_error`):**
   - Thông báo toast khi nộp đơn ứng tuyển thất bại do tin tuyển dụng không mở (HTTP 400), ứng viên đã nộp đơn trước đó (HTTP 409 Conflict) hoặc lỗi xác thực (HTTP 401/403) (`CandidateHomePage.tsx:96`).

Các điểm rẽ nhánh kiểm tra (choice pseudostates):
- `choice_cv`: Kiểm tra trạng thái phân tích hồ sơ CV của ứng viên (`form.analyzed`).
- `choice_ai`: Kiểm tra kết quả phản hồi từ dịch vụ AI đối sánh `cv-matching-ai` (`POST /match/no-llm`).
- `choice_job`: Kiểm tra tính hợp lệ và sự tồn tại của mã tin tuyển dụng `jobId`.
- `choice_apply`: Kiểm tra điều kiện nộp đơn ứng tuyển tại backend (trạng thái tin `PUBLISHED` và kiểm tra đơn trùng).

Các điểm mốc vòng đời:
- `initial_state`: Trạng thái bắt đầu khi ứng viên đã đăng nhập truy cập hệ thống.
- `final_state`: Trạng thái kết thúc sau khi hoàn tất nộp đơn ứng tuyển hoặc thoát chức năng.

---

## Bước 2: Xác định các chuyển trạng thái
Quy tắc chuyển trạng thái giữa các giao diện và điểm rẽ nhánh kiểm tra được xác định như sau:

- **Khởi đầu:**
  - Từ trạng thái ban đầu (`initial_state`), khi ứng viên truy cập vào route `/candidate`, hệ thống khởi tạo và chuyển sang **Hiện giao diện Trang chủ ứng viên**.
    - Nhãn: `[Ứng viên truy cập /candidate] / Khởi tạo Trang chủ ứng viên`

- **Tại giao diện Trang chủ ứng viên:**
  - Nếu ứng viên nhấn nút "Xem xếp hạng" (hoặc chọn menu "Việc phù hợp") thì hệ thống gọi API `cvsApi.mine()` kiểm tra trạng thái CV và chuyển tới điểm kiểm tra trạng thái CV (`choice_cv`).
    - Nhãn: `[Nhấn nút Xem xếp hạng] / Gọi cvsApi.mine() kiểm tra trạng thái CV`
  - Nếu ứng viên chọn một tin tuyển dụng trong danh sách và nhấn nút "Ứng tuyển" tại khung `SidePanel` thì hệ thống gửi yêu cầu `POST /api/applications/jobs/{jobId}` và chuyển tới điểm kiểm tra điều kiện ứng tuyển (`choice_apply`).
    - Nhãn: `[Chọn tin và nhấn nút Ứng tuyển] / Gửi yêu cầu nộp đơn applicationsApi.apply()`

- **Tại điểm kiểm tra trạng thái CV (`choice_cv`):**
  - Nếu CV chưa được phân tích hoàn tất (`form.analyzed == false`) thì chuyển sang **Hiện thông báo yêu cầu tải CV**.
    - Nhãn: `[CV chưa phân tích] / Hiển thị hướng dẫn và nút Tải CV`
  - Nếu CV đã được phân tích hoàn tất (`form.analyzed == true`) thì hệ thống tải danh sách tin tuyển dụng, lấy điểm đã lưu và gọi `matchingApi.refreshMine()`, sau đó chuyển tới điểm kiểm tra kết quả đối sánh AI (`choice_ai`).
    - Nhãn: `[CV đã phân tích] / Tải tin và gọi matchingApi.refreshMine()`

- **Tại giao diện Hiện thông báo yêu cầu tải CV:**
  - Nếu ứng viên nhấn nút "Tải CV" thì hệ thống điều hướng sang trang quản lý CV (`/candidate/cv`, ngoài phạm vi M3) và kết thúc tiến trình M3.
    - Nhãn: `[Nhấn nút Tải CV] / Chuyển sang /candidate/cv`
  - Nếu ứng viên nhấn quay lại (hoặc chọn menu trên header) thì hệ thống quay về **Hiện giao diện Trang chủ ứng viên**.
    - Nhãn: `[Click back] / Quay về Trang chủ ứng viên`

- **Tại điểm kiểm tra kết quả đối sánh AI (`choice_ai`):**
  - Nếu dịch vụ AI phản hồi điểm số hợp lệ thì backend lưu kết quả vào bảng `matching_results`, frontend sắp xếp giảm dần và chuyển sang **Hiện giao diện Việc làm phù hợp (đã xếp hạng)**.
    - Nhãn: `[AI đối sánh thành công] / Lưu kết quả và xếp hạng theo điểm giảm dần`
  - Nếu dịch vụ AI gặp sự cố (502/503/timeout) nhưng hệ thống đã có điểm lưu cũ hoặc có danh sách tin tuyển dụng đang mở thì chuyển sang **Hiện giao diện Việc làm phù hợp (chế độ dự phòng)**.
    - Nhãn: `[AI gặp sự cố nhưng có điểm cũ hoặc tin mở] / Hiển thị tin kèm cảnh báo AI không chạy`
  - Nếu xảy ra lỗi nghiêm trọng (chưa xác thực, sai vai trò hoặc không có cả điểm lưu lẫn tin) thì chuyển sang **Hiện thông báo lỗi tải việc phù hợp**.
    - Nhãn: `[Lỗi xác thực hoặc không có dữ liệu] / Hiển thị toast lỗi tải việc phù hợp`

- **Tại giao diện Hiện thông báo lỗi tải việc phù hợp:**
  - Nếu ứng viên bấm xác nhận thông báo thì hệ thống quay về **Hiện giao diện Trang chủ ứng viên**.
    - Nhãn: `[Click OK] / Quay về Trang chủ ứng viên`
  - Nếu ứng viên đóng ứng dụng hoặc rời trang thì chuyển đến trạng thái Kết thúc (`final_state`).
    - Nhãn: `[Đóng / Rời trang] / Thoát chức năng`

- **Tại giao diện Việc làm phù hợp (đã xếp hạng):**
  - Nếu ứng viên nhấn nút "Cập nhật theo CV" thì hệ thống kích hoạt hàm `rematch()` gọi lại API `refreshMine()` và chuyển tới điểm kiểm tra kết quả đối sánh AI (`choice_ai`).
    - Nhãn: `[Nhấn nút Cập nhật theo CV] / Gọi rematch() làm mới điểm đối sánh`
  - Nếu ứng viên nhấn nút "Xem chi tiết" tại một tin tuyển dụng xếp hạng thì hệ thống trích xuất `jobId` và chuyển tới điểm kiểm tra mã tin (`choice_job`).
    - Nhãn: `[Nhấn nút Xem chi tiết] / Trích xuất jobId và kiểm tra mã tin`
  - Nếu ứng viên chọn menu "Việc làm" trên header thì hệ thống quay về **Hiện giao diện Trang chủ ứng viên**.
    - Nhãn: `[Chọn menu Việc làm] / Điều hướng về Trang chủ ứng viên`

- **Tại giao diện Việc làm phù hợp (chế độ dự phòng):**
  - Nếu ứng viên nhấn nút "Cập nhật theo CV" thì hệ thống gửi lại yêu cầu tính điểm đối sánh AI và chuyển tới điểm kiểm tra kết quả đối sánh AI (`choice_ai`).
    - Nhãn: `[Nhấn nút Cập nhật theo CV] / Thử lại tiến trình đối sánh AI`
  - Nếu ứng viên nhấn nút "Xem chi tiết" tại một tin tuyển dụng đang mở thì hệ thống trích xuất `jobId` và chuyển tới điểm kiểm tra mã tin (`choice_job`).
    - Nhãn: `[Nhấn nút Xem chi tiết] / Trích xuất jobId và kiểm tra mã tin`
  - Nếu ứng viên chọn menu "Việc làm" trên header thì hệ thống quay về **Hiện giao diện Trang chủ ứng viên**.
    - Nhãn: `[Chọn menu Việc làm] / Điều hướng về Trang chủ ứng viên`

- **Tại điểm kiểm tra mã tin tuyển dụng (`choice_job`):**
  - Nếu tham số `jobId` không hợp lệ (không phải số hữu hạn) hoặc không tồn tại trong CSDL (lỗi 404) thì chuyển sang **Hiện thông báo không tìm thấy tin tuyển dụng**.
    - Nhãn: `[Mã tin không hợp lệ hoặc không tồn tại] / Hiển thị thông báo không tìm thấy`
  - Nếu tin tuyển dụng hợp lệ và tồn tại trong CSDL thì hệ thống tải chi tiết và chuyển sang **Hiện giao diện Chi tiết việc làm**.
    - Nhãn: `[Tin tuyển dụng hợp lệ và tồn tại] / Tải dữ liệu và hiển thị chi tiết việc làm`

- **Tại giao diện Hiện thông báo không tìm thấy tin tuyển dụng:**
  - Nếu ứng viên nhấn nút "Quay lại" thì hệ thống quay về **Hiện giao diện Việc làm phù hợp (đã xếp hạng)**.
    - Nhãn: `[Click back] / Quay lại Trang việc làm phù hợp`

- **Tại giao diện Chi tiết việc làm:**
  - Nếu ứng viên nhấn nút "Quay lại" thì hệ thống quay về **Hiện giao diện Việc làm phù hợp (đã xếp hạng)**.
    - Nhãn: `[Click back] / Quay lại Trang việc làm phù hợp`
  - Nếu ứng viên chọn menu "Việc làm" trên header để chuẩn bị nộp hồ sơ ứng tuyển thì hệ thống quay về **Hiện giao diện Trang chủ ứng viên**.
    - Nhãn: `[Chọn menu Việc làm] / Trở về Trang chủ ứng viên để ứng tuyển`
  - Nếu ứng viên nhấn nút "Ôn tập phỏng vấn" thì hệ thống chuyển sang mô-đun ôn tập phỏng vấn (Module M4, `/candidate/interview?jobId=...`) và kết thúc tiến trình M3.
    - Nhãn: `[Nhấn nút Ôn tập phỏng vấn] / Chuyển sang mô-đun luyện phỏng vấn`

- **Tại điểm kiểm tra điều kiện ứng tuyển (`choice_apply`):**
  - Nếu tin tuyển dụng không ở trạng thái mở tiếp nhận hồ sơ (`JobStatus.PUBLISHED`) hoặc ứng viên đã nộp đơn vào vị trí này trước đó (lỗi 409 Conflict) thì chuyển sang **Hiện thông báo lỗi ứng tuyển**.
    - Nhãn: `[Đã ứng tuyển trước đó hoặc tin đã đóng] / Hiển thị toast lỗi ứng tuyển`
  - Nếu tin tuyển dụng đang mở và ứng viên chưa từng nộp đơn thì backend tạo bản ghi `JobApplication` mới với trạng thái `SUBMITTED`, lưu CSDL và chuyển sang **Hiện thông báo nộp hồ sơ thành công**.
    - Nhãn: `[Tin đang mở và chưa ứng tuyển] / Lưu đơn SUBMITTED và hiển thị toast thành công`

- **Tại giao diện Hiện thông báo lỗi ứng tuyển:**
  - Nếu ứng viên bấm xác nhận hoặc toast tự tắt thì hệ thống giữ nguyên giao diện và quay về **Hiện giao diện Trang chủ ứng viên**.
    - Nhãn: `[Click OK] / Đóng thông báo lỗi và giữ trạng thái trang chủ`

- **Tại giao diện Hiện thông báo nộp hồ sơ thành công:**
  - Nếu ứng viên bấm xác nhận hoàn tất kịch bản thì chuyển đến trạng thái Kết thúc (`final_state`).
    - Nhãn: `[Click OK] / Hoàn tất nộp hồ sơ ứng tuyển`
  - Nếu ứng viên tiếp tục tìm kiếm việc làm khác thì quay về **Hiện giao diện Trang chủ ứng viên**.
    - Nhãn: `[Tiếp tục tìm việc] / Quay lại danh sách tin tuyển dụng`

Ta được biểu đồ trạng thái chức năng “Đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển”:

---

## Bảng truy vết phần tử và chuyển trạng thái

| Phần tử / Chuyển trạng thái | Loại | Nguồn truy vết trong mã nguồn (`source/recruit_system/`) |
|---|---|---|
| `initial_state` | Initial State | `frontend/src/App.tsx:72` |
| `state_home` | State | `frontend/src/pages/candidate/CandidateHomePage.tsx:36` |
| `choice_cv` | Choice | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:31` |
| `state_empty_cv` | State | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:104` |
| `choice_ai` | Choice | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:50` |
| `state_matching` | State | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:147` |
| `state_matching_fallback` | State | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:120` |
| `state_error_matching` | State | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:63` |
| `choice_job` | Choice | `frontend/src/pages/candidate/CandidateJobDetailPage.tsx:51` |
| `state_job_detail` | State | `frontend/src/pages/candidate/CandidateJobDetailPage.tsx:88` |
| `state_job_not_found` | State | `frontend/src/pages/candidate/CandidateJobDetailPage.tsx:86` |
| `choice_apply` | Choice | `backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:29` |
| `state_apply_success` | State | `frontend/src/pages/candidate/CandidateHomePage.tsx:94` |
| `state_apply_error` | State | `frontend/src/pages/candidate/CandidateHomePage.tsx:96` |
| `final_state` | Final State | `frontend/src/pages/candidate/CandidateHomePage.tsx:94` |
| `initial_state` → `state_home` | Transition | `frontend/src/App.tsx:72` |
| `state_home` → `choice_cv` | Transition | `frontend/src/pages/candidate/CandidateHomePage.tsx:141` |
| `state_home` → `choice_apply` | Transition | `frontend/src/pages/candidate/CandidateHomePage.tsx:212` |
| `choice_cv` → `state_empty_cv` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:34` |
| `choice_cv` → `choice_ai` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:50` |
| `state_empty_cv` → `state_home` | Transition | `frontend/src/components/common/SiteHeader.tsx:46` |
| `state_empty_cv` → `final_state` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:110` |
| `choice_ai` → `state_matching` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:52` |
| `choice_ai` → `state_matching_fallback` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:57` |
| `choice_ai` → `state_error_matching` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:56` |
| `state_error_matching` → `state_home` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:63` |
| `state_error_matching` → `final_state` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:63` |
| `state_matching` → `choice_ai` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:67` |
| `state_matching` → `choice_job` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:158` |
| `state_matching` → `state_home` | Transition | `frontend/src/components/common/SiteHeader.tsx:46` |
| `state_matching_fallback` → `choice_ai` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:67` |
| `state_matching_fallback` → `choice_job` | Transition | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:139` |
| `state_matching_fallback` → `state_home` | Transition | `frontend/src/components/common/SiteHeader.tsx:46` |
| `choice_job` → `state_job_detail` | Transition | `frontend/src/pages/candidate/CandidateJobDetailPage.tsx:58` |
| `choice_job` → `state_job_not_found` | Transition | `frontend/src/pages/candidate/CandidateJobDetailPage.tsx:53` |
| `state_job_not_found` → `state_matching` | Transition | `frontend/src/pages/candidate/CandidateJobDetailPage.tsx:77` |
| `state_job_detail` → `state_matching` | Transition | `frontend/src/pages/candidate/CandidateJobDetailPage.tsx:77` |
| `state_job_detail` → `state_home` | Transition | `frontend/src/components/common/SiteHeader.tsx:46` |
| `state_job_detail` → `final_state` | Transition | `frontend/src/pages/candidate/CandidateJobDetailPage.tsx:154` |
| `choice_apply` → `state_apply_success` | Transition | `frontend/src/pages/candidate/CandidateHomePage.tsx:94` |
| `choice_apply` → `state_apply_error` | Transition | `frontend/src/pages/candidate/CandidateHomePage.tsx:96` |
| `state_apply_error` → `state_home` | Transition | `frontend/src/pages/candidate/CandidateHomePage.tsx:96` |
| `state_apply_success` → `final_state` | Transition | `frontend/src/pages/candidate/CandidateHomePage.tsx:94` |
| `state_apply_success` → `state_home` | Transition | `frontend/src/pages/candidate/CandidateHomePage.tsx:160` |

---

## Mâu thuẫn tài liệu – mã nguồn

1. **Vị trí thao tác ứng tuyển:** Trong kịch bản nghiệp vụ thông thường, người dùng thường xem chi tiết tin tuyển dụng rồi mới quyết định ứng tuyển. Tuy nhiên mã nguồn giao diện `CandidateJobDetailPage.tsx:154` hoàn toàn không có nút nộp đơn ứng tuyển (chỉ có nút "Ôn tập phỏng vấn" liên kết sang M4). Người dùng phải quay lại trang chủ ứng viên (`CandidateHomePage.tsx:212`) mới có nút "Ứng tuyển" tại khung `SidePanel`. Biểu đồ trạng thái phản ánh chính xác hành vi mã nguồn thật.
2. **Xử lý dự phòng khi dịch vụ AI gián đoạn:** Mã nguồn `CandidateMatchingPage.tsx:53-58` cài đặt cơ chế giữ điểm cũ hoặc hiển thị tin tuyển dụng chưa chấm kèm cảnh báo, giúp người dùng vẫn duyệt được tin việc khi dịch vụ AI gặp lỗi 502/503. Trạng thái `Hiện giao diện Việc làm phù hợp (chế độ dự phòng)` được bổ sung nhằm thể hiện chính xác hành vi này.

---

## Open questions

1. Trang chi tiết việc làm (`CandidateJobDetailPage.tsx`) hiện chỉ có nút "Ôn tập phỏng vấn" mà không có nút "Ứng tuyển", buộc ứng viên phải quay về trang chủ để nộp đơn. Cần xác nhận với nhóm phát triển xem trong các phiên bản tiếp theo có dự định bổ sung nút ứng tuyển trực tiếp trên trang chi tiết hay không.
