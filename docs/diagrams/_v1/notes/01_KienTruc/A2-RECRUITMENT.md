# A2-RECRUITMENT — Kiến trúc chiều ngang MVC

## Ánh xạ và phạm vi
- View là nhóm logic DTO nhận/trả, không hàm ý backend render HTML; Controller gồm controller của service; Model gồm service, repository, entity và client.
- Biểu đồ chọn đại diện các luồng CV, đối sánh, việc làm và ứng tuyển; không thể hiện mọi lớp hoặc mọi kết nối. Mỗi nhóm chứa tối đa bốn lớp/interface; tổng cộng 24 phần tử và 7 quan hệ.
- Phụ thuộc giữa các package là ví dụ có nguồn, không suy ra mọi lớp trong package đều phụ thuộc. Các nhóm common và các lớp ngoài phạm vi đại diện đã được lược bỏ.
- Lược bỏ: DashboardDtos, DashboardController, InternalRecruitmentController, DashboardService, ProfileProvisioningService, SettingService, CvExtractionModule, CvProfileMapper, CvMatchingModule, CandidateProfileRepository, CompanyRepository, JobRepository, JobSkillRepository, MatchingResultRepository, RecruiterProfileRepository, SettingRepository, SkillRepository, ApplicationStatus, CandidateProfile, Company, Job, JobSkill, JobStatus, MatchingResult, ParsingStatus, RecruiterProfile, Setting, Skill, IdentityClient, ServiceDtos, ErrorResponse, HealthController, UserPrincipal, SecurityUtils, PrincipalLookup, RemotePrincipalLookup, JwtService, JwtAuthenticationFilter, InternalAccessFilter, AuthenticatedRequestHook, ApiException, GlobalExceptionHandler, SecurityConfig, FilterRegistrationConfig, AppProperties, ProfileProvisioningFilter.

## Bảng truy vết

| Phần tử | Nguồn |
|---|---|
| `View` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/dto/CvDtos.java:1` |
| `Controller` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:1` |
| `Model` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:1` |
| `service` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:1` |
| `repository` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CvDataRepository.java:1` |
| `entity` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CvData.java:1` |
| `client` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:1` |
| `ApplicationDtos` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/dto/ApplicationDtos.java:7` |
| `CvDtos` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/dto/CvDtos.java:5` |
| `JobDtos` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/dto/JobDtos.java:10` |
| `MatchingDtos` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/dto/MatchingDtos.java:7` |
| `ApplicationsController` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/ApplicationsController.java:13` |
| `CvController` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:13` |
| `JobsController` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/JobsController.java:14` |
| `MatchingController` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/MatchingController.java:13` |
| `ApplicationService` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:18` |
| `CvService` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:32` |
| `JobService` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/JobService.java:25` |
| `MatchingService` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:20` |
| `CvDataRepository` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CvDataRepository.java:8` |
| `JobApplicationRepository` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/JobApplicationRepository.java:11` |
| `CvData` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CvData.java:13` |
| `JobApplication` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/JobApplication.java:17` |
| `AiJsonClient` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:11` |

## Truy vết quan hệ

| Từ → đến | Nguồn |
|---|---|
| `Controller` → `View` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:7` |
| `Controller` → `Model` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:8` |
| `Model` → `View` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:9` |
| `View` → `Model` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/dto/JobDtos.java:4` |
| `service` → `repository` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:15` |
| `repository` → `entity` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CvDataRepository.java:4` |
| `service` → `client` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:5` |

## Mâu thuẫn và giới hạn
- DIAGRAM_RULES.md §1.2 quy định View → Controller → Model, nhưng import thực tế chứng minh Controller → View và Controller → Model; ưu tiên chiều phụ thuộc theo source. View và Model còn phụ thuộc hai chiều qua DTO/enum; không vẽ View → Controller khi không có chứng cứ.
- CLAUDE.md ghi báo cáo v6 mô tả monolith trong khi source được chọn là microservices; PDF không có trên đĩa nên không thể trực tiếp đối chiếu báo cáo. `source/recruit_system/docs/Module3_Interview_Flow.md:33` mô tả Interview gọi Recruitment, phù hợp kiến trúc service; tài liệu không đặc tả MVC để đối chiếu chi tiết.
- Không chạy ứng dụng hoặc build; biểu đồ không bao quát toàn bộ lớp của service.

## Open questions
- Không còn câu hỏi mở về kích thước: spec đã được rút gọn theo yêu cầu.
