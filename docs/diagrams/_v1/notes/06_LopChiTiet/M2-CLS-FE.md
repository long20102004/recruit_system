# M2-CLS-FE — Biểu đồ lớp chi tiết: Tải lên CV PDF, kiểm tra và xác nhận các trường hồ sơ (Frontend)

## 1. Diễn giải vai trò từng lớp và luồng gọi chính

### 1.1. Nhóm package

Biểu đồ tổ chức theo mô hình MVC của phía client (theo ánh xạ ở DIAGRAM_RULES §1.2):

| Package | Nội dung | Nguồn |
|---|---|---|
| **View** | Page, component React và route guard của SPA | `frontend/src/pages/candidate/`, `frontend/src/components/common/`, `frontend/src/App.tsx` |
| **Controller** | React Context Provider + custom hook giữ trạng thái toàn cục | `frontend/src/context/ToastContext.tsx`, `frontend/src/context/AuthContext.tsx` |
| **Model** | API client gọi qua API Gateway và DTO trao đổi với recruitment-service | `frontend/src/api/client.ts` |

### 1.2. Vai trò từng lớp

| Lớp | Stereotype | Vai trò trong module M2 |
|---|---|---|
| `RequireAuth` | «boundary» | Route guard: trước khi vào `/candidate/cv`, đọc `user`/`loading` từ `useAuth()`; chuyển hướng về `/login`, `/choose-role` hoặc trang của role nếu không phải `CANDIDATE` (`App.tsx:22-37, 63-70`). |
| `CandidateCvPage` | «boundary» | Trang chính 3 bước (Tải lên → Kiểm tra → Xác nhận). State `step`, `fileName`, `fields`, `values`, `busy`, `loaded` (`:96-101`). Hàm module `cleanLines`/`valuesFrom` (`:24, :31`) chuẩn hóa giá trị đa dòng; `applyForm` (`:103`) chuyển `CvFormDto` thành state và tự chọn bước theo `analyzed`/`fileName`; `onUpload` (`:122`) kiểm tra `.pdf` rồi gọi `cvsApi.upload`; `onConfirm` (`:139`) kiểm tra `fileName` rồi gọi `cvsApi.confirm`; `setField` (`:158`) cập nhật một trường khi người dùng sửa. |
| `UploadZone` | «boundary» | Component kéo-thả/chọn file, tái sử dụng được: nhận callback `onFile` qua props (`UploadZone.tsx:4-18`), xử lý `handleFiles`/`onDragOver`/`onDragLeave`/`onDrop` (`:21-39`), mở hộp thoại chọn file qua `input[type=file]` ẩn (`:56-62`). |
| `FieldLines` | «boundary» | Component con nội bộ của `CandidateCvPage` (`:40-78`): hiển thị và cho sửa giá trị một trường (đơn dòng `TextInput` hoặc đa dòng `TextTextarea` theo `long`), hàm `update` (`:51`) chèn/split theo ký tự xuống dòng — khớp mô hình EAV đa dòng phía backend. |
| `LineView` | «boundary» | Component con ở Bước 3 (`:80-92`): hiển thị giá trị trường ở dạng chỉ đọc khi người dùng xem "Hồ sơ của bạn". |
| `Toast` | «boundary» | Hiển thị thông báo thành công/lỗi (`Toast.tsx:5-7`); được `ToastProvider` render khi có `message`. |
| `ToastContext` | «control» | Provider trạng thái toast toàn cục (`ToastContext.tsx:15-33`): hàm `toast(msg)` ghi message và tự xóa sau 2600ms (`:22`); `useToast()` (`:35`) cho page lấy hàm `toast` — dùng ở mọi nhánh thành công/lỗi của luồng M2 (`CandidateCvPage.tsx:124, 131, 133, 141, 150, 152`). |
| `AuthContext` | «control» | Nguồn trạng thái đăng nhập (`AuthContext.tsx:44-102`). Trong M2 chỉ phương thức `useAuth()` được gọi (bởi `RequireAuth`); `login/register/chooseRole/logout` thuộc module M1 nên không đưa vào biểu đồ. |
| `ApiClient` (file `api/client.ts`, hàm `api`/`getToken`/`setToken`) | «client» | Điểm đi qua duy nhất của mọi lời gọi HTTP: dựng URL từ `API_BASE` = `VITE_API_URL ?? "/api"` (`client.ts:1`), gắn `Authorization: Bearer` từ `localStorage` (`:40-41`), giữ `Content-Type: application/json` trừ khi body là `FormData` (`:37-39`), bọc lỗi thành `ApiError` (`:44-46`). |
| `cvsApi` | «client» | Nhóm 3 endpoint của module CV: `mine()` → `GET /api/cvs` (`:100`), `upload(file)` → `POST /api/cvs` với `FormData` (`:101-105`), `confirm(fields)` → `PUT /api/cvs` (`:106-110`). |
| `ApiError` | «entity» | Lớp lỗi của tầng client: giữ `status` HTTP và message lấy từ body phản hồi (`client.ts:14-21, 23-30`); `CandidateCvPage` đọc `e.message` để hiển thị toast (`:133, 152`). |
| `CvFormDto` | «entity» | DTO phản hồi của cả 3 endpoint CV: `fileName`, `parsingStatus`, `analyzed`, `fields` (`client.ts:225-230`). |
| `CvFieldDto` | «entity» | DTO một trường hồ sơ: `field`, `values` (`client.ts:220-223`); `confirm()` nhận mảng `CvFieldDto[]` bọc trong `{ fields }`. |

