"""Threshold evaluation strategies (Strategy pattern).

IThresholdStrategy defines the contract; concrete implementations can be
swapped at runtime or in tests without changing the RulesEngine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.modules.alerts.models.alert import AlertSeverity
from src.modules.thresholds.models.threshold import Threshold


@dataclass
class Violation:
    """A single sensor field that breached its configured limit."""

    field: str
    value: float
    threshold_min: float | None
    threshold_max: float | None
    severity: AlertSeverity


class IThresholdStrategy(ABC):
    @abstractmethod
    def evaluate(
        self,
        field: str,
        value: float,
        min_val: float | None,
        max_val: float | None,
    ) -> tuple[bool, AlertSeverity]:
        """Return (is_violated, severity). Called once per sensor field."""
        ...


class RangeCheckStrategy(IThresholdStrategy):
    """Checks whether a value falls outside [min_val, max_val].

    Severity is proportional to how far the value deviates from the breached
    limit, relative to that limit's magnitude:
        < 10% outside → low
        10–30% outside → medium
        30–50% outside → high
        > 50% outside  → critical
    """

    def evaluate(
        self,
        field: str,
        value: float,
        min_val: float | None,
        max_val: float | None,
    ) -> tuple[bool, AlertSeverity]:
        if min_val is not None and value < min_val:
            return True, self._severity(min_val - value, min_val)
        if max_val is not None and value > max_val:
            return True, self._severity(value - max_val, max_val)
        return False, AlertSeverity.low

    @staticmethod
    def _severity(deviation: float, reference: float) -> AlertSeverity:
        if reference == 0:
            return AlertSeverity.medium
        pct = abs(deviation / reference) * 100
        if pct < 10:
            return AlertSeverity.low
        if pct < 30:
            return AlertSeverity.medium
        if pct < 50:
            return AlertSeverity.high
        return AlertSeverity.critical


def get_limits(threshold: Threshold, field: str) -> tuple[float | None, float | None]:
    """Extract (min, max) for a sensor field from a Threshold record."""
    return (
        getattr(threshold, f"{field}_min", None),
        getattr(threshold, f"{field}_max", None),
    )
