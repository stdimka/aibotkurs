FROM python:3.12-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Создаём папку для медиа
RUN mkdir -p media

EXPOSE 8000

# По умолчанию запускаем web-сервер
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]