#!/bin/sh
# GreenPulse API — entrypoint de producción
# 1. Espera a que la base de datos esté lista
# 2. Ejecuta las migraciones Alembic
# 3. Arranca uvicorn

set -e

echo "==> Ejecutando migraciones Alembic..."
python -m alembic upgrade head
echo "==> Migraciones completadas."

echo "==> Iniciando GreenPulse API en 0.0.0.0:${PORT:-8000}..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 2 \
    --log-level info \
    --no-access-log
