"""Memory 2.0 CLI regression tests."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from rosclaw.memory.seekdb_client import SQLiteKnowledgeStore
from rosclaw.memory.v2.cli import (
    _close,
    _open_stack,
    cmd_memory_v2_benchmark,
    cmd_memory_v2_explain,
)
from rosclaw.memory.v2.index import EmbeddingIndexManager
from rosclaw.memory.v2.models import MemoryItem
from rosclaw.memory.v2.repository import MemoryRepository
from rosclaw.memory.v2.retrieval import MemoryQuery, MemoryRetriever
from rosclaw.storage.vector import SQLiteVectorStore, TfidfEmbedder


def test_benchmark_command_resolves_source_harness(monkeypatch) -> None:
    called: list[list[str]] = []

    def fake_call(command: list[str]) -> int:
        called.append(command)
        return 0

    monkeypatch.setattr(subprocess, "call", fake_call)
    assert cmd_memory_v2_benchmark(argparse.Namespace()) == 0
    assert called
    assert Path(called[0][1]).is_file()
    assert called[0][1].endswith("benchmarks/memory/run_benchmark.py")


def test_explain_v2_requires_memory_id(capsys) -> None:
    args = argparse.Namespace(memory_id=None)
    assert cmd_memory_v2_explain(args) == 2
    assert "--memory-id" in capsys.readouterr().err


def test_cli_reopens_index_with_identical_tfidf_revision(tmp_path: Path) -> None:
    path = tmp_path / "memory.sqlite"
    client = SQLiteKnowledgeStore(str(path))
    client.connect()
    repo = MemoryRepository(client)
    item = MemoryItem(
        memory_type="episodic",
        robot_id="r1",
        title="calibration note",
        document="completed successfully",
        tags=["rare_tag_token"],
        evidence_refs=["evt_1"],
    )
    repo.store(item)
    manager = EmbeddingIndexManager(client, SQLiteVectorStore(client))
    manager.build(repo.query(limit=100), TfidfEmbedder())
    client.disconnect()

    reopened, reopened_repo, vector, embedder = _open_stack(
        argparse.Namespace(v2_path=str(path)),
        with_vector=True,
    )
    try:
        assert vector is not None
        EmbeddingIndexManager(reopened, vector).check_query_embedder(embedder)
        results = MemoryRetriever(
            reopened_repo,
            vector_store=vector,
            embedder=embedder,
        ).retrieve(MemoryQuery(text="rare_tag_token"))
        assert results and results[0].memory_id == item.memory_id
        assert results[0].vector_score is not None
    finally:
        _close(reopened)
