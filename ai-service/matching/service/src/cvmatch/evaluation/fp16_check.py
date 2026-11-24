"""T17 - fp16 cho BERTScore: chi chuyen khi lech so voi fp32 < 0,001 tren golden (thiet ke 07 muc 2, 11 muc 1.3).

Chay golden (qua buoc chuan bi cua pipeline) hai lan - fp32 roi fp16, NAP TUNG MODEL MOT (GPU 4 GB) - so moi
diem Recall cua moi bien the, moi cach chia S1/S2/S3. Ket luan: max |fp16 - fp32| < nguong va G1 fp16 khong
co test nao tu Dat -> Khong dat. Chi IN ket luan; doi `bertscore.dtype` + `models.embed.dtype` la viec cua nguoi dung
(doi dtype -> doi `bertscore_config` -> cache token cu khong dung nua).
"""

from __future__ import annotations

import gc
from dataclasses import dataclass

from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.evaluation.golden.runner import SPLITS, GoldenReport, run_golden
from cvmatch.rerank.bertscore.engine import BertScorer


@dataclass
class Fp16Result:
    max_diff: float
    where: str
    passed_fp32: dict[str, tuple[int, int]]
    passed_fp16: dict[str, tuple[int, int]]
    regressions: list[str]          # test S2 Dat o fp32 nhung Khong dat o fp16
    threshold: float
    timings: dict[str, float]

    @property
    def ok(self) -> bool:
        return self.max_diff < self.threshold and not self.regressions

    def to_markdown(self) -> str:
        out = ["# fp16 cho BERTScore (golden qua pipeline)", "",
               f"- max |fp16 − fp32| = **{self.max_diff:.5f}** ({self.where}), ngưỡng {self.threshold}",
               "- G1 S2 fp32: %d/%d · fp16: %d/%d" % (*self.passed_fp32["S2"], *self.passed_fp16["S2"]),
               f"- Test S2 đạt → không đạt khi fp16: {', '.join(self.regressions) or 'không có'}",
               f"- Thời gian golden: fp32 {self.timings['fp32_s']:.1f}s · fp16 {self.timings['fp16_s']:.1f}s", "",
               ("**Kết luận: giữ fp32** (lệch vượt ngưỡng hoặc có test bị hỏng)." if not self.ok else
                ("**Kết luận: fp16 đạt về độ chính xác nhưng CHẬM hơn fp32 trên GPU này** (không có tensor core, vd"
                 " GTX 1650): giữ fp32, chỉ chuyển khi cần tiết kiệm VRAM hoặc chạy trên GPU có tensor core."
                 if self.timings["fp16_s"] > self.timings["fp32_s"] else
                 "**Kết luận: đủ điều kiện chuyển fp16** (đặt `bertscore.dtype: fp16` và `models.embed.dtype: fp16` trong"
                 " bản config mới; cache token tính lại vì `bertscore_config` đổi)."))]
        return "\n".join(out) + "\n"


def _report(cfg, dtype: str, snapshot) -> GoldenReport:
    from cvmatch.core.models.bge_m3 import load_bge_m3

    e = cfg.models.embed
    enc = load_bge_m3(e.model, e.revision, e.device, dtype, e.batch_size, e.max_len, e.key)
    bcfg = cfg.bertscore.model_copy(update={"dtype": dtype})
    rep = run_golden(BertScorer(enc, bcfg, SkillMatcher(snapshot)), bare=False)
    del enc
    load_bge_m3.cache_clear()
    gc.collect()
    try:
        import torch

        torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass
    return rep


def check_fp16(cfg, snapshot, *, threshold: float = 0.001) -> Fp16Result:
    a = _report(cfg, "fp32", snapshot)
    b = _report(cfg, "fp16", snapshot)
    worst, where = 0.0, "-"
    for ra, rb in zip(a.results, b.results):
        for sp in SPLITS:
            for v, x in ra.scores.get(sp, {}).items():
                d = abs(x - rb.scores[sp][v])
                if d > worst:
                    worst, where = d, f"{ra.id}/{sp}/{v}"
    reg = [ra.id for ra, rb in zip(a.results, b.results) if ra.status.get("S2") is True and rb.status.get("S2") is False]
    return Fp16Result(worst, where, {s: a.passed(s) for s in SPLITS}, {s: b.passed(s) for s in SPLITS}, reg, threshold,
                      {"fp32_s": a.seconds, "fp16_s": b.seconds})
