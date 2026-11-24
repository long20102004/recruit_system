"""Viec chay nen don gian trong tien trinh (nap CV theo lo, match lau): `submit` -> `GET /jobs/{id}`.

Mot luong lam viec (cac viec deu can khoa chi muc nen chay song song khong nhanh hon). Mat khi
tien trinh khoi dong lai - backend Java goi lai neu thay `404`.
"""

from __future__ import annotations

import threading
import traceback
import uuid
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from cvmatch.api.logjson import log_event


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobRegistry:
    def __init__(self, max_kept: int = 500):
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cvmatch-job")
        self._jobs: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self.max_kept = max_kept

    def submit(self, kind: str, fn: Callable[[], Any]) -> dict:
        job_id = str(uuid.uuid4())
        job = {"job_id": job_id, "kind": kind, "status": "queued", "created_at": _now(), "finished_at": None,
               "result": None, "error": None}
        with self._lock:
            self._jobs[job_id] = job
            while len(self._jobs) > self.max_kept:
                self._jobs.popitem(last=False)

        def run():
            job["status"] = "running"
            try:
                job["result"] = fn()
                job["status"] = "done"
            except Exception as e:  # noqa: BLE001
                job["status"], job["error"] = "failed", f"{type(e).__name__}: {e}"
                log_event("job_failed", job_id=job_id, kind=kind, error=job["error"], trace=traceback.format_exc())
            job["finished_at"] = _now()

        self._pool.submit(run)
        return dict(job)

    def get(self, job_id: str) -> dict | None:
        j = self._jobs.get(job_id)
        return dict(j) if j else None

    def wait_all(self) -> None:
        """Cho moi viec da gui xong (dung trong test)."""
        self._pool.submit(lambda: None).result()

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)
