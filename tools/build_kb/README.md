# build_kb: Knowledge Base kỹ năng IT

KB (đồ thị tri thức) cho module match CV – JD: kỹ năng và alias, quan hệ giữa kỹ năng, kỹ năng của nhóm vai trò,
chức danh, cấp bậc, ngành học, khoảng cách giữa các nhóm vai trò.

Tài liệu:

- `docs/Knowledge base.md`: thiết kế (schema, quy tắc gộp, bản chụp cho module match)
- `docs/pack-format.md`: định dạng gói đóng góp (đầu vào của thư ký chung)
- `docs/trang-thai-kb.md`: trạng thái và số liệu KB

## Cách KB được dựng

Mỗi nguồn có một **adapter** riêng. Adapter chỉ làm một việc: đọc nguồn rồi ghi ra một **gói đóng góp** trong `packs/`,
theo một định dạng chung. **Thư ký chung** `kb_pipeline` đọc mọi gói, tự đối chiếu với KB, xử lý trùng và mâu thuẫn,
rồi ghi KB cuối cùng.

```
roadmap PDF ──kb1──┐
ITviec      ──kb2──┼──> packs/<pack_id>/ ──kb_pipeline──> out/ (JSONL, kb.cypher, hàng đợi duyệt) ──> Neo4j
CSV do AI   ──kb3──┘                                                                              └─> export_snapshot.py
```

Adapter không cần biết KB đang có gì: nó gọi thực thể theo tên ("ReactJS"), thư ký tự nhận ra đó là React đã có.

| Gói | Nguồn | Ưu tiên | Trust |
|---|---|---|---|
| `kb1-roadmap` | 18 PDF roadmap.sh (P01–P18), alias từ tag synonyms Stack Overflow | 10 | medium |
| `kb2-itviec` | chức danh ITviec (W01), ngành học tự sinh (M01), alias cấp bậc tự soạn (M02) | 20 | medium / low |
| `kb3-generated` | tri thức do Claude sinh (G01–G09) | 30 | low |

Ưu tiên nhỏ được nạp trước và được coi là "đã có": khi alias trùng, gói trước thắng.

```
build_kb/
├── kb_pipeline/      thư ký chung: kiểm gói, đối chiếu, gộp, luật quan hệ, chấm điểm, phiên bản, xuất
├── packs/            gói đóng góp của từng nguồn (đầu vào duy nhất của kb_pipeline)
├── kb1/              adapter roadmap PDF: pipeline/, data/ (pdf/, sources.csv, tag_synonyms.csv), out/
├── kb2/              adapter ITviec: pipeline/, data/ (itviec_*.csv, majors.csv, levels.csv), out/
├── kb3/              adapter AI sinh: pipeline/, data/ (bảng CSV, sources.csv)
├── shared/           hàm và hằng dùng chung (ROLE_GROUPS, LEVEL_RANKS, norm, strip_accents)
├── out/              KB cuối cùng và báo cáo (xem "Kết quả")
├── load_kb.py        lệnh cũ, gọi kb_pipeline
├── export_snapshot.py  xuất bản chụp cho module match từ Neo4j
├── tests/
└── docs/
```

## Cài đặt

```powershell
conda activate module2
pip install -r requirements.txt
copy .env.example .env        # điền groq_api_key (console.groq.com), chỉ cần cho kb1 s4_classify
docker start neo4j            # lần đầu: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/changeme123 neo4j:5-community
```

Mọi lệnh chạy từ thư mục `build_kb/`.

## Chạy nhanh

Dữ liệu trung gian của KB1, KB2 đã có sẵn, nên dựng lại KB chỉ cần đóng gói rồi gộp:

```powershell
python -m kb1.pipeline.s7_pack      # packs/kb1-roadmap/
python -m kb2.pipeline.s5_pack      # packs/kb2-itviec/
python -m kb3.pipeline.build        # packs/kb3-generated/
python -m kb_pipeline --load        # gộp, kiểm, ghi out/, nạp Neo4j
python export_snapshot.py           # bản chụp cho module match
```

Sửa dữ liệu một nguồn thì chỉ chạy lại adapter của nguồn đó, rồi `python -m kb_pipeline`.

## Adapter của từng nguồn

### KB1: roadmap.sh

```powershell
python -m kb1.pipeline.s1_survey      # ảnh có khung ở kb1/out/survey/
python -m kb1.pipeline.s2_nodes       # --only backend,ai-engineer để chạy thử
python -m kb1.pipeline.s3_groups
python -m kb1.pipeline.s4_classify    # gọi Groq, có cache ở kb1/out/label_cache.json; hết hạn mức thì chạy lại để tiếp tục
python -m kb1.pipeline.s5_triples     # ghi kb1_nodes.jsonl, kb1_edges.jsonl, thêm alias Stack Overflow
python -m kb1.pipeline.s6_report      # số liệu ở kb1/out/report/
python -m kb1.pipeline.s7_pack        # đóng gói vào packs/kb1-roadmap/
```

