"""Rules engine that applies a threshold strategy to a sensor reading."""

from src.modules.readings.models.reading import Reading
from src.modules.readings.repositories.reading_repository import AGGREGATABLE_FIELDS
from src.modules.thresholds.models.threshold import Threshold
from src.modules.thresholds.rules.strategy import IThresholdStrategy, Violation, get_limits


class RulesEngine:
    """Evaluates a Reading against a Threshold using an injected strategy.

    The strategy can be swapped (e.g., for testing) without modifying this class.
    """

    def __init__(self, strategy: IThresholdStrategy) -> None:
        self._strategy = strategy

    def evaluate(self, reading: Reading, threshold: Threshold) -> list[Violation]:
        """Return all sensor fields that breach their configured limits."""
        violations: list[Violation] = []
        for field in AGGREGATABLE_FIELDS:
            value = getattr(reading, field, None)
            if value is None:
                continue
            min_val, max_val = get_limits(threshold, field)
            if min_val is None and max_val is None:
                continue
            violated, severity = self._strategy.evaluate(field, value, min_val, max_val)
            if violated:
                violations.append(
                    Violation(
                        field=field,
                        value=value,
                        threshold_min=min_val,
                        threshold_max=max_val,
                        severity=severity,
                    )
                )
        return violations
