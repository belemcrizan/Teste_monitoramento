"""Adaptadores AWS opcionais.

Os clientes são injetáveis, permitindo testes sem credenciais. `boto3` só é
importado pelas factories e não contamina o núcleo local-first.
"""

from __future__ import annotations

import json
from typing import Any, cast

from ..ids import stable_id


class S3ObjectStore:
    def __init__(self, client: Any, bucket: str, prefix: str = "vertice") -> None:
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def _key(self, key: str) -> str:
        clean = key.strip("/")
        return f"{self.prefix}/{clean}" if self.prefix else clean

    def put_json(self, key: str, value: dict[str, Any] | list[Any]) -> str:
        object_key = self._key(key if key.endswith(".json") else f"{key}.json")
        body = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=body,
            ContentType="application/json",
            ServerSideEncryption="aws:kms",
        )
        return f"s3://{self.bucket}/{object_key}"

    def get_json(self, ref: str) -> dict[str, Any] | list[Any]:
        prefix = f"s3://{self.bucket}/"
        if not ref.startswith(prefix):
            raise ValueError("referência não pertence ao bucket configurado")
        response = self.client.get_object(Bucket=self.bucket, Key=ref.removeprefix(prefix))
        return cast(dict[str, Any] | list[Any], json.loads(response["Body"].read()))


class SqsEventPublisher:
    def __init__(self, client: Any, queue_url: str) -> None:
        self.client = client
        self.queue_url = queue_url

    def publish(self, event_type: str, payload: dict[str, Any]) -> str:
        event_id = stable_id("EVT", event_type, payload)
        envelope = {"event_id": event_id, "event_type": event_type, "payload": payload}
        self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(envelope, sort_keys=True, default=str),
        )
        return event_id


class BedrockInvestigativeAssistant:
    def __init__(self, client: Any, model_id: str) -> None:
        self.client = client
        self.model_id = model_id

    def summarize(self, dossier: dict[str, Any]) -> dict[str, Any]:
        prompt = {
            "instruction": (
                "Resuma somente os fatos do dossiê. Não conclua culpa ou intenção. "
                "Cada afirmação factual deve citar um source_ref existente. Responda em JSON."
            ),
            "required_keys": [
                "executive_summary",
                "factual_timeline",
                "triggered_scenarios",
                "supporting_evidence",
                "counter_evidence",
                "unknowns",
                "suggested_next_steps",
                "source_refs",
                "limitations",
            ],
            "dossier": dossier,
        }
        response = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": json.dumps(prompt, default=str)}]}],
            inferenceConfig={"temperature": 0, "maxTokens": 2000},
        )
        text = response["output"]["message"]["content"][0]["text"]
        result = cast(dict[str, Any], json.loads(text))
        allowed_refs = {
            ref
            for finding in dossier.get("findings", [])
            for ref in finding.get("evidence_refs", [])
        }
        returned_refs = set(result.get("source_refs", []))
        if not returned_refs.issubset(allowed_refs):
            raise ValueError("a resposta do modelo contém citações não presentes no dossiê")
        return result


def boto3_client(service: str, region: str) -> Any:
    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError as error:  # pragma: no cover - depende do extra aws
        raise RuntimeError("instale o extra AWS: pip install 'vertice-surveillance[aws]'") from error
    return boto3.client(service, region_name=region)
