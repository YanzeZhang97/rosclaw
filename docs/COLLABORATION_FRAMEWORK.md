# ROSClaw v1.0 双实例协作框架

## 角色分工

### rosclaw (执行者)
- 负责：代码实现、模块填充、测试编写
- 输入：读取 ARCHITECTURE_REVIEW.md 获取改进建议
- 输出：实施结果写入 COLLABORATION_LOG.md

### rosclaw_qwen (架构师/审查者)
- 负责：架构审查、代码质量检查、设计建议
- 输入：读取所有源码和文档
- 输出：审查报告写入 ARCHITECTURE_REVIEW.md

## 协作流程

```
rosclaw_qwen          共享文件系统            rosclaw
    |                                            |
    |-- 1. 读取所有源码+文档                      |
    |-- 2. 生成 ARCHITECTURE_REVIEW.md --------->|
    |                                            |-- 3. 读取审查报告
    |                                            |-- 4. 按建议实施代码
    |<-- 5. 读取 COLLABORATION_LOG.md <----------|
    |-- 6. 验证实施质量，更新审查意见 --------->|
    |                                            |-- 7. 继续修复/优化
```

## 文件约定

- `docs/ARCHITECTURE_REVIEW.md` - rosclaw_qwen 输出，rosclaw 输入
- `docs/COLLABORATION_LOG.md` - rosclaw 输出，rosclaw_qwen 输入
- `docs/DESIGN_DECISIONS.md` - 双方共同维护的重要设计决策

## 当前任务状态

- [IN_PROGRESS] rosclaw_qwen: 全面架构审查
- [PENDING] rosclaw: 按审查报告实施改进
- [PENDING] 联合验收: pytest 全部通过
