from fastapi import APIRouter, Depends, Query, HTTPException, status
from datetime import datetime

from app.dependencies import get_redis
from app.schemas.posts import PostsItemOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/filtered_posts",
    tags=["filtered_posts"],
    responses={404: {"description": "Posts not found"}},
)

@router.get("/", response_model=list[PostsItemOut])
async def list_filtered_posts(
    skip: int = Query(0, ge=0, description="Пропустить N элементов"),
    limit: int = Query(50, ge=1, le=500, description="Максимум элементов"),
    redis = Depends(get_redis),
):
    """Получить список свежих новостей из Redis"""
    try:
        keys = await redis.keys("news:filtered:*")
        if not keys:
            return []

        # сортируем по дате публикации (из ключа)
        keys_sorted = sorted(keys, reverse=True)[skip : skip + limit]
        news_list = []

        for key in keys_sorted:
            if isinstance(key, bytes):
                key = key.decode()

            data = await redis.hgetall(key)
            if not data:
                continue

            # приводим published_at к datetime
            pub_at_raw = data.get("published_at")
            if pub_at_raw:
                pub_at = datetime.fromisoformat(pub_at_raw)
            else:
                pub_at = None

            news_list.append(
                PostsItemOut(
                    title=data.get("title", ""),
                    url=data.get("url") or None,
                    summary=data.get("summary"),
                    source=data.get("source", ""),
                    published_at=pub_at,
                )
            )

        return news_list

    except Exception:
        logger.exception("Ошибка при получении свежих новостей")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching fresh news",
        )
