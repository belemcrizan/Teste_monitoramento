from __future__ import annotations

from datetime import UTC, datetime

from vertice_surveillance.market_reference import FixedIncomeReferenceService
from vertice_surveillance.models import FixedIncomeProduct, FixedIncomeReference


def _reference(reference_id: str, minute: int) -> FixedIncomeReference:
    return FixedIncomeReference(
        reference_id=reference_id,
        instrument_id="DEB-X",
        product_type=FixedIncomeProduct.DEBENTURE,
        reference_time=datetime(2026, 8, 28, 10, minute, tzinfo=UTC),
        source="TEST",
        methodology_version="1",
        price_unit=100,
    )


def test_latest_reference_never_uses_future_information() -> None:
    service = FixedIncomeReferenceService((_reference("FUTURE", 5),))
    match = service.latest_at("DEB-X", datetime(2026, 8, 28, 10, 0, tzinfo=UTC), 3600)
    assert match.reference is None
    assert match.reason_code == "FIXED_INCOME_REFERENCE_MISSING"


def test_reference_freshness_is_enforced() -> None:
    service = FixedIncomeReferenceService((_reference("OLD", 0),))
    match = service.latest_at("DEB-X", datetime(2026, 8, 28, 10, 30, tzinfo=UTC), 60)
    assert match.reference is None
    assert match.reason_code == "FIXED_INCOME_REFERENCE_STALE"


def test_first_after_respects_horizon() -> None:
    service = FixedIncomeReferenceService((_reference("AFTER", 5),))
    outside = service.first_after("DEB-X", datetime(2026, 8, 28, 10, 0, tzinfo=UTC), 120)
    inside = service.first_after("DEB-X", datetime(2026, 8, 28, 10, 0, tzinfo=UTC), 600)
    assert outside.reference is None
    assert inside.reference is not None
    assert inside.reference.reference_id == "AFTER"
