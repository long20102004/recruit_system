# Trạng thái Knowledge Base

> **Cập nhật 24/11/2026: bản phát hành `kb-2026-11-24` cho tích hợp HireLens (plan I02).**
> - Nội dung tri thức **không đổi** so với `kb-2026-11-21-4` (1.710 kỹ năng, cùng alias, quan hệ, `skill_id`); chỉ đổi
>   tên hiển thị của 73 kỹ năng bằng bản vá `display` mới ở `kb3/data/skill_fixes.csv` (`java` → `Java`,
>   `javascript` → `JavaScript`, `node.js` → `Node.js`, `vpn` → `VPN`…). Còn 31 technology viết thường cố ý
>   (`npm`, `curl`, `pandas`, `pytest`…). Kiểm bằng `release_check.py`: 0 thêm / bớt, 0 alias chuyển chủ,
>   0 `skill_id` đổi nghĩa (`out/snapshot/kb-2026-11-24/release_check.md`).
> - sha256 nguồn / gói tính trên nội dung đã bỏ `\r`. Lần này 4 nguồn KB3 (G03 thật sự đổi; G04, G05, G09 chỉ do
>   checkout CRLF) đổi sha một lần; sau đó checkout Windows / Linux cho cùng sha.
> - `services/cvmatch-ai/config/active.yaml` chuyển sang `kb-2026-11-24`. Chưa so `--policy rule` với `provisional` bằng
>   ablation (Q-E của plan): cần nhãn thật; bản tích hợp giữ `provisional`.

> **Cập nhật 21/11/2026 (3): nhận tạm toàn bộ + bổ sung KB3.** Phiên bản `kb-2026-11-21-4`.
> - **Chính sách `provisional`** (`ACCEPT_POLICY` trong `kb_pipeline/schema.py`): mọi thứ không `rejected`/`review`
>   đều `accepted`. Thực thể 2.231 accepted (1.717 qua luật, 514 tạm) / 32 rejected; quan hệ 6.473 accepted
>   (1.701 qua luật, toàn bộ là `EVIDENCED_BY`; 4.772 tạm) / 75 rejected; 0 candidate. Mọi quan hệ cấu trúc
>   (`PARENT_OF`, `IN_CATEGORY`, `USED_IN`, `MAPS_TO`, `NEAR`) vẫn là `accepted_by = provisional`, chưa có cái nào
>   qua luật. 99/331 Category nhận tạm `sibling_ok = true` từ đề xuất. Quay về luật: `--policy rule`.
> - **KB3 bổ sung:** +43 `PARENT_OF` (GraphQL → Apollo, OpenGL → GLSL, PostgreSQL → Supabase, OAuth → OpenID,
>   Android SDK → thành phần UI...), 29 Category mới (Cloud Compute, Object Storage, SQL Dialects, Linux
>   Distributions...), +151 `IN_CATEGORY` cho kỹ năng chưa có nhóm, +169 `USED_IN` (còn 26 kỹ năng không có nhóm vai
>   trò, chủ yếu kỹ năng mềm và ngoại ngữ, cố ý để trống), `NEAR` hypothesis đủ 91 cặp cho 14 nhóm (trước: 32), gộp
>   `vector databases` → `vector database`, `soap api` → `soap`.
> - **`NEAR` computed đổi từ Jaccard sang cosine:** Backend–Fullstack 0,038 → 0,15. Vẫn thấp hơn thang của ma trận M,
>   nên Rerank nên ưu tiên `hypothesis`.
> - **Bản chụp:** `export_snapshot.py --from-out` đọc `out/kb_*.jsonl`, không cần Neo4j. Đã xuất
>   `out/snapshot/kb-2026-11-21-4/` (`--accepted-only`): 1.710 kỹ năng, 348 cạnh cha/con, 407 kỹ năng có Category
>   `sibling_ok`, 666 alias chức danh, 63 alias cấp bậc, 307 alias ngành, 182 dòng `role_distance`.
> - Còn thiếu: 302 kỹ năng chưa có Category (phần lớn là concept), `df_jd`/`share_jd` (cần JD), ESCO, nguồn độc lập
>   thứ hai để chuyển `provisional` thành `rule`.

> **Cập nhật 21/11/2026 (2): thư ký chung `kb_pipeline`.** KB giờ dựng từ 3 gói trong `packs/` (kb1-roadmap,
> kb2-itviec, kb3-generated), phiên bản `kb-2026-11-21` (`out/versions.jsonl`). Đã có quy tắc nhận ở mục 6:
> thực thể 1.719 accepted / 485 candidate / 32 rejected; quan hệ 1.702 accepted (chủ yếu EVIDENCED_BY),
> 4.353 candidate, 75 rejected, 0 review. Hàng đợi duyệt rỗng. 19 PARENT_OF sai luật (concept làm cha/con) đã bỏ
> khỏi dữ liệu KB3. Định dạng gói: `docs/pack-format.md`.

> **Cập nhật 21/11/2026: thêm KB3 (tự sinh, G01–G09, `trust = low`).** Số liệu lấy từ `out/kb_checks.json`, chưa nạp
> Neo4j. KB gộp KB1 + KB2 + KB3: 1.744 `Skill` (1.712 còn dùng, 32 `rejected`), 302 `Category` (80 có `sibling_ok_suggest`),
> 124 `JobTitle` (0 chưa có nhóm), 60 `Major`, 6 `Level`, 30 `Source`. Quan hệ: 324 `PARENT_OF`, 1.535 `IN_CATEGORY`,
> 1.965 `USED_IN`, 135 `MAPS_TO`, 123 `NEAR` (32 hypothesis + 91 computed), 2.067 `EVIDENCED_BY`.
> 14 nhóm vai trò (thêm Embedded, Game, Design, Business, IT Support). 59 cặp skill trùng đã gộp (`merged_from`).
> Script Cypher của KB cuối cùng: `out/kb.cypher`. Tri thức KB3 chưa đủ điều kiện `accepted` (mục 6): cần duyệt
> hoặc nguồn thật đối chiếu. Phần dưới là trạng thái 05/11/2026, trước KB3.

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
