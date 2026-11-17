# CLS-M2 — Biểu đồ lớp chi tiết chức năng Tải và xác nhận CV

## 1. Giới thiệu công nghệ và các bước xây dựng

Biểu đồ lớp chi tiết của chức năng **Tải và xác nhận CV (M2)** được thiết kế trên nền tảng kiến trúc Microservices hiện đại của hệ thống HireLens, bao gồm 3 tầng công nghệ chính:
- **Frontend:** Xây dựng bằng thư viện **React 19**, ngôn ngữ **TypeScript**, công cụ đóng gói **Vite**, chạy tại cổng `5173`.
- **Backend:** Xây dựng bằng framework **Spring Boot 4.1**, cơ chế truy xuất dữ liệu **Spring Data JPA**, quản lý dịch vụ tuyển dụng `recruitment-service` tại cổng `8082` và cơ sở dữ liệu riêng `hirelens_recruitment`.
- **Dịch vụ AI:** Xây dựng bằng framework **FastAPI** (Python), dịch vụ `cv-extraction-ai` chạy tại cổng `8001`, tích hợp mô hình ngôn ngữ lớn Qwen 2.5 (GGUF) thông qua thư viện `llama-cpp-python`.
- **Cổng giao tiếp:** Mọi yêu cầu từ giao diện Client được định tuyến tập trung qua **API Gateway** (Nginx) tại cổng `8080`.

Biểu đồ lớp chi tiết được xây dựng thông qua 4 bước chuẩn hóa theo mẫu báo cáo PTIT:

- **Bước 1 — Xác định thành phần giao diện (Tầng View):**
  Từ trang giao diện thực tế `CandidateCvPage.tsx`, phân tích toàn bộ các thành phần hiển thị, bao gồm các thuộc tính điều khiển tường minh (`txtFileName`, `txtFieldLines`, `btnUpload`, `btnUploadAnother`, `btnConfirm`, `btnUpdateProfile`, `btnViewMatching`) và các thuộc tính ẩn lưu giữ trạng thái component (`step`, `fileName`, `fields`, `values`, `busy`, `loaded`, `toast`). Xác định các phương thức xử lý sự kiện tương ứng (`applyForm`, `onUpload`, `onConfirm`, `setField`).

- **Bước 2 — Xác định các lớp phụ trợ giao tiếp (Tầng Client, Controller và Dịch vụ AI):**
  - Phía Client: Module `frontend/src/api/client.ts` chứa lớp `ApiClient` (hàm `api<T>()`, `getToken()`, `setToken()`) và nhóm hàm `cvsApi` đóng vai trò là `HTTPClient.fetch()`.
  - Phía Backend: Lớp `CvController` tại `backend/recruitment-service` đảm nhiệm vai trò của `RestController`, tiếp nhận các yêu cầu HTTP REST (`GET /api/cvs`, `POST /api/cvs`, `PUT /api/cvs`).
  - Giao tiếp liên dịch vụ và AI: Lớp `AiJsonClient` gọi sang dịch vụ `cv-extraction-ai` qua `HTTP POST /api/v1/extract-cv`; lớp `IdentityClient` gọi sang `identity-service` qua `HTTP PATCH /internal/users/{id}`; router FastAPI `routes` và bộ sinh LLM `generator` xử lý phân tích và bóc tách nội dung CV.

- **Bước 3 — Xác định tầng thao tác CSDL (Tầng Service/Repository):**
  Thay thế mô hình `DAO` truyền thống trong tài liệu mẫu bằng tầng `CvService` kết hợp với các Spring Data JPA Repositories (`CvDataRepository`, `CandidateProfileRepository`). Bổ sung các lớp hỗ trợ nghiệp vụ trích xuất gồm `CvExtractionModule` (điều phối kiểm tra text và gọi AI), `PdfTextExtractor` (trích xuất văn bản từ file PDF thuần), `CvProfileMapper` (chuyển đổi cấu trúc JSON từ AI thành các trường phẳng), và `SettingService` (quản lý danh sách cấu hình trường CV hợp lệ `CV_FIELD`). Xác định chi tiết chữ ký, tham số đầu vào (Input) và kết quả trả về (Output) cho từng phương thức.

