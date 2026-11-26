# Đo thời gian match theo cỡ pool (S05)

- Thiết bị: `cuda`, 6 luồng torch · kho: 300 CV · rerank toàn bộ pool (K = N = n)
- `cold`: lần đầu với pool đó (cache token BERTScore chỉ ở RAM, chưa có) · `warm`: chạy lại ngay

| Luồng | n | Lần | Retrieve (s) | Rerank (s) | trong đó BERTScore (s) | Tổng (s) | ms / ứng viên |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| jd_to_cv | 10 | cold | 0.066 | 1.093 | 1.012 | 1.206 | 120.6 |
| jd_to_cv | 10 | warm | 0.033 | 0.057 | 0.009 | 0.132 | 13.2 |
| jd_to_cv | 50 | cold | 0.047 | 1.268 | 1.122 | 1.348 | 27.0 |
| jd_to_cv | 50 | warm | 0.136 | 0.210 | 0.046 | 0.372 | 7.4 |
| jd_to_cv | 100 | cold | 0.089 | 1.175 | 0.841 | 1.325 | 13.2 |
| jd_to_cv | 100 | warm | 0.079 | 0.401 | 0.082 | 0.517 | 5.2 |
| jd_to_cv | 200 | cold | 0.105 | 1.331 | 0.621 | 1.465 | 7.3 |
| jd_to_cv | 200 | warm | 0.092 | 0.796 | 0.179 | 0.918 | 4.6 |
| jd_to_cv | 300 | cold | 0.131 | 1.375 | 0.376 | 1.538 | 5.1 |
| jd_to_cv | 300 | warm | 0.135 | 1.178 | 0.279 | 1.346 | 4.5 |
| cv_to_jd | 27 | cold | 0.029 | 0.322 | 0.093 | 0.380 | 14.1 |
| cv_to_jd | 27 | warm | 0.025 | 0.229 | 0.017 | 0.288 | 10.7 |
