# Nguồn dữ liệu Knowledge Base

Seed được dựng offline bằng `python -m kb.build_external`, chỉ từ snapshot trong `kb/sources/`. SHA-256 được kiểm tra trước khi dựng; MANIFEST.json ghi URL, phiên bản, ngày truy cập và giấy phép. Mỗi dòng mang `source`; phần trước dấu `:` khớp `prefix` trong manifest. Số liệu bên dưới đếm nguồn trực tiếp của từng dòng (không đếm lặp các nguồn bổ trợ).

## esco_occupations.json

ESCO, European Commission / European Union (https://esco.ec.europa.eu) — kỹ năng transversal và nhãn nghề ICT thuộc ISCO 25, 35; snapshot compact giữ nhãn, URI, loại và liên kết cần thiết từ API, không phải bản sao nguyên response; dùng cho skills, skill_aliases và job_titles.

Trích dẫn: **© European Union, ESCO**. Năm/phiên bản/revision: `v1.2.1`. URL: https://ec.europa.eu/esco/api. Truy cập: **2026-11-05**. Giấy phép: **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).

## esco_transversal.json

ESCO, European Commission / European Union (https://esco.ec.europa.eu) — kỹ năng transversal và nhãn nghề ICT thuộc ISCO 25, 35; snapshot compact giữ nhãn, URI, loại và liên kết cần thiết từ API, không phải bản sao nguyên response; dùng cho skills, skill_aliases và job_titles.

Trích dẫn: **© European Union, ESCO**. Năm/phiên bản/revision: `v1.2.1`. URL: https://ec.europa.eu/esco/api. Truy cập: **2026-11-05**. Giấy phép: **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).

## kb1_books.json

Prefix `book` — KB1: sách PDF Pro Git và Think Python; chỉ dữ kiện cấu trúc (tiêu đề, cây chương/mục, trang) và đếm nhắc tới kỹ năng KB2, không lưu đoạn văn. Dùng cho Neo4j: Book, Section, MENTIONS, RELATED_TO; không thêm vào CSV seed. RELATED_TO đếm đồng xuất hiện trong ít nhất 2 mục lá mỗi sách, không đếm lặp chương cha; khoảng trang mục bao gồm trang biên dùng chung. Tái dựng bằng `python -m kb.books`; PDF chỉ ở cache git-ignored, SHA-256 từng PDF ghi trong MANIFEST.

Trích dẫn: **Scott Chacon and Ben Straub (Pro Git); Allen B. Downey (Think Python)**. Năm/phiên bản/revision: `Pro Git 2.1.450; Think Python 2e`. URL: https://github.com/progit/progit2/releases/download/2.1.450/progit.pdf ; https://greenteapress.com/thinkpython2/thinkpython2.pdf. Truy cập: **2026-11-05**. Giấy phép: **CC BY-NC-SA 3.0 (Pro Git); CC BY-NC 3.0 (Think Python)** (https://creativecommons.org/licenses/by-nc-sa/3.0/ ; https://creativecommons.org/licenses/by-nc/3.0/).

## languages.yml

GitHub Linguist — alias của ngôn ngữ đã có trong skills; dùng cho skill_aliases, không thêm ngôn ngữ ngoài phạm vi khảo sát/gap-fill.

Trích dẫn: **GitHub, Inc. and Linguist contributors**. Năm/phiên bản/revision: `d456527fe93355baa28c3c29d542c97282b61bc7`. URL: https://raw.githubusercontent.com/github-linguist/linguist/d456527fe93355baa28c3c29d542c97282b61bc7/lib/linguist/languages.yml. Truy cập: **2026-11-05**. Giấy phép: **MIT** (https://opensource.org/license/mit).

## linguist_LICENSE

GitHub Linguist — alias của ngôn ngữ đã có trong skills; dùng cho skill_aliases, không thêm ngôn ngữ ngoài phạm vi khảo sát/gap-fill.

Trích dẫn: **GitHub, Inc. and Linguist contributors**. Năm/phiên bản/revision: `d456527fe93355baa28c3c29d542c97282b61bc7`. URL: https://raw.githubusercontent.com/github-linguist/linguist/d456527fe93355baa28c3c29d542c97282b61bc7/LICENSE. Truy cập: **2026-11-05**. Giấy phép: **MIT** (https://opensource.org/license/mit).

## official_vn_colleges.json

Trang chính thức của cơ sở đào tạo — chỉ trích tên trường từ title công khai và tên ngắn bằng bỏ tiền tố Cao đẳng; không sao chép nội dung bài, không khẳng định website có giấy phép mở. Fallback hẹp cho FPT Polytechnic khi không tìm thấy item Wikidata.

Trích dẫn: **FPT Polytechnic, official institution website**. Năm/phiên bản/revision: `Thu, 05 Nov 2026 08:10:18 GMT`. URL: https://caodang.fpt.edu.vn/. Truy cập: **2026-11-05**. Giấy phép: **Factual names only; website copyright retained** ().

## stackoverflow_2024_technology.json

Stack Overflow Developer Survey — lựa chọn công nghệ, tên chuẩn và câu hỏi phân nhóm; dùng cho skills, skill_aliases và ánh xạ categories.

Trích dẫn: **Stack Overflow Developer Survey 2024, Stack Exchange, Inc.**. Năm/phiên bản/revision: `2024`. URL: https://raw.githubusercontent.com/StackExchange/Survey/main/packages/archive/2024/json/technology.json. Truy cập: **2026-11-05**. Giấy phép: **ODbL 1.0 / DbCL 1.0** (https://opendatacommons.org/licenses/odbl/1-0/ ; https://opendatacommons.org/licenses/dbcl/1-0/).

## stackoverflow_2025_technology.json

Stack Overflow Developer Survey — lựa chọn công nghệ, tên chuẩn và câu hỏi phân nhóm; dùng cho skills, skill_aliases và ánh xạ categories.

Trích dẫn: **Stack Overflow Developer Survey 2025, Stack Exchange, Inc.**. Năm/phiên bản/revision: `2025`. URL: https://raw.githubusercontent.com/StackExchange/Survey/main/packages/archive/2025/json/technology.json. Truy cập: **2026-11-05**. Giấy phép: **ODbL 1.0 / DbCL 1.0** (https://opendatacommons.org/licenses/odbl/1-0/ ; https://opendatacommons.org/licenses/dbcl/1-0/).

## stackoverflow_2026_technology.json

Stack Overflow Developer Survey — lựa chọn công nghệ, tên chuẩn và câu hỏi phân nhóm; dùng cho skills, skill_aliases và ánh xạ categories.

Trích dẫn: **Stack Overflow Developer Survey 2026, Stack Exchange, Inc.**. Năm/phiên bản/revision: `2026`. URL: https://raw.githubusercontent.com/StackExchange/Survey/main/packages/archive/2026/json/technology.json. Truy cập: **2026-11-05**. Giấy phép: **ODbL 1.0 / DbCL 1.0** (https://opendatacommons.org/licenses/odbl/1-0/ ; https://opendatacommons.org/licenses/dbcl/1-0/).

## stackoverflow_tags.json

Stack Overflow tags (nội dung người dùng, CC BY-SA 4.0) — chỉ các tag đã phổ biến (≥ 500 câu hỏi) khớp từ vựng kỹ năng của CV tổng hợp mà khảo sát/Wikidata không có (ví dụ Spring MVC, Lombok, AutoMapper); tag và tag đồng nghĩa làm alias; nhóm để Other.

Trích dẫn: **Stack Overflow tags, Stack Exchange, Inc. and contributors**. Năm/phiên bản/revision: `2026-11-05`. URL: https://api.stackexchange.com/2.3/tags/{tags}/info ; https://api.stackexchange.com/2.3/tags/{tags}/synonyms. Truy cập: **2026-11-05**. Giấy phép: **CC BY-SA 4.0** (https://creativecommons.org/licenses/by-sa/4.0/).

## vn_universities.csv

Wikipedia tiếng Việt, cộng đồng biên tập viên và Wikimedia Foundation — bảng đại học/học viện và trường thành viên; tên chính thức tiếng Việt và tên khác trong bản trích dẫn; dùng cho universities và university_aliases. Bản trích dẫn theo CC BY-SA 4.0.

Trích dẫn: **Wikipedia tiếng Việt contributors**. Năm/phiên bản/revision: `75654510`. URL: https://vi.wikipedia.org/w/index.php?title=Danh_sách_trường_đại_học,_học_viện_và_cao_đẳng_tại_Việt_Nam&oldid=75654510. Truy cập: **2026-11-05**. Giấy phép: **CC BY-SA 4.0** (https://creativecommons.org/licenses/by-sa/4.0/).

## wikidata_classes.json

Wikidata, cộng đồng biên tập viên và Wikimedia Foundation — nhãn/alias en, vi, P1813, lớp P31/P279*, P277/P361/P527; dùng cho skills gap-fill, kỹ năng mềm, skill_aliases, skill_edges, universities và university_aliases.

Trích dẫn: **Wikidata contributors**. Năm/phiên bản/revision: `SPARQL class labels`. URL: https://query.wikidata.org/sparql. Truy cập: **2026-11-05**. Giấy phép: **CC0 1.0** (https://creativecommons.org/publicdomain/zero/1.0/).

## wikidata_entities.json

Wikidata, cộng đồng biên tập viên và Wikimedia Foundation — nhãn/alias en, vi, P1813, lớp P31/P279*, P277/P361/P527; dùng cho skills gap-fill, kỹ năng mềm, skill_aliases, skill_edges, universities và university_aliases.

Trích dẫn: **Wikidata contributors**. Năm/phiên bản/revision: `lastrevid recorded per entity`. URL: https://www.wikidata.org/w/api.php. Truy cập: **2026-11-05**. Giấy phép: **CC0 1.0** (https://creativecommons.org/publicdomain/zero/1.0/).

## wikidata_vn_universities.json

Wikidata, cộng đồng biên tập viên và Wikimedia Foundation — nhãn/alias en, vi, P1813, lớp P31/P279*, P277/P361/P527; dùng cho skills gap-fill, kỹ năng mềm, skill_aliases, skill_edges, universities và university_aliases.

Trích dẫn: **Wikidata contributors**. Năm/phiên bản/revision: `lastrevid recorded per entity`. URL: https://query.wikidata.org/sparql. Truy cập: **2026-11-05**. Giấy phép: **CC0 1.0** (https://creativecommons.org/publicdomain/zero/1.0/).

## Số dòng theo nguồn

| Nguồn | skills | skill_aliases | skill_edges | universities | university_aliases | job_titles | categories |
|---|---:|---:|---:|---:|---:|---:|---:|
| book | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| esco | 167 | 995 | 0 | 0 | 0 | 743 | 1 |
| institution | 0 | 0 | 0 | 1 | 2 | 0 | 0 |
| linguist | 0 | 35 | 0 | 0 | 0 | 0 | 0 |
| stackoverflow-2024 | 104 | 317 | 0 | 0 | 0 | 0 | 5 |
| stackoverflow-2025 | 56 | 47 | 0 | 0 | 0 | 0 | 0 |
| stackoverflow-2026 | 317 | 121 | 0 | 0 | 0 | 0 | 3 |
| stackoverflow-tags | 40 | 57 | 0 | 0 | 0 | 0 | 1 |
| wikidata | 129 | 712 | 132 | 104 | 848 | 0 | 6 |
| wikipedia | 0 | 0 | 0 | 282 | 409 | 0 | 0 |
| **Tổng** | 813 | 2284 | 132 | 387 | 1259 | 743 | 16 |

## Phương pháp và giới hạn

- Gộp công nghệ khảo sát 2024–2026; ưu tiên tên của năm mới nhất, chỉ đọc response của câu hỏi công nghệ được cho phép. Không dùng nhãn lát cắt/nhóm người trả lời; loại Other và các câu hỏi AIModels, LLM, CommPlatform, SOTags, BuildTool, Disruption, TechDropDown.
- Lựa chọn ghép HTML/CSS được tách thêm thành các entity Wikidata được chấp nhận trong survey_components; mỗi công nghệ có canonical/alias riêng. Tên đầy đủ và acronym trong ngoặc của lựa chọn khảo sát được giữ làm alias dẫn nguồn khảo sát.
- Categories giữ taxonomy của dự án (16 nhóm), ánh xạ từ loại câu hỏi khảo sát/lớp Wikidata và ESCO; không phải taxonomy chính thức của một nhà xuất bản. Cột source của categories dẫn đến một nguồn làm cơ sở ánh xạ (khảo sát, lớp Wikidata hoặc ESCO); nhóm chưa có skill dùng nguồn khảo sát tham chiếu. Không khẳng định nhãn nhóm do Stack Overflow xuất bản.
- Gap-fill: chỉ đếm nhãn skills/tech_stack trong data/clean/silver_dataset.jsonl và data/synth_v3/profiles/*.jsonl (hồ sơ tổng hợp/hư cấu). Gộp tần suất theo key chuẩn hóa trên các nguồn được phép, chỉ tra key xuất hiện ≥ 2 lần và không trùng tên khảo sát; thử tối đa 5 biến thể bề mặt phổ biến nhất. Không đọc data/real_test/ hoặc dataset/. Không lưu từ vựng đầu vào, CV hoặc dữ liệu cá nhân vào sources; chỉ lưu entity công khai được chấp nhận.
- Tìm wbsearchentities tiếng Anh, tối đa 5 ứng viên mỗi truy vấn; thử bỏ hậu tố JS/.js, tách dấu / và phần trong ngoặc. Danh sách thuật ngữ công khai trong yêu cầu nghiệm thu cũng được dùng làm truy vấn, không làm tri thức. Chỉ nhận tên khớp chính xác label/alias công khai và có bằng chứng SPARQL P31/P279* hoặc P279* thuộc lớp được phép; không dùng LLM để bù dữ liệu.
- Đọc nhãn en/vi và nhãn trung lập ngôn ngữ mul, bật languagefallback (nhiều tên sản phẩm đã chuyển sang mul). Tra thêm tên/alias chính xác và title enwiki trên Wikidata cho danh sách thuật ngữ công khai khi top 5 bị lấn bởi người/địa danh. Chỉ chuẩn hóa dấu câu khi so tên. Alias ghép tên với @scope/package được tách hai phần từ chính chuỗi công khai; không thêm tên thủ công.
- Lớp công nghệ được phép (TECH_CLASSES): Q7397 → Tool/Platform; Q9143 → Programming Language; Q271680 → Framework/Library; Q188860 → Framework/Library; Q176165 → Database; Q1330336 → Framework/Library; Q66747126 → Methodology/Concept; Q8366 → Methodology/Concept; Q9135 → Tool/Platform; Q483639 → Cloud; Q37045 → Programming Language; Q188267 → Methodology/Concept; Q846636 → Methodology/Concept; Q635346 → Methodology/Concept; Q181156 → Methodology/Concept; Q188522 → Testing/QA; Q317623 → Methodology/Concept; Q681263 → Methodology/Concept; Q494823 → Methodology/Concept; Q1378470 → Methodology/Concept; Q123370638 → Data/AI; Q235557 → Methodology/Concept; Q845739 → Programming Language; Q190686 → Methodology/Concept; Q190637 → Design/UI-UX; Q65938634 → Testing/QA.
- Q65938634 (quality control method) chỉ nhận khi P1269=Q950250 (test-driven development); không nhận trò chơi chỉ vì thuộc phần mềm. Kỹ năng mềm trùng nhãn chọn concept có nhiều sitelink nhất. Linker chuẩn hóa riêng Soft Skill tiếng Việt bằng bỏ từ nối theo và tiền tố danh hóa chủ nghĩa; chỉ nhận khi duy nhất một chủ sở hữu từ nguồn, không thêm dòng alias vào seed.
- Stack Overflow tags: với từ vựng gap-fill, thử các cách viết tag (dấu cách → '-', bỏ '-', '/', '.'), nhận tag có ≥ 500 câu hỏi, lấy tag đồng nghĩa; chỉ thêm skill khi key chưa thuộc nguồn khác. Tên hiển thị là cách viết thuật ngữ trong từ vựng tổng hợp đã khớp tag.
- Tên hiển thị: lựa chọn ghép của khảo sát (HTML/CSS) giữ đúng phần tên trong khảo sát; nhãn Wikidata viết thường được viết hoa chữ cái đầu (scrum → Scrum).
- Trường: sinh biến thể chính tả của tên đã công bố (Ho Chi Minh City ↔ HCMC/TP HCM, "Cao đẳng X" ↔ "X College"), cùng nguồn với tên gốc; không thêm tên mới.
- Quan hệ: P277 → REQUIRES chỉ với framework/library (theo lớp Wikidata VÀ nhóm trong KB; công cụ/nền tảng như Docker không sinh REQUIRES tới ngôn ngữ cài đặt); P361 → PART_OF; P527 → PART_OF đảo chiều. Chỉ giữ hai đầu có trong KB. Đây là quan hệ tri thức từ nguồn, không phải khẳng định ứng viên thành thạo công nghệ phụ thuộc.
- Loại 18 key alias skill mơ hồ (bỏ mọi chủ sở hữu); 17 key trường mơ hồ; 16 key nghề mơ hồ. Alias thông dụng như cake bị chặn. Loại 1 cạnh tự lặp/tạo chu trình theo thứ tự ổn định trên đồ thị hợp nhất.
- Trường đại học/cao đẳng: P17=Q881, P31/P279* thuộc university Q3918, academy Q38723, college Q189004, community college Q1336920, vocational school Q322563/Q2696153 hoặc academic institution Q4671277. Nhãn lớp được kiểm chứng bằng SPARQL trong wikidata_classes.json. Ghép duy nhất bằng tên đầy đủ vi/en hoặc phần trước dấu phẩy (bỏ đơn vị mẹ), không ghép riêng acronym. Bổ sung trường chưa khớp từ query; canonical vi rồi en; alias en/vi, P1813 và title enwiki/viwiki công khai trên Wikidata. university_alias_blocklist.csv là luật an toàn, không phải nguồn tri thức.
- ESCO không có nhãn tiếng Việt; Wikidata bổ sung nhãn/alias kỹ năng mềm en/vi. esco_matches ghép duy nhất QID với skill thành viên ESCO bằng label/alias công khai, chuẩn hóa hình thái danh từ/động từ (-ing/-ment/-s) và thứ tự token; không ghép nhóm skills-hierarchy. Hai nguồn dùng cùng canonical, không sinh skill trùng; concept chưa ghép là Soft Skill độc lập. Tên nghề gồm nhãn ưu tiên và nhãn thay thế tiếng Anh; một dòng cho mỗi alias duy nhất.
- Snapshot là các thời điểm độc lập; Wikidata có thể thay đổi/lỗi thời. Dựng offline tái lập từ manifest không cần truy cập dữ liệu tổng hợp. Fetch dùng cache SHA-256; --refresh để tải lại. Năm khảo sát không có sẽ được ghi unavailable trong manifest.
