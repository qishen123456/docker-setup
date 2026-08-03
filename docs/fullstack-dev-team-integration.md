# 全栈研发专家团集成落地方案

> 将优化后的 `fullstack-dev-team` 专家团（9 角色 SOP 驱动）集成到 SmartAsk 项目，
> 使其在项目代码内即可被 AI 工具和代码调用，不依赖 WorkBuddy 平台运行时。

---

## 一、已完成的专家包优化

### 1.1 新增第 9 角色：代码审查工程师

| 字段 | 值 |
|---|---|
| Agent ID | `fullstack-dev-reviewer` |
| 花名 | 贺明察（He） |
| 职业 | 代码审查工程师 |
| 能力域 | 静态代码审查、OWASP 安全审计、契约符合性核对、变更影响面分析、项目公约符合性 |

**为什么新增**：原团队 QA 明确只做黑盒测试且不碰源码，没有任何角色做白盒静态审查。安全漏洞、契约偏离、破坏性变更这类跑测试也未必暴露的问题，在 QA 开工前无人拦截。按团队自身判据「用户会不会直接问它」——"帮我 review 这段代码""这个改动有没有安全隐患"是高频直问。

**SOP 位置**：插在 Phase 3（编码实现）之后、Phase 5（QA 测试）之前，作为 Phase 4 代码审查门禁。`REVIEW: REJECT`（有 BLOCKER）则回流修复，最多 2 轮。先审后测，减少 QA 返工。

### 1.2 SOP 结构改造

| 改造点 | Before | After |
|---|---|---|
| Phase 数 | 5 阶段 | 6 阶段 + Phase 0 |
| Phase 0 | 无 | **项目公约勘察**（存量项目必走）：架构师产出技术栈实况/目录约定/既有模式/质量基线/禁区五项摘要，后续所有成员 prompt 原文携带 |
| 代码审查 | 无 | Phase 4 审查门禁，REJECT 回流 |
| 契约管理 | "逐字一致" | **版本冻结**：合并时打 `CONTRACT v1` 冻结，修订升版本+同步双方 |
| 上下文传递 | "传完整原文"（与 skill 协议矛盾） | **三级传递规则**：L1 逐字全文（契约/Token/验收标准/公约摘要）/ L2 结构化摘要（代码产出/无关PRD章节）/ L3 按需索取（历史讨论） |
| 阻塞上报 | 各角色零散提及 | **统一 BLOCKED 格式**，主理人分级处理（自裁→调度→问用户） |
| 增量模式 | 5 步无公约勘察 | 必走 Phase 0 + 审查员重点审变更影响面与公约符合性 |

### 1.3 协作配置强化

- **审查 vs 测试分工表**：明确白盒（审查员）与黑盒（QA）的边界
- **能力归属仲裁表**扩充：代码质量/应用层安全发现归审查员，修复归实现方
- **6 条设计原则**（原 4 条）：契约版本冻结、上下文分级、入乡随俗
- 所有 meta-spec 文件（skill-matrix / collaboration-protocol / role-template / SKILL.md / README）同步更新至 9 角色

---

## 二、项目集成方案

### 2.1 目录结构

在 SmartAsk 仓库根目录新增以下资产（**零侵入业务代码**）：

```
smartask/
├── AGENTS.md                              # [新增] 项目级 AI 协作公约（任何 AI 工具必读）
├── .ai-team/                              # [新增] 框架无关的专家团资产
│   ├── team-config.yaml                   #   机器可读：角色注册/SOP/路由/门禁
│   ├── agents/                            #   9 个角色纯 prompt 模板
│   │   ├── fullstack-dev-team-lead.md     #   主理人（含完整 SOP）
│   │   ├── fullstack-dev-pm.md
│   │   ├── fullstack-dev-designer.md
│   │   ├── fullstack-dev-architect.md
│   │   ├── fullstack-dev-frontend.md
│   │   ├── fullstack-dev-backend.md
│   │   ├── fullstack-dev-reviewer.md      #   新增角色
│   │   ├── fullstack-dev-qa.md
│   │   └── fullstack-dev-devops.md
│   └── README.md                          #   资产说明与使用方式
├── scripts/
│   └── sync-from-expert-pack.sh           # [新增] 专家包变更同步脚本
└── docs/
    └── fullstack-dev-team-integration.md  # [新增] 本文档
```

