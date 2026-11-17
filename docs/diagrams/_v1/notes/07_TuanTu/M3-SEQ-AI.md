# M3-SEQ-AI — Biểu đồ tuần tự chi tiết phía Dịch vụ AI (cv-matching-ai)

## 1. Giới thiệu và phạm vi

Biểu đồ tuần tự `M3-SEQ-AI` đặc tả chi tiết luồng tương tác nội bộ bên trong dịch vụ AI FastAPI (`cv-matching-ai`, cổng 8002) khi tiếp nhận và xử lý yêu cầu đối sánh độ phù hợp giữa CV ứng viên và bản mô tả công việc (JD) từ `recruitment-service` (cổng 8082).
Luồng này tương ứng trực tiếp với hành động **N10 ("Tính điểm và tạo giải thích tự động")** trong biểu đồ hoạt động `M3-ACT` (`diagrams/specs/02_HoatDong/M3-ACT.json`), được gọi qua API nội bộ `POST /match/no-llm`.

Các thành phần tham gia (Lifelines) gồm:
- `:Backend`: Đại diện cho `recruitment-service` (`CvMatchingModule.java`) đóng vai trò client bên ngoài gửi HTTP request.
- `:main`: Module điều phối chính và định tuyến FastAPI (`app/main.py`), tiếp nhận request và bọc xử lý lỗi.
- `:normalize`: Module chuẩn hóa dữ liệu đầu vào (`app/normalize.py`) làm sạch và tra cứu từ điển kỹ năng.
- `:extraction_adapter`: Module thích ứng cấu trúc CV từ bộ trích xuất (`app/extraction_adapter.py`).
- `:features`: Module trích xuất các đặc trưng đối sánh (`app/features.py`: kỹ năng, kinh nghiệm, học vấn, ngữ cảnh).
- `:graph`: Module đồ thị tri thức kỹ năng (`app/graph.py`), tra cứu khoảng cách và quan hệ trực tiếp giữa các nút kỹ năng.
- `:embeddings`: Module tính toán tương đồng ngữ nghĩa bằng embedding cosine similarity (`app/embeddings.py`).
- `:scoring`: Module kiểm tra trọng số và tính điểm số tổng hợp cuối cùng (`app/scoring.py`).

---

## 2. Kịch bản văn bản đánh số (khớp 1-1 với `seq`)

### Luồng chính (Seq 1 – 20): Đối sánh thành công (Dữ liệu và trọng số hợp lệ)

