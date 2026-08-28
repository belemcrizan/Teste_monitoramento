from __future__ import annotations

from pathlib import Path
from typing import Any

from vertice_surveillance.adapters.local import LocalJsonObjectStore
from vertice_surveillance.pipeline import SurveillancePipeline
from vertice_surveillance.sample_data import build_benign_dataset, build_demo_dataset


class FailingAssistant:
    def summarize(self, dossier: dict[str, Any]) -> dict[str, Any]:
        raise TimeoutError("modelo indisponível")


def test_pipeline_exercises_complete_catalog_and_persists_evidence(tmp_path: Path) -> None:
    run = SurveillancePipeline(object_store=LocalJsonObjectStore(tmp_path)).run(
        build_demo_dataset()
    )
    assert run.quality.passed is True
    assert {item.scenario for item in run.findings} == {
        "CONCENTRATION",
        "MANIPULATION_BEHAVIOR",
        "CHURNING",
        "OTC_COMPLEX",
        "FIXED_INCOME_CONDUCT",
        "FIXED_INCOME_OBSERVED_PARTICIPATION",
        "FIXED_INCOME_POST_TRADE_RESPONSE",
        "PRINCIPAL_CUSTOMER_CONDUCT",
    }
    assert run.metrics["scenario_coverage"] == 8
    assert run.metrics["scenario_catalog_size"] == 8
    assert run.metrics["fixed_income_trade_count"] == 7
    assert run.metrics["audit_chain_valid"] == 1
    assert len(run.cases) >= 4
    assert list(tmp_path.rglob("run.json"))
    assert list(tmp_path.rglob("evidence/*.json"))


def test_replay_has_stable_logical_ids(tmp_path: Path) -> None:
    dataset = build_demo_dataset()
    first = SurveillancePipeline(object_store=LocalJsonObjectStore(tmp_path / "one")).run(dataset)
    second = SurveillancePipeline(object_store=LocalJsonObjectStore(tmp_path / "two")).run(dataset)
    assert first.run_id == second.run_id
    assert [item.finding_id for item in first.findings] == [
        item.finding_id for item in second.findings
    ]
    assert [item.alert_id for item in first.alerts] == [item.alert_id for item in second.alerts]
    assert [item.case_id for item in first.cases] == [item.case_id for item in second.cases]


def test_benign_dataset_does_not_create_cases(tmp_path: Path) -> None:
    run = SurveillancePipeline(object_store=LocalJsonObjectStore(tmp_path)).run(
        build_benign_dataset()
    )
    assert run.quality.passed is True
    assert run.findings == ()
    assert run.cases == ()


def test_assistant_failure_does_not_block_cases(tmp_path: Path) -> None:
    run = SurveillancePipeline(
        object_store=LocalJsonObjectStore(tmp_path), assistant=FailingAssistant()
    ).run(build_demo_dataset())
    assert run.cases
    notes = list(tmp_path.rglob("assistant/*.json"))
    assert notes
    assert "ASSISTANT_UNAVAILABLE" in notes[0].read_text(encoding="utf-8")
