# 010 · Màn C04 Tạo / sửa CV

Lỗi: nút **Sửa** ở C02 (và "Tạo CV từ đầu") mở màn C03 "Upload CV + AI trích xuất" thay vì C04 "Tạo / sửa CV"
theo Figma (`HireLens UI Redesign`, artboard `CvEditor`). FE chưa có C04.

## Quyết định (2026-11-27)

| Câu hỏi | Chọn |
|---|---|
| Phần backend chưa có (mẫu CV, xuất/xem trước PDF, "Đang tìm việc", tự lưu nháp) | Làm đủ giao diện, phần thiếu **vô hiệu + nhãn "Sắp có"** |
| "Tạo CV từ đầu" | **Làm luôn**: API tạo CV trống, C04 với form trống |

## Hành vi

- `/candidate/cv/edit?cvId=X`: sửa CV X. Không có `cvId`: CV chính. `?new=1`: tạo CV từ đầu (CV chỉ được tạo khi bấm **Lưu CV**).
- Bố cục theo Figma: breadcrumb, tên CV sửa tại chỗ, badge CV chính; trái: 8 mục (Thông tin cá nhân, Học vấn, Kinh nghiệm,
  Kỹ năng, Dự án, Chứng chỉ, Ngoại ngữ, Giải thưởng & hoạt động) với trạng thái Đủ/Trống/Đang sửa; giữa: form của mục,
  nút ← mục trước / Tiếp →; phải: Mẫu CV (Sắp có), xem trước trực tiếp.
- Mục nhiều phần tử (học vấn, kinh nghiệm, dự án, ngoại ngữ): thêm, xoá, đưa lên trên; kinh nghiệm có "Tôi đang làm ở đây".
- CV có file: nút "Tải file khác" mở C03 cho CV đó. C03 vẫn dùng cho tải CV mới.
- C02: nguồn CV hiện "Tải lên <file>" hoặc "Tạo từ form"; "Tạo CV từ đầu" khoá khi đủ 5 CV.
- Trang chủ ứng viên: "Cập nhật CV" mở C04, "Tải CV" (chưa có CV) mở C03.

## Thay đổi contract (recruitment-service)

- Mới: `POST /api/cvs/documents/blank` body `{title?}` → `BaseResponse<CvDocumentDto>`; đủ 5 CV trả 400; CV đầu tiên là CV chính.
- `PUT /api/cvs?cvId=` không còn yêu cầu CV có file (trước trả 400 "Hãy tải CV trước").

## Ngoài phạm vi

Mẫu CV, xuất PDF, cờ `open_to_work`, tự lưu nháp; trường "Công nghệ" cho từng kinh nghiệm (CandidateProfile không có).

## Kiểm chứng

- `mvn -pl recruitment-service -am test`: `createBlank` (CV chính, giới hạn 5), `confirm` lưu CV không có file.
- FE: `tsc --noEmit`, lint, build. Chưa kiểm trên trình duyệt (máy không có trình duyệt headless).
