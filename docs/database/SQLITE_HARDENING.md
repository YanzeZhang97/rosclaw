# SQLite Hardening Guide (Phase 0)

> Applies to: `SQLiteKnowledgeStore` (legacy `SeekDBSQLiteClient`) and `PracticeCatalog` SQLite backend.

## Problem Statement

The current SQLite usage in `rosclaw` is configured with default `sqlite3` settings. Under multi-threaded loads (RuntimeBus + MemoryInterface preloader + PracticeRecorder), this causes:

- `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`
- `OperationalError: database is locked`
- Excessive fsync due to per-event commits.

## Phase 0 Hardening

### 1. Connection Flags

```python
self._conn = sqlite3.connect(
    self._db_path,
    check_same_thread=False,  # Allow the RLock-protected connection to move across threads.
)
```

### 2. PRAGMAs at Connection Init

```sql
PRAGMA journal_mode=WAL;          -- Readers do not block writers; writers do not block readers.
PRAGMA synchronous=NORMAL;        -- Balanced durability vs. throughput.
PRAGMA foreign_keys=ON;           -- Enforce referential integrity.
PRAGMA busy_timeout=5000;         -- Wait up to 5s before returning "database is locked".
PRAGMA temp_store=MEMORY;         -- Keep temp tables in memory for speed.
```

Notes:
- `WAL` is set once and persists per database file.
- `busy_timeout` is per-connection; set it on every new connection.
- `synchronous=NORMAL` is sufficient with WAL; `FULL` is safer but slower.

### 3. Thread Safety

All connection access is wrapped with `threading.RLock`:

```python
with self._lock:
    cur = self._conn.cursor()
    cur.execute(...)
    self._conn.commit()
```

This is not a substitute for `check_same_thread=False`; both are required.

### 4. Upsert Strategy

Replace the broad `except Exception: REPLACE INTO` pattern with explicit upsert:

```sql
INSERT INTO table_name (id, col1, col2, ...)
VALUES (?, ?, ?, ...)
ON CONFLICT(id) DO UPDATE SET
    col1=excluded.col1,
    col2=excluded.col2,
    ...
```

This preserves row identity and foreign-key relationships and does not silently swallow real errors.

### 5. Catalog Batching

`PracticeCatalog` will batch inserts:

- Queue size: bounded (default 2000 events).
- Flush trigger: 500 events **or** 300 ms idle.
- `close()` / `__del__` forces final flush.
- On queue full: drop oldest and log error (crash-safe over throughput).

This reduces WAL checkpoints from per-event (711k+ times) to ~1.4k transactions for the same data.

### 6. Migration Safety

`_migrate_missing_columns()` will:

- Add missing columns with safe defaults.
- For `NOT NULL` columns without defaults, add as `NULL` first, backfill, then apply `NOT NULL`.

## Validation Checklist

- [ ] `SQLiteKnowledgeStore` passes 8-writer / 8-reader / 1-preloader stress test (60s).
- [ ] `PracticeCatalog` batch writer does not lose events on `close()`.
- [ ] `events.jsonl` line count equals `catalog.events` count equals `manifest.event_count`.
- [ ] `ruff check src/rosclaw tests` passes.
- [ ] `pytest tests/test_seekdb.py tests/test_seekdb_indexes.py tests/test_sqlite_store_concurrency.py tests/practice/test_catalog_batch_writer.py -q` passes.

## References

- SQLite WAL mode: https://sqlite.org/wal.html
- SQLite PRAGMAs: https://sqlite.org/pragma.html
- `docs/database/DATABASE_INVENTORY.md`
- `docs/database/FINAL_DATABASE_AUDIT_REPORT.md` (post-validation)
