# M3-CLS-FE — Biểu đồ lớp chi tiết: Đối sánh, xem chi tiết việc, ứng tuyển (Frontend)

Phạm vi: `source/recruit_system/frontend/src` (React + Vite + TypeScript). Chỉ gồm các lớp/phương thức thực sự tham gia các luồng của `M3-ACT`; không chép toàn bộ frontend. 18 lớp, 5 package, 32 quan hệ.

## 1. Vai trò từng lớp và luồng gọi chính

### 1.1. Tầng View (boundary)

| Lớp | Vai trò | Nguồn |
|---|---|---|
| `CandidateHomePage` | Trang chủ ứng viên: tải danh sách việc, CV, điểm phù hợp; chọn tin ở panel phải; phát sinh ứng tuyển qua `apply(jobId)`. State: `keyword`, `city`, `mode`, `jobs`, `matches`, `cvReady`, `selectedId`. | `pages/candidate/CandidateHomePage.tsx:36` |
| `CandidateMatchingPage` | Trang "Công việc phù hợp với tôi": kiểm tra CV đã phân tích, tải tin, lấy điểm cũ rồi làm mới điểm; xếp hạng giảm dần và render `MatchItem`. | `pages/candidate/CandidateMatchingPage.tsx:21` |
| `CandidateJobDetailPage` | Trang chi tiết việc theo `:jobId`: kiểm tra mã, tải tin, map sang mô hình hiển thị; chỉ có nút "Ôn tập phỏng vấn", **không có nút ứng tuyển**. | `pages/candidate/CandidateJobDetailPage.tsx:44` |
| `JobCard` | Component trình bày một tin trong danh sách; nhận `job`, `match` (tùy chọn) và callback `onApply`, không tự gọi API. | `components/common/JobCard.tsx:17` |
| `MatchItem` | Component trình bày một kết quả xếp hạng: hạng, điểm, thanh tiến trình, kỹ năng thiếu (`gapLine`), nút "Xem chi tiết". | `components/common/MatchItem.tsx:31` |

### 1.2. Tầng Controller (control)

| Lớp | Vai trò | Nguồn |
|---|---|---|
| `AuthProvider` | Provider giữ `user`, `loading`; cung cấp `login/register/chooseRole/logout` qua context. Trang dùng `useAuth()` để lấy `user.fullName` và header mode. | `context/AuthContext.tsx:44`, hook `:104` |
| `ToastProvider` | Provider giữ `message` và hàm `toast(msg)` (tự xóa sau 2600 ms); cả 3 trang dùng `useToast()`. | `context/ToastContext.tsx:17`, hook `:35` |

Cả hai provider được bọc ngoài `AppRoutes` tại `App.tsx:145-149`, nên mọi trang M3 đều nằm trong context.

### 1.3. Tầng Model — client

| Lớp | Vai trò | Nguồn |
|---|---|---|
| `api` | Hàm gọi HTTP lõi: ghép `API_BASE`, gắn `Authorization: Bearer`, `Content-Type`, xử lý 204, ném `ApiError`; kèm `getToken/setToken` đọc ghi `localStorage`. | `api/client.ts:32`, token `:5`, `:9` |
| `jobsApi` | Nhóm endpoint `/jobs`: `list`, `mine`, `get`. Module M3 dùng `list()` và `get(id)`. | `api/client.ts:70` |
| `applicationsApi` | Nhóm endpoint `/applications`: `apply(jobId, body?)` → `POST /applications/jobs/{jobId}`. | `api/client.ts:89` |
| `cvsApi` | Nhóm endpoint `/cvs`: `mine()` → `GET /cvs`, dùng để đọc cờ `analyzed`. | `api/client.ts:99` |
| `matchingApi` | Nhóm endpoint `/matching`: `mine()` (`GET /matching/mine`) và `refreshMine()` (`POST /matching/mine/refresh`). | `api/client.ts:113` |
| `mappers` | Module hàm thuần chuyển DTO → mô hình hiển thị: `mapJob`, `mapMatch`; điền mặc định cho trường null và tính `logo`, `postedAgo`. | `utils/mappers.ts:31`, `:57` |

### 1.4. Tầng Model — entity

