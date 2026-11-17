# Trạng thái Knowledge Base

> Cập nhật: 05/11/2026. Đối chiếu với `Knowledge base.md`, số liệu lấy từ Neo4j.
> KB trong Neo4j gộp từ KB1 (18 PDF roadmap, alias Stack Overflow) và KB2 (chức danh ITviec) bằng `load_kb.py`. Mọi nút và quan hệ đều là `candidate`, chưa dùng được cho module match.

## Các loại tri thức

- [x] **T1. Kỹ năng và alias** (có một phần): 1.470 `Skill` (591 technology, 879 concept). 284 kỹ năng có từ 2 alias, đã có dạng như "k8s" → Kubernetes nhờ tag synonyms của Stack Overflow. Còn các cặp skill trùng nghĩa chưa gộp (`kafka` / `apache kafka`...), xem dòng `conflict` trong `kb1/out/so_alias_report.csv`.
- [x] **T2. Quan hệ giữa kỹ năng** (có một phần): 1.234 `IN_CATEGORY`, 246 `Category`. Chỉ 15 `PARENT_OF`, thiếu quan hệ kiểu Java → Spring Boot. `sibling_ok` mới là đề xuất, 3 nhóm "chọn một".
- [x] **T3. Kỹ năng của nhóm vai trò** (có một phần): 1.269 `USED_IN` tới 9 nhóm, có `in_roadmap`. Chưa có `df_jd`, `share_jd` (cần dữ liệu JD).
- [x] **T4. Chức danh và cấp bậc** (có một phần): 96 `JobTitle` từ ITviec (nguồn `W01`), 45 `MAPS_TO` gán tay. 54 chức danh chưa có nhóm vai trò (quản lý, BA, thiết kế, hỗ trợ, nhúng...). 6 `Level` (Intern 0 đến Lead 5), alias tự soạn, nguồn `M02`.
- [x] **T5. Khoảng cách nhóm vai trò** (có một phần): 36 `NEAR` với `method = computed` (Jaccard trên `USED_IN`). Giá trị rất thấp, ví dụ Backend – Fullstack 0,038, nên chưa dùng làm ma trận `M` được. Chưa có `method = hypothesis`.
- [x] **T6. Nhóm ngành học** (có một phần): 39 `Major` tự sinh (11 `it`, 13 `related`, 15 `other`), nguồn `M01`, `trust = low`, chưa đối chiếu nguồn.

## Hạ tầng KB

- [x] Nguồn và bằng chứng: 21 `Source` (18 PDF, 1 web, 2 tự sinh), 1.746 `EVIDENCED_BY`
- [x] `RoleGroup`: 9 nhóm (đã tách `AI/ML` khỏi `Data`)
- [x] KB2 (có một phần): chức danh ITviec. Chưa có ESCO, JD, tài liệu chính thức
- [x] Gộp KB1 + KB2 thành KB (có một phần): đã gộp và nạp bằng `load_kb.py`. Chưa cấp `skill_id`, chưa chuyển sang `accepted`, chưa áp quy tắc nhận quan hệ ở mục 6 của thiết kế
- [ ] `KBVersion`
- [ ] Bản chụp cho module match (`skill_ontology`, `role_title_map`, `role_distance`, `major_group`)
