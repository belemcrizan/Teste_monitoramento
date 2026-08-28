from __future__ import annotations

from pathlib import Path

import pytest

from vertice_surveillance.adapters.local import LocalJsonObjectStore
from vertice_surveillance.bootstrap import build_pipeline
from vertice_surveillance.settings import Settings


def test_local_bootstrap_uses_local_adapters(tmp_path: Path) -> None:
    pipeline = build_pipeline(Settings(artifact_dir=tmp_path))
    assert isinstance(pipeline.object_store, LocalJsonObjectStore)


def test_unknown_case_repository_fails_explicitly(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Aurora"):
        build_pipeline(Settings(artifact_dir=tmp_path, case_repository="aurora"))