### 1.3. Luồng gọi chính (khớp M2-ACT)

1. **Vào trang:** `RequireAuth` gọi `useAuth()` của `AuthContext` để chặn quyền (`App.tsx:29, 66`), sau đó render `CandidateCvPage`.
2. **Khởi tạo:** `useEffect` trong `CandidateCvPage` gọi `cvsApi.mine()` → `ApiClient.api` (`GET /api/cvs`); có sẵn hồ sơ thì `applyForm` khôi phục bước hiện tại theo `analyzed`/`fileName` (`CandidateCvPage.tsx:114-120, 103-112`).
3. **Tải lên (Bước 1):** người dùng thả file → `UploadZone.onDrop` → `handleFiles` → callback `onFile` → `CandidateCvPage.onUpload`: sai `.pdf` thì `toast("Chỉ nhận file PDF")` ngay tại client (`:123-124`); đúng thì `cvsApi.upload(file)` (đóng gói `FormData`) → `ApiClient.api` (`POST /api/cvs`, kèm `Authorization`) → nhận `CvFormDto` → `applyForm(form, 2)` và `toast` thành công (`:129-131`).
4. **Kiểm tra (Bước 2):** người dùng sửa qua `FieldLines.update` → `setField` cập nhật `values` (`:158-160, 51-55`).
5. **Xác nhận:** `onConfirm`: chưa có file thì `toast("Hãy tải CV trước")` (`:140-141`); ngược lại `cvsApi.confirm(fields.map(...cleanLines...))` → `ApiClient.api` (`PUT /api/cvs`) → `applyForm(form, 3)` → Bước 3 render `LineView` (`:146-150, 173-226`).
6. **Lỗi:** mọi `ApiError` bị bắt trong `onUpload`/`onConfirm` và hiển thị qua `ToastContext.toast` (`:132-133, 151-152`) — thông điệp lỗi lấy đúng `message` trả về từ recruitment-service.

## 2. Pattern có thật trong code (kèm dẫn chứng và ưu điểm cho HireLens)

### 2.1. Facade — API client thống nhất (`api<T>` + `ApiError`)

