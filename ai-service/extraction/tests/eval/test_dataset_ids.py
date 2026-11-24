"""Sample ids: a row's own "id" wins; rows without one fall back to sha1(input)[:12]. Fictional data only."""

import hashlib
import json

from eval.dataset import load_split

PROFILE = {"personal_info": {"full_name": "Nguyen Van Fiction", "email": None, "phone": None, "github_url": None}}


def _write(tmp_path, rows):
    path = tmp_path / "split.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path


def test_row_id_is_used_when_present(tmp_path):
    path = _write(tmp_path, [{"id": "v6-test-004", "input": "Fictional CV A", "output": json.dumps(PROFILE)}])
    assert [s.id for s in load_split(path)] == ["v6-test-004"]


def test_sha1_fallback_without_id(tmp_path):
    text = "Fictional CV B"
    path = _write(tmp_path, [{"input": text, "output": PROFILE}, {"id": "  ", "input": text + "!", "output": PROFILE}])
    assert [s.id for s in load_split(path)] == [hashlib.sha1(text.encode("utf-8")).hexdigest()[:12],
                                               hashlib.sha1((text + "!").encode("utf-8")).hexdigest()[:12]]
