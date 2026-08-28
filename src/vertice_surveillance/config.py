"""Política versionada e carregável para replay e gestão de mudanças."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field


class PolicyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConcentrationPolicy(PolicyModel):
    share_threshold: float = Field(default=0.35, gt=0, le=1)
    recurring_days_threshold: int = Field(default=3, ge=2)
    symmetry_threshold: float = Field(default=0.75, ge=0, le=1)


class ManipulationPolicy(PolicyModel):
    robust_deviation_threshold: float = Field(default=2.0, gt=0)


class ChurningPolicy(PolicyModel):
    turnover_threshold: float = Field(default=2.0, gt=0)
    cost_equity_threshold: float = Field(default=0.02, gt=0)


class OtcPolicy(PolicyModel):
    ipv_z_threshold: float = Field(default=2.0, gt=0)


class RiskWeights(PolicyModel):
    intercept: float = -2.0
    strength: float = 1.8
    materiality: float = 1.0
    urgency: float = 1.2
    connectivity: float = 1.2
    history: float = 0.5
    multi_scenario: float = 0.35
    graph_relation: float = 0.25
    concentration_price: float = 0.30


class PolicyConfig(PolicyModel):
    policy_version: str = "1.0.0"
    concentration: ConcentrationPolicy = ConcentrationPolicy()
    manipulation: ManipulationPolicy = ManipulationPolicy()
    churning: ChurningPolicy = ChurningPolicy()
    otc: OtcPolicy = OtcPolicy()
    risk: RiskWeights = RiskWeights()


def load_policy(path: Path | str) -> PolicyConfig:
    raw = cast(dict[str, Any], json.loads(Path(path).read_text(encoding="utf-8")))
    return PolicyConfig.model_validate(raw)

