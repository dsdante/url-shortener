from pydantic import BaseModel


class LinkCreate(BaseModel):
    url: str


class LinkResponse(BaseModel):
    code: str


class StatsResponse(BaseModel):
    code: str
    url: str
    clicks: int