# HireLens — UI Prototype

Prototype giao diện tiếng Việt cho **hệ thống hỗ trợ tuyển dụng sinh viên IT**.  
Dữ liệu minh họa trên trình duyệt; chưa nối backend.

## Vai trò

### Ứng viên
1. Xem / tìm việc gần mình  
2. Tải CV → kiểm tra thông tin → xác nhận hồ sơ  
3. Xem việc phù hợp (điểm %, kỹ năng trùng/thiếu)  
4. Luyện phỏng vấn text → điểm 0–10 + ý đủ/thiếu  

### Nhà tuyển dụng
1. Đăng vị trí: tiêu đề, cấp bậc, kỹ năng, yêu cầu, mô tả  
2. Quản lý tin đang mở (lưu trên trình duyệt)  
3. Xem hồ sơ ứng viên  
4. Ghép hồ sơ–tin tuyển dụng  
5. Ngân hàng câu hỏi + kết quả phiên phỏng vấn  

## Cách mở

```bash
cd ui-prototype
python3 -m http.server 5500
```

Mở `http://localhost:5500` → **Đăng nhập** → chọn **Ứng viên** hoặc **Nhà tuyển dụng**.

## Cấu trúc

```
ui-prototype/
├── index.html              # Trang tìm việc (công khai)
├── login.html
├── candidate/              # Luồng ứng viên
├── recruiter/              # Luồng nhà tuyển dụng
└── assets/
    ├── css/main.css
    └── js/
        ├── mock-data.js
        └── common.js       # job list + tin đăng localStorage
```

Tin đăng mới từ nhà tuyển dụng được lưu trong `localStorage` (`hirelens_jobs_extra`) và hiện trên feed tìm việc.
