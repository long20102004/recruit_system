# M2-SEQ-AI — Trích xuất hồ sơ ứng viên từ CV bằng AI và Knowledge Graph (Dịch vụ AI FastAPI)

## Kịch bản theo message

1. `:Backend` (`recruitment-service`) gửi HTTP request `POST /api/v1/extract-cv?include=kg` kèm nội dung văn bản CV tới FastAPI router `routes.extract_cv`.
2. `routes` kiểm tra trạng thái nạp của mô hình LLM, làm sạch sơ bộ văn bản và gọi `generator.generate_cv_result` để kích hoạt luồng suy luận.
3. `generator` tự gọi `build_prompt` để render prompt chuyên dụng theo định dạng Jinja2/ChatML tương ứng phiên bản mô hình được cấu hình. **[Thành công: Suy luận hợp lệ, hậu xử lý và làm giàu tri thức]**
4. `generator` tự gọi `_generate_llama` để khởi chạy suy luận sinh chuỗi token qua engine `llama.cpp` (mô hình GGUF).
5. Trong quá trình nhận stream token, `generator` đẩy từng khối ký tự vào `LoopGuard.feed` để giám sát suy biến lặp chuỗi.
6. `LoopGuard` kiểm tra độ dài chuỗi và tần suất lặp lại giá trị, trả về `False` (chuỗi an toàn, không rơi vào vòng lặp vô hạn).
7. `_generate_llama` hoàn tất sinh chuỗi JSON, đóng gói vào `GenerationResult` và trả về cho `routes`.
8. `routes` gọi `json_parse.extract_json` để loại bỏ thẻ `<think>`, gọt bỏ markdown code block và bóc tách khối JSON.
9. `json_parse` phân tích chuỗi thành cấu trúc từ điển `dict` hoàn chỉnh và trả về cho `routes`.
10. `routes` gọi `pipeline.postprocess` để thực thi đường ống hậu xử lý: làm sạch tên trường, ép kiểu dữ liệu, đối soát văn bản gốc chống ảo giác và sắp xếp mốc thời gian.
11. `pipeline` hoàn thành hậu xử lý, trả về bộ đôi gồm hồ sơ đã làm sạch và đối tượng thống kê `(dict, PostprocessStats)` cho `routes`.
12. `routes` gọi `enrich.enrich` để đối soát với đồ thị tri thức `KnowledgeBase`, suy diễn các kỹ năng ngầm định (`implied_skills`) và sinh cờ cảnh báo (`flags`).
13. `enrich` hoàn tất suy diễn tri thức trên đồ thị, trả về từ điển chứa các trường làm giàu cho `routes`.
14. `routes` gọi `normalize.normalize_profile_with_kb` để chuẩn hóa danh sách kỹ năng và tên cơ sở đào tạo sang danh mục chuẩn.
15. `normalize` hoàn tất chuẩn hóa thực thể, trả về từ điển hồ sơ chuẩn hóa cho `routes`.
16. `routes` tổng hợp các trường dữ liệu, đóng gói vào mô hình Pydantic `CVResponse` và trả về phản hồi HTTP 200 cho `:Backend`.
17. Mô hình LLM sinh ra nội dung bị lỗi cú pháp, rỗng hoặc bị ngắt cụt không thể khôi phục; `generator` trả về `GenerationResult` chứa chuỗi văn bản lỗi. **[Ngoại lệ: Mô hình sinh JSON lỗi cú pháp hoặc rỗng (ModelOutputError)]**
18. `routes` gọi `json_parse.extract_json` để phân tích kết quả chuỗi thô.
19. `json_parse` không thể phân tích cú pháp hoặc không tìm thấy đối tượng JSON hợp lệ, phát sinh ngoại lệ `ValueError` trả về cho `routes`.
20. `routes` bắt lỗi, nâng cấp thành `ModelOutputError` và chuyển đổi thành phản hồi HTTP 502 Bad Gateway trả về cho `:Backend`.
21. Trong quá trình chuẩn bị suy luận, `generator` tự gọi `count_prompt_tokens` để tính toán chính xác số lượng token của prompt đầu vào. **[Ngoại lệ: Độ dài prompt vượt quá giới hạn ngữ cảnh (InputTooLongError)]**
22. Số lượng token vượt quá ngân sách ngữ cảnh cho phép (`context_tokens - MAX_NEW_TOKENS`); `generator` ném ngoại lệ `InputTooLongError` trả về cho `routes`.
23. `routes` bắt ngoại lệ `InputTooLongError`, đóng gói chi tiết lỗi và trả về phản hồi HTTP 413 Payload Too Large cho `:Backend`.

---

## Truy vết message → file:dòng

