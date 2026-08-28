from __future__ import annotations

import json
from io import BytesIO
from typing import Any

from vertice_surveillance.adapters.aws import (
    BedrockInvestigativeAssistant,
    S3ObjectStore,
    SqsEventPublisher,
)


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, **kwargs: Any) -> None:
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        return {"Body": BytesIO(self.objects[(kwargs["Bucket"], kwargs["Key"])])}


class FakeSqs:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def send_message(self, **kwargs: Any) -> None:
        self.messages.append(kwargs)


class FakeBedrock:
    def converse(self, **_: Any) -> dict[str, Any]:
        result = {
            "executive_summary": "Resumo com fonte.",
            "factual_timeline": [],
            "triggered_scenarios": [],
            "supporting_evidence": [],
            "counter_evidence": [],
            "unknowns": [],
            "suggested_next_steps": [],
            "source_refs": ["record://trade/T-1"],
            "limitations": [],
        }
        return {"output": {"message": {"content": [{"text": json.dumps(result)}]}}}


def test_s3_adapter_roundtrip() -> None:
    fake = FakeS3()
    store = S3ObjectStore(fake, "bucket", "prefix")
    ref = store.put_json("run/evidence", {"ok": True})
    assert ref == "s3://bucket/prefix/run/evidence.json"
    assert store.get_json(ref) == {"ok": True}


def test_sqs_adapter_emits_stable_envelope() -> None:
    fake = FakeSqs()
    publisher = SqsEventPublisher(fake, "queue-url")
    first = publisher.publish("CaseCreated", {"case_id": "C-1"})
    second = publisher.publish("CaseCreated", {"case_id": "C-1"})
    assert first == second
    assert len(fake.messages) == 2
    assert json.loads(fake.messages[0]["MessageBody"])["event_type"] == "CaseCreated"


def test_bedrock_adapter_validates_citations() -> None:
    assistant = BedrockInvestigativeAssistant(FakeBedrock(), "model")
    dossier = {"findings": [{"evidence_refs": ["record://trade/T-1"]}]}
    result = assistant.summarize(dossier)
    assert result["source_refs"] == ["record://trade/T-1"]

