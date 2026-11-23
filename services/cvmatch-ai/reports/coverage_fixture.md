# Báo cáo độ phủ Module 1

- CV: 34 hợp lệ / 34 file · JD: 3 hợp lệ / 3 file
- Tỉ lệ tính trên tài liệu **hợp lệ** (qua A1). Ngưỡng ở `config/coverage.yaml` (thiết kế 11 mục 2.1).

## Trường · tỉ lệ · ngưỡng · feature

| Trường | Tỉ lệ | Ngưỡng | Đạt | → Feature |
| --- | --- | --- | --- | --- |
| CV có ≥ 1 kinh nghiệm đủ `title` + `start` + (`end` | `is_current`) | 97.1% | ≥ 80.0% | ✅ | B1, B2, B3 |
| CV có ≥ 1 gạch `description` (sau tách, ≥ `bullet.min_words` từ) | 97.1% | ≥ 80.0% | ✅ | B4, B5 |
| CV có `major` + `end` học vấn | 100.0% | ≥ 70.0% | ✅ | B3, C1 |
| CV phân biệt job / dự án (có trường `projects` riêng — kể cả rỗng — hoặc `kind`) | 100.0% | ≥ 70.0% | ✅ | B2 |
| CV có `technologies` ở kinh nghiệm/dự án | 100.0% | – | – | ghi nhận |
| CV có ngày không đọc được (`date_unparsed`) | 2.9% | – | – | ghi nhận (thấp là tốt) |
| CV tiếng Việt gõ không dấu (`no_diacritics`) | 0.0% | – | – | ghi nhận (thấp là tốt) |
| JD có `responsibilities` | 100.0% | ≥ 90.0% | ✅ | B4 |
| JD có `skills` | 100.0% | – | – | ghi nhận |
| JD: `skills` kèm `required` | 66.7% | – | – | ghi nhận |
| JD: `skills` kèm `importance` | 66.7% | – | – | ghi nhận |
| JD có `min_years` | 100.0% | – | – | ghi nhận |
| JD có `level` | 33.3% | – | – | ghi nhận |
| JD có `role_group` | 0.0% | – | – | ghi nhận |
| JD có yêu cầu học vấn (`edu_required`) | 0.0% | – | – | ghi nhận |

## Quyết định theo feature

| Feature | Bật? | Lý do |
| --- | --- | --- |
| A1 | bật | không cần trường riêng |
| A2 | bật | không cần trường riêng |
| B1 | bật | đủ ngưỡng |
| B2 | bật | đủ ngưỡng |
| B3 | bật | đủ ngưỡng |
| B4 | bật | đủ ngưỡng |
| B5 | bật | đủ ngưỡng |
| C1 | bật | đủ ngưỡng |

> A1/A2: 66.7% JD có `required`, 66.7% có `importance` cho mọi kỹ năng. Thiếu → mọi kỹ năng coi là bắt buộc, `w_imp = 1` (thiết kế 11 mục 3.1.2).

## Chi tiết

- Số gạch trung bình / CV: 3.97
- Độ dài gạch (từ): p50 = 12.0, p95 = 15.0
- `description` theo mục: mảng 50 · đoạn văn 1

### Định dạng ngày (top 3)

| Mẫu | Số lần |
| --- | --- |
| `9999-99` | 65 |
| `9999` | 34 |
| `mùa xuân năm ngoái` | 1 |

## Đề xuất sửa config (không tự sửa)

Feature đang bật (`A1, B4, B1, B2`) → đề xuất:

```yaml
features_enabled: [A1, B4, B1, B2]
```
