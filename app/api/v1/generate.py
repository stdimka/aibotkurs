from fastapi import APIRouter, HTTPException, status, Query, Depends
from starlette.concurrency import run_in_threadpool

from app.dependencies import get_redis
from app.schemas.generate import GenerateRequest, GenerateResponse, GeneratedPostOut
from app.ai.generator import ai_generate_post
from app.utils.logging import get_logger

GENERATED_PREFIX = "news:generated"

logger = get_logger(__name__)

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/", response_model=GenerateResponse, status_code=200)
async def manual_generate(request: GenerateRequest):
    """
    Ручная генерация поста через AI (для тестов и отладки)
    """
    logger.info(f"Ручная генерация запрошена: {request.title[:80]}...")

    try:
        result: GenerateResponse = await run_in_threadpool(
            ai_generate_post,
            request.title,
            request.summary,
        )

        return result


    except Exception as e:
        logger.exception("Ошибка ручной генерации")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation failed: {str(e)}",
        )


@router.get("/", response_model=list[GeneratedPostOut])
async def list_generated_posts(
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=200),
        redis=Depends(get_redis),
):
    try:
        raw_keys = await redis.keys(f"{GENERATED_PREFIX}:*")
        keys = [k.decode("utf-8") if isinstance(k, bytes) else k for k in raw_keys]
        keys.sort(reverse=True)  # новые сверху

        if not keys:
            return []

        paginated_keys = keys[skip: skip + limit]

        result = []
        for key in paginated_keys:
            data = await redis.hgetall(key)
            if not data:
                continue

            result.append(
                GeneratedPostOut(
                    key=key,
                    original_title=data.get("original_title"),
                    new_title=data.get("new_title"),
                    generated_post=data.get("generated_post"),
                    hash=data.get("hash"),
                )
            )

        return result

    except Exception as e:
        logger.exception("Ошибка получения сгенерированных постов")
        raise HTTPException(status_code=500, detail="Не удалось получить список")