- **Bước 4 — Tích hợp tầng thực thể (Tầng Entity):**
  Kế thừa trực tiếp các thực thể tham gia chức năng M2 từ biểu đồ thiết kế thực thể E1: `CandidateProfile` (hồ sơ ứng viên), `CvData` (chi tiết trường dữ liệu CV theo mô hình EAV) và `User` (thông tin người dùng từ `identity-service`). Thiết lập quan hệ Aggregation (toàn thể - bộ phận) giữa `CandidateProfile` và `CvData`, cùng quan hệ Association logic liên dịch vụ giữa `CandidateProfile` và `User`.

Ta được biểu đồ lớp chi tiết chức năng Tải và xác nhận CV (CLS-M2):

---

## 2. Chi tiết các tầng trong biểu đồ

### a. Tầng giao diện (Package `View`)

Giao diện chức năng tải và xác nhận CV được hiện thực tập trung tại trang `CandidateCvPage.tsx` (`source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:94`). Trang vận hành theo quy trình 3 bước khép kín (1: Tải lên -> 2: Kiểm tra & Chỉnh sửa -> 3: Xem hồ sơ đã xác nhận).

- **Thuộc tính tường minh (Explicit UI Controls):**
  - `txtFileName: input` — Hiển thị tên tệp tin PDF đã chọn hoặc "Chưa chọn file" (`CandidateCvPage.tsx:247`).
  - `txtFieldLines: input` — Ô nhập liệu (hoặc trường đa dòng textarea) cho từng mục hồ sơ (Họ tên, Email, Điện thoại, Tóm tắt, Học vấn, Kinh nghiệm, Kỹ năng, Chứng chỉ...) thông qua component `FieldLines` (`CandidateCvPage.tsx:271`).
  - `btnUpload: Button` — Vùng chọn và tải tệp tin PDF lên hệ thống thông qua callback của `UploadZone` (`CandidateCvPage.tsx:246`).
  - `btnUploadAnother: Button` — Nút bấm "Tải file khác" giúp ứng viên làm mới trạng thái và quay lại bước 1 (`CandidateCvPage.tsx:249`).
  - `btnConfirm: Button` — Nút bấm "Xác nhận hồ sơ" ở bước 2 gửi dữ liệu đã kiểm tra lên backend (`CandidateCvPage.tsx:281`).
  - `btnUpdateProfile: Button` — Nút bấm "Cập nhật hồ sơ" ở bước 3 cho phép chuyển về bước 2 để chỉnh sửa lại thông tin (`CandidateCvPage.tsx:214`).
  - `btnViewMatching: link` — Nút bấm liên kết "Xem việc phù hợp" điều hướng ứng viên sang màn hình đối sánh việc làm của chức năng M3 (`CandidateCvPage.tsx:217`).

- **Thuộc tính ẩn (Hidden States & Contexts):**
  - `step: number` — Chỉ số bước hiện tại của quy trình (1: Tải lên, 2: Kiểm tra, 3: Xem hồ sơ) (`CandidateCvPage.tsx:96`).
  - `fileName: string` — Chuỗi lưu trữ tên file PDF đang xử lý (`CandidateCvPage.tsx:97`).
  - `fields: string[]` — Mảng danh sách các tên trường hồ sơ lấy từ phản hồi backend (`CandidateCvPage.tsx:98`).
  - `values: Record<string, string[]>` — Cấu trúc từ điển lưu trữ mảng các dòng dữ liệu của từng trường (`CandidateCvPage.tsx:99`).
  - `busy: boolean` — Cờ trạng thái đang tải hoặc gửi dữ liệu, dùng để vô hiệu hóa nút bấm và chống gửi lặp (`CandidateCvPage.tsx:100`).
  - `loaded: boolean` — Cờ xác nhận đã tải xong dữ liệu hồ sơ ban đầu từ backend (`CandidateCvPage.tsx:101`).
  - `toast: (msg: string) => void` — Hàm hiển thị thông báo phản hồi nhận từ `ToastContext` qua hook `useToast()` (`CandidateCvPage.tsx:95`).

- **Gọi backend và luồng xử lý:**
  - Khi mở trang: `useEffect` gọi `cvsApi.mine()` (GET `/api/cvs`) để nạp thông tin hồ sơ đã lưu trước đó. Nếu đã có hồ sơ phân tích (`analyzed = true`), hàm `applyForm` tự động chuyển thẳng sang Bước 3.
  - Khi tải tệp: Kiểm tra phần mở rộng `.pdf`. Nếu hợp lệ, gọi `cvsApi.upload(file)` (POST `/api/cvs`) đóng gói `FormData`. Nhận dữ liệu `CvFormDto`, gọi `applyForm(form, 2)` và hiển thị toast thông báo.
  - Khi xác nhận: Gọi `cvsApi.confirm(fields)` (PUT `/api/cvs`) gửi mảng các trường đã làm sạch dòng trống qua `cleanLines`. Thành công thì chuyển sang Bước 3 `applyForm(form, 3)` và hiển thị toast xác nhận.

