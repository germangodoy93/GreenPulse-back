"""Create devices table.

Revision ID: b3c5d7e9f1a3
Revises: ae1b35f5c2a0
Create Date: 2026-06-13

Schema:
    devices
    ├── id              INTEGER PRIMARY KEY AUTOINCREMENT
    ├── nombre          VARCHAR(100) NOT NULL
    ├── tipo_zona       ENUM('interior','exterior','invernadero','bodega') NOT NULL
    ├── latitud         FLOAT NULL
    ├── longitud        FLOAT NULL
    ├── api_key_hash    VARCHAR(255) NOT NULL     -- bcrypt hash, never plain
    ├── activo          BOOLEAN NOT NULL DEFAULT TRUE  -- soft delete flag
    ├── propietario_id  INTEGER FK → users.id (CASCADE)
    └── created_at      TIMESTAMP WITH TIME ZONE NOT NULL
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c5d7e9f1a3"
down_revision: Union[str, None] = "ae1b35f5c2a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column(
            "tipo_zona",
            sa.Enum("interior", "exterior", "invernadero", "bodega", name="tipozona"),
            nullable=False,
        ),
        sa.Column("latitud", sa.Float(), nullable=True),
        sa.Column("longitud", sa.Float(), nullable=True),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("propietario_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["propietario_id"],
            ["users.id"],
            name=op.f("fk_devices_propietario_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
    )
    op.create_index(op.f("ix_devices_propietario_id"), "devices", ["propietario_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_devices_propietario_id"), table_name="devices")
    op.drop_table("devices")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS tipozona")
