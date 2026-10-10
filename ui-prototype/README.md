# HireLens — UI Prototype (HTML/CSS/JS)

Prototype giao diện tiếng Việt cho đồ án **Hệ thống tuyển dụng thông minh** (Module 1–3).  
Đây là **template UI + dữ liệu minh họa**, chưa kết nối Spring Boot / PostgreSQL / AI service.

## Hướng UX

Trang mở ra là danh sách việc (gần bạn trước), nhưng mặt hình theo kiểu biên tập: nền giấy, chữ serif, ít badge.

- Ô tìm + danh sách việc, không banner marketing
- AI (CV / matching / phỏng vấn) nằm trên menu, không phải dashboard
- Màu mực / đất, không xanh lá kiểu job board đại trà

## Cách mở

1. Mở file `index.html` bằng trình duyệt (Chrome/Edge/Firefox).
2. Duyệt việc ngay trên trang chủ; hoặc **Đăng nhập** → chọn **Ứng viên** / **Nhà tuyển dụng**.

Khuyến nghị khi chỉnh sửa CSS/JS: chạy static server tại thư mục này, ví dụ:

```bash
# Python
python -m http.server 5500

# Node (nếu có)
npx --yes serve -p 5500
```

Rồi mở `http://localhost:5500`.

## Cấu trúc

```
ui-prototype/
├── index.html                 # Landing
├── login.html                 # Chọn vai trò (demo)
├── candidate/                 # Luồng ứng viên
│   ├── index.html
│   ├── cv.html                # Module 1
│   ├── matching.html          # Module 2
│   └── interview.html         # Module 3
├── recruiter/                 # Luồng nhà tuyển dụng
│   ├── index.html
│   ├── jobs.html
│   ├── candidates.html
│   ├── matching.html
│   └── interviews.html
└── assets/
    ├── css/main.css
    └── js/
        ├── mock-data.js       # Dữ liệu minh họa
        └── common.js
```

## Luồng demo

### Ứng viên
1. Upload / chạy trích xuất CV (giả lập)
2. Sửa & xác nhận JSON trích xuất
3. Xem ranking job + kỹ năng trùng/thiếu + lý do
4. Trả lời phỏng vấn text, xem điểm đã hiệu chỉnh + ý thiếu

### Nhà tuyển dụng
1. Quản lý JD / skill bắt buộc
2. Xem CV đã parse (kèm JSON schema mẫu)
3. Xem bảng matching
4. Ngân hàng câu hỏi, rubric, kết quả phiên phỏng vấn

## Lưu ý học thuật / kỹ thuật

- Banner trên mọi trang ghi rõ đây là prototype.
- Điểm matching và BERTScore có định nghĩa trên UI; **không** tuyên bố mô hình đã train/evaluate đầy đủ.
- `mock-data.js` là dữ liệu minh họa; bản production phải lấy từ API.
- Frontend **không** truy cập database hay file model trực tiếp.

## Bước tiếp theo (ngoài prototype)

1. Spring Boot REST + PostgreSQL theo schema đồ án  
2. AI service (Python) cho NER / embedding / BERTScore  
3. Thay mock bằng fetch API, giữ nguyên cấu trúc màn hình này  

## Trạng thái

| Hạng mục | Trong prototype |
|---|---|
| UI 3 module + 2 vai trò | Có |
| Mock CV / Job / Interview | Có (minh họa) |
| Backend / DB / AI thật | Chưa |
| Learning-to-Rank đã train | Chưa |
| BERTScore service online | Chưa (có script offline ở thư mục `DO_AN`) |
