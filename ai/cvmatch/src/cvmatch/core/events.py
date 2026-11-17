"""Su kien sau commit (thiet ke 04 A11: "chi sau khi commit moi cap nhat bo nho").

Don gian: danh sach callback trong tien trinh. Retrieve (T08) dang ky `on("cv_committed", ...)` de
them hang vao ma tran; T10 dang ky `on("cv_deleted", ...)` de xoa cache BERTScore.
Callback loi khong lam hong viec nap (da commit) - chi ghi log.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CvCommitted:
    cv_id: str
    replaced_cv_id: str | None


@dataclass(frozen=True)
class CvDeleted:
    cv_id: str
    bullet_texts_raw: tuple[str, ...] = field(default=())


@dataclass(frozen=True)
class JdCommitted:
    jd_id: str
    version: int


@dataclass(frozen=True)
class JdStatusChanged:
    jd_id: str
    version: int
    status: str


_HANDLERS: dict[str, list[Callable]] = defaultdict(list)


def on(event: str, handler: Callable) -> None:
    _HANDLERS[event].append(handler)


def off(event: str, handler: Callable) -> None:
    if handler in _HANDLERS[event]:
        _HANDLERS[event].remove(handler)


def emit(event: str, payload) -> None:
    for h in list(_HANDLERS[event]):
        try:
            h(payload)
        except Exception:  # noqa: BLE001
            log.exception("handler su kien %s loi", event)
