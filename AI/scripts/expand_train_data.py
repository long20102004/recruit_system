#!/usr/bin/env python3
"""Expand intern/fresher CNTT interview dataset for real training (~800+ answers)."""

from __future__ import annotations

import csv
import json
import random
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q_PATH = ROOT / "data" / "questions.json"
A_PATH = ROOT / "data" / "answers.csv"

random.seed(42)

NEW_QUESTIONS = [
    {
        "id": "java-03",
        "track": "backend",
        "topic": "Java",
        "skill": "Exception",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Checked exception và unchecked exception trong Java khác nhau thế nào?",
        "reference_answer": "Checked exception bắt buộc xử lý hoặc khai báo throws lúc compile (IOException). Unchecked (RuntimeException và subclass) không bắt buộc try-catch (NullPointerException, IllegalArgumentException). Checked thường cho lỗi Recoverable bên ngoài; unchecked thường do bug logic.",
        "criteria": [
            {"key": "checked", "label": "Checked: compile bắt buộc xử lý", "weight": 0.35, "hints": ["checked", "compile", "throws", "try-catch", "ioexception"]},
            {"key": "unchecked", "label": "Unchecked / RuntimeException", "weight": 0.35, "hints": ["unchecked", "runtime", "nullpointer", "không bắt buộc"]},
            {"key": "when", "label": "Khi nào dùng / ý nghĩa", "weight": 0.3, "hints": ["recoverable", "bug", "lỗi logic", "khi nào"]},
        ],
    },
    {
        "id": "java-04",
        "track": "backend",
        "topic": "Java",
        "skill": "equals/hashCode",
        "difficulty": "Trung bình",
        "rank": ["fresher"],
        "question": "Tại sao cần override equals() và hashCode() cùng nhau?",
        "reference_answer": "equals so sánh logic bằng nhau theo nghiệp vụ. hashCode dùng trong HashMap/HashSet. Hợp đồng Java: hai object equals thì phải cùng hashCode. Override một cái mà không cái kia gây lỗi chứa trùng hoặc không tìm thấy trong collection dựa hash.",
        "criteria": [
            {"key": "equals", "label": "equals: so sánh logic", "weight": 0.3, "hints": ["equals", "so sánh", "bằng nhau"]},
            {"key": "hashcode", "label": "hashCode: HashMap/HashSet", "weight": 0.3, "hints": ["hashcode", "hashmap", "hashset", "hash"]},
            {"key": "contract", "label": "Hợp đồng equals-hashCode", "weight": 0.4, "hints": ["cùng hash", "hợp đồng", "override cả hai", "contract"]},
        ],
    },
    {
        "id": "java-05",
        "track": "backend",
        "topic": "Java",
        "skill": "String vs StringBuilder",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "String và StringBuilder khác nhau thế nào? Khi nào dùng StringBuilder?",
        "reference_answer": "String là immutable: mỗi thao tác nối tạo object mới. StringBuilder mutable, nối chuỗi hiệu quả trong vòng lặp. Dùng StringBuilder khi xây chuỗi động nhiều lần; String đủ khi chuỗi ít thay đổi hoặc cần thread-safe immutability.",
        "criteria": [
            {"key": "immutable", "label": "String immutable", "weight": 0.35, "hints": ["immutable", "không đổi", "object mới", "string"]},
            {"key": "mutable", "label": "StringBuilder mutable / nhanh hơn", "weight": 0.35, "hints": ["stringbuilder", "mutable", "nối", "hiệu năng", "vòng lặp"]},
            {"key": "when", "label": "Khi nào dùng", "weight": 0.3, "hints": ["khi nào", "nối nhiều", "động"]},
        ],
    },
    {
        "id": "sb-06",
        "track": "backend",
        "topic": "Spring Boot",
        "skill": "application.properties",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "application.properties / application.yml dùng để làm gì? Cho ví dụ cấu hình phổ biến.",
        "reference_answer": "File cấu hình externalize settings: port server, datasource URL/username/password, logging level, profile. Có thể dùng .properties hoặc .yml. Ví dụ server.port=8080, spring.datasource.url=..., logging.level.root=INFO. Profile (dev/prod) giúp tách cấu hình môi trường.",
        "criteria": [
            {"key": "purpose", "label": "Externalize cấu hình", "weight": 0.35, "hints": ["cấu hình", "properties", "yml", "external"]},
            {"key": "examples", "label": "Ví dụ port/datasource/logging", "weight": 0.4, "hints": ["port", "datasource", "url", "logging", "password"]},
            {"key": "profile", "label": "Profile môi trường", "weight": 0.25, "hints": ["profile", "dev", "prod", "môi trường"]},
        ],
    },
    {
        "id": "sb-07",
        "track": "backend",
        "topic": "Spring",
        "skill": "Bean / Component",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "@Component, @Service, @Repository khác nhau thế nào?",
        "reference_answer": "Cả ba đều là stereotype để Spring quét và tạo bean. @Component là generic. @Service đánh dấu lớp nghiệp vụ. @Repository đánh dấu lớp truy cập dữ liệu, còn giúp dịch persistence exception. Về kỹ thuật gần giống nhau; đặt đúng stereotype giúp đọc code và AOP/exception rõ hơn.",
        "criteria": [
            {"key": "all_beans", "label": "Đều tạo bean / stereotype", "weight": 0.3, "hints": ["bean", "stereotype", "component scan", "quét"]},
            {"key": "service", "label": "@Service: business", "weight": 0.25, "hints": ["service", "nghiệp vụ", "business"]},
            {"key": "repo", "label": "@Repository: data access", "weight": 0.25, "hints": ["repository", "data", "persistence", "dao"]},
            {"key": "why", "label": "Ý nghĩa phân tầng", "weight": 0.2, "hints": ["tầng", "rõ ràng", "đọc code", "aop"]},
        ],
    },
    {
        "id": "sb-08",
        "track": "backend",
        "topic": "Spring Web",
        "skill": "DTO / Entity",
        "difficulty": "Trung bình",
        "rank": ["fresher"],
        "question": "Tại sao API thường trả DTO thay vì trả trực tiếp Entity JPA?",
        "reference_answer": "DTO tách contract API khỏi schema DB, tránh lộ field nội bộ/quan hệ lazy, giảm vòng lặp JSON (bidirectional), cho phép shape khác Entity. Entity gắn persistence; DTO ổn định cho client. Mapping thủ công hoặc MapStruct.",
        "criteria": [
            {"key": "decouple", "label": "Tách API khỏi DB schema", "weight": 0.3, "hints": ["tách", "contract", "schema", "api"]},
            {"key": "security_lazy", "label": "Tránh lộ field / lazy load", "weight": 0.35, "hints": ["lazy", "lộ", "password", "quan hệ", "json"]},
            {"key": "shape", "label": "Shape phù hợp client", "weight": 0.35, "hints": ["dto", "mapstruct", "client", "response"]},
        ],
    },
    {
        "id": "sql-03",
        "track": "database",
        "topic": "SQL",
        "skill": "PRIMARY / FOREIGN KEY",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "PRIMARY KEY và FOREIGN KEY dùng để làm gì?",
        "reference_answer": "PRIMARY KEY định danh duy nhất mỗi dòng, thường NOT NULL và unique. FOREIGN KEY tham chiếu PK/unique của bảng khác để đảm bảo toàn vẹn tham chiếu: không tạo quan hệ tới bản ghi không tồn tại, hỗ trợ cascade khi cần.",
        "criteria": [
            {"key": "pk", "label": "PK: định danh unique", "weight": 0.4, "hints": ["primary", "unique", "định danh", "not null"]},
            {"key": "fk", "label": "FK: tham chiếu bảng khác", "weight": 0.4, "hints": ["foreign", "tham chiếu", "quan hệ", "bảng khác"]},
            {"key": "integrity", "label": "Toàn vẹn dữ liệu", "weight": 0.2, "hints": ["toàn vẹn", "integrity", "cascade"]},
        ],
    },
    {
        "id": "sql-04",
        "track": "database",
        "topic": "SQL",
        "skill": "GROUP BY / HAVING",
        "difficulty": "Trung bình",
        "rank": ["intern", "fresher"],
        "question": "GROUP BY dùng khi nào? HAVING khác WHERE thế nào?",
        "reference_answer": "GROUP BY gom nhóm dòng theo cột để dùng hàm tổng hợp (COUNT, SUM, AVG). WHERE lọc dòng trước khi gom nhóm; HAVING lọc sau khi gom (điều kiện trên aggregate). Ví dụ: đếm đơn theo khách, rồi HAVING COUNT(*) > 5.",
        "criteria": [
            {"key": "groupby", "label": "GROUP BY + aggregate", "weight": 0.35, "hints": ["group by", "count", "sum", "avg", "gom"]},
            {"key": "where", "label": "WHERE lọc trước group", "weight": 0.3, "hints": ["where", "trước", "lọc dòng"]},
            {"key": "having", "label": "HAVING lọc sau aggregate", "weight": 0.35, "hints": ["having", "sau", "aggregate", "count"]},
        ],
    },
    {
        "id": "sql-05",
        "track": "database",
        "topic": "SQL",
        "skill": "Transaction ACID",
        "difficulty": "Trung bình",
        "rank": ["fresher"],
        "question": "Transaction trong database là gì? Nêu ngắn gọn ACID.",
        "reference_answer": "Transaction là nhóm thao tác xem như một đơn vị: thành công hết hoặc rollback. ACID: Atomicity (tất cả hoặc không), Consistency (DB nhất quán theo rule), Isolation (giao dịch song song ít ảnh hưởng lẫn), Durability (commit rồi bền vững).",
        "criteria": [
            {"key": "tx", "label": "Định nghĩa transaction", "weight": 0.25, "hints": ["transaction", "commit", "rollback", "đơn vị"]},
            {"key": "acid", "label": "ACID đủ ý", "weight": 0.5, "hints": ["atomic", "consist", "isolat", "durab", "acid"]},
            {"key": "example", "label": "Hiểu áp dụng", "weight": 0.25, "hints": ["chuyển tiền", "ví dụ", "all or nothing"]},
        ],
    },
    {
        "id": "http-02",
        "track": "general_cs",
        "topic": "HTTP / REST",
        "skill": "Idempotent",
        "difficulty": "Trung bình",
        "rank": ["fresher"],
        "question": "Idempotent trong HTTP nghĩa là gì? Method nào thường idempotent?",
        "reference_answer": "Idempotent: gọi nhiều lần cùng request cho kết quả giống như gọi một lần (về phía resource). GET, PUT, DELETE thường idempotent; POST thường không (mỗi lần có thể tạo thêm). Hữu ích khi retry mạng lỗi.",
        "criteria": [
            {"key": "def", "label": "Định nghĩa idempotent", "weight": 0.4, "hints": ["idempotent", "nhiều lần", "cùng kết quả", "một lần"]},
            {"key": "methods", "label": "GET/PUT/DELETE vs POST", "weight": 0.4, "hints": ["get", "put", "delete", "post"]},
            {"key": "why", "label": "Retry / an toàn", "weight": 0.2, "hints": ["retry", "mạng", "an toàn"]},
        ],
    },
    {
        "id": "http-03",
        "track": "general_cs",
        "topic": "HTTP",
        "skill": "Status & headers",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "HTTP status code và header dùng để làm gì? Cho ví dụ header phổ biến.",
        "reference_answer": "Status code báo kết quả xử lý request (2xx/4xx/5xx). Header mang metadata: Content-Type, Authorization, Cache-Control, Set-Cookie. Client/server dựa vào status + header để xử lý đúng (parse JSON, gắn token, cache).",
        "criteria": [
            {"key": "status", "label": "Status: kết quả request", "weight": 0.35, "hints": ["status", "2xx", "4xx", "5xx", "mã"]},
            {"key": "header", "label": "Header: metadata", "weight": 0.35, "hints": ["header", "content-type", "authorization", "cookie"]},
            {"key": "example", "label": "Ví dụ dùng", "weight": 0.3, "hints": ["token", "json", "cache", "ví dụ"]},
        ],
    },
    {
        "id": "fe-03",
        "track": "frontend",
        "topic": "JavaScript",
        "skill": "var/let/const",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "var, let, const trong JavaScript khác nhau thế nào?",
        "reference_answer": "var có function scope, có hoisting dễ gây lỗi. let/const có block scope. const không cho gán lại binding (object vẫn mutate được). Nên dùng const mặc định, let khi cần gán lại, tránh var trong code mới.",
        "criteria": [
            {"key": "scope", "label": "var function vs let/const block", "weight": 0.4, "hints": ["scope", "block", "function", "var", "let"]},
            {"key": "const", "label": "const không gán lại", "weight": 0.3, "hints": ["const", "không gán lại", "immutable binding"]},
            {"key": "practice", "label": "Best practice", "weight": 0.3, "hints": ["nên dùng", "tránh var", "const mặc định"]},
        ],
    },
    {
        "id": "fe-04",
        "track": "frontend",
        "topic": "JavaScript",
        "skill": "DOM / Event",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "DOM là gì? Event listener dùng để làm gì?",
        "reference_answer": "DOM là mô hình cây đại diện tài liệu HTML để JS đọc/sửa phần tử. Event listener đăng ký hàm chạy khi có sự kiện (click, submit, input). Giúp trang tương tác: validate form, gọi API, đổi UI khi user thao tác.",
        "criteria": [
            {"key": "dom", "label": "DOM: cây HTML", "weight": 0.4, "hints": ["dom", "cây", "html", "phần tử", "document"]},
            {"key": "event", "label": "Event listener", "weight": 0.35, "hints": ["event", "listener", "click", "addeventlistener"]},
            {"key": "usecase", "label": "Tương tác UI", "weight": 0.25, "hints": ["form", "tương tác", "ui", "api"]},
        ],
    },
    {
        "id": "fe-05",
        "track": "frontend",
        "topic": "React",
        "skill": "useEffect / hooks",
        "difficulty": "Trung bình",
        "rank": ["fresher"],
        "question": "useState và useEffect trong React dùng khi nào?",
        "reference_answer": "useState lưu state local và kích hoạt re-render khi đổi. useEffect chạy side effect sau render: fetch API, subscribe, cập nhật document title; dependency array kiểm soát lần chạy. Không đặt side effect trực tiếp trong body render.",
        "criteria": [
            {"key": "usestate", "label": "useState: state + re-render", "weight": 0.35, "hints": ["usestate", "state", "re-render"]},
            {"key": "useeffect", "label": "useEffect: side effect", "weight": 0.4, "hints": ["useeffect", "fetch", "side effect", "dependency"]},
            {"key": "deps", "label": "Dependency array", "weight": 0.25, "hints": ["dependency", "deps", "mảng phụ thuộc", "[]"]},
        ],
    },
    {
        "id": "fe-06",
        "track": "frontend",
        "topic": "CSS",
        "skill": "Box model / Flex",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "CSS box model gồm gì? Flexbox giải quyết bài toán gì?",
        "reference_answer": "Box model: content, padding, border, margin. Hiểu box model để tính kích thước layout đúng. Flexbox bố trí phần tử theo một chiều (row/column), căn chỉnh khoảng cách dễ dàng, phù hợp navbar, card hàng, căn giữa — giảm float/hack cũ.",
        "criteria": [
            {"key": "box", "label": "content/padding/border/margin", "weight": 0.4, "hints": ["content", "padding", "border", "margin", "box model"]},
            {"key": "flex", "label": "Flexbox layout 1 chiều", "weight": 0.4, "hints": ["flex", "flexbox", "row", "column", "căn"]},
            {"key": "usecase", "label": "Navbar / căn chỉnh", "weight": 0.2, "hints": ["navbar", "card", "căn giữa", "layout"]},
        ],
    },
    {
        "id": "qa-04",
        "track": "tester_qa",
        "topic": "Software Testing",
        "skill": "Test levels",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Unit test, integration test và system test khác nhau thế nào?",
        "reference_answer": "Unit test kiểm tra đơn vị nhỏ (hàm/class) isolat, nhanh. Integration test kiểm tra tương tác giữa module/API/DB. System/E2E kiểm tra toàn hệ theo luồng người dùng. Kim tự tháp: nhiều unit, ít hơn integration, ít E2E vì chậm/flaky.",
        "criteria": [
            {"key": "unit", "label": "Unit: đơn vị nhỏ", "weight": 0.3, "hints": ["unit", "hàm", "class", "isolate"]},
            {"key": "integration", "label": "Integration: giữa module", "weight": 0.3, "hints": ["integration", "api", "db", "tương tác"]},
            {"key": "system", "label": "System/E2E", "weight": 0.25, "hints": ["system", "e2e", "end to end", "luồng"]},
            {"key": "pyramid", "label": "Test pyramid", "weight": 0.15, "hints": ["pyramid", "nhiều unit", "ít e2e"]},
        ],
    },
    {
        "id": "qa-05",
        "track": "tester_qa",
        "topic": "Software Testing",
        "skill": "Equivalence / Boundary",
        "difficulty": "Trung bình",
        "rank": ["intern", "fresher"],
        "question": "Equivalence partitioning và boundary value analysis là gì?",
        "reference_answer": "Equivalence partitioning chia input thành lớp tương đương, chọn đại diện mỗi lớp để giảm số case. Boundary value chọn giá trị biên (min, min±1, max) vì lỗi hay nằm ở biên. Hai kỹ thuật black-box bổ sung khi thiết kế test data.",
        "criteria": [
            {"key": "ep", "label": "Equivalence partitioning", "weight": 0.4, "hints": ["equivalence", "phân lớp", "đại diện", "tương đương"]},
            {"key": "bva", "label": "Boundary value", "weight": 0.4, "hints": ["boundary", "biên", "min", "max"]},
            {"key": "why", "label": "Giảm case / bắt lỗi biên", "weight": 0.2, "hints": ["giảm", "lỗi biên", "test data"]},
        ],
    },
    {
        "id": "qa-06",
        "track": "tester_qa",
        "topic": "Software Testing",
        "skill": "Severity vs Priority",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Severity và Priority của bug khác nhau thế nào?",
        "reference_answer": "Severity đo mức ảnh hưởng kỹ thuật tới hệ thống (crash = high). Priority đo độ ưu tiên sửa theo nghiệp vụ/release (lỗi logo trang chủ có thể priority cao dù severity thấp). QA đề xuất severity; PO/PM thường quyết priority.",
        "criteria": [
            {"key": "severity", "label": "Severity: ảnh hưởng kỹ thuật", "weight": 0.4, "hints": ["severity", "ảnh hưởng", "crash", "nghiêm trọng"]},
            {"key": "priority", "label": "Priority: thứ tự sửa", "weight": 0.4, "hints": ["priority", "ưu tiên", "release", "business"]},
            {"key": "example", "label": "Ví dụ phân biệt", "weight": 0.2, "hints": ["ví dụ", "logo", "khác nhau"]},
        ],
    },
    {
        "id": "qa-07",
        "track": "tester_qa",
        "topic": "API Testing",
        "skill": "API test basics",
        "difficulty": "Trung bình",
        "rank": ["fresher"],
        "question": "Khi test API REST, bạn thường kiểm tra những gì?",
        "reference_answer": "Kiểm tra status code, body schema/field, business rule, header (content-type/auth), lỗi input invalid, auth/unauthorized, performance cơ bản. Dùng Postman/curl hoặc automation. So expected vs actual và cover positive/negative cases.",
        "criteria": [
            {"key": "status_body", "label": "Status + body/schema", "weight": 0.35, "hints": ["status", "body", "schema", "json"]},
            {"key": "neg_auth", "label": "Negative / auth", "weight": 0.35, "hints": ["negative", "invalid", "401", "auth", "unauthorized"]},
            {"key": "tools", "label": "Tool / expected-actual", "weight": 0.3, "hints": ["postman", "curl", "expected", "actual"]},
        ],
    },
    {
        "id": "git-02",
        "track": "general_cs",
        "topic": "Git",
        "skill": "pull / push / clone",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "git clone, pull và push khác nhau thế nào?",
        "reference_answer": "clone sao chép repo remote về máy lần đầu. pull lấy thay đổi mới từ remote về nhánh hiện tại (fetch+merge/rebase). push đẩy commit local lên remote để chia sẻ. Làm việc nhóm cần pull trước khi push để giảm conflict.",
        "criteria": [
            {"key": "clone", "label": "clone: copy repo", "weight": 0.3, "hints": ["clone", "sao chép", "lần đầu"]},
            {"key": "pull", "label": "pull: lấy về", "weight": 0.35, "hints": ["pull", "fetch", "lấy về", "cập nhật"]},
            {"key": "push", "label": "push: đẩy lên", "weight": 0.35, "hints": ["push", "đẩy", "remote", "chia sẻ"]},
        ],
    },
    {
        "id": "git-03",
        "track": "general_cs",
        "topic": "Git",
        "skill": "Conflict",
        "difficulty": "Trung bình",
        "rank": ["intern", "fresher"],
        "question": "Merge conflict là gì? Cách xử lý cơ bản?",
        "reference_answer": "Conflict xảy ra khi hai nhánh sửa cùng chỗ và Git không tự gộp. Xử lý: mở file conflict, chọn/giữ đúng thay đổi, xóa marker, add và commit hoàn tất merge. Nên communicate, chia nhỏ PR, pull thường xuyên để giảm conflict.",
        "criteria": [
            {"key": "what", "label": "Conflict khi sửa cùng chỗ", "weight": 0.35, "hints": ["conflict", "cùng chỗ", "không tự gộp"]},
            {"key": "resolve", "label": "Sửa marker / add / commit", "weight": 0.4, "hints": ["marker", "add", "commit", "resolve", "giải quyết"]},
            {"key": "prevent", "label": "Giảm conflict", "weight": 0.25, "hints": ["pull thường", "pr nhỏ", "communicate"]},
        ],
    },
    {
        "id": "cs-02",
        "track": "general_cs",
        "topic": "CS Fundamentals",
        "skill": "OOP vs Procedural",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Lập trình hướng đối tượng khác lập trình thủ tục ở điểm nào?",
        "reference_answer": "Thủ tục tổ chức theo hàm/procedure thao tác dữ liệu. OOP tổ chức theo object gồm data+behavior, dùng encapsulation/inheritance/polymorphism để mô hình hóa miền bài toán, tái sử dụng và mở rộng dễ hơn ở hệ lớn.",
        "criteria": [
            {"key": "procedural", "label": "Thủ tục: hàm + dữ liệu tách", "weight": 0.3, "hints": ["thủ tục", "hàm", "procedure", "function"]},
            {"key": "oop", "label": "OOP: object data+behavior", "weight": 0.4, "hints": ["object", "oop", "đóng gói", "class"]},
            {"key": "benefit", "label": "Tái sử dụng / mở rộng", "weight": 0.3, "hints": ["tái sử dụng", "mở rộng", "bảo trì"]},
        ],
    },
    {
        "id": "cs-03",
        "track": "general_cs",
        "topic": "CS Fundamentals",
        "skill": "Time complexity",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Độ phức tạp thời gian O(1), O(n), O(n^2) nghĩa là gì? Cho ví dụ.",
        "reference_answer": "Big-O mô tả tăng thời gian theo kích thước input. O(1) gần như không đổi (truy cập mảng theo index). O(n) tuyến tính (duyệt list). O(n^2) lồng hai vòng duyệt. Giúp so thuật toán và ước lượng khi data lớn.",
        "criteria": [
            {"key": "big_o", "label": "Big-O theo input size", "weight": 0.3, "hints": ["big-o", "độ phức tạp", "input", "n"]},
            {"key": "examples", "label": "Ví dụ O(1)/O(n)/O(n^2)", "weight": 0.5, "hints": ["o(1)", "o(n)", "o(n^2)", "vòng lặp", "index"]},
            {"key": "why", "label": "So thuật toán", "weight": 0.2, "hints": ["so sánh", "data lớn", "hiệu năng"]},
        ],
    },
    {
        "id": "cs-04",
        "track": "general_cs",
        "topic": "Networking",
        "skill": "TCP vs UDP",
        "difficulty": "Trung bình",
        "rank": ["fresher"],
        "question": "TCP và UDP khác nhau thế nào? Khi nào dùng từng loại?",
        "reference_answer": "TCP hướng kết nối, đảm bảo tin cậy/thứ tự (web HTTP, email). UDP không kết nối, nhanh hơn nhưng có thể mất gói (streaming, DNS, game realtime). Chọn TCP khi cần đủ dữ liệu; UDP khi ưu tiên độ trễ.",
        "criteria": [
            {"key": "tcp", "label": "TCP: tin cậy / kết nối", "weight": 0.35, "hints": ["tcp", "tin cậy", "kết nối", "thứ tự"]},
            {"key": "udp", "label": "UDP: nhanh / không đảm bảo", "weight": 0.35, "hints": ["udp", "nhanh", "mất gói", "không kết nối"]},
            {"key": "when", "label": "Use case", "weight": 0.3, "hints": ["http", "streaming", "dns", "game"]},
        ],
    },
    {
        "id": "cs-05",
        "track": "general_cs",
        "topic": "Security basics",
        "skill": "Auth vs Authz",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Authentication và Authorization khác nhau thế nào?",
        "reference_answer": "Authentication xác minh danh tính (login, JWT, session) — bạn là ai. Authorization quyết định được phép làm gì (role, permission) — bạn được truy cập resource nào. Thường authn trước, rồi authz trên từng request.",
        "criteria": [
            {"key": "authn", "label": "Authentication: danh tính", "weight": 0.4, "hints": ["authentication", "login", "danh tính", "jwt", "session"]},
            {"key": "authz", "label": "Authorization: quyền", "weight": 0.4, "hints": ["authorization", "permission", "role", "quyền"]},
            {"key": "order", "label": "Thứ tự / ví dụ", "weight": 0.2, "hints": ["trước", "sau", "ví dụ", "401", "403"]},
        ],
    },
    {
        "id": "devops-01",
        "track": "general_cs",
        "topic": "DevOps basics",
        "skill": "CI/CD intro",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "CI/CD là gì? Lợi ích với team nhỏ?",
        "reference_answer": "CI (Continuous Integration) tự động build/test khi code mới merge. CD (Continuous Delivery/Deployment) tự động đưa bản build sang staging/production theo pipeline. Giúp phát hiện lỗi sớm, giảm deploy tay, thống nhất môi trường.",
        "criteria": [
            {"key": "ci", "label": "CI: build/test tự động", "weight": 0.35, "hints": ["ci", "build", "test", "integrate", "merge"]},
            {"key": "cd", "label": "CD: deliver/deploy", "weight": 0.35, "hints": ["cd", "deploy", "delivery", "pipeline"]},
            {"key": "benefit", "label": "Lợi ích", "weight": 0.3, "hints": ["sớm", "tự động", "giảm lỗi", "nhanh"]},
        ],
    },
    {
        "id": "devops-02",
        "track": "general_cs",
        "topic": "DevOps basics",
        "skill": "Docker intro",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Docker container giúp gì so với cài trực tiếp lên máy?",
        "reference_answer": "Container đóng gói app + dependency theo image, chạy nhất quán trên máy dev/server. Nhẹ hơn VM vì chia sẻ kernel. Giảm lỗi “chạy được trên máy tôi”, dễ scale và cô lập dịch vụ. Dockerfile mô tả cách build image.",
        "criteria": [
            {"key": "package", "label": "Đóng gói app+dependency", "weight": 0.35, "hints": ["container", "image", "dependency", "đóng gói"]},
            {"key": "consistent", "label": "Nhất quán môi trường", "weight": 0.35, "hints": ["nhất quán", "dev", "prod", "máy tôi"]},
            {"key": "vs_vm", "label": "Nhẹ hơn VM / isolate", "weight": 0.3, "hints": ["vm", "kernel", "nhẹ", "cô lập"]},
        ],
    },
    {
        "id": "be-01",
        "track": "backend",
        "topic": "API Design",
        "skill": "REST resource",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Thiết kế URL REST tốt thường như thế nào? Cho ví dụ CRUD user.",
        "reference_answer": "Dùng danh từ số nhiều cho resource, method HTTP thể hiện hành động: GET /users, GET /users/{id}, POST /users, PUT/PATCH /users/{id}, DELETE /users/{id}. Tránh động từ trong path; dùng query cho lọc/phân trang.",
        "criteria": [
            {"key": "noun", "label": "Resource danh từ", "weight": 0.3, "hints": ["resource", "danh từ", "/users", "noun"]},
            {"key": "methods", "label": "HTTP method CRUD", "weight": 0.4, "hints": ["get", "post", "put", "delete", "patch"]},
            {"key": "query", "label": "Query filter/paging", "weight": 0.3, "hints": ["query", "page", "filter", "không dùng động từ"]},
        ],
    },
    {
        "id": "be-02",
        "track": "backend",
        "topic": "Backend",
        "skill": "Validation",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Tại sao cần validate dữ liệu đầu vào ở backend? Ví dụ cách làm.",
        "reference_answer": "Client có thể bypass validate UI; backend phải bảo vệ DB và business rule. Kiểm tra null/format/range/permission. Trong Spring dùng @Valid, Bean Validation (@NotNull, @Email). Trả 400 kèm message rõ khi invalid.",
        "criteria": [
            {"key": "why", "label": "Bảo vệ / không tin client", "weight": 0.35, "hints": ["bypass", "bảo vệ", "không tin client", "security"]},
            {"key": "what", "label": "Null/format/rule", "weight": 0.3, "hints": ["null", "format", "email", "range"]},
            {"key": "how", "label": "Annotation / 400", "weight": 0.35, "hints": ["valid", "notnull", "400", "bean validation"]},
        ],
    },
    {
        "id": "be-03",
        "track": "backend",
        "topic": "Backend",
        "skill": "Logging",
        "difficulty": "Dễ",
        "rank": ["intern", "fresher"],
        "question": "Logging trong ứng dụng backend dùng để làm gì? Nên log gì / tránh gì?",
        "reference_answer": "Log giúp debug, audit, theo dõi lỗi production (level INFO/WARN/ERROR). Nên log request id, lỗi kèm stack cần thiết, sự kiện nghiệp vụ quan trọng. Tránh log mật khẩu/token/PII; không log quá mức gây ồn và lộ dữ liệu.",
        "criteria": [
            {"key": "purpose", "label": "Debug / monitor", "weight": 0.3, "hints": ["debug", "monitor", "lỗi", "production"]},
            {"key": "levels", "label": "Log level", "weight": 0.3, "hints": ["info", "warn", "error", "level"]},
            {"key": "sensitive", "label": "Không log secret/PII", "weight": 0.4, "hints": ["password", "token", "pii", "nhạy cảm", "không log"]},
        ],
    },
]

