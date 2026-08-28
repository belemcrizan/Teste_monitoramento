"""Conduta de mercado em Renda Fixa com referência temporal e linguagem não conclusiva."""

from __future__ import annotations

from collections import defaultdict

from ..ids import stable_id
from ..market_reference import FixedIncomeReferenceService
from ..models import (
    EvidenceQuality,
    Finding,
    FindingDisposition,
    FixedIncomeTrade,
    QualityReport,
    SurveillanceDataset,
)
from .base import clamp, scaled, window
from .treasury_common import PartyView, party_views


class FixedIncomeMarketConductDetector:
    scenario = "FIXED_INCOME_CONDUCT"
    version = "1.0.0"

    def __init__(
        self,
        price_deviation_bps_threshold: float = 75.0,
        yield_deviation_bps_threshold: float = 50.0,
        spread_deviation_bps_threshold: float = 75.0,
        max_reference_age_seconds: int = 3600,
    ) -> None:
        self.price_threshold = price_deviation_bps_threshold
        self.yield_threshold = yield_deviation_bps_threshold
        self.spread_threshold = spread_deviation_bps_threshold
        self.max_reference_age_seconds = max_reference_age_seconds

    def detect(self, dataset: SurveillanceDataset, quality: QualityReport) -> list[Finding]:
        if self.scenario in quality.blocked_scenarios:
            return []
        service = FixedIncomeReferenceService(dataset.fixed_income_references)
        groups: dict[tuple[str, str, str], list[tuple[FixedIncomeTrade, PartyView]]] = defaultdict(
            list
        )
        for trade in dataset.fixed_income_trades:
            if trade.status != "CONFIRMED":
                continue
            for view in party_views(trade):
                groups[(view.party_id, view.actor_type.value, trade.instrument_id)].append(
                    (trade, view)
                )

        findings: list[Finding] = []
        for (subject_id, subject_type, instrument_id), group in sorted(groups.items()):
            usable: list[tuple[FixedIncomeTrade, str, float, float, float, float]] = []
            missing_reasons: set[str] = set()
            evidence_refs = [f"record://fixed-income-trade/{trade.trade_id}" for trade, _ in group]
            for trade, _view in group:
                match = service.latest_at(
                    instrument_id, trade.event_time, self.max_reference_age_seconds
                )
                if match.reference is None:
                    missing_reasons.add(match.reason_code or "FIXED_INCOME_REFERENCE_MISSING")
                    continue
                reference = match.reference
                price_bps = (
                    abs(trade.price_unit - reference.price_unit) / reference.price_unit * 10_000
                    if reference.price_unit is not None
                    else 0.0
                )
                yield_bps = (
                    abs(trade.yield_rate - reference.yield_rate) * 10_000
                    if trade.yield_rate is not None and reference.yield_rate is not None
                    else 0.0
                )
                spread_bps = (
                    abs(trade.spread_bps - reference.spread_bps)
                    if trade.spread_bps is not None and reference.spread_bps is not None
                    else 0.0
                )
                usable.append(
                    (
                        trade,
                        reference.reference_id,
                        price_bps,
                        yield_bps,
                        spread_bps,
                        reference.confidence,
                    )
                )
                evidence_refs.append(f"record://fixed-income-reference/{reference.reference_id}")

            start, end = window(trade for trade, _ in group)
            if not usable:
                findings.append(
                    Finding(
                        finding_id=stable_id(
                            "F-FIC",
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
                        strength=0.5,
                        materiality=clamp(
                            sum(trade.financial_value for trade, _ in group) / 1_000_000
                        ),
                        urgency=0.45,
                        evidence_quality=EvidenceQuality.INCONCLUSIVE,
                        disposition=FindingDisposition.INCONCLUSIVE,
                        reason_codes=tuple(sorted(missing_reasons)),
                        feature_values={
                            "instrument_id": instrument_id,
                            "trade_count": len(group),
                            "usable_reference_count": 0,
                        },
                        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
                        missing_data=("contemporaneous_fixed_income_reference",),
                        limitations=(
                            "A ausência de referência contemporânea impede concluir aderência de preço, taxa ou spread.",
                        ),
                    )
                )
                continue

            max_price = max(item[2] for item in usable)
            max_yield = max(item[3] for item in usable)
            max_spread = max(item[4] for item in usable)
            reasons: list[str] = []
            if max_price >= self.price_threshold:
                reasons.append("FIXED_INCOME_PRICE_DEVIATION_HIGH")
            if max_yield >= self.yield_threshold:
                reasons.append("FIXED_INCOME_YIELD_DEVIATION_HIGH")
            if max_spread >= self.spread_threshold:
                reasons.append("FIXED_INCOME_SPREAD_DEVIATION_HIGH")
            if not reasons:
                continue

            degraded = bool(missing_reasons) or any(item[5] < 1 for item in usable)
            findings.append(
                Finding(
                    finding_id=stable_id(
                        "F-FIC",
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
                        max(
                            scaled(max_price, self.price_threshold),
                            scaled(max_yield, self.yield_threshold),
                            scaled(max_spread, self.spread_threshold),
                        )
                    ),
                    materiality=clamp(
                        sum(trade.financial_value for trade, *_rest in usable) / 1_000_000
                    ),
                    urgency=0.55,
                    evidence_quality=(
                        EvidenceQuality.DEGRADED if degraded else EvidenceQuality.COMPLETE
                    ),
                    disposition=FindingDisposition.ACTIONABLE,
                    reason_codes=tuple(reasons),
                    feature_values={
                        "instrument_id": instrument_id,
                        "trade_count": len(group),
                        "usable_reference_count": len(usable),
                        "max_price_deviation_bps": round(max_price, 6),
                        "max_yield_deviation_bps": round(max_yield, 6),
                        "max_spread_deviation_bps": round(max_spread, 6),
                    },
                    evidence_refs=tuple(dict.fromkeys(evidence_refs)),
                    missing_data=(("reference_for_part_of_window",) if missing_reasons else ()),
                    limitations=(
                        "Desvio contra referência é sinal para revisão, não prova de manipulação ou preço injusto.",
                        "A qualidade depende da metodologia, liquidez e contemporaneidade da referência.",
                    ),
                )
            )
        return findings