1. **seq 1 (`Backend` → `main`):** `:Backend` gửi yêu cầu HTTP `POST /match/no-llm` đến API route, kích hoạt hàm `match_without_llm(request)` với dữ liệu gồm thông tin ứng viên (`candidate`), công việc (`jd`), và trọng số tùy chọn (`weights`).
2. **seq 2 (`main` → `main`):** `match_without_llm` gọi hàm nội bộ `_run_match(request, use_llm=False)` để thực thi quy trình tính điểm không sử dụng mô hình ngôn ngữ lớn (LLM).
3. **seq 3 (`main` → `normalize`):** `_run_match` gọi `normalize_candidate(candidate)` để làm sạch và chuẩn hóa dữ liệu hồ sơ ứng viên.
4. **seq 4 (`normalize` → `extraction_adapter`):** `normalize_candidate` chuyển tiếp dữ liệu qua `adapt_candidate(candidate)` để chuyển đổi cấu trúc phân tích CV thành dạng phẳng chuẩn.
5. **seq 5 (`extraction_adapter` → `normalize`):** `adapt_candidate` hoàn tất chuyển đổi và trả về từ điển thông tin ứng viên đã thích ứng (`candidate`).
6. **seq 6 (`normalize` → `main`):** `normalize_candidate` tra cứu từ điển kỹ năng, chuẩn hóa danh sách kỹ năng, số năm kinh nghiệm, học vấn và trả về từ điển `candidate` đã chuẩn hóa cho `main`.
7. **seq 7 (`main` → `normalize`):** `_run_match` tiếp tục gọi `normalize_jd(jd)` để chuẩn hóa các yêu cầu của tin tuyển dụng.
8. **seq 8 (`normalize` → `main`):** `normalize_jd` trả về từ điển `jd` đã chuẩn hóa (kỹ năng yêu cầu, năm kinh nghiệm tối thiểu, trình độ học vấn, ngữ cảnh).
9. **seq 9 (`main` → `features`):** `_run_match` gọi `extract_features(candidate, jd)` để trích xuất và chấm điểm từng thành phần đặc trưng.
10. **seq 10 (`features` → `graph`):** Trong quá trình so khớp kỹ năng (`skill_match_details`), `features` gọi `default_skill_graph()` để lấy đồ thị tri thức kỹ năng.
11. **seq 11 (`graph` → `features`):** `graph` trả về thể hiện đồ thị tri thức NetworkX (`graph`).
12. **seq 12 (`features` → `embeddings`):** `features` gọi `cosine_similarity(left, right)` để đo khoảng cách ngữ nghĩa giữa các cặp kỹ năng, chức danh hoặc ngữ cảnh tóm tắt.
13. **seq 13 (`embeddings` → `features`):** `embeddings` trả về giá trị tương đồng ngữ nghĩa `similarity` (kiểu số thực từ 0.0 đến 1.0).
14. **seq 14 (`features` → `main`):** `extract_features` hoàn tất tổng hợp và trả về bộ ba `(scores, matched, missing)` gồm điểm từng đặc trưng, danh sách kỹ năng khớp và danh sách kỹ năng còn thiếu.
15. **seq 15 (`main` → `scoring`):** *(Bắt đầu nhánh `[Dữ liệu và trọng số hợp lệ]` của combined fragment `alt_scoring`)* `_run_match` gọi `validate_weights(weights)` để kiểm tra tính hợp lệ của trọng số cấu hình.
16. **seq 16 (`scoring` → `main`):** `validate_weights` xác nhận các trọng số không âm, có tổng dương và trả về từ điển `weights` hợp lệ.
17. **seq 17 (`main` → `scoring`):** `_run_match` gọi `compute_final_score(features, weights)` để tính điểm tổng hợp theo trọng số trên thang điểm 100.
18. **seq 18 (`scoring` → `main`):** `compute_final_score` trả về điểm số tổng hợp `score` (số thực làm tròn 2 chữ số thập phân).
19. **seq 19 (`main` → `main`):** `_run_match` đóng gói kết quả đối sánh (`score`, `matched_skills`, `missing_skills`, `reasoning`, `feature_scores`, `weights_used`, `processing_time_ms`) và trả về `result`.
20. **seq 20 (`main` → `Backend`):** `match_without_llm` trả về mã phản hồi HTTP `200 OK (result)` cho `:Backend`.

---

### Luồng ngoại lệ (Seq 21 – 24): Dữ liệu hoặc trọng số không hợp lệ

21. **seq 21 (`main` → `scoring`):** *(Nhánh `[Trọng số không hợp lệ hoặc sai dữ liệu (ValueError / TypeError / KeyError)]` của combined fragment `alt_scoring`)* `_run_match` gọi `validate_weights(weights)` khi trọng số chứa khóa lạ, giá trị âm hoặc tổng bằng 0 (hoặc dữ liệu đầu vào thiếu trường gây ra lỗi kiểu).
22. **seq 22 (`scoring` → `main`):** `validate_weights` phát hiện vi phạm ràng buộc và ném ngoại lệ `raise ValueError` ("unknown weight keys" hoặc "weights must be non-negative and have a positive total").
23. **seq 23 (`main` → `main`):** Khối `try...except` tại `_run_match` bắt ngoại lệ `(TypeError, ValueError, KeyError)` và chuyển đổi thành `raise HTTPException(status_code=422, detail=str(exc))`.
24. **seq 24 (`main` → `Backend`):** FastAPI hoàn tất xử lý ngoại lệ và trả về mã phản hồi HTTP `422 Unprocessable Entity` cho `:Backend`.

---

## 3. Bảng truy vết message → file:dòng

