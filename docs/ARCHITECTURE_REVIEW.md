# ROSClaw v1.0 Architecture Review

**Date**: 2026-05-27
**Reviewer**: rosclaw_qwen (Chief Architecture Reviewer)
**Collaboration**: rosclaw_qwen (architect) → rosclaw (executor) via shared filesystem
**Scope**: `rosclaw-v1.0/src/rosclaw/` (3,696 LOC), `tests/`, vision documents
**Status**: Alpha (Sprint 1-2 partial completion)

---

## Executive Summary

ROSClaw v1.0 的代码骨架已初步成形，核心基础设施（EventBus, Lifecycle, Runtime）设计合理，Firewall 和 Data Layer 实现质量较高。但**愿景文档与实际代码之间存在重大架构鸿沟**：Event Bus 虽然存在但未被用作模块间通信的唯一通道；Memory 是在内存列表而非 SeekDB Knowledge Plane；Agent Runtime 硬编码了单一 LLM 提供商。当前代码更接近"可运行的原型"而非"统一工程架构"。

**Critical Issues**: 6 | **Major Issues**: 9 | **Minor Issues**: 7

---

## 1. Module Dependency Graph

### 1.1 实际代码依赖关系

```text
                          cli.py / bin/rosclaw
                               |
                               v
                     +-- core/runtime.py --+
                     |     (Runtime)       |
                     |                     |
          creates    |    creates          |   creates
          +----------+----------+----------+----------+
          |          |          |          |          |
          v          v          v          v          v
     firewall/   memory/    practice/   swarm/    e_urdf/
     decorator   interface  recorder    manager   parser
       |                      |
       |                      v
       |                  data/flywheel.py
       |                      |
       |                      v
       |                  data/ring_buffer.py
       |
       +---> [mujoco, numpy]
       
     mcp/ur5_server.py -----> firewall/decorator.py
          |                    (direct import)
          +---> [rclpy, mcp, ROS 2 msgs]
          
     agent_runtime/mcp_hub.py -----> core/event_bus.py
          |                           core/lifecycle.py
          +---> [mcp.server (optional)]
          
     agent_runtime/ai_collaboration.py
          |
          +---> [openai (for DeepSeek API)]
```

### 1.2 愿景中的依赖关系（未实现）

```text
     ┌──────────────────────────────────────────┐
     │            Agent Runtime                  │
     │   (Claude / GPT / Gemini / Qwen / ...)   │
     └────────────────┬─────────────────────────┘
                      │ MCP
                      v
     ┌──────────────────────────────────────────┐
     │           ROSClaw Runtime                 │
     │                                          │
     │  ┌──────────────────────────────────┐    │
     │  │       Event Bus (唯一通道)        │    │
     │  │  publish/subscribe only           │    │
     │  └──────┬───┬───┬───┬───┬───────────┘    │
     │         │   │   │   │   │                │
     │    ┌────┘   │   │   │   └────┐           │
     │    v        v   v   v        v           │
     │  Memory  Practice Firewall How  Darwin   │
     │    │        │      │                       │
     │    └────────┴──────┴──── SeekDB ──┘       │
     │           (Shared Knowledge Plane)         │
     └──────────────────────────────────────────┘
```

### 1.3 依赖偏差分析

| 维度 | 愿景 | 实际 | 偏差等级 |
|------|------|------|----------|
| 模块通信 | Event Bus 唯一通道 | Runtime 直接实例化并持有引用 | **CRITICAL** |
| Memory 后端 | SeekDB Knowledge Plane | 内存 list | **CRITICAL** |
| Agent Runtime | 多 LLM 抽象 | 硬编码 DeepSeek | **MAJOR** |
| PraxisEvent | 统一事件结构体 | 不存在 | **MAJOR** |
| Skill Manager | 独立引擎 | 不存在 | **MAJOR** |
| DDS Reflex | Swarm 底层通信 | 不存在 | **MINOR** (Sprint 4) |
| Flywheel | 独立 CLI `rosclaw distill` | DataFlywheel 类存在但无 CLI 导出 | **MINOR** |

---

## 2. Interface Inconsistencies

### 2.1 [CRITICAL] Event Bus 未被用作模块间唯一通道

**愿景要求**（见解一, Section 五）：
> 所有模块禁止互相调用。只能 publish / subscribe。

**实际代码**：`Runtime._do_initialize()` 直接实例化模块并存储在 `self._modules` 列表中。模块没有接收 EventBus 引用，无法发布或订阅事件。

