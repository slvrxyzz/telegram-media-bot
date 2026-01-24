# Telegram Media Bot

Телеграмм-бот сейчас работает и развернут на сервере, если есть желание запустить его локально, то вот небольшая инструкция. В таком случае, не забудьте изменить токен бота.



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

Никнейм бота в телеграмме: @hackathon_enter_test_bot


Актуальная ссылка: https://t.me/hackathon_enter_test_bot
