from fastapi import APIRouter, Depends, Query
from app.dependencies import get_redis
from app.schemas.history import DupHistoryOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/history",
    tags=["history"],
    responses={404: {"description": "Keyword not found"}},
)

@router.get("/history/dup", response_model=list[DupHistoryOut])
async def get_dup_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    redis = Depends(get_redis),
):
    """
    История дедупликации (хэши заголовков + summary)
    """
    keys = await redis.keys("news:dup:*")
    if not keys:
        return []

    keys = sorted(keys)[skip : skip + limit]

    result = []

    for key in keys:
        data = await redis.hgetall(key)
        if not data:
            continue

        result.append(
            DupHistoryOut(
                hash=data.get("hash"),
                title=data.get("title"),
                summary=data.get("summary"),
                source=data.get("source"),
                published_at=data.get("published_at"),
            )
        )

    return result