- **Vai trò:** `ApiClient.api` là mặt tiền duy nhất che giấu chi tiết fetch: base URL của API Gateway (`VITE_API_URL ?? "/api"`, `client.ts:1`), gắn token, xử lý `FormData`, parse lỗi (`client.ts:32-49`). Các nhóm endpoint (`authApi`, `jobsApi`, `cvsApi`, …) chỉ nêu path nghiệp vụ.
- **Ưu điểm cụ thể:** toàn bộ ~20 endpoint của FE dùng chung một chỗ gắn `Authorization`, nên việc đổi cách lưu token hay đổi cổng gateway chỉ sửa một file; lỗi HTTP 400/401/403/422/502 từ recruitment-service được chuyển thành `ApiError` với đúng `message` backend (`client.ts:23-30`), để `CandidateCvPage` hiển thị toast chính xác ("Hãy tải CV trước", "Field không nằm trong cấu hình CV_FIELD…" mà không cần FE tự diễn dịch lại mã lỗi.

### 2.2. DTO (Data Transfer Object)

- **Vai trò:** `CvFormDto`, `CvFieldDto` (`client.ts:220-230`) là bản mô tả TypeScript của hợp đồng phản hồi từ `CvController` bên recruitment-service.
- **Ưu điểm cụ thể:** backend lưu hồ sơ theo mô hình EAV (`cv_data` nhiều dòng `(field, value)`) nhưng FE chỉ cần làm việc với `fields: CvFieldDto[]`; nếu cách lưu phía DB thay đổi thì hợp đồng DTO này giữ nguyên, FE không phải sửa. Kiểu `string[]` cho `values` cũng ép FE xử lý đúng dữ liệu đa dòng (kỹ năng, học vấn) ngay từ lúc compile.

### 2.3. Context / Provider (React Context)

- **Vai trò:** `ToastContext` (`ToastContext.tsx:15-33`) và `AuthContext` (`AuthContext.tsx:30-102`) dùng `createContext` + `Provider` + `useContext`, được mount một lần ở gốc app (`App.tsx:145-148`).
- **Ưu điểm cụ thể:** `CandidateCvPage` gọi `toast()` ở 6 điểm (thành công, lỗi PDF, lỗi HTTP, chưa có file…) mà không cần nhận prop qua chuỗi component; Provider là nơi duy nhất quyết định thời gian hiển thị (2600ms, `ToastContext.tsx:22`) và cách render `Toast`, nên đồng bộ hành vi thông báo trên toàn hệ thống. `AuthContext` cho phép `RequireAuth` chặn route `/candidate/cv` theo role mà page không phải tự kiểm tra quyền.

### 2.4. Custom Hook (kèm bảo vệ lỗi sử dụng)

- **Vai trò:** `useToast()` (`ToastContext.tsx:35-41`) và `useAuth()` (`AuthContext.tsx:104-108`) bọc `useContext` và ném lỗi nếu dùng ngoài Provider.
- **Ưu điểm cụ thể:** lỗi "quên bọc Provider" bị phát hiện ngay lúc chạy thay vì âm thầm nhận `null`; các page chỉ thấy interface gọn (`{ toast }`, `{ user, loading }`) thay vì toàn bộ state nội bộ của Provider.

### 2.5. Dependency Injection qua callback (Inversion of Control)

- **Vai trò:** `UploadZone` không biết gì về nghiệp vụ CV: nó nhận callback `onFile?: (file: File) => void` qua props (`UploadZone.tsx:8`) và chính `CandidateCvPage` tiêm `onUpload` vào (`CandidateCvPage.tsx:246`).
- **Ưu điểm cụ thể:** component tải file dùng lại được ở chỗ khác (ví dụ trang recruiter) chỉ bằng tiêm callback khác; logic kiểm tra `.pdf` thuộc về page gọi nên không bị đóng cứng trong component UI.

### 2.6. Mapper / Adapter nội bộ (DTO → state biểu mẫu)

- **Vai trò:** `cleanLines` và `valuesFrom` (`CandidateCvPage.tsx:24-38`) chuyển `CvFormDto.fields` (danh sách `CvFieldDto`) thành `Record<string, string[]>` phục vụ biểu mẫu; `applyForm` (`:103-112`) là điểm chuyển tiếp duy nhất DTO → state và tự suy ra bước hiện tại từ `analyzed`/`fileName`.
- **Ưu điểm cụ thể:** phần còn lại của page không đụng tới cấu trúc DTO; khi muốn thêm dạng hiển thị (ví dụ gộp dòng trống) chỉ sửa `cleanLines`. Việc chọn `step` tập trung một chỗ tránh trạng thái bước bị lệch giữa "tải lại trang" và "vừa upload xong".

### 2.7. Route Guard (bộ lọc phía client)

- **Vai trò:** `RequireAuth` (`App.tsx:22-37`) bọc route `/candidate/cv` với `roles={["CANDIDATE"]}` (`App.tsx:63-70`): chưa đăng nhập → `/login`, chưa chọn role → `/choose-role`, sai role → trang của role đó.
- **Ưu điểm cụ thể:** ứng viên không thể vào trang CV khi chưa có hồ sơ/quyền, giảm số request lỗi 401/403 gửi lên recruitment-service; đây là lớp phòng thủ thứ nhất, phía backend `CvService` vẫn kiểm tra lại `Role.CANDIDATE` (phòng thủ hai tầng, khớp luồng N05-N06 của M2-ACT).

### Không có trong code FE của module này

Repository/DAO, Factory, Strategy, Observer/Event bus, Singleton GoF: không tìm thấy. `ToastProvider`/`AuthProvider` chỉ là một instance duy nhất trên cây React (đặc điểm của Provider), không phải pattern Singleton GoF — không nêu trong báo cáo. Mối quan hệ giữa FE và backend là HTTP/REST qua API Gateway, không có Adapter gọi trực tiếp CSDL.

## 3. Bảng truy vết phần tử → nguồn

| Phần tử | Nguồn |
|---|---|
| `CandidateCvPage` (class, state, các operation) | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:94, 96-101, 103, 114, 122, 129, 133, 139, 146, 158, 21-22, 24, 31` |
| `FieldLines` | `CandidateCvPage.tsx:40, 51` |
| `LineView` | `CandidateCvPage.tsx:80` |
| `UploadZone` | `source/recruit_system/frontend/src/components/common/UploadZone.tsx:4, 12, 19, 21, 26, 31, 35, 56-62` |
| `Toast` | `source/recruit_system/frontend/src/components/common/Toast.tsx:5` |
| `RequireAuth` | `source/recruit_system/frontend/src/App.tsx:22, 29, 63-70` |
| `ToastContext` | `source/recruit_system/frontend/src/context/ToastContext.tsx:11, 15, 17, 18, 20, 30, 35` |
| `AuthContext` | `source/recruit_system/frontend/src/context/AuthContext.tsx:19, 30, 44, 45, 46, 104` |
| `ApiClient` (`api`, `getToken`, `setToken`, `parseError`, `ApiError`) | `source/recruit_system/frontend/src/api/client.ts:1, 3, 5, 9, 14, 15, 17, 23, 32, 40-41, 45` |
| `cvsApi` | `source/recruit_system/frontend/src/api/client.ts:99, 100, 101-105, 106-110` |
| `CvFormDto` | `source/recruit_system/frontend/src/api/client.ts:225` |
| `CvFieldDto` | `source/recruit_system/frontend/src/api/client.ts:220` |

## 4. Phạm vi chọn lọc và loại trừ (đối chiếu M2-ACT)

- Chỉ lấy lớp thực sự chạy trong luồng N00-N25 của M2-ACT: trang CV, `UploadZone` (N01), kiểm tra `.pdf` (N02-N03), gọi `POST/PUT /api/cvs` (N04, N18), toast lỗi/thành công (N03, N17, N24), route guard trước khi vào trang, DTO trao đổi.
- **Loại trừ** (có trong source nhưng không nằm trong luồng M2): `authApi`, `jobsApi`, `applicationsApi`, `matchingApi`, `interviewsApi`, `dashboardApi` (module khác — `cvsApi` cũng chỉ gồm 3 hàm được gọi trong M2); `AuthContext.login/register/chooseRole/logout` (M1); `types/index.ts` chứa interface mock cũ (`ExtractedCv`, `Job`, `MatchResult`, `InterviewQuestion`, `InterviewSession`…) chỉ dùng bởi `data/mockData.ts`, không được `CandidateCvPage` dùng; các component trang trí chung (`Steps`, `Step`, `Page`, `Panel`, `Button`, `SiteHeader`, `Grid2`, `SplitActions`, `TextInput`, `TextTextarea`) không chứa logic nghiệp vụ M2.
- React component là hàm: mô hình hóa thành class «boundary», props/state là attributes, hàm nội bộ là operations; operation trùng tên lớp thể hiện chính hàm component (render entry). `visibility` `-` dùng cho hàm/state khai báo bên trong component hoặc không export; `+` dùng cho những gì export hoặc nhận qua props.

## 5. Mâu thuẫn và cần xác nhận

- **Không phát hiện mâu thuẫn tài liệu–source trong phạm vi FE module M2:** `docs/Module3_Interview_Flow.md` chỉ đặc tả luồng phỏng vấn (M4), không mô tả M2; file PDF báo cáo chưa có trên đĩa nên không có gì để đối chiếu.
- **Ghi chú:** `App.tsx` chặn route `/candidate/cv` bằng `RequireAuth roles={["CANDIDATE"]}` (cho phép cả `ADMIN` qua điều kiện `user.role !== "ADMIN"` ở `App.tsx:33`) — tức ADMIN cũng xem được trang CV của ứng viên; phía backend `CvService` yêu cầu đúng `CANDIDATE`. Không mâu thuẫn chức năng (ADMIN không upload được), nhưng ghi lại để biết hành vi hai tầng không giống hệt nhau.
- [cần xác nhận] AuthContext đưa vào biểu đồ chỉ với `useAuth()`; có cần thể hiện đủ các phương thức auth để đồng bộ với M1-CLS-FE?
- [cần xác nhận] Các interface mock trong `types/index.ts` đã loại khỏi biểu đồ; có cần giữ lại làm tài liệu tham chiếu không?
