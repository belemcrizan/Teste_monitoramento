from __future__ import annotations

from pathlib import Path

from vertice_surveillance.config import load_policy


def test_example_policy_is_valid_and_versioned() -> None:
    policy = load_policy(Path("configs/policy.example.json"))
    assert policy.policy_version == "1.0.0"
    assert policy.concentration.share_threshold == 0.35
    assert policy.risk.strength == 1.8
    assert policy.fixed_income_conduct.price_deviation_bps_threshold == 75
    assert policy.observed_participation.minimum_coverage_ratio == 0.8
