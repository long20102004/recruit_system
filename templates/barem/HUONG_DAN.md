# Mẫu barem điểm — Nhà tuyển dụng

HireLens gửi file này cho nhà tuyển dụng **tải về → điền → upload** lên hệ thống.

## File trong thư mục

| File | Mục đích |
|------|----------|
| `barem_template.csv` | Mẫu trống (chỉ header + 1 dòng ví dụ) — **điền vào file này** |
| `barem_mau_Junior_Backend_Java.csv` | Ví dụ đã điền sẵn (tham khảo) |
| `barem.schema.json` | Schema kỹ thuật (dev / validate sau khi upload) |

Mở bằng **Excel / Google Sheets**. Lưu lại dạng **CSV (UTF-8)**.

## Cách điền

Mỗi **dòng = một tiêu chí chấm** thuộc một vị trí tuyển dụng.

1. Điền thông tin vị trí (các cột đầu) — **lặp lại giống nhau** trên mọi dòng của cùng một tin.
2. Mỗi tiêu chí một dòng: tên, loại chấm, điểm tối đa, từ khóa…
3. Có thể thêm cột câu hỏi gợi ý + đáp án mẫu (tuỳ chọn) để hệ thống đưa vào ngân hàng ôn tập.

### `loai_cham` (bắt buộc chọn đúng 1 giá trị)

| Giá trị | Ý nghĩa | Ví dụ |
|---------|---------|--------|
| `diem_cong` | Cộng điểm cố định nếu đạt điều kiện | Biết tiếng Nhật N3 → +5 |
| `cham_theo_y` | Chấm theo mức độ đủ ý (0 → điểm tối đa) | Java OOP đủ 3 ý → tới 10 điểm |
| `dat_khong_dat` | Đạt / không đạt (thường dùng sàng lọc) | Có bằng tốt nghiệp CNTT |

### `bat_buoc`

- `co` — bắt buộc phải đạt / phải trả lời  
- `khong` — ưu tiên, cộng điểm thêm  

### `tu_khoa_goi_y`

Các cụm từ giúp hệ thống nhận diện ứng viên đã nêu ý (cách nhau bởi `;`).  
VD: `huong doi tuong;oop;da nen tang`

## Sau khi upload, hệ thống dùng để

1. Lưu barem theo **vị trí**  
2. Gợi ý / gắn **câu hỏi ôn tập** theo `nhom_tieu_chi` + `tu_khoa_goi_y` (+ câu hỏi recruiter điền sẵn)  
3. Chấm câu trả lời theo trọng số / điểm tối đa trong file  

## Lưu ý

- Không gộp nhiều tiêu chí vào một ô.  
- `diem_toi_da` là số (vd `5` hoặc `10`).  
- Tổng điểm các tiêu chí `cham_theo_y` + `diem_cong` nên thiết kế rõ (vd thang 100 hoặc thang 10 — ghi ở `ghi_chu` dòng đầu).  
- Không xóa dòng header.
