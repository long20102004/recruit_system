"""
HireLens Interview Scoring API

Chạy:
  cd AI
  source .venv/bin/activate
  uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

Docs: http://localhost:8000/docs
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from .io_utils import load_questions, questions_by_id
from .semantic import get_scorer
from .scoring import clear_calibration_cache, evaluate_by_id, evaluate_question, load_calibration

DEFAULT_MODE = os.getenv("HIRELENS_MODE", "bertscore")  # fast | bertscore | finetune
DEFAULT_DEVICE = os.getenv("HIRELENS_DEVICE")  # cpu | cuda | None

@asynccontextmanager
async def lifespan(app):
    ready_model()
    yield


app = FastAPI(
    title="HireLens Interview Scoring API",
    description=(
        "Chấm câu trả lời phỏng vấn theo barem (coverage) + BERTScore/fast + Ridge calibration. "
        "Backend Spring Boot gọi POST /v1/interview/evaluate."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("HIRELENS_CORS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CriterionIn(BaseModel):
    key: str
    label: str
    # Spring có thể gửi weight chưa chuẩn hóa; normalize trong endpoint
    weight: float = Field(ge=0, default=1.0, allow_inf_nan=False)
    hints: list[str] = Field(default_factory=list, max_length=30)
    reference_answers: list[str] = Field(default_factory=list, max_length=5)
    misconceptions: list[str] = Field(default_factory=list, max_length=5)


class EvaluateRequest(BaseModel):
    """
    Cách 1: gửi question_id (lấy barem từ data/questions.json).
    Cách 2: gửi reference_answer + criteria (Spring tự truyền barem từ DB).
    Ưu tiên cách 2 nếu có đủ reference + criteria.
    """

    answer: str = Field(..., min_length=1, max_length=4000, description="Câu trả lời ứng viên")
    question_id: str | None = None
    question: str | None = None
    reference_answer: str | None = None
    criteria: list[CriterionIn] | None = Field(default=None, max_length=12)
    mode: Literal["fast", "bertscore", "finetune"] | None = None
    include_debug: bool = False

    @model_validator(mode="after")
    def check_source(self) -> EvaluateRequest:
        if not self.answer.strip(): raise ValueError("Câu trả lời không được chỉ chứa khoảng trắng")
        if self.criteria and len({c.key for c in self.criteria}) != len(self.criteria):
            raise ValueError("Rubric keys must be unique")
        has_id = bool(self.question_id)
        has_inline = bool(
            self.reference_answer
            and self.reference_answer.strip()
            and self.criteria
            and len(self.criteria) > 0
        )
        if not has_id and not has_inline:
            raise ValueError(
                "Cần question_id hoặc (reference_answer + criteria không rỗng)"
            )
        return self


def _normalize_criteria(criteria: list[CriterionIn]) -> list[dict[str, Any]]:
    raw = [max(0.0, float(c.weight)) for c in criteria]
    total = sum(raw)
    if total <= 0: raise ValueError("Rubric weights must have a positive total")
    out: list[dict[str, Any]] = []
    for c, w in zip(criteria, raw, strict=True):
        out.append(
            {
                "key": c.key,
                "label": c.label,
                "weight": (w / total) if total else 0.0,
                "hints": list(c.hints or []),
                "reference_answers": list(c.reference_answers or [c.label]),
                "misconceptions": list(c.misconceptions or []),
            }
        )
    return out


class EvaluateResponse(BaseModel):
    question_id: str | None = None
    predicted_score: float
    score_scale: str
    covered_points: list[str]
    missing_points: list[str]
    comment: str
    model_version: str | None = None
    mode: str
    bertscore_precision: float | None = None
    bertscore_recall: float | None = None
    bertscore_f1: float | None = None
    coverage_score: float = 0
    criterion_results: list[dict[str, Any]] = Field(default_factory=list)
    label_source: str | None = None
    debug: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    default_mode: str
    calibration_loaded: dict[str, bool]
    model_loaded: bool = False


def ready_model():
    if DEFAULT_MODE == "finetune":
        from .regressor import load_regressor
        load_regressor()
        return
    load_calibration(DEFAULT_MODE)
    if DEFAULT_MODE == "bertscore":
        from .semantic import get_scorer
        calib = load_calibration(DEFAULT_MODE)
        get_scorer(calib.get("bert_model_type") or "bert-base-multilingual-cased", DEFAULT_DEVICE or "cpu")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    loaded = {}
    for m in ("fast", "bertscore"):
        try:
            load_calibration(m)
            loaded[m] = True
        except FileNotFoundError:
            loaded[m] = False
    finetune_loaded = False
    if DEFAULT_MODE == "finetune":
        from .regressor import load_regressor
        try:
            load_regressor()
            finetune_loaded = True
        except FileNotFoundError:
            finetune_loaded = False
    return HealthResponse(
        status="ok",
        default_mode=DEFAULT_MODE,
        calibration_loaded=loaded,
        model_loaded=finetune_loaded or DEFAULT_MODE == "fast" or get_scorer.cache_info().currsize > 0,
    )


@app.get("/v1/questions")
def list_questions() -> dict[str, Any]:
    """Danh sách câu hỏi demo trong data/questions.json (tiện test)."""
    bundle = load_questions()
    items = [
        {
            "id": q["id"],
            "topic": q.get("topic"),
            "skill": q.get("skill"),
            "difficulty": q.get("difficulty"),
            "question": q["question"],
            "rank": q.get("rank"),
        }
        for q in bundle["questions"]
    ]
    return {"role": bundle["meta"].get("role"), "questions": items}


@app.get("/v1/questions/{question_id}")
def get_question(question_id: str) -> dict[str, Any]:
    qmap = questions_by_id()
    if question_id not in qmap:
        raise HTTPException(404, f"Không tìm thấy question_id={question_id}")
    return qmap[question_id]


@app.post("/v1/interview/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest) -> EvaluateResponse:
    mode = req.mode or DEFAULT_MODE
    try:
        use_inline = bool(
            req.reference_answer
            and req.reference_answer.strip()
            and req.criteria
            and len(req.criteria) > 0
        )
        if use_inline:
            question = {
                "id": req.question_id,
                "question": req.question or "",
                "reference_answer": req.reference_answer,
                "criteria": _normalize_criteria(req.criteria),
            }
            result = evaluate_question(
                answer=req.answer,
                question=question,
                mode=mode,
                device=DEFAULT_DEVICE,
                include_debug=req.include_debug,
            )
        else:
            assert req.question_id
            result = evaluate_by_id(
                req.question_id,
                req.answer,
                mode=mode,
                device=DEFAULT_DEVICE,
                include_debug=req.include_debug,
            )
    except FileNotFoundError as e:
        raise HTTPException(
            503,
            str(e) + " — chạy train_calibration trước khi start API.",
        ) from e
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Lỗi chấm điểm: {e}") from e

    return EvaluateResponse(**result)


@app.post("/v1/admin/reload-calibration")
def reload_calibration() -> dict[str, str]:
    """Gọi sau khi train lại Ridge để API nạp hệ số mới (không restart)."""
    clear_calibration_cache()
    return {"status": "reloaded"}
