# ROSClaw Database / Storage Inventory (Phase 0)

> Scope: `rosclaw` Python package (under `src/rosclaw`) and the running RH56 7×24 stress test.
> Date: 2026-07-15
> Auditor: Claude Code (database optimization Phase 0)

## Executive Summary

The project uses **three distinct storage abstractions** that are currently conflated under the name "SeekDB":

1. **Internal `rosclaw.memory` knowledge store** — SQLite / in-memory / experimental MySQL backends for the agent's long-term memory (KNOW/HOW/Auto evidence).
2. **Internal `rosclaw.practice` catalog & SeekDB ingestor** — SQLite catalog for practice episodes, plus an ingestor that writes distilled results into the same `SeekDB*` client schema.
3. **`SeekDBBridge` HTTP adapter** — Talks to an external SeekDB-compatible HTTP endpoint (default `http://localhost:2881`). This is **not** the same as the SQL backends above.

The naming collision between (1)/(2) and (3) is a primary source of configuration conflicts and operator confusion.

---

## 1. File Inventory

### 1.1 Memory / Knowledge Plane

| File | Responsibility | Backend Used |
|---|---|---|
| `src/rosclaw/memory/seekdb_client.py` | `SEEKDB_SCHEMAS`, `InMemoryKnowledgeStore` (legacy `SeekDBMemoryClient`), `SQLiteKnowledgeStore` (legacy `SeekDBSQLiteClient`), `SeekDBMySQLClient` | memory / sqlite / mysql |
| `src/rosclaw/memory/interface.py` | `MemoryInterface`, background `_preload_worker` thread, KNOW/HOW/Auto wrappers | Defaults to `SeekDBMemoryClient` |
| `src/rosclaw/memory/__init__.py` | Public exports and backward aliases | — |

### 1.2 Practice Data Flywheel

| File | Responsibility | Notes |
|---|---|---|
| `src/rosclaw/practice/storage/catalog.py` | `PracticeCatalog` SQLite index of sessions, events, artifacts | 711k+ `events` rows in 7×24 run; `practice_event_index` empty |
| `src/rosclaw/practice/storage/layout.py` | Directory layout, `finalize_session`, `timeline.jsonl` writer | Duplicates `events.jsonl` into `timeline.jsonl` |
| `src/rosclaw/practice/recorder.py` | `PracticeRecorder`: JSONL + MCAP + catalog per event | Writes one catalog row per event |
| `src/rosclaw/practice/coordinator.py` | `PracticeCoordinator`, session lifecycle, `event_count` tracking | Under-counts events sent directly to `RuntimeBus` |
| `src/rosclaw/practice/artifact_store.py` | Artifact manifests, SHA-256, byte offsets | Referenced by `_build_v2_artifact_records` |
| `src/rosclaw/practice/writers/jsonl_writer.py` | `JsonlWriter` append + flush per event | — |
| `src/rosclaw/practice/seekdb_bridge.py` | `SeekDBBridge` HTTP client to SeekDB server | Default URL `http://localhost:2881` |
| `src/rosclaw/practice/seekdb_ingestor.py` | `SeekDBIngestor` distills practice results into SeekDB schema | Defaults to `SeekDBMemoryClient` |
| `src/rosclaw/practice/query.py` | `PracticeQuery` over SeekDB client | — |
| `src/rosclaw/practice/config.py` | `SeekDBConfig` reads `ROSCLAW_SEEKDB_URL` | Used by both SQL and HTTP paths |

### 1.3 Runtime / First Boot

| File | Responsibility | Notes |
|---|---|---|
| `src/rosclaw/core/runtime.py` | `RuntimeConfig.seekdb_backend`, `Runtime._do_initialize()` | Supports only `memory` or `sqlite`; defaults to `memory` |
| `src/rosclaw/firstboot/config.py` | `memory.backend` defaults to `"local"` | Not wired to `RuntimeConfig` |
| `src/rosclaw/cli.py` | `_memory_db_path()`, `_practice_seekdb_client()`, practice subcommands | Creates `SeekDBBridge` at `http://localhost:2881` |

---

## 2. SQLite Databases in the Wild

| Path | Size (approx.) | Purpose | Rows / Notes |
|---|---|---|---|
| `~/.rosclaw/memory/seekdb.sqlite` | small | CLI/agent long-term memory | Default `memory` backend is in-memory; only used when SQLite chosen |
| `~/.rosclaw/practice/runs/rh56_rps/indexes/practice_catalog.sqlite` | part of 5.9 GB data root | Practice event/session catalog | `events`: 711,091; `practice_event_index`: 0; `practices`: 110; `artifacts`: 0 |
| `~/.rosclaw/practice/runs/rh56_rps/seekdb.sqlite` | small-medium | Distilled practice knowledge | Written by `SeekDBIngestor` |