```python
# core/runtime.py L112-117
self._memory = MemoryInterface(self.config.robot_id)  # 无 event_bus 参数
self._modules.append(self._memory)

self._practice = PracticeRecorder(                     # 无 event_bus 参数
    robot_id=self.config.robot_id,
    joint_dof=self.config.joint_dof,
)
```

**影响**：模块无法通过 EventBus 通信，整个"统一事件总线"架构形同虚设。

### 2.2 [CRITICAL] MCPHub.handle_tool_call() 是 fire-and-forget

`MCPHub` 的 tool handler 向 EventBus 发布命令后**不等待结果**直接返回：

```python
# agent_runtime/mcp_hub.py L219-228
def _handle_move_joints(self, arguments: dict) -> dict:
    self.event_bus.publish(Event(
        topic="agent.command",
        payload={...},
        source="mcp_hub",
    ))
    return {"status": "command_issued"}  # 无实际执行结果
```

LLM Agent 收到 `command_issued` 但永远不知道命令是否成功执行。需要一个 request-response 模式或 future/promise 机制。

### 2.3 [MAJOR] 两套重复的 RobotState 定义

| 位置 | 类名 | 字段 |
|------|------|------|
| `data/flywheel.py` | `RobotState` | `timestamp, joint_positions, joint_velocities, joint_torques, end_effector_pose, gripper_state` |
| `mcp/ur5_server.py` | `RobotState` | `joint_positions, joint_velocities, joint_efforts, joint_names, end_effector_pose, is_connected, last_update_time` |

两个同名 dataclass 字段完全不同，缺乏统一的 `core/types.py` 定义标准类型。

### 2.4 [MAJOR] CLI 入口重复

| 文件 | 内容 |
|------|------|
| `bin/rosclaw` | 89 行，完整 CLI 实现 |
| `src/rosclaw/cli.py` | 80 行，几乎相同实现 |

`pyproject.toml` 的 `project.scripts` 指向 `rosclaw.cli:main`，但 `bin/rosclaw` 是独立脚本。维护两套入口极易导致行为不一致。

### 2.5 [MAJOR] `__init__.py` 顶层导入过于 eager

`src/rosclaw/__init__.py` 尝试导入所有模块，对缺少可选依赖（如 `mujoco`, `rclpy`）的环境会大面积失败：

```python
# L51-55: 这些导入在没有可选依赖时会全部失败
from rosclaw.e_urdf import EURDFParser, RobotModel
from rosclaw.agent_runtime import MCPHub, AgentContext, DeepSeekClient, DeepSeekConfig
from rosclaw.memory import MemoryInterface
from rosclaw.practice import PracticeRecorder
from rosclaw.swarm import SwarmRuntimeManager
```

只有 `firewall` 有 try/except 保护，其他 5 个模块导入失败会直接让 `import rosclaw` 崩溃。

### 2.6 [MINOR] pyproject.toml 中 MCP 依赖名可能不正确

```toml
dependencies = [
    "mcp>=1.0.0",  # 实际 PyPI 包名可能是 "mcp" 或 "modelcontextprotocol"
]
```

需确认 PyPI 上的实际包名。

---

## 3. Missing Implementations

### 3.1 Critical Missing Components

| 组件 | 愿景描述 | 当前状态 | 优先级 |
|------|----------|----------|--------|
| **SeekDB Integration** | Knowledge Plane，所有模块共用 | Memory 使用 `list[dict]`，无 SeekDB 连接 | P0 |
| **PraxisEvent** | 统一实践事件结构体，绑定 CoT + 物理数据 | 不存在 | P0 |
| **Agent Runtime 抽象** | 屏蔽 Claude/GPT/Gemini/Qwen 差异 | 硬编码 `DeepSeekClient` | P0 |
| **Module → EventBus wiring** | 所有模块通过 EventBus 通信 | 模块不持有 EventBus 引用 | P0 |
| **Command Response 机制** | LLM 发出命令后获取执行结果 | fire-and-forget | P0 |
| **Skill Manager** | 经验→技能转化引擎 | 不存在 | P1 |

### 3.2 Sprint Gap Analysis

| Sprint | 愿景目标 | 实现状态 | 完成度 |
|--------|----------|----------|--------|
| Sprint 0 | Architecture Freeze, RFC-0001 | 无 RFC 文档 | 10% |
| Sprint 1 | e-urdf-zoo, core, cli, mcp | e_urdf parser 完成，core 基本完成 | 60% |
| Sprint 2 | runtime, agent-runtime, event-bus | EventBus 存在但未连通，agent-runtime 有骨架 | 40% |
| Sprint 3 | firewall, mjlab, e-urdf integration | Firewall 实现完整且质量高 | 70% |
| Sprint 4 | practice, MCAP, Unified Timeline | PracticeRecorder 存在但未接入事件流 | 30% |
| Sprint 5 | seekdb, rosclaw-memory | Memory 是 placeholder | 10% |
| Sprint 6 | how, know | 不存在 | 0% |
| Sprint 7 | flywheel, auto | DataFlywheel 存在但无 distill CLI | 20% |
| Sprint 8 | swarm, DDS Reflex | SwarmRuntimeManager 是 stub | 15% |
| Sprint 9 | darwin, eeib | 不存在 | 0% |

