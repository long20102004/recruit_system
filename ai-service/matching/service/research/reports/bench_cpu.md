# Đo thời gian match theo cỡ pool (S05)

- Thiết bị: `cpu`, 4 luồng torch · kho: 300 CV · rerank toàn bộ pool (K = N = n)
- `cold`: lần đầu với pool đó (cache token BERTScore chỉ ở RAM, chưa có) · `warm`: chạy lại ngay

| Luồng | n | Lần | Retrieve (s) | Rerank (s) | trong đó BERTScore (s) | Tổng (s) | ms / ứng viên |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| jd_to_cv | 10 | cold | 0.048 | 7.909 | 7.808 | 8.002 | 800.2 |
| jd_to_cv | 10 | warm | 0.058 | 0.142 | 0.019 | 0.251 | 25.1 |
| jd_to_cv | 50 | cold | 0.128 | 12.374 | 12.116 | 12.595 | 251.9 |
| jd_to_cv | 50 | warm | 0.068 | 0.245 | 0.043 | 0.359 | 7.2 |
| jd_to_cv | 100 | cold | 0.101 | 8.848 | 8.340 | 8.997 | 90.0 |
| jd_to_cv | 100 | warm | 0.080 | 0.495 | 0.120 | 0.618 | 6.2 |
| jd_to_cv | 200 | cold | 0.136 | 6.481 | 5.342 | 6.653 | 33.3 |
| jd_to_cv | 200 | warm | 0.142 | 1.332 | 0.201 | 1.514 | 7.6 |
| jd_to_cv | 300 | cold | 0.238 | 2.880 | 1.570 | 3.169 | 10.6 |
| jd_to_cv | 300 | warm | 0.210 | 1.307 | 0.363 | 1.576 | 5.3 |
| cv_to_jd | 27 | cold | 0.036 | 0.986 | 0.620 | 1.073 | 39.7 |
| cv_to_jd | 27 | warm | 0.056 | 0.394 | 0.033 | 0.500 | 18.5 |