Mỗi bước đọc kết quả của bước trước trong `kb1/out/`, nên sai ở bước nào thì chạy lại từ bước đó.
`kb1/pipeline/config.py` (`ROADMAPS`) gán mỗi PDF cho nhóm vai trò; game-developer, ux-design, network-engineer là
roadmap của nhóm Game, Design, IT Support.

**Alias từ Stack Overflow.** `python -m kb1.pipeline.so_tag_synonyms --key YOUR_API_KEY` tải
`kb1/data/tag_synonyms.csv`, `s5_triples` thêm alias qua `so_aliases.py`. Tag chỉ được nhận khi cùng tên với tag đích
hoặc nằm trong danh sách duyệt tay ở `kb1/pipeline/config.py` (`SO_KEEP`, `SO_AMBIGUOUS`, `SO_BRIDGE`). Từng quyết
định ghi ở `kb1/out/so_alias_report.csv`.

**Kiểm tay cho báo cáo.** Điền `parent_expected` trong `kb1/out/gold_groups.csv` và `type_expected` trong
`kb1/out/gold_labels.csv` (`technology`, `concept`, `category`, `not_skill`), rồi chạy lại `s6_report`.

### KB2: ITviec

```powershell
python -m kb2.pipeline.s1_crawl_itviec   # cào bản Việt và Anh về kb2/data/itviec_titles_raw.csv
python -m kb2.pipeline.s2_titles         # chức danh: kb2/out/kb2_nodes.jsonl, kb2_edges.jsonl, kb2_checks.json
python -m kb2.pipeline.s3_majors         # ngành học: kb2/out/kb2_major_nodes.jsonl
python -m kb2.pipeline.s4_levels         # cấp bậc: kb2/out/kb2_level_nodes.jsonl
python -m kb2.pipeline.s5_pack           # đóng gói vào packs/kb2-itviec/
```

`kb2/data/itviec_title_map.csv` là bảng duyệt tay: cặp Việt – Anh, tên chuẩn (`canonical`), `role_groups`, alias thêm.
`s2_titles` dừng nếu bảng này lệch với dữ liệu đã cào. `kb2/data/levels.csv` giữ thang `rank` của thiết kế
(`LEVEL_RANKS` trong `shared/config.py`), `s4_levels` dừng nếu lệch thang.

### KB3: AI sinh

```powershell
python -m kb3.pipeline.build             # ghi gói packs/kb3-generated/
```

Mỗi bảng trong `kb3/data/` là một nguồn `type = generated`, `trust = low` (`kb3/data/sources.csv`). Bằng chứng của mỗi
quan hệ là `{source_id, page = số dòng, quote = nguyên dòng CSV}`.

| Bảng | Nguồn | Nội dung |
|---|---|---|
| `new_skills.csv` | G01 | kỹ năng chưa có (framework, công cụ, nhúng, game, thiết kế, BA/PM, kỹ năng mềm, ngoại ngữ, chứng chỉ), kèm nhóm, cha, nhóm vai trò |
| `skill_aliases.csv` | G02 | alias thêm cho kỹ năng đã có, chủ yếu tiếng Việt |
| `skill_fixes.csv` | G03 | `same_as` gộp trùng, `reject` loại nhãn rác, `ambiguous` tên trùng từ thường, `type` đổi loại, `drop_category` bỏ IN_CATEGORY sai, `display` tên hiển thị (`java` -> `Java`; khoá và alias giữ nguyên) |
| `edges.csv` | G04 | PARENT_OF, IN_CATEGORY, USED_IN giữa các kỹ năng đã có |
| `categories.csv` | G05 | nhóm kỹ năng và `sibling_ok` đề xuất (dùng `override`, nên thắng giá trị của KB1) |
| `titles.csv` | G06 | chức danh và MAPS_TO |
| `levels.csv` | G07 | alias cấp bậc |
| `majors.csv` | G08 | ngành học |
| `near.csv` | G09 | NEAR `method = hypothesis`; 8 cặp đầu là ma trận M giả thuyết của thiết kế |

Theo luật (`--policy rule`), tri thức KB3 luôn `candidate`: nguồn tự sinh không được tính là nguồn độc lập (thiết kế
mục 6). Với chính sách tạm thời `provisional` (mặc định từ 21/11/2026) nó được `accepted` với `accepted_by = provisional`.

## Thư ký chung (`kb_pipeline`)

```powershell
python -m kb_pipeline --dry-run   # chỉ gộp và kiểm, in tóm tắt, không ghi gì
python -m kb_pipeline             # gộp, kiểm, ghi out/ (cả kb.cypher)
python -m kb_pipeline --load      # như trên rồi nạp Neo4j (= python load_kb.py)
```