- **Điều hướng:**
  - Bấm `btnUpdateProfile`: Điều hướng nội bộ trên cùng trang, chuyển `step = 2`.
  - Bấm `btnViewMatching`: Điều hướng sang đường dẫn `/candidate/matching` thuộc chức năng M3 (Đối sánh việc làm).

---

### b. Tầng thao tác CSDL (Package `Service/Repository`)

Trong cấu trúc của hệ thống HireLens, tầng này thay thế cho mô hình `DAO` của mẫu báo cáo truyền thống bằng cách kết hợp giữa các `Service` nghiệp vụ và các Spring Data JPA `Repository`:

- **Lớp `CvService` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:32`):**
  - `mine()`:
    - *Input:* Không có tham số tường minh (đọc thông tin người dùng hiện tại từ Spring Security Context).
    - *Output:* `CvDtos.CvFormResponse` chứa thông tin tệp, trạng thái phân tích và các trường hồ sơ hiện tại.
  - `upload(file: MultipartFile)`:
    - *Input:* `file: MultipartFile` (tệp tin CV PDF tải lên).
    - *Output:* `CvDtos.CvFormResponse` chứa danh sách trường đã được trích xuất tự động qua AI.
  - `confirm(request: CvDtos.ConfirmCvRequest)`:
    - *Input:* `request: CvDtos.ConfirmCvRequest` (chứa danh sách `fields: List<FieldValue>` được ứng viên xác nhận).
    - *Output:* `CvDtos.CvFormResponse` chứa dữ liệu hồ sơ sau khi cập nhật CSDL và đồng bộ.
  - `syncProfile(candidate: CandidateProfile, field: String, lines: List<String>)`:
    - *Input:* `candidate: CandidateProfile`, `field: String`, `lines: List<String>`.
    - *Output:* `void` (đồng bộ họ tên/số điện thoại sang `identity-service` và tóm tắt vào `CandidateProfile`).
  - `replaceLines(candidateId: Integer, field: String, lines: List<String>)`:
    - *Input:* `candidateId: Integer`, `field: String`, `lines: List<String>`.
    - *Output:* `void` (xóa các dòng cũ của field và lưu danh sách dòng mới vào bảng `cv_data`).
  - `requireCandidate()`:
    - *Input:* Không có tham số.
    - *Output:* `CandidateProfile` tương ứng với tài khoản ứng viên đang đăng nhập.

- **Lớp `CvExtractionModule` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:12`):**
  - `extract(pdf: byte[])`:
    - *Input:* `pdf: byte[]` (dữ liệu nhị phân của tệp PDF).
    - *Output:* `JsonNode` (cấu trúc JSON trích xuất nhận từ dịch vụ AI).

- **Lớp `PdfTextExtractor` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/extraction/pdf/PdfTextExtractor.java:24`):**
  - `extract(pdfBytes: byte[])`:
    - *Input:* `pdfBytes: byte[]`.
    - *Output:* `ExtractionResult` (kết quả trích xuất gồm nội dung văn bản text và số lượng trang PDF, chặn các file vượt quá 10 trang hoặc text dưới 50 ký tự).

- **Lớp `CvProfileMapper` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvProfileMapper.java:6`):**
  - `fields(profile: JsonNode)`:
    - *Input:* `profile: JsonNode` (cây dữ liệu JSON thô từ AI).
    - *Output:* `Map<String, List<String>>` (bản đồ ánh xạ tên trường tiếng Việt sang danh sách các dòng thông tin tương ứng).

- **Lớp `SettingService` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/SettingService.java:15`):**
  - `cvFields()`:
    - *Input:* Không có tham số.
    - *Output:* `List<String>` (danh sách tên các trường hồ sơ hợp lệ lấy từ cấu hình hệ thống `CV_FIELD`).

- **Interface `CvDataRepository` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CvDataRepository.java:8`):**
  - Kế thừa `JpaRepository<CvData, Integer>`, đóng vai trò Data Access Object cho bảng `cv_data`.
  - `findByCandidateIdAndFieldOrderByIdAsc(candidateId: Integer, field: String)`:
    - *Input:* `candidateId: Integer`, `field: String`.
    - *Output:* `List<CvData>` (danh sách các dòng dữ liệu theo đúng thứ tự lưu trữ).