**Overall Sprint Completion**: ~25%

### 3.3 Empty Packages

| Package | 文件数 | 说明 |
|---------|--------|------|
| `mcp_drivers/` | 1 (`__init__.py`, 8 行) | 声明为"Hardware Abstraction Layer"但完全为空 |

---

## 4. Test Coverage Analysis

### 4.1 测试覆盖矩阵

| 模块 | 源文件 | LOC | 测试文件 | 测试数 | 覆盖状态 |
|------|--------|-----|----------|--------|----------|
| `firewall/decorator.py` | 1 | 438 | `test_firewall.py` | 17 | **Good** |
| `data/ring_buffer.py` | 1 | 302 | `test_data_layer.py` | 10 | **Good** |
| `data/flywheel.py` | 1 | 413 | `test_data_layer.py` | 7 | **Partial** |
| `mcp/ur5_server.py` | 1 | 650 | `test_mcp_server.py` | 14 | **Schema-only** |
| `core/event_bus.py` | 1 | 162 | - | 0 | **MISSING** |
| `core/runtime.py` | 1 | 243 | - | 0 | **MISSING** |
| `core/lifecycle.py` | 1 | 118 | - | 0 | **MISSING** |
| `e_urdf/parser.py` | 1 | 355 | - | 0 | **MISSING** |
| `agent_runtime/mcp_hub.py` | 1 | 308 | - | 0 | **MISSING** |
| `agent_runtime/ai_collaboration.py` | 1 | 205 | - | 0 | **MISSING** |
| `memory/interface.py` | 1 | 54 | - | 0 | **MISSING** |
| `practice/recorder.py` | 1 | 77 | - | 0 | **MISSING** |
| `swarm/manager.py` | 1 | 69 | - | 0 | **MISSING** |
| `cli.py` | 1 | 80 | - | 0 | **MISSING** |
| **TOTAL** | **14** | **3,696** | **3** | **48** | **~30%** |

### 4.2 测试质量问题

**`test_mcp_server.py`**: 14 个测试中大部分是**数据格式验证**而非功能测试：
- `TestMCPTools.test_tool_schemas`: 验证硬编码的 tool 列表（不是从代码读取的）
- `TestJointStateResponse`: 验证手写的 response 结构
- `TestMoveJointsValidation`: 验证 `len(positions) == 6`
- `TestMCPProtocol`: 验证 JSON-RPC 格式（与代码无关的纯格式检查）
- **没有任何测试实际调用 `UR5MCPServer` 或 `UR5ROSNode` 的方法**

### 4.3 关键测试缺失

| 缺失测试 | 风险 | 优先级 |
|----------|------|--------|
| EventBus publish/subscribe 正确性 | 核心通信基础设施未验证 | P0 |
| EventBus 并发安全（async subscribers） | 多线程/异步场景可能数据竞争 | P0 |
| Runtime 初始化/启动/停止生命周期 | 编排逻辑未验证 | P0 |
| LifecycleMixin 状态机转换 | 状态转换可能有 bug | P0 |
| EURDFParser 解析 UR5e XML | 模型解析正确性未验证 | P1 |
| MCPHub tool call → EventBus 流转 | 端到端命令流未验证 | P0 |
| MemoryInterface store/query | 即使是内存实现也需要验证 | P1 |
| PracticeRecorder 与 DataFlywheel 集成 | 录制流程未验证 | P1 |
| 端到端 Pipeline（LLM → Runtime → Firewall → Response） | 核心用户流程未验证 | P0 |

---

## 5. Strengths (What's Working Well)

### 5.1 Digital Twin Firewall (`firewall/decorator.py`) - Excellent

- **438 LOC**，MuJoCo 集成完整
- 三级安全等级（STRICT/MODERATE/LENIENT）
- 装饰器模式优雅，可直接用于生产
- 碰撞检测 + 关节限位 + 力矩限位三重验证
- `ValidationResult` 数据结构设计合理
- **测试覆盖最好**的模块（17 个测试）

### 5.2 Data Layer (`data/`) - Very Good

