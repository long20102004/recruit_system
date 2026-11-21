# Định dạng gói đóng góp (contribution pack)

> Đầu vào duy nhất của thư ký chung `kb_pipeline`. Mọi nguồn (PDF, web, CSV do AI sinh, API, JD...) đều phải tự đổi
> sang định dạng này. Luật trong code: `kb_pipeline/schema.py`, kiểm bằng `kb_pipeline/packs.py: validate_pack`.

## Đọc nhanh

Gói giống một **phiếu góp ý**. Nguồn chỉ cần ghi "tôi thấy gì, bằng chứng ở đâu", không cần biết KB đang có gì.
Pipeline tự tra, tự gộp, tự xử lý trùng và mâu thuẫn.

```
packs/<pack_id>/
├── manifest.json    gói là ai, ưu tiên bao nhiêu, dùng những nguồn nào
├── nodes.jsonl      thực thể (kỹ năng, nhóm, chức danh, cấp bậc, ngành)
├── edges.jsonl      quan hệ, mỗi quan hệ có bằng chứng
└── patches.jsonl    sửa KB đã có (tuỳ chọn)
```

Ghi gói bằng `kb_pipeline.packs.write_pack(pack_id, kb_origin, priority, sources, nodes, edges, patches)`: hàm kiểm
định dạng trước khi ghi, sai thì dừng.

## manifest.json

```json
{
  "pack_id": "kb3-generated",
  "kb_origin": "KB3",
  "priority": 30,
  "enabled": true,
  "description": "...",
  "sources": [
    {"source_id": "G01", "type": "generated", "title": "...", "publisher": "Claude (claude-opus-5-5)",
     "uri": "kb3/data/new_skills.csv", "trust": "low", "license": "...", "accessed": "2026-11-21", "sha256": "..."}
  ]
}
```

- `priority`: nhỏ hơn thì nạp trước và được coi là "đã có". Gói trước thắng khi alias trùng. Hiện dùng: KB1 = 10,
  KB2 = 20, KB3 = 30. Nguồn chính thức (ESCO, docs) nên có ưu tiên nhỏ hơn nguồn AI.
- `sources[].type = generated` cho nguồn tự sinh: không bao giờ được tính là nguồn độc lập.
- `trust`: `high` | `medium` | `low` (thiết kế mục 1).
- `publisher`: hai nguồn cùng publisher (vd. 18 PDF của roadmap.sh) chỉ tính là một khi xét "2 nguồn độc lập".
- `source_id` không được trùng với gói khác (trừ khi khai báo y hệt).

## nodes.jsonl

Mỗi dòng là một khẳng định về một thực thể. `label` là `Skill`, `Category`, `JobTitle`, `Level` hoặc `Major`.

```json
{"label": "Skill", "name": "Spring Boot", "type": "technology", "aliases": ["springboot"],
 "ambiguous_aliases": ["spring"], "sources": ["G01"]}
{"label": "Skill", "ref": "oop", "aliases": ["lập trình hướng đối tượng"], "sources": ["G02"]}
{"label": "Category", "name": "Relational Databases", "sibling_ok_suggest": true, "override": ["sibling_ok_suggest"]}
```

| Trường | Ý nghĩa |
|---|---|
| `name` | tên thực thể: khớp được thì dùng thực thể có sẵn, không khớp thì tạo mới |
| `ref` | thay cho `name`: phải khớp thực thể có sẵn, không khớp thì vào hàng đợi duyệt (dùng khi chỉ thêm alias) |
| `key` | tuỳ chọn, khoá muốn dùng; mặc định là `name` chuẩn hoá |
| `aliases`, `ambiguous_aliases` | tên gọi khác, và tên gọi dễ nhầm (không tự khớp trong văn bản tự do) |
| `sources` | `source_id` ủng hộ thực thể này |
| `override` | danh sách trường mà gói này muốn thắng mọi gói khác |
| trường riêng | Skill: `type` (`technology` / `concept`, bắt buộc khi tạo mới). Category: `sibling_ok_suggest`, `sibling_ok`. JobTitle: `itviec_group`. Level: `rank` (bắt buộc, phải đúng thang). Major: `group` (`it` / `related` / `other`, bắt buộc) |

