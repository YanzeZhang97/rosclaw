"""Schema migration runner for SQLite and MySQL-compatible backends.

Migrations live as plain ``.sql`` files in ``src/rosclaw/storage/migrations``.
Each file may start with a backend marker comment such as ``-- backend: sqlite``
or ``-- backend: all`` (default).  The runner records applied versions in a
``schema_migrations`` table and skips already-applied migrations.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("rosclaw.storage.migrations")


def _split_statements(sql: str) -> list[str]:
    """Split a SQL script into individual statements.

    This is intentionally simple: it splits on semicolons and ignores empty
    statements and line comments.  For complex migrations, keep one statement
    per line or use explicit delimiters.
    """
    statements = []
    for raw in sql.split(";"):
        cleaned = re.sub(r"--.*", "", raw)
        cleaned = cleaned.strip()
        if cleaned:
            statements.append(cleaned)
    return statements


def _read_backend(path: Path) -> str:
    """Return the backend target from the first comment line, defaulting to all."""
    text = path.read_text(encoding="utf-8")
    first_line = text.splitlines()[0] if text else ""
    match = re.match(r"^--\s*backend:\s*(\w+)", first_line)
    return match.group(1).lower() if match else "all"


class MigrationRunner:
    """Apply versioned SQL migrations and track them in ``schema_migrations``."""

    def __init__(self, migrations_dir: Path | str | None = None) -> None:
        self._migrations_dir = (
            Path(migrations_dir) if migrations_dir else Path(__file__).parent / "migrations"
        )

    def apply(self, connection: Any, backend: str) -> list[str]:
        """Apply all pending migrations for *backend*.

        :param connection: ``sqlite3.Connection`` or a PyMySQL connection.
        :param backend: ``sqlite`` or ``mysql``.
        :return: list of applied migration version strings.
        """
        self._ensure_table(connection, backend)
        applied = self._applied_versions(connection, backend)
        applied_versions = {row["version"] for row in applied}

        new: list[str] = []
        for path in sorted(self._migrations_dir.glob("*.sql")):
            version = self._version_from_filename(path)
            if version in applied_versions:
                continue
            target = _read_backend(path)
            if target != "all" and target != backend:
                continue
            logger.info("Applying migration %s for backend %s", path.name, backend)
            self._execute_script(connection, path.read_text(encoding="utf-8"), backend)
            self._record(connection, version, backend)
            new.append(version)

        if isinstance(connection, sqlite3.Connection):
            connection.commit()
        return new

    @staticmethod
    def _version_from_filename(path: Path) -> str:
        """Migration versions are the leading numeric token of the filename."""
        match = re.match(r"(\d+)", path.name)
        if not match:
            raise ValueError(f"Migration filename must start with a version number: {path.name}")
        return match.group(1)

    @staticmethod
    def _ensure_table(connection: Any, backend: str) -> None:
        if backend == "sqlite":
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at REAL NOT NULL
                )
                """
            )
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(64) PRIMARY KEY,
                        applied_at DOUBLE NOT NULL
                    ) DEFAULT CHARACTER SET utf8mb4
                    """
                )

    @staticmethod
    def _applied_versions(connection: Any, backend: str) -> list[dict[str, Any]]:
        if backend == "sqlite":
            cursor = connection.execute("SELECT version, applied_at FROM schema_migrations")
            return [{"version": row[0], "applied_at": row[1]} for row in cursor.fetchall()]
        with connection.cursor() as cursor:
            cursor.execute("SELECT version, applied_at FROM schema_migrations")
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def _record(connection: Any, version: str, backend: str) -> None:
        if backend == "sqlite":
            connection.execute(
                "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, time.time()),
            )
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    "REPLACE INTO schema_migrations (version, applied_at) VALUES (%s, %s)",
                    (version, time.time()),
                )

    @staticmethod
    def _execute_script(connection: Any, sql: str, backend: str) -> None:
        statements = _split_statements(sql)
        if backend == "sqlite":
            for statement in statements:
                connection.execute(statement)
        else:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
