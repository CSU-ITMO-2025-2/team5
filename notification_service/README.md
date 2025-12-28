# Notification Service

Сервис уведомлений через Telegram

- Потребление обработанных отзывов из Kafka топика `processed-reviews`
- Преобразование эмоций в русские названия и sentiment
- Отправка уведомлений в Telegram
- Поддержка Telegram бота для подписки пользователей

## Стэк
- FastAPI
- Kafka (aiokafka)
- Telegram Bot API (aiogram)
- PostgreSQL (для хранения подписчиков)
- Circuit Breaker для отказоустойчивости

## Запуск
```bash
uvicorn app:app --host 0.0.0.0 --port 7071
```

## Environment Variables
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka endpoints
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `DATABASE_URL` - PostgreSQL connection string

## Особенности
- Автоматическая подписка через Telegram бота
- Circuit Breaker для защиты от сбоев Telegram API
- Форматирование сообщений в Markdown
- Поддержка SASL/SCRAM аутентификации Kafka
