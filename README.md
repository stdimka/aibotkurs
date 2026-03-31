# 🤖 AI News Bot

Автоматический Telegram-бот, который собирает новости из RSS-сайтов и Telegram-каналов, фильтрует их, переписывает с помощью ИИ и публикует в ваш канал.

---

## ✨ Возможности

- Парсинг новостей из **RSS** (Habr, VC.ru, RBC, Tproger и др.)
- Парсинг постов из **Telegram-каналов**
- Умная фильтрация по ключевым словам
- Переписывание постов с помощью ИИ (апгрейд стиля и качества)
- Автоматическая публикация в Telegram-канал
- Полноценный **CRUD** для управления источниками через API
- Запуск по расписанию через Celery Beat
- Хранение состояния в Redis

---

## 🛠 Технологии

- **FastAPI** — веб-интерфейс и API
- **Celery** + Redis — асинхронные задачи и очередь
- **Telethon** — работа с Telegram (парсинг и публикация)
- **Pydantic** + Settings — конфигурация
- **Docker** + Docker Compose — развёртывание

---

## 🚀 Быстрый запуск (локально)

### 1. Клонируйте репозиторий
```bash
git clone https://github.com/stdimka/aibotkurs.git
cd aibotkurs

2. Создайте виртуальное окружение
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

3. Установите зависимости
pip install -r requirements.txt

4. Настройте конфигурацию
cp local_setting_1.py local_settings.py

Откройте local_settings.py и заполните:

tg_api_id
tg_api_hash
tg_session_str
tg_channel

5. Запустите Redis
docker compose up --build

6. Запустите проект
# Терминал 1 — FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Терминал 2 — Celery Worker
celery -A celery_app worker --pool=solo -l info

# Терминал 3 — Celery Beat
celery -A celery_app beat -l info

📁 Структура проекта
aibotkurs/
├── app/
│   ├── api/              # FastAPI эндпоинты
│   ├── tasks/            # Celery задачи (parse, filter, generate, publish, pipeline)
│   ├── news_parser/      # Парсеры (сайты + Telegram)
│   ├── telegram/         # Публикация в канал
│   ├── services/         # Бизнес-логика
│   └── schemas/          # Pydantic модели
├── local_settings.py
├── celery_app.py
├── docker-compose.yml
├── Dockerfile
└── README.md
