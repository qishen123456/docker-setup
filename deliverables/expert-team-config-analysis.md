# SmartAsk 双专家团队配置分析报告

> 分析日期：2026-08-03
> 分析范围：`.ai-team/`（代码开发团队，9角色） + `.ai-data/`（数据分析团队，10角色）
> 分析维度：配置问题/风险 · 跨IDE适配 · 优化空间

---

## 一、配置现状概览

| 维度 | .ai-team/（代码开发） | .ai-data/（数据分析） |
|------|----------------------|----------------------|
| 角色数 | 9 | 10 |
| team-config.yaml | ✅ 完整（SOP/路由/门禁/契约/仲裁） | ⚠️ 部分（工作流/路由有，无门禁/契约/仲裁） |
| agents/*.md | ✅ 9个纯prompt | ✅ 10个纯prompt |
| knowledge-base/ | ✅ 4个文件（但全空，仅注释示例） | ❌ 不存在 |
| checklists/ | ✅ 3个文件（安全审计/AI模板味/像素校验） | ❌ 不存在 |
| 同步脚本 | ✅ sync-from-expert-pack.sh（仅同步prompt） | ❌ 无 |
| 检查点机制 | ✅ team-lead.md中有规范 | ❌ 无 |
| 集成状态 | 已可用 | not_started（仅知识储备） |

---

## 二、配置问题与潜在风险

### 风险1：Agent ID 命名空间冲突（P0级）

两套团队的 Agent ID 命名规范不一致：

| 团队 | ID 命名模式 | 示例 |
|------|------------|------|
| .ai-team/ | `fullstack-dev-{role}` 带团队前缀 | `fullstack-dev-pm` |
| .ai-data/ | `{role}` 无前缀 | `data-engineer` |

**风险**：当两套团队同时被加载到同一运行时（如 SmartAsk 未来集成时），`.ai-data/` 的 `team-lead` 会与 `.ai-team/` 的概念主理人产生歧义。`routing_table` 合并时也可能出现关键词冲突（如"趋势"在两个团队都有路由）。

**建议**：统一为 `data-team-{role}` 前缀，如 `data-team-trend-analyst`。

### 风险2：team-config.yaml 完整度不对等（P1级）

`.ai-data/team-config.yaml` 缺失以下关键配置块：

| 配置块 | .ai-team/ | .ai-data/ |
|--------|-----------|-----------|
| quality_gates | ✅ 7道门禁 | ❌ 无 |
| contract_versioning | ✅ 冻结+修订规则 | ❌ 无 |
| arbitration | ✅ 冲突仲裁规则 | ❌ 无 |
| context_rules | ✅ 三级传递规则 | ❌ 无 |
| blocked_format | ✅ 统一阻塞上报格式 | ❌ 无 |

**影响**：数据团队的工作流没有质量门禁和上下文传递规则，成员产出质量缺乏约束，阶段间信息传递无规范。

### 风险3：知识库与清单完全缺失于数据团队（P1级）

`.ai-team/` 有完整的知识沉淀体系（pitfalls/decisions/patterns/ai-smells + 3个checklist），`.ai-data/` 完全没有。数据团队的 team-lead.md 中也没有提到知识沉淀机制。

### 风险4：知识库文件全部为空（P2级）

`.ai-team/knowledge-base/` 下4个文件全部只有注释示例，无实际条目：

| 文件 | 实际条目数 | 内容 |
|------|-----------|------|
| pitfalls.md | 0 | 仅有注释中的示例格式 |
| decisions.md | 0 | 仅有注释中的示例格式 |
| patterns.md | 0 | 仅有注释中的示例格式 |
| ai-smells.md | 有内容 | P0/P1 级坏味道清单（非空） |

> ai-smells.md 是唯一有实际内容的，其余三个是"空壳"。

### 风险5：同步脚本覆盖不全（P2级）

`sync-from-expert-pack.sh` 只同步 `agents/*.md`（角色prompt），不同步：
- `team-config.yaml`（需手动核对，脚本仅打印提示）
- `knowledge-base/` 目录
- `checklists/` 目录

### 风险6：数据团队无同步机制（P1级）

`.ai-data/` 从12个专家包整合而来，但没有同步脚本。`source_packs` 字段仅做溯源记录，不机器可执行。源头专家包更新后，项目副本会脱节。

### 风险7：Agent prompt 硬依赖 WorkBuddy 工具（P1级）

两个 team-lead 的 prompt 中大量引用 WorkBuddy 专属工具：

| 引用 | 出现位置 | 非 WorkBuddy IDE 是否可用 |
|------|---------|--------------------------|
| `TeamCreate` | 两套 team-lead.md | ❌ Claude Code/Cursor 无此概念 |
| `Agent spawn` | 两套 team-lead.md | ❌ 其他IDE需用其他方式并行 |
| `SendMessage` | 两套 team-lead.md | ❌ 其他IDE无消息中转机制 |
| `.ai-team/checkpoints/` | team-lead.md 检查点 | ⚠️ 路径依赖WorkBuddy工作目录 |

---

## 三、跨 IDE 适配分析

### 3.1 当前跨IDE可用性评估

| 适配层 | 评估 | 说明 |
|--------|------|------|
| Agent prompt 文件 | ✅ 可用 | 已去除 WorkBuddy frontmatter，纯 markdown |
| team-config.yaml | ✅ 可用 | 纯 YAML，任何工具可解析 |
| AGENTS.md 项目公约 | ✅ 可用 | 标准 markdown，所有IDE可读 |
| 并行调度（spawn多成员） | ❌ 不可用 | 依赖 WorkBuddy TeamCreate/Agent 机制 |
| 消息中转（SendMessage） | ❌ 不可用 | 其他IDE无等价机制 |
| 检查点恢复 | ⚠️ 部分 | 文件可读写，但恢复逻辑需手动实现 |

### 3.2 各IDE适配要点

**Claude Code / Cursor / Windsurf（文件驱动型IDE）**

这些IDE通过读 `.md` 文件作为 system prompt，但没有 TeamCreate/spawn 机制。适配方案：

1. **单角色模式**：直接读 `agents/{role}.md` 注入为 system prompt，跳过团队编排。适用于 routing_table 的单点直调场景。
2. **串行模拟并行**：按 SOP phases 顺序，依次加载每个角色的 prompt，手动拼接上下文。Phase 2 的"并行"退化为"先设计师后架构师"的串行。
3. **上下文传递**：按 `context_rules` 三级规则，手动把 L1 内容复制到下一个角色的 prompt 中。
4. **消息中转**：主理人的编排逻辑由人类或外部脚本承担，而非 IDE 自动完成。

**需要补充的适配文件**：
- `AGENTS.md` 中增加"非 WorkBuddy IDE 使用说明"章节
- 提供 `team-config.yaml` 的 JSON Schema，支持配置校验
- 为每个角色 prompt 增加"独立使用"说明（不依赖 TeamCreate 的用法）

### 3.3 跨IDE适配建议清单

| 优先级 | 适配项 | 工作量 |
|--------|--------|--------|
| P0 | 为 team-config.yaml 编写 JSON Schema | 小 |
| P0 | 在 team-lead.md 中增加"非WorkBuddy降级模式"说明 | 中 |
| P1 | 提供各角色的独立使用说明（不依赖团队调度） | 中 |
| P1 | 在 AGENTS.md 中增加跨IDE适配章节 | 小 |
| P2 | 提供串行模拟并行的编排脚本（Python） | 大 |
| P2 | 提供检查点恢复的独立实现 | 中 |

---

## 四、优化空间分析

### 4.1 团队协作效率

**问题1：两团队无跨团队协作协议**

当前两套团队完全独立，没有定义"数据分析结果需要前端实现看板"这类跨团队场景的协作路径。

**建议**：在两个 team-config.yaml 中增加 `cross_team` 配置块：
```yaml
cross_team:
  triggers:
    - when: 数据分析结果需要前端实现
      from: .ai-data/viz-designer
      to: .ai-team/fullstack-dev-frontend
      handoff: 数据团队产出设计规范 -> 代码团队接收为实现输入
```

**问题2：数据团队缺检查点机制**

代码团队的 team-lead.md 有完整的检查点规范（`.ai-team/checkpoints/`），数据团队没有。

**建议**：在 `.ai-data/` 下创建 `checkpoints/` 目录，并在 team-lead.md 中增加检查点规范。

### 4.2 配置规范性

**问题1：team-config.yaml 无 Schema 校验**

两个 YAML 文件都是自由格式，缺少 JSON Schema 约束。成员列表、SOP阶段、路由表的字段名和结构没有强类型检查。

**建议**：编写 `schema/team-config.schema.json`，覆盖 members/sop/workflows/routing_table/context_rules/quality_gates 等所有配置块。

**问题2：prompt_file 路径无校验**

team-config.yaml 中 `prompt_file: agents/xxx.md` 是字符串，没有校验文件是否真实存在。

**建议**：在同步脚本或 CI 中增加校验步骤：遍历 members，检查每个 prompt_file 路径存在。

**问题3：数据团队 source_packs 不可执行**

`.ai-data/team-config.yaml` 的 `source_packs` 仅做信息记录，12个源头专家包的更新无法自动同步。

**建议**：为数据团队编写类似的同步脚本，或至少在 README 中明确"手动同步"的操作步骤。

### 4.3 可维护性

**问题1：知识库空置**

`.ai-team/knowledge-base/` 下3个文件（pitfalls/decisions/patterns）全是空壳，只有注释示例。ai-smells.md 是唯一有实际内容的。

**影响**：team-lead.md 中规定"Phase 0 读 knowledge-base 补充到公约摘要"、"Phase 4 审查时读 checklists/"，但实际无内容可读。

**建议**：将 SmartAsk 已知的架构事实（如"advanced默认关闭"、"SSE多worker丢状态"、"four_agent_ask.py是上帝文件"）沉淀到 pitfalls.md 和 decisions.md 中。

**问题2：checklists 缺数据团队对应物**

`.ai-team/checklists/` 有3个清单（安全审计/AI模板味/像素校验），全面向代码开发场景。数据团队没有对应的审查清单（如"数据质量校验清单"、"可视化规范清单"）。

**建议**：为数据团队创建 `checklists/`：
- `data-quality-check.md`：数据质量校验清单
- `viz-spec-check.md`：可视化规范校验清单
- `analysis-rigor-check.md`：分析严谨性校验清单

**问题3：AGENTS.md 对数据团队的描述过于简略**

AGENTS.md 第四节（四点五）对 `.ai-data/` 的描述仅4行，没有说明数据团队的工作流、角色边界、使用方式。

**建议**：扩展为与代码团队对等的描述，包含工作流路由表和使用示例。

---

## 五、优化优先级排序

> 标注 [已完成] 的项已在本次完善中落地。

| 优先级 | 优化项 | 团队 | 状态 | 理由 |
|--------|--------|------|------|------|
| P0 | 统一 Agent ID 命名空间 | .ai-data/ | [已完成] | Agent ID 全加 data-team- 前缀 |
| P0 | 补齐数据团队 team-config.yaml 缺失配置块 | .ai-data/ | [已完成] | 补 quality_gates(6道)/context_rules/arbitration/blocked_format/checkpoints/knowledge_base/cross_team/sync_note |
| P1 | 沉淀 SmartAsk 已知架构事实到知识库 | .ai-team/ | [已完成] | pitfalls(4条)/decisions(4条)/patterns(5条) 已填充 |
| P1 | 为数据团队创建 checklists/ | .ai-data/ | [已完成] | data-quality-check/viz-spec-check/analysis-rigor-check |
| P1 | 在 team-lead.md 中增加跨IDE降级说明 | 两团队 | [已完成] | 两套 team-lead.md 各增加"跨IDE降级模式"章节 |
| P2 | 定义跨团队协作协议 | 两团队 | [已完成] | 两个 team-config.yaml 对称增加 cross_team 配置块 |
| P2 | 扩展 AGENTS.md 对数据团队的描述 | AGENTS.md | [已完成] | 第四节重写，明确场景差异/使用方式/跨IDE适配 |
| P1 | 编写 team-config.yaml JSON Schema | 两团队 | 待做 | 配置规范性的基础保障 |
| P2 | 为数据团队编写同步脚本 | .ai-data/ | 待做 | 已在 team-config.yaml 中补 sync_note 手动流程说明 |
| P2 | 校验 prompt_file 路径完整性 | 两团队 | 待做 | 防止配置与文件脱节 |

---

## 六、本次完善改动清单

| 文件 | 改动内容 |
|------|----------|
| `AGENTS.md` | 第四节重写：明确两团队场景差异（开发态/生产态）、Agent ID前缀隔离、跨IDE适配说明、跨团队交接说明 |
| `.ai-data/team-config.yaml` | 版本升至v2：Agent ID全加data-team-前缀；补6道质量门禁/context_rules/arbitration/blocked_format/checkpoints/knowledge_base/cross_team/sync_note |
| `.ai-data/README.md` | 同步更新文件结构（新增knowledge-base/+checklists/）、ID列表、质量门禁说明 |
| `.ai-data/agents/team-lead.md` | Agent ID引用全更新为data-team-*；补知识沉淀/检查点/跨团队交接/跨IDE降级模式章节 |
| `.ai-data/knowledge-base/pitfalls.md` | 新建（数据分析踩坑记录模板+示例） |
| `.ai-data/knowledge-base/decisions.md` | 新建（分析方法决策记录模板+示例） |
| `.ai-data/knowledge-base/patterns.md` | 新建（分析模式记录模板+示例） |
| `.ai-data/checklists/data-quality-check.md` | 新建（CRITICAL/WARN/INFO三级数据质量校验清单） |
| `.ai-data/checklists/viz-spec-check.md` | 新建（图表选型/视觉规范/交互状态/无障碍四维校验） |
| `.ai-data/checklists/analysis-rigor-check.md` | 新建（方法标注/交叉验证/可溯源性/数据诚实/行动导向五维校验） |
| `.ai-team/knowledge-base/pitfalls.md` | 填入4条SmartAsk已知坑（SSE多worker/上帝文件/advanced关闭/vanna版本） |
| `.ai-team/knowledge-base/decisions.md` | 填入4条关键决策（advanced关闭/SSE单worker/上帝文件不拆/配置优先） |
| `.ai-team/knowledge-base/patterns.md` | 填入5条项目模式（配置优先/Blueprint分层/SSE帧序列/契约边界/API封装层） |
| `.ai-team/team-config.yaml` | 补 cross_team 交接协议配置块（与.ai-data/对称） |
| `.ai-team/agents/fullstack-dev-team-lead.md` | 补"跨IDE降级模式"章节（Claude Code/Cursor用法+纯后端代码调用示例） |
