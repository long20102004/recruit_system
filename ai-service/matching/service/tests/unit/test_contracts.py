import pytest
from pydantic import ValidationError

from cvmatch.core.contracts import FinalItem, RerankRequest


def test_rerank_request_roundtrip():
    req = RerankRequest(
        direction="jd_to_cv",
        run_id="r1",
        retrieve_run_id="m1",
        jd_id="JD-0412",
        jd_version=1,
        config_version="rr-1.0",
        bertscore_config="bge-m3@5617a9f61b/L24/noidf/norescale/2048/mask1",
        candidates=[
            {"cv_id": "c1", "rank": 1, "s": {"dense": 0.71, "bm25": 14.2, "skill": 0.8, "resp": 0.66},
             "n": {"dense": 1, "bm25": 0.62, "skill": 1, "resp": 0.87}, "fused": 0.87}
        ],
    )
    assert req.N == 30
    assert RerankRequest.model_validate_json(req.model_dump_json()) == req


def test_final_item_rejects_bad_gate_cap():
    with pytest.raises(ValidationError):
        FinalItem(cv_id="c1", rank=1, score=79, score_raw=0.794, gate_cap=60,
                  cap_applied=False, features={})


def test_final_item_minimal():
    item = FinalItem(cv_id="c1", rank=1, score=79, score_raw=0.794, gate_cap=100,
                     cap_applied=False, features={"A1": 0.8, "B4": 0.74})
    assert item.features.C1 is None
    assert item.skill_facts.missing == []
