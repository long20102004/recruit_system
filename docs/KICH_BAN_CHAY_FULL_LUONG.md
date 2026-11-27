# Kịch bản chạy full luồng HireLens

Dùng để kiểm thử toàn hệ thống trước khi demo/bảo vệ. Chạy theo thứ tự: phần sau dùng dữ liệu phần trước tạo ra.
Mỗi bước có **Kỳ vọng**; đánh dấu ✅/❌ vào bảng ở cuối và ghi lỗi.

Thời gian: khoảng 60–90 phút (lần đầu AI tải model lâu hơn).

---

## 0. Chuẩn bị

### 0.1 Dịch vụ cần chạy

| Thành phần | Cổng | Cách chạy |
|---|---|---|
| MySQL (identity, recruitment, interview, notification), Redis, RabbitMQ, Mailpit | 3307–3310, 6380, 5672/15672, 8025 | `docker compose up -d identity-db recruitment-db interview-db notification-db redis rabbitmq mailpit` |
| identity-service | 8081 | IDE hoặc Docker |
| recruitment-service | 8082 | cần `.env` có `R2_*` (docs/R2_STORAGE.md) |
| interview-service | 8083 | |
| notification-service | 8084 | |
| api-gateway | 8080 | |
| cv-extraction-ai, cvmatch-ai (+ `cvmatch-db`), interview-ai | 8001, 8003, 8000 | local (`--profile cv-ai/match/ai`) hoặc máy GPU (docs/GPU_REMOTE_HOSTING.md) |
| Frontend | 5173 | `cd frontend && npm run dev` |

- Backend chạy bằng **JDK 21** (JDK 25 làm Lombok lỗi).
- Chạy AI trên máy GPU: dán 3 URL vào `.env` (`AI_URL`, `CV_EXTRACTION_URL`, `CVMATCH_URL`) trước khi khởi động backend.

### 0.2 Kiểm tra nhanh (smoke)

```bash
for p in 8080 8081 8082 8083 8084; do curl -s -o /dev/null -w "$p %{http_code}\n" localhost:$p/health; done
curl -s localhost:8001/health; curl -s localhost:8003/health; curl -s localhost:8000/health   # hoặc URL máy GPU
```

**Kỳ vọng:** gateway và 4 service Java trả `200`, 3 service AI trả `"status":"ok"`.
Mở sẵn: Mailpit `http://localhost:8025`, RabbitMQ UI `http://localhost:15672` (guest/guest), Cloudflare R2 dashboard.

### 0.3 Tài khoản và dữ liệu

| Vai trò | Tài khoản | Ghi chú |
|---|---|---|
| Admin | `admin@hirelens.local` / `demo1234` | có sẵn |
| Nhà tuyển dụng mới | `ntd.test+<ngày>@example.com` | tạo ở bước 1 |
| Ứng viên mới | `uv.test+<ngày>@example.com` | tạo ở bước 1 |
| CV mẫu | 1 file PDF + 1 file DOCX **tổng hợp** (không dùng CV thật) | |
| Ảnh | logo PNG < 5MB, ảnh bìa JPG, file GPKD PDF | |

Dùng 3 trình duyệt/cửa sổ ẩn danh riêng cho Admin, Nhà tuyển dụng, Ứng viên để xem thông báo realtime song song.

---

## 1. Đăng ký và xác thực tài khoản

| # | Vai trò | Thao tác | Kỳ vọng |
|---|---|---|---|
| 1.1 | Ứng viên | `/register` đăng ký email ứng viên | Báo đã gửi mail xác thực; chưa đăng nhập được |
| 1.2 | Ứng viên | Mailpit → mở mail → bấm link | `/verify-email` báo thành công |
| 1.3 | Ứng viên | `/login` → `/choose-role` chọn **Ứng viên** | Vào `/candidate` |
| 1.4 | NTD | Lặp 1.1–1.3, chọn **Nhà tuyển dụng** | Vào khu vực nhà tuyển dụng, được dẫn tới đăng ký công ty |
| 1.5 | Bất kỳ | `/forgot-password` → mail Mailpit → đặt lại mật khẩu → đăng nhập bằng mật khẩu mới | Thành công |
| 1.6 | Bất kỳ | Đăng nhập sai 5 lần | Bị khoá 15 phút (sau đó dùng tài khoản khác hoặc chờ) |

