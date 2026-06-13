"""Create users table.

Revision ID: ae1b35f5c2a0
Revises:
Create Date: 2026-06-12

Schema:
    users
    ├── id            INTEGER PRIMARY KEY AUTOINCREMENT
    ├── email         VARCHAR(255) UNIQUE NOT NULL
    ├── password_hash VARCHAR(255) NOT NULL          -- bcrypt, never plain text
    ├── rol           ENUM('admin','operator','viewer') NOT NULL DEFAULT 'viewer'
    └── created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ae1b35f5c2a0"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "rol",
            sa.Enum("admin", "operator", "viewer", name="userrole"),
            nullable=False,
            server_default="viewer",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    # Drop the PostgreSQL ENUM type (no-op on SQLite)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS userrole")