WRONG_POOL = [
    "Em chưa học phần này nên không biết.",
    "Cái này giống nhau hết, không có khác biệt.",
    "Chỉ cần Google là được, không cần hiểu khái niệm.",
    "Đó là phần cứng máy tính, không liên quan phần mềm.",
    "Dùng AI viết code thì không cần quan tâm.",
    "Đây là thuật toán sắp xếp nhanh.",
    "Chỉ dành cho quản lý dự án, lập trình viên không dùng.",
]

SHALLOW_PREFIX = [
    "Em biết sơ là",
    "Hình như là",
    "Theo em thì",
    "Em nhớ mang máng",
    "Nói ngắn gọn thì",
]


def _keys(criteria: list[dict], n: int | None = None) -> str:
    ks = [c["key"] for c in criteria]
    if n is not None:
        ks = ks[:n]
    return ";".join(ks)


def _sentence_from_criterion(c: dict) -> str:
    hint = c["hints"][0]
    return f"Về {c['label'].split(':')[0].strip()}, cần nắm '{hint}'."


def synthesize_answers(q: dict, start_idx: int, need: int) -> list[dict]:
    """Create diverse scored answers for one question."""
    rows: list[dict] = []
    crit = q["criteria"]
    ref = q["reference_answer"]
    qid = q["id"]
    ranks = q.get("rank") or ["intern", "fresher"]

    paraphrases = [
        ref,
        ref.replace("là ", "chính là ").replace(" giúp ", " hỗ trợ "),
        "Tóm lại: " + ref,
        ref.split(".")[0] + ". " + (" ".join(_sentence_from_criterion(c) for c in crit)),
    ]

    templates: list[tuple[float, str, str, str]] = []

    # Excellent / near-ref
    for i, p in enumerate(paraphrases[:3]):
        templates.append((9.0 + (i % 2) * 0.5, p, _keys(crit), "near-ref"))

    # Good: drop last criterion wording but keep most
    good = ". ".join(_sentence_from_criterion(c) for c in crit[:-1]) + f" Liên quan câu hỏi: {q['question'][:60]}…"
    templates.append((7.5, good, _keys(crit, len(crit) - 1), "good-partial-last"))
    templates.append(
        (
            8.0,
            f"{crit[0]['label']}: {crit[0]['hints'][0]}. "
            + ". ".join(c["label"] + " (" + c["hints"][0] + ")" for c in crit[1:]),
            _keys(crit),
            "good-structured",
        )
    )

    # Mid: only first half criteria
    half = max(1, len(crit) // 2)
    mid = ". ".join(_sentence_from_criterion(c) for c in crit[:half])
    templates.append((5.5, mid, _keys(crit, half), "mid-half"))
    templates.append(
        (
            6.0,
            f"{SHALLOW_PREFIX[0]} {crit[0]['hints'][0]} và {crit[min(1, len(crit)-1)]['hints'][0]}, còn lại em chưa nhớ rõ.",
            _keys(crit, min(2, len(crit))),
            "mid-vague",
        )
    )
    templates.append(
        (
            4.5,
            f"Em chỉ nhớ ý '{crit[0]['hints'][0]}', các ý khác chưa chắc.",
            _keys(crit, 1),
            "mid-one-key",
        )
    )

    # Weak / wrong
    templates.append((2.0, random.choice(WRONG_POOL), "", "wrong"))
    templates.append((1.5, f"{q['topic']} là công nghệ không liên quan đến câu hỏi này.", "", "off-topic"))
    templates.append(
        (
            3.0,
            f"{SHALLOW_PREFIX[1]} liên quan {q['skill']} nhưng em không giải thích được chi tiết.",
            "",
            "shallow",
        )
    )
    templates.append(
        (
            3.5,
            f"Khác nhau ở tên gọi thôi, thực tế {crit[0]['hints'][0]} dùng cho mọi trường hợp.",
            _keys(crit, 1) if crit else "",
            "oversimplify",
        )
    )

    # Extra paraphrases with score jitter to reach `need`
    extra_bits = [
        (8.5, f"Theo hướng thực tế: {ref}", _keys(crit), "practical"),
        (7.0, f"Các ý chính: " + "; ".join(c["label"] for c in crit) + ".", _keys(crit), "label-list"),
        (
            6.5,
            f"Em hiểu {crit[0]['label']} nhờ hint '{crit[0]['hints'][0]}'. "
            + (f"Thêm {crit[1]['label']}." if len(crit) > 1 else ""),
            _keys(crit, min(2, len(crit))),
            "two-points",
        ),
        (
            5.0,
            f"Liên quan {q['skill']}: {crit[0]['hints'][0]}. Phần còn lại em trả lời chưa đủ.",
            _keys(crit, 1),
            "incomplete",
        ),
        (4.0, f"{SHALLOW_PREFIX[2]} {q['topic']} quan trọng với fresher.", "", "too-generic"),
        (2.5, "Em trả lời sai: cái này chỉ dùng trên frontend React.", "", "wrong-domain"),
        (
            9.5,
            ref + " Đây là phần kiến thức intern/fresher nên nắm vững.",
            _keys(crit),
            "excellent-plus",
        ),
        (
            8.0,
            " ".join(f"{c['hints'][0]} → {c['label']}." for c in crit),
            _keys(crit),
            "hint-walk",
        ),
    ]
    templates.extend(extra_bits)

    # Deduplicate by answer text, then take `need`
    seen = set()
    uniq: list[tuple[float, str, str, str]] = []
    for score, ans, keys, notes in templates:
        key = ans.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append((score, ans, keys, notes))

    # If still short, mutate shallow variants
    i = 0
    while len(uniq) < need:
        base = uniq[i % len(uniq)]
        mutated = (
            max(1.0, min(9.5, base[0] + random.choice([-0.5, 0.0, 0.5]))),
            base[1] + f" (cách diễn đạt thêm #{len(uniq)+1}).",
            base[2],
            base[3] + "-var",
        )
        uniq.append(mutated)
        i += 1

    for j in range(need):
        score, ans, keys, notes = uniq[j]
        rank = ranks[j % len(ranks)]
        rows.append(
            {
                "id": f"a{start_idx + j:04d}",
                "question_id": qid,
                "rank_target": rank,
                "answer": ans.replace("\n", " ").strip(),
                "human_score": f"{score:.1f}",
                "human_covered_keys": keys,
                "notes": notes,
            }
        )
    return rows


def main() -> None:
    data = json.loads(Q_PATH.read_text(encoding="utf-8"))
    existing_ids = {q["id"] for q in data["questions"]}
    added = 0
    for nq in NEW_QUESTIONS:
        if nq["id"] not in existing_ids:
            data["questions"].append(nq)
            existing_ids.add(nq["id"])
            added += 1

    data["meta"]["notes"] = (
        "Dataset train intern/fresher CNTT đa mảng (backend, FE, QA, SQL, Git, CS, DevOps basics). "
        "Mỗi câu weight tổng ≈ 1.0. Sinh bổ sung để fine-tune/calibration."
    )
    data["meta"]["tracks"] = sorted(
        {q["track"] for q in data["questions"]}
    )
    Q_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Load existing answers
    with A_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        old_rows = list(reader)

    by_q: dict[str, list[dict]] = {}
    for r in old_rows:
        by_q.setdefault(r["question_id"], []).append(r)

    # Next id
    max_n = 0
    for r in old_rows:
        try:
            max_n = max(max_n, int(r["id"].lstrip("a")))
        except ValueError:
            pass
    next_id = max_n + 1

    TARGET_PER_Q = 20
    new_rows: list[dict] = []
    for q in data["questions"]:
        have = by_q.get(q["id"], [])
        need = max(0, TARGET_PER_Q - len(have))
        if need == 0:
            continue
        gen = synthesize_answers(q, next_id, need)
        next_id += need
        new_rows.extend(gen)
        by_q.setdefault(q["id"], []).extend(gen)

    all_rows = old_rows + new_rows
    with A_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in all_rows:
            w.writerow(r)

    # Stats
    from collections import Counter

    scores = [float(r["human_score"]) for r in all_rows]
    tracks = Counter(q["track"] for q in data["questions"])
    print(f"questions_total={len(data['questions'])} (+{added} new)")
    print(f"answers_total={len(all_rows)} (+{len(new_rows)} new)")
    print(f"tracks={dict(tracks)}")
    print(f"per_q_min={min(len(v) for v in by_q.values())} per_q_max={max(len(v) for v in by_q.values())}")
    print(f"score_min={min(scores)} max={max(scores)} mean={sum(scores)/len(scores):.2f}")


if __name__ == "__main__":
    main()
