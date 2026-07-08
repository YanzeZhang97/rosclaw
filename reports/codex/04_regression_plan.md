# Regression Plan

## P1: Environment Hygiene

- Fix the `.venv-codex` `mcap` duplicate-module mapping so the script's mypy step can become required.
- Fix the ROS1 rosbridge container so external port 9091 is accepted by its websocket Host validation.

## P1: SeekDB Operations

- Add a deployment integration job that starts `oceanbase/seekdb` and runs the real MySQL DSN Practice loop.
- Decide whether RuntimeConfig should add a `mysql`/`seekdb` backend alongside `memory` and `sqlite`.
- Deprecate or clearly package the legacy HTTP `SeekDBBridge` adapter path.

## P2: Provider Reality

- Run provider invoke/latency/schema benchmarks against configured VLM/VLA/world-model endpoints.
- Record endpoint health and benchmark evidence in Practice rather than treating the built-in catalog as runtime health.

## P2: Evolution Hardening

- Keep `tests/integration/test_physical_ai_agent_acceptance.py` as the
  no-hardware acceptance chain for Runtime -> Practice/Memory -> How -> Auto
  -> sandbox/Darwin -> simulated Skill Registry promotion.
- Add production benchmark datasets and explicit human approval before any
  promotion beyond the simulated `sim` level.

## P3: Hardware Acceptance

- Validate one explicitly authorized robot through read-only state, simulation preview, guarded command validation, and supervised execution.
- Keep certified emergency-stop and industrial safety systems outside ROSClaw's software trust boundary.
