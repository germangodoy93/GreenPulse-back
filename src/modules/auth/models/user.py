"""SQLAlchemy ORM model for the users table."""

import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class UserRole(str, enum.Enum):
    """Application roles for access control."""

    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class User(Base):
    """Registered application user.

    Passwords are NEVER stored in plain text — only the bcrypt hash.
    The API key for IoT devices belongs to the Device model (Stage 3).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.viewer,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} rol={self.rol}>"