### 2.2 配置文件说明

#### `AGENTS.md`（项目级 AI 协作公约）

放在仓库根目录，是 AI 工具约定的标准位置（等同 CLAUDE.md）。包含：

- **项目速写**：SmartAsk 是什么、技术栈、关键模块（含 four_agent_ask.py 上帝文件警告）
- **工作准则**：只读优先 / 最小变更 / 入乡随俗 / 上帝文件慎改 / 配置优先于代码
- **调用专家团**的方式（读 prompt 文件 / 代码加载 yaml）
- **SOP 速查**与**上下文/质量规则速查**
- **SmartAsk 专属约定**：four_agent_ask.py 改动规则、配置体系、SSE 帧、前端规范、测试部署命令

任何 AI 工具打开此仓库时会自动读取该文件，按专家团规范工作。

#### `.ai-team/team-config.yaml`（机器可读配置）

单一事实来源，代码可直接 `yaml.safe_load()` 加载。包含：

| 段落 | 内容 |
|---|---|
| `team` | 团队元信息（名称、主理人、规模、源头路径） |
| `members` | 9 角色注册表（id/花名/职业/角色/prompt文件/能力列表/典型问法） |
| `sop.phases` | 7 阶段定义（含 Phase 0 存量勘察），每阶段含成员/并行性/输入/输出/门禁 |
| `workflows` | 6 条工作流（单点直调/快速/BugFix/标准SOP/增量/部分） |
| `routing_table` | 单点直调路由表（问题类型→角色） |
| `context_rules` | 上下文三级传递规则（L1/L2/L3） |
| `quality_gates` | 7 道质量门禁 |
| `contract_versioning` | 契约版本冻结与修订规则 |
| `arbitration` | 冲突仲裁规则 |
| `blocked_format` | 阻塞上报统一格式 |

#### `.ai-team/agents/*.md`（角色 prompt 模板）

从专家包萃取的纯 prompt 正文，已去除 WorkBuddy 专属 frontmatter（name/description/displayName/profession/maxTurns/skills）。任何 LLM 可直接作为 system prompt 使用。元信息统一在 `team-config.yaml` 管理，prompt 文件保持干净。

### 2.3 调用方式

#### 方式一：IDE 内 AI 协作（已验证约定 ✅）

三个主流 AI IDE 均支持读取项目根目录的 `AGENTS.md`，**开箱即用**：

| IDE | 自动读取 | 细粒度规则目录 | 额外能力 |
|---|---|---|---|
| **Trae** | `AGENTS.md` ✅ | `.trae/rules/*.md`（Always/Glob/Manual 三种激活模式） | - |
| **Antigravity** | `AGENTS.md` ✅（跨工具基础，与 Cursor/Claude Code 共享） | `.agents/rules/*.md`（Always/Glob/ModelDecision/Manual） | `.agents/workflows/*.md` 可 `/command` 触发；`GEMINI.md` 专属覆盖 |
| **VSCode + GitHub Copilot** | `.github/copilot-instructions.md` ✅（1.194+） | - | - |

仓库内已配置：
- `AGENTS.md` - 根目录，三个 IDE 共享的项目公约
- `.trae/rules/` - Trae 细粒度规则（全局准则 + 后端 globs + 前端 globs）
- `.agents/rules/` - Antigravity 细粒度规则（后端 + 前端）
- `.agents/workflows/start-cycle.md` - Antigravity 可 `/start-cycle` 触发的专家团 SOP 工作流
- `.github/copilot-instructions.md` - VSCode Copilot 指令

**使用方式**：在任意上述 IDE 中打开 SmartAsk 项目，AI 助手自动读取对应规则文件并遵循专家团规范。无需额外配置。在 Antigravity 中还可以输入 `/start-cycle` 触发完整的专家团 SOP 流水线。

#### 方式二：代码加载（编程调用）

