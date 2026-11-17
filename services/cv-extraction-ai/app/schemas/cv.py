from pydantic import BaseModel


class CVRequest(BaseModel):
    cv_text: str


class CVResponse(BaseModel):
    data: dict
