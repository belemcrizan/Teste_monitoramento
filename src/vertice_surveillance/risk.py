"""Correlação e prioridade operacional explicável."""

from __future__ import annotations

import math
from collections import defaultdict

from .config import RiskWeights
from .ids import stable_id
from .models import (
    Alert,
    EvidenceQuality,
    Finding,
    FindingDisposition,
    RiskExplanation,
)


class RiskPolicy:
    """Baseline especialista versionado; não representa probabilidade de culpa."""

    def __init__(self, version: str = "1.0.0", weights: RiskWeights | None = None) -> None:
        self.version = version
        self.weights = weights or RiskWeights()

    def score(self, findings: list[Finding]) -> RiskExplanation:
        if not findings:
            raise ValueError("não é possível priorizar sem findings")
        components = {
            "strength": max(item.strength for item in findings),
            "materiality": max(item.materiality for item in findings),
            "urgency": max(item.urgency for item in findings),
            "connectivity": max(
                float(item.feature_values.get("graph_connectivity") or 0) for item in findings
            ),
            "history": 0.0,
        }
        scenarios = {item.scenario for item in findings}
        interactions: list[str] = []
        interaction_value = 0.0
        if len(scenarios) > 1:
            interactions.append("MULTI_SCENARIO_CORROBORATION")
            interaction_value += self.weights.multi_scenario
        if any("TEMPORAL_GRAPH_RELATION_RELEVANT" in item.reason_codes for item in findings):
            interactions.append("FINDING_PLUS_TEMPORAL_RELATION")
            interaction_value += self.weights.graph_relation
        if {"CONCENTRATION", "MANIPULATION_BEHAVIOR"}.issubset(scenarios):
            interactions.append("CONCENTRATION_PLUS_PRICE_BEHAVIOR")
            interaction_value += self.weights.concentration_price

        z_value = (
            self.weights.intercept
            + self.weights.strength * components["strength"]
            + self.weights.materiality * components["materiality"]
            + self.weights.urgency * components["urgency"]
            + self.weights.connectivity * components["connectivity"]
            + self.weights.history * components["history"]
            + interaction_value
        )
        priority = round(100 / (1 + math.exp(-z_value)), 2)
        all_inconclusive = all(
            item.disposition == FindingDisposition.INCONCLUSIVE for item in findings
        )
        if all_inconclusive:
            priority = max(priority, 50.0)
            priority_class = "INCONCLUSIVE"
        elif priority >= 80:
            priority_class = "CRITICAL"
        elif priority >= 60:
            priority_class = "HIGH"
        elif priority >= 30:
            priority_class = "TRIAGE"
        else:
            priority_class = "OBSERVATION"

        explanation = [
            f"Força máxima dos achados: {components['strength']:.2f}.",
            f"Materialidade normalizada: {components['materiality']:.2f}.",
            f"Urgência máxima: {components['urgency']:.2f}.",
            f"Conectividade temporal: {components['connectivity']:.2f}.",
            "O score é prioridade operacional, não probabilidade de culpa.",
        ]
        if any(item.evidence_quality != EvidenceQuality.COMPLETE for item in findings):
            explanation.append("Há evidência ausente/degradada; isso foi sinalizado, não descontado silenciosamente.")
        return RiskExplanation(
            priority=priority,
            priority_class=priority_class,  # type: ignore[arg-type]
            components={key: round(value, 6) for key, value in components.items()},
            interactions=tuple(interactions),
            policy_version=self.version,
            explanation=tuple(explanation),
        )


class CorrelationEngine:
    version = "1.0.0"

    def __init__(self, policy: RiskPolicy | None = None) -> None:
        self.policy = policy or RiskPolicy()

    def correlate(self, findings: list[Finding], snapshot_id: str) -> list[Alert]:
        grouped: dict[str, list[Finding]] = defaultdict(list)
        for finding in findings:
            grouped[finding.subject_id].append(finding)

        alerts: list[Alert] = []
        for subject_id, subject_findings in sorted(grouped.items()):
            ordered = sorted(subject_findings, key=lambda item: item.finding_id)
            risk = self.policy.score(ordered)
            alert_id = stable_id(
                "A",
                self.version,
                subject_id,
                tuple(item.finding_id for item in ordered),
                snapshot_id,
            )
            alerts.append(
                Alert(
                    alert_id=alert_id,
                    subject_id=subject_id,
                    finding_ids=tuple(item.finding_id for item in ordered),
                    scenarios=tuple(sorted({item.scenario for item in ordered})),
                    risk=risk,
                )
            )
        return alerts
