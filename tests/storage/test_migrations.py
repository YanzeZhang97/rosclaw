"""Tests for rosclaw.storage.migrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from rosclaw.storage.migrations import MigrationRunner


def test_migration_applies_sqlite(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_create_test_table_sqlite.sql").write_text(
        "-- backend: sqlite\nCREATE TABLE IF NOT EXISTS test_table (id TEXT PRIMARY KEY);",
        encoding="utf-8",
    )
    (migrations_dir / "002_create_test_table_mysql.sql").write_text(
        "-- backend: mysql\nCREATE TABLE IF NOT EXISTS test_table (id VARCHAR(64) PRIMARY KEY);",
        encoding="utf-8",
    )

    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))
    runner = MigrationRunner(migrations_dir)
    applied = runner.apply(conn, "sqlite")
    assert "001" in applied
    assert "002" not in applied

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "test_table" in tables
    assert "schema_migrations" in tables

    # Idempotent: second apply returns nothing new.
    applied2 = runner.apply(conn, "sqlite")
    assert applied2 == []


def test_migration_tracks_versions(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_first.sql").write_text("-- backend: all\nSELECT 1;", encoding="utf-8")
    (migrations_dir / "002_second.sql").write_text("-- backend: all\nSELECT 1;", encoding="utf-8")

    conn = sqlite3.connect(":memory:")
    runner = MigrationRunner(migrations_dir)
    assert runner.apply(conn, "sqlite") == ["001", "002"]
    assert runner.apply(conn, "sqlite") == []


def test_migration_bad_filename(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "bad_name.sql").write_text("SELECT 1;", encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    with pytest.raises(ValueError, match="version number"):
        MigrationRunner(migrations_dir).apply(conn, "sqlite")
