# Changelog

All notable changes to ROSClaw will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-28

### Added

- **Core Architecture**
  - EventBus with publish/subscribe, priority queuing, and history
  - LifecycleMixin with 8-state lifecycle management
  - Runtime orchestrating all six grounding engines
  - Command-Response pattern for MCPHub via asyncio Futures

- **Six Grounding Engines**
  - **Physical (e-URDF)**: Robot model parser with JointSpec/LinkSpec
  - **Action (Firewall)**: DigitalTwinFirewall with 3-layer validation (joint limits, collision, torque), SafetyLevel enum (STRICT/MODERATE/PERMISSIVE)
  - **Timeline (Practice)**: UnifiedTimeline with 8-channel sensorimotor recording at 1kHz, PracticeRecorder with PraxisEvent schema
  - **Experience (Memory)**: SeekDB with Memory/SQLite backends, experience storage and similarity search
  - **Skill (SkillManager)**: SkillRegistry with stats, SkillExecutor with precondition checking, SkillLoader for JSON/programmed skills
  - **Collaboration (Swarm)**: SwarmRuntimeManager for multi-agent task allocation

- **LLM Provider Abstraction**
  - LLMProvider ABC with plan_task, analyze_failure, generate_skill_description, health_check
  - DeepSeekProvider, OpenAIProvider, QwenProvider implementations
  - Factory pattern: get_provider(), list_providers(), register_provider()
  - Backward-compatible aliases (DeepSeekClient, DeepSeekConfig)

- **MCP Drivers**
  - BaseDriver abstract base with DriverState and TrajectoryCommand
  - MuJoCoSimDriver with mock mode fallback
  - ROS2Driver and SerialDriver stubs

- **CLI Tool**
  - `rosclaw --version`
  - `rosclaw init [DIR]` — workspace initialization with config file
  - `rosclaw run` / `rosclaw start` — runtime launcher
  - `rosclaw status` — status check

- **Docker Support**
  - Dockerfile based on python:3.11-slim
  - docker-compose.yml with volume mounts and health checks

- **Developer Experience**
  - Makefile with install, test, lint, format, clean, all targets
  - hello_robot.py example demonstrating full workflow
  - CONTRIBUTING.md with dev standards and PR process
  - MIT LICENSE

- **Documentation**
  - API_REFERENCE.md with full public API
  - BENCHMARK.md with performance metrics
  - SECURITY_AUDIT.md
  - ROLE_SWAP_REVIEW.md (architecture review)
  - COLLABORATION_LOG.md

### Fixed

- LifecycleMixin `_state` collision with BaseDriver `_driver_state` (renamed to `_lifecycle_state`)
- EventBus accepting non-callable handlers (added TypeError guard)
- MuJoCoSimDriver empty path causing ParseXML error (added whitespace guard)
- SkillExecutor registry parameter inconsistency (reverted to required)
- Driver `move_joints` allowed before initialization (added `_ensure_ready` guard)
- Joint position validation accepting unsafe values (tightened bound to 1e5)
- EventBus `clear_history` missing type annotation

### Security

- Input validation for joint positions (type, finiteness, bounds)
- SkillRegistry validation (SkillEntry type check, empty name rejection)
- Double-initialization guard in LifecycleMixin
