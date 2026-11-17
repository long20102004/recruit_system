# Biểu đồ trạng thái chức năng M4: Ôn tập và chấm phỏng vấn

**Bước 1.** Căn cứ kịch bản chuẩn, xác định các giao diện chính thật trong luồng gồm Chi tiết công việc, Luyện phỏng vấn, câu hỏi và ô trả lời, Kết quả đánh giá, Tổng kết phiên; các thông báo lỗi được biểu diễn thành trạng thái riêng. Các trạng thái câu hỏi, đánh giá và tổng kết là các vùng hiển thị trên cùng trang `CandidateInterviewPage.tsx`, không phải trang độc lập.

**Bước 2.** Xác định chuyển trạng thái theo thao tác ứng viên và kết quả xử lý: mở luyện tập từ chi tiết tin, bắt đầu/mở phiên, gửi câu trả lời, kiểm tra nội dung và chấm. Nhánh tạo phiên hoặc gửi câu trả lời thất bại hiển thị thông báo rồi quay về giao diện đang thao tác; nội dung rỗng hiển thị thông báo yêu cầu nhập câu trả lời rồi quay về ô nhập. Khi phiên hoàn thành, ứng viên có thể xem tổng kết.

Ta được biểu đồ trạng thái chức năng Ôn tập và chấm phỏng vấn:

| Tại giao diện | Điều kiện và chuyển trạng thái |
|---|---|
| Chi tiết công việc | Nếu ứng viên click **Ôn tập phỏng vấn** thì mở giao diện **Luyện phỏng vấn**. |
| Luyện phỏng vấn | Nếu click **Bắt đầu phiên 6 câu** hoặc **Tạo phiên mới**, hệ thống tạo phiên; nếu thành công thì hiện câu hỏi hiện tại, nếu thất bại thì hiện thông báo lỗi và ở lại Luyện phỏng vấn. |
| Luyện phỏng vấn | Nếu chọn một phiên gần đây và tải phiên/tổng kết thành công thì hiện câu hiện tại; nếu tải danh sách hoặc phiên thất bại thì hiện thông báo lỗi và vẫn ở Luyện phỏng vấn. |
| Câu hỏi và ô trả lời | Nếu click **Gửi & nhận đánh giá**, hệ thống kiểm tra nội dung. Nếu nội dung rỗng hoặc chỉ có khoảng trắng thì hiện **Hãy nhập câu trả lời**; click OK để quay lại ô trả lời. |
| Câu hỏi và ô trả lời | Nếu câu trả lời hợp lệ và gửi/chấm thành công thì hiện **Kết quả đánh giá**; nếu gửi hoặc tải dữ liệu sau khi chấm thất bại thì hiện thông báo lỗi và ở lại giao diện câu hỏi để xử lý/thử lại. |
| Kết quả đánh giá | Nếu click **Câu tiếp theo** khi phiên còn câu thì hiện câu tiếp theo; nếu phiên đã hoàn thành và ứng viên chọn **Xem tổng kết** thì hiện Tổng kết phiên. |

**Truy vết:** trạng thái và chuyển tiếp dùng `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:65`, `:153` và `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:21`, `:23`, `:31`, `:40`, `:41`, `:44`, `:45`, `:47`, `:50`, `:71`, `:81`, `:82`. Nội dung kịch bản và ngoại lệ đối chiếu `diagrams/notes/02_KichBan/KB-M4.md`.

**Open questions:** Không có dữ liệu phiên/kết quả AI thực chạy để xác nhận số điểm, nhận xét và thứ tự câu; các giá trị phụ thuộc kết quả thực tế.
