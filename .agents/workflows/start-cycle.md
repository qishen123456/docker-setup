# Start Development Cycle

> Antigravity Workflow - 在 Agent 输入框输入 `/start-cycle` 触发。
> 将全栈研发专家团 SOP 映射为 Antigravity 可执行的分阶段流水线。
> 完整角色 prompt 见 `.ai-team/agents/`，完整配置见 `.ai-team/team-config.yaml`。

## Description

对用户提出的需求，按全栈研发专家团标准 SOP 分阶段执行。
存量项目（SmartAsk 本身）必须从 Phase 0 开始。

## Steps

### Step 1: 判定工作流类型

读取用户需求，判定走哪条路径：
- 只问一个专业问题 -> 单点直调（查 `.ai-team/team-config.yaml` 的 routing_table）
- ≤10 文件小需求 -> 快速模式（跳过 PRD/架构/审查）
- 明确缺陷修复 -> BugFix 路径
- 中大型多模块需求 -> 标准 SOP（下面 Step 2-7）
- 已有项目加功能/重构 -> 增量模式（同样从 Phase 0 开始）
- 只要中间产物 -> 部分工作流

判定原则：**宁可轻，不要重。**

### Step 2: Phase 0 - 项目公约勘察（存量项目必走）

读取 `.ai-team/agents/fullstack-dev-architect.md` 作为角色 prompt。
要求 AI 先通读 SmartAsk 现有代码结构，输出项目公约摘要（≤1页），包含：
1. 技术栈实况（语言/框架/版本/依赖管理）
2. 目录约定（代码放哪、命名规则、模块划分）
3. 既有模式（错误处理、日志、配置、鉴权、数据访问各怎么写，给代表性文件路径）
4. 质量基线（有无 lint/格式化/测试/CI，命令是什么）
5. 禁区（哪些文件自动生成、哪些历史遗留不该动）

如果项目根目录已有 `AGENTS.md`，以其为准并注明来源。

### Step 3: Phase 1 - 需求定义

读取 `.ai-team/agents/fullstack-dev-pm.md` 作为角色 prompt。
输出精简 PRD：产品目标 + 用户故事 + P0/P1/P2 需求池 + Given-When-Then 验收标准 + 待确认问题。
有阻塞级待确认问题时暂停，向用户澄清后再继续。

### Step 4: Phase 2 - 设计与架构

读取 `.ai-team/agents/fullstack-dev-designer.md` 和 `.ai-team/agents/fullstack-dev-architect.md`。
两人都拿到 PRD 全文，并行产出：
- 设计师：信息架构、页面流、Design Token、组件清单
- 架构师：技术选型、模块划分、数据模型、**接口契约**、文件清单、任务列表

合并后给接口契约打版本号 `CONTRACT v1` 并冻结。

### Step 5: Phase 3 - 编码实现

读取 `.ai-team/agents/fullstack-dev-frontend.md` 和 `.ai-team/agents/fullstack-dev-backend.md`。
各自拿到：PRD + 架构方案 + 带版本号的接口契约 + 任务子集 + 项目公约摘要。
两人 prompt 里的契约必须逐字一致。

### Step 6: Phase 4 - 代码审查

读取 `.ai-team/agents/fullstack-dev-reviewer.md`。
附上接口契约、前后端实现摘要与文件清单。
输出分级问题清单（BLOCKER/MAJOR/MINOR/NIT）+ `REVIEW: PASS/CONDITIONAL/REJECT`。
REJECT 则回流修复，最多 2 轮。

### Step 7: Phase 5 - 测试验证

读取 `.ai-team/agents/fullstack-dev-qa.md`。
附上代码摘要、文件清单和 Phase 4 审查报告。
必须真实执行测试命令，记录真实输出。输出测试报告 + 缺陷路由 + 质量结论。

### Step 8: Phase 6 - 部署交付（可选）

读取 `.ai-team/agents/fullstack-dev-devops.md`。
产出 Dockerfile / compose / CI 配置 / 环境变量清单 / 部署与回滚步骤。
用户说"不用部署"时跳过。

### Step 9: 汇总交付

输出交付说明：TL;DR + 交付概览（含审查结论和测试通过率）+ 文件清单 + 角色贡献 + 下一步建议。
有遗留问题如实标注，不许粉饰。