Các bước, theo thứ tự:

1. **Kiểm gói**: nhãn, trường, giá trị hợp lệ, mọi quan hệ có evidence, `source_id` không trùng giữa các gói.
2. **Đối chiếu thực thể**: trùng khoá, hoặc tên trùng alias của thực thể đã có ("ReactJS" -> React).
   Alias tiếng Việt được tự thêm dạng không dấu.
3. **Alias**: alias đã thuộc thực thể khác thì bỏ và ghi vào hàng đợi duyệt. Alias dễ nhầm ("go", "spring") được
   phép chung nhiều thực thể.
4. **Bản vá**: `same_as` chạy trước khi đọc quan hệ, các bản vá khác chạy sau.
5. **Giá trị mâu thuẫn** (vd. hai gói cho `type` khác nhau): `override` > trust cao hơn > gói nạp trước.
6. **Luật quan hệ**: PARENT_OF chỉ nối hai kỹ năng technology và không được có vòng (bỏ cạnh yếu nhất). Vi phạm thì
   quan hệ thành `review`: vẫn ghi, nhưng không xuất cho module match.
7. **Chấm điểm** (thiết kế mục 6): `confidence = 1 − Π(1 − w_trust)`, mỗi publisher tính một lần. Quan hệ `accepted`
   khi có 2 publisher độc lập hoặc 1 nguồn `high`. Thực thể `accepted` khi có một nguồn không tự sinh, trust medium
   trở lên. **Tạm thời (21/11/2026) chính sách mặc định là `provisional`**: mọi thứ không `rejected`/`review` đều
   `accepted`; cái qua luật ghi `accepted_by = rule`, cái không qua ghi `accepted_by = provisional`; Category chưa
   được duyệt `sibling_ok` nhận tạm `sibling_ok_suggest` (`sibling_ok_by = provisional`). Quay về luật:
   `python -m kb_pipeline --policy rule` (đổi `ACCEPT_POLICY` trong `kb_pipeline/schema.py` để thành mặc định).
8. **Kiểm chặn**: alias trùng, quan hệ trỏ tới nút không có, vòng PARENT_OF -> dừng, không ghi gì.
9. **Phiên bản**: so với lần chạy trước; KB đổi thì thêm một `KBVersion`, không đổi thì báo "không đổi".
10. **Xuất**: JSONL, `out/kb.cypher`, Neo4j (với `--load`).

Neo4j: mỗi lần nạp thay toàn bộ `Skill`, `Category`, `JobTitle`, `Level`, `Major`, `Source` và quan hệ NEAR trong một
giao dịch; giữ `RoleGroup` và `KBVersion`.

### Kết quả

| File | Nội dung |
|---|---|
| `out/kb_nodes.jsonl`, `out/kb_edges.jsonl` | KB cuối cùng; mỗi nút và quan hệ có `status`, `confidence`, `sources`, `kb_origin` |
| `out/kb_checks.json` | tóm tắt: số nút, quan hệ, trạng thái, hàng đợi duyệt, diff |
| `out/review_queue.jsonl` | việc cần người xem, mỗi dòng một mục có `kind` |
| `out/kb_diff.json` | thêm, bớt, đổi gì so với lần chạy trước |
| `out/versions.jsonl` | lịch sử `KBVersion` |
| `out/kb.cypher` | script dựng lại toàn bộ KB trong Neo4j, không cần Python |

`status`: `accepted`, `candidate`, `rejected`, và `review` (vi phạm luật, chờ duyệt).

Chạy `out/kb.cypher`:

```powershell
cypher-shell -u neo4j -p changeme123 -f out/kb.cypher
# hoặc: docker exec -i neo4j cypher-shell -u neo4j -p changeme123 < out/kb.cypher
```

### Xử lý hàng đợi duyệt

Mỗi mục trong `out/review_queue.jsonl` có `pack` (gói gây ra) và `kind`:

| `kind` | Nghĩa | Thường sửa thế nào |
|---|---|---|
| `alias_conflict` | alias đề xuất đã thuộc thực thể khác | bỏ alias khỏi dữ liệu nguồn, hoặc thêm `same_as` nếu hai thực thể thật ra là một |
| `value_conflict` | hai gói cho giá trị khác nhau | sửa nguồn sai, hoặc dùng `override` / bản vá `set` |
| `unresolved_node`, `unresolved_edge`, `unresolved_patch` | gọi tên thứ không có trong KB | sửa tên trong dữ liệu nguồn |
| `new_node_missing_fields` | tạo thực thể mới nhưng thiếu trường bắt buộc | thêm `type` (Skill), `group` (Major), `rank` (Level) |
| `parent_of_type` | PARENT_OF có đầu không phải technology | bỏ, đổi sang IN_CATEGORY, hoặc sửa `type` |
| `parent_of_cycle` | vòng cha/con, cạnh yếu nhất đã bị gác | bỏ cạnh sai trong dữ liệu nguồn |

