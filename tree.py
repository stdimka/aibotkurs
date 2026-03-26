
from pathlib import Path

SPACES = 4  # Число пробелов на 1 уровень

tree = """
aibot/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app + lifespan (подключение redis при старте)
│   ├── config.py                   # настройки через pydantic-settings / .env
│   ├── dependencies.py             # Depends для redis клиента
│   ├── ai/
│   │   ├── __init__.py
│   │   └── generator.py            # клиент OpenAI + промпты
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── filtered_posts.py   # история отфильтровнных постов (пока заглушки)
│   │       ├── generate.py         # ручная генерация (пока заглушка)
│   │       ├── keywords.py         # CRUD ключевых слов (полностью)
│   │       ├── posts.py            # история постов (пока заглушки)
│   │       ├── site_sources.py     # CRUD источников сайтов (полностью)
│   │       └── tg_sources.py       # CRUD источников т-каналов (полностью)
│   ├── news_parser/
│   │   ├── __init__.py
│   │   ├── base.py                 # абстрактный парсер
│   │   ├── sites.py                # парсеры сайтов (habr, vc, etc.)
│   │   └── telegram.py             # Telethon-парсер
│   ├── schemas/                    # все pydantic модели
│   │   ├── __init__.py
│   │   ├── filtered_posts.py
│   │   ├── generate.py
│   │   ├── keywords.py
│   │   ├── posts.py
│   │   ├── site_sources.py
│   │   └── tg_sources.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── keyword_service.py      # бизнес-логика ключевых слов (Redis)
│   │   ├── source_service.py       # бизнес-логика источников (Redis)
│   │   └── dedup_service.py        # проверка дублей (Redis set)
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── parse_sites.py          # задачи парсинга сайтов
│   │   ├── parse_tg.py             # задачи парсинга телеграм-каналов
│   │   ├── filter.py               # задачи фильтрации (по словам и дубликатам)
│   │   ├── generate.py             # задачи генерации статей
│   │   └── publish.py              # задачи публикации статей
│   ├── telegram/
│   │   ├── __init__.py
│   │   └── publisher.py            # Telethon-клиент для публикации
│   └── utils/
│       ├── __init__.py
│       ├── initialization.py       # загрузка начальных данных из settings
│       └── logging.py              # конфигуратор логирования
│
├── celery_app.py                   # создание celery app + autodiscover_tasks
├── celery_worker.py                # точка запуска worker & beat (если отдельно)
├── local_settings.py               # секреты и начальные установки
├── requirements.txt
├── docker-compose.yml
├── README.md
└── .gitignore
""".strip()


def create_structure(tree_text: str, root_dir: str = "."):
    root = Path(root_dir).resolve()
    stack = [root]

    for line in tree_text.splitlines():
        if not line.strip():
            continue

        # Считаем уровень вложенности по отступам (4 пробела = 1 уровень)
        if line.lstrip(" │├─└") == line:
            continue
            # raise ValueError("Удалите строку с именем корневой папки!")

        stripped = line.lstrip(" │├─└")
        level = (len(line) - len(stripped)) // SPACES

        # Убираем комментарии
        stripped = stripped.split("#", 1)[0].rstrip()

        # Убираем префиксы веток
        name = stripped.lstrip(" ─└├│")

        if not name:
            continue

        # Возвращаемся на нужный уровень в стеке
        while len(stack) > level:
            stack.pop()

        current = stack[-1]
        path = current / name

        # Папка или файл?
        if name.endswith('/'):
            name = name.rstrip('/')
            path = current / name
            path.mkdir(parents=True, exist_ok=True)
            stack.append(path)
        else:
            # Файл
            path.parent.mkdir(parents=True, exist_ok=True)
            existed = path.exists()
            path.touch(exist_ok=True)
            symbol = "✓" if existed else "✓"

    print("\nСтруктура создана/проверена")


if __name__ == "__main__":
    print("Создание структуры проекта...\n")
    create_structure(tree)