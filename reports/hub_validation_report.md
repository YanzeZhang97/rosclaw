# ROSClaw Hub Validation Report

**Date:** 2026-06-21
**Scope:** `src/rosclaw/hub/`, `tests/hub/`, Hub documentation, README/QUICKSTART/CI updates
**Objective:** Confirm that the Hub subsystem meets the acceptance criteria from
the master implementation plan.

## Validation criteria

| # | Criterion | Method | Result |
|---|-----------|--------|--------|
| 1 | Code passes lint | `ruff check src/rosclaw/hub tests/hub` | PASS |
| 2 | Code is formatted | `ruff format --check src/rosclaw/hub tests/hub` | PASS |
| 3 | Unit + integration tests pass | `pytest tests/hub -q` | PASS (153 passed) |
| 4 | E2E lifecycle works | `tests/hub/test_e2e_fake_registry.py` | PASS |
| 5 | Security regressions covered | `tests/hub/test_security_regression.py` | PASS |
| 6 | Documentation written | `docs/hub/*.md` created | PASS |
| 7 | Progress / validation reports written | `reports/hub_*.md` created | PASS |
| 8 | README / QUICKSTART updated | Hub quickstart added | PASS |
| 9 | CI updated | Dedicated `hub-test` job added to `.github/workflows/ci.yml` | PASS |
| 10 | Installer transaction / rollback tests | `tests/hub/test_installer_transaction.py` | PASS |
| 11 | MCP config merge tests | `tests/hub/test_mcp_merge.py` | PASS |

## Commands run

```bash
ruff check src/rosclaw/hub tests/hub
ruff format --check src/rosclaw/hub tests/hub
pytest tests/hub -q
```

CI workflow additionally runs `pytest tests/hub -v` in a dedicated `hub-test` job
after `lint` and `type-check` succeed.

## Pull request

- **PR:** [#18 feat(hub): Phase 6 completion — installer transaction/rollback tests, MCP merge tests, and lockfile cleanup fix](https://github.com/ros-claw/rosclaw/pull/18)
- **Branch:** `hub/phase6-completion` → `main`
- **Status:** OPEN; CI checks in progress/queued at time of report

## Detailed findings

### Lint and format

- `ruff check` reports no errors across `src/rosclaw/hub` and `tests/hub`.
- `ruff format --check` reports all 36 files already formatted.

### Tests

- `pytest tests/hub -q` reports **153 passed**.
- Test modules cover schema, refs, cache, index, CLI, verifier, permissions,
  licenses, lockfile, installer transaction, MCP merge, publisher, E2E
  lifecycle, and security regression.

### Transaction and rollback

`tests/hub/test_installer_transaction.py` validates:

1. Happy-path local install writes the target directory, lockfile entry,
   cache record, registry entry, and managed MCP server.
2. Registry failure after file copy rolls back the target directory, lockfile,
   cache record, and MCP state.
3. Post-MCP failure rolls back the registry entry, MCP fragment, lockfile,
   and cache record.
4. Re-installing an already-installed asset raises `ASSET_ALREADY_INSTALLED`.
5. Uninstall removes the target directory, lockfile entry, cache record,
   registry entry, and MCP server entry.

A real bug was found and fixed during this work: `_rollback()` in
`src/rosclaw/hub/installer.py` now removes the lockfile entry and saves the
lockfile, preventing partial-install state leaks.

### MCP config merge

`tests/hub/test_mcp_merge.py` validates:

1. `add_server()` writes `.mcp.json` and a per-server runtime fragment.
2. Re-adding the same asset is idempotent (overwrites, never duplicates).
3. `remove_server()` deletes the entry and fragment but preserves unmanaged
   servers.
4. `list_servers()` only returns rosclaw-managed entries.
5. `is_managed()` reflects whether an asset's server is present.
6. Corrupt `.mcp.json` and missing-entrypoint-command errors raise `HubError`.

### End-to-end lifecycle

`test_full_lifecycle_publish_sync_search_install_list_uninstall` exercises:

1. Publishing a valid skill to the fake registry.
2. Verifying registry files (`manifests/...`, `bundles/...`, `catalog.jsonl`).
3. Syncing the catalog into SQLite and caching manifests.
4. Searching the catalog.
5. Installing by `rosclaw://` reference.
6. Checking the lockfile, runtime registry, and installed-state JSON.
7. Listing installed assets.
8. Uninstalling and verifying removal.

`test_install_by_ref_requires_cached_manifest` confirms that installing by
reference fails gracefully when the manifest has not been cached by `sync`.

### Security regression coverage

`tests/hub/test_security_regression.py` includes:

- Tampered `checksums.txt` detected by verifier and installer.
- Tampered artifact digest detected by verifier and installer.
- Missing SBOM / provenance files detected.
- Dangerous `safety_config` modification blocked without
  `--allow-safety-config-changes`.
- Non-local inbound network access blocked without
  `--allow-network-inbound`.
- License denial without `--accept-license`.
- License acceptance with `--accept-license`.
- Secret-scan publish rejection in strict mode.
- Secret-scan warning in non-failing mode.

### Documentation

- `docs/hub/cli.md` — command reference for all `rosclaw hub` subcommands.
- `docs/hub/security.md` — threat model, verification, permission/license
  policy, install-time guards.
- `docs/hub/publish_guide.md` — full publishing workflow.
- `docs/hub/private_assets.md` — private/internal asset handling.
- `docs/hub/asset_manifest.md` — manifest schema reference.

### Reports

- `reports/hub_progress.md` — implementation summary by phase.
- `reports/hub_validation_report.md` — this report.

### README / QUICKSTART / CI

- `README.md` updated with a Hub quickstart section, feature summary, and
  repository structure note.
- `QUICKSTART.md` updated with Hub quickstart steps.
- `.github/workflows/ci.yml` updated with a dedicated `hub-test` job that runs
  `pytest tests/hub -v` after `lint` and `type-check` succeed.

## Known issues

- `mypy src/rosclaw/hub` reports many pre-existing type errors in modules
  outside the Hub subsystem because mypy follows imports. These are not
  introduced by the Hub work and are tracked separately.
- Placeholder signing material is present and must be replaced before
  production use.

## Sign-off

The ROSClaw Hub subsystem satisfies the Phase 6 acceptance criteria and is
ready for wider runtime integration and future cloud-registry work.

**Validated by:** Claude Code / automated test suite
**Date:** 2026-06-21
