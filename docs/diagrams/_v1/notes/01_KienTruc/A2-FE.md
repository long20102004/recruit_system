# Ghi chú kiến trúc chiều ngang MVC của Frontend (A2-FE)

## 1. Giới thiệu và Bối cảnh
Biểu đồ **A2-FE** (`diagrams/specs/01_KienTruc/A2-FE.json`) mô tả kiến trúc phân tầng chiều ngang theo mô hình **MVC (Model - View - Controller)** áp dụng cho ứng dụng Single Page Application (SPA) của HireLens, được xây dựng bằng React 18, TypeScript và Vite (`source/recruit_system/frontend/`).

Theo quy ước chuẩn được quy định tại [DIAGRAM_RULES.md §1.2](file:///home/hocnguyen/Documents/VPProjects/DIAGRAM_RULES.md#L52-L66) và khuyến nghị tinh gọn số lượng phần tử (§0.3):
- Tầng **View**: Gồm định tuyến (`routing`), các trang màn hình tiêu biểu đại diện cho 4 luồng chính M1–M4 (`LoginPage`, `CandidateCvPage`, `CandidateMatchingPage`, `CandidateInterviewPage`).
- Tầng **Controller**: Gồm các React Context (`AuthContext`, `ToastContext`) và các API client modules tương ứng 4 luồng chính (`authApi`, `cvsApi`, `matchingApi`, `interviewsApi`).
- Tầng **Model**: Gồm HTTP Client cơ sở (`api()`, `ApiError`), các DTOs tương ứng 4 luồng chính (`UserDto`, `CvFormDto`, `MatchDto`, `SessionDto`) và bộ chuyển đổi dữ liệu (`mappers`).

Chiều phụ thuộc chính: **View → Controller → Model**.

---

## 2. Bảng ánh xạ thư mục mã nguồn sang các tầng MVC

| Tầng MVC | Package / Module con | Thành phần tiêu biểu trong Spec (M1-M4) | Đường dẫn và dòng truy vết | Vai trò / Trách nhiệm |
|---|---|---|---|---|
| **View** | `routing` | `AppRoutes`, `RequireAuth` | [App.tsx:22-63](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/App.tsx#L22-L63) | Cấu hình 14 routes điều hướng, bảo vệ truy cập theo vai trò. |
| **View** | `pages` (Tiêu biểu M1–M4) | `LoginPage`, `CandidateCvPage`, `CandidateMatchingPage`, `CandidateInterviewPage` | [LoginPage.tsx:17](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/pages/LoginPage.tsx#L17), [CandidateCvPage.tsx:9](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx#L9), [CandidateMatchingPage.tsx:21](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx#L21), [CandidateInterviewPage.tsx:9](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx#L9) | Đại diện cho 4 luồng người dùng chính: M1 (Đăng nhập), M2 (Tải/xác nhận CV), M3 (Đối sánh việc làm), M4 (Luyện phỏng vấn AI). |
| **Controller** | `context` | `AuthContext`, `ToastContext` | [AuthContext.tsx:30](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/context/AuthContext.tsx#L30), [ToastContext.tsx:15](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/context/ToastContext.tsx#L15) | Quản lý trạng thái phiên đăng nhập, lưu trữ token, phân quyền và hiển thị thông báo phản hồi thao tác. |
| **Controller** | `api` (Endpoints Controller) | `authApi`, `cvsApi`, `matchingApi`, `interviewsApi` | [client.ts:51](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L51), [client.ts:99](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L99), [client.ts:113](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L113), [client.ts:125](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L125) | Điều phối các hành động nghiệp vụ từ giao diện, đóng gói tham số và gửi request tới các microservices qua API Gateway. |
| **Model** | `client` | `api (HTTP Client)`, `ApiError` | [client.ts:14-49](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L14-L49) | HTTP Client cơ sở gắn Bearer token JWT vào header, parse phản hồi JSON và xử lý mã lỗi HTTP. |
| **Model** | `types` (DTOs) | `UserDto`, `CvFormDto`, `MatchDto`, `SessionDto` | [client.ts:153](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L153), [client.ts:225](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L225), [client.ts:232](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L232), [client.ts:285](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L285) | Khai báo cấu trúc dữ liệu thực thể trao đổi giữa client và server cho 4 luồng chính. |
| **Model** | `utils & mappers` | `mappers` | [mappers.ts:31](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/utils/mappers.ts#L31) | Chuyển đổi dữ liệu từ dạng DTO thô sang View Model phù hợp cho giao diện. |

---

## 3. Danh sách các lớp được lược bớt để đảm bảo giới hạn kích thước
Để biểu đồ không vượt quá ~20-30 phần tử chính theo quy chuẩn [DIAGRAM_RULES.md §0.3](file:///home/hocnguyen/Documents/VPProjects/DIAGRAM_RULES.md#L25) và §1.2 ("chỉ vài lớp tiêu biểu"), các phần tử sau đã được lược bỏ khỏi biểu đồ:
- **Tầng View**:
  - `pages`: `RegisterPage`, `ChooseRolePage`, `PublicHomePage`, `CandidateJobDetailPage`, `RecruiterJobsPage` (do đồ án tập trung trình bày M1-M4, các màn hình phụ hoặc của recruiter M5 được giảm lược).
  - `components`: Toàn bộ package `components` gồm `SiteHeader`, `UploadZone`, `MatchItem`, `ChatBubble` (được ẩn để tập trung vào kiến trúc phân tầng chính).
- **Tầng Controller**:
  - `api`: `jobsApi`, `applicationsApi`, `dashboardApi` (thuộc luồng việc làm phụ và recruiter dashboard).
- **Tầng Model**:
  - `types`: `JobDto`, `ApplicationDto`, `EvaluationDto`.
  - `utils`: `accountUtils`, `jobsUtils`.

---

## 4. Phân tích chi tiết các luồng tương tác giữa các tầng

### 4.1. Luồng View → Controller
- Các thành phần giao diện (Pages) không gọi trực tiếp HTTP fetch. Chúng sử dụng các custom hook từ Controller (`useAuth()`, `useToast()`) hoặc gọi các hàm đóng gói nghiệp vụ trong các API controller (`authApi`, `cvsApi.upload()`, `matchingApi.mine()`, `interviewsApi.submit()`).
- Ví dụ:
  - `LoginPage` gọi `useAuth()` để đăng nhập, nhận thông tin người dùng và lưu token.
  - `CandidateCvPage` gọi `cvsApi` để tải lên và xác nhận nội dung CV.
  - `CandidateMatchingPage` gọi `matchingApi` để lấy danh sách việc làm phù hợp và độ match.
  - `CandidateInterviewPage` gọi `interviewsApi` để khởi tạo phiên phỏng vấn và gửi câu trả lời.

### 4.2. Luồng Controller → Model
- Các API controllers nhận payload từ View, chuẩn hóa định dạng (JSON hoặc `FormData`) rồi ủy quyền cho hạ tầng `api()` (HTTP Client) của Model.
- Tầng Model gắn kèm Bearer token JWT (`hirelens_token`), gửi request qua Nginx Gateway (`/api/*`), giải mã dữ liệu trả về thành các kiểu dữ liệu `Dto` chuẩn (`UserDto`, `CvFormDto`, `MatchDto`, `SessionDto`) và ném `ApiError` khi có lỗi HTTP.
- Dữ liệu nhận về được ánh xạ qua `mappers` để hiển thị trực tiếp trên giao diện.

---

## 5. Mâu thuẫn giữa Tài liệu và Mã nguồn thực tế
1. **Kiến trúc ứng dụng Client-Server vs. Monolith**:
   - Báo cáo đồ án cũ (bản v6) mô tả mô hình monolithic với backend nguyên khối.
   - Mã nguồn thực tế tại commit `1c96706` đã tách biệt hoàn toàn frontend thành một Single Page Application (React + TypeScript + Vite) độc lập, kết nối tới hệ thống microservices qua Nginx API Gateway trên cổng `8080` (với tiền tố `/api/`).
2. **Quản lý dữ liệu Mock**:
   - Trong `frontend/src/data/mockData.ts` còn tồn tại dữ liệu mẫu từ bản nguyên mẫu. Tuy nhiên các trang trong `pages/` đều đã chuyển hẳn sang gọi API thật qua `api/client.ts`. Biểu đồ A2-FE phản ánh trung thực mã nguồn kết nối thực tế.

---

## 6. Câu hỏi mở (Open Questions)
- Không có câu hỏi mở nào. Cấu trúc mã nguồn frontend được phân tách rõ ràng và đã được thu gọn tiêu biểu đúng theo 4 luồng M1–M4.
