from fastapi import FastAPI

from app.api.routes import router
from app.core import config
from app.core.logging import logger
from app.services.model_loader import load_model

app = FastAPI(
    title="CV Extraction AI Service"
)

app.include_router(router)


@app.on_event("startup")
def startup():
    if config.LOG_CV_CONTENT:
        logger.warning(
            "LOG_CV_CONTENT=true: raw model output (có thể chứa dữ liệu cá nhân) sẽ được ghi log. Không bật ở production."
        )
    load_model()
