"""Atividade potencialmente excessiva; conclusão de churning permanece humana."""

from __future__ import annotations

from collections import defaultdict

from ..ids import stable_id
from ..models import (
    EvidenceQuality,
    Finding,
    FindingDisposition,
    QualityReport,
    Side,
    SurveillanceDataset,
    TradeEvent,
)
from .base import clamp, scaled, window


class ChurningDetector:
    scenario = "CHURNING"
    version = "1.0.0"

    def __init__(self, turnover_threshold: float = 2.0, cost_equity_threshold: float = 0.02) -> None:
        self.turnover_threshold = turnover_threshold
        self.cost_equity_threshold = cost_equity_threshold

    @staticmethod
    def _rapid_reversal_ratio(trades: list[TradeEvent], max_days: int = 5) -> float:
        ordered = sorted(trades, key=lambda item: item.event_time)
        eligible = 0
        rapid = 0
        for index, current in enumerate(ordered):
            for later in ordered[index + 1 :]:
                if later.instrument_id != current.instrument_id or later.side == current.side:
                    continue
                eligible += 1
                if (later.event_time - current.event_time).days <= max_days:
                    rapid += 1
                break
        return rapid / eligible if eligible else 0.0

    def detect(self, dataset: SurveillanceDataset, quality: QualityReport) -> list[Finding]:
        if self.scenario in quality.blocked_scenarios:
            return []
        groups: dict[str, list[TradeEvent]] = defaultdict(list)
        for trade in dataset.trades:
            if trade.status == "CONFIRMED":
                groups[trade.client_id].append(trade)
        clients = {item.client_id: item for item in dataset.clients}
        equity_by_client: dict[str, list[float]] = defaultdict(list)
        for position in dataset.positions:
            equity_by_client[position.client_id].append(position.average_equity)

        findings: list[Finding] = []
        for client_id, trades in sorted(groups.items()):
            if len(trades) < 4:
                continue
            start, end = window(trades)
            equities = equity_by_client.get(client_id, [])
            refs = tuple(f"record://trade/{item.trade_id}" for item in trades)
            if not equities:
                findings.append(
                    Finding(
                        finding_id=stable_id(
                            "F-CHURN", self.version, client_id, start, end, dataset.snapshot_id
                        ),
                        scenario=self.scenario,
                        scenario_version=self.version,
                        subject_id=client_id,
                        subject_type="CLIENT",
                        window_start=start,
                        window_end=end,
                        strength=0.5,
                        materiality=clamp(sum(item.notional for item in trades) / 1_000_000),
                        urgency=0.4,
                        evidence_quality=EvidenceQuality.INCONCLUSIVE,
                        disposition=FindingDisposition.INCONCLUSIVE,
                        reason_codes=("ACTIVITY_VOLUME_RELEVANT", "AVERAGE_EQUITY_MISSING"),
                        feature_values={"trade_count": len(trades)},
                        evidence_refs=refs,
                        missing_data=("average_equity",),
                        limitations=("Sem patrimônio médio, turnover e custo/patrimônio não são defensáveis.",),
                    )
                )
                continue

            equity = sum(equities) / len(equities)
            buys = sum(item.notional for item in trades if item.side == Side.BUY)
            sells = sum(item.notional for item in trades if item.side == Side.SELL)
            turnover_gross = (buys + sells) / max(2 * equity, 1e-9)
            turnover_matched = min(buys, sells) / max(equity, 1e-9)
            fees = sum(item.fees for item in trades)
            cost_equity = fees / max(equity, 1e-9)
            reversal_ratio = self._rapid_reversal_ratio(trades)
            client = clients.get(client_id)
            reasons: list[str] = []
            if turnover_gross >= self.turnover_threshold:
                reasons.append("TURNOVER_ABOVE_COHORT_BASELINE")
            if cost_equity >= self.cost_equity_threshold:
                reasons.append("COST_TO_EQUITY_HIGH")
            if reversal_ratio >= 0.5:
                reasons.append("RAPID_IN_OUT_CYCLES")
            if client and client.suitability_profile.upper() == "CONSERVATIVE" and turnover_gross >= 1:
                reasons.append("SUITABILITY_MISMATCH_CONTEXT")
            if len(reasons) < 2:
                continue
            missing: list[str] = []
            evidence_quality = EvidenceQuality.COMPLETE
            if not client or client.control_source == "UNKNOWN":
                reasons.append("CLIENT_CONTROL_UNKNOWN")
                missing.append("decision_control_source")
                evidence_quality = EvidenceQuality.DEGRADED
            strength = clamp(
                (
                    scaled(turnover_gross, self.turnover_threshold)
                    + scaled(cost_equity, self.cost_equity_threshold)
                    + reversal_ratio
                )
                / 3
            )
            findings.append(
                Finding(
                    finding_id=stable_id("F-CHURN", self.version, client_id, start, end, dataset.snapshot_id),
                    scenario=self.scenario,
                    scenario_version=self.version,
                    subject_id=client_id,
                    subject_type="CLIENT",
                    window_start=start,
                    window_end=end,
                    strength=strength,
                    materiality=clamp((buys + sells) / 1_000_000),
                    urgency=0.45,
                    evidence_quality=evidence_quality,
                    disposition=FindingDisposition.ACTIONABLE,
                    reason_codes=tuple(reasons),
                    feature_values={
                        "turnover_gross": round(turnover_gross, 6),
                        "turnover_matched": round(turnover_matched, 6),
                        "cost_to_equity": round(cost_equity, 6),
                        "rapid_reversal_ratio": round(reversal_ratio, 6),
                        "average_equity": round(equity, 2),
                    },
                    evidence_refs=refs,
                    missing_data=tuple(missing),
                    limitations=(
                        "O finding indica atividade potencialmente excessiva; não conclui churning.",
                        "A reconstrução usa reversões rápidas como proxy e deve ser substituída por lot matching aprovado.",
                    ),
                )
            )
        return findings

