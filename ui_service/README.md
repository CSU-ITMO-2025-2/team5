# UI Service

Веб-интерфейс для взаимодействия с системой

- Главная страница с описанием системы
- Страница аутентификации и регистрации
- Личный кабинет для отправки отзывов
- Отображение результатов анализа
- API для фронтенда

## Стэк
- FastAPI
- Jinja2 templates
- Bootstrap 5
- HTML/CSS/JavaScript
- CORS для API запросов

## Запуск
```bash
uvicorn app:app --host 0.0.0.0 --port 8080
```

## Environment Variables
- `AUTH_SERVICE_URL` - URL auth сервиса
- `PRODUCER_SERVICE_URL` - URL producer сервиса
- `ML_SERVICE_URL` - URL ML сервиса

## Страницы
- `/` - Главная страница
- `/login` - Страница входа/регистрации
- `/dashboard` - Личный кабинет

## API Endpoints
- `POST /api/users` - Регистрация
- `POST /api/sessions` - Аутентификация
- `POST /api/reviews` - Отправка отзыва
- `GET /api/reviews/{review_id}` - Получение результата