Sửa ở dữ liệu nguồn của gói (không sửa `out/`), chạy lại adapter rồi `python -m kb_pipeline`.

### Thêm một nguồn mới

1. Tạo thư mục adapter (vd. `kb4/`), đọc nguồn, rồi ghi gói bằng `kb_pipeline.packs.write_pack(...)`:

   ```python
   from kb_pipeline.packs import write_pack

   sources = [{"source_id": "E01", "type": "web", "title": "ESCO skills", "publisher": "European Commission",
               "trust": "high"}]
   nodes = [{"label": "Skill", "name": "ReactJS", "type": "technology", "aliases": ["react.js"], "sources": ["E01"]}]
   edges = [{"type": "PARENT_OF", "src": "JavaScript", "dst": "ReactJS",
             "evidence": [{"source_id": "E01", "page": 1, "quote": "..."}]}]
   write_pack("kb4-esco", "KB4", 15, sources, nodes, edges)
   ```

2. `python -m kb_pipeline --dry-run` để xem trước, rồi `python -m kb_pipeline --load`.
3. Xem `out/review_queue.jsonl`.

`source_id` phải mới (không trùng gói khác). Không sửa code của `kb_pipeline`. Tắt một nguồn: đặt `"enabled": false`
trong `packs/<pack_id>/manifest.json`. Nhóm vai trò mới: thêm vào `ROLE_GROUPS` trong `shared/config.py`.

## Bản chụp cho module match

```powershell
python export_snapshot.py                  # bản dev (cả candidate), thư mục out/snapshot/<phiên bản>-dev/
python export_snapshot.py --accepted-only  # chỉ tri thức accepted
python export_snapshot.py --dry-run        # chỉ kiểm tra
python export_snapshot.py --from-out --accepted-only   # đọc out/kb_*.jsonl thay vì Neo4j
```

Đọc từ Neo4j (chạy `python -m kb_pipeline --load` trước) hoặc từ `out/kb_*.jsonl` (`--from-out`), cấp `skill_id` ổn định (`out/skill_ids.csv`), ghi
`skill_ontology`, `role_title_map`, `role_distance`, `major_group`, `ambiguous_aliases` và `manifest.json`.
`ontology_version` lấy từ `KBVersion` cuối trong `out/versions.jsonl`. Quan hệ `review` và `rejected` không được xuất.

Lưu ý: với policy `provisional` mọi quan hệ còn sống là `accepted`, nên `--accepted-only` đã đủ quan hệ. Lọc
`accepted_by = provisional` khi cần biết phần chưa qua luật. Tên kỹ năng trong bản chụp là `display_name` nếu có
(bản vá `display` của KB3), không thì `name`.

### Phát hành cho hệ thống (HireLens)

Module match trong stack (`cvmatch-ai`) mount `out/snapshot/` read-only và tự nạp bản `ontology_version` đang chọn khi
khởi động. Không thành phần nào trong stack chạy `build_kb` hay Neo4j.

```powershell
python -m kb_pipeline                                    # gộp + kiểm chặn, ghi KBVersion mới nếu KB đổi
python export_snapshot.py --from-out --accepted-only     # out/snapshot/<KBVersion>/
python release_check.py out/snapshot/<mới> --prev out/snapshot/<đang dùng>   # ghi release_check.md; exit 1 = chặn
python -m pytest tests
```

1. Bản chụp đã phát hành **không sửa lại**: sửa KB = phiên bản mới. Commit cùng lúc `out/snapshot/<mới>/`,
   `out/skill_ids.csv`, `out/versions.jsonl`.
2. `release_check.py` chặn khi một `skill_id` đổi nghĩa (cùng id, khác tên và không chung alias). `skill_id` ổn định là
   điều kiện để module match `reprocess cv --from A5` giữ vector. Đổi tên hiển thị, alias chuyển chủ chỉ báo để xem.
3. Bên module match: `cvmatch kb import` (hoặc khởi động lại container) → `reprocess cv --from A5` + `reprocess jd` nếu
   alias / quan hệ đổi (chỉ đổi tên hiển thị thì không cần) → sửa `ontology_version` trong `services/cvmatch-ai/config/active.yaml`
   (hoặc `CVMATCH_ONTOLOGY_VERSION`) → khởi động lại.

sha256 của nguồn và gói tính trên nội dung đã bỏ `\r` (checkout Windows với `core.autocrlf` không làm sinh phiên bản giả).

## Test

```powershell
python -m pytest tests
```
