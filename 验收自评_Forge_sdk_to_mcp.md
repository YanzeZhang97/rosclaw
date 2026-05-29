# ROSClaw v1.0 模块验收自评

## 模块名称：Forge / sdk_to_mcp（Asset Compiler）

## 负责人：Claude Opus 4.8 (rosclaw-forge 重构 + sdk_to_mcp 测试补齐)

## 当前Commit：
- `sdk_to_mcp` 仓库：`570c794` (rosclaw-forge v1.0 + sandbox validation + install logic)
- `rosclaw-v1.0` 仓库：`beadb19` (sdk_to_mcp 测试补齐，100% coverage)

---

## 一、P0 阻塞项自评

| P0项 | 当前状态 | 证据/说明 |
|------|----------|-----------|
| L0: 从零安装启动 | ⚠️ 部分 | rosclaw-forge 有 `pip install -e .` 能力，但**无 install.sh 脚本**；rosclaw init/start 不在本模块范围 |
| L1: Claude Code MCP接入 | ⚠️ 部分 | MCP Tools 入口已写 (`compile_embodied_asset_bundle`, `validate_embodied_asset_bundle`, `publish_embodied_asset_bundle`)，但**Claude Code 真实调用生成 bundle 未验证** |
| L2: Event Bus真实工作 | ✅ 通过 | rosclaw-forge 内部不直接耦合 EventBus，通过 CLI/Skill/MCP Tool 暴露接口，符合模块边界原则 |
| L3: Practice记录全过程 | ❌ 未通过 | **Forge 编译过程未写入 Practice episode**，无 `rosclaw practice list` 命令记录编译事件 |
| L4: Memory回答真实问题 | ❌ 未通过 | **Memory 未记录 Forge 生成的新能力 bundle**，无知识沉淀链路 |
| L5: How给出恢复策略 | ❌ 未通过 | **Critic 反馈未接入 How 模块生成恢复建议**，失败时无自动修复策略生成 |

---

## 二、场景验收自评

| 场景 | 当前状态 | 证据/说明 |
|------|----------|-----------|
| A: 小车PID运动控制 | ❌ 不涉及 | 非本模块范围 |
| B: 机械臂reach | ❌ 不涉及 | 非本模块范围 |
| C: 机械臂抓取红杯子 | ❌ 不涉及 | 非本模块范围 |
| D: Unitree巡检 | ❌ 不涉及 | 非本模块范围 |
| E: G1人形行走 | ❌ 不涉及 | 非本模块范围 |
| **F: Forge自扩展** | **⚠️ 部分** | 见下详述 |

### 场景 F（Forge自扩展）详细自评

| 验收指标 | 状态 | 证据 |
|----------|------|------|
| 1. Forge 能读取 SDK 文档 | ✅ | `IngestorPipeline` 可读取 ROS2 interfaces、SDK docs、e-URDF |
| 2. 能生成 bundle | ✅ | `EmbodiedBundleBuilder` 生成 8 文件 bundle (mcp_server, manifests, tests, CI, README, metadata) |
| 3. Critic 能检查 async/schema/safety/preemption/firewall hook | ✅ | `CriticAgent` 检查 6 项 ROSClaw-Native 标准，E2E 验证可发现缺失 |
| 4. validate 能通过 | ✅ | `BundleValidator` + `SandboxValidator` 验证结构和 sandbox 合规性 |
| 5. install --staging 能成功 | ✅ | `install_bundle(target="staging")` 实现复制到 `~/.rosclaw/staging/` 并写 `install_manifest.json` |
| 6. Claude Code 能看到新 MCP tool | ❌ | **未验证**：需要真实 LLM 生成可通过 critic 的代码，当前 mock LLM 生成的 placeholder 被 critic 拒绝 |
| 7. Practice 记录 forge 过程 | ❌ | **未实现**：ForgeEngine 未接入 Practice 记录 compilation episode |
| 8. Memory 记录新增能力 | ❌ | **未实现**：生成 bundle 后未写入 Memory/SeekDB |

### 场景 F 关键缺口
- **自修复未闭环**：Critic 能发现错误，但 mock LLM 无法自动修复（需真实 DeepSeek/OpenAI）
- **物理启用未验证**：sandbox validate → enable_physical_execution 链路已写，但未在真实机器人上验证
- **无 Practice/Memory 集成**：Forge 过程是黑盒，系统无法回答"刚才生成了什么能力"