| Lớp | Vai trò | Nguồn |
|---|---|---|
| `JobDto` | Hợp đồng JSON tin tuyển dụng từ recruitment-service; nhiều trường nullable. | `api/client.ts:171` |
| `MatchDto` | Hợp đồng JSON điểm đối sánh (overallScore, similarity, matched/missing skills, reasons, rankPosition…). | `api/client.ts:232` |
| `CvFormDto` | Hợp đồng JSON hồ sơ CV; trang đối sánh chỉ dùng `analyzed`, `fields`. | `api/client.ts:225` |
| `Job` | Mô hình tin tuyển dụng của giao diện (id `string`, salary/location đã chuẩn hóa, `logo`, `postedAgo`, `distanceKm`). | `types/index.ts:21` |
| `MatchResult` | Mô hình điểm phù hợp của giao diện (jobId `string`, score đã ép `number`). | `types/index.ts:44` |

### 1.5. Luồng gọi chính (lần theo code)

**A. Mở trang đối sánh (`/candidate/matching`)**

1. `CandidateMatchingPage` mount → `useEffect` gọi `load()` và bắt lỗi bằng `toast` (`CandidateMatchingPage.tsx:61-65`).
2. `load()` gọi `cvsApi.mine()` (`:31`), đọc `form.analyzed` (`:32`). Nếu chưa phân tích: xóa `matches/jobs`, trả `"empty"` (`:34-38`) → giao diện hiện hướng dẫn tải CV (`:104-114`).
3. `jobsApi.list()` (`:40`) → `GET /jobs`; lưu `jobs`.
4. `matchingApi.mine()` (`:44`) lấy điểm đã lưu; lỗi thì coi như mảng rỗng (`:43-47`).
5. `matchingApi.refreshMine()` (`:50`): thành công thì thay `matches`, xóa `scoreError`, trả `"scored"` (`:51-52`).
6. Nếu refresh lỗi: giữ điểm cũ; chỉ ném lỗi khi không có cả điểm lẫn tin (`:53-58`). `rematch()` (`:67-79`) gọi lại `load()` và thông báo theo kết quả.
7. Render: sắp xếp `overallScore` giảm dần (`:81-83`), `mapJob`/`mapMatch` (`:127`, `:150-151`) rồi render `MatchItem` (`:154-160`).

**B. Xem chi tiết việc**

1. Từ `MatchItem`/nút "Xem chi tiết" điều hướng `/candidate/jobs/{id}` (`CandidateMatchingPage.tsx:139`, `:158`).
2. `CandidateJobDetailPage` lấy `jobId` bằng `useParams` (`:45`), kiểm tra `Number.isFinite` trước khi gọi API (`:51-55`).
3. `jobsApi.get(id)` (`:56-57`) → `GET /jobs/{id}`; thành công `mapJob(dto)` (`:58`), lỗi `toast` (`:59`).
4. Hiển thị mô tả/yêu cầu/kỹ năng; nhánh không có tin hiện "Không tìm thấy tin tuyển dụng này" (`:85-86`).

**C. Ứng tuyển**

1. `CandidateHomePage` mount: `jobsApi.list()` (`:48`), `cvsApi.mine()` (`:49`); nếu `analyzed` thì `matchingApi.mine()` (`:58`).
2. `useMemo` map danh sách (`:66-67`), lọc/sắp xếp bằng `filterJobs`, `jobById`, `matchForJob` (`:69-89`).
3. Người dùng bấm "Ứng tuyển" ở `JobCard` (truyền `onApply={apply}`, `:169`) hoặc ở panel chi tiết (`:212`).
4. `apply(jobId)` → `applicationsApi.apply(Number(jobId))` (`:91-93`) → `POST /applications/jobs/{jobId}`; toast thành công/thất bại (`:94-97`). Kết quả `ApplicationDto` không được dùng.

## 2. Pattern thực sự có trong code

### 2.1. Context / Provider (React Context)

- **Lớp tham gia:** `AuthProvider` + `useAuth` (`context/AuthContext.tsx:30`, `:44`, `:104`); `ToastProvider` + `useToast` (`context/ToastContext.tsx:15`, `:17`, `:35`); gắn vào cây tại `App.tsx:145-149`.
- **Vai trò:** Provider giữ trạng thái dùng chung; hook là điểm truy cập duy nhất cho lớp View. `CandidateHomePage` lấy `user` (`:37`), cả 3 trang lấy `toast`.
- **Ưu điểm cụ thể cho HireLens:** chỉ một nguồn `user` cho toàn bộ khu vực ứng viên, nên kiểm tra `roleChosen`/role ở `RequireAuth` (`App.tsx:22-37`) và hiển thị tên ở trang chủ không lệch nhau; thông báo lỗi API (401/403/409, lỗi chấm điểm) hiển thị đồng nhất mà không phải truyền callback `toast` xuyên qua `JobCard`/`MatchItem`. Khi đổi cách lưu token chỉ sửa `AuthProvider`, không sửa trang.

