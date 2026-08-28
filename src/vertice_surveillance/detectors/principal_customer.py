"""Conduta principal versus cliente com benchmark e preservação de neutralidade."""

from __future__ import annotations

from collections import defaultdict

from ..ids import stable_id
from ..market_reference import FixedIncomeReferenceService
from ..models import (
    ActorType,
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


class PrincipalCustomerConductDetector:
    scenario = "PRINCIPAL_CUSTOMER_CONDUCT"
    version = "1.0.0"

    def __init__(
        self,
        adverse_price_bps_threshold: float = 50.0,
        minimum_trade_count: int = 2,
        max_reference_age_seconds: int = 3600,
    ) -> None:
        self.adverse_threshold = adverse_price_bps_threshold
        self.minimum_trade_count = minimum_trade_count
        self.max_reference_age_seconds = max_reference_age_seconds

    def detect(self, dataset: SurveillanceDataset, quality: QualityReport) -> list[Finding]:
        if self.scenario in quality.blocked_scenarios:
            return []
        service = FixedIncomeReferenceService(dataset.fixed_income_references)
        groups: dict[tuple[str, str], list[tuple[FixedIncomeTrade, PartyView]]] = defaultdict(list)
        for trade in dataset.fixed_income_trades:
            view = client_view(trade) if trade.status == "CONFIRMED" else None
            if view and view.counterparty_actor_type == ActorType.TREASURY_PROP:
                groups[(view.party_id, trade.instrument_id)].append((trade, view))

        findings: list[Finding] = []
        for (client_id, instrument_id), group in sorted(groups.items()):
            if len(group) < self.minimum_trade_count:
                continue
            adverse_values: list[float] = []
            reference_ids: list[str] = []
            missing_reasons: set[str] = set()
            for trade, view in group:
                match = service.latest_at(
                    instrument_id, trade.event_time, self.max_reference_age_seconds
                )
                if match.reference is None or match.reference.price_unit is None:
                    missing_reasons.add(match.reason_code or "FIXED_INCOME_PRICE_REFERENCE_MISSING")
                    continue
                reference = match.reference
                assert reference.price_unit is not None
                reference_price = reference.price_unit
                adverse = (
                    (trade.price_unit - reference_price) / reference_price * 10_000
                    if view.side == Side.BUY
                    else (reference_price - trade.price_unit) / reference_price * 10_000
                )
                adverse_values.append(adverse)
                reference_ids.append(reference.reference_id)

            start, end = window(trade for trade, _ in group)
            trade_refs = tuple(
                f"record://fixed-income-trade/{trade.trade_id}" for trade, _ in group
            )
            if not adverse_values:
                findings.append(
                    Finding(
                        finding_id=stable_id(
                            "F-PC",
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
                        strength=0.55,
                        materiality=clamp(
                            sum(trade.financial_value for trade, _ in group) / 1_000_000
                        ),
                        urgency=0.6,
                        evidence_quality=EvidenceQuality.INCONCLUSIVE,
                        disposition=FindingDisposition.INCONCLUSIVE,
                        reason_codes=tuple(sorted(missing_reasons)),
                        feature_values={
                            "instrument_id": instrument_id,
                            "principal_customer_trade_count": len(group),
                            "usable_price_reference_count": 0,
                        },
                        evidence_refs=trade_refs,
                        missing_data=("contemporaneous_price_reference",),
                        limitations=(
                            "Sem referência independente, a execução principal versus cliente não é classificada como aderente.",
                        ),
                    )
                )
                continue

            positive_adverse = [max(value, 0.0) for value in adverse_values]
            mean_adverse = sum(positive_adverse) / len(positive_adverse)
            max_adverse = max(positive_adverse)
            if max_adverse < self.adverse_threshold and mean_adverse < self.adverse_threshold:
                continue
            reference_refs = tuple(
                f"record://fixed-income-reference/{reference_id}"
                for reference_id in dict.fromkeys(reference_ids)
            )
            findings.append(
                Finding(
                    finding_id=stable_id(
                        "F-PC",
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
                            scaled(max_adverse, self.adverse_threshold)
                            + scaled(mean_adverse, self.adverse_threshold)
                        )
                        / 2
                    ),
                    materiality=clamp(sum(trade.financial_value for trade, _ in group) / 1_000_000),
                    urgency=0.65,
                    evidence_quality=(
                        EvidenceQuality.DEGRADED if missing_reasons else EvidenceQuality.COMPLETE
                    ),
                    disposition=FindingDisposition.ACTIONABLE,
                    reason_codes=(
                        "REPEATED_PRINCIPAL_CUSTOMER_FLOW",
                        "CLIENT_ADVERSE_PRICE_DEVIATION_HIGH",
                        "TREASURY_PROP_COUNTERPARTY",
                    ),
                    feature_values={
                        "instrument_id": instrument_id,
                        "principal_customer_trade_count": len(group),
                        "usable_price_reference_count": len(adverse_values),
                        "mean_client_adverse_price_bps": round(mean_adverse, 6),
                        "max_client_adverse_price_bps": round(max_adverse, 6),
                    },
                    evidence_refs=trade_refs + reference_refs,
                    missing_data=(("reference_for_part_of_window",) if missing_reasons else ()),
                    limitations=(
                        "O sinal não prova conflito de interesse, vantagem indevida ou preço injusto.",
                        "O analista deve considerar liquidez, tamanho, mandato e custos de hedge.",
                    ),
                )
            )
        return findings
