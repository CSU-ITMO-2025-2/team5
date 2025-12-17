"""Declarative base for all ORM models."""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import declarative_base


class Base(AsyncAttrs, declarative_base()):
    """
    Абстрактный базовый класс для всех ORM-моделей.
    """

    __abstract__ = True
