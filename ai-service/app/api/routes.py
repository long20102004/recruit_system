from fastapi import APIRouter, HTTPException

from app.core.config import BASE_MODEL_NAME, LORA_PATH
from app.core.logging import logger
from app.schemas.cv import CVRequest, CVResponse
from app.services.generator import generate_cv
from app.services.model_loader import state
from app.utils.json_parse import extract_json
from app.utils.text import clean_cv_text

router = APIRouter()


@router.get("/health")
def health():
    if state.engine is None:
        raise HTTPException(
            status_code=503,
            detail="Model chưa được load"
        )

    info = {"status": "ok", "engine": state.engine}
    if state.engine == "llama_cpp":
        info["model"] = state.gguf_path_used
    else:
        info["model"] = BASE_MODEL_NAME
        info["lora"] = LORA_PATH
        info["device"] = str(next(state.model.parameters()).device)
    return info


@router.post("/api/v1/extract-cv", response_model=CVResponse)
def extract_cv(request: CVRequest):
    if state.engine is None:
        raise HTTPException(
            status_code=503,
            detail="Model chưa được load"
        )

    if not request.cv_text.strip():
        raise HTTPException(
            status_code=400,
            detail="cv_text không được rỗng"
        )

    cv_text = clean_cv_text(request.cv_text)

    logger.info(f"CV length: {len(cv_text)} chars")

    try:
        raw_output = generate_cv(cv_text)

        logger.info("Raw model output:")
        logger.info(raw_output)

        data = extract_json(raw_output)

        return {"data": data}

    except Exception as e:
        logger.exception("CV extraction failed")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