- `RingBuffer`: 预分配内存，O(1) append，适合 1kHz 实时控制
- `MultiChannelRingBuffer`: 多通道同步采集
- `DataFlywheel`: 事件驱动的数据捕获，存储优化 100x
- 测试包含性能基准（1kHz append <100ms/1000ops）
- LeRobot 导出接口为后续 Flywheel 奠定基础

### 5.3 Lifecycle Management (`core/lifecycle.py`) - Good

- 清晰的 8 状态状态机
- Mixin 设计便于所有模块继承
- 异常处理正确（ERROR state + error_message）
- stop() 使用 try/finally 确保状态转换

### 5.4 e-URDF Parser (`e_urdf/parser.py`) - Good

- 标准 URDF + 扩展语义解析
- `RobotModel.to_llm_context()` 直接解决 Symbol Grounding Problem
- 支持 sensor、control、metadata 扩展元素
- 数值计算（RPY → 旋转矩阵）正确

---

## 6. Improvement Recommendations

### 6.1 [P0] Wire EventBus into All Modules

**问题**: 模块不持有 EventBus 引用，无法实现事件驱动通信。

**方案**:
```python
class MemoryInterface(LifecycleMixin):
    def __init__(self, robot_id: str, event_bus: EventBus):  # 新增 event_bus
        super().__init__()
        self.robot_id = robot_id
        self.event_bus = event_bus

    def _do_initialize(self) -> None:
        # 订阅 PraxisEvent 自动记录
        self.event_bus.subscribe("praxis.completed", self._on_praxis_completed)
        self.event_bus.subscribe("praxis.failed", self._on_praxis_failed)
```

Runtime 需要在创建模块时注入 EventBus：
```python
self._memory = MemoryInterface(self.config.robot_id, event_bus=self.event_bus)
```

### 6.2 [P0] Define PraxisEvent Schema (RFC-0001)

**方案**:
```python
# core/types.py (NEW)
@dataclass(frozen=True)
class PraxisEvent:
    """统一实践事件 - RFC-0001"""
    event_id: str
    event_type: str           # "success" | "failure" | "emergency"
    timestamp: float
    robot_id: str
    agent_instruction: str    # LLM 的原始指令
    cot_trace: list[str]      # Chain-of-Thought 思维链
    joint_trajectory: list[list[float]]
    mcap_path: Optional[str]
    error_details: Optional[str]
    metadata: dict
```

### 6.3 [P0] Add Command-Response Pattern to MCPHub

**问题**: LLM 发命令后无法获取执行结果。

**方案**: 引入 EventBus request-response 模式：
```python
async def _handle_move_joints(self, arguments: dict) -> dict:
    request_id = str(uuid.uuid4())[:8]
    future = asyncio.get_event_loop().create_future()

    # 注册一次性响应处理器
    def on_response(event: Event):
        if event.metadata.get("request_id") == request_id:
            future.set_result(event.payload)

    self.event_bus.subscribe(f"agent.response.{request_id}", on_response)

    # 发布命令
    self.event_bus.publish(Event(
        topic="agent.command",
        payload={...},
        metadata={"request_id": request_id},
    ))

    # 等待结果（带超时）
    result = await asyncio.wait_for(future, timeout=30.0)
    return result
```

### 6.4 [P0] Unify Agent Runtime with LLM Provider Abstraction

**问题**: `ai_collaboration.py` 硬编码了 DeepSeek。

**方案**:
```python
# agent_runtime/llm_provider.py (NEW)
class LLMProvider(ABC):
    @abstractmethod
    def plan_task(self, instruction: str, context: dict) -> dict: ...

    @abstractmethod
    def analyze_failure(self, task: str, error: str) -> dict: ...

class DeepSeekProvider(LLMProvider): ...
class ClaudeProvider(LLMProvider): ...
class OpenAIProvider(LLMProvider): ...
class QwenProvider(LLMProvider): ...
```

### 6.5 [P1] Consolidate CLI Entry Points

删除 `bin/rosclaw`，保留 `src/rosclaw/cli.py` 作为唯一入口（通过 `pyproject.toml` 的 `project.scripts` 注册）。

### 6.6 [P1] Create `core/types.py` for Shared Types

统一 `RobotState`、`PraxisEvent`、`ValidationResult` 等核心类型，消除 `data/flywheel.py` 和 `mcp/ur5_server.py` 之间的重复定义。

### 6.7 [P1] Lazy Import All Optional Modules in `__init__.py`

