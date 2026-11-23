"""Bo sinh du lieu demo: tat dinh, moi CV/JD qua schema A1/B1, co du cac kieu da dang."""

import json
from collections import Counter

from cvmatch.demo.generate import generate
from cvmatch.ingest.cv.adapter import adapt_cv
from cvmatch.ingest.cv.schema import validate_cv
from cvmatch.ingest.jd.schema import adapt_jd, validate_jd


def test_generate_deterministic_and_valid(tmp_path):
    a = generate(tmp_path / "a", n_cv=60, seed=5, n_updates=4)
    generate(tmp_path / "b", n_cv=60, seed=5, n_updates=4)
    assert a["n_cv"] == 60 and a["n_jd"] == 30
    fa = sorted(p.name for p in (tmp_path / "a" / "cv").glob("*.json"))
    assert fa == sorted(p.name for p in (tmp_path / "b" / "cv").glob("*.json"))
    assert (tmp_path / "a" / "cv" / fa[7]).read_text(encoding="utf-8") == \
        (tmp_path / "b" / "cv" / fa[7]).read_text(encoding="utf-8")
    for f in (tmp_path / "a" / "cv").glob("*.json"):
        validate_cv(adapt_cv(json.loads(f.read_text(encoding="utf-8"))))
    for f in (tmp_path / "a" / "jd").glob("*.json"):
        validate_jd(adapt_jd(json.loads(f.read_text(encoding="utf-8"))))
    m = json.loads((tmp_path / "a" / "manifest.json").read_text(encoding="utf-8"))
    assert len(m["cv_updates"]) == 4 and Counter(v["status"] for v in m["jd"].values())["open"] == 27
    upd = next(iter(m["cv_updates"].values()))["updates"]
    v1 = json.loads((tmp_path / "a" / "cv" / upd).read_text(encoding="utf-8"))
    v2 = json.loads((tmp_path / "a" / "cv_updates" / upd.replace(".json", "_v2.json")).read_text(encoding="utf-8"))
    assert v1["email"] == v2["email"] and v1 != v2
    assert len({v["group"] for v in m["cv"].values()}) >= 8