| Seq | Message | Nguồn truy vết |
|---:|---|---|
| 1 | `backend` → `routes.extract_cv(request, response, include)` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:64` |
| 2 | `routes` → `generator.generate_cv_result(cv_text)` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:100` |
| 3 | `generator` → `generator.build_prompt(cv_text)` | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:217` |
| 4 | `generator` → `generator._generate_llama(prompt, max_tokens, prefix, continue_output)` | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:230` |
| 5 | `generator` → `loop_guard.feed(chunk)` | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:84` |
| 6 | `loop_guard` → `generator.feed: bool` | `source/recruit_system/services/cv-extraction-ai/app/services/loop_guard.py:27` |
| 7 | `generator` → `routes.generate_cv_result: GenerationResult` | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:115` |
| 8 | `routes` → `json_parse.extract_json(text)` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:110` |
| 9 | `json_parse` → `routes.extract_json: dict` | `source/recruit_system/services/cv-extraction-ai/app/utils/json_parse.py:42` |
| 10 | `routes` → `pipeline.postprocess(data, cv_text)` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:121` |
| 11 | `pipeline` → `routes.postprocess: tuple[dict, PostprocessStats]` | `source/recruit_system/services/cv-extraction-ai/app/postprocess/pipeline.py:57` |
| 12 | `routes` → `enrich.enrich(profile, kb, pp_stats, cv_text)` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:138` |
| 13 | `enrich` → `routes.enrich: dict` | `source/recruit_system/services/cv-extraction-ai/app/kg/enrich.py:94` |
| 14 | `routes` → `normalize.normalize_profile_with_kb(profile, kb)` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:160` |
| 15 | `normalize` → `routes.normalize_profile_with_kb: dict` | `source/recruit_system/services/cv-extraction-ai/app/kb/normalize.py:50` |
| 16 | `routes` → `backend.extract_cv: CVResponse` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:192` |
| 17 | `generator` → `routes.generate_cv_result: GenerationResult (text rỗng/lỗi)` | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:115` |
| 18 | `routes` → `json_parse.extract_json(text)` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:110` |
| 19 | `json_parse` → `routes.extract_json: ValueError` | `source/recruit_system/services/cv-extraction-ai/app/utils/json_parse.py:42` |
| 20 | `routes` → `backend.extract_cv: HTTP 502 Bad Gateway` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:211` |
| 21 | `generator` → `generator.count_prompt_tokens(prompt)` | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:223` |
| 22 | `generator` → `routes.generate_cv_result: InputTooLongError` | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:227` |
| 23 | `routes` → `backend.extract_cv: HTTP 413 Payload Too Large` | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:200` |

---

## Đối chiếu hoạt động và mâu thuẫn

- **Phạm vi biểu đồ:** Biểu đồ hoạt động `M2-ACT` mô tả tổng thể cả 4 swimlane (Người dùng, Frontend, recruitment-service, cv-extraction-ai); tại swimlane AI, hoạt động được tóm tắt trong một hành động duy nhất là `N10` ("Trích xuất JSON bằng LLM và làm giàu qua Knowledge Graph") cùng quyết định `N11` ("AI phản hồi dữ liệu trích xuất hợp lệ?"). Biểu đồ tuần tự `M2-SEQ-AI` đi sâu vào chi tiết các bước bên trong `cv-extraction-ai`: tiền xử lý prompt, giám sát vòng lặp với `LoopGuard`, bóc tách JSON, đường ống hậu xử lý chống ảo giác, suy diễn đồ thị tri thức và chuẩn hóa thực thể.
- **Xử lý ngoại lệ:** Biểu đồ tuần tự làm rõ hai ngoại lệ nghiệp vụ chính được ghi nhận trong `M2-ACT.md` (mục Ngoại lệ 4):
  1. `ModelOutputError`: Xảy ra khi mô hình sinh chuỗi không phân tích được cú pháp JSON hoặc đối tượng kết quả rỗng không có nội dung hữu ích (`_has_content == False`). Dịch vụ AI chuyển đổi thành mã lỗi `HTTP 502 Bad Gateway`.
  2. `InputTooLongError`: Xảy ra khi văn bản CV có số token vượt quá ngân sách ngữ cảnh của mô hình. Dịch vụ AI chuyển đổi thành mã lỗi `HTTP 413 Payload Too Large`.
  3. Lỗi `503 Service Unavailable` xảy ra khi mô hình chưa hoàn tất nạp trọng số (`state.engine is None`) hoặc hàng đợi inference bị nghẽn (`ModelBusyError`), được bảo vệ ngay tại đầu hàm `routes.extract_cv`.
- **Nhất quán với biểu đồ lớp chi tiết M2-CLS-AI:** Mọi lifeline kiểu `object` đều ánh xạ trực tiếp sang các lớp/module tương ứng trong `M2-CLS-AI.json` (`routes`, `generator`, `LoopGuard`, `json_parse`, `pipeline`, `enrich`, `normalize`). Mọi thông điệp gọi phương thức đều có tên hàm và danh sách tham số thật khớp 100% với chữ ký phương thức đã khai báo.
- **Tài liệu và mã nguồn:** Tài liệu trong repo `source/recruit_system/docs/Module3_Interview_Flow.md` chỉ đặc tả module phỏng vấn AI (Module 3); toàn bộ logic của dịch vụ `cv-extraction-ai` được phân tích trực tiếp từ mã nguồn triển khai thực tế tại thư mục `source/recruit_system/services/cv-extraction-ai/`.

---

## Cần xác nhận

- [cần xác nhận] Trong luồng suy luận GGUF bằng `llama.cpp`, hàm `_continue_llama` có cơ chế tự động kích hoạt lượt suy luận thứ hai (`continuation`) nếu phát hiện cắt cụt (`truncated`). Hiện tại biểu đồ tuần tự đã rút gọn và thể hiện chu trình suy luận đại diện qua `feed` của `LoopGuard` để đảm bảo giới hạn số message (<= 26), có cần bổ sung một biểu đồ chi tiết riêng biệt cho thuật toán multi-turn continuation hay không?
- [cần xác nhận] Việc làm giàu tri thức bằng Knowledge Graph (`enrich` và `normalize`) phụ thuộc vào tham số `include=kg` từ `recruitment-service`; khi gọi không có tham số này, nhánh `enrich` được bỏ qua và `normalize` chỉ chạy chuẩn hóa cơ bản. Đồ án có kế hoạch luôn bật mặc định tính năng làm giàu KG trên toàn bộ môi trường hay không?