# fp16 cho BERTScore (golden qua pipeline)

- max |fp16 − fp32| = **0.00029** (T13/S1/B_diluted), ngưỡng 0.001
- G1 S2 fp32: 26/26 · fp16: 26/26
- Test S2 đạt → không đạt khi fp16: không có
- Thời gian golden: fp32 5.4s · fp16 19.7s

**Kết luận: fp16 đạt về độ chính xác nhưng CHẬM hơn fp32 trên GPU này** (không có tensor core, vd GTX 1650): giữ fp32, chỉ chuyển khi cần tiết kiệm VRAM hoặc chạy trên GPU có tensor core.