### 2.2. Adapter + DTO

- **Lớp tham gia:** DTO `JobDto`, `MatchDto`, `CvFormDto` (`api/client.ts:171`, `:232`, `:225`); adapter `mapJob`, `mapMatch` (`utils/mappers.ts:31`, `:57`); mô hình đích `Job`, `MatchResult` (`types/index.ts:21`, `:44`).
- **Vai trò:** DTO phản ánh đúng JSON của recruitment-service; mapper chuyển sang kiểu mà component cần.
- **Ưu điểm cụ thể:** backend trả nhiều trường `null` (`location`, `salaryText`, `workType`, `level`, `minYears`) và `id` dạng số, trong khi giao diện cần `id: string`, `salary: "Thỏa thuận"`, `workType: "Hybrid"`, `level: "Junior"`, `minYears: 0` (`mappers.ts:32-54`). Nhờ adapter, `JobCard`/`MatchItem` không phải rải `??` khắp nơi và không vỡ khi backend đổi tên trường; `MatchDto.overallScore` kiểu number nhưng được ép `Number(...)` để tránh chuỗi từ JSON (`mappers.ts:61`). `postedAt` ISO được đổi thành "x giờ trước" (`mappers.ts:72-79`) chỉ ở một chỗ.

### 2.3. Facade (mức module API client)

- **Lớp tham gia:** `api<T>` (`api/client.ts:32-49`) và các facade con `jobsApi` (`:70`), `applicationsApi` (`:89`), `cvsApi` (`:99`), `matchingApi` (`:113`).
- **Vai trò:** `api` che giấu chi tiết `fetch`, base URL, header, parse lỗi; facade con nhóm endpoint theo nghiệp vụ.
- **Ưu điểm cụ thể:** cả 3 trang chỉ gọi `jobsApi.get(1)` thay vì tự dựng `fetch("/api/jobs/1")`; token Bearer và `Content-Type` được gắn tự động (`:40-41`), xử lý `204` (`:47`) và lỗi JSON (`:23-30`, `:44-46`) tập trung. Đổi `VITE_API_URL` hoặc thêm header là sửa một hàm, không sửa 4 lời gọi rải rác. Đường dẫn khớp gateway: `/api/(jobs|cvs|applications|matching)` (`infra/gateway/nginx.conf:23`).

### 2.4. Dependency Injection qua props/callback

- **Lớp tham gia:** `CandidateHomePage` truyền `onApply={apply}` (`CandidateHomePage.tsx:169`); `JobCard` khai báo prop `onApply?: (jobId: string) => void` (`JobCard.tsx:14`) và gọi `onApply?.(job.id)` (`:66`).
- **Vai trò:** component hiển thị không biết API; hành vi ứng tuyển do trang inject.
- **Ưu điểm cụ thể:** `JobCard` không import `applicationsApi`, nên dùng lại được ở danh sách việc công khai hoặc trang nhà tuyển dụng mà không mang theo logic ứng tuyển; muốn đổi cách nộp (ví dụ mở form cover letter) chỉ sửa `apply` ở trang. Cũng giúp kiểm thử `JobCard` bằng callback giả, không cần mock mạng.

### 2.5. Module singleton (ES module)

- **Lớp tham gia:** các `export const ...Api` (`client.ts:70`, `:89`, `:99`, `:113`) và biến module `API_BASE`, `TOKEN_KEY` (`:1`, `:3`).
- **Vai trò:** mỗi nhóm API chỉ được khởi tạo một lần khi bundle nạp module; token đọc từ cùng một key.
- **Ưu điểm cụ thể:** tránh nhiều "client" cùng tồn tại với base URL/token khác nhau; `getToken()` trong `api()` luôn thấy token mới nhất do `AuthProvider` ghi (`AuthContext.tsx:63`), nên sau đăng nhập không cần khởi tạo lại client.

## 3. Bảng truy vết (phần tử → nguồn)

