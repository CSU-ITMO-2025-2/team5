# ML Service

Сервис машинного обучения для анализа эмоций и генерации ответов.

- Потребление отзывов из Kafka топика `raw-reviews`
- Анализ эмоций с помощью OpenAI API
- Генерация ответов на отзывы
- Сохранение результатов в PostgreSQL
- Отправка обработанных отзывов в Kafka топик `processed-reviews`

## Технологии
- FastAPI
- Kafka (aiokafka)
- OpenAI API (gpt-4o-mini)
- PostgreSQL
- Circuit Breaker для отказоустойчивости

## Запуск
```bash
uvicorn app:app --host 0.0.0.0 --port 7070
```

## Environment Variables
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka endpoints
- `API_KEY` - OpenAI API key
- `OPENAI_BASE_URL` - OpenAI base URL
- `OPENAI_MODEL` - OpenAI model name

## Особенности
- Circuit Breaker для защиты от сбоев OpenAI
- Worker pool для обработки сообщений
- Автоматическое создание таблиц в БД
- Поддержка SASL/SCRAM аутентификации Kafka
- Стандартный fallback при ошибках OpenAI
