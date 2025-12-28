# Producer Service

Сервис приема отзывов от пользователей и отправки их в Kafka.

## Назначение
- Прием отзывов от аутентифицированных пользователей
- Отправка отзывов в Kafka топик `raw-reviews`
- Валидация JWT токенов

## API Endpoints
- `POST /reviews` - Отправка отзыва на обработку
- `GET /health` - Health check

## Технологии
- FastAPI
- Kafka (aiokafka)
- JWT аутентификация

## Запуск
```bash
uvicorn app:app --host 0.0.0.0 --port 5050
```

## Environment Variables
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka endpoints
- `SECRET_KEY` - JWT секрет
- `ALGORITHM` - Алгоритм шифрования

## Особенности
- Генерирует UUID для каждого отзыва
- Сохраняет username пользователя
- Отправляет сообщения в Kafka для дальнейшей обработки ML сервисом