| Phần tử | Nguồn |
|---|---|
| `CandidateHomePage` | `frontend/src/pages/candidate/CandidateHomePage.tsx:36` |
| `CandidateMatchingPage` | `frontend/src/pages/candidate/CandidateMatchingPage.tsx:21` |
| `CandidateJobDetailPage` | `frontend/src/pages/candidate/CandidateJobDetailPage.tsx:44` |
| `JobCard` | `frontend/src/components/common/JobCard.tsx:17` |
| `MatchItem` | `frontend/src/components/common/MatchItem.tsx:31` |
| `AuthProvider` | `frontend/src/context/AuthContext.tsx:44` |
| `ToastProvider` | `frontend/src/context/ToastContext.tsx:17` |
| `api` | `frontend/src/api/client.ts:32` |
| `jobsApi` | `frontend/src/api/client.ts:70` |
| `applicationsApi` | `frontend/src/api/client.ts:89` |
| `cvsApi` | `frontend/src/api/client.ts:99` |
| `matchingApi` | `frontend/src/api/client.ts:113` |
| `mappers` | `frontend/src/utils/mappers.ts:31` |
| `JobDto` | `frontend/src/api/client.ts:171` |
| `MatchDto` | `frontend/src/api/client.ts:232` |
| `CvFormDto` | `frontend/src/api/client.ts:225` |
| `Job` | `frontend/src/types/index.ts:21` |
| `MatchResult` | `frontend/src/types/index.ts:44` |

## 4. Mâu thuẫn và khác biệt tài liệu – source

1. **Đánh số module:** `source/recruit_system/docs/Module3_Interview_Flow.md:1` gọi "Module 3" là luyện phỏng vấn; báo cáo/task gọi M3 là đối sánh, xem chi tiết, ứng tuyển. Đây là khác định danh phạm vi, không phải mâu thuẫn nghiệp vụ; biểu đồ này chỉ lấy phần matching/apply.
2. **Thiếu thao tác ứng tuyển ở trang chi tiết:** yêu cầu module gộp "xem chi tiết việc, ứng tuyển", nhưng source chỉ đặt ứng tuyển ở `CandidateHomePage.tsx:212` và `JobCard` (`JobCard.tsx:66`); `CandidateJobDetailPage.tsx:153-159` chỉ có nút ôn phỏng vấn. Ghi nhận, không tự thêm nút.
3. **Kiểu `jobId` khác giữa hai tầng:** `MatchDto.jobId: number` (`client.ts:234`) vs `MatchResult.jobId: string` (`types/index.ts:45`). Đây là chủ ý của adapter (`mappers.ts:59`), không phải lỗi; nhưng nếu bỏ `mappers` sẽ so sánh sai kiểu.
4. **Bộ lọc "gần bạn" không có dữ liệu:** `Job.nearYou`/`distanceKm` (`types/index.ts:31-33`) luôn được `mapJob` gán `null`/`false` (`mappers.ts:43-45`); `filterJobs` có nhánh `nearOnly` (`utils/jobs.ts:25`) nhưng `CandidateHomePage` chỉ truyền `keyword`, `city` (`:78`). Nhánh này hiện không dùng.
5. **Tải toàn bộ tin rồi lọc ở client:** `jobsApi.list()` gọi `/jobs` không tham số (`CandidateHomePage.tsx:48`, `CandidateMatchingPage.tsx:40`) trong khi facade hỗ trợ `keyword/city` (`client.ts:71-76`). Với dữ liệu lớn, lọc client sẽ tốn băng thông; ghi nhận là điểm cần cải thiện, không phải mâu thuẫn tài liệu.
6. **PDF báo cáo chưa có trên đĩa**, nên không đối chiếu trực tiếp được với mục 5.7 của báo cáo. `docs/schema.dbml` chỉ mô tả CSDL, không đặc tả UI/luồng này.

## 5. Ghi chú kỹ thuật khi đọc biểu đồ

- Các trang là hàm React, không có thuộc tính/phương thức theo nghĩa OOP: `attributes` là state/props, `operations` là handler có tên trong source. Trang chi tiết không có handler đặt tên nên `operations` rỗng; lời gọi `jobsApi.get` nằm trong `useEffect` (`CandidateJobDetailPage.tsx:50-61`).
- `useAuth`/`useToast` là hook export; biểu đồ quy chúng về `AuthProvider`/`ToastProvider` để giữ số lớp ≤ 18. Quan hệ View → Controller mang nhãn `useAuth()`/`useToast()`.
- `mappers` và `api` là module/function chứ không phải lớp TypeScript; được mô hình hóa thành class để thể hiện trách nhiệm và chữ ký hàm.
- Quan hệ `composition` từ trang tới `JobCard`/`MatchItem` phản ánh việc trang render danh sách con; `JobCard`/`MatchItem` không tồn tại độc lập ngoài ngữ cảnh danh sách.