```python
# 对所有可选模块使用 try/except
for module_name, symbols in [
    ("rosclaw.e_urdf", ["EURDFParser", "RobotModel"]),
    ("rosclaw.memory", ["MemoryInterface"]),
    ("rosclaw.practice", ["PracticeRecorder"]),
    ("rosclaw.swarm", ["SwarmRuntimeManager"]),
]:
    try:
        mod = importlib.import_module(module_name)
        for sym in symbols:
            globals()[sym] = getattr(mod, sym)
    except ImportError:
        for sym in symbols:
            globals()[sym] = None
```

### 6.8 [P1] SeekDB Integration Roadmap

1. 定义 `SeekDBClient` 接口（连接池 + CRUD）
2. `MemoryInterface` 接受 `SeekDBClient` 参数
3. 实现 `experience_graph` 表 schema
4. 添加 `rosclaw-compose` docker-compose.yaml 启动 SeekDB

### 6.9 [P2] Test Coverage Priority Plan

| 优先级 | 需新增测试 | 预估测试数 |
|--------|-----------|-----------|
| P0 | `test_event_bus.py` | 15 |
| P0 | `test_runtime.py` | 12 |
| P0 | `test_lifecycle.py` | 10 |
| P0 | `test_mcp_hub.py` | 10 |
| P1 | `test_eurdf_parser.py` | 8 |
| P1 | `test_memory.py` | 6 |
| P1 | `test_practice.py` | 6 |
| P1 | `test_swarm.py` | 4 |
| P2 | `test_e2e_pipeline.py` | 5 |
| **Total** | | **~76** |

当前 48 个测试 → 目标 124 个测试，覆盖率从 ~30% 提升至 ~70%。

---

## 7. Architecture Compliance Score

| 维度 | 评分 (1-10) | 说明 |
|------|:-----------:|------|
| Event Bus 架构 | 3 | EventBus 实现好但未被使用 |
| 模块解耦 | 4 | Runtime 直接引用模块，非 EventBus 通信 |
| 物理锚定 (Grounding) | 8 | Firewall + e-URDF 实现质量高 |
| LLM 抽象 | 2 | 硬编码单一提供商 |
| 数据层 | 8 | RingBuffer + Flywheel 设计优秀 |
| 测试覆盖 | 4 | Firewall/Data 好，其他模块空白 |
| 文档完整性 | 5 | 代码注释好，但缺少 RFC/接口文档 |
| 工程规范 | 7 | pyproject.toml 配置合理，ruff/mypy 已设置 |
| **总体** | **5.1** | |

---

## 8. Recommended Next Actions (Priority Order)

### Week 1: Fix Core Wiring
1. **[P0]** Wire EventBus into Memory, Practice, Swarm constructors
2. **[P0]** Define `core/types.py` with `PraxisEvent`, unified `RobotState`
3. **[P0]** Add request-response pattern to MCPHub
4. **[P0]** Write `test_event_bus.py` and `test_runtime.py`

### Week 2: LLM Abstraction + Memory
5. **[P0]** Extract `LLMProvider` ABC from `DeepSeekClient`
6. **[P0]** Implement SeekDB client interface
7. **[P1]** Consolidate CLI entry points
8. **[P1]** Fix `__init__.py` lazy imports

### Week 3: Close Sprint 4-5 Gap
9. **[P1]** Wire Practice recorder into EventBus command flow
10. **[P1]** Implement PraxisEvent pipeline: Command → Practice → Memory
11. **[P1]** Write remaining test files

### Week 4: Documentation + Polish
12. **[P2]** Write RFC-0001 (Architecture Document)
13. **[P2]** Add `docker-compose.yaml` for SeekDB
14. **[P2]** Remove `mcp_drivers/` or implement at least one driver

---

## 9. Detailed Missing Module Specifications (Executor Handoff)

This section provides concrete implementation blueprints for the executor (`rosclaw`) to implement the most critical missing modules.

### 9.1 `mcp_drivers/` — Hardware Abstraction Layer

**Current state**: Empty package (8 LOC `__init__.py` with `__all__ = []`).

**Vision**: Provide standardized MCP server implementations for specific robot platforms, decoupled from the generic `mcp/ur5_server.py` which is a monolithic ROS 2 + MCP implementation.

**Required structure**:
```text
mcp_drivers/
├── __init__.py          # Registry of available drivers
├── base.py              # Abstract base class (NEW)
├── ur5_driver.py        # Extract from mcp/ur5_server.py (REFACTOR)
├── g1_driver.py         # G1 humanoid driver (NEW - Sprint 4+)
└── simulated_driver.py  # MuJoCo-only driver for testing (NEW - P0)
```

