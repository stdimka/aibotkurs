import logging
import sys
from typing import Optional

from app.config import settings


def setup_logging() -> None:
    """Настраивает корневой логгер. Вызывать один раз при старте приложения."""
    level_name = settings.log_level.upper()
    log_level = getattr(logging, level_name, logging.INFO)

    if not isinstance(log_level, int):
        log_level = logging.INFO
        print(f"WARNING: неизвестный LOG_LEVEL '{level_name}', используется INFO", file=sys.stderr)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    root = logging.getLogger()
    root.setLevel(log_level)

    # Убираем старые handlers, чтобы не дублировать при повторных вызовах
    for h in root.handlers[:]:
        root.removeHandler(h)

    root.addHandler(console_handler)

    # Подавляем слишком шумные логгеры
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    if name is None:
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get("__name__", "root")
    return logging.getLogger(name)
