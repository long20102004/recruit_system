import traceback
import uuid

from fastapi import APIRouter, HTTPException, Response

from app.core import config
from app.core.errors import InputTooLongError, ModelBusyError
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
        info["model"] = config.BASE_MODEL_NAME
        info["lora"] = config.LORA_PATH
        info["device"] = str(next(state.model.parameters()).device)

    info["context_tokens"] = getattr(state, "context_tokens", None)
    fallback_reason = getattr(state, "fallback_reason", None)
    if fallback_reason is not None:
        info["fallback_reason"] = fallback_reason

    return info


@router.post("/api/v1/extract-cv", response_model=CVResponse)
def extract_cv(request: CVRequest, response: Response):
    request_id = uuid.uuid4().hex[:12]
    response.headers["X-Request-ID"] = request_id
    req_headers = {"X-Request-ID": request_id}

    if state.engine is None:
        raise HTTPException(
            status_code=503,
            detail="Model chưa được load",
            headers=req_headers,
        )

    if not request.cv_text.strip():
        raise HTTPException(
            status_code=400,
            detail="cv_text không được rỗng",
            headers=req_headers,
        )

    cv_text = clean_cv_text(request.cv_text)

    logger.info("request_id=%s CV length: %d chars", request_id, len(cv_text))

    try:
        raw_output = generate_cv(cv_text)

        if config.LOG_CV_CONTENT:
            logger.info("Raw model output:")
            logger.info(raw_output)

        data = extract_json(raw_output)

        return {"data": data}

    except InputTooLongError as e:
        logger.warning(
            "CV extraction rejected request_id=%s error=%s",
            request_id,
            type(e).__name__,
        )
        raise HTTPException(
            status_code=413,
            detail=str(e),
            headers=req_headers,
        )
    except ModelBusyError as e:
        logger.warning(
            "CV extraction rejected request_id=%s error=%s",
            request_id,
            type(e).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail=str(e),
            headers=req_headers,
        )
    except Exception as e:
        if config.LOG_CV_CONTENT:
            logger.exception("CV extraction failed")
        else:
            logger.error(
                "CV extraction failed request_id=%s type=%s\n%s",
                request_id,
                type(e).__name__,
                "".join(traceback.format_tb(e.__traceback__)),
            )
        raise HTTPException(
            status_code=500,
            detail=f"Trích xuất CV thất bại (request_id={request_id})",
            headers=req_headers,
        )
