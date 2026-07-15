"""Tests for rosclaw.storage.outbox."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rosclaw.storage.outbox import OutboxRecord, OutboxStore, OutboxWorker


@pytest.fixture
def outbox(tmp_path: Path) -> OutboxStore:
    store = OutboxStore(db_path=str(tmp_path / "outbox.sqlite"))
    store.connect()
    return store


def test_enqueue_and_pending(outbox: OutboxStore) -> None:
    rid = outbox.enqueue("seekdb_http", {"event": "test"})
    pending = outbox.pending(limit=10)
    assert len(pending) == 1
    assert pending[0].id == rid
    assert pending[0].payload == {"event": "test"}


def test_mark_delivered(outbox: OutboxStore) -> None:
    rid = outbox.enqueue("seekdb_http", {"event": "test"})
    outbox.mark_delivered(rid)
    assert outbox.pending(limit=10) == []
    assert outbox.stats()["total"] == 0


def test_mark_failed_backoff(outbox: OutboxStore) -> None:
    rid = outbox.enqueue("seekdb_http", {"event": "test"})
    outbox.mark_failed(rid, "timeout")
    # Immediately after failure, next_retry_at is in the future.
    assert outbox.pending(limit=10) == []
    rows = outbox.records()
    assert len(rows) == 1
    assert rows[0].retry_count == 1
    assert rows[0].next_retry_at is not None
    assert rows[0].next_retry_at > time.time()
    assert rows[0].error_log == "timeout"


def test_capacity_drops_oldest(outbox: OutboxStore) -> None:
    outbox._max_records = 2
    first = outbox.enqueue("seekdb_http", {"seq": 1})
    time.sleep(0.01)
    second = outbox.enqueue("seekdb_http", {"seq": 2})
    time.sleep(0.01)
    third = outbox.enqueue("seekdb_http", {"seq": 3})
    stats = outbox.stats()
    assert stats["total"] == 2
    ids = {r.id for r in outbox.pending(limit=10)}
    assert first not in ids
    assert second in ids
    assert third in ids


def test_worker_drains_successfully(outbox: OutboxStore) -> None:
    committer = MagicMock()
    worker = OutboxWorker(outbox, committer, interval_sec=0.05, batch_size=10)
    outbox.enqueue("seekdb_http", {"event": "a"})
    outbox.enqueue("seekdb_http", {"event": "b"})
    worker.start()
    # Wait for worker to drain.
    for _ in range(100):
        if outbox.stats()["total"] == 0:
            break
        time.sleep(0.01)
    worker.stop()
    assert outbox.stats()["total"] == 0
    assert committer.save_to_seekdb.call_count == 2


def test_worker_retries_failed_commits(outbox: OutboxStore) -> None:
    committer = MagicMock()
    committer.save_to_seekdb.side_effect = RuntimeError("upstream down")
    worker = OutboxWorker(
        outbox, committer, interval_sec=0.05, batch_size=10, max_retries=2
    )
    outbox.enqueue("seekdb_http", {"event": "a"})
    worker.start()
    # Wait for the worker to exhaust retries.
    for _ in range(300):
        if committer.save_to_seekdb.call_count >= 2:
            break
        time.sleep(0.01)
    worker.stop()
    assert outbox.stats()["total"] == 1
    assert committer.save_to_seekdb.call_count >= 2
    rows = outbox.records()
    assert rows[0].retry_count >= 2
    assert "upstream down" in rows[0].error_log


def test_worker_stops_gracefully(outbox: OutboxStore) -> None:
    committer = MagicMock()
    worker = OutboxWorker(outbox, committer, interval_sec=60.0)
    worker.start()
    assert worker._thread is not None and worker._thread.is_alive()
    worker.stop(timeout=1.0)
    assert worker._thread is None or not worker._thread.is_alive()


def test_outbox_record_to_dict() -> None:
    record = OutboxRecord(
        id="r1",
        target="seekdb_http",
        payload={"x": 1},
        created_at=1.0,
        retry_count=0,
        next_retry_at=None,
        error_log=None,
    )
    d = record.to_dict()
    assert d["id"] == "r1"
    assert json.loads(d["payload_json"]) == {"x": 1}


import json  # noqa: E402
