# Trích lớp thực thể liên quan đến các chức năng M1–M4

## Bước 1. Mô tả hệ thống

HireLens cho phép người dùng đăng ký, đăng nhập và chọn vai trò ứng viên hoặc nhà tuyển dụng; hệ thống tạo hồ sơ tương ứng và gắn nhà tuyển dụng với công ty. Ứng viên tải CV, kiểm tra và xác nhận thông tin hồ sơ; dữ liệu được lưu theo các trường CV. Ứng viên xem việc làm và kỹ năng yêu cầu, nhận kết quả đối sánh hồ sơ với từng việc và nộp đơn ứng tuyển. Từ việc làm, ứng viên có thể tạo phiên ôn tập phỏng vấn gồm các câu hỏi, gửi câu trả lời và nhận kết quả chấm theo tiêu chí đánh giá. Các dữ liệu thuộc ba dịch vụ định danh, tuyển dụng và phỏng vấn; một số tham chiếu giữa dịch vụ chỉ được biểu diễn bằng định danh logic.

## Bước 2. Trích danh từ thành lớp và thuộc tính

Các danh từ có thông tin riêng hoặc tham gia trực tiếp vào nghiệp vụ được chọn thành lớp thực thể sau; trong ngoặc là các thuộc tính nghiệp vụ tiêu biểu, giữ nguyên tên trong mã nguồn:

- Người dùng → `User` (`fullName`, `email`, `passwordHash`, `phone`, `role`, `roleChosen`, `status`).
- Hồ sơ ứng viên → `CandidateProfile` (`dateOfBirth`, `address`, `headline`, `summary`, `yearsOfExperience`, `educationLevel`).
- Hồ sơ nhà tuyển dụng → `RecruiterProfile` (`position`); công ty → `Company` (`name`, `description`, `website`, `address`).
- Trường dữ liệu CV → `CvData` (`field`, `value`); không đặt thêm lớp CV riêng vì source hiện không có entity tương ứng.
- Việc làm → `Job` (`title`, `description`, `requirements`, `responsibilities`, `employmentType`, `workLocation`, `salaryMin`, `salaryMax`, `status`, `deadline`).
- Kỹ năng → `Skill` (`name`, `category`); yêu cầu kỹ năng của việc làm → `JobSkill` (`required`, `minimumYears`).
- Đơn ứng tuyển → `JobApplication` (`status`, `coverLetter`, `appliedAt`); kết quả đối sánh → `MatchingResult` (`semanticScore`, `skillsScore`, `experienceScore`, `overallScore`, `matchedSkills`, `missingSkills`, `explanation`).
- Phiên phỏng vấn → `InterviewSession` (`jobTitle`, `title`, `status`, `startedAt`, `completedAt`); câu hỏi → `InterviewQuestion` (`title`, `skill`, `questionText`, `topic`, `difficulty`, `referenceAnswer`, `maxScore`).
- Câu hỏi trong phiên → `InterviewSessionQuestion` (`questionOrder`, `maxScore`, `timeLimitSeconds`); câu trả lời → `InterviewResponse` (`answerText`, `submittedAt`, `responseDurationSeconds`, `status`).
- Tiêu chí đánh giá → `EvaluationRubric` (`criterionName`, `criterionDescription`, `maxScore`, `weight`, `expectedKeywords`, `referenceAnswers`); kết quả đánh giá → `EvaluationResult` (`evaluationMethod`, `predictedScore`, `correctnessScore`, `completenessScore`, `feedback`, `strengths`, `missingPoints`, `criterionResults`); phiên bản mô hình → `ModelVersion` (`moduleName`, `modelName`, `version`, `active`).

## Bước 3. Đánh giá các danh từ còn lại

