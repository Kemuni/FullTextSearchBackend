import datetime

from pydantic import BaseModel, Field


class Post(BaseModel):
    id: int
    text: str
    created_date: datetime.datetime | None = None
    rubrics: list[str] = Field(default_factory=list)
