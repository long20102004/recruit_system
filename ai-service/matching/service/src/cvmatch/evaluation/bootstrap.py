"""Bootstrap ghep cap theo truy van (JD), khoang tin cay 95% cho chenh lech hai cau hinh (thiet ke 09 muc 4.5).

Lay mau co hoan lai tren TAP JD (giu nguyen cap A/B cua cung JD) -> phan phoi cua mean(B - A).
Chenh lech nho hon khoang tin cay (CI chua 0) thi coi la nhieu, trinh bay nhu xu huong.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BootstrapResult:
    diff: float                  # mean(B - A) tren cac JD chung
    lo: float
    hi: float
    n: int
    p_gt0: float                 # ti le mau bootstrap co diff > 0

    @property
    def significant(self) -> bool:
        return self.lo > 0 or self.hi < 0


def paired_bootstrap(a: Mapping[str, float | None], b: Mapping[str, float | None], *, n_boot: int = 2000,
                     seed: int = 13, alpha: float = 0.05) -> BootstrapResult | None:
    keys = sorted(k for k in a if k in b and a[k] is not None and b[k] is not None)
    if not keys:
        return None
    d = np.array([b[k] - a[k] for k in keys], dtype=np.float64)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return BootstrapResult(float(d.mean()), float(lo), float(hi), len(d), float((means > 0).mean()))
