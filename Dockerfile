# ─────────────────────────────────────────────────────────────────────────────
# GreenPulse API — Multi-stage Dockerfile
# Stage 1: instala dependencias (builder con herramientas de compilación)
# Stage 2: imagen de runtime mínima sin herramientas de build
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Herramientas de compilación para extensiones C (asyncpg, bcrypt, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar sólo requirements para aprovechar la cache de Docker en rebuilds
COPY requirements.txt .

# Instalar en un prefix separado para copiar solo lo necesario al runtime
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="GreenPulse API" \
      org.opencontainers.image.description="Sistema de Monitoreo Ambiental IoT — TFE UNIR" \
      org.opencontainers.image.authors="GodoyGerman"

WORKDIR /app

# Copiar paquetes instalados desde el builder
COPY --from=builder /install /usr/local

# Copiar código fuente (excluye lo listado en .dockerignore)
COPY . .

# Crear usuario no-root para seguridad (principio de menor privilegio)
RUN groupadd --gid 1001 greenpulse \
    && useradd --uid 1001 --gid greenpulse --no-create-home --shell /bin/sh appuser \
    && chown -R appuser:greenpulse /app

USER appuser

# Railway asigna el puerto vía $PORT; 8000 es el fallback local
EXPOSE 8000

# El entrypoint ejecuta las migraciones y luego arranca el servidor
ENTRYPOINT ["sh", "scripts/entrypoint.sh"]
