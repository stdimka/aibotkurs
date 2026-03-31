from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class TgSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)


class TgSourceCreate(TgSourceBase):
    """Схема для добавления нового источника"""
    pass


class TgSourceUpdate(BaseModel):
    """Схема для обновления источника"""
    name: str | None = Field(None, min_length=1, max_length=100)


class TgSourceOut(TgSourceBase):
    """Схема для вывода источника"""
    last_post_at: datetime | None = None

