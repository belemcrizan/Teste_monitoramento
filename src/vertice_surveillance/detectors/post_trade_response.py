"""Associação entre negócio e resposta posterior, sem inferência causal automática."""

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
    Side,
    SurveillanceDataset,
)
from .base import clamp, scaled, window
from .treasury_common import PartyView, client_view


class PostTradeMarketResponseDetector:
    scenario = "FIXED_INCOME_POST_TRADE_RESPONSE"
    version = "1.0.0"

    def __init__(
        self,
        response_threshold_bps: float = 15.0,
        minimum_aligned_events: int = 2,
        horizon_seconds: int = 900,
        max_reference_age_seconds: int = 3600,
    ) -> None:
        self.response_threshold = response_threshold_bps
        self.minimum_aligned_events = minimum_aligned_events
        self.horizon_seconds = horizon_seconds
        self.max_reference_age_seconds = max_reference_age_seconds

    def detect(self, dataset: SurveillanceDataset, quality: QualityReport) -> list[Finding]:
        if self.scenario in quality.blocked_scenarios:
            return []
        service = FixedIncomeReferenceService(dataset.fixed_income_references)
        groups: dict[tuple[str, str], list[tuple[FixedIncomeTrade, PartyView]]] = defaultdict(list)
        for trade in dataset.fixed_income_trades:
            view = client_view(trade) if trade.status == "CONFIRMED" else None
            if view:
                groups[(view.party_id, trade.instrument_id)].append((trade, view))

        findings: list[Finding] = []
        for (client_id, instrument_id), group in sorted(groups.items()):
            if len(group) < self.minimum_aligned_events:
                continue
            aligned: list[float] = []
            matched_reference_ids: list[str] = []
            missing_reasons: set[str] = set()
            for trade, view in group:
                before = service.latest_at(
                    instrument_id, trade.event_time, self.max_reference_age_seconds
                )
                after = service.first_after(instrument_id, trade.event_time, self.horizon_seconds)
                if before.reference is None or after.reference is None:
                    missing_reasons.add(
                        before.reason_code or after.reason_code or "POST_TRADE_REFERENCE_MISSING"
                    )
                    continue
                sign = 1.0 if view.side == Side.BUY else -1.0
                responses: list[float] = []
                if before.reference.price_unit and after.reference.price_unit:
                    responses.append(
                        sign
                        * (after.reference.price_unit - before.reference.price_unit)
                        / before.reference.price_unit
                        * 10_000
                    )
                if (
                    before.reference.yield_rate is not None
                    and after.reference.yield_rate is not None
                ):
                    responses.append(
                        -sign * (after.reference.yield_rate - before.reference.yield_rate) * 10_000
                    )
                if not responses:
                    missing_reasons.add("POST_TRADE_COMPARABLE_METRIC_MISSING")
                    continue
                aligned.append(max(responses))
                matched_reference_ids.extend(
                    [before.reference.reference_id, after.reference.reference_id]
                )

            significant = [value for value in aligned if value >= self.response_threshold]
            start, end = window(trade for trade, _ in group)
            trade_refs = tuple(
                f"record://fixed-income-trade/{trade.trade_id}" for trade, _ in group
            )
            reference_refs = tuple(
                f"record://fixed-income-reference/{reference_id}"
                for reference_id in dict.fromkeys(matched_reference_ids)
            )
            if not aligned:
                findings.append(
                    Finding(
                        finding_id=stable_id(
                            "F-PTR",
                            self.version,
                            client_id,
                            instrument_id,
                            start,
                            end,
                            dataset.snapshot_id,
                        ),
                        scenario=self.scenario,
                        scenario_version=self.version,
                        subject_id=client_id,
                        subject_type="CLIENT",
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
                            "matched_response_count": 0,
                            "horizon_seconds": self.horizon_seconds,
                        },
                        evidence_refs=trade_refs,
                        missing_data=("pre_and_post_trade_market_reference",),
                        limitations=(
                            "Sem referências antes e depois, a resposta de mercado não pode ser estimada.",
                        ),
                    )
                )
                continue
            if len(significant) < self.minimum_aligned_events:
                continue
            findings.append(
                Finding(
                    finding_id=stable_id(
                        "F-PTR",
                        self.version,
                        client_id,
                        instrument_id,
                        start,
                        end,
                        dataset.snapshot_id,
                    ),
                    scenario=self.scenario,
                    scenario_version=self.version,
                    subject_id=client_id,
                    subject_type="CLIENT",
                    window_start=start,
                    window_end=end,
                    strength=clamp(
                        (
                            scaled(max(significant), self.response_threshold)
                            + len(significant) / max(len(group), 1)
                        )
                        / 2
                    ),
                    materiality=clamp(sum(trade.financial_value for trade, _ in group) / 1_000_000),
                    urgency=0.55,
                    evidence_quality=(
                        EvidenceQuality.DEGRADED if missing_reasons else EvidenceQuality.COMPLETE
                    ),
                    disposition=FindingDisposition.ACTIONABLE,
                    reason_codes=("REPEATED_ALIGNED_POST_TRADE_RESPONSE",),
                    feature_values={
                        "instrument_id": instrument_id,
                        "trade_count": len(group),
                        "matched_response_count": len(aligned),
                        "significant_aligned_response_count": len(significant),
                        "max_aligned_response_bps": round(max(significant), 6),
                        "horizon_seconds": self.horizon_seconds,
                    },
                    evidence_refs=trade_refs + reference_refs,
                    missing_data=(("reference_for_part_of_window",) if missing_reasons else ()),
                    limitations=(
                        "O detector mede associação temporal; não atribui causalidade nem influência de preço.",
                        "Eventos de mercado e liquidez devem ser avaliados pelo analista.",
                    ),
                )
            )
        return findings
