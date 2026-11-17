# T07 · Script độ phủ Module 1 (P0)

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `11` mục 2.1 (bảng ngưỡng) và 3.1.

## Mục tiêu

Trả lời bằng số: với dữ liệu thật, trường nào đủ để **bật** feature nào. Feature chưa đạt ngưỡng thì tắt trong config, không đoán bù.

## Làm

1. `evaluation/coverage.py` + lệnh `cvmatch eval coverage --cv <dir> --jd <dir> --out report/coverage.md`.
2. Đọc JSON qua **adapter + schema của T04/T06** (không viết parser riêng), nhưng không chạy pipeline đầy đủ; chỉ cần A1 (và parse ngày).
3. Đếm đúng các dòng trong bảng 2.1 của thiết kế 11:
   - CV: tỉ lệ CV có ≥ 1 mục kinh nghiệm đủ `title/start/end|is_current`; có ≥ 1 gạch `description`; `description` dạng mảng hay đoạn; có `major` + `end` học vấn; có phân biệt job/dự án; có `technologies`.
   - JD: có `responsibilities`; `skills` có `required` / `importance`; có `min_years`, `level`, `role_group`, yêu cầu học vấn.
   - Thêm: định dạng ngày gặp được (top 10 mẫu), tỉ lệ `date_unparsed`, tỉ lệ CV không dấu, số gạch trung bình/CV, độ dài gạch (token) p50/p95.
4. Báo cáo Markdown: bảng "trường · tỉ lệ · ngưỡng · → bật/tắt feature", và đề xuất sửa `config/rr-1.0.yaml` (in ra, không tự sửa).

## Tiêu chí xong

- Chạy được trên thư mục fixture; khi có dữ liệu thật (Q-8) chạy và đính kèm báo cáo.
- Test với 3 CV tổng hợp có/thiếu trường → tỉ lệ đúng.

## Ghi chú bàn giao

_(agent điền)_
