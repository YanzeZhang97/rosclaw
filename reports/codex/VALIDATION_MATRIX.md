# ROSClaw Validation Matrix

Date: 2026-07-09

| Area | Actual | Status | Evidence |
|---|---|---|---|
| Install/dependencies | `pip check` clean | pass | `20260709_050044/commands.log` |
| Lint/format/type | Ruff pass; mypy pass on 457 source files | pass | `00_baseline_failures.md` |
| Unit/integration | 3704 passed, 30 skipped, 15 deselected | pass | `20260709_050044/commands.log` |
| CLI | All required module help commands return zero | pass | `20260709_050044/cli.log` |
| Agent integration | Universal install and MCP stdio discovery, 13 tools | pass | `20260709_050044/commands.log` |
| Provider | Health contract, explainable route, benchmark dry-run | pass | `20260709_050044/commands.log` |
| Sandbox | UR5e MuJoCo advances 8 steps with real qpos/qvel | pass | `20260709_050044/commands.log` |
| Physical-AI loop | Runtime block -> Practice/Memory -> How -> Auto -> Darwin -> simulated champion | pass | `tests/integration/test_physical_ai_agent_acceptance.py` |
| Practice | Record, strict verify, distill, query, Parquet, LeRobot | pass | `20260709_050044/commands.log` |
| SeekDB | Native 2881 SQL ingest/query; repeated ingest remains 1 row/table | pass | `20260709_050044/commands.log` |
| ROS2 | Read-only ping/discover on 9090 and 32887 | pass | `20260709_050044/commands.log` |
| ROS1 | 9091 TCP open; websocket Host port mismatch | environment issue | `20260709_050044/commands.log` |
| Hidden Unicode | No bidi control characters | pass | `20260709_050044/commands.log` |

The detailed matrix is maintained in `03_validation_matrix.md`.