- Họ tên, email, mật khẩu băm, điện thoại, vai trò và trạng thái là thuộc tính của `User`, không tách thành lớp người dùng theo từng vai trò.
- Ngày sinh, địa chỉ, tóm tắt, số năm kinh nghiệm và trình độ học vấn là thuộc tính của `CandidateProfile`; các nội dung CV theo trường được lưu trong `CvData.field` và `CvData.value`.
- Mô tả, yêu cầu, trách nhiệm, địa điểm và khoảng lương là thuộc tính của `Job`; mức độ bắt buộc và số năm tối thiểu thuộc `JobSkill`.
- Điểm phù hợp, kỹ năng khớp, kỹ năng thiếu và giải thích thuộc `MatchingResult`; điểm, nhận xét và kết quả theo tiêu chí thuộc `EvaluationResult`.
- Nội dung câu hỏi, chủ đề, độ khó và đáp án tham chiếu thuộc `InterviewQuestion`; thứ tự câu thuộc `InterviewSessionQuestion`; nội dung trả lời thuộc `InterviewResponse`.
- “Hệ thống”, “giao diện”, “dịch vụ”, “thông báo”, “nút” và “danh sách” chỉ môi trường, cách trình bày hoặc khái niệm chung, không chọn làm lớp thực thể. Tệp PDF và JWT là dữ liệu phục vụ xử lý, không có entity tương ứng trong phạm vi này.
- Biểu đồ phân tích chỉ chọn thuộc tính nghiệp vụ tiêu biểu, không ghi kiểu, phương thức, khóa định danh hay lặp thuộc tính tham chiếu đối tượng; `cvId` không được đưa vào thực thể vì bảng đích CV cũ đã bị xóa.

## Bước 4. Xác định quan hệ giữa các lớp

Trong các câu sau, bội số ghi theo thứ tự hai lớp được nêu; `n` là không hoặc nhiều, `1` là không hoặc một.

1. `CandidateProfile` (1) – `User` (1): hồ sơ ứng viên tham chiếu một người dùng qua `userId`, còn một người dùng có thể chưa có hồ sơ ứng viên.
2. `RecruiterProfile` (n) – `User` (1): mỗi hồ sơ nhà tuyển dụng tham chiếu một người dùng, một người dùng có thể có nhiều hồ sơ gắn với các công ty.
3. `RecruiterProfile` (n) – `Company` (1): mỗi hồ sơ nhà tuyển dụng thuộc một công ty và công ty có thể có nhiều hồ sơ.
4. `CvData` (n) – `CandidateProfile` (1): mỗi trường CV lưu định danh một hồ sơ ứng viên và hồ sơ có thể có nhiều trường dữ liệu.
5. `Job` (n) – `Company` (1): mỗi việc làm thuộc một công ty, trong khi một công ty có thể đăng nhiều việc.
6. `Job` (n) – `User` (1): mỗi việc làm ghi định danh người đăng, một người dùng có thể đăng nhiều việc.
7. `JobSkill` (n) – `Job` (1): mỗi yêu cầu kỹ năng gắn với một việc, một việc có thể có nhiều yêu cầu.
8. `JobSkill` (n) – `Skill` (1): mỗi yêu cầu gắn với một kỹ năng, một kỹ năng có thể xuất hiện trong nhiều yêu cầu việc làm.
9. `JobApplication` (n) – `CandidateProfile` (1): mỗi đơn thuộc một hồ sơ ứng viên và một hồ sơ có thể có nhiều đơn.
10. `JobApplication` (n) – `Job` (1): mỗi đơn dành cho một việc và một việc có thể nhận nhiều đơn.
11. `MatchingResult` (n) – `CandidateProfile` (1): mỗi kết quả đối sánh gắn với một hồ sơ và một hồ sơ có thể có nhiều kết quả.
12. `MatchingResult` (n) – `Job` (1): mỗi kết quả đối sánh gắn với một việc và một việc có thể có nhiều kết quả.
13. `InterviewQuestion` (n) – `User` (1): câu hỏi có thể ghi người tạo và một người dùng có thể tạo nhiều câu hỏi.
14. `EvaluationRubric` (n) – `InterviewQuestion` (1): mỗi tiêu chí thuộc một câu hỏi và một câu hỏi có thể có nhiều tiêu chí.
15. `InterviewSession` (n) – `CandidateProfile` (1): phiên ghi định danh hồ sơ ứng viên và một hồ sơ có thể có nhiều phiên.
16. `InterviewSession` (n) – `User` (1), vai trò ứng viên: phiên ghi `candidateUserId` và một người dùng có thể tham gia nhiều phiên.
17. `InterviewSession` (n) – `User` (1), vai trò nhà tuyển dụng: phiên có thể ghi `recruiterUserId` và một người dùng có thể gắn với nhiều phiên.
18. `InterviewSession` (n) – `Job` (1): phiên có thể ghi việc làm làm ngữ cảnh và một việc có thể có nhiều phiên.
19. `InterviewSession` (n) – `JobApplication` (1): phiên có thể ghi đơn ứng tuyển liên quan và một đơn có thể được tham chiếu bởi nhiều phiên.
20. `InterviewSessionQuestion` (n) – `InterviewSession` (1): mỗi câu trong phiên thuộc một phiên và một phiên có thể chứa nhiều câu.
21. `InterviewSessionQuestion` (n) – `InterviewQuestion` (1): mỗi câu trong phiên tham chiếu một câu hỏi và câu hỏi có thể xuất hiện trong nhiều phiên.
22. `InterviewResponse` (1) – `InterviewSessionQuestion` (1): mỗi câu trả lời thuộc một câu trong phiên và ràng buộc duy nhất cho phép tối đa một câu trả lời cho câu đó.
23. `EvaluationResult` (1) – `InterviewResponse` (1): mỗi kết quả thuộc một câu trả lời và ràng buộc duy nhất cho phép tối đa một kết quả cho câu trả lời.
24. `EvaluationResult` (n) – `ModelVersion` (1): kết quả có thể tham chiếu phiên bản mô hình và một phiên bản có thể gắn với nhiều kết quả.

