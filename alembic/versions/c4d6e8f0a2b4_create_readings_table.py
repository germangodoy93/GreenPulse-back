"""Create readings table and index api_key_hash on devices.

Revision ID: c4d6e8f0a2b4
Revises: b3c5d7e9f1a3
Create Date: 2026-06-13

Changes:
  1. Add index on devices.api_key_hash (O(1) SHA-256 lookup for X-API-Key auth)
  2. Create readings table with all ESP32 sensor columns

Schema:
    readings
    ├── id              INTEGER PRIMARY KEY AUTOINCREMENT
    ├── device_id       INTEGER FK → devices.id (CASCADE, indexed)
    ├── batch_id        VARCHAR(36) NULL INDEXED  -- UUID4 for idempotent batches
    ├── soil_humidity   FLOAT NULL   -- % (resistive sensor)
    ├── temperature     FLOAT NULL   -- °C (AHT20)
    ├── air_humidity    FLOAT NULL   -- % (AHT20)
    ├── pressure        FLOAT NULL   -- hPa (BMP280)
    ├── altitude        FLOAT NULL   -- m (BMP280 calculated)
    ├── light_lux       FLOAT NULL   -- lux (BH1750)
    ├── water_level     FLOAT NULL   -- cm (HC-SR04)
    ├── recorded_at     TIMESTAMP WITH TIME ZONE NOT NULL  -- device timestamp
    └── created_at      TIMESTAMP WITH TIME ZONE NOT NULL  -- server receipt time
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d6e8f0a2b4"
down_revision: Union[str, None] = "b3c5d7e9f1a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Index on devices.api_key_hash for O(1) SHA-256 lookup
    op.create_index(op.f("ix_devices_api_key_hash"), "devices", ["api_key_hash"], unique=True)

    op.create_table(
        "readings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=True),
        sa.Column("soil_humidity", sa.Float(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("air_humidity", sa.Float(), nullable=True),
        sa.Column("pressure", sa.Float(), nullable=True),
        sa.Column("altitude", sa.Float(), nullable=True),
        sa.Column("light_lux", sa.Float(), nullable=True),
        sa.Column("water_level", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name=op.f("fk_readings_device_id_devices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_readings")),
    )
    op.create_index(op.f("ix_readings_device_id"), "readings", ["device_id"])
    op.create_index(op.f("ix_readings_batch_id"), "readings", ["batch_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_readings_batch_id"), table_name="readings")
    op.drop_index(op.f("ix_readings_device_id"), table_name="readings")
    op.drop_table("readings")
    op.drop_index(op.f("ix_devices_api_key_hash"), table_name="devices")
