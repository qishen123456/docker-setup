# SmartAsk 多 IDE 文档目录统一治理方案

> 日期：2026-08-28
> 状态：已评审（CONDITIONAL PASS → 修正后定稿），待执行
> 范围：`.qoder/`、`.workbuddy/`、`.trae/`、`.agents/`、`AGENTS.md`、`.ai-team/`、`.ai-data/`、`docs/`

---

## 1. 背景与问题

项目在多个 IDE（WorkBuddy / Qoder / Trae / 其他）协作过程中积累了四套 AI 相关目录，内容互相重复且新旧不一，容易误导 AI 和开发者：

| 目录 | 性质 | 文件数 | 最后更新 | git 跟踪 |
|---|---|---|---|---|
| `.qoder/repowiki/` | Qoder 自动生成的仓库 wiki 快照 | 374 | **2026-08-08（全部同一分钟批量生成，零后续更新）** | ✅ 已跟踪（374 个文件） |
| `.workbuddy/` | WorkBuddy IDE 会话工作区（memory 日志 + artifacts 诊断产物 + backup） | ~100 | 2026-08-27 | ❌ 未跟踪（`.gitignore:236` 已忽略） |
| `.trae/rules/` | Trae 自动加载的规则文件 | 4 | 2026-08-08 | ✅ 已跟踪 |
| `.trae/documents/` | 孤立的任务规划文档 | 1 | 2026-08-08 | ✅ 已跟踪 |
| `.agents/` | 跨 IDE 的 rules + skills（开放标准目录） | 24 | **2026-08-22（最勤维护）** | ✅ 已跟踪 |
| `.ai-team/` + `.ai-data/` | 两套专家团资产（AGENTS.md 第四节定义） | 39 | 维护中 | ✅ 已跟踪 |

**关键事实**：
- `.qoder` "最全"但"最死"——374 个文件全部为 2026-08-08 一次性生成的静态快照，之后 20 天的所有修复（排名、历史快照、跨集对比等）均未反映，作为事实源反而最误导。
- `.agents` 是开放标准目录，Trae 已在自动加载，且维护最勤（QA 用例、坑记录、迁移脚本均为活资产）。
- `.workbuddy` 未进 git，且已在 `.gitignore` 中。

---

## 2. 治理原则

**文档只能有一个权威版本。IDE 专属目录要么删除、要么作为权威源的生成产物，禁止多处手工维护重复内容。**

## 3. 权威源分层（修正后）

```
AGENTS.md              = 项目级 AI 协作公约（总纲，所有 IDE 约定俗成读取）
.agents/               = 跨 IDE 的 rules + skills（行为规则 + 领域知识，AI 行为权威源）
.ai-team/ + .ai-data/  = 专家团资产（角色 prompt / SOP / 知识库）
docs/                  = 人类读的文档（设计方案 / 诊断报告 / 归档）
```

> 修正说明：初版方案只列了 `.agents` + `docs`，漏了 `AGENTS.md` 总纲和两套专家团资产，本版补齐。

---

## 4. 各目录处置方案

### 4.1 `.qoder/` — 删除（含 git 移除）

- **处置**：`git rm -r --cached .qoder` + 物理删除 + `.gitignore` 增加 `.qoder/`。
- **理由**：374 文件零手工内容、过期 20 天、Qoder 可随时重新生成。
- **零损失保障**：已进 git 历史，任何内容可通过 git 历史找回。
- **禁止事项**：不迁移其内容到权威源（内容已过期，迁移等于引入错误信息）。

### 4.2 `.workbuddy/` — 保留为会话产物，甄别归档

- **定性**：WorkBuddy IDE 的会话工作区，不是文档，不进 git（现状已满足，无需改 `.gitignore`）。
- **artifacts/ 甄别**：
  - **归档**（方法论 / 架构决策类，移入 `docs/archive/`）：如 `clarification-design.md`、`architecture-refactoring-plan-2026-08-13.md`、`intent-single-source-refactor-plan-2026-08-14.md` 等方案/决策类文档。
  - **删除**（一次性运行产物）：`ask_result*.json`、`conc_*.json`、`mid_*.json`、`*.png` 截图、`*.txt` token、`sql_*.json/sql`、`sse_test.txt` 等。
  - **诊断/回归报告**（`amount-followup-diagnosis-*.md`、`baseline-audit-*.md`、`fix-report-*.md` 等）：按"是否描述仍需遵循的口径/决策"逐份判断，是则归档 `docs/archive/`，否则删除。
- **memory/ 保留**：工作日志（最新 08-27），是活动记录非规范文档。
- **backup/ 删除前确认**：`backup/20260814-104501/` 是 8/14 的代码快照，确认当前代码已包含其后所有修复后删除。

### 4.3 `.trae/` — 改为 `.agents/rules` 的同步副本（修正坑 1）

**坑 1 说明**："薄引用壳"（文件里写一行"以 .agents/rules/xxx.md 为准"）对 Trae **无效**——Trae 会把该行文字当规则指令读进上下文，但不会去打开目标文件，等于规则静默失效。