```python
import yaml

cfg = yaml.safe_load(open('.ai-team/team-config.yaml'))

# 获取某角色 prompt
member = next(m for m in cfg['members'] if m['id'] == 'fullstack-dev-backend')
system_prompt = open(f".ai-team/{member['prompt_file']}").read()

# 按 SOP 阶段编排
for phase in cfg['sop']['phases']:
    if phase['condition'] == 'brownfield' and not is_brownfield_project:
        continue
    for member_id in phase['members']:
        m = next(x for x in cfg['members'] if x['id'] == member_id)
        prompt = open(f".ai-team/{m['prompt_file']}").read()
        # 注入上下文 + 调用 LLM（接 SmartAsk 现有的 LLM 客户端）

# 单点直调
target_role = cfg['routing_table']['接口/数据库/性能']  # → fullstack-dev-backend
```

SmartAsk 后端已有 LLM 客户端（openai SDK，兼容通义千问/DeepSeek），可直接复用。无需引入新依赖，仅需 `pyyaml`（已在 requirements.txt 体系中）。

#### 方式三：WorkBuddy 专家中心消费

专家包源头在 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/fullstack-dev-team/`，已注册到 WorkBuddy 专家中心，可直接以"全栈研发专家团"形式对话使用，获得完整的 TeamCreate + Agent spawn 协作体验。

### 2.4 与现有项目模块的对接

| 现有模块 | 对接方式 |
|---|---|
| `backend/four_agent_ask.py`（问数四智能体） | **不对接**。fullstack-dev-team 是"研发协作"团队，服务于开发过程，不接入问数运行时管线。两者职责正交。 |
| `backend/ask_flow/controller.py`（引擎开关） | 不对接。同上。 |
| `backend/requirements.txt` | 仅需确认 `pyyaml` 可用（代码加载 yaml 时）。若缺失则 `pip install pyyaml`。 |
| `config/`（配置体系） | 不对接。专家团配置独立在 `.ai-team/team-config.yaml`，与问数业务配置分离。 |
| `.workbuddy/memory/`（项目记忆） | 并列存在。`.ai-team/` 是可共享的团队资产（建议提交 Git），`.workbuddy/memory/` 是个人工作记忆（建议 .gitignore 忽略）。 |
| `scripts/`（项目脚本） | 新增 `sync-from-expert-pack.sh`，与现有脚本并列。 |
| `docs/`（项目文档） | 本文档放入 `docs/`。 |

**核心原则**：集成是"加法"不是"改法"。不修改任何现有业务代码，不动问数管线，不引入运行时依赖。专家团能力作为开发辅助资产存在。

---

## 三、对接步骤（落地清单）

1. **已完成** ✅ 专家包优化（9 角色 + SOP 改造 + 协作配置）
2. **已完成** ✅ 专家包校验注册（WorkBuddy 专家中心可见）
3. **已完成** ✅ 创建 `.ai-team/` 目录与资产（team-config.yaml + 9 个 prompt）
4. **已完成** ✅ 创建 `AGENTS.md` 项目公约
5. **已完成** ✅ 创建同步脚本 `scripts/sync-from-expert-pack.sh`
6. **建议** 将 `.ai-team/` 和 `AGENTS.md` 纳入 Git 版本控制（团队共享）
7. **建议** 在 `.gitignore` 中忽略 `.workbuddy/memory/`（个人记忆不提交）
8. **按需** 若要代码运行时调用，在 `backend/` 中新增一个 `ai_team_loader.py` 封装 yaml 加载逻辑，接入现有 LLM 客户端

---

## 四、验证

```bash
# 1. 确认资产就位
ls -la AGENTS.md .ai-team/team-config.yaml .ai-team/agents/

# 2. 验证 yaml 可加载
python3 -c "import yaml; c=yaml.safe_load(open('.ai-team/team-config.yaml')); print(f'{len(c[\"members\"])} members, {len(c[\"sop\"][\"phases\"])} phases')"

# 3. 验证同步脚本
bash scripts/sync-from-expert-pack.sh
```

预期输出：9 members, 7 phases；同步脚本打印 9 个角色 prompt 同步成功。
