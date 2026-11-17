# ST-M2 — Biểu đồ trạng thái chức năng tải lên và xác nhận CV

**Bước 1.** Từ kịch bản M2, xác định các giao diện chính của `CandidateCvPage`: giao diện đang tải hồ sơ, giao diện “Hồ sơ của bạn”, giao diện “Hồ sơ & phân tích CV” và các thông báo kết quả tải lên/xác nhận. Các giao diện xem và chỉnh sửa cùng thuộc một trang; trạng thái bước được điều khiển bởi `step`.

**Bước 2.** Xác định chuyển trạng thái theo thao tác ứng viên và kết quả xử lý. Khi tải trang, hệ thống lấy hồ sơ; hồ sơ đã phân tích được hiển thị ở giao diện “Hồ sơ của bạn”, còn hồ sơ chưa phân tích hoặc lỗi lấy dữ liệu dẫn tới giao diện “Hồ sơ & phân tích CV”. Tại giao diện này, chọn PDF hợp lệ dẫn tới tải lên; lỗi định dạng, lỗi xử lý và lỗi xác nhận hiện thông báo tương ứng rồi quay lại giao diện. Xác nhận thành công chuyển về giao diện hồ sơ. Nút “Cập nhật hồ sơ” quay từ hồ sơ về giao diện kiểm tra. Ta được biểu đồ trạng thái:

- Tại giao diện “Hồ sơ của bạn”, nếu ứng viên chọn “Cập nhật hồ sơ” thì chuyển sang giao diện “Hồ sơ & phân tích CV”, bước 2.
- Tại giao diện “Hồ sơ & phân tích CV”, nếu chọn tệp không có đuôi `.pdf` thì hiện thông báo “Chỉ nhận file PDF”; đóng thông báo thì quay lại giao diện trước đó.
- Tại giao diện “Hồ sơ & phân tích CV”, nếu chọn PDF hợp lệ và tải lên thành công thì hiện thông báo tải CV thành công; đóng thông báo thì tiếp tục kiểm tra, chỉnh sửa thông tin.
- Tại giao diện “Hồ sơ & phân tích CV”, nếu tải lên hoặc xử lý CV thất bại thì hiện thông báo lỗi; đóng thông báo thì giữ giao diện kiểm tra.
- Tại giao diện “Hồ sơ & phân tích CV”, nếu chọn “Xác nhận hồ sơ” khi chưa có tệp thì hiện thông báo “Hãy tải CV trước”; đóng thông báo thì quay lại giao diện kiểm tra.
- Tại giao diện “Hồ sơ & phân tích CV”, nếu đã có tệp và xác nhận thành công thì hiện thông báo “Đã xác nhận hồ sơ”; đóng thông báo thì hiện giao diện “Hồ sơ của bạn”. Nếu xác nhận thất bại thì hiện thông báo lỗi và đóng thông báo để quay lại giao diện kiểm tra.
- Tại giao diện “Hồ sơ của bạn”, nếu ứng viên rời chức năng CV thì kết thúc luồng.

**Ghi chú:** Đích điều hướng cụ thể khi phiên hết hạn hoặc sai vai trò chưa được xác định từ hành vi trang CV; nội dung này được ghi trong `open_questions` của spec.