## Bước 5. Bổ sung và đánh giá quan hệ đối tượng

- Việc làm và kỹ năng có quan hệ nhiều–nhiều qua lớp thực thể trung gian `JobSkill`, vì mỗi bản ghi gắn một việc với một kỹ năng và mang mức độ bắt buộc, số năm tối thiểu.
- Hồ sơ ứng viên và việc làm có quan hệ nhiều–nhiều qua `JobApplication`, vì mỗi bản ghi ứng tuyển gắn một hồ sơ với một việc và có trạng thái riêng; `MatchingResult` là lớp kết quả riêng cũng gắn một hồ sơ với một việc, không đồng nhất với đơn ứng tuyển.
- Phiên phỏng vấn và câu hỏi có quan hệ nhiều–nhiều qua `InterviewSessionQuestion`, vì bản ghi trung gian lưu thứ tự, điểm tối đa và thời gian của câu trong từng phiên.
- Các lớp trung gian được thể hiện bằng lớp thông thường và hai association có bội số; không thêm một đường nhiều–nhiều trùng lặp. Việc renderer có hỗ trợ đường nét đứt association class cần xác nhận.
- Các quan hệ giữa ba service là tham chiếu logic bằng định danh, không khẳng định khóa ngoại xuyên CSDL hay trường đối tượng JPA. Riêng `CvData.candidateId` cũng là trường số, không phải quan hệ đối tượng JPA.
- Không bổ sung kế thừa giữa `User` và các hồ sơ hoặc giữa các trạng thái, vì entity trong source không khai báo các quan hệ kế thừa đó. Mẫu báo cáo v6 mô tả một backend và một CSDL; biểu đồ này theo source microservices hiện tại.

Nguồn truy vết từng lớp, thuộc tính và quan hệ được ghi trực tiếp trong `diagrams/specs/03_TrichThucThe/TT.json` dưới trường `src`. Bội số hồ sơ ứng viên theo người dùng dựa trên ràng buộc duy nhất `uq_candidate_profiles_user` (`source/recruit_system/backend/recruitment-service/src/main/resources/db/migration/V1__schema.sql:12`); các bội số giữa service chỉ mô tả ý nghĩa logic, không phải FK xuyên CSDL.

Ta được biểu đồ trích lớp thực thể liên quan đến các chức năng M1–M4:
