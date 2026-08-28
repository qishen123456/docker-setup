# AGENTS.md — SmartAsk 项目 AI 协作公约

> 任何在本仓库工作的 AI 助手（WorkBuddy / Claude Code / Cursor / Trae / Windsurf 等）**必读本文件**。
> 本文件是全栈研发专家团（fullstack-dev-team）SOP 在 SmartAsk 项目内的落地公约。
> 机器可读的完整配置见 `.ai-team/team-config.yaml`，角色 prompt 见 `.ai-team/agents/`。

---

## 一、项目速写

**SmartAsk** 是一个 NL2SQL「问数」系统：用户用自然语言提问，系统转成 SQL 查询数据库并返回结果。

| 层 | 技术 | 关键模块 |
|---|---|---|
| 后端 | Flask 3.0.3 (端口 5002) + Vanna[chromadb] 0.7.9 | `backend/app.py`(入口,18 blueprint) · `backend/controllers/smart_chat.py`(问数主路由,同步+SSE) · `backend/ask_flow/controller.py`(basic/advanced引擎开关) · `backend/four_agent_ask.py`(**9063行,单类FourAgentAskService/156方法**,四智能体流水线+硬编码规则SQL引擎) |
| 前端 | Vue 3.5 + Vite 8 + Element Plus + ECharts | `frontend/src/` (views/components/api) |
| 配置 | `config/` 下 16 json + 9 md | datasetPolicies · feature_flag(advanced_ask_flow) · advancedRoles(默认super_admin) |
| 数据 | MySQL/PostgreSQL + ChromaDB(向量) | `docker/*.sql`(建表) |
| 测试 | pytest + pytest-asyncio | `backend/requirements.txt` |
| 部署 | docker-compose | `docker-compose.yml` · `docker/` · `deploy.sh/.ps1` |

**已知架构事实**（改任何东西前必须知道）：
- 默认 advanced 关闭，流量全走 basic 引擎
- SSE 本质同步（单 worker 线程 + 内存 queue），多 worker 部署会丢确认会话状态
- `four_agent_ask.py` 是 9063 行单类（156 方法），但 **58% 零实例状态依赖**（35 方法 / 5215 行），三套规则 SQL 引擎 2112 行实例属性引用=0，拆分成本远低于直觉判断
- 改动边界：`backend/ask_flow/contracts.py` 的 AskRequest/ConfirmRequest/FlowDecision
- **安全护栏方向反置**：approved=True 的 SQL 不校验直落执行，approved=False 的才过校验，物理执行点零护栏（详见 `docs/audit/2026-08-06_final-audit-report.md` A-01）
- **LLM 状态共享**：模块级单例 + 每请求写共享 `_preferred_model_id`，并发请求互相覆盖模型选择（详见审计报告 A-03/SD-1）
- **部署不完整**：`angel_group_data` 表仅靠 docker init 首次执行建表，bootstrap 迁移无对应项；三张 bs_* 表不在任何迁移文件中，唯一定义在请求处理器内联 DDL（详见审计报告 L-01/L-02）
- **语义层空转**：`backend/data/dataset_dimension_profiles.json` 不存在，31 个调用点全部返回 None，路由层级判定和实体消解全部退化（详见审计报告 A-02）
- **`_connect()` 无连接池**：44 处裸调用 / 13 文件 / 3 套独立定义，`backend/services/` 和 `backend/repositories/` 目录不存在

---

## 二、工作准则（铁律）

1. **只读优先** — 理解项目后再动手。不确定时多读代码，少改代码。
2. **最小变更** — 存量项目上只改必须改的，禁止顺手重写无关代码。改一个函数不要重构整个文件。
3. **入乡随俗** — 新代码要像这个项目原本的一部分：用项目既有的错误处理模式、日志格式、命名约定、配置读取方式。不要引入项目没用过的新模式或新依赖，除非有充分理由并说明。
4. **上帝文件慎改** — `four_agent_ask.py` 已 1 万+行。改动前先定位精确位置，改后必须确认不影响其他分支。
5. **配置优先于代码** — 能用 `config/` 下的配置解决的，不要硬编码进代码。
6. **不预设技术栈** — SmartAsk 已定栈（Flask/Vue/Vanna），在 SmartAsk 上工作时遵循现有栈，不擅自换栈。新项目才走架构师决策树。

---

## 三、调用专家团

本仓库自带一套 9 角色全栈研发专家团，框架无关，任何 AI 工具或代码均可调用。

### 方式一：AI 工具读 prompt 文件

