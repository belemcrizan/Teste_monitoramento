from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from vertice_surveillance.adapters.local import LocalJsonObjectStore
from vertice_surveillance.api import create_app
from vertice_surveillance.pipeline import SurveillancePipeline


def _client(tmp_path: Path) -> TestClient:
    pipeline = SurveillancePipeline(object_store=LocalJsonObjectStore(tmp_path))
    return TestClient(create_app(pipeline))


def test_health_and_demo(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/health").json()["status"] == "ok"
    response = client.post("/v1/demo/run")
    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["scenario_coverage"] == 4
    assert client.get("/v1/runs/latest").status_code == 200


def test_case_and_audit_endpoints(tmp_path: Path) -> None:
    client = _client(tmp_path)
    run = client.post("/v1/demo/run").json()
    case_id = next(item["case_id"] for item in run["cases"] if item["state"] == "OPEN")
    case = client.get(f"/v1/cases/{case_id}")
    assert case.status_code == 200
    transition = client.post(
        f"/v1/cases/{case_id}/transition",
        json={
            "target": "INVESTIGATING",
            "actor": "analyst-1",
            "actor_role": "ANALYST",
            "reason": "Triagem iniciada",
        },
    )
    assert transition.status_code == 200
    assert transition.json()["state"] == "INVESTIGATING"
    assert len(client.get(f"/v1/cases/{case_id}/audit").json()) == 2


def test_demo_page_is_human_friendly(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/demo")
    assert response.status_code == 200
    assert "VÉRTICE" in response.text
    assert "Executar golden cases" in response.text