---

## 2. Đăng ký công ty và duyệt

| # | Vai trò | Thao tác | Kỳ vọng |
|---|---|---|---|
| 2.1 | NTD | `/recruiter/company/register`: nhập thông tin, **chọn logo** và **file GPKD** | Toast "Đã tải logo/giấy phép lên"; R2: object trong `hirelens/companies/<id>/logo/` và `hirelens-private/companies/<id>/license/` |
| 2.2 | NTD | Gửi đăng ký | Trạng thái chờ duyệt |
| 2.3 | Admin | `/admin/companies` → mở công ty → **Xem giấy phép** | Tab mới mở PDF qua link R2 ký tạm (URL có `X-Amz-Signature`) |
| 2.4 | Admin | **Từ chối** kèm lý do | NTD: chuông +1 **ngay** (không tải lại trang), thông báo "Hồ sơ công ty bị từ chối"; Mailpit có email tới NTD |
| 2.5 | NTD | Sửa, gửi lại; Admin **Duyệt** | NTD nhận thông báo "Công ty đã được duyệt" + email |
| 2.6 | NTD | `/recruiter/company`: đổi **ảnh bìa** | Ảnh bìa hiển thị; `/companies/<id>` (trang công khai) hiện logo + ảnh bìa |

---

## 3. Đăng tin tuyển dụng

| # | Vai trò | Thao tác | Kỳ vọng |
|---|---|---|---|
| 3.1 | NTD | `/recruiter/jobs/new`: tạo tin (VD "Backend Java Developer", kỹ năng Java, Spring, MySQL) → đăng | Tin ở trạng thái đang tuyển trong `/recruiter/jobs` |
| 3.2 | Khách | `/jobs` tìm theo từ khoá | Thấy tin vừa đăng |
| 3.3 | NTD | Tạo thêm 1 tin khác ngành (để so sánh điểm matching) | |

---

## 4. Ứng viên chuẩn bị CV

| # | Vai trò | Thao tác | Kỳ vọng |
|---|---|---|---|
| 4.1 | Ứng viên | `/candidate/profile` (C14) cài đặt thông báo: bật email cho "Trạng thái đơn ứng tuyển" | Lưu thành công |
| 4.2 | Ứng viên | `/candidate/cvs` → tải **CV PDF** | AI trích xuất (vài giây), form điền sẵn kỹ năng/kinh nghiệm; CV đầu tiên là **CV chính**; chuông có thông báo "AI đã xử lý xong CV" (không có email vì loại này mặc định tắt email) |
| 4.3 | Ứng viên | Sửa vài trường → lưu | Lưu thành công |
| 4.4 | Ứng viên | Thêm **CV DOCX** | Xem trước DOCX hiển thị; AI trích xuất; R2 có object `.docx` |
| 4.5 | Ứng viên | Đổi tên CV, **đặt CV DOCX làm CV chính**, **Tải về** | Tải về đúng tên file gốc (link ký tạm) |
| 4.6 | Ứng viên | Thêm đến CV thứ 6 | Báo lỗi tối đa 5 CV |

---

## 5. Tìm việc, gợi ý và ứng tuyển

| # | Vai trò | Thao tác | Kỳ vọng |
|---|---|---|---|
| 5.1 | Ứng viên | `/candidate/matching` | Danh sách tin có điểm phù hợp; tin Backend Java cao hơn tin khác ngành |
| 5.2 | Ứng viên | Lưu tin → `/candidate/saved` | Tin có trong danh sách đã lưu |
| 5.3 | Ứng viên | `/candidate/jobs/<id>` → Ứng tuyển, **chọn CV PDF** (không phải CV chính) | Đơn ở trạng thái "Đã nộp" trong `/candidate/applications` |
| 5.4 | Ứng viên | Thử xoá CV vừa dùng để ứng tuyển | Bị chặn (CV đang trong đơn chưa kết thúc) |