**`base.py` — Required interface**:
```python
# src/rosclaw/mcp_drivers/base.py (NEW)
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class DriverCapabilities:
    """What this robot driver can do."""
    joint_dof: int
    has_gripper: bool
    has_force_sensors: bool
    max_payload_kg: float
    supported_actions: list[str]  # ["move_joints", "grasp", "move_cartesian", ...]

class RobotDriver(ABC):
    """
    Abstract base for all robot hardware drivers.
    Every driver must implement these methods.
    """

    @abstractmethod
    def get_capabilities(self) -> DriverCapabilities: ...

    @abstractmethod
    async def get_joint_states(self) -> dict: ...

    @abstractmethod
    async def move_joints(
        self, positions: list[float], duration: float = 2.0
    ) -> dict: ...

    @abstractmethod
    async def emergency_stop(self) -> dict: ...

    @abstractmethod
    def get_joint_limits(self) -> dict: ...

    @property
    @abstractmethod
    def robot_id(self) -> str: ...

    @property
    @abstractmethod
    def is_connected(self) -> bool: ...
```

**`simulated_driver.py` — P0 priority**: This is the most important driver because it enables the full test pipeline without real hardware.
```python
# src/rosclaw/mcp_drivers/simulated_driver.py (NEW)
class SimulatedDriver(RobotDriver):
    """
    MuJoCo-only driver for testing and CI.
    No ROS 2 dependency. Uses DigitalTwinFirewall as the simulation backend.
    """
    def __init__(self, model_path: str, robot_id: str = "sim_ur5e"):
        self._firewall = DigitalTwinFirewall(model_path)
        self._robot_id = robot_id
        # State tracked via MuJoCo sim

    async def move_joints(self, positions, duration=2.0):
        # Validate through firewall, then update sim state
        result = self._firewall.validate_trajectory([np.array(positions)])
        if not result.is_safe:
            return {"success": False, "error": result.violation_details}
        self._firewall.set_joint_positions(np.array(positions))
        return {"success": True, "positions": positions}
```

**Refactoring `mcp/ur5_server.py`**: The current 650 LOC monolith should be split:
- `UR5ROSNode` → move to `mcp_drivers/ur5_driver.py` (implements `RobotDriver`)
- `UR5MCPServer` → keep in `mcp/` as the MCP protocol layer
- The MCP layer should accept any `RobotDriver` via dependency injection

### 9.2 `skill_manager/` — Evolution Engine (Missing)

**Current state**: Does not exist. Not even an empty package.

**Vision** (from 见解一, Sprint 7): The `flywheel` + `auto` modules transform experiences into reusable skills:
```text
Experience (SeekDB) → Pattern Extraction → Skill Definition → Skill Registry
```

**Required structure**:
```text
skill_manager/           # (NEW - entire package)
├── __init__.py
├── skill.py             # Skill data model
├── registry.py          # Skill storage and retrieval
├── extractor.py         # Pattern extraction from PraxisEvents
└── executor.py          # Skill execution with validation
```

**`skill.py` — Core data model**:
```python
# src/rosclaw/skill_manager/skill.py (NEW)
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SkillPrecondition:
    """Condition that must be true before skill execution."""
    condition_type: str   # "joint_range", "object_present", "no_collision", ...
    parameters: dict

@dataclass
class Skill:
    """
    A reusable robot skill extracted from successful experiences.
    This is the atomic unit of the evolution flywheel.
    """
    skill_id: str
    name: str
    description: str                    # Natural language (LLM-generated)
    trajectory_template: list[list[float]]  # Parameterized trajectory
    preconditions: list[SkillPrecondition]
    parameters: dict                    # e.g., {"target_object": "cup"}
    success_rate: float = 0.0          # Updated after each execution
    execution_count: int = 0
    source_experience_ids: list[str] = field(default_factory=list)
    created_at: float = 0.0

    def is_reliable(self, threshold: float = 0.8) -> bool:
        return self.success_rate >= threshold and self.execution_count >= 3
```

**`registry.py` — Skill registry**:
```python
# src/rosclaw/skill_manager/registry.py (NEW)
class SkillRegistry(LifecycleMixin):
    """
    Registry for all learned skills.
    Backed by SeekDB in production, in-memory for testing.
    """
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.event_bus = event_bus
        self._skills: dict[str, Skill] = {}

    def register_skill(self, skill: Skill) -> str: ...
    def find_skill(self, task_description: str) -> Optional[Skill]: ...
    def update_skill_result(self, skill_id: str, success: bool) -> None: ...

    def _do_initialize(self):
        # Subscribe to PraxisEvents to auto-update skill stats
        self.event_bus.subscribe("praxis.completed", self._on_praxis_completed)
        self.event_bus.subscribe("praxis.failed", self._on_praxis_failed)
```

