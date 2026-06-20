"""Unit tests for the rules engine and RangeCheckStrategy."""

from datetime import UTC, datetime

import pytest

from src.modules.alerts.models.alert import AlertSeverity
from src.modules.readings.models.reading import Reading
from src.modules.thresholds.models.threshold import Threshold
from src.modules.thresholds.rules.engine import RulesEngine
from src.modules.thresholds.rules.strategy import RangeCheckStrategy, Violation


def _make_threshold(**kwargs) -> Threshold:
    t = Threshold(device_id=1)
    for k, v in kwargs.items():
        setattr(t, k, v)
    t.id = 1
    t.created_at = datetime.now(UTC)
    t.updated_at = datetime.now(UTC)
    return t


def _make_reading(**sensor_kwargs) -> Reading:
    r = Reading(
        device_id=1,
        batch_id=None,
        recorded_at=datetime.now(UTC),
        **sensor_kwargs,
    )
    r.id = 1
    r.created_at = datetime.now(UTC)
    return r


engine = RulesEngine(RangeCheckStrategy())


# ── RangeCheckStrategy ────────────────────────────────────────────────────────

class TestRangeCheckStrategy:
    strategy = RangeCheckStrategy()

    def test_value_within_range_no_violation(self) -> None:
        violated, _ = self.strategy.evaluate("temperature", 22.0, 15.0, 35.0)
        assert violated is False

    def test_value_below_min_is_violation(self) -> None:
        violated, _ = self.strategy.evaluate("temperature", 5.0, 15.0, 35.0)
        assert violated is True

    def test_value_above_max_is_violation(self) -> None:
        violated, _ = self.strategy.evaluate("temperature", 40.0, 15.0, 35.0)
        assert violated is True

    def test_null_min_does_not_violate_below_max(self) -> None:
        # min=None: no lower bound. value=-100 is below max=35 so no violation.
        violated, _ = self.strategy.evaluate("temperature", -100.0, None, 35.0)
        assert violated is False

    def test_null_min_still_checks_max(self) -> None:
        # min=None: no lower bound. value=50 is ABOVE max=35 → violation.
        violated, _ = self.strategy.evaluate("temperature", 50.0, None, 35.0)
        assert violated is True

    def test_null_max_does_not_violate_above_min(self) -> None:
        # max=None: no upper bound. value=100 is above min=15 so no violation.
        violated, _ = self.strategy.evaluate("temperature", 100.0, 15.0, None)
        assert violated is False

    def test_null_max_still_checks_min(self) -> None:
        # max=None: no upper bound. value=5 is BELOW min=15 → violation.
        violated, _ = self.strategy.evaluate("temperature", 5.0, 15.0, None)
        assert violated is True

    def test_both_null_never_violates(self) -> None:
        violated, _ = self.strategy.evaluate("temperature", 999.0, None, None)
        assert violated is False

    def test_small_deviation_is_low_severity(self) -> None:
        # 5% below min=100 → low
        _, severity = self.strategy.evaluate("pressure", 95.0, 100.0, None)
        assert severity == AlertSeverity.low

    def test_medium_deviation(self) -> None:
        # 20% below min=100 → medium
        _, severity = self.strategy.evaluate("pressure", 80.0, 100.0, None)
        assert severity == AlertSeverity.medium

    def test_high_deviation(self) -> None:
        # 40% above max=100 → high
        _, severity = self.strategy.evaluate("pressure", 140.0, None, 100.0)
        assert severity == AlertSeverity.high

    def test_critical_deviation(self) -> None:
        # 60% above max=100 → critical
        _, severity = self.strategy.evaluate("pressure", 160.0, None, 100.0)
        assert severity == AlertSeverity.critical


# ── RulesEngine ───────────────────────────────────────────────────────────────

class TestRulesEngine:
    def test_no_violations_when_all_within_range(self) -> None:
        threshold = _make_threshold(temperature_min=15.0, temperature_max=35.0)
        reading = _make_reading(temperature=22.0)
        violations = engine.evaluate(reading, threshold)
        assert violations == []

    def test_detects_temperature_violation(self) -> None:
        threshold = _make_threshold(temperature_min=15.0, temperature_max=35.0)
        reading = _make_reading(temperature=40.0)
        violations = engine.evaluate(reading, threshold)
        assert len(violations) == 1
        assert violations[0].field == "temperature"
        assert violations[0].value == 40.0

    def test_null_sensor_value_skipped(self) -> None:
        threshold = _make_threshold(temperature_min=15.0, temperature_max=35.0)
        reading = _make_reading(temperature=None)
        violations = engine.evaluate(reading, threshold)
        assert violations == []

    def test_no_threshold_limits_skips_field(self) -> None:
        threshold = _make_threshold()  # all limits are None
        reading = _make_reading(temperature=999.0)
        violations = engine.evaluate(reading, threshold)
        assert violations == []

    def test_multiple_violations_detected(self) -> None:
        threshold = _make_threshold(
            temperature_max=30.0,
            soil_humidity_min=40.0,
        )
        reading = _make_reading(temperature=50.0, soil_humidity=10.0)
        violations = engine.evaluate(reading, threshold)
        assert len(violations) == 2
        fields = {v.field for v in violations}
        assert "temperature" in fields
        assert "soil_humidity" in fields

    def test_violation_carries_threshold_limits(self) -> None:
        threshold = _make_threshold(temperature_min=15.0, temperature_max=35.0)
        reading = _make_reading(temperature=40.0)
        v: Violation = engine.evaluate(reading, threshold)[0]
        assert v.threshold_min == 15.0
        assert v.threshold_max == 35.0