```
.ai-team/
├── team-config.yaml          # 机器可读配置（角色注册/SOP/路由/门禁）
├── agents/                   # 9 个角色的纯 prompt 模板（无 WorkBuddy frontmatter）
│   ├── fullstack-dev-team-lead.md   # 主理人（含完整 SOP）
│   ├── fullstack-dev-pm.md
│   ├── fullstack-dev-designer.md
│   ├── fullstack-dev-architect.md
│   ├── fullstack-dev-frontend.md
│   ├── fullstack-dev-backend.md
│   ├── fullstack-dev-reviewer.md
│   ├── fullstack-dev-qa.md
│   └── fullstack-dev-devops.md
└── README.md                 # 资产说明与同步方式
```

需要某角色能力时，读取对应 `agents/*.md`，将其作为 system prompt 注入即可。主理人文件包含完整 SOP 与路由表，可独立驱动整个流程。

### 方式二：代码加载 team-config.yaml

```python
import yaml
cfg = yaml.safe_load(open('.ai-team/team-config.yaml'))
# 获取角色 prompt
member = next(m for m in cfg['members'] if m['id'] == 'fullstack-dev-backend')
prompt = open(f".ai-team/{member['prompt_file']}").read()
# 获取 SOP 阶段
phases = cfg['sop']['phases']
# 获取路由表
route = cfg['routing_table']
```

---

## 四、SOP 速查

收到请求后**第一步判定走哪条工作流**：

| 场景 | 走哪条 |
|---|---|
| 只问一个专业问题 | 🎯 单点直调（查 routing_table） |
| ≤10 文件的小需求 | ⚡ 快速模式 |
| 明确缺陷修复 | 🔧 BugFix（触及鉴权/数据/契约时插审查） |
| 中大型多模块需求 | 🏗️ 标准 SOP（Phase 0-6） |
| 已有项目加功能/重构 | 🔄 增量模式（**必走 Phase 0**） |
| 只要中间产物 | 📋 部分工作流 |

**标准 SOP（在 SmartAsk 上几乎都是增量模式）**：

```
Phase 0  架构师 → 项目公约摘要（存量项目必走，不许省）
Phase 1  PM → PRD
Phase 2  设计师 ∥ 架构师 → 设计规范 ∥ 架构+契约(v1冻结)+任务列表
Phase 3  前端 ∥ 后端 → 实现（契约逐字一致）
Phase 4  审查员 → 审查报告 REVIEW: PASS/CONDITIONAL/REJECT
Phase 5  QA → 测试报告+缺陷路由
Phase 6  DevOps → 部署+回滚
```

判定原则：**宁可轻，不要重。** 大多数请求落在单点直调或快速模式。走重流程前先问自己："这真的需要 PRD 和架构设计文档吗？"

---

## 四点五、两套专家团队的区别与分工

项目拥有两套 **定位不同、消费者不同、运行环境不同** 的 AI 专家资产：

| 维度 | `.ai-team/` 代码开发专家团 | `.ai-data/` 数据分析专家团 |
|---|---|---|
| 路径 | `.ai-team/` | `.ai-data/` |
| 定位 | 帮 SmartAsk 写代码 | 帮 SmartAsk 做数据分析/研究/金融分析 |
| 消费者 | 人 + IDE（开发者本人） | SmartAsk 系统本身（集成到四智能体流水线） |
| 运行环境 | 开发态 — 人在 IDE 中通过 WorkBuddy/Claude Code/Cursor 调度 | 生产态 — 作为系统组件被 four_agent_ask.py 调用 |
| 角色数 | 9 | 10 |
| Agent ID 前缀 | `fullstack-dev-*` | `data-team-*`（统一前缀，防冲突） |
| 当前状态 | 已可用 | 知识储备中，尚未集成到系统 |
| 质量门禁 | 7 道（SOP 全链路） | 按数据场景定制（数据质量/分析严谨性/可视化规范） |

**为什么不能简单对齐配置？**

- 代码团队门禁是 **契约冻结 → 代码审查 → 测试通过 → 部署可回滚**，面向"代码交付质量"
- 数据团队门禁是 **数据完整性 → 分析方法严谨性 → 结论可溯源 → 可视化规范**，面向"分析结论质量"
- 两者共享 `context_rules`（三级传递）和 `blocked_format`（阻塞上报格式），但门禁内容各自设计

### .ai-team/ 使用方式

需要改代码时，读取 `.ai-team/agents/<角色>.md` 作为 system prompt 注入。主理人文件 `fullstack-dev-team-lead.md` 包含完整 SOP 与路由表。详见 `.ai-team/README.md`。

**非 WorkBuddy IDE（Claude Code/Cursor）降级用法**：见 `.ai-team/agents/fullstack-dev-team-lead.md` 末尾"跨 IDE 降级模式"章节。

