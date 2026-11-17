# Biểu đồ use case chi tiết - Ôn tập và chấm phỏng vấn

## Bước 1: Sao chép actor và use case chính
Actor Ứng viên tương tác với chức năng Ôn tập và chấm phỏng vấn thông qua route `/candidate/interview`, được bảo vệ dành cho vai trò `CANDIDATE`.

## Bước 2: Xác định các giao diện chính
Source có một trang giao diện chính là `CandidateInterviewPage.tsx`. Các thao tác bắt đầu phiên và gửi câu trả lời được thực hiện ngay trên trang này; kết quả đánh giá và tổng kết cũng được hiển thị trong cùng trang, không có route hoặc hộp thoại riêng. Vì vậy, use case chi tiết giao diện là “Sử dụng trang Luyện phỏng vấn”.

## Bước 3: Xác định quan hệ include và extend
Use case “Sử dụng trang Luyện phỏng vấn”, “Bắt đầu phiên 6 câu” và “Gửi câu trả lời và nhận đánh giá” là các bước cốt lõi của chức năng, được biểu diễn bằng `<<include>>`. Mở phiên trước đây, chuyển sang câu hỏi tiếp theo và xem tổng kết chỉ xảy ra khi ứng viên lựa chọn hoặc khi phiên đạt trạng thái hoàn thành; chúng được biểu diễn bằng `<<extend>>` tại các extension point tương ứng.

## Bước 4: Mô tả use case chi tiết
- **Ôn tập và chấm phỏng vấn:** cho phép Ứng viên bắt đầu phiên luyện tập, trả lời câu hỏi và xem đánh giá.
- **Sử dụng trang Luyện phỏng vấn:** cho phép Ứng viên thao tác trên giao diện luyện phỏng vấn.
- **Bắt đầu phiên 6 câu:** cho phép Ứng viên tạo phiên luyện tập mới gồm sáu câu hỏi.
- **Gửi câu trả lời và nhận đánh giá:** cho phép Ứng viên gửi câu trả lời không rỗng để hệ thống chấm.
- **Mở phiên ôn tập trước đây:** cho phép Ứng viên mở một phiên trong danh sách phiên gần đây.
- **Chuyển sang câu hỏi tiếp theo:** cho phép Ứng viên chuyển tiếp sau khi câu hiện tại đã được đánh giá.
- **Xem tổng kết phiên:** cho phép Ứng viên xem tiến độ, điểm trung bình và kết quả từng câu.

Ta được biểu đồ use case chi tiết chức năng Ôn tập và chấm phỏng vấn:

## Bảng truy vết
| Phần tử | Nguồn |
|---|---|
| Actor Ứng viên, route bảo vệ | `source/recruit_system/frontend/src/App.tsx:87` |
| Trang Luyện phỏng vấn | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:61` |
| Bắt đầu phiên | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:31` |
| Gửi câu trả lời | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:40` |
| Mở phiên cũ | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:23` |
| Chuyển câu | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:50` |
| Tổng kết | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:82` |

## Open questions
- Trang hiện tại gộp màn hình câu hỏi, kết quả và tổng kết trong một giao diện; cần xác nhận cách phân rã các use case chi tiết theo quy ước báo cáo.
