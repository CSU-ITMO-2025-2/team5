import os
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from alembic import context
from logging.config import fileConfig

# Загрузка переменных окружения из файла .env
load_dotenv()

# Подключаем конфиг Alembic
config = context.config

# Загружаем файл конфигурации логирования, если он существует
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Мета-данные SQLAlchemy для миграций
# Используем Base.metadata для миграций
# из модели (предположим, что ваш Base импортирован из auth_service)
from models import Base
target_metadata = Base.metadata

# Подключение к базе данных из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
else:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

# Функции для выполнения миграций

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