| Seq | Message / Thao tác | Từ (`from`) | Đến (`to`) | Loại (`kind`) | Nguồn truy vết (`src`) |
|:---:|---|---|---|:---:|---|
| 1 | `match_without_llm(request)` | `Backend` | `main` | `sync` | `source/recruit_system/services/cv-matching-ai/app/main.py:91` |
| 2 | `_run_match(request, use_llm)` | `main` | `main` | `self` | `source/recruit_system/services/cv-matching-ai/app/main.py:57` |
| 3 | `normalize_candidate(candidate)` | `main` | `normalize` | `sync` | `source/recruit_system/services/cv-matching-ai/app/normalize.py:44` |
| 4 | `adapt_candidate(candidate)` | `normalize` | `extraction_adapter` | `sync` | `source/recruit_system/services/cv-matching-ai/app/normalize.py:45` |
| 5 | `adapt_candidate: candidate` | `extraction_adapter` | `normalize` | `return` | `source/recruit_system/services/cv-matching-ai/app/extraction_adapter.py:40` |
| 6 | `normalize_candidate: candidate` | `normalize` | `main` | `return` | `source/recruit_system/services/cv-matching-ai/app/normalize.py:54` |
| 7 | `normalize_jd(jd)` | `main` | `normalize` | `sync` | `source/recruit_system/services/cv-matching-ai/app/normalize.py:67` |
| 8 | `normalize_jd: jd` | `normalize` | `main` | `return` | `source/recruit_system/services/cv-matching-ai/app/normalize.py:70` |
| 9 | `extract_features(candidate, jd)` | `main` | `features` | `sync` | `source/recruit_system/services/cv-matching-ai/app/features.py:111` |
| 10 | `default_skill_graph()` | `features` | `graph` | `sync` | `source/recruit_system/services/cv-matching-ai/app/features.py:31` |
| 11 | `default_skill_graph: graph` | `graph` | `features` | `return` | `source/recruit_system/services/cv-matching-ai/app/graph.py:74` |
| 12 | `cosine_similarity(left, right)` | `features` | `embeddings` | `sync` | `source/recruit_system/services/cv-matching-ai/app/features.py:70` |
| 13 | `cosine_similarity: similarity` | `embeddings` | `features` | `return` | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:66` |
| 14 | `extract_features: (scores, matched, missing)` | `features` | `main` | `return` | `source/recruit_system/services/cv-matching-ai/app/features.py:119` |
| 15 | `validate_weights(weights)` | `main` | `scoring` | `sync` | `source/recruit_system/services/cv-matching-ai/app/scoring.py:10` |
| 16 | `validate_weights: weights` | `scoring` | `main` | `return` | `source/recruit_system/services/cv-matching-ai/app/scoring.py:19` |
| 17 | `compute_final_score(features, weights)` | `main` | `scoring` | `sync` | `source/recruit_system/services/cv-matching-ai/app/scoring.py:22` |
| 18 | `compute_final_score: score` | `scoring` | `main` | `return` | `source/recruit_system/services/cv-matching-ai/app/scoring.py:25` |
| 19 | `_run_match: result` | `main` | `main` | `return` | `source/recruit_system/services/cv-matching-ai/app/main.py:80` |
| 20 | `match_without_llm: 200 OK (result)` | `main` | `Backend` | `return` | `source/recruit_system/services/cv-matching-ai/app/main.py:91` |
| 21 | `validate_weights(weights)` | `main` | `scoring` | `sync` | `source/recruit_system/services/cv-matching-ai/app/scoring.py:10` |
| 22 | `validate_weights: raise ValueError` | `scoring` | `main` | `return` | `source/recruit_system/services/cv-matching-ai/app/scoring.py:14` |
| 23 | `_run_match: raise HTTPException(status_code=422)` | `main` | `main` | `return` | `source/recruit_system/services/cv-matching-ai/app/main.py:82` |
| 24 | `match_without_llm: 422 Unprocessable Entity` | `main` | `Backend` | `return` | `source/recruit_system/services/cv-matching-ai/app/main.py:82` |

---

## 4. Ghi chú và đối chiếu với Biểu đồ hoạt động (`M3-ACT`)

1. **Khớp nối với bước N10:** Trong biểu đồ hoạt động `M3-ACT`, hành động **N10** ("Tính điểm và tạo giải thích tự động" thuộc swimlane `cv-matching-ai`) được mô tả mức tổng quát từ góc nhìn quy trình nghiệp vụ hệ thống. Biểu đồ tuần tự `M3-SEQ-AI` mở rộng chi tiết nội bộ của N10, thể hiện tuần tự từ khâu nhận HTTP request, chuẩn hóa dữ liệu, tra cứu đồ thị tri thức kỹ năng, tính tương đồng ngữ nghĩa, và chấm điểm đa tiêu chí.
2. **Khớp nối với quyết định N11:** Trong `M3-ACT`, sau N10 là quyết định **N11** ("AI trả kết quả hợp lệ?") do `recruitment-service` kiểm tra. Nếu AI trả về `200 OK` với dữ liệu hợp lệ (seq 20), luồng đi tiếp sang **N12** ("Lưu điểm và xếp hạng kết quả"). Nếu AI trả về lỗi `422 Unprocessable Entity` (seq 24), `recruitment-service` (`AiJsonClient`) ánh xạ thành ngoại lệ `BAD_GATEWAY` hoặc `INTERNAL_SERVER_ERROR`, kích hoạt nhánh ngoại lệ số 3 trong `M3-ACT` chuyển về node lỗi **N27 / N25**.
3. **Không gọi LLM:** Trong mã nguồn `main.py`, endpoint `/match/no-llm` kích hoạt `use_llm=False`. Do đó, module `explain.py` và các lệnh gọi OpenAI API không xuất hiện trong biểu đồ tuần tự này. Điều này hoàn toàn khớp với ghi chú số 4 trong `diagrams/notes/02_HoatDong/M3-ACT.md`.

---

## 5. Mâu thuẫn giữa tài liệu và mã nguồn

1. **Định danh Module:** Tài liệu `source/recruit_system/docs/Module3_Interview_Flow.md` gọi Module 3 là tính năng phỏng vấn luyện tập ("Interview Practice Flow"). Tuy nhiên, kiến trúc phân rã chính của hệ thống và bảng phân chia task của đồ án HireLens định nghĩa Module 3 (M3) là "Đối sánh, xem chi tiết việc, ứng tuyển". Dịch vụ AI cho module này là `services/cv-matching-ai/`.
2. **Cơ chế giải thích đối sánh:** Báo cáo đồ án ban đầu đề xuất sử dụng mô hình ngôn ngữ lớn (LLM) để sinh văn bản nhận xét ứng viên. Tuy nhiên, mã nguồn triển khai thực tế cho tính năng gợi ý việc làm của ứng viên chuyển sang gọi `/match/no-llm` để tối ưu chi phí và độ trễ, sinh giải thích dựa trên mẫu câu tất định (f-string) từ số lượng kỹ năng khớp/thiếu.

---

## 6. Open Questions (Vấn đề cần xác nhận)

1. `[cần xác nhận]` **Nguồn dữ liệu đồ thị tri thức:** Hiện tại `cv-matching-ai` nạp đồ thị kỹ năng từ tệp JSON tĩnh local (`data/kb_skill_graph.json`) và từ điển kỹ năng (`data/skills_dictionary.json`). Khi nhà tuyển dụng thêm kỹ năng mới vào CSDL `hirelens_recruitment`, đồ thị này chưa tự động cập nhật. Cần xác nhận xem có kế hoạch đồng bộ động dữ liệu kỹ năng giữa hai dịch vụ hay không?
2. `[cần xác nhận]` **Phân loại mã lỗi API AI:** Hàm `_run_match` gom tất cả các lỗi `(TypeError, ValueError, KeyError)` vào mã lỗi `422 Unprocessable Entity`. Cần xác nhận xem có nên phân tách lỗi tham số sai (ví dụ trọng số âm) thành `400 Bad Request` để `recruitment-service` có thể hiển thị cảnh báo tường minh hơn cho người dùng?
