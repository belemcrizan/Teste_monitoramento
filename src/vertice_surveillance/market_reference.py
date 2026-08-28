"""Seleção temporal de referências sem look-ahead e com freshness explícita."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from .models import FixedIncomeReference


@dataclass(frozen=True, slots=True)
class ReferenceMatch:
    reference: FixedIncomeReference | None
    age_seconds: float | None
    reason_code: str | None = None


class FixedIncomeReferenceService:
    """Indexa snapshots e impede o uso acidental de informação futura."""

    def __init__(self, references: tuple[FixedIncomeReference, ...]) -> None:
        grouped: dict[str, list[FixedIncomeReference]] = defaultdict(list)
        for reference in references:
            grouped[reference.instrument_id].append(reference)
        self._by_instrument = {
            instrument_id: tuple(sorted(items, key=lambda item: item.reference_time))
            for instrument_id, items in grouped.items()
        }

    def latest_at(
        self,
        instrument_id: str,
        at: datetime,
        max_age_seconds: int,
    ) -> ReferenceMatch:
        candidates = [
            item for item in self._by_instrument.get(instrument_id, ()) if item.reference_time <= at
        ]
        if not candidates:
            return ReferenceMatch(None, None, "FIXED_INCOME_REFERENCE_MISSING")
        reference = candidates[-1]
        age = (at - reference.reference_time).total_seconds()
        if age > max_age_seconds:
            return ReferenceMatch(None, age, "FIXED_INCOME_REFERENCE_STALE")
        return ReferenceMatch(reference, age)

    def first_after(
        self,
        instrument_id: str,
        at: datetime,
        horizon_seconds: int,
    ) -> ReferenceMatch:
        candidates = [
            item
            for item in self._by_instrument.get(instrument_id, ())
            if at < item.reference_time
            and (item.reference_time - at).total_seconds() <= horizon_seconds
        ]
        if not candidates:
            return ReferenceMatch(None, None, "POST_TRADE_REFERENCE_MISSING")
        reference = candidates[0]
        age = (reference.reference_time - at).total_seconds()
        return ReferenceMatch(reference, age)
