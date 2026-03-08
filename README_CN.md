# nano_agent_evo_20260308_000429

[nano_agent_team_selfevolve](https://github.com/nanoAgentTeam/nano_agent_team_selfevolve) 的演化会话仓库。

## 项目背景

`nano_agent_team_selfevolve` 是一个基于**黑板架构**的多 Agent 协作框架——Agent 通过共享文件协作，"监督者"（watchdog）负责规划任务，工作 Agent 按角色认领。框架内置了**自进化引擎**：一个自动化循环，由"进化架构师"Agent 调度子 Agent（研究员、审计员、开发者、测试员、审查员）来改进框架自身。

本仓库就是一次这样的演化会话——由 `evolve_session.sh` 创建的隔离克隆，运行了 3 轮自主演化。

## 演化配置

| 参数 | 值 |
|------|------|
| 脚本 | `evolve_session.sh` |
| 轮数 | 3 |
| 模型 | `qwen/qwen3.5-plus`（阿里通义千问 3.5 Plus）|
| 基准分支 | `original`（会话启动时上游 `main` 的快照）|
| 隔离方式 | 全新 GitHub 仓库克隆，独立 venv |
| 总耗时 | 62 分 19 秒 |
| 成绩 | **2 PASS / 1 FAIL**（通过率 66%）|

### `evolve_session.sh` 工作流程

1. 在组织下创建新 GitHub 仓库
2. 将当前 `main` 分支推送为种子代码
3. 本地克隆，创建 `original` 分支作为基准
4. 安装全新 Python venv
5. 运行 N 轮 `python main.py --evolution`
6. 每轮结束后：检查判定结果，推送所有分支到 GitHub
7. 最终：将最后一个 PASS 分支提升为 `main`（force-push）

## 演化做了什么

### 第 1 轮 — 通过：集成 ActivateSkillTool 和 ArxivSearchTool（20 分 49 秒）

**分支：** `evolution/r1-20260308_000525` | **类型：** 集成（INTEGRATION）

审计员扫描代码库后发现两个工具作为源文件存在但未接入运行系统：

- **`ActivateSkillTool`** — 已存在于 `backend/tools/activate_skill.py`，甚至已在 `tool_registry.py` 中注册，但 `main.py` 和 `agent_bridge.py` 的 `add_tool()` 调用中从未添加。演化加了两行接线代码。**边际价值** — 代码本来就在那里。
- **`ArxivSearchTool`** — 存在于 `backend/tools/arxiv_search.py`，但有一个真实 bug：`class ArxivSearchTool:` 没有继承 `BaseTool`，导致与工具系统不兼容。演化修复了继承关系、完成注册和接线。**真正的修复**。
- 新增 15 个集成测试 `tests/test_tools_integration.py`。

**变更文件：** `backend/llm/tool_registry.py`、`backend/tools/arxiv_search.py`、`main.py`、`src/tui/agent_bridge.py`、`tests/test_tools_integration.py`、`docs/system_design.md`

### 第 2 轮 — 通过：会话成本追踪与导出工具（16 分 33 秒）

**分支：** `evolution/r2-20260308_002612` | **类型：** 新功能（FEATURE）

从零创建了 `backend/tools/session_cost_export.py`（281 行）——可追踪、汇总和导出每会话的 token 用量和费用数据。同时在 TUI 中添加了 `/cost` 斜杠命令。

**诚实评估：** 该工具是一个**有数据结构但没有数据来源的空壳**。它定义了主流模型（GPT-4、Claude、Gemini、Qwen）的费用计算逻辑和导出格式（JSON/CSV），但框架中没有中间件在实际收集 LLM 响应中的 token 用量。调用 `/cost` 永远返回 "No cost data recorded"。需要编写 `CostTrackerMiddleware` 才能让该工具产生实际输出。

**变更文件：** `backend/tools/session_cost_export.py`（新）、`backend/llm/tool_registry.py`、`main.py`、`src/tui/agent_bridge.py`、`src/tui/slash_commands.py`、`tests/test_session_cost_export.py`（新）、`docs/system_design.md`

### 第 3 轮 — 失败：Agent 级成本仪表盘组件（24 分 32 秒）

**分支：** `evolution/r3-20260308_004252` | **类型：** 新功能（被拒）

试图修改 `src/tui/screens/monitor.py` 以添加成本仪表盘组件。质量门控拒绝了该变更，因为该文件在 `evolution_gate.py` 的 `PROTECTED_DIRS` 列表中。**安全系统按设计运作。**

## 调试与验证

将演化结果（第 1 轮 + 第 2 轮）合并回上游仓库后，我们进行了验证：

| 检查项 | 结果 | 备注 |
|--------|------|------|
| 工具导入 | 通过 | 3 个工具均可正常导入和实例化 |
| 单元测试 | 29/29 通过 | 两个测试文件全部通过 |
| 入口接线 | 通过 | `main.py` 和 `agent_bridge.py` 均加载新工具 |
| ArxivSearchTool 功能 | **可用** | 调用 arXiv API，返回论文结果 |
| ActivateSkillTool 功能 | **可用** | 在技能注册表加载后可激活技能 |
| SessionCostExportTool 功能 | **不可用** | 无数据来源——需要 CostTrackerMiddleware |
| `/cost` TUI 命令 | **不可用** | 永远显示空（同一根本原因）|

### 已知未修复问题

`SessionCostExportTool` 需要一个 `CostTrackerMiddleware` 来拦截 LLM 响应并将 token 用量记录到 `session.metadata` 中。现有的 `ExecutionBudgetManager`（`backend/llm/middleware.py`）管理的是迭代次数限制，不追踪 token 数量。缺少该中间件时，第 2 轮的产出在结构上完整但实际上无法工作。

### 做得好的地方

- 演化的质量门控（导入检查、受保护文件守护、重复扫描）成功阻止了第 3 轮的问题变更
- ArxivSearchTool 的 `BaseTool` 继承 bug 是一个真正的发现和修复
- 所有生成的测试都有意义且全部通过
- 没有引入代码破坏性问题

### 做得不好的地方

- 第 1 轮花了 20 分钟来添加本质上只有 2 行 `add_tool()` 接线的 `ActivateSkillTool`
- 第 2 轮构建了导出工具却缺少数据收集层，产出了一个不可用的功能
- 演化系统缺乏跨会话记忆——无法知道之前的会话已经尝试过类似工作

## 分支结构

```
original          ← 会话启动时上游 main 的快照
  └── evolution/r1-20260308_000525   ← PASS: 工具集成
        └── evolution/r2-20260308_002612   ← PASS: 成本导出工具（已提升为 main）
              └── evolution/r3-20260308_004252   ← FAIL: 仪表盘组件（被拒）
main              ← 指向 r2（最后一个 PASS）
```

## 报告

详细的每轮报告在 `evolution_reports/` 目录中：
- `round_1_20260308_002410.md`
- `round_2_2026-03-08T00-41-03Z.md`
- `round_3_20260308_004252.md`