---

## 6. Nhà tuyển dụng xử lý đơn (luồng thông báo chính)

Mở song song cửa sổ Ứng viên, để ý chuông.

| # | Vai trò | Thao tác | Kỳ vọng |
|---|---|---|---|
| 6.1 | NTD | `/recruiter/candidates` → mở đơn | Thấy điểm matching, thông tin CV đúng **CV PDF đã chọn** ở 5.3 |
| 6.2 | NTD | **Tải CV** | Tải PDF qua link ký tạm |
| 6.3 | NTD | `/recruiter/matching`: chạy matching cho tin | Danh sách ứng viên xếp hạng |
| 6.4 | NTD | Chuyển đơn sang **Đang xem xét** | Ứng viên: chuông +1 trong ~1–2 giây; `/notifications` tab **Ứng tuyển** có "Đơn ứng tuyển Đang xem xét"; Mailpit có email (đã bật ở 4.1) |
| 6.5 | Ứng viên | Bấm thông báo | Điều hướng tới `/candidate/applications`, thông báo chuyển đã đọc, **chuông giảm** |
| 6.6 | Ứng viên | Mở 2 tab, bấm "Đánh dấu tất cả đã đọc" ở 1 tab | Chuông ở **cả 2 tab** về 0 |
| 6.7 | NTD | Chuyển sang **Phỏng vấn** | Ứng viên nhận "Lời mời phỏng vấn" (tab **Phỏng vấn**) + email |

---

## 7. Phỏng vấn AI

| # | Vai trò | Thao tác | Kỳ vọng |
|---|---|---|---|
| 7.1 | Ứng viên | `/candidate/interview` → bắt đầu phiên cho đơn/tin vừa mời | Nhận bộ câu hỏi theo tin |
| 7.2 | Ứng viên | Trả lời từng câu → kết thúc | Có tóm tắt/điểm (interview-ai chấm) |
| 7.3 | NTD | `/recruiter/interview-results` | Thấy kết quả phiên của ứng viên |
| 7.4 | Admin | `/admin/questions` thêm 1 câu hỏi; tạo phiên mới | Câu hỏi mới có thể xuất hiện trong phiên |

---

## 8. Kết thúc đơn

| # | Vai trò | Thao tác | Kỳ vọng |
|---|---|---|---|
| 8.1 | NTD | Chuyển đơn sang **Đã tuyển** | Ứng viên nhận thông báo + email |
| 8.2 | Ứng viên | Ứng tuyển tin thứ 2 → NTD **Từ chối** | Ứng viên nhận thông báo "Từ chối" |
| 8.3 | NTD | Thử chuyển đơn đã tuyển về "Đang xem xét" | Bị chặn (chuyển trạng thái không hợp lệ) |
| 8.4 | Ứng viên | Xoá CV PDF (đơn đã kết thúc) | Xoá được; object trên R2 biến mất |

---

## 9. Quản trị

| # | Vai trò | Thao tác | Kỳ vọng |
|---|---|---|---|
| 9.1 | Admin | `/admin/jobs` → **Khoá** tin thứ 2 kèm lý do | NTD nhận thông báo "Tin tuyển dụng bị khoá" (tab **Công ty**) + email; ứng viên không còn thấy tin ở `/jobs` |
| 9.2 | Admin | Mở khoá | Tin hiển thị lại |
| 9.3 | Admin | `/admin/users` khoá tài khoản ứng viên | Ứng viên bị đăng xuất / không đăng nhập được; mở khoá lại |
| 9.4 | Admin | `/admin/roles` xem/bỏ 1 quyền của vai trò NTD → NTD thử thao tác tương ứng | Bị từ chối (403); trả quyền lại |
| 9.5 | Admin | `/admin` dashboard | Số liệu khớp dữ liệu vừa tạo |

---

## 10. Độ tin cậy của thông báo (RabbitMQ)

