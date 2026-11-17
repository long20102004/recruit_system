"""A2. Chong trung (thiet ke 04 A2).

- `content_hash` = SHA-256 cua canonical JSON (sap khoa, bo khoang trang thua) cua CV DAU VAO.
- `candidate_key` = HMAC-SHA256(khoa bi mat, email chuan hoa), khong co email thi sdt chuan hoa.
  Dung HMAC thay hash thuong de khong do nguoc duoc bang danh sach email.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any

from cvmatch.ingest.cv.record import CvContext, CvRecord, DuplicateCV


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def content_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    e = re.sub(r"\s+", "", str(email)).lower()
    return e if "@" in e else None


def normalize_phone(phone: str | int | None) -> str | None:
    if phone is None:
        return None
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("84") and len(digits) >= 11:
        digits = "0" + digits[2:]
    return digits if len(digits) >= 9 else None


def candidate_key(email: str | None, phone: str | int | None, key: bytes) -> str | None:
    ident = normalize_email(email)
    kind = "email"
    if ident is None:
        ident, kind = normalize_phone(phone), "phone"
    if ident is None:
        return None
    mac = hmac.new(key, f"{kind}:{ident}".encode("utf-8"), hashlib.sha256).hexdigest()
    return f"hmac:{mac}"


def step_a02(rec: CvRecord, raw_input: Any, ctx: CvContext) -> CvRecord:
    rec.content_hash = content_hash(raw_input)
    rec.candidate_key = candidate_key(rec.raw_json.get("email"), rec.raw_json.get("phone"), ctx.hmac_key)
    if rec.candidate_key is None:
        rec.add_flag("no_identity")

    if ctx.dedup is not None:
        existing = ctx.dedup.find_by_hash(rec.content_hash)
        if existing is not None:
            raise DuplicateCV(existing, rec.content_hash)
        if rec.candidate_key is not None:
            prev = ctx.dedup.latest_version(rec.candidate_key)
            if prev is not None:
                rec.replaces_cv_id, prev_version = prev
                rec.version = prev_version + 1
    rec.is_latest = True
    return rec
