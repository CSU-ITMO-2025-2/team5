# Auth Service

Сервис аутентификации и авторизации пользователей.

- Регистрация новых пользователей
- Аутентификация пользователей
- Генерация JWT токенов

## API Endpoints
- `POST /users` - Регистрация пользователя
- `POST /sessions` - Аутентификация
- `GET /health` - Health check

## Технологии
- FastAPI
- PostgreSQL
- SQLAlchemy ORM
- JWT (Argon2 хеширование паролей)

## Запуск
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Environment Variables
- `SECRET_KEY` - JWT секрет
- `ALGORITHM` - Алгоритм шифрования
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Время жизни токена