### .ai-data/ 使用方式

`.ai-data/` 从 WorkBuddy 平台 12 个专家包（70 角色）整合为 **10 个各司其职的专家**：主理人、数据工程师、趋势分析师、结构分析师、异常侦察员、算法工程师、行业研究员、深度研究员、金融分析师、可视化设计师。详见 `.ai-data/README.md` 和 `.ai-data/team-config.yaml`。

**集成方向**：SmartAsk 四智能体流水线中，Agent4（业务分析官）是分析能力薄弱点。数据团队的三视角分析（趋势/结构/异常）是对 Agent4 的增强方向。集成设计见 `docs/data-analysis-integration-design.md`。

**非 WorkBuddy IDE 降级用法**：见 `.ai-data/agents/team-lead.md` 末尾"跨 IDE 降级模式"章节。

### 跨团队交接

两个团队虽然定位不同，但存在交接场景（如数据团队产出看板设计 → 代码团队实现前端）。交接协议定义在两个 `team-config.yaml` 的 `cross_team` 配置块中。

---

## 五、上下文与质量规则速查

**上下文三级传递**：
- **L1 逐字全文**：接口契约、Design Token、验收标准、项目公约摘要 → 一字不改复制
- **L2 结构化摘要**：代码产出、无关PRD章节、上轮报告 → 保留文件清单+结论，去掉过程
- **L3 按需索取**：历史讨论、被否方案 → 默认不传

**质量门禁**：公约完备(Phase0) → 需求完整(1) → 契约完备(2) → 实现自检(3) → 审查门禁(4) → 测试门禁(5) → 部署门禁(6)。每道门最多 2 轮，不通过如实标注遗留，**不许假装通过**。

**先审后测**：静态审查在动态测试之前。带着漏洞的代码不送去跑测试。

---

## 六、SmartAsk 专属约定

1. **four_agent_ask.py** — 改前先全局搜索目标函数/规则的位置，确认所有调用方。改后跑 `pytest`。不要在这个文件里新增大类，尽量外移到 `ask_flow/` 或 `ask_engine_*.py`。
2. **配置体系** — 新增数据集策略写 `config/` 下 json；功能开关走 feature_flag；角色权限写 advancedRoles。不要硬编码。
3. **SSE 路由** — 改 `controllers/smart_chat.py` 的 SSE 逻辑时，注意帧序列（ready/trace/summary/heartbeat/result/done）和内存 queue 的单线程约束。
4. **前端** — Vue3 `<script setup>` + Element Plus 组件 + ECharts 图表。新增页面放 `views/`，复用组件放 `components/`，API 调用走 `api/` 层封装。
5. **测试** — `pytest`，新功能至少配单测。跑测试：`cd backend && python -m pytest`。
6. **部署** — `docker-compose up`。改 `docker-compose.yml` 或 `docker/*.sql` 后需重建。

---

## 七、同步与维护

- 专家团源头：`~/.workbuddy/plugins/marketplaces/my-experts/plugins/fullstack-dev-team/`
- 本目录是框架无关副本，专家包变更后运行 `scripts/sync-from-expert-pack.sh` 同步
- 新增角色时，先在专家包侧按 `dev-team-blueprint` 扩展流程操作，再同步到本目录
- **配置校验**：改动 `.ai-team/` 或 `.ai-data/` 的配置后，运行 `python3 scripts/verify-expert-teams.py` 校验 YAML 语法、prompt_file 路径存在性、Agent ID 一致性、旧 ID 残留、cross_team 对称性

---

## 八、文档权威源声明（2026-08-28）

- **AI 行为规则唯一权威源：`.agents/`**（rules + skills）。`.trae/rules/` 是其同步副本（由 `scripts/sync-ide-rules.ps1` 生成），**禁止手改**；改规则只改 `.agents/rules/` 后重跑脚本。
- **专家团资产**：`.ai-team/`（代码开发）、`.ai-data/`（数据分析），见第四节。
- **人类文档**：`docs/`；历史方案/决策类报告归档在 `docs/archive/`。
- **`.qoder/`** 为 Qoder 可再生产物，已于 2026-08-28 移除并加入 `.gitignore`，**禁止作为事实源引用**（内容为 2026-08-08 过期快照，可从 git 历史找回）。
- **`.workbuddy/`** 为 WorkBuddy 会话产物，不进 git；只保留 `memory/` 工作日志，方案/决策类报告一律归档 `docs/archive/`。
- **禁止在多处维护重复文档**；新增规则只改 `.agents/`。
- 治理方案全文见 `docs/ai-docs-consolidation-plan.md`。