- **Interface `CandidateProfileRepository` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CandidateProfileRepository.java:8`):**
  - Kế thừa `JpaRepository<CandidateProfile, Integer>`, đóng vai trò Data Access Object cho bảng `candidate_profiles`.
  - `findByUserId(userId: Integer)`:
    - *Input:* `userId: Integer`.
    - *Output:* `Optional<CandidateProfile>` (tìm hồ sơ ứng viên theo mã định danh người dùng).

---

### c. Tầng thực thể (Package `Entity`)

Bao gồm các lớp thực thể trực tiếp tham gia lưu trữ và biểu diễn dữ liệu của chức năng M2, giữ nguyên định nghĩa và kiểu dữ liệu từ biểu đồ thiết kế thực thể E1:

1. **`CandidateProfile` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CandidateProfile.java:19`):**
   - Thuộc tính: `-id: Integer`, `-dateOfBirth: Date`, `-address: String`, `-headline: String`, `-summary: String`, `-yearsOfExperience: Decimal`, `-educationLevel: String`, `-userId: Integer`, `-listCvData: List<CvData>`.
   - Vai trò: Lưu trữ thông tin hồ sơ cơ bản của ứng viên trong CSDL `hirelens_recruitment`.

2. **`CvData` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CvData.java:13`):**
   - Thuộc tính: `-id: Integer`, `-candidateId: Integer`, `-field: String`, `-value: String`, `-candidateProfile: CandidateProfile`.
   - Vai trò: Lưu trữ từng dòng dữ liệu chi tiết của CV theo mô hình EAV (Entity - Attribute - Value) linh hoạt, hỗ trợ các mục có nhiều dòng dữ liệu như kỹ năng, học vấn, kinh nghiệm.

3. **`User` (`source/recruit_system/backend/identity-service/src/main/java/recruit/demo/entity/User.java:17`):**
   - Thuộc tính: `-id: Integer`, `-fullName: String`, `-email: String`, `-passwordHash: String`, `-phone: String`, `-role: Role`, `-roleChosen: Boolean`, `-status: UserStatus`.
   - Vai trò: Thực thể người dùng thuộc CSDL `hirelens_identity`. Quan hệ giữa `CandidateProfile` và `User` là tham chiếu logic (`userId`) giữa các microservices độc lập, không thiết lập khóa ngoại cứng (foreign key) ở mức CSDL.

- **Quan hệ giữa các thực thể:**
  - `CandidateProfile` có quan hệ **Aggregation** (`1` toàn thể đến `n` bộ phận) với `CvData`.
  - `CandidateProfile` có quan hệ **Association** logic (`1` đến `1`) với `User`.

---

### d. Các lớp phụ trợ (Package `Client`, `Controller` và `AI`)

1. **Tầng Client (`ApiClient`, `cvsApi`):**
   - Lớp `ApiClient` (`source/recruit_system/frontend/src/api/client.ts:32`): Đóng vai trò là `HTTPClient.fetch()` tập trung của toàn bộ Frontend. Quản lý cấu hình `API_BASE` (`/api`), tự động bổ sung JWT token (`Authorization: Bearer ...`) từ `localStorage`, thiết lập `Content-Type: application/json` (hoặc giữ nguyên khi truyền `FormData`) và bọc lỗi HTTP thành `ApiError`.
   - Lớp `cvsApi` (`source/recruit_system/frontend/src/api/client.ts:99`): Cung cấp 3 phương thức gọi API chuyên biệt cho chức năng CV:
     - `mine()`: Gửi `GET /api/cvs` -> trả về `Promise<CvFormDto>`.
     - `upload(file: File)`: Đóng gói tệp vào `FormData`, gửi `POST /api/cvs` -> trả về `Promise<CvFormDto>`.
     - `confirm(fields: CvFieldDto[])`: Gửi `PUT /api/cvs` kèm danh sách trường -> trả về `Promise<CvFormDto>`.

2. **Tầng Controller (`CvController`):**
   - Lớp `CvController` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:13`): Đóng vai trò `RestController` của Spring Boot, định tuyến các yêu cầu từ Gateway `/api/cvs` tới `CvService`.

