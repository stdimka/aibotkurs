from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_redis
from app.schemas.keywords import KeywordCreate, KeywordUpdate, KeywordOut
from app.utils.logging import get_logger

from starlette.concurrency import run_in_threadpool

from app.redis_sync import get_sync_redis
from app.services.keyword_service import get_all_keywords


logger = get_logger(__name__)

router = APIRouter(
    prefix="/keywords",
    tags=["keywords"],
    responses={404: {"description": "Keyword not found"}},
)



@router.get("/", response_model=list[KeywordOut])
async def list_keywords(
    skip: int = Query(0, ge=0, description="Пропустить N элементов"),
    limit: int = Query(50, ge=1, le=500, description="Максимум элементов"),
    redis = Depends(get_sync_redis),
):
    """Получить список ключевых слов"""
    logger.debug(f"Запрос списка ключевых слов: {skip}, {limit}")

    try:
        keywords = await run_in_threadpool(get_all_keywords, redis)
        return [KeywordOut(keyword=kw) for kw in sorted(keywords)]

    except Exception as e:
        logger.exception("Ошибка при получении списка ключевых слов")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching keywords",
        )

@router.get("/{keyword}", response_model=KeywordOut)
async def get_keyword(keyword: str, redis = Depends(get_redis)):
    """Получить одно ключевое слово по его значению"""

    logger.debug(f"Запрос ключевого слова: {keyword}")

    exists = await redis.sismember("keywords", keyword)
    if not exists:
        raise HTTPException(status_code=404, detail="Keyword not found")

    return KeywordOut(keyword=keyword)


@router.post("/", response_model=KeywordOut, status_code=201)
async def create_keyword(data: KeywordCreate, redis=Depends(get_redis)):
    keyword = data.keyword.strip()
    if not keyword:
        raise HTTPException(422, "Keyword cannot be empty")

    logger.info(f"Попытка создать ключевое слово: {keyword}")

    if await redis.sismember("keywords", keyword):
        raise HTTPException(409, detail=f"Keyword '{keyword}' уже существует")

    try:
        await redis.sadd("keywords", keyword)
        return KeywordOut(keyword=keyword)
    except Exception as e:
        logger.exception(f"Ошибка при создании ключевого слова: {keyword}")
        raise HTTPException(500, "Failed to create keyword")


@router.patch("/{keyword}", response_model=KeywordOut)
async def update_keyword(
    keyword: str,
    data: KeywordUpdate,
    redis = Depends(get_redis),
):
    """Обновить существующее ключевое слово word на new_word (заменить слово)"""

    if not data.keyword:
        raise HTTPException(422, "Nothing to update")

    new_keyword = data.keyword.strip()
    if not new_keyword:
        raise HTTPException(422, "Keyword cannot be empty")

    logger.info(f"Обновление ключевого слова: {keyword} → {new_keyword}")

    # Проверяем существование старого слова
    exists = await redis.sismember("keywords", keyword)
    if not exists:
        raise HTTPException(404, "Keyword not found")

    # Проверяем, не занято ли новое слово
    if new_keyword != keyword and await redis.sismember("keywords", new_keyword):
        raise HTTPException(409, f"Keyword '{new_keyword}' already exists")

    try:
        # Удаляем старое и добавляем новое
        await redis.srem("keywords", keyword)
        await redis.sadd("keywords", new_keyword)

        return KeywordOut(keyword=new_keyword)

    except Exception as e:
        logger.exception(f"Ошибка обновления ключевого слова {keyword} → {new_keyword}")
        raise HTTPException(500, "Failed to update keyword")


@router.delete("/{keyword}", status_code=204)
async def delete_keyword(keyword: str, redis = Depends(get_redis)):
    """Удалить ключевое слово"""

    logger.warning(f"Удаление ключевого слова: {keyword}")

    removed = await redis.srem("keywords", keyword)
    if removed == 0:
        raise HTTPException(404, "Keyword not found")

    await redis.delete(f"keyword:meta:{keyword}")

    logger.info(f"Ключевое слово удалено: {keyword}")
    return None
