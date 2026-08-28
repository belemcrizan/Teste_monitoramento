"""Padrões associados à manipulação, condicionados à observabilidade disponível."""

from __future__ import annotations

from collections import defaultdict
from datetime import time

from ..ids import stable_id
from ..models import (
    EvidenceQuality,
    Finding,
    FindingDisposition,
    QualityReport,
    SurveillanceDataset,
    TradeEvent,
)
from .base import clamp, scaled, window


class ManipulationBehaviorDetector:
    scenario = "MANIPULATION_BEHAVIOR"
    version = "1.0.0"

    def __init__(self, robust_deviation_threshold: float = 2.0) -> None:
        self.robust_deviation_threshold = robust_deviation_threshold

    def detect(self, dataset: SurveillanceDataset, quality: QualityReport) -> list[Finding]:
        if self.scenario in quality.blocked_scenarios:
            return []
        groups: dict[tuple[str, str, object], list[TradeEvent]] = defaultdict(list)
        instrument_notional: dict[tuple[str, object], float] = defaultdict(float)
        for trade in dataset.trades:
            if trade.status != "CONFIRMED":
                continue
            day = trade.event_time.date()
            groups[(trade.client_id, trade.instrument_id, day)].append(trade)
            instrument_notional[(trade.instrument_id, day)] += trade.notional

        findings: list[Finding] = []
        for (client_id, instrument_id, _day), group in sorted(groups.items(), key=str):
            close_trades = [item for item in group if item.event_time.timetz().replace(tzinfo=None) >= time(16, 45)]
            if not close_trades:
                continue
            with_reference = [item for item in close_trades if item.reference_price is not None]
            start, end = window(close_trades)
            base_evidence = tuple(f"record://trade/{item.trade_id}" for item in close_trades)
            if not with_reference:
                findings.append(
                    Finding(
                        finding_id=stable_id(
                            "F-MANIP", self.version, client_id, instrument_id, start, end, dataset.snapshot_id
                        ),
                        scenario=self.scenario,
                        scenario_version=self.version,
                        subject_id=client_id,
                        subject_type="CLIENT",
                        window_start=start,
                        window_end=end,
                        strength=0.5,
                        materiality=clamp(sum(item.notional for item in close_trades) / 1_000_000),
                        urgency=0.8,
                        evidence_quality=EvidenceQuality.INCONCLUSIVE,
                        disposition=FindingDisposition.INCONCLUSIVE,
                        reason_codes=("CLOSE_WINDOW_ACTIVITY", "MARKET_REFERENCE_MISSING"),
                        feature_values={"instrument_id": instrument_id, "close_trade_count": len(close_trades)},
                        evidence_refs=base_evidence,
                        missing_data=("contemporary_market_reference",),
                        limitations=("Não é possível avaliar impacto de preço sem referência contemporânea.",),
                    )
                )
                continue

            deviations: list[float] = []
            for item in with_reference:
                reference = item.reference_price or 0
                scale = max(item.market_spread or 0, reference * 0.003, 1e-9)
                deviations.append((item.price - reference) / scale)
            max_deviation = max(abs(value) for value in deviations)
            buy_notional = sum(item.notional for item in close_trades if item.side == "BUY")
            sell_notional = sum(item.notional for item in close_trades if item.side == "SELL")
            total = buy_notional + sell_notional
            directionality = abs(buy_notional - sell_notional) / max(total, 1e-9)
            participation = total / max(instrument_notional[(instrument_id, close_trades[0].event_time.date())], 1e-9)
            position_benefit = any(
                (item.side == "BUY" and (item.position_before or 0) > 0 and item.price > (item.reference_price or item.price))
                or (
                    item.side == "SELL"
                    and (item.position_before or 0) < 0
                    and item.price < (item.reference_price or item.price)
                )
                for item in with_reference
            )
            reasons = ["CLOSE_WINDOW_ACTIVITY"]
            if max_deviation >= self.robust_deviation_threshold:
                reasons.append("ROBUST_PRICE_DEVIATION_HIGH")
            if directionality >= 0.8:
                reasons.append("DIRECTIONALITY_HIGH")
            if participation >= 0.2:
                reasons.append("OBSERVED_WINDOW_PARTICIPATION_HIGH")
            if position_benefit:
                reasons.append("POSITION_BENEFIT_ALIGNED")
            # Timing + direção + participação, sem desvio ou benefício econômico,
            # é contexto insuficiente para um finding acionável.
            if (
                max_deviation < self.robust_deviation_threshold
                and not position_benefit
            ) or len(reasons) < 3:
                continue
            strength = clamp(
                (
                    scaled(max_deviation, self.robust_deviation_threshold)
                    + directionality
                    + participation
                    + float(position_benefit)
                )
                / 4
            )
            limitations = [
                "O achado descreve comportamento associado; não conclui manipulação ou intenção.",
            ]
            if not dataset.orders:
                limitations.append("Sem order lifecycle/livro, não há cobertura de spoofing ou layering.")
            findings.append(
                Finding(
                    finding_id=stable_id(
                        "F-MANIP", self.version, client_id, instrument_id, start, end, dataset.snapshot_id
                    ),
                    scenario=self.scenario,
                    scenario_version=self.version,
                    subject_id=client_id,
                    subject_type="CLIENT",
                    window_start=start,
                    window_end=end,
                    strength=strength,
                    materiality=clamp(total / 1_000_000),
                    urgency=0.9,
                    evidence_quality=EvidenceQuality.COMPLETE,
                    disposition=FindingDisposition.ACTIONABLE,
                    reason_codes=tuple(reasons),
                    feature_values={
                        "instrument_id": instrument_id,
                        "max_robust_price_deviation": round(max_deviation, 6),
                        "directionality": round(directionality, 6),
                        "observed_window_participation": round(participation, 6),
                        "position_benefit_aligned": position_benefit,
                    },
                    evidence_refs=base_evidence,
                    limitations=tuple(limitations),
                )
            )
        return findings
