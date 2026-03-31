from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.concurrency import run_in_threadpool

from app.redis_sync import get_sync_redis
from app.services.source_service import (
    get_all_tg_sources,
    create_tg_source,
    update_tg_source,
    delete_tg_source
)
from app.schemas.tg_sources import TgSourceCreate, TgSourceUpdate, TgSourceOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/tg_sources",
    tags=["tg_sources"],
    responses={404: {"description": "Tg source not found"}},
)


@router.get("/", response_model=list[TgSourceOut])
async def list_tg_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    redis=Depends(get_sync_redis),
):
    """Получить список всех TG источников"""
    try:
        all_sources = await run_in_threadpool(get_all_tg_sources, redis)
        return all_sources[skip : skip + limit]
    except Exception as e:
        logger.exception("Ошибка при получении списка tg_sources")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=TgSourceOut, status_code=status.HTTP_201_CREATED)
async def create_tg_source_endpoint(
    source: TgSourceCreate,
    redis=Depends(get_sync_redis),
):
    """Добавить новый TG источник"""
    try:
        created = await run_in_threadpool(create_tg_source, redis, source)
        return created
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Ошибка создания tg_source")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{name}", response_model=TgSourceOut)
async def update_tg_source_endpoint(
    name: str,
    update_data: TgSourceUpdate,
    redis=Depends(get_sync_redis),
):
    """Обновить TG источник"""
    try:
        updated = await run_in_threadpool(update_tg_source, redis, name, update_data)
        if updated is None:
            raise HTTPException(status_code=404, detail=f"TG source {name} not found")
        return updated
    except Exception as e:
        logger.exception(f"Ошибка обновления tg_source {name}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tg_source_endpoint(
    name: str,
    redis=Depends(get_sync_redis),
):
    """Удалить TG источник"""
    try:
        deleted = await run_in_threadpool(delete_tg_source, redis, name)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"TG source {name} not found")
        return None
    except Exception as e:
        logger.exception(f"Ошибка удаления tg_source {name}")
        raise HTTPException(status_code=500, detail="Internal server error")