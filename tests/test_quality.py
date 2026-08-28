from __future__ import annotations

from vertice_surveillance.models import LoadManifest
from vertice_surveillance.quality import validate_dataset
from vertice_surveillance.sample_data import build_demo_dataset


def test_demo_reconciles_and_preserves_high_quality_warnings() -> None:
    report = validate_dataset(build_demo_dataset())
    assert report.passed is True
    assert report.record_count == 15
    assert "OTC_VALUATION_PARTIAL" in {item.code for item in report.issues}


def test_duplicate_trade_blocks_all_scenarios() -> None:
    dataset = build_demo_dataset()
    broken = dataset.model_copy(
        update={"trades": dataset.trades + (dataset.trades[0],), "manifest": None}
    )
    report = validate_dataset(broken)
    assert report.passed is False
    assert set(report.blocked_scenarios) == {
        "CONCENTRATION",
        "MANIPULATION_BEHAVIOR",
        "CHURNING",
        "OTC_COMPLEX",
    }


def test_manifest_count_mismatch_fails_closed() -> None:
    dataset = build_demo_dataset()
    assert dataset.manifest is not None
    bad_manifest: LoadManifest = dataset.manifest.model_copy(
        update={"expected_record_count": dataset.manifest.expected_record_count + 1}
    )
    report = validate_dataset(dataset.model_copy(update={"manifest": bad_manifest}))
    assert report.passed is False
    assert "MANIFEST_COUNT_MISMATCH" in {item.code for item in report.issues}

