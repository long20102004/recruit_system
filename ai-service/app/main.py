from fastapi import FastAPI

from app.api.routes import router
from app.core import config
from app.core.logging import logger
from app.kb.store import kb_state, load_kb
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
    if config.KG_ENABLED:
        kb_state["kb"] = load_kb(
            config.KB_DSN,
            config.KB_SEED_DIR,
            neo4j_uri=config.NEO4J_URI,
            neo4j_user=config.NEO4J_USER,
            neo4j_password=config.NEO4J_PASSWORD,
        )
