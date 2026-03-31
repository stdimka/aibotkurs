from celery import shared_task, group, chord, chain
from app.tasks.parse_sites import parse_site_task
from app.tasks.parse_tg import parse_tg_task
from app.tasks.filter import filter_posts_task
from app.tasks.generate import generate_post_task
from app.tasks.publish import publish_to_telegram_task
from app.redis_sync import get_sync_redis
from app.utils.logging import get_logger

logger = get_logger(__name__)


def get_all_source_names() -> list[str]:
    """Получить все источники сайтов"""
    redis = get_sync_redis()
    keys = redis.keys("site_sources:*")
    return [key.split(":")[1] for key in keys]


def get_all_tg_names() -> list[str]:
    """Получить все Telegram-каналы"""
    redis = get_sync_redis()
    keys = redis.keys("tg_sources:*")
    return [key.split(":")[1] for key in keys]


def start_pipeline():
    """Запускает полный конвейер: парсинг → фильтрация → генерация → публикация"""
    source_site_names = get_all_source_names()
    source_tg_names = get_all_tg_names()

    if not (source_site_names or source_tg_names):
        logger.info("Нет активных источников для парсинга")
        return None

    # 1. Задачи парсинга (сайты + TG)
    parse_tasks = (
        [parse_site_task.s(source_name=name) for name in source_site_names] +
        [parse_tg_task.s(source_name=name) for name in source_tg_names]
    )

    if not parse_tasks:
        logger.warning("Нет задач для парсинга")
        return None

    logger.info(f"Запуск пайплайна: {len(source_site_names)} сайтов + {len(source_tg_names)} TG-каналов")

    # 2. Полный workflow: парсинг → фильтрация → генерация всех постов → публикация
    workflow = chord(parse_tasks)(
        chain(
            filter_posts_task.s(),
            generate_all_posts.s(),
            publish_all_posts.s()
        )
    )

    logger.info("✅ Полный pipeline запущен через Celery (chord + chain)")
    return workflow


@shared_task
def generate_all_posts(_):
    """Генерирует посты для всех отфильтрованных новостей"""
    redis = get_sync_redis()
    filtered_keys = redis.keys("news:filtered:*")

    if not filtered_keys:
        logger.info("Нет отфильтрованных новостей для генерации")
        return 0

    logger.info(f"Запущена генерация {len(filtered_keys)} постов")

    tasks = [
        generate_post_task.s(key.decode("utf-8") if isinstance(key, bytes) else key)
        for key in filtered_keys
    ]

    group(tasks).apply_async()
    return len(filtered_keys)


@shared_task
def publish_all_posts(_):
    """Публикует все сгенерированные, но ещё не опубликованные посты"""
    redis = get_sync_redis()
    generated_keys = redis.keys("news:generated:*")

    if not generated_keys:
        logger.info("Нет сгенерированных постов для публикации")
        return 0

    unpublished_keys = []
    for raw_key in generated_keys:
        key_str = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key
        data = redis.hgetall(raw_key)

        # Проверяем флаг публикации
        published_flag = data.get(b"is_published") or data.get("is_published")
        is_published = False
        if published_flag:
            flag_str = str(published_flag).strip().lower()
            is_published = flag_str in ("1", "true", "yes")

        if not is_published:
            unpublished_keys.append(key_str)

    if not unpublished_keys:
        logger.info("Все сгенерированные посты уже опубликованы")
        return 0

    logger.info(f"Запущена публикация {len(unpublished_keys)} постов в Telegram")

    publish_tasks = [publish_to_telegram_task.s(key) for key in unpublished_keys]
    group(publish_tasks).apply_async()

    return len(unpublished_keys)


# Задача для Celery Beat (будет запускаться по расписанию)
@shared_task(name="run_pipeline_task")
def run_pipeline_task():
    """Точка входа для автоматического запуска пайплайна"""
    logger.info("=== Запуск запланированного пайплайна ===")
    start_pipeline()