**`extractor.py` — Pattern extraction** (connects to DataFlywheel):
```python
# src/rosclaw/skill_manager/extractor.py (NEW)
class SkillExtractor:
    """
    Extracts reusable skills from successful PraxisEvents.
    Reads trajectory data from DataFlywheel event captures.
    """
    def extract_from_experience(
        self, experience: dict, flywheel_data_path: Path
    ) -> Optional[Skill]:
        """
        Analyze a successful experience and extract a parameterized skill.
        Uses LLM (via AgentRuntime) to generate natural language description.
        """
        # 1. Load trajectory from event data
        # 2. Generalize trajectory (remove absolute positions, keep relative motions)
        # 3. Identify preconditions from initial state
        # 4. Generate skill description via LLM
        # 5. Return Skill object
```

**Integration with EventBus**:
```text
PraxisEvent(SUCCESS) → SkillExtractor.extract() → SkillRegistry.register()
                                                    → EventBus.publish("skill.created")
                                                    → Memory stores skill metadata
                                                    → Darwin tracks skill evolution
```

### 9.3 `core/types.py` — Shared Type Definitions (NEW)

To eliminate the duplicate `RobotState` definitions:

```python
# src/rosclaw/core/types.py (NEW)
from dataclasses import dataclass, field
from typing import Optional, Any
import numpy as np

@dataclass
class RobotState:
    """
    Canonical robot state representation.
    Used by ALL modules — replaces duplicates in data/flywheel.py and mcp/ur5_server.py.
    """
    timestamp: float
    joint_positions: np.ndarray         # Shape: (dof,)
    joint_velocities: np.ndarray        # Shape: (dof,)
    joint_torques: np.ndarray           # Shape: (dof,)
    joint_names: list[str] = field(default_factory=list)
    end_effector_pose: Optional[np.ndarray] = None  # Shape: (4, 4)
    gripper_state: Optional[float] = None            # 0.0=open, 1.0=closed
    is_connected: bool = True

    def validate(self, expected_dof: int) -> bool:
        return (
            self.joint_positions.shape == (expected_dof,) and
            self.joint_velocities.shape == (expected_dof,) and
            self.joint_torques.shape == (expected_dof,)
        )

@dataclass(frozen=True)
class PraxisEvent:
    """
    Unified practice event — the core data structure of ROSClaw.
    Binds LLM reasoning (CoT) with physical execution data on a single timeline.
    RFC-0001 core type.
    """
    event_id: str
    event_type: str              # "success" | "failure" | "emergency"
    timestamp: float
    robot_id: str
    agent_instruction: str      # LLM's original natural language instruction
    cot_trace: list[str]         # Chain-of-Thought reasoning steps
    initial_state: RobotState
    final_state: Optional[RobotState]
    trajectory: list[list[float]]
    mcap_path: Optional[str]     # Path to MCAP recording
    error_details: Optional[str]
    duration_sec: float
    metadata: dict = field(default_factory=dict)
```

---

## 10. Executor Checklist (For `rosclaw` Instance)

Based on this review, here is the prioritized implementation checklist. Complete items in order.

### Phase 1: Fix Core Wiring (Critical — blocks everything else)

- [ ] **1.1** Create `src/rosclaw/core/types.py` with `RobotState` and `PraxisEvent` (Section 9.3)
- [ ] **1.2** Add `event_bus: EventBus` parameter to `MemoryInterface.__init__()` and `PracticeRecorder.__init__()` and `SwarmRuntimeManager.__init__()`
- [ ] **1.3** Update `Runtime._do_initialize()` to pass `self.event_bus` to all module constructors
- [ ] **1.4** In each module's `_do_initialize()`, subscribe to relevant EventBus topics
- [ ] **1.5** Add request-response pattern to `MCPHub.handle_tool_call()` (Section 6.3)
- [ ] **1.6** Write `tests/test_event_bus.py` (subscribe, publish, async, wildcard topics)
- [ ] **1.7** Write `tests/test_runtime.py` (lifecycle, module init, shutdown order)

### Phase 2: Consolidation (Major issues)

- [ ] **2.1** Delete `bin/rosclaw` — keep only `src/rosclaw/cli.py`
- [ ] **2.2** Replace `RobotState` in `data/flywheel.py` with import from `core/types.py`
- [ ] **2.3** Replace `RobotState` in `mcp/ur5_server.py` with import from `core/types.py`
- [ ] **2.4** Fix `__init__.py` to use lazy imports for all optional modules (Section 6.7)
- [ ] **2.5** Extract `LLMProvider` ABC from `DeepSeekClient` in `agent_runtime/llm_provider.py`
- [ ] **2.6** Write `tests/test_lifecycle.py` and `tests/test_mcp_hub.py`

