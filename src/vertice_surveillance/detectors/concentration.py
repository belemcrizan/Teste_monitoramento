"""Concentração relacional atípica — não é conclusão de conluio."""

from __future__ import annotations

from collections import defaultdict

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


class ConcentrationDetector:
    scenario = "CONCENTRATION"
    version = "1.0.0"

    def __init__(
        self,
        share_threshold: float = 0.35,
        recurring_days_threshold: int = 3,
        symmetry_threshold: float = 0.75,
    ) -> None:
        self.share_threshold = share_threshold
        self.recurring_days_threshold = recurring_days_threshold
        self.symmetry_threshold = symmetry_threshold

    def detect(self, dataset: SurveillanceDataset, quality: QualityReport) -> list[Finding]:
        if self.scenario in quality.blocked_scenarios:
            return []
        trades = [
            trade
            for trade in dataset.trades
            if trade.status == "CONFIRMED" and trade.counterparty_id is not None
        ]
        instrument_total: dict[str, float] = defaultdict(float)
        groups: dict[tuple[str, str, str], list[TradeEvent]] = defaultdict(list)
        client_instrument_counterparties: dict[tuple[str, str], dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        for trade in trades:
            instrument_total[trade.instrument_id] += trade.notional
            key = (trade.client_id, trade.counterparty_id or "UNKNOWN", trade.instrument_id)
            groups[key].append(trade)
            client_instrument_counterparties[(trade.client_id, trade.instrument_id)][
                trade.counterparty_id or "UNKNOWN"
            ] += trade.notional

        findings: list[Finding] = []
        for (client_id, counterparty_id, instrument_id), group in sorted(groups.items()):
            pair_notional = sum(item.notional for item in group)
            share = pair_notional / max(instrument_total[instrument_id], 1e-9)
            days = len({item.event_time.date() for item in group})
            buy_qty = sum(item.quantity for item in group if item.side == "BUY")
            sell_qty = sum(item.quantity for item in group if item.side == "SELL")
            symmetry = 1 - abs(buy_qty - sell_qty) / max(buy_qty + sell_qty, 1e-9)
            cp_values = client_instrument_counterparties[(client_id, instrument_id)].values()
            client_total = sum(cp_values)
            hhi = sum((value / max(client_total, 1e-9)) ** 2 for value in cp_values)

            reasons: list[str] = []
            if share >= self.share_threshold:
                reasons.append("PAIR_OBSERVED_VOLUME_SHARE_HIGH")
            if days >= self.recurring_days_threshold:
                reasons.append("RECURRENT_DAYS_HIGH")
            if symmetry >= self.symmetry_threshold:
                reasons.append("QUANTITY_SYMMETRY_HIGH")
            if hhi >= 0.5:
                reasons.append("COUNTERPARTY_CONCENTRATION_HIGH")
            if len(group) < 4 or len(reasons) < 2:
                continue

            start, end = window(group)
            strength = clamp(
                (
                    scaled(share, self.share_threshold)
                    + scaled(float(days), float(self.recurring_days_threshold))
                    + scaled(symmetry, self.symmetry_threshold)
                    + hhi
                )
                / 4
            )
            finding_id = stable_id(
                "F-CONC", self.version, client_id, counterparty_id, instrument_id, start, end, dataset.snapshot_id
            )
            findings.append(
                Finding(
                    finding_id=finding_id,
                    scenario=self.scenario,
                    scenario_version=self.version,
                    subject_id=client_id,
                    subject_type="CLIENT",
                    window_start=start,
                    window_end=end,
                    strength=strength,
                    materiality=clamp(pair_notional / 1_000_000),
                    urgency=0.35,
                    evidence_quality=EvidenceQuality.COMPLETE,
                    disposition=(
                        FindingDisposition.ACTIONABLE if len(reasons) >= 3 else FindingDisposition.OBSERVATION
                    ),
                    reason_codes=tuple(reasons),
                    feature_values={
                        "pair_observed_volume_share": round(share, 6),
                        "distinct_trade_days": days,
                        "quantity_symmetry": round(symmetry, 6),
                        "counterparty_hhi": round(hhi, 6),
                        "pair_notional": round(pair_notional, 2),
                        "counterparty_id": counterparty_id,
                        "instrument_id": instrument_id,
                    },
                    evidence_refs=tuple(f"record://trade/{item.trade_id}" for item in group),
                    limitations=(
                        "A participação usa o universo observado pela instituição, não market share total.",
                        "Concentração relacional não prova coordenação ou intenção.",
                    ),
                )
            )
        return findings

