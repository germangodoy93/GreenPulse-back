"""Declarative base for all SQLAlchemy ORM models.

All models must inherit from Base to be discovered by Alembic.
The naming convention ensures consistent constraint names across migrations.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Alembic-recommended naming convention for auto-generated constraint names.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base for all domain models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
