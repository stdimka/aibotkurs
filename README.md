# 🤖 AI News Bot

An automated Telegram bot that collects news from RSS websites and Telegram channels, filters them, rewrites them using AI, and publishes them to your channel.
---

## ✨ Features

News parsing from RSS feeds (Habr, VC.ru, RBC, Tproger, etc.)
Parsing posts from Telegram channels
Smart keyword-based filtering
AI-powered rewriting of posts (style and quality enhancement)
Automatic publishing to a Telegram channel
Full CRUD for managing sources via API
Scheduled execution using Celery Beat
State storage in Redis

---

## 🛠 Technologies

FastAPI — web interface and API
Celery + Redis — asynchronous tasks and queue
Telethon — Telegram integration (parsing and publishing)
Pydantic + Settings — configuration management
Docker + Docker Compose — deployment

---

## 🚀 Quick start (local)

1. Clone the repository
```bash
git clone https://github.com/stdimka/aibotkurs.git
cd aibotkurs

2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

3. Install dependencies
pip install -r requirements.txt

4. Configure the settings
cp local_setting_1.py local_settings.py

Open local_settings.py and fill in:
tg_api_id
tg_api_hash
tg_session_str
tg_channel

5. Run the Redis
docker compose up --build

6. Run the project
# Terminal 1 — FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Celery Worker
celery -A celery_app worker --pool=solo -l info

# Terminal 3 — Celery Beat
celery -A celery_app beat -l info

📁 Project structure
aibotkurs/
├── app/
│   ├── api/              # FastAPI endpoints
│   ├── tasks/            # Celery tasks (parse, filter, generate, publish, pipeline)
│   ├── news_parser/      # Parsers (websites + Telegram)
│   ├── telegram/         # Publishing to a channel
│   ├── services/         # Business logic
│   └── schemas/          # Pydantic models
├── local_settings.py
├── celery_app.py
├── docker-compose.yml
├── Dockerfile
└── README.md
