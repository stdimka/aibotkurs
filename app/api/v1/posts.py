from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.dependencies import get_redis
from app.schemas.posts import PostsItemOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/posts",
    tags=["posts"],
    responses={404: {"description": "Posts not found"}},
)

@router.get("/", response_model=list[PostsItemOut])
async def list_posts(
    source: str | None = Query(None, description="Фильтр по источнику"),
    limit: int = Query(50, ge=1, le=500),
    redis = Depends(get_redis),
):
    """
    Получить список сырых новостей из Redis.
    Если source не указан — все источники.
    """
    try:
        pattern = f"news:raw:{source}:*" if source else "news:raw:*:*"
        keys = await redis.keys(pattern)

        if not keys:
            return []

        # сортировка по дате из ключа (yyyy-mm-ddT...)
        keys_sorted = sorted(keys, reverse=True)[:limit]

        news_list = []
        for key in keys_sorted:
            if isinstance(key, bytes):
                key = key.decode()

            data = await redis.hgetall(key)
            if not data:
                continue

            try:
                news_list.append(PostsItemOut(
                    title=data["title"],
                    url=data.get("url"),
                    summary=data.get("summary"),
                    source=data["source"],
                    published_at=data["published_at"]
                ))
            except KeyError as e:
                logger.warning(f"Некорректная новость в Redis {key}: {e}")
                continue

        return news_list

    except Exception as e:
        logger.exception("Ошибка при получении новостей")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching news"
        )
