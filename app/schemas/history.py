from pydantic import BaseModel
from datetime import datetime

class DupHistoryOut(BaseModel):
    hash: str
    title: str
    summary: str
    source: str
    published_at: datetime