### Phase 3: Missing Modules

- [ ] **3.1** Create `src/rosclaw/mcp_drivers/base.py` with `RobotDriver` ABC (Section 9.1)
- [ ] **3.2** Create `src/rosclaw/mcp_drivers/simulated_driver.py` (MuJoCo-only, no ROS 2)
- [ ] **3.3** Refactor `mcp/ur5_server.py` to use `RobotDriver` interface
- [ ] **3.4** Create `src/rosclaw/skill_manager/` package (Section 9.2)
- [ ] **3.5** Implement `skill.py` (Skill dataclass) and `registry.py` (SkillRegistry)
- [ ] **3.6** Wire SkillRegistry to EventBus (`praxis.completed` → skill extraction)

### Phase 4: SeekDB + Testing

- [ ] **4.1** Define `SeekDBClient` interface in `memory/seekdb_client.py`
- [ ] **4.2** Implement in-memory mock for testing
- [ ] **4.3** Write `tests/test_eurdf_parser.py` using `specs/ur5e.xml`
- [ ] **4.4** Write `tests/test_practice.py` and `tests/test_memory.py`
- [ ] **4.5** Write `tests/test_e2e_pipeline.py` (MCPHub → EventBus → Firewall → Response)
- [ ] **4.6** Create `docker-compose.yaml` with SeekDB service

### Acceptance Criteria

```bash
# All tests pass
cd rosclaw-v1.0 && python -m pytest tests/ -v

# No import errors
python -c "import rosclaw; print(rosclaw.__version__)"

# CLI works without robot model
rosclaw start --robot-id test_robot

# Simulated driver works end-to-end
python -c "
from rosclaw.mcp_drivers.simulated_driver import SimulatedDriver
driver = SimulatedDriver('src/rosclaw/specs/ur5e.xml')
import asyncio
result = asyncio.run(driver.move_joints([0.1, 0.0, 0.0, 0.0, 0.0, 0.0]))
assert result['success']
"
```

---

## Appendix A: File Inventory

```text
src/rosclaw/
├── __init__.py              (80 LOC)  - Package root, eager imports
├── cli.py                   (80 LOC)  - CLI entry point
├── core/
│   ├── __init__.py          (22 LOC)
│   ├── event_bus.py        (162 LOC)  - Pub/sub bus
│   ├── lifecycle.py        (118 LOC)  - State machine mixin
│   └── runtime.py          (243 LOC)  - Central orchestrator
├── agent_runtime/
│   ├── __init__.py          (14 LOC)
│   ├── mcp_hub.py          (308 LOC)  - MCP tool server
│   └── ai_collaboration.py (205 LOC)  - DeepSeek client
├── e_urdf/
│   ├── __init__.py          (16 LOC)
│   └── parser.py           (355 LOC)  - URDF + extensions parser
├── firewall/
│   ├── __init__.py          (14 LOC)
│   └── decorator.py        (438 LOC)  - MuJoCo validation (BEST)
├── memory/
│   ├── __init__.py          (10 LOC)
│   └── interface.py         (54 LOC)  - Placeholder (in-memory list)
├── practice/
│   ├── __init__.py          (10 LOC)
│   └── recorder.py          (77 LOC)  - Event-driven recorder
├── data/
│   ├── __init__.py          (34 LOC)
│   ├── flywheel.py         (413 LOC)  - Event-driven capture
│   └── ring_buffer.py      (302 LOC)  - High-perf circular buffer
├── swarm/
│   ├── __init__.py          (10 LOC)
│   └── manager.py           (69 LOC)  - Stub (agent registry only)
├── mcp/
│   ├── __init__.py           (4 LOC)
│   └── ur5_server.py       (650 LOC)  - ROS 2 + MCP server
├── mcp_drivers/
│   └── __init__.py           (8 LOC)  - Empty
└── specs/
    └── ur5e.xml                      - MuJoCo model

tests/
├── test_firewall.py        (361 LOC)  - 17 tests, good coverage
├── test_data_layer.py      (327 LOC)  - 17 tests, good coverage
└── test_mcp_server.py      (377 LOC)  - 14 tests, schema-only
```

## Appendix B: Vision Documents Referenced

| 文档 | 核心主张 |
|------|----------|
| `rosclaw_v1.0见解一.md` | 统一工程架构，4 大公共基础设施，9 Sprint 规划 |
| `rosclaw_v1.0见解二.md` | Monorepo 微内核总线，5 Sprint 规划，rosclaw-compose 部署 |
| `rosclaw_哲学思辨.md` | Grounding 哲学定位，6 大引擎命名，对外宣言 |