**正确做法**：
1. **先合并差异**：`.trae/rules/` 有 4 个文件，`.agents/rules/` 只有 `backend.md`、`frontend.md`。需先把 `.trae/rules/` 独有的 `project-conventions.md`、`开发规则.md` 的内容归并到 `.agents/rules/`（去重后保留增量），权威源落在 `.agents/rules/`。
2. **再建同步机制**：新增脚本 `scripts/sync-ide-rules.ps1`，从 `.agents/rules/` 复制生成 `.trae/rules/`，每个生成文件顶部自动加注释头：
   ```
   <!-- 自动生成自 .agents/rules/<同名文件>，请勿手改；修改请改权威源后运行 scripts/sync-ide-rules.ps1 -->
   ```
3. **不用 mklink**：Windows 符号链接需管理员/开发者模式，且部分 IDE 对 symlink 读取不一致，复制生成更稳。
4. `.trae/documents/smartask-task-model-redesign-plan.md`：归档到 `docs/` 后删除 `.trae/documents/`。

### 4.4 `.agents/` — 确立为 AI 行为规则权威源

- 接收 `.trae/rules` 归并来的增量内容。
- 现有 skills（qa-regression / ranking-debug / subject-extraction-debug / feishu-sync-ops / runtime-migration / skill-maintenance / skill-usage-guide / global-constraints）维持不变。

### 4.5 `AGENTS.md` — 追加权威源声明

在第七节"同步与维护"追加一段：

```markdown
## 文档权威源声明（2026-08-28）

- AI 行为规则唯一权威源：`.agents/`（rules + skills）。`.trae/rules/` 是其同步副本（scripts/sync-ide-rules.ps1 生成），禁止手改。
- 专家团资产：`.ai-team/`（代码开发）、`.ai-data/`（数据分析），见第四节。
- 人类文档：`docs/`。
- `.qoder/` 为 Qoder 可再生产物，已移除，禁止作为事实源引用。
- `.workbuddy/` 为 WorkBuddy 会话产物，不进 git，其中方案/决策类报告归档 `docs/archive/`。
- 禁止在多处维护重复文档；新增规则只改 `.agents/`。
```

---

## 5. gitignore 变更

```gitignore
# 新增
.qoder/

# 已存在（无需改动）
.workbuddy/      # .gitignore:236
```

> 协作影响评估：`.workbuddy` 已是忽略状态无影响；`.qoder` 采用"删除 + 忽略"而非仅忽略——它可再生、无协作共享价值，忽略只是防止团队成员本地重新生成后污染 git 状态。

---

## 6. 执行步骤（按序）

| # | 步骤 | 验证 |
|---|---|---|
| 1 | 对比 `.trae/rules/` 4 文件与 `.agents/rules/` 2 文件，把增量内容归并进 `.agents/rules/` | 人工 diff，确认 `.trae` 独有内容无丢失 |
| 2 | 新建 `scripts/sync-ide-rules.ps1`（复制 `.agents/rules/*` → `.trae/rules/`，加生成头注释），运行一次 | Trae 重启后规则仍自动加载，内容与 `.agents/rules` 一致 |
| 3 | `.trae/documents/` 的规划文档移入 `docs/`，删除 `.trae/documents/` | 文件在 docs/ 可访问 |
| 4 | `git rm -r --cached .qoder`，物理删除 `.qoder/`，`.gitignore` 加 `.qoder/` | `git status` 干净；`git log` 可找回历史 |
| 5 | 甄别 `.workbuddy/artifacts/`：方案/决策类 → `docs/archive/`，一次性产物删除 | `docs/archive/` 含归档件；无有效信息丢失 |
| 6 | 确认 `.workbuddy/backup/20260814-104501/` 不再需要后删除 | 当前代码包含 8/14 后全部修复 |
| 7 | `AGENTS.md` 第七节追加权威源声明 | 声明与第 3 节分层一致 |
| 8 | （可选）`.ai-data/` 根目录清理散件：`tmp_voice.wav`、`probe_jd_tmall.py`、`probe-jd-tmall.json` 删除或归档 | 目录只留团队资产 |

## 7. 不做的事

- 不迁移 `.qoder` 内容到任何权威源（已过期）。
- 不改动 `.ai-team/`、`.ai-data/` 的目录结构（只纳入权威源声明）。
- 不动 `.workbuddy/memory/`。
- 不为 `.trae/rules` 使用符号链接（Windows 兼容性差）。

---

## 8. 执行复盘（2026-08-28 补记）

- 步骤 1-4、6-8 按方案执行并验证通过（规则零丢失、Trae 实际加载、脚本幂等、编码 UTF-8 无 BOM）。
- 步骤 5 偏差：`.workbuddy/artifacts/` 诊断/回归报告实际按类别批量删除，未按方案"逐份判断"；`.workbuddy/` 不在 git 跟踪内，删除不可逆。缓解：长效坑已沉淀于 `.agents/skills/` 各 SKILL 与 `.workbuddy/memory/` 日志，决策类文档已归档 `docs/archive/`。
- **教训（纳入后续守则）：非 git 跟踪目录的删除必须逐份甄别、禁止批量删；批量删除前先整目录打包备份。**
- 执行后修正：`.agents/skills/smartask-qa-regression/SKILL.md` 中对 `.workbuddy/artifacts/bug-backlog-2026-08-14.md` 的悬空引用已改指 `docs/archive/`。
