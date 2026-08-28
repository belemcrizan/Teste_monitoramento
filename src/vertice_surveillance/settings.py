"""Configuração explícita por ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "local"
    artifact_dir: Path = Path("artifacts")
    object_store: str = "local"
    event_bus: str = "memory"
    case_repository: str = "memory"
    aws_region: str = "us-east-1"
    s3_bucket: str | None = None
    s3_prefix: str = "vertice"
    sqs_queue_url: str | None = None
    bedrock_model_id: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            environment=os.getenv("VERTICE_ENV", "local"),
            artifact_dir=Path(os.getenv("VERTICE_ARTIFACT_DIR", "artifacts")),
            object_store=os.getenv("VERTICE_OBJECT_STORE", "local"),
            event_bus=os.getenv("VERTICE_EVENT_BUS", "memory"),
            case_repository=os.getenv("VERTICE_CASE_REPOSITORY", "memory"),
            aws_region=os.getenv("VERTICE_AWS_REGION", "us-east-1"),
            s3_bucket=os.getenv("VERTICE_S3_BUCKET") or None,
            s3_prefix=os.getenv("VERTICE_S3_PREFIX", "vertice"),
            sqs_queue_url=os.getenv("VERTICE_SQS_QUEUE_URL") or None,
            bedrock_model_id=os.getenv("VERTICE_BEDROCK_MODEL_ID") or None,
        )

