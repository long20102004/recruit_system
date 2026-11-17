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
