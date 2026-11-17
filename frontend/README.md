# HireLens Frontend

React, Vite và TypeScript. Dữ liệu lấy từ backend `/api`.

## Chạy

```bash
npm install
npm run dev
```

Vite proxy: `/api` → `http://localhost:8080`.

## Tài khoản dữ liệu mẫu

- Ứng viên: `candidate@hirelens.local` / `demo1234`
- Nhà tuyển dụng: `recruiter@hirelens.local` / `demo1234`

## Đường dẫn

| Path | Mô tả |
|------|--------|
| `/` | Trang việc làm công khai; đã đăng nhập thì vào trang tài khoản |
| `/jobs` | Danh sách việc làm công khai |
| `/login` | Đăng nhập |
| `/register` | Đăng ký email và mật khẩu |
| `/choose-role` | Chọn vai trò lần đầu |
| `/candidate` | Trang việc làm của ứng viên |
| `/candidate/cv` | Hồ sơ CV |
| `/candidate/matching` | Việc phù hợp với hồ sơ |
| `/candidate/jobs/:id` | Chi tiết tin tuyển dụng |
| `/candidate/interview` | Ôn tập phỏng vấn |
| `/recruiter` | Tổng quan nhà tuyển dụng |