3. **Client giao tiếp liên dịch vụ:**
   - Lớp `AiJsonClient` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:11`): HTTP Client chuyên dụng kết nối tới FastAPI, gửi body JSON và nhận kết quả, đồng thời chuyển đổi các mã lỗi HTTP từ AI (chẳng hạn đổi 503 từ AI thành 502 Bad Gateway phía Gateway).
   - Lớp `IdentityClient` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/IdentityClient.java:6`): HTTP Client liên dịch vụ, gọi sang `identity-service` qua `ServiceHttpClient` để cập nhật họ tên và số điện thoại của ứng viên sau khi xác nhận CV (`update(id, name, phone)`).

4. **Dịch vụ AI trích xuất CV (Package `AI`):**
   - Lớp `routes` (`source/recruit_system/services/cv-extraction-ai/app/api/routes.py:20`): Định nghĩa router tiếp nhận `POST /api/v1/extract-cv`, kiểm tra tính hợp lệ của văn bản `cv_text` và điều phối quy trình trích xuất.
   - Lớp `generator` (`source/recruit_system/services/cv-extraction-ai/app/services/generator.py:29`): Bộ sinh suy luận LLM, điều khiển gọi model Qwen 2.5 qua cơ chế phòng vệ chống lặp ký tự (`LoopGuard`) và tiếp tục sinh khi bị cắt ngắn độ dài (`plan_continuation`).

---

## 3. Phân tích các Design Pattern có trong mã nguồn

### 3.1. Repository Pattern (Spring Data JPA)
- **Minh chứng trong code:** `CvDataRepository` và `CandidateProfileRepository` kế thừa `JpaRepository` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CvDataRepository.java:8`, `CandidateProfileRepository.java:8`).
- **Ưu điểm cụ thể cho HireLens:** Tách biệt hoàn toàn tầng logic nghiệp vụ (`CvService`) khỏi chi tiết câu lệnh SQL/JPA; tự động quản lý các thao tác CRUD và truy vấn theo tên hàm (`findByCandidateIdAndFieldOrderByIdAsc`), giúp mã nguồn ngắn gọn, an toàn giao dịch và dễ bảo trì khi thay đổi cấu trúc bảng.

### 3.2. DTO (Data Transfer Object) Pattern
- **Minh chứng trong code:** Các cấu trúc dữ liệu `CvDtos.CvFormResponse`, `CvDtos.ConfirmCvRequest`, `CvDtos.FieldValue` phía Java (`backend/recruitment-service/.../dto/CvDtos.java:10-21`) và các interface TypeScript `CvFormDto`, `CvFieldDto` phía Frontend (`frontend/src/api/client.ts:220-230`).
- **Ưu điểm cụ thể cho HireLens:** Che giấu cấu trúc lưu trữ CSDL nội bộ (mô hình EAV nhiều dòng `CvData`); chỉ truyền tải các trường dữ liệu cần thiết qua mạng; đảm bảo tính toàn vẹn kiểu dữ liệu tĩnh giữa Frontend và Backend.

### 3.3. Dependency Injection & Inversion of Control (DI / IoC)
- **Minh chứng trong code:**
  - Backend: `CvController` và `CvService` sử dụng cơ chế tiêm phụ thuộc qua Constructor nhờ annotation `@RequiredArgsConstructor` của Lombok (`CvController.java:12`, `CvService.java:31`).
  - Frontend: `CandidateCvPage` tiêm hàm xử lý sự kiện `onUpload` vào `UploadZone` thông qua props callback (`CandidateCvPage.tsx:246`).
- **Ưu điểm cụ thể cho HireLens:** Loại bỏ sự gắn kết chặt chẽ (tight coupling) giữa các lớp; giúp việc viết kiểm thử đơn vị (Unit Test) trở nên dễ dàng bằng cách mock các repository hoặc client liên dịch vụ.

### 3.4. API Gateway / Facade & Adapter Pattern
- **Minh chứng trong code:**
  - Nginx đóng vai trò API Gateway tập trung tại cổng `8080` (`infra/gateway/nginx.conf`).
  - Phía Frontend, hàm `ApiClient.api<T>()` đóng vai trò Facade duy nhất đại diện cho toàn bộ các lời gọi HTTP (`frontend/src/api/client.ts:32`).
  - Phía Backend, `AiJsonClient` và `IdentityClient` đóng vai trò Adapter che giấu giao thức HTTP thuần, cung cấp giao diện gọi hàm rõ ràng (`post()`, `update()`).
- **Ưu điểm cụ thể cho HireLens:** Cho phép thay đổi cổng, cơ chế xác thực hoặc địa chỉ mạng của từng microservice mà không làm ảnh hưởng đến mã nguồn của các thành phần gọi; tập trung hóa xử lý lỗi mạng và đính kèm JWT token.

### 3.5. Mapper Pattern
- **Minh chứng trong code:** Lớp `CvProfileMapper` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvProfileMapper.java:6`).
- **Ưu điểm cụ thể cho HireLens:** Chuyển đổi linh hoạt cấu trúc cây JSON lồng nhau từ mô hình AI thành cấu trúc bảng phẳng `Map<String, List<String>>` phù hợp với cấu hình các trường nghiệp vụ (`SettingService.cvFields()`).

