from pydantic import BaseModel, HttpUrl
from datetime import datetime

class PostsItemOut(BaseModel):
    title: str
    url: str | None = None
    summary: str | None = None
    source: str
    published_at: datetime
    image: str | None = None  # 🔹 Новое опциональное поле
