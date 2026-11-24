# T17 · Backlog (làm sau, mỗi mục tách thành một phần việc riêng khi tới lượt)

Chỉ làm khi đã xong T13 (P1) và có số liệu từ T14. Mỗi mục cần ablation chứng minh có ích mới giữ (thiết kế 09 mục 4.5).

| Mục | Thiết kế | Ghi chú |
| --- | --- | --- |
| Explain bằng LLM (chọn câu + mã bằng chứng, code điền số; EX4 kiểm, trượt → mẫu) | 08 mục 4 | `explain.mode = llm`; không gửi `text_raw`; đo tỉ lệ quay về mẫu. Chọn model cục bộ/API theo Q mở 18 |
| RR5 LLM kiểm chứng vùng biên [N−10, N+10] | 07 phụ lục | chỉ hạ `c_j`, kiểm quote là chuỗi con; cache theo khoá ở phụ lục; thí nghiệm R-X4 |
| Mốc đối chứng R-X1 cross-encoder `bge-reranker-v2-m3`, R-X2 ColBERT bge-m3, R-X3 backbone khác | 09 mục 4.4 | cắm vào engine T10 dưới dạng backend thay thế `recall_matrix` |
| LoRA fine-tune bge-m3 cho BERTScore | 12 (toàn bộ) | dataset JSONL, mẫu âm khó, loss CE + KL, thí nghiệm R-E15; đổi `bertscore_config` → xoá cache, chạy lại G1 |
| HyDE ngược (sinh JD mẫu từ CV lúc nạp) | 06 mục 6 | thêm một vector vào Luồng A |
| Phục hồi dấu tiếng Việt cho CV `no_diacritics` | 04 A4, 11 Q12 | chọn công cụ và đo trước |
| Quy trình chuyển phiên bản an toàn (KB/chuẩn hoá/model mới, ghi song song, chuyển cùng lúc) | 03 "Khi có thay đổi" | mở rộng lệnh `reprocess` của T05 |
| Feature để sau: A3 độ mới kỹ năng (`last_used`), B6 lĩnh vực, C2 chứng chỉ | 07 mục 5.11 | weight 0 cho tới khi ablation |
| Hiệu chuẩn điểm isotonic từ phản hồi HR | 07 mục 5.10, 11 P4 | |
| fp16 cho BERTScore sau khi kiểm lệch < 0,001 trên golden | 07 mục 2 | |

## Trạng thái (23/11/2026)

| Mục | Trạng thái |
| --- | --- |
| fp16 cho BERTScore | **đã đo** (`cvmatch eval fp16`, `services/cvmatch-ai/reports/fp16_check.md`): lệch tối đa 0,00029 < 0,001, G1 26/26 cả hai; nhưng fp16 **chậm hơn** fp32 gần 4 lần trên GTX 1650 (không có tensor core) → giữ fp32 |
| Quy trình chuyển phiên bản an toàn | **một phần**: ghi song song (`cvmatch reprocess cv/jd`), liệt kê bộ khoá (`cvmatch db versions`), đánh giá bản mới (`eval ablation --kb-version`), chuyển = sửa `active.yaml`. Chưa có lệnh dọn bản cũ / quay lại tự động |
| Explain LLM, RR5, HyDE ngược | **chờ chốt**: chọn model cục bộ hay API (Q mở 18) và chính sách gửi dữ liệu (không gửi `text_raw`) |
| R-X1 cross-encoder, R-X2 ColBERT, R-X3 backbone khác | chờ nhãn thật: so trên nhãn tổng hợp không có nghĩa (mọi cấu hình nDCG ≈ 0,95–0,97); kiểm model card + giấy phép trước khi tải |
| LoRA fine-tune (file 12) | chờ dữ liệu cặp có nhãn (file 12 cần hàng nghìn cặp + mẫu âm khó) |
| Phục hồi dấu | chọn công cụ và đo trước (chưa chọn) |
| A3 / B6 / C2, isotonic | chờ ablation / phản hồi HR (P4) |
