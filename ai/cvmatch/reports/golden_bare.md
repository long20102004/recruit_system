# Golden test BERTScore (mô hình trần)

`bertscore_config` = `bge-m3@5617a9f61b/L24/noidf/norescale/2048/mask0/alias0/text_raw/fp32` · 7.7 s

| Cách chia | Đạt | Không đạt | span |
|---|---|---|---|
| S1 | 24/25 | T19 | 0.3861 |
| S2 | 25/26 | T19 | 0.3861 |
| S3 | 25/26 | T19 | 0.3861 |

Lệch lớn nhất so với file 10 (Recall S2): **0.0190** ở `T17.pos`

| Test | Biến thể: Recall S2 | Kết quả S2 | Ghi nhận |
|---|---|---|---|
| T01 Diễn đạt khác, cùng tiếng Việt | `pos` 0.7408 · `neg` 0.6081 | ✅ pos − neg = +0.1326 (+34.4% span) |  |
| T02 Diễn đạt khác, tiếng Anh | `pos` 0.8173 · `neg` 0.6155 | ✅ pos − neg = +0.2018 (+52.3% span) |  |
| T03 Khác ngôn ngữ | `pos` 0.8652 · `neg` 0.6081 | ✅ pos − neg = +0.2571 (+66.6% span) |  |
| T04 Từ trùng, khác nghĩa (học, không làm) | `student` 0.8320 · `real` 0.9414 | ✅ real − student = +0.1093 (+28.3% span) |  |
| T05 Phủ định | `negation` 0.8222 · `real` 0.8907 · `neg` 0.6047 | ✅ real − negation = +0.0685 (+17.7% span) | ghi nhận negation − neg = +0.2175 (+56.3% span) |
| T06 Viết tắt | `pos` 0.6146 · `neg` 0.5418 | ✅ pos − neg = +0.0728 (+18.9% span) |  |
| T07 Alias công nghệ | `pos` 0.8538 · `neg` 0.5669 | ✅ pos − neg = +0.2868 (+74.3% span) |  |
| T08 Số năm | `1y` 0.8183 · `5y` 0.9291 | ✅ 5y − 1y = +0.1108 (+28.7% span) |  |
| T09 Chỉ liệt kê vs dùng thật | `A_list` 0.7326 · `B_used` 0.8442 | ✅ B_used − A_list = +0.1116 (+28.9% span) |  |
| T10 Không liên quan | `unrelated` 0.6139 · `rel_T01` 0.8039 · `rel_T03` 0.8488 · `rel_T12` 0.7251 · `rel_spring` 0.8453 | ✅ unrelated thấp hơn rel_T12: +0.1112 (+28.8% span) |  |
| T11 Không dấu | `pos` 0.6244 · `neg` 0.5668 · `pos_jd_dau` 1.0000 | ✅ pos − neg = +0.0576 (+14.9% span) | ghi nhận pos − pos_jd_dau = -0.3756 (-97.3% span) |
| T12 CV trộn Anh–Việt | `pos` 0.7826 · `neg` 0.6303 | ✅ pos − neg = +0.1522 (+39.4% span) |  |
| T13 Pha loãng (dài) | `A_one` 0.8080 · `B_diluted` 0.8080 | ✅ |B_diluted − A_one| = 5.96e-08 (0.00% span, ngưỡng 2%) | ghi nhận B_diluted − A_one = -0.0000 (-0.0% span) |
| T14 Nhồi từ khoá | `A_stuffed` 0.6655 · `B_real` 0.8782 | ✅ B_real − A_stuffed = +0.2127 (+55.1% span) |  |
| T15 CV rất ngắn | `short` 0.6698 · `neg` 0.6580 | ✅ không lỗi, mọi biến thể ra điểm | ghi nhận short − neg = +0.0119 (+3.1% span) |
| T16 CV vượt giới hạn token | `long` 0.8964 · `only_rel` 0.8964 · `neg` 0.6290 | ✅ không lỗi, mọi biến thể ra điểm | ghi nhận long − only_rel = -0.0000 (-0.0% span) |
| T17 Văn bản lỗi từ PDF | `pos` 0.7954 · `neg` 0.6027 · `clean` 0.7951 | ✅ pos − neg = +0.1927 (+49.9% span) | ghi nhận pos − clean = +0.0003 (+0.1% span) |
| T18 JD tiếng Anh, CV tiếng Việt | `pos` 0.9025 · `neg` 0.5950 | ✅ pos − neg = +0.3075 (+79.7% span) |  |
| T19 Diễn đạt khác, mức vừa | `pos` 0.6555 · `neg` 0.6896 | ❌ pos − neg = -0.0340 (-8.8% span) |  |
| T20 Kỹ năng mềm | `pos` 0.8157 · `neg` 0.6452 | ✅ pos − neg = +0.1705 (+44.2% span) |  |
| T21 Cấp bậc | `intern` 0.6197 · `lead` 0.7258 | ✅ lead − intern = +0.1061 (+27.5% span) |  |
| T22 Chuỗi kiểu lệnh trong CV | `injected` 0.7591 · `clean` 0.8182 | ✅ injected − clean = -0.0592 (-15.3% span, ngưỡng +5%) |  |
| T23 Trùng hoàn toàn | `identical` 1.0000 | ✅ điểm = 1.0000 (ngưỡng ≥ 0.99) |  |
| T24 Đảo chiều | `forward` 0.7408 · `reverse` 0.7361 | 📝  | ghi nhận forward − reverse = +0.0047 (+1.2% span) |
| F01 Bất biến: Đổi họ tên | `base` 0.8556 · `variant` 0.8556 | ✅ |variant − base| = 0.00e+00 (0.00% span, ngưỡng 2%) |  |
| F02 Bất biến: Đổi tên trường | `base` 0.8556 · `variant` 0.8556 | ✅ |variant − base| = 0.00e+00 (0.00% span, ngưỡng 2%) |  |
| F03 Bất biến: Đổi năm sinh / tốt nghiệp | `base` 0.8556 · `variant` 0.8556 | ✅ |variant − base| = 0.00e+00 (0.00% span, ngưỡng 2%) |  |
| F04 Bất biến: Đổi thứ tự gạch | `base` 0.8556 · `variant` 0.8556 | 📝  | ghi nhận variant − base = +0.0000 (+0.0% span) |
| F05 Bất biến: Chữ thường + bỏ dấu | `base` 0.8556 · `variant` 0.6833 | 📝  | ghi nhận variant − base = -0.1723 (-44.6% span) |

## Chi phí

```json
{
  "cold_s": 18.83,
  "warm_s": 0.097,
  "ms_per_cv_cold": 94.1,
  "peak_gpu_mb": 2272,
  "pairs": 4800
}
```