---

## 三、已知缺口（必须诚实填写）

1. **Auto-heal 未验证**：Critic 发现缺失 async/firewall/TF2/preemption 后，Generator 无法自动修复（mock LLM 无真实生成能力）。需接入真实 LLM 验证 5-retry 内通过。
2. **Claude Code 真实闭环未跑**：MCP Tools 入口存在，但缺少一次"Claude Code → Forge → Bundle → Install → Sandbox"的端到端验证记录。
3. **Practice/Memory/How 集成缺失**：Forge 编译过程未作为 episode 记录，失败时无 How 恢复建议，成功时无 Memory 沉淀。
4. **真实机器人验证缺失**：Unitree Go2 / RealSense SDK 文档未实际用于生成并通过 sandbox 验证的 bundle。
5. **文档缺口**：rosclaw-forge 缺少面向用户的 README（安装、配置 LLM API key、快速开始）。

---

## 四、预计修复工时

| 任务 | 工时 | 说明 |
|------|------|------|
| 接入真实 LLM 验证 auto-heal | 4h | 配置 DeepSeek API key，运行 compile，验证 critic→feedback→generator 闭环 |
| Claude Code 真实闭环验证 | 4h | 通过 MCP Tool 调用 compile，生成 bundle，install --staging，enable_physical --approve |
| Practice/Memory/How 集成 | 6h | ForgeEngine 编译前后 publish EventBus 事件，Practice 记录 episode，Memory 写入新能力 |
| 真实机器人 SDK 验证（Go2/RealSense） | 4h | 用真实 SDK 文档生成 bundle，通过 sandbox validate |
| 补齐文档（README + 配置指南） | 3h | 安装、LLM 配置、CLI 用法、安全边界说明 |
| **总计** | **21h** | 约 2.5 人天 |

---

## 五、需要其他模块配合的事项

1. **Practice 模块**：需要 Practice 模块提供 `record_forge_compilation()` 接口或 EventBus topic， Forge 才能写入编译 episode。
2. **Memory 模块**：需要 Memory 提供 `store_capability_bundle(bundle_manifest)` 接口， Forge 生成 bundle 后才能沉淀知识。
3. **How 模块**：需要 How 提供 `generate_recovery_hint(critic_feedback)` 接口， Critic 拒绝后才能生成修复建议。
4. **Runtime/Agent**：需要 Runtime 在启动时加载 staging 目录的 bundle， Claude Code 才能看到新生成的 MCP tools。
5. **LLM Provider 抽象**：当前 LLM client 直接耦合 DeepSeek/OpenAI，建议其他模块提供统一的 `LLMProvider` ABC（已知问题 K-01）。

---

## 六、模块当前评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 代码完成度 | 8/10 | 核心编译器、打包器、验证器、安装器、安全边界均已实现 |
| 测试通过 | 9/10 | rosclaw-forge E2E 9/9 通过；sdk_to_mcp 43/43 通过，100% coverage |
| 文档 | 4/10 | 代码注释充分，但缺少用户-facing README 和配置指南 |
| 用户闭环 | 5/10 | CLI/Skill/MCP 入口齐全，但未验证 Claude Code 真实调用 |
| **模块综合评分** | **6.5/10** | 功能开发基本完成，集成验证和真实 LLM 闭环待补 |

---

## 七、主管初评对照

主管初评中 `Forge/sdk_to_mcp` 为 **6/10**，与本自评 **6.5/10** 基本一致。

主管指出的缺口：
- ✅ **Claude Code 调用生成 bundle 未验证** → 承认，已列入修复计划（4h）
- ✅ **无 critic validation** → 部分承认：critic 逻辑已写且 E2E 验证能发现错误，但 auto-heal 闭环未验证

本模块不属于 P0 阻塞项的直接责任方（P0 阻塞主要是 How/Practice/install.sh/Claude Code 闭环），但 **Scenario F（Forge自扩展）是 v1.0 发布的必要场景**，必须在本模块内补齐上述 21h 工作量才能通过。

---

**填表日期**: 2026-05-29
**填表人**: Claude Opus 4.8
