"""Participação e acumulação no universo observado, sem alegar market share total."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ..ids import stable_id
from ..models import (
    EvidenceQuality,
    Finding,
    FindingDisposition,
    FixedIncomeTrade,
    MarketCoverageSnapshot,
    QualityReport,
    SurveillanceDataset,
)
from .base import clamp, scaled, window
from .treasury_common import PartyView, party_views


class ObservedParticipationDetector:
    scenario = "FIXED_INCOME_OBSERVED_PARTICIPATION"
    version = "1.0.0"

    def __init__(
        self,
        notional_share_threshold: float = 0.35,
        quantity_share_threshold: float = 0.35,
        trade_share_threshold: float = 0.35,
        minimum_trade_count: int = 3,
        minimum_coverage_ratio: float = 0.80,
    ) -> None:
        self.notional_threshold = notional_share_threshold
        self.quantity_threshold = quantity_share_threshold
        self.trade_threshold = trade_share_threshold
        self.minimum_trade_count = minimum_trade_count
        self.minimum_coverage_ratio = minimum_coverage_ratio

    @staticmethod
    def _coverage_for(
        instrument_id: str,
        start: datetime,
        end: datetime,
        snapshots: tuple[MarketCoverageSnapshot, ...],
    ) -> MarketCoverageSnapshot | None:
        candidates = [
            item
            for item in snapshots
            if item.instrument_id == instrument_id
            and item.window_start <= start
            and item.window_end >= end
        ]
        return max(candidates, key=lambda item: item.coverage_ratio, default=None)

    def detect(self, dataset: SurveillanceDataset, quality: QualityReport) -> list[Finding]:
        if self.scenario in quality.blocked_scenarios:
            return []
        instrument_trades: dict[str, list[FixedIncomeTrade]] = defaultdict(list)
        groups: dict[tuple[str, str, str], list[tuple[FixedIncomeTrade, PartyView]]] = defaultdict(
            list
        )
        for trade in dataset.fixed_income_trades:
            if trade.status != "CONFIRMED":
                continue
            instrument_trades[trade.instrument_id].append(trade)
            for view in party_views(trade):
                groups[(view.party_id, view.actor_type.value, trade.instrument_id)].append(
                    (trade, view)
                )

        findings: list[Finding] = []
        for (subject_id, subject_type, instrument_id), group in sorted(groups.items()):
            if len(group) < self.minimum_trade_count:
                continue
            universe = instrument_trades[instrument_id]
            total_notional = sum(item.financial_value for item in universe)
            total_quantity = sum(item.quantity for item in universe)
            notional = sum(item.financial_value for item, _ in group)
            quantity = sum(item.quantity for item, _ in group)
            notional_share = notional / max(total_notional, 1e-9)
            quantity_share = quantity / max(total_quantity, 1e-9)
            trade_share = len(group) / max(len(universe), 1)
            reasons: list[str] = []
            if notional_share >= self.notional_threshold:
                reasons.append("OBSERVED_NOTIONAL_SHARE_HIGH")
            if quantity_share >= self.quantity_threshold:
                reasons.append("OBSERVED_QUANTITY_SHARE_HIGH")
            if trade_share >= self.trade_threshold:
                reasons.append("OBSERVED_TRADE_SHARE_HIGH")
            if len(reasons) < 2:
                continue

            start, end = window(trade for trade, _ in group)
            coverage = self._coverage_for(instrument_id, start, end, dataset.market_coverage)
            coverage_ok = bool(coverage and coverage.coverage_ratio >= self.minimum_coverage_ratio)
            reason_codes = list(reasons)
            missing_data: tuple[str, ...] = ()
            if coverage is None:
                reason_codes.append("DENOMINATOR_COVERAGE_MISSING")
                missing_data = ("market_coverage_snapshot",)
            elif not coverage_ok:
                reason_codes.append("DENOMINATOR_COVERAGE_INSUFFICIENT")

            evidence_refs = [f"record://fixed-income-trade/{trade.trade_id}" for trade, _ in group]
            if coverage:
                evidence_refs.append(
                    f"record://market-coverage/{instrument_id}/{coverage.window_start.isoformat()}"
                )
            findings.append(
                Finding(
                    finding_id=stable_id(
                        "F-OBS",
                        self.version,
                        subject_id,
                        instrument_id,
                        start,
                        end,
                        dataset.snapshot_id,
                    ),
                    scenario=self.scenario,
                    scenario_version=self.version,
                    subject_id=subject_id,
                    subject_type=subject_type,
                    window_start=start,
                    window_end=end,
                    strength=clamp(
                        (
                            scaled(notional_share, self.notional_threshold)
                            + scaled(quantity_share, self.quantity_threshold)
                            + scaled(trade_share, self.trade_threshold)
                        )
                        / 3
                    ),
                    materiality=clamp(notional / 1_000_000),
                    urgency=0.45,
                    evidence_quality=(
                        EvidenceQuality.COMPLETE if coverage_ok else EvidenceQuality.INCONCLUSIVE
                    ),
                    disposition=(
                        FindingDisposition.ACTIONABLE
                        if coverage_ok
                        else FindingDisposition.INCONCLUSIVE
                    ),
                    reason_codes=tuple(reason_codes),
                    feature_values={
                        "instrument_id": instrument_id,
                        "observed_notional_share": round(notional_share, 6),
                        "observed_quantity_share": round(quantity_share, 6),
                        "observed_trade_share": round(trade_share, 6),
                        "observed_universe_trade_count": len(universe),
                        "coverage_ratio": coverage.coverage_ratio if coverage else None,
                        "coverage_source": coverage.source if coverage else None,
                        "coverage_universe": coverage.universe.value if coverage else None,
                    },
                    evidence_refs=tuple(evidence_refs),
                    missing_data=missing_data,
                    limitations=(
                        "As participações são do universo observado e não devem ser chamadas de market share.",
                        "Concentração ou acumulação não demonstra domínio de mercado ou intenção.",
                    ),
                )
            )
        return findings
