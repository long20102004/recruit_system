# Báo cáo độ phủ Module 1

- CV: 5 hợp lệ / 5 file · JD: 0 hợp lệ / 0 file
- Tỉ lệ tính trên tài liệu **hợp lệ** (qua A1). Ngưỡng ở `config/coverage.yaml` (thiết kế 11 mục 2.1).

## Trường · tỉ lệ · ngưỡng · feature

| Trường | Tỉ lệ | Ngưỡng | Đạt | → Feature |
| --- | --- | --- | --- | --- |
| CV có ≥ 1 kinh nghiệm đủ `title` + `start` + (`end` | `is_current`) | 40.0% | ≥ 80.0% | ❌ tắt | B1, B2, B3 |
| CV có ≥ 1 gạch `description` (sau tách, ≥ `bullet.min_words` từ) | 100.0% | ≥ 80.0% | ✅ | B4, B5 |
| CV có `major` + `end` học vấn | 60.0% | ≥ 70.0% | ❌ tắt | B3, C1 |
| CV phân biệt job / dự án (có trường `projects` riêng — kể cả rỗng — hoặc `kind`) | 100.0% | ≥ 70.0% | ✅ | B2 |
| CV có `technologies` ở kinh nghiệm/dự án | 40.0% | – | – | ghi nhận |
| CV có ngày không đọc được (`date_unparsed`) | 20.0% | – | – | ghi nhận (thấp là tốt) |
| CV tiếng Việt gõ không dấu (`no_diacritics`) | 0.0% | – | – | ghi nhận (thấp là tốt) |
| JD có `responsibilities` | – | ≥ 90.0% | – | B4 |
| JD có `skills` | – | – | – | ghi nhận |
| JD: `skills` kèm `required` | – | – | – | ghi nhận |
| JD: `skills` kèm `importance` | – | – | – | ghi nhận |
| JD có `min_years` | – | – | – | ghi nhận |
| JD có `level` | – | – | – | ghi nhận |
| JD có `role_group` | – | – | – | ghi nhận |
| JD có yêu cầu học vấn (`edu_required`) | – | – | – | ghi nhận |

## Quyết định theo feature

| Feature | Bật? | Lý do |
| --- | --- | --- |
| A1 | bật | không cần trường riêng |
| A2 | bật | không cần trường riêng |
| B1 | **tắt** | không đạt: cv_exp_dated |
| B2 | **tắt** | không đạt: cv_exp_dated |
| B3 | **tắt** | không đạt: cv_exp_dated, cv_edu_major_end |
| B4 | bật | đủ ngưỡng |
| B5 | bật | đủ ngưỡng |
| C1 | **tắt** | không đạt: cv_edu_major_end |

## Chi tiết

- Số gạch trung bình / CV: 2.40
- Độ dài gạch (từ): p50 = 8.5, p95 = 12.0
- `description` theo mục: mảng 7 · đoạn văn 0

### Định dạng ngày (top 6)

| Mẫu | Số lần |
| --- | --- |
| `9999` | 10 |
| `99/9999` | 4 |
| `t9/9999` | 1 |
| `giữa năm 9999` | 1 |
| `Mon 9999` | 1 |
| `present` | 1 |

## Đề xuất sửa config (không tự sửa)

Feature đang bật (`A1, B4, B1, B2`) → đề xuất:

```yaml
features_enabled: [A1, B4]
```

Không bật ở P2 khi dữ liệu chưa đổi: B1, B2, B3, C1.

> Chưa đủ cả CV và JD: dòng không có dữ liệu để `–`, feature tương ứng giữ nguyên.
