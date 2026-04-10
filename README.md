# AI News Bot

Автоматизированный Telegram-канал с парсингом новостей, фильтрацией по ключевым словам, генерацией постов через ИИ и автоматической публикацией.

## Основные возможности

- Парсинг новостей из RSS-сайтов и Telegram-каналов
- Гибкая фильтрация по ключевым словам
- Генерация качественных постов с помощью ИИ (с редактируемым System Prompt)
- Автоматическая публикация в Telegram-канал
- Удобная веб-админка с поддержкой русского и английского языков
- Полностью контейнеризированное приложение (Docker + Celery + Redis)

## Технологии

- **Backend**: FastAPI
- **Очередь задач**: Celery + Redis
- **Хранилище**: Redis
- **AI**: Groq / OpenRouter / любой OpenAI-совместимый провайдер
- **Telegram**: Telethon
- **Админка**: Jinja2 + JavaScript
- **Контейнеризация**: Docker Compose

⚡ Быстрый старт (локально)
# 1. Клонировать репозиторий
git clone https://github.com/stdimka/aibotkurs.git
cd aibotkurs

# 2. Создать файл настроек
cp local_settings.example.py local_settings.py

# 3. Запустить проект
docker compose up --build -d

После запуска админка доступна по адресу:
👉 http://localhost:8000/admin

⚙️ Настройка

Настройки можно менять двумя способами:

через файл local_settings.py
через веб-интерфейс /settings

🔑 Важные параметры

tg_api_id        # Telegram API ID
tg_api_hash      # Telegram API Hash
tg_session_str   # Сессия Telegram
tg_channel       # Канал для публикации (например: @your_channel)

AI_API_KEY       # Ключ AI-провайдера

👉 Ключевые слова и System Prompt лучше настраивать через админку.

📁 Структура проекта

aibotkurs/
├── app/
│   ├── ai/                # Генерация постов ИИ
│   ├── api/               # REST API
│   ├── news_parser/       # Парсинг новостей
│   ├── schemas/           # Pydantic схемы
│   ├── services/          # Бизнес-логика
│   ├── tasks/             # Celery задачи
│   ├── telegram/          # Публикация в Telegram
│   ├── utils/             # Утилиты
│   ├── config.py
│   ├── main.py
│   └── ...
├── templates/             # HTML админка
├── Dockerfile
├── docker-compose.yml
├── celery_app.py
├── requirements.txt
└── run_pipeline.py

🐳 Docker команды

# Запуск в фоне
docker compose up -d

# Просмотр логов
docker compose logs -f worker
docker compose logs -f web

# Перезапуск worker
docker compose restart worker

# Полная пересборка
docker compose up --build -d

# Остановка
docker compose down


☁️ Автодеплой на VPS

Рекомендуемые инструменты:

Coolify (самый простой вариант)
Dokploy
Docker Swarm / Portainer

👉 Подробный гайд по деплою будет добавлен позже.

📄 Лицензия

MIT License