Data root size: **5.9 GB** for the RH56 7×24 self-RPS stress test.

---

## 3. Tables & Schemas

### 3.1 `SEEKDB_SCHEMAS` (memory / knowledge plane)

Defined in `src/rosclaw/memory/seekdb_client.py`. Includes:

- `knowledge_entities` (id, type, name, observations, metadata, …)
- `knowledge_relations` (from_entity, relation_type, to_entity, …)
- `heuristic_rules` (id, rule_type, condition_json, action_json, …)
- `skill_registry` (id, skill_id, version, manifest_json, …)
- `interventions` (id, failure_signature, how_rule_id, outcome, …)
- Plus Sprint 8 Knowledge Plane tables (`body_cognition`, `sim2real_deltas`, `candidates`, `promotion_results`, etc.)

All tables use `id` as primary key. SQLite backend auto-creates `_migrated_at` columns on first open.

### 3.2 `PracticeCatalog` tables

Defined in `src/rosclaw/practice/storage/catalog.py`:

- `practices` — top-level practice record
- `sessions` — session metadata
- `episodes` — episode metadata
- `events` — one row per event (event_id, event_type, source, timestamp, payload JSON)
- `practice_event_index` — v2 index (currently never populated)
- `artifacts` — artifact records (currently 0 rows)

---

## 4. Risk Map

| Location | Risk | Severity | Phase 0 Action |
|---|---|---|---|
| `memory/seekdb_client.py` `SeekDBSQLiteClient` | No `check_same_thread=False`, no RLock | High | Rename to `SQLiteKnowledgeStore`, add RLock + PRAGMAs |
| `memory/seekdb_client.py` `insert()` | Broad `except Exception` + `REPLACE INTO` swallows errors | High | Use `ON CONFLICT(id) DO UPDATE SET` |
| `memory/seekdb_client.py` `SeekDBMySQLClient` | Single `pymysql` connection, no thread lock | High | Add RLock (Phase 0); connection pool later |
| `practice/storage/catalog.py` | Per-event `commit()` | High | Introduce `_BatchWriter` |
| `practice/storage/layout.py` | `timeline.jsonl` duplicates `events.jsonl` | Medium | Default to not writing `timeline.jsonl` |
| `practice/recorder.py` + `coordinator.py` | `event_count` under-counts | Medium | Derive from actual JSONL/catalog rows |
| `practice/seekdb_bridge.py` + `core/runtime.py` | Same `ROSCLAW_SEEKDB_URL` interpreted as HTTP or SQL DSN | High | Separate env vars, distinct default ports |
| `core/runtime.py` | Default `seekdb_backend="memory"` | Medium | Keep default but allow `sqlite`/`mysql`; document trade-off |
| `practice/storage/catalog.py` | `practice_event_index` empty | Low | Populate in Commit 4 |

---

## 5. External Products We Do **Not** Use

- **https://docs.seekdb.ai/seekdb/seekdb-overview/** — This is an unrelated commercial/open-source product. `rosclaw` has its own internal "SeekDB" naming that predates awareness of that site.
- **OceanBase** — Mentioned in the audit document as a future target; no real backend exists today.
- **pyseekdb / SeekDB Embedded / SeekDB Server** — Not integrated.

---

## 6. Recommended Naming Cleanup

| Current Name | Phase 0 Name | Notes |
|---|---|---|
| `SeekDBMemoryClient` | `InMemoryKnowledgeStore` | Deprecated alias kept |
| `SeekDBSQLiteClient` | `SQLiteKnowledgeStore` | Deprecated alias kept |
| `SeekDBMySQLClient` | `SeekDBMySQLClient` (unchanged) | Docstring updated to clarify experimental status |
| `SeekDBBridge` | `SeekDBBridge` (unchanged) | Default URL moved to `:2882` or explicit config |
| `ROSCLAW_SEEKDB_URL` | `ROSCLAW_SEEKDB_URL` (SQL DSN only) | HTTP bridge uses `ROSCLAW_PRACTICE_HTTP_ADAPTER_URL` |

---

## 7. References

- `~/workspace/rosclaw/rosclaw_test/数据库优化v1.md` — Original audit request.
- `docs/database/M0_LINEAGE_AUDIT.md` — Git history of the "SeekDB" name.
- `docs/database/SQLITE_HARDENING.md` — SQLite-specific hardening decisions.
- `docs/database/FINAL_DATABASE_AUDIT_REPORT.md` — Final report (populated after validation).
