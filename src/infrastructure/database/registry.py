"""Central model registry for Alembic auto-detection.

Import every SQLAlchemy model here so that Base.metadata is fully populated
before Alembic generates or applies migrations.

Add one import per model as each module is implemented:
"""

# Stage 2 — Auth
from src.modules.auth.models.user import User  # noqa: F401

# Stage 3 — Devices
# from src.modules.devices.models.device import Device  # noqa: F401

# Stage 4 — Readings
# from src.modules.readings.models.reading import Reading  # noqa: F401

# Stage 5 — Thresholds
# from src.modules.thresholds.models.threshold import Threshold  # noqa: F401

# Stage 6 — Alerts
# from src.modules.alerts.models.alert import Alert  # noqa: F401
