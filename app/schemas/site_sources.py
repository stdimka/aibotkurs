from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

class SiteSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    url: HttpUrl = Field(..., max_length=500)


class SiteSourceCreate(SiteSourceBase):
    """Схема для добавления нового источника"""
    pass


class SiteSourceUpdate(BaseModel):
    """Схема для обновления источника"""
    name: str | None = Field(None, min_length=1, max_length=100)
    url: HttpUrl | None = Field(None, max_length=500)


class SiteSourceOut(SiteSourceBase):
    """Схема для вывода источника"""
    last_post_at: datetime | None = None


