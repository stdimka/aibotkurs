from pydantic import BaseModel, Field


class KeywordBase(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200, strip_whitespace=True)


class KeywordCreate(KeywordBase):
    """Схема для создания нового ключевого слова"""
    pass


class KeywordUpdate(BaseModel):
    """Схема для обновления ключевого слова"""
    keyword: str | None = Field(None, min_length=1, max_length=200)


class KeywordOut(KeywordBase):
    """Схема для вывода ключевого слова"""
    pass  # временная метка убрана
