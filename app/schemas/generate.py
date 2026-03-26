from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=300)
    summary: str = Field(..., min_length=10, max_length=2000)

class GenerateResponse(BaseModel):
    original_title: str
    new_title: str
    generated_post: str


class GeneratedPostOut(GenerateResponse):
    key: str = Field(..., description="Redis-ключ записи")
    hash: str = Field(..., description="MD5 хеш оригинала")