"""Log co cau truc (JSON moi dong) cho API va `run-e2e`: `run_id` xuyen suot, thoi gian tung tang."""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOGGER = "cvmatch.run"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        d = {"ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
             "level": record.levelname.lower(), "event": record.getMessage()}
        d.update(getattr(record, "fields", {}) or {})
        if record.exc_info:
            d["exc"] = self.formatException(record.exc_info)
        return json.dumps(d, ensure_ascii=False, default=str)


def setup_json_logging(path: str | Path | None = None, *, stream: bool = False) -> logging.Logger:
    """Gan handler JSON cho logger `cvmatch.run` (file va / hoac stderr). Goi lai khong nhan doi handler."""
    log = logging.getLogger(LOGGER)
    log.setLevel(logging.INFO)
    log.propagate = False
    want = []
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        want.append(logging.FileHandler(path, encoding="utf-8"))
    if stream:
        want.append(logging.StreamHandler(sys.stderr))
    for h in want:
        if any(type(x) is type(h) and getattr(x, "baseFilename", None) == getattr(h, "baseFilename", None)
               for x in log.handlers):
            h.close()
            continue
        h.setFormatter(JsonFormatter())
        log.addHandler(h)
    return log


def detach_file(path: str | Path) -> None:
    log = logging.getLogger(LOGGER)
    target = str(Path(path).resolve())
    for h in list(log.handlers):
        if getattr(h, "baseFilename", None) == target:
            log.removeHandler(h)
            h.close()


def log_event(event: str, *, level: int = logging.INFO, **fields) -> None:
    logging.getLogger(LOGGER).log(level, event, extra={"fields": fields})


class Timer:
    """`with Timer() as t: ...` -> t.s (giay)."""

    def __enter__(self) -> "Timer":
        self._t = time.perf_counter()
        self.s = 0.0
        return self

    def __exit__(self, *exc) -> None:
        self.s = round(time.perf_counter() - self._t, 4)
