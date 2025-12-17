import os
import logging
from sqlalchemy import BigInteger, select
from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set!")

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(AsyncAttrs, declarative_base()):
    """
    Абстрактный базовый класс для всех ORM-моделей.
    """

    __abstract__ = True


class Subscriber(Base):
    __tablename__ = "subscribers"
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


async def init_db():
    """
    Инициализирует соединение с БД и создает таблицу, если ее нет.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized (PostgreSQL).")


async def add_subscriber(chat_id: int):
    """Добавляет нового подписчика в PostgreSQL. Игнорирует дубликаты."""
    async with async_session_maker() as session:
        new_subscriber = Subscriber(chat_id=chat_id)
        try:
            await session.merge(new_subscriber)
            await session.commit()
            logger.info("Subscriber %s added or already exists in PostgreSQL.", chat_id)
        except Exception as e:
            await session.rollback()
            logger.error("Failed to add subscriber %s: %s", chat_id, e, exc_info=True)


async def get_all_subscribers() -> list[int]:
    """Получает список всех chat_id подписчиков из PostgreSQL."""
    async with async_session_maker() as session:
        stmt = select(Subscriber.chat_id)
        result = await session.execute(stmt)
        subscribers = result.scalars().all()
        return subscribers
