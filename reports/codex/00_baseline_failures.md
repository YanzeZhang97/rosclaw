# Current Baseline

Date: 2026-07-09

Repository: `/home/ubuntu/rosclaw/rosclaw/rosclaw-v1.0`

Branch: `main`

PR #55 merge commit: `342d81735df7ad03c6ffa8346fb473ce1f5457dc`

## Current Gates

| Command | Result |
|---|---|
| `python -m compileall -q src tests` | pass |
| `ruff check .` | pass |
| `ruff format --check .` | pass, 890 files formatted |
| `mypy src/rosclaw` | pass, 457 source files |
| `pytest -q` | pass, 3704 passed, 30 skipped, 15 deselected |
| `scripts/codex/validate_full_runtime.sh` | pass, `FAILURES=0` |

Full validation evidence: `reports/codex/20260709_050044/commands.log`.

## Resolved Historical Failures

- Repo-wide format debt is cleared.
- Top-level `rosclaw darwin --help` is present.
- Provider `health`, explainable `route`, and safe `benchmark --dry-run` commands are present.
- Universal agent installation and MCP stdio discovery pass with 13 tools.
- UR5e MuJoCo verification passes with real physics state.
- ROS2 rosbridge discovery passes on ports 9090 and 32887.
- Practice record, strict verify, distill, query, Parquet export, and LeRobot export pass.
- Real SeekDB/OceanBase ingestion and query pass through the native MySQL-compatible port 2881.
- Repeated real SeekDB ingestion is idempotent across all seven Practice tables.
- Runtime safety failure now flows through Practice, Memory, How, Auto,
  sandbox/Darwin evaluation, and simulated Skill Registry promotion.

## Remaining Environment Notes

- `.venv-codex/bin/mypy src/rosclaw` still encounters duplicate `mcap` package mapping. The normal `mypy src/rosclaw` command passes; the validation script records the virtualenv-specific command as optional.
- ROS1 port 9091 accepts TCP but its websocket handshake reports an internal 9090 Host/port mismatch. This is a container configuration issue, not a ROSClaw CLI failure.
