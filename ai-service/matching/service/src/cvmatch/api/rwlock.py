"""Khoa doc - ghi cho `Services` (S05, V-11).

- Doc (match, explain): nhieu luong cung luc.
- Ghi (nap CV / JD, xoa, doi trang thai, xem truoc CV, dung lai chi muc): doc quyen.
- Uu tien ghi: co luong cho ghi thi luong doc moi phai doi (khong de nap CV bi doi mai).
- Re-entrant cho luong dang giu khoa ghi (vd `preview_cv` giu ghi roi goi `match_cv`, `explain`); luong dang giu
  khoa doc thi KHONG duoc xin ghi (se ket) - code cua Services khong lam vay.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager


class RWLock:
    def __init__(self) -> None:
        self._cond = threading.Condition(threading.Lock())
        self._readers: dict[int, int] = {}       # thread id -> so lan giu doc
        self._writer: int | None = None
        self._write_depth = 0
        self._waiting_writers = 0

    @contextmanager
    def read(self):
        me = threading.get_ident()
        with self._cond:
            if self._writer != me:
                while self._writer is not None or (self._waiting_writers and me not in self._readers):
                    self._cond.wait()
            self._readers[me] = self._readers.get(me, 0) + 1
        try:
            yield
        finally:
            with self._cond:
                n = self._readers[me] - 1
                if n:
                    self._readers[me] = n
                else:
                    del self._readers[me]
                self._cond.notify_all()

    @contextmanager
    def write(self):
        me = threading.get_ident()
        with self._cond:
            if self._writer == me:
                self._write_depth += 1
            else:
                if me in self._readers:
                    raise RuntimeError("dang giu khoa doc thi khong xin khoa ghi duoc")
                self._waiting_writers += 1
                try:
                    while self._writer is not None or self._readers:
                        self._cond.wait()
                finally:
                    self._waiting_writers -= 1
                self._writer, self._write_depth = me, 1
        try:
            yield
        finally:
            with self._cond:
                self._write_depth -= 1
                if not self._write_depth:
                    self._writer = None
                self._cond.notify_all()
