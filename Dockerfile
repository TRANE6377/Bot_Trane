FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data directory for SQLite DB and Telethon session
VOLUME ["/app/data"]

ENV DATABASE_PATH=/app/data/bot_data.db
ENV TELETHON_SESSION=/app/data/user_session

CMD ["python", "bot.py"]
