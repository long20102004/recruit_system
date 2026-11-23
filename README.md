# HireLens

Hệ thống tuyển dụng: quản lý CV, đối sánh CV–JD và luyện phỏng vấn. Backend hiện được tổ chức thành các microservice chạy độc lập qua API Gateway.

| Thư mục | Chức năng |
|---|---|
| `backend/identity-service/` | Tài khoản, đăng nhập, JWT |
| `backend/recruitment-service/` | CV, việc làm, ứng tuyển, điều phối extraction/matching |
| `backend/interview-service/` | Phiên phỏng vấn, rubric và kết quả chấm |
| `backend/common/` | Thư viện xác thực, DTO, HTTP; không chứa database dùng chung |
| `services/cv-extraction-ai/` | Service trích xuất CV từ nhánh `hocnv/DO-06` |
| `services/cv-matching-ai/` | Service matching từ nhánh `locnh/matchCV` |
| `AI/` | Service chấm câu trả lời phỏng vấn |
| `infra/gateway/` | Nginx gateway, cổng 8080 |
| `frontend/` | React, Vite, TypeScript |

## Khởi động

```bash
cp .env.microservices.example .env
docker compose up -d --build
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`. API Gateway: `http://localhost:8080/api`.

Để bật AI phỏng vấn và hai service AI về CV:

```bash
# Đặt file model-v4-q4_k_m.gguf vào models/cv-extraction/ trước khi bật extraction.
docker compose --profile ai --profile cv-ai up -d --build
```

Trọng số Qwen không nằm trong Git. Có thể cấu hình `CV_EXTRACTION_URL` tới AI service đang chạy trên máy khác/Colab. Matching có model embedding riêng và tải model ở lần chạy đầu. Upload CV và matching báo lỗi khi AI chưa sẵn sàng, không trả dữ liệu mẫu.

Tài khoản seed: `candidate@hirelens.local`, `recruiter@hirelens.local`, `admin@hirelens.local`; mật khẩu `demo1234`.

Xem [hướng dẫn backend](backend/README.md) để biết kiến trúc, cổng, API, kiểm thử và cách chuyển dữ liệu cũ. Database cũ `recruit_system` được giữ nguyên; không chạy migration mới trực tiếp lên database cũ.

Module 3 đã bổ sung ngân hàng câu hỏi theo JD/CV, chấm BERTScore + rubric, lịch sử và tổng kết phiên. Xem [toàn bộ luồng Module 3](docs/Module3_Interview_Flow.md).
