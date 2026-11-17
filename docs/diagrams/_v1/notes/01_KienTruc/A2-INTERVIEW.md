# A2-INTERVIEW — Kiến trúc chiều ngang MVC interview-service

Biểu đồ ánh xạ cấu trúc Spring service theo MVC: `View` chứa DTO giao tiếp; `Controller` nhận request và gọi nghiệp vụ; `Model` chứa service, client, repository và entity. `common` được tách thành package dùng chung vì luồng nghiệp vụ trực tiếp dùng lớp xác thực, exception và HTTP client từ `backend/common`.

## Bảng truy vết

| Nhóm | Phần tử tiêu biểu | Nguồn |
|---|---|---|
| View | InterviewDtos.QuestionResponse, CreateSessionRequest, SessionResponse, SubmitResponseRequest | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/dto/InterviewDtos.java:16-57` |
| Controller | InterviewController, InternalInterviewController | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/controller/InterviewController.java:14`; `.../InternalInterviewController.java:8` |
| Model | InterviewService, AiScoringClient, InterviewSessionRepository, InterviewSession | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:23`; `.../AiScoringClient.java:26`; `.../repository/InterviewSessionRepository.java:8`; `.../entity/InterviewSession.java` |
| common | SecurityUtils, UserPrincipal, ApiException, ServiceHttpClient | `source/recruit_system/backend/common/src/main/java/recruit/demo/security/SecurityUtils.java`; `.../security/UserPrincipal.java`; `.../exception/ApiException.java`; `.../client/ServiceHttpClient.java` |

## Hướng phụ thuộc

- DTO được tham chiếu trong chữ ký các endpoint của `InterviewController` (ví dụ `listQuestions`, `createSession`, `submitResponse`), thể hiện View → Controller.
- `InterviewController` inject và gọi `InterviewService`; `InternalInterviewController` phụ thuộc `InterviewQuestionRepository`, thể hiện Controller → Model.
- `InterviewService` dùng `SecurityUtils`, `UserPrincipal`, `ApiException`, `ServiceHttpClient` từ common; `AiScoringClient` cũng dùng `ApiException`, thể hiện Model → common.

Không phát hiện mâu thuẫn giữa tài liệu đã đọc và source trong phạm vi biểu đồ. Tài liệu luồng/schema không định nghĩa khác cấu trúc package MVC này.
