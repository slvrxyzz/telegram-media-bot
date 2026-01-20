# Telegram Media Bot

Короткий запуск:

1) Установить зависимости:
```
pip install -r requirements.txt
```

2) Создать `.env` в корне проекта и указать:
```
BOT_TOKEN=ваш_токен
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_media
```

3) Запустить PostgreSQL (через Docker):
```
docker compose up -d
```

4) Запустить бота:
```
python -m bot.main
```

Если включена модерация (`MODERATION_ENABLED=true`), не забудьте указать `ADMIN_IDS`.
