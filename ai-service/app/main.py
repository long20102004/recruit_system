from fastapi import FastAPI

from app.api.routes import router
from app.services.model_loader import load_model

app = FastAPI(
    title="CV Extraction AI Service"
)

app.include_router(router)


@app.on_event("startup")
def startup():
    load_model()
