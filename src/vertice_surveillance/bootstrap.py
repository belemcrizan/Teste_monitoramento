"""Composição de adaptadores por ambiente, sem alterar o núcleo."""

from __future__ import annotations

from .adapters.aws import (
    BedrockInvestigativeAssistant,
    S3ObjectStore,
    SqsEventPublisher,
    boto3_client,
)
from .adapters.local import (
    DeterministicAssistant,
    LocalJsonObjectStore,
    MemoryCaseRepository,
    MemoryEventPublisher,
)
from .api import create_app
from .cases import CaseManager
from .pipeline import SurveillancePipeline
from .ports import EventPublisher, InvestigativeAssistant, ObjectStore
from .settings import Settings


def build_pipeline(settings: Settings) -> SurveillancePipeline:
    object_store: ObjectStore
    if settings.object_store == "local":
        object_store = LocalJsonObjectStore(settings.artifact_dir)
    elif settings.object_store == "s3":
        if not settings.s3_bucket:
            raise ValueError("VERTICE_S3_BUCKET é obrigatório para object_store=s3")
        object_store = S3ObjectStore(
            boto3_client("s3", settings.aws_region),
            settings.s3_bucket,
            settings.s3_prefix,
        )
    else:
        raise ValueError(f"object store não suportado: {settings.object_store}")

    publisher: EventPublisher
    if settings.event_bus == "memory":
        publisher = MemoryEventPublisher()
    elif settings.event_bus == "sqs":
        if not settings.sqs_queue_url:
            raise ValueError("VERTICE_SQS_QUEUE_URL é obrigatório para event_bus=sqs")
        publisher = SqsEventPublisher(
            boto3_client("sqs", settings.aws_region), settings.sqs_queue_url
        )
    else:
        raise ValueError(f"event bus não suportado: {settings.event_bus}")

    assistant: InvestigativeAssistant
    if settings.bedrock_model_id:
        assistant = BedrockInvestigativeAssistant(
            boto3_client("bedrock-runtime", settings.aws_region),
            settings.bedrock_model_id,
        )
    else:
        assistant = DeterministicAssistant()

    if settings.case_repository != "memory":
        raise RuntimeError(
            "O adaptador transacional Aurora deve ser integrado ao schema corporativo antes "
            "de habilitar VERTICE_CASE_REPOSITORY diferente de memory."
        )
    case_manager = CaseManager(MemoryCaseRepository(), publisher)
    return SurveillancePipeline(
        object_store=object_store,
        event_publisher=publisher,
        assistant=assistant,
        case_manager=case_manager,
    )


app = create_app(build_pipeline(Settings.from_env()))