| # | Thao tác | Kỳ vọng |
|---|---|---|
| 10.1 | `docker compose stop rabbitmq` → NTD đổi trạng thái 1 đơn | Thao tác nghiệp vụ **vẫn thành công**; bảng `outbox_events` (recruitment DB) có dòng `published_at IS NULL`, `attempts` tăng |
| 10.2 | `docker compose start rabbitmq`, chờ ~10 giây | Ứng viên nhận thông báo bị trễ; dòng outbox có `published_at` |
| 10.3 | Tắt identity-service → đổi trạng thái 1 đơn → chờ ~20 giây | RabbitMQ UI: message vào `notification.events.dlq` sau 4 lần thử |
| 10.4 | Bật lại identity; (tuỳ chọn) chuyển message từ DLQ về `notification.events` bằng RabbitMQ UI (Shovel / Move messages) | Thông báo được tạo, không trùng |
| 10.5 | Tắt Mailpit → đổi trạng thái → bật lại sau 1 phút | Email vẫn được gửi (thử lại sau 30s, 1m, 2m...) |

Truy vấn hữu ích:

```sql
-- recruitment DB (cổng 3308)
SELECT id, routing_key, attempts, published_at, last_error FROM outbox_events ORDER BY id DESC LIMIT 10;
-- notification DB (cổng 3310)
SELECT id, user_id, type, title, read_at FROM notifications ORDER BY id DESC LIMIT 10;
SELECT id, recipient_email, status, attempts, next_attempt_at FROM email_deliveries ORDER BY id DESC LIMIT 10;
```

---

## 11. Phân quyền và dữ liệu riêng tư (kiểm tra âm)

| # | Thao tác | Kỳ vọng |
|---|---|---|
| 11.1 | Ứng viên gọi `GET /api/applications/<id>/cv-file` của đơn người khác | 403/404 |
| 11.2 | Ứng viên gọi `POST /api/notifications/<id>/read` với id thông báo của người khác | 404 |
| 11.3 | Ứng viên mở `/recruiter/jobs`, `/admin` | Bị chặn / chuyển hướng |
| 11.4 | Mở link R2 ký tạm sau hơn 5 phút | R2 trả lỗi hết hạn |
| 11.5 | Mở URL object private bỏ phần `?X-Amz-...` | Bị từ chối |
| 11.6 | Tải file `.txt` làm CV; tải ảnh logo > 5MB | Báo lỗi định dạng / kích thước |

---

## 12. Bảng ghi kết quả

| Phần | Số bước | Đạt | Lỗi | Ghi chú |
|---|---|---|---|---|
| 0. Chuẩn bị | | | | |
| 1. Tài khoản | 6 | | | |
| 2. Công ty | 6 | | | |
| 3. Tin tuyển dụng | 3 | | | |
| 4. CV | 6 | | | |
| 5. Ứng tuyển | 4 | | | |
| 6. Xử lý đơn + thông báo | 7 | | | |
| 7. Phỏng vấn AI | 4 | | | |
| 8. Kết thúc đơn | 4 | | | |
| 9. Quản trị | 5 | | | |
| 10. Độ tin cậy | 5 | | | |
| 11. Phân quyền | 6 | | | |

Mẫu ghi lỗi: `<phần.bước> — thao tác — kết quả thực tế — kỳ vọng — log/ảnh chụp (service, thời điểm)`.

### Kịch bản demo rút gọn (~15 phút, cho buổi bảo vệ)

1. Ứng viên tải CV PDF → AI điền form (4.2).
2. Ứng viên xem gợi ý việc làm có điểm (5.1) → ứng tuyển (5.3).
3. NTD xem đơn, điểm matching, tải CV (6.1–6.2) → chuyển **Phỏng vấn** → chuông ứng viên nhảy realtime + email Mailpit (6.7).
4. Ứng viên phỏng vấn AI (7.1–7.2) → NTD xem kết quả (7.3).
5. Admin khoá tin → NTD nhận thông báo (9.1).
6. (Nếu còn thời gian) tắt RabbitMQ, thao tác, bật lại → thông báo vẫn tới (10.1–10.2).
