# GreenPulse API

> Backend REST para el **Sistema Inteligente de Monitoreo Ambiental IoT** — Trabajo de Fin de Estudio (UNIR)

GreenPulse recibe telemetría de nodos **ESP32**, la almacena en PostgreSQL, evalúa los datos contra umbrales configurables mediante un motor de reglas, genera alertas automáticas y expone todos los datos a un dashboard React.

---

## Contenidos

- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura](#arquitectura)
- [Módulos y endpoints](#módulos-y-endpoints)
- [Inicio rápido (local sin Docker)](#inicio-rápido-local-sin-docker)
- [Inicio con Docker Compose](#inicio-con-docker-compose)
- [Variables de entorno](#variables-de-entorno)
- [Autenticación](#autenticación)
- [Motor de reglas](#motor-de-reglas)
- [Tests](#tests)
- [Despliegue en Railway](#despliegue-en-railway)
- [Estructura del proyecto](#estructura-del-proyecto)

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.13 |
| Framework | FastAPI 0.115 |
| Servidor ASGI | Uvicorn 0.32 |
| ORM | SQLAlchemy 2.0 async |
| Driver PostgreSQL | asyncpg |
| Migraciones | Alembic 1.14 |
| Validación | Pydantic v2 |
| Autenticación JWT | python-jose (HS256) |
| Hashing contraseñas | passlib (bcrypt) |
| Rate limiting | slowapi |
| Logging | loguru |
| Tests | pytest + pytest-asyncio |
| Base de datos tests | SQLite in-memory (aiosqlite) |
| Contenedores | Docker + Docker Compose |
| Despliegue | Railway |

---

## Arquitectura

```
┌──────────────┐  X-API-Key   ┌─────────────────────────────────────────┐
│  ESP32 Node  │─────────────▶│                                         │
└──────────────┘              │          FastAPI Application             │
                              │                                         │
┌──────────────┐  JWT Bearer  │  CORS · RateLimit · SecurityHeaders     │
│   Dashboard  │─────────────▶│  RequestLogging                         │
└──────────────┘              │                                         │
                              └────────────────┬────────────────────────┘
                                               │
                              ┌────────────────▼────────────────────────┐
                              │             Module Layer                 │
                              │                                          │
                              │  Controller → Service → Repository       │
                              │                 │                        │
                              │           Rules Engine                   │
                              │         (Strategy Pattern)               │
                              └────────────────┬────────────────────────┘
                                               │
                              ┌────────────────▼────────────────────────┐
                              │            PostgreSQL                    │
                              │  users · devices · readings              │
                              │  thresholds · alerts                     │
                              └──────────────────────────────────────────┘
```

**Flujo de ingesta de telemetría:**
```
ESP32 → POST /api/v1/readings (X-API-Key)
  → ReadingService.ingest()
  → lectura guardada en BD
  → RulesEngineService.evaluate_and_alert()
  → si umbral excedido → Alert creada automáticamente
  → 201 Created
```

**Principios SOLID aplicados:**

| Principio | Aplicación |
|---|---|
| SRP | Controller / Service / Repository son clases independientes |
| OCP | Nuevas estrategias de evaluación sin modificar `RulesEngine` |
| LSP | `IReadingRepository` → `SQLAlchemyReadingRepository` intercambiables |
| ISP | Interfaces pequeñas por módulo, sin megaclases |
| DIP | Services dependen de interfaces; FastAPI inyecta implementaciones vía `Depends()` |

---

## Módulos y endpoints

Base URL: `https://greenpulse-back-production.up.railway.app/api/v1`

### Sistema

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del servicio y versión |

### Autenticación

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/auth/register` | Registro de usuario |
| `POST` | `/auth/login` | Login — devuelve JWT |
| `GET` | `/auth/me` | Perfil del usuario autenticado |

### Dispositivos

> Autenticación: `Authorization: Bearer <token>`

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/devices` | Registrar dispositivo ESP32 (devuelve API Key) |
| `GET` | `/devices` | Listar dispositivos del usuario |
| `GET` | `/devices/{id}` | Detalle de un dispositivo |
| `PUT` | `/devices/{id}` | Actualizar dispositivo |
| `DELETE` | `/devices/{id}` | Dar de baja (soft delete) |
| `POST` | `/devices/{id}/rotate-key` | Rotar API Key |

### Umbrales

> Autenticación: `Authorization: Bearer <token>`

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/devices/{id}/thresholds` | Ver umbrales configurados |
| `PUT` | `/devices/{id}/thresholds` | Crear o actualizar umbrales |

Campos configurables: `soil_humidity`, `temperature`, `air_humidity`, `pressure`, `altitude`, `light_lux`, `water_level`. Cada uno acepta `_min` y `_max` (ej. `temperature_min`, `temperature_max`).

### Lecturas

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/readings` | X-API-Key | Ingestar lectura individual |
| `POST` | `/readings/batch` | X-API-Key | Ingestar lote idempotente |
| `GET` | `/readings` | JWT | Historial con filtros |
| `GET` | `/readings/{id}` | JWT | Lectura por ID |
| `GET` | `/readings/latest` | JWT | Última lectura por dispositivo |
| `GET` | `/readings/aggregate` | JWT | Estadísticas (min/max/avg/count) |

### Alertas

> Autenticación: `Authorization: Bearer <token>`

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/alerts` | Listar alertas (filtros: `device_id`, `resuelta`, `severity`) |
| `GET` | `/alerts/{id}` | Detalle de alerta |
| `PUT` | `/alerts/{id}/resolve` | Marcar alerta como resuelta |

**Severidades:** `low` · `medium` · `high` · `critical`

---

## Inicio rápido (local sin Docker)

### Prerrequisitos

- Python 3.13
- PostgreSQL 14+ corriendo en `localhost:5432`

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/germangodoy93/GreenPulse-back.git
cd GreenPulse-back

# 2. Crear entorno virtual e instalar dependencias
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu DATABASE_URL y SECRET_KEY

# 4. Aplicar migraciones
alembic upgrade head

# 5. Arrancar el servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API disponible en `http://localhost:8000`
Documentación interactiva en `http://localhost:8000/docs`

---

## Inicio con Docker Compose

```bash
# Primera vez (construye imagen y levanta PostgreSQL + API)
docker compose up --build

# Sucesivas ejecuciones
docker compose up

# Detener y eliminar volúmenes
docker compose down -v
```

La app aplica las migraciones automáticamente al arrancar. El puerto expuesto es `8000`.

> PostgreSQL corre en el puerto `5433` del host (para no colisionar con una instalación local en `5432`).

---

## Variables de entorno

Copia `.env.example` a `.env` y rellena los valores:

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | Sí | `postgresql+asyncpg://user:pass@host:port/db` |
| `SECRET_KEY` | Sí | Clave JWT, mínimo 32 caracteres |
| `ENVIRONMENT` | No | `development` / `staging` / `production` |
| `DEBUG` | No | `true` / `false` (default: `false`) |
| `PORT` | No | Puerto del servidor (default: `8000`) |
| `JWT_EXPIRATION_HOURS` | No | Expiración del token (default: `24`) |
| `CORS_ORIGINS` | No | JSON array de orígenes permitidos |
| `RATE_LIMIT_PER_MINUTE` | No | Límite global de peticiones (default: `60`) |

Generar `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## Autenticación

El sistema usa **dos mecanismos** según el tipo de cliente:

### JWT Bearer — Dashboard / usuarios
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
Se obtiene en `POST /api/v1/auth/login`. Expira según `JWT_EXPIRATION_HOURS`.

### X-API-Key — Dispositivos ESP32
```
X-API-Key: gp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
Se genera en `POST /api/v1/devices` (mostrada una única vez) o al rotar con `POST /api/v1/devices/{id}/rotate-key`.

La clave se almacena como hash **SHA-256** en la base de datos con índice `UNIQUE` para verificación O(1), sin overhead de bcrypt en cada petición del sensor.

---

## Motor de reglas

Cuando se recibe una lectura, el sistema evalúa automáticamente cada variable contra los umbrales configurados para el dispositivo:

```
valor < umbral_min  →  violación lower bound
valor > umbral_max  →  violación upper bound
```

**Cálculo de severidad** (basado en % de desviación del límite):

| Desviación | Severidad |
|---|---|
| < 10 % | `low` |
| 10 – 30 % | `medium` |
| 30 – 50 % | `high` |
| > 50 % | `critical` |

La lógica de evaluación implementa el patrón **Strategy** (`IThresholdStrategy`), lo que permite añadir nuevos criterios de alerta sin modificar el motor central.

---

## Tests

```bash
# Ejecutar suite completa con cobertura
python -m pytest tests/ --tb=short -q

# Solo tests unitarios
python -m pytest tests/unit/ -q

# Solo tests de integración
python -m pytest tests/integration/ -q

# Con informe de cobertura detallado
python -m pytest tests/ --cov=src --cov-report=html
```

- **161 tests** · cobertura **89 %** (mínimo configurado: 80 %)
- Tests unitarios: repositorios y servicios mocked con `AsyncMock`
- Tests de integración: base de datos SQLite en memoria vía `aiosqlite`

---

## Despliegue en Railway

El proyecto está configurado para despliegue automático en Railway con PostgreSQL gestionado.

### Variables de entorno en Railway

| Variable | Valor |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `SECRET_KEY` | Clave generada con `secrets.token_urlsafe(64)` |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `PORT` | `8000` |

### Proceso de arranque

El script `scripts/entrypoint.sh` ejecuta en orden:
1. `alembic upgrade head` — aplica migraciones pendientes
2. `uvicorn main:app` — arranca el servidor

La imagen Docker usa **multi-stage build** con usuario no-root para minimizar la superficie de ataque.

---

## Estructura del proyecto

```
GreenPulse/
├── main.py                          # Entry point — monta routers y middleware
├── config/
│   └── settings.py                  # Pydantic Settings (variables de entorno)
├── src/
│   ├── modules/                     # Módulos de dominio
│   │   ├── system/                  # Healthcheck
│   │   ├── auth/                    # Registro, login, JWT
│   │   ├── devices/                 # CRUD nodos ESP32 + API Key
│   │   ├── readings/                # Ingesta y consulta de telemetría
│   │   ├── thresholds/              # Umbrales + motor de reglas (Strategy)
│   │   └── alerts/                  # Alertas generadas automáticamente
│   ├── shared/
│   │   ├── exceptions/              # Jerarquía de excepciones de dominio
│   │   ├── middleware/              # Security headers, request logging
│   │   ├── response/                # Envelopes SuccessResponse / PaginatedResponse
│   │   └── utils/                   # PaginationParams
│   └── infrastructure/
│       ├── database/                # Engine async, sesiones, Base, registry
│       ├── security/                # Hashing bcrypt, JWT, SHA-256 API Key
│       └── logging/                 # Configuración loguru
├── alembic/                         # Migraciones de esquema (Alembic)
│   └── versions/
│       ├── ..._create_users_table.py
│       ├── ..._create_devices_table.py
│       ├── ..._create_readings_table.py
│       └── ..._create_thresholds_and_alerts.py
├── tests/
│   ├── conftest.py                  # Fixtures compartidas (app, client, DB)
│   ├── unit/                        # Tests sin BD — mocks de repositorios
│   └── integration/                 # Tests con SQLite en memoria
├── docs/
│   └── architecture.md              # Diagrama de arquitectura
├── scripts/
│   └── entrypoint.sh               # Migrations → uvicorn
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── pyproject.toml                   # Configuración pytest, ruff, mypy, black
└── .env.example
```

---

## Licencia

MIT — ver [LICENSE](LICENSE)
