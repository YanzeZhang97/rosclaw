# ROSClaw Database Audit — Final Report (Phase 0)

> Status: **DRAFT / IN PROGRESS**
> This report will be finalized after all Phase 0 commits are validated against the RH56 7×24 stress test.

## 1. Audit Scope

- Internal knowledge storage (`rosclaw.memory`)
- Practice data flywheel catalog and ingestor (`rosclaw.practice`)
- SeekDB HTTP bridge (`rosclaw.practice.seekdb_bridge`)
- Running validation target: RH56 7×24 self-RPS stress test

## 2. Problems Confirmed

See `DATABASE_INVENTORY.md` for the full risk map. The P0 problems verified by code audit and real data:

| # | Problem | Evidence | Severity |
|---|---|---|---|
| 1 | `SeekDBSQLiteClient` not thread-safe | Code inspection: no `check_same_thread=False`, no RLock | High |
| 2 | SQLite PRAGMAs missing | No WAL, busy_timeout, synchronous config | High |
| 3 | `insert()` swallows errors with `REPLACE INTO` | `seekdb_client.py` broad exception handler | High |
| 4 | `SeekDBMySQLClient` single connection, no lock | `pymysql` connection reused across threads | High |
| 5 | `PracticeCatalog` per-event commit | 711k+ events in 7×24 catalog | High |
| 6 | `timeline.jsonl` duplicates `events.jsonl` | `layout.py` copies stream | Medium |
| 7 | `event_count` under-counts | Latest session log shows `event_count` mismatch | Medium |
| 8 | `practice_event_index` empty | Catalog query returns 0 rows | Low |
| 9 | `ROSCLAW_SEEKDB_URL` HTTP/SQL conflict | `seekdb_bridge.py` vs `_practice_seekdb_client()` | High |
| 10 | Runtime default `seekdb_backend="memory"` | `core/runtime.py` | Medium |

## 3. Phase 0 Commits

| Commit | Title | Status |
|---|---|---|
| 1 | `docs(db): add Phase 0 audit and architecture baseline` | In Progress |
| 2 | `refactor(storage): rename SeekDB SQLite/Memory clients with deprecated aliases` | Pending |
| 3 | `fix(sqlite): harden SQLiteKnowledgeStore concurrency, PRAGMAs, and upsert` | Pending |
| 4 | `fix(practice): batch catalog writes, remove timeline duplication, fix event_count` | Pending |
| 5 | `fix(runtime): unify storage backend selection and deprecate conflicting seekdb_url usage` | Pending |
| 6 | `test(db): add SQLite concurrency and catalog batch tests` | Pending |

## 4. Validation Results

TBD. Will include:

- Static analysis (`ruff`, `mypy`) output.
- Unit / integration test results.
- SQLite concurrency stress test results.
- Mock stress session metrics.
- 7×24 runner observation (manager log, catalog WAL growth, event_count consistency, timeline.jsonl absence).

## 5. Remaining Work (Phase 1+)

- True `StorageFactory` abstraction unifying memory/sqlite/mysql/http backends.
- Outbox + async sync worker for SeekDB Server / OceanBase.
- Vector / hybrid retrieval for KNOW/HOW evidence.
- `rosclaw db doctor` migration and health command.
- Migration tooling for old `seekdb.sqlite` files.

## 6. References

- `DATABASE_INVENTORY.md`
- `M0_LINEAGE_AUDIT.md`
- `SQLITE_HARDENING.md`
- `~/workspace/rosclaw/rosclaw_test/数据库优化v1.md`