Pipeline tìm thực thể theo thứ tự: khoá trùng, rồi tên trùng một alias (không dễ nhầm) của thực thể đã có.
Alias tiếng Việt được tự thêm dạng không dấu.

## edges.jsonl

```json
{"type": "PARENT_OF", "src": "Java", "dst": "Spring Boot",
 "evidence": [{"source_id": "G01", "page": 2, "quote": "Spring Boot,technology,..."}]}
{"type": "USED_IN", "src": "Spring Boot", "dst": "Backend", "in_roadmap": false, "evidence": [...]}
{"type": "NEAR", "src": "Backend", "dst": "Fullstack", "method": "hypothesis", "m": 0.8, "evidence": [...]}
```

| `type` | `src` → `dst` | Thuộc tính riêng |
|---|---|---|
| `PARENT_OF` | Skill → Skill (cả hai phải là technology) | |
| `IN_CATEGORY` | Skill → Category | |
| `USED_IN` | Skill → RoleGroup | `in_roadmap`, `node_kind` |
| `EVIDENCED_BY` | Skill → Source (`source_id`) | `page`, `snippet` |
| `MAPS_TO` | JobTitle → RoleGroup | `method` |
| `NEAR` | RoleGroup → RoleGroup (đối xứng) | `m`, `method` (`hypothesis`) |

- `src`, `dst` gọi theo tên hoặc alias. RoleGroup phải nằm trong `ROLE_GROUPS` (`shared/config.py`).
- `evidence` bắt buộc, mỗi mục có `source_id` (khai báo trong manifest), `page`, `quote`.
- Đầu mút không tìm thấy: quan hệ bị bỏ và ghi vào hàng đợi duyệt (`unresolved_edge`).
- `NEAR` computed do pipeline tự tính, gói không cần ghi.

## patches.jsonl

| `op` | Trường | Tác dụng |
|---|---|---|
| `same_as` | `label`, `drop`, `keep` | gộp `drop` vào `keep`: alias, nguồn, quan hệ chuyển sang `keep`. Chạy trước khi đọc quan hệ |
| `reject` | `label`, `ref` | thực thể và quan hệ chạm nó thành `rejected` |
| `ambiguous` | `label`, `ref` | mọi alias (cả tên) thành alias dễ nhầm |
| `set` | `label`, `ref`, `fields` | ghi đè trường, vd. `{"type": "concept"}` |
| `drop_edge` | `type`, `src`, `dst` | bỏ quan hệ |

Bản vá trỏ tới thứ không có thì bỏ qua và ghi vào hàng đợi duyệt (`unresolved_patch`).

## Kết quả

| File | Nội dung |
|---|---|
| `out/kb_nodes.jsonl`, `out/kb_edges.jsonl` | KB cuối cùng, mỗi nút/quan hệ có `status`, `confidence`, `sources`, `kb_origin` |
| `out/review_queue.jsonl` | việc cần người xem: `alias_conflict`, `value_conflict`, `unresolved_node`, `unresolved_edge`, `unresolved_patch`, `new_node_missing_fields`, `parent_of_type`, `parent_of_cycle` |
| `out/kb_diff.json` | thêm, bớt, đổi gì so với lần chạy trước |
| `out/versions.jsonl` | lịch sử `KBVersion`; chỉ thêm khi KB đổi |
| `out/kb.cypher` | script dựng lại toàn bộ KB trong Neo4j |

`status`: `accepted`, `candidate`, `rejected` (thiết kế), và `review`: quan hệ vi phạm luật, chờ duyệt, không xuất cho
module match. `accepted_by`: `rule` (qua luật mục 6) hoặc `provisional` (nhận tạm theo chính sách mặc định hiện tại,
xem `ACCEPT_POLICY` trong `kb_pipeline/schema.py`; `--policy rule` để chạy đúng luật).
