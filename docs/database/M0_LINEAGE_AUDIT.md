# M0 Lineage Audit: Where Did "SeekDB" Come From?

> Goal: Trace the origin of the `SeekDB*` naming in `rosclaw`, understand how it became overloaded, and document the decision to rename the SQLite/Memory clients in Phase 0.

## Key Commits

```text
f573d32  feat: Sprint 4+5 UnifiedTimeline + SeekDB
1af6b63  feat(practice): Physical Data Flywheel P0 skeleton (#34)
5b9151f  feat(practice): wire SeekDBBridge into EpisodeRecorder and Runtime
716786e  feat(practice): add closed-loop core (ids, schema, artifact store, catalog v2, recorder, coordinator)
4a28d0f  feat(practice): add verify, distill, seekdb ingest, query, and export
837b9cb  fix(practice): stabilize closed-loop catalog v2, SeekDB ingest, and verify
6cf63a9  fix(practice): canonical FAILED→failure outcome mapping and RPS SeekDB body_id
```

## Timeline

### 1. `f573d32` — "Sprint 4+5 UnifiedTimeline + SeekDB"

- Added `src/rosclaw/memory/seekdb_client.py` with `SEEKDB_SCHEMAS`.
- Added `SeekDBMemoryClient` and `SeekDBSQLiteClient`.
- Added `src/rosclaw/practice/timeline.py` (later replaced by the practice flywheel).
- Tests: `tests/test_seekdb.py`, `tests/test_timeline.py`.

At this point, "SeekDB" meant: *an internal SQLite/memory knowledge graph store for the Runtime's long-term memory*.

### 2. `1af6b63` / `d037fdd` — "Physical Data Flywheel P0 skeleton"

- Added `src/rosclaw/practice/` package.
- Introduced `SeekDBBridge` as an HTTP adapter to a SeekDB-compatible server.
- Added `SeekDBMySQLClient` (experimental SQL port).

This is the first naming collision: the same word "SeekDB" now refers to both:
- The internal SQL/memory knowledge store (`SeekDB*Client`), and
- An external HTTP service (`SeekDBBridge`).

### 3. `716786e` — "add closed-loop core"

- Added `PracticeCatalog` with `events`, `sessions`, `episodes`, `practices` tables.
- Added `practice_event_index` table but never populated it.
- `PracticeCatalog` commits after every INSERT.

### 4. `4a28d0f` / `837b9cb` — Distill / Ingest / Verify / Query

- `SeekDBIngestor` writes distilled practice results into the same `SeekDB*Client` schema.
- `PracticeQuery` reads from the same client.
- `SeekDBBridge` remained at default `http://localhost:2881`.

### 5. `6cf63a9` — RPS body_id / outcome fix

- Fixed canonical `FAILED → failure` mapping.
- Confirmed `SeekDB` ingest path is used by the RPS demo.

## How the Overload Happened

1. **Single schema file, multiple backends.** `SEEKDB_SCHEMAS` was designed for the knowledge plane, then reused for practice distilled data. The schemas fit, but the naming implied a single product.
2. **HTTP bridge borrowed the brand.** `SeekDBBridge` talks to an external service that happens to expose a compatible schema. It is not the same implementation.
3. **URL collision.** `ROSCLAW_SEEKDB_URL` is read by `SeekDBConfig` and passed to `_practice_seekdb_client()` (SQL path) and to `SeekDBBridge` (HTTP path). A value like `http://localhost:2881` makes sense to the bridge but is invalid to the SQL client.

## Phase 0 Decision

- Rename the internal SQLite/Memory clients to `*KnowledgeStore` to clarify they are **local knowledge-plane storage**.
- Keep `SeekDBMySQLClient` name but update docstring to "Experimental MySQL-compatible backend (SeekDB/OceanBase SQL port)".
- Keep `SeekDBBridge` name but move its default URL to `:2882` and introduce `ROSCLAW_PRACTICE_HTTP_ADAPTER_URL` for HTTP configuration.
- Reserve `ROSCLAW_SEEKDB_URL` for SQL DSNs (`sqlite://`, `mysql://`, `seekdb://`).

## Git Commands Used

```bash
git log --oneline --all --diff-filter=A -- src/rosclaw/memory/seekdb_client.py src/rosclaw/practice/storage/catalog.py src/rosclaw/practice/recorder.py src/rosclaw/practice/coordinator.py
git log --oneline --all -S "SeekDB" -- src/rosclaw/memory/seekdb_client.py src/rosclaw/practice/storage/catalog.py
git log --oneline --all --grep="SeekDB"
git show --stat --oneline f573d32
```

## Conclusion

"SeekDB" in `rosclaw` is an internal name for a family of storage clients and one HTTP bridge. It is **not** the external product at docs.seekdb.ai. Phase 0 renames the most misleading classes to reduce operator confusion while keeping backward-compatible aliases.
