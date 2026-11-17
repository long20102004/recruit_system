# Golden test BERTScore (qua pipeline)

`bertscore_config` = `bge-m3@5617a9f61b/L24/noidf/norescale/2048/mask1/alias1/text_raw/fp32` · 4.9 s

| Cách chia | Đạt | Không đạt | span |
|---|---|---|---|
| S1 | 24/25 | T19 | 0.3861 |
| S2 | 25/26 | T19 | 0.3861 |
| S3 | 25/26 | T19 | 0.3861 |

| Test | Biến thể: Recall S2 | Kết quả S2 | Ghi nhận |
|---|---|---|---|
| T01 Diễn đạt khác, cùng tiếng Việt | `pos` 0.7408 · `neg` 0.6081 | ✅ pos − neg = +0.1326 (+34.4% span) |  |
| T02 Diễn đạt khác, tiếng Anh | `pos` 0.8173 · `neg` 0.6155 | ✅ pos − neg = +0.2018 (+52.3% span) |  |
| T03 Khác ngôn ngữ | `pos` 0.8652 · `neg` 0.6081 | ✅ pos − neg = +0.2571 (+66.6% span) |  |
| T04 Từ trùng, khác nghĩa (học, không làm) | `student` 0.8471 · `real` 0.9608 | ✅ real − student = +0.1137 (+29.5% span) |  |
| T05 Phủ định | `negation` 0.8222 · `real` 0.8907 · `neg` 0.6047 | ✅ real − negation = +0.0685 (+17.7% span) | ghi nhận negation − neg = +0.2175 (+56.3% span) |
| T06 Viết tắt | `pos` 0.8121 · `neg` 0.6180 | ✅ pos − neg = +0.1941 (+50.3% span) |  |
| T07 Alias công nghệ | `pos` 0.9201 · `neg` 0.5849 | ✅ pos − neg = +0.3352 (+86.8% span) |  |
| T08 Số năm | `1y` 0.9304 · `5y` 0.9304 | ✅ |5y − 1y| = 0.00e+00 (0.00% span, ngưỡng 2%) |  |
| T09 Chỉ liệt kê vs dùng thật | `A_list` 0.7326 · `B_used` 0.8442 | ✅ B_used − A_list = +0.1116 (+28.9% span) |  |
| T10 Không liên quan | `unrelated` 0.6139 · `rel_T01` 0.8039 · `rel_T03` 0.8488 · `rel_T12` 0.7325 · `rel_spring` 0.8030 | ✅ unrelated thấp hơn rel_T12: +0.1186 (+30.7% span) |  |
| T11 Không dấu | `pos` 0.6244 · `neg` 0.5668 · `pos_jd_dau` 1.0000 | ✅ pos − neg = +0.0576 (+14.9% span) | ghi nhận pos − pos_jd_dau = -0.3756 (-97.3% span) |
| T12 CV trộn Anh–Việt | `pos` 0.7824 · `neg` 0.6303 | ✅ pos − neg = +0.1521 (+39.4% span) |  |
| T13 Pha loãng (dài) | `A_one` 0.8306 · `B_diluted` 0.8306 | ✅ |B_diluted − A_one| = 5.96e-08 (0.00% span, ngưỡng 2%) | ghi nhận B_diluted − A_one = +0.0000 (+0.0% span) |
| T14 Nhồi từ khoá | `A_stuffed` 0.6655 · `B_real` 0.8858 | ✅ B_real − A_stuffed = +0.2203 (+57.1% span) |  |
| T15 CV rất ngắn | `short` 0.6698 · `neg` 0.6580 | ✅ không lỗi, mọi biến thể ra điểm | ghi nhận short − neg = +0.0119 (+3.1% span) |
| T16 CV vượt giới hạn token | `long` 0.8753 · `only_rel` 0.8753 · `neg` 0.6290 | ✅ không lỗi, mọi biến thể ra điểm | ghi nhận long − only_rel = +0.0000 (+0.0% span) |
| T17 Văn bản lỗi từ PDF | `pos` 0.8165 · `neg` 0.6027 · `clean` 0.8210 | ✅ pos − neg = +0.2137 (+55.4% span) | ghi nhận pos − clean = -0.0045 (-1.2% span) |
| T18 JD tiếng Anh, CV tiếng Việt | `pos` 0.9025 · `neg` 0.5950 | ✅ pos − neg = +0.3075 (+79.7% span) |  |
| T19 Diễn đạt khác, mức vừa | `pos` 0.6555 · `neg` 0.6896 | ❌ pos − neg = -0.0340 (-8.8% span) |  |
| T20 Kỹ năng mềm | `pos` 0.8496 · `neg` 0.6452 | ✅ pos − neg = +0.2044 (+53.0% span) |  |
| T21 Cấp bậc | `intern` 0.6767 · `lead` 0.8357 | ✅ lead − intern = +0.1590 (+41.2% span) |  |
| T22 Chuỗi kiểu lệnh trong CV | `injected` 0.7632 · `clean` 0.8182 | ✅ injected − clean = -0.0550 (-14.3% span, ngưỡng +5%) |  |
| T23 Trùng hoàn toàn | `identical` 1.0000 | ✅ điểm = 1.0000 (ngưỡng ≥ 0.99) |  |
| T24 Đảo chiều | `forward` 0.7408 · `reverse` 0.7361 | 📝  | ghi nhận forward − reverse = +0.0047 (+1.2% span) |
| F01 Bất biến: Đổi họ tên | `base` 0.8608 · `variant` 0.8608 | ✅ |variant − base| = 0.00e+00 (0.00% span, ngưỡng 2%) |  |
| F02 Bất biến: Đổi tên trường | `base` 0.8608 · `variant` 0.8608 | ✅ |variant − base| = 0.00e+00 (0.00% span, ngưỡng 2%) |  |
| F03 Bất biến: Đổi năm sinh / tốt nghiệp | `base` 0.8608 · `variant` 0.8608 | ✅ |variant − base| = 0.00e+00 (0.00% span, ngưỡng 2%) |  |
| F04 Bất biến: Đổi thứ tự gạch | `base` 0.8608 · `variant` 0.8608 | 📝  | ghi nhận variant − base = +0.0000 (+0.0% span) |
| F05 Bất biến: Chữ thường + bỏ dấu | `base` 0.8608 · `variant` 0.6983 | 📝  | ghi nhận variant − base = -0.1624 (-42.1% span) |
