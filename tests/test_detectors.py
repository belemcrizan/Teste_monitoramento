from __future__ import annotations

from vertice_surveillance.detectors import (
    ChurningDetector,
    ConcentrationDetector,
    ManipulationBehaviorDetector,
    OtcComplexDetector,
)
from vertice_surveillance.models import FindingDisposition
from vertice_surveillance.quality import validate_dataset
from vertice_surveillance.sample_data import build_demo_dataset


def _context():  # type: ignore[no-untyped-def]
    dataset = build_demo_dataset()
    return dataset, validate_dataset(dataset)


def test_concentration_uses_observed_universe_and_reason_codes() -> None:
    dataset, quality = _context()
    finding = ConcentrationDetector().detect(dataset, quality)[0]
    assert finding.subject_id == "CLIENT-A"
    assert finding.feature_values["pair_observed_volume_share"] > 0.5
    assert "PAIR_OBSERVED_VOLUME_SHARE_HIGH" in finding.reason_codes
    assert any("não market share" in item for item in finding.limitations)


def test_manipulation_is_composite_and_does_not_claim_spoofing() -> None:
    dataset, quality = _context()
    findings = ManipulationBehaviorDetector().detect(dataset, quality)
    finding = next(item for item in findings if item.subject_id == "CLIENT-A")
    assert finding.disposition == FindingDisposition.ACTIONABLE
    assert "ROBUST_PRICE_DEVIATION_HIGH" in finding.reason_codes
    assert any("spoofing" in item for item in finding.limitations)
    assert not any(item.subject_id == "CLIENT-B" for item in findings)


def test_churning_keeps_unknown_control_as_degraded_evidence() -> None:
    dataset, quality = _context()
    finding = next(
        item for item in ChurningDetector().detect(dataset, quality) if item.subject_id == "CLIENT-C"
    )
    assert finding.feature_values["turnover_gross"] >= 2
    assert finding.feature_values["cost_to_equity"] >= 0.02
    assert "CLIENT_CONTROL_UNKNOWN" in finding.reason_codes
    assert "decision_control_source" in finding.missing_data


def test_otc_has_actionable_and_inconclusive_paths() -> None:
    dataset, quality = _context()
    findings = OtcComplexDetector().detect(dataset, quality)
    by_client = {item.subject_id: item for item in findings}
    assert by_client["CLIENT-D"].disposition == FindingDisposition.ACTIONABLE
    assert "IPV_NORMALIZED_DEVIATION_HIGH" in by_client["CLIENT-D"].reason_codes
    assert by_client["CLIENT-E"].disposition == FindingDisposition.INCONCLUSIVE
    assert "independent_value" in by_client["CLIENT-E"].missing_data