---

## 4. Bảng truy vết phần tử đến mã nguồn

| STT | Phần tử trong biểu đồ | Package | Vai trò thiết kế | Đường dẫn truy vết nguồn |
|:---:|---|---|---|---|
| 1 | `CandidateCvPage` | `View` | Giao diện chính (Boundary) | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:94` |
| 2 | `ApiClient` | `Client` | HTTP Client Gateway (Client) | `source/recruit_system/frontend/src/api/client.ts:32` |
| 3 | `cvsApi` | `Client` | Endpoint Client CV (Client) | `source/recruit_system/frontend/src/api/client.ts:99` |
| 4 | `CvController` | `Controller` | Điều khiển REST (Control) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:13` |
| 5 | `CvService` | `Service/Repository` | Xử lý nghiệp vụ chính (Service) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:32` |
| 6 | `CvExtractionModule` | `Service/Repository` | Điều phối gọi AI (Service) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:12` |
| 7 | `PdfTextExtractor` | `Service/Repository` | Trích xuất text PDF (Control) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/extraction/pdf/PdfTextExtractor.java:24` |
| 8 | `CvProfileMapper` | `Service/Repository` | Ánh xạ JSON sang trường (Control) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvProfileMapper.java:6` |
| 9 | `SettingService` | `Service/Repository` | Quản lý cấu hình trường (Service) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/SettingService.java:15` |
| 10 | `AiJsonClient` | `Service/Repository` | HTTP Client gọi AI (Client) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:11` |
| 11 | `IdentityClient` | `Service/Repository` | HTTP Client gọi Identity (Client) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/IdentityClient.java:6` |
| 12 | `CvDataRepository` | `Service/Repository` | DAO bảng `cv_data` (Repository) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CvDataRepository.java:8` |
| 13 | `CandidateProfileRepository` | `Service/Repository` | DAO bảng `candidate_profiles` (Repository) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CandidateProfileRepository.java:8` |
| 14 | `routes` | `AI` | Router tiếp nhận FastAPI (Boundary) | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:20` |
| 15 | `generator` | `AI` | Bộ sinh suy luận LLM (Control) | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:29` |
| 16 | `CandidateProfile` | `Entity` | Thực thể hồ sơ ứng viên (Entity) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CandidateProfile.java:19` |
| 17 | `CvData` | `Entity` | Thực thể dữ liệu CV EAV (Entity) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CvData.java:13` |
| 18 | `User` | `Entity` | Thực thể người dùng logic (Entity) | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/entity/User.java:17` |

---

## 5. Các câu hỏi mở và lưu ý kiến trúc (Open Questions)

- **[Cần xác nhận]** Đích điều hướng cụ thể khi phiên làm việc hết hạn hoặc người dùng không có vai trò `CANDIDATE` và API trả về mã lỗi 401/403: Hiện tại phía Frontend route guard `RequireAuth` (`App.tsx:29`) tự động kiểm tra trạng thái và chuyển hướng về `/login` hoặc `/choose-role`, trong khi `CandidateCvPage` chỉ bắt lỗi và hiện toast nếu request API thất bại.
- **[Cần xác nhận]** Cơ chế xử lý tệp PDF dạng ảnh quét (scan/ảnh chụp) không có text layer: Hiện tại `PdfTextExtractor` kiểm tra độ dài chuỗi ký tự trích xuất nếu dưới 50 ký tự sẽ ném lỗi HTTP 422 Unprocessable Entity ("PDF không có nội dung chữ hoặc chất lượng scan quá thấp"), hệ thống chưa tích hợp engine OCR (như Tesseract).
