"""Valuation e contexto para OTC complexo, com falha segura."""

from __future__ import annotations

from ..ids import stable_id
from ..models import (
    EvidenceQuality,
    Finding,
    FindingDisposition,
    QualityReport,
    SurveillanceDataset,
)
from .base import clamp, scaled


class OtcComplexDetector:
    scenario = "OTC_COMPLEX"
    version = "1.0.0"

    def __init__(self, ipv_z_threshold: float = 2.0) -> None:
        self.ipv_z_threshold = ipv_z_threshold

    def detect(self, dataset: SurveillanceDataset, quality: QualityReport) -> list[Finding]:
        if self.scenario in quality.blocked_scenarios:
            return []
        clients = {item.client_id: item for item in dataset.clients}
        findings: list[Finding] = []
        for trade in dataset.otc_trades:
            ref = f"record://otc/{trade.structure_id}"
            required = {
                "independent_value": trade.independent_value,
                "model_uncertainty": trade.model_uncertainty,
                "liquidity_band": trade.liquidity_band,
                "model_id": trade.model_id,
                "model_version": trade.model_version,
                "market_snapshot_id": trade.market_snapshot_id,
            }
            missing = tuple(sorted(name for name, value in required.items() if value is None))
            if missing:
                findings.append(
                    Finding(
                        finding_id=stable_id(
                            "F-OTC", self.version, trade.structure_id, trade.event_time, dataset.snapshot_id
                        ),
                        scenario=self.scenario,
                        scenario_version=self.version,
                        subject_id=trade.client_id,
                        subject_type="CLIENT",
                        window_start=trade.event_time,
                        window_end=trade.event_time,
                        strength=0.55,
                        materiality=clamp(trade.notional / 1_000_000),
                        urgency=0.55,
                        evidence_quality=EvidenceQuality.INCONCLUSIVE,
                        disposition=FindingDisposition.INCONCLUSIVE,
                        reason_codes=("INCONCLUSIVE_VALUATION",),
                        feature_values={
                            "structure_id": trade.structure_id,
                            "notional": trade.notional,
                            "strategy_chain_id": trade.strategy_chain_id,
                        },
                        evidence_refs=(ref,),
                        missing_data=missing,
                        limitations=("Dado crítico ausente nunca é convertido em baixo risco.",),
                    )
                )
                continue

            scale = max(trade.model_uncertainty or 0, trade.liquidity_band or 0, 1e-9)
            ipv_z = ((trade.trade_premium - (trade.independent_value or 0)) / scale)
            client = clients.get(trade.client_id)
            suitability_mismatch = bool(
                client and trade.product_complexity > client.complexity_limit
            )
            reasons: list[str] = []
            if abs(ipv_z) >= self.ipv_z_threshold:
                reasons.append("IPV_NORMALIZED_DEVIATION_HIGH")
            if suitability_mismatch:
                reasons.append("SUITABILITY_COMPLEXITY_MISMATCH")
            if trade.rolled_from:
                reasons.append("STRATEGY_ROLLOVER_CHAIN")
            if not reasons:
                continue
            strength = clamp(
                (
                    scaled(abs(ipv_z), self.ipv_z_threshold)
                    + float(suitability_mismatch)
                    + float(bool(trade.rolled_from))
                )
                / 3
            )
            findings.append(
                Finding(
                    finding_id=stable_id(
                        "F-OTC", self.version, trade.structure_id, trade.event_time, dataset.snapshot_id
                    ),
                    scenario=self.scenario,
                    scenario_version=self.version,
                    subject_id=trade.client_id,
                    subject_type="CLIENT",
                    window_start=trade.event_time,
                    window_end=trade.event_time,
                    strength=strength,
                    materiality=clamp(trade.notional / 1_000_000),
                    urgency=0.55,
                    evidence_quality=EvidenceQuality.COMPLETE,
                    disposition=FindingDisposition.ACTIONABLE,
                    reason_codes=tuple(reasons),
                    feature_values={
                        "structure_id": trade.structure_id,
                        "strategy_chain_id": trade.strategy_chain_id,
                        "ipv_z": round(ipv_z, 6),
                        "product_complexity": trade.product_complexity,
                        "client_complexity_limit": client.complexity_limit if client else None,
                        "notional": trade.notional,
                    },
                    evidence_refs=(ref,),
                    limitations=(
                        "O desvio IPV deve ser revisado por especialista e Model Risk.",
                        "Incerteza de modelo e liquidez são preservadas no denominador.",
                    ),
                )
            )
        return findings

