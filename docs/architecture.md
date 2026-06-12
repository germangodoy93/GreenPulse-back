# GreenPulse — Arquitectura del Backend

## Visión general

```
┌──────────────┐  X-API-Key   ┌─────────────────────────────────────────┐
│   ESP32 Node │─────────────▶│                                         │
└──────────────┘              │            FastAPI Application           │
                              │                                         │
┌──────────────┐  JWT Bearer  │  ┌──────────────────────────────────┐  │
│ React Dashboard│────────────▶│  │         Middleware Stack          │  │
└──────────────┘              │  │  CORS · RateLimit · SecHeaders   │  │
                              │  │  RequestLogging                   │  │
                              │  └──────────────────────────────────┘  │
                              │                                         │
                              │  ┌──────────┐  ┌──────────────────┐   │
                              │  │ /api/v1/ │  │  Exception       │   │
                              │  │ Routers  │  │  Handlers        │   │
                              │  └────┬─────┘  └──────────────────┘   │
                              │       │                                 │
                              └───────┼─────────────────────────────────┘
                                      │
                    ┌─────────────────▼──────────────────────┐
                    │            Module Layer                  │
                    │                                          │
                    │  ┌──────────┐  ┌───────────────────┐   │
                    │  │Controller│  │Controller validates│   │
                    │  │(Router)  │──▶ DTOs (Pydantic)   │   │
                    │  └────┬─────┘  └───────────────────┘   │
                    │       │                                  │
                    │  ┌────▼─────┐                           │
                    │  │ Service  │  ← Lógica de negocio      │
                    │  └────┬─────┘    Motor de reglas        │
                    │       │          (Strategy pattern)      │
                    │  ┌────▼──────────┐                      │
                    │  │  Repository   │  ← Interfaz abstracta│
                    │  │  (Interface)  │                       │
                    │  └────┬──────────┘                      │
                    │       │                                  │
                    │  ┌────▼──────────────┐                  │
                    │  │SQLAlchemy         │                  │
                    │  │Implementation     │                  │
                    │  └────┬──────────────┘                  │
                    └───────┼──────────────────────────────────┘
                            │
                    ┌───────▼──────────┐
                    │   PostgreSQL     │
                    │                  │
                    │  devices         │
                    │  readings        │
                    │  alerts          │
                    │  thresholds      │
                    │  users           │
                    └──────────────────┘
```

## Estructura de carpetas

```
GreenPulse/
├── main.py                     # Entry point FastAPI
├── config/
│   └── settings.py             # Pydantic Settings (variables de entorno)
├── src/
│   ├── modules/                # Módulos de dominio (una carpeta por bounded context)
│   │   ├── system/             # Healthcheck
│   │   ├── auth/               # Registro, login, JWT
│   │   ├── devices/            # CRUD de nodos ESP32
│   │   ├── readings/           # Ingesta y consulta de telemetría
│   │   ├── alerts/             # Alertas generadas por el motor de reglas
│   │   └── thresholds/         # Umbrales por dispositivo/variable
│   ├── shared/
│   │   ├── exceptions/         # Jerarquía de excepciones de dominio
│   │   ├── middleware/         # Security headers, request logging
│   │   ├── response/           # Envelopes SuccessResponse / ErrorResponse
│   │   └── utils/              # PaginationParams y helpers reutilizables
│   └── infrastructure/
│       ├── database/           # Engine, sesiones, Base declarativa, registry
│       ├── security/           # Hashing, JWT, API Key
│       └── logging/            # Configuración loguru
├── alembic/                    # Migraciones de esquema
├── tests/
│   ├── unit/                   # Tests sin BD (mocks de repositorios)
│   └── integration/            # Tests con BD SQLite en memoria
└── docs/
    └── architecture.md
```

## Principios aplicados

| Principio | Aplicación |
|-----------|-----------|
| SRP | Cada clase tiene una sola razón para cambiar (controllers ≠ services ≠ repositories) |
| OCP | Motor de reglas usa Strategy pattern — nuevos tipos de alerta sin modificar código existente |
| LSP | `IReadingRepository` (abstracta) → `SQLAlchemyReadingRepository` (concreta) |
| ISP | Interfaces pequeñas por módulo, sin megaclases |
| DIP | Services dependen de la interfaz del repositorio; FastAPI inyecta via `Depends()` |

## Flujo de datos — ingesta de lectura

```
ESP32 POST /api/v1/readings
  → [X-API-Key auth] → ReadingController.create_reading()
  → ReadingService.ingest()
  → ReadingRepository.save()
  → ThresholdService.evaluate()      ← motor de reglas
  → AlertRepository.save() (si alerta)
  → ReadingResponse (201 Created)
```
