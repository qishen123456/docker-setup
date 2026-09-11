---
name: smartask-qa-regression
description: >
  SmartAsk 问数功能的一键自动化回归测试。适用于：用户反馈问数效果异常、
  改完代码后要验证有没有"挖东墙补西墙"、要还原某段历史修复效果、
  或想快速确认某个问法（单点/总览/对比/筛选/排名/聚合/多轮）当前是否正常时。
  解决"手写 diag_*.py 脚本 + docker cp + grep 过滤 SQL 噪音"太慢、太不准的痛点：
  内置环境自检（PG 探活/代码可导入）、声明式用例、自动断言、
  干净报告，一条命令跑完所有基线回归。
  当用户说"测一下这个问法""回归一下基线""帮我验证有没有破坏别的问题""跑一遍测试清单"时触发使用。
---

# SmartAsk 问数回归测试技能

一条命令跑完问数功能回归，自动判 PASS/FAIL，随代码和 baseline 一起演进。

## 为什么需要它（历史痛点）

手写临时脚本测试有三个坑，本技能全部规避：

| 痛点 | 根因 | 本技能对策 |
|---|---|---|
| 慢 | 每次写 `diag_*.py` + `docker cp` + `docker exec` + grep 过滤 SQL 噪音 | runner 常驻容器，直接 import 最新代码，秒级 |
| 不准确 | token 截断 403 假象、Flask 进程跑旧代码、独立进程≠HTTP、SQL 污染断言、靠人肉看 | preflight 两道闸自检 + md5 报告头 + 自动断言 + 干净报告 |
| 不可维护 | 诊断脚本散落几十个、baseline 变了用例不更新 | 声明式 JSON 用例，`source` 锚定 baseline §X / bug #N |

## 核心决策：容器内直接 import 跑

`four_agent_ask_service.ask()` 是 HTTP handler 与诊断脚本共用的**同一函数**，容器内 import 调用即与生产同代码路径，且无 HTTP 鉴权（彻底消灭 token 截断 403 假象）。拿到的是完整 Python 对象而非序列化 JSON，断言面更小。

**权限声明**：runner 恒以 super_admin 跑（可用例级 `user` 字段覆盖，见下），权限过滤路径默认不覆盖。

## 快速开始

```bash
# Windows Git Bash 注意：docker cp/exec 的容器路径会被 MSYS 路径转换吃掉，
# 必须加 MSYS_NO_PATHCONV=1 前缀（cmd/PowerShell 不需要）。

# 1. 同步 runner + 用例到容器
# 注意：docker cp 目录时若容器内 qa_cases 已存在，会嵌套成 qa_cases/cases/ 导致跑到旧用例
# （2026-08-18 实测踩坑：容器内 21 条旧用例 vs 本地 29 条，报告却显示全 PASS 的假象）。
# 稳妥做法：先删容器内旧目录再 cp，或 cp 后用 md5sum 比对容器/宿主机文件。
MSYS_NO_PATHCONV=1 docker cp .agents/skills/smartask-qa-regression/runner/qa_runner.py smartask-backend:/app/backend/qa_runner.py
MSYS_NO_PATHCONV=1 docker exec smartask-backend rm -rf /app/backend/qa_cases
MSYS_NO_PATHCONV=1 docker cp .agents/skills/smartask-qa-regression/cases smartask-backend:/app/backend/qa_cases

# 2. 跑用例库（baseline 和 bugs 是两个文件，分别跑，或用 && 串联）
MSYS_NO_PATHCONV=1 docker exec smartask-backend python /app/backend/qa_runner.py /app/backend/qa_cases/baseline.json
MSYS_NO_PATHCONV=1 docker exec smartask-backend python /app/backend/qa_runner.py /app/backend/qa_cases/bugs.json
# 串联：MSYS_NO_PATHCONV=1 docker exec smartask-backend bash -c "python /app/backend/qa_runner.py /app/backend/qa_cases/baseline.json && python /app/backend/qa_runner.py /app/backend/qa_cases/bugs.json"

# 3. 只跑某个用例（按 id 前缀过滤）
MSYS_NO_PATHCONV=1 docker exec smartask-backend python /app/backend/qa_runner.py /app/backend/qa_cases/bugs.json B15
```

## 环境自检（preflight 两道闸：PG 全灭或代码不可导入才中止，绝不跑出错误结果）

1. **PG 探活（分级）** — 遍历 `config/datasources.json` 里全部 `is_active` 的 PostgreSQL 源逐一 `SELECT 1`（跳过 `is_active=false` 的源），每个源的连通结果（数据源名 + OK/失败原因）打印到报告头。**全部不可达**才 `ENV-FAIL` 中止（此时跑下去必是全假"没结果"）；**至少一个可达即放行**，不可达的源降级为警告、不阻断
2. **代码可导入** — `import four_agent_ask` 失败即中止

### 同步完整性自检（防"跑到旧用例"假象）

`docker cp` 目录到已存在的容器路径会嵌套（见快速开始注意）。跑完后建议比对用例数：报告头"加载 N 个用例"应与本地 `cases/*.json` 条数一致；不一致即同步失败，重跑同步步骤。

自检失败输出 `ENV-FAIL`，与用例 FAIL 严格分离，杜绝误报。

### 报告头 md5 自检（报告项，不是阻断闸）

runner 启动时在报告头部打印三个文件的 **md5 + mtime**：容器内 `/app/backend/four_agent_ask.py`、runner 自身、用例文件。用于肉眼发现"容器跑的不是本地这份代码"的漂移，**只报告不拦截**（容器内无 .git，不打 git hash）。宿主机比对：

```bash
md5sum backend/four_agent_ask.py
```

## 用例格式（声明式，非工程师可加）

在 `cases/*.json` 里加一个对象即可：

```json
{
  "id": "R1",
  "question": "消费者城市分公司排名",
  "source": "baseline §2.1",
  "asserts": [
    {"path": "dataset_results.0.query_intent.intent", "op": "eq", "expect": "ranking"},
    {"path": "dataset_results.0.query_intent.top_n", "op": "eq", "expect": 0},
    {"path": "dataset_results.0.row_count", "op": "eq", "expect": 69}
  ]
}
```

多轮（同 session 连续问）用 `turns`：

```json
{
  "id": "M5",
  "source": "baseline §8.3",
  "turns": [
    {"question": "消费者事业部业绩"},
    {"question": "东部分公司业绩",
     "asserts": [{"path": "route.dataset_ids", "op": "eq", "expect": [3]}]}
  ]
}
```

数据前提不存在等原因需要暂停的用例，加 `"skip": true` + `"skip_reason"`（2026-09-10 起支持）：runner 会打印 SKIP 行并跳过执行，不打 LLM、不计入断言合计。数据前提恢复后删掉这两个字段即可重新启用。

**弹确认要「走完」**（用 `confirm` 数组，每个候选数据集都测一遍）：

```json
{
  "id": "R-bottom3-confirm",
  "source": "baseline §2.6/bug#18",
  "question": "垫底的三个分公司",
  "asserts": [{"path": "requires_confirmation", "op": "allow_confirm"}],
  "confirm": [
    {"select": {"dataset_ids": [2]},
     "asserts": [
       {"path": "route.dataset_ids", "op": "eq", "expect": [2]},
       {"path": "dataset_results.0.query_intent.top_n", "op": "eq", "expect": 3},
       {"path": "dataset_results.0.query_intent.direction", "op": "eq", "expect": "asc"},
       {"path": "dataset_results.0.row_count", "op": "eq", "expect": 3}
     ]},
    {"select": {"dataset_ids": [3]},
     "asserts": [
       {"path": "route.dataset_ids", "op": "eq", "expect": [3]},
       {"path": "dataset_results.0.row_count", "op": "eq", "expect": 3}
     ]}
  ]
}
```

`select.dataset_ids` 指定选哪个数据集，runner 会从 `confirmation_options` 找到对应选项，真正调 `confirm_by_boss` 走完流程，再对确认后的结果跑 `asserts`。**只有 3 个数据集（消费者2/商用3/电商62），弹确认的场景务必把每个候选数据集都写一个分支走完。**

**用例级身份覆盖**（可选 `user` 字段，缺省字段回退默认 super_admin）：

```json
{
  "id": "P1-perm",
  "source": "bug#13 权限路径后端半边",
  "question": "各分公司业绩排名",
  "user": {"role": "user", "id": 88888, "username": "qa-user", "organization_codes": [], "organization_node_ids": []},
  "asserts": [{"path": "requires_confirmation", "op": "eq", "expect": true}]
}
```

**error 特判**：ask/confirm 结果被服务吞成 `{"error": "..."}` 时，该 turn 记一行 `error ... EXC` 并跳过其余断言（避免一片 None FAIL 噪音）；EXC 计入失败数。

## 2.0 新增能力

2.0 将“已知问法回归”扩展为“问法变体 + 语义 + 数据一致性 + 前端渲染 + 文本卫生”回归：

- `entity_exists`：检查题干实体是否真实出现在返回明细节点中，防止不存在节点静默返回大量幽灵行。
- `rows_semantic_check`：按题干显式节点检查返回行，节点不存在且有数据时失败；空结果必须显式提示“未找到”。
- `kpi_equals_sum`：从 `report_spec.kpis` 找指定 KPI，与明细对应列求和比较，允许 1% 浮点误差。
- `analysis_contains` / `analysis_not_contains`：针对 `dataset_results.0.analysis` 做文本卫生检查，例如拦截 `<think` 标签泄漏；也支持简写 `path: "analysis"`，此时可继续使用 `contains` / `not_contains`。
- 前端关键场景独立使用 `runner/front_render_check.js`，通过 Puppeteer + 现有 Chrome 截图并检查报告/卡片 DOM，不在 runner 中强耦合浏览器环境。

```bash
CHROME_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe" node .agents/skills/smartask-qa-regression/runner/front_render_check.js http://localhost:5173 "业绩最好的分公司" qa-front.png
```

脚本执行输入、提交、等待报告 DOM，并输出 `qa-front.png`；若项目未安装 Puppeteer，先在项目依赖中执行 `npm install puppeteer`。

N1-N8、think 标签泄漏和 R-bottom5 详见 `cases/bugs.json`；完整问法变体矩阵详见 `cases/variants.json`。runner 会将 `variants.json` 的 `groups[].variants[]` 自动展平为可执行用例并输出 PASS/FAIL/CONFIRM/EXC 报告。
### 可断言的路径（path）

- `route.dataset_ids` / `route.decision` / `route.requires_confirmation`
- `requires_confirmation`（顶层，与 `route.requires_confirmation` 区分：弹确认判断建议用顶层键）
- `dataset_results.0.query_intent.intent` / `.top_n` / `.direction` / `.rank_sides` / `.sort_metric_column` / `.target_level`
- `dataset_results.0.row_count`
- `dataset_results.0.analysis`（LLM 解读；用 `analysis_contains` / `analysis_not_contains` 做文本卫生断言）
- `analysis`（analysis 断言的简写，等价于首个数据集的 `dataset_results.0.analysis`）
- `dataset_results.0.sql`（断言用 contains / not_contains，匹配**完整 SQL 文本**；报告展示才用截断摘要）
- `dataset_results.0.rows.0.节点名称`（第一个节点名）
- `dataset_results[ds=N].row_count`（**数据集选择器**：在 list 中按 `dataset_id==N` 选元素再取子路径，不按索引——多数据集顺序不保证；找不到返回 None）

### 断言操作符（op）

| op | 含义 |
|---|---|
| `eq` | 精确等于（intent/dataset_ids/top_n/direction/rank_sides 用这个） |
| `contains` | 字符串包含（节点名、SQL 片段；对 `.sql` 路径匹配的是**完整 SQL**，不是摘要） |
| `not_contains` | 字符串不含（抓 top_n 丢失回归；`.sql` 同样对完整 SQL 匹配） |
| `gt` / `gte` / `lt` / `lte` | 数值比较（row_count）；got 非数值（含 None/字符串）判 False 不抛异常 |
| `range` | `[min, max]` 范围（容忍数据抖动）；got 非数值判 False |
| `nonempty` | 非空（rows>0、analysis 非空） |
| `entity_exists` | 题干节点名必须出现在数据集明细中；空结果可返回，但非空幽灵行会 FAIL |
| `rows_semantic_check` | 按题干节点检查返回行；非空但不含节点，或空结果未提示“未找到”都会 FAIL |
| `kpi_equals_sum` | 指定 KPI 卡值与所有明细行同名列合计一致，允许 1% 浮点误差 |
| `analysis_contains` / `analysis_not_contains` | 检查 `dataset_results.0.analysis` 文本；用于拦截 `<think` 等泄漏 |
| `allow_confirm` | 该问题弹确认是**正确行为**（跨数据集歧义），弹确认记 CONFIRM（不算失败）、不弹判 FAIL |

### "合理弹确认"白名单

以下问题命中多个数据集的真实层级/裸节点，弹确认是**正确行为**（用 `allow_confirm` 标记）：

- 「分公司」层级词：`各分公司业绩排名`/`分公司业绩排名`/`前3的分公司`/`垫底的三个分公司`/`业绩最好的分公司`
- 「业务部」层级词：`业务部业绩排名`/`业务部的业绩情况`（商用+电商都有）
- 裸节点：`上海那边业绩如何了`（上海城市公司 vs 上海代表处）

**反例**（弹确认 = FAIL）：带明确前缀的 `看下前三的商用分公司`、唯一命中的 `看下上海代表处的业绩咋样了`。

## 随代码演进（可持续更新）

1. **每个用例必须写 `source`**：锚定 `baseline §X.Y` 或 `bug #N`（隐性锚定也要显式写出，如 `baseline §2.3/bug#16`）
2. **改 baseline 前**：`grep "§2.1" cases/` 找出该节全部用例，同步更新期望值
3. **修好一个 bug**：把 `bugs.json` 里对应用例的 `source` 从 `bug #N` 改成 `baseline §X`，升格为永久回归；若 baseline 已有等价用例（source 锚定同一 bug），直接删除 bugs.json 里的重复条
4. **新增问法**：从 `config/confirmed_behaviors_baseline.md` 的代表问题里取，按本格式加进对应 `cases/*.json`

## 二期 backlog（已知缺口，暂不做）

- `turns` 内支持 confirm（当前多轮与弹确认互斥）
- `set_eq` / `len_eq` 操作符（集合相等、长度相等）
- 报告中文列宽对齐（`east_asian_width`）
- 用例 schema 校验（启动时校验 cases/*.json 结构）
- 业务部 confirm 族 + 电商 ds=62 用例密度补强

## 目录结构

```
.agents/skills/smartask-qa-regression/
├── SKILL.md                  # 本文件
├── runner/
│   ├── qa_runner.py          # 容器内 runner（preflight + md5 报告头 + 断言 + 报告 + 多轮 + user 覆盖）
│   └── front_render_check.js # 可选 Puppeteer 前端关键场景 DOM/截图检查
└── cases/
    ├── baseline.json         # 已知基线用例
    ├── bugs.json             # N1-N8、think 泄漏等 2.0 红色验收用例
    └── variants.json         # 时间、节点、口语、who/which、复合问法变体矩阵
```

## 关键文件索引

- `config/confirmed_behaviors_baseline.md` — 已确认行为基线（唯一事实源）
- `docs/archive/bug-backlog-2026-08-14.md` — 待修复问题清单 + 分组（#1-6/#11-18 已于 2026-08-13~17 全部修复，验收用例已迁入 baseline.json；2026-08-28 从 .workbuddy/artifacts 归档至此）
- `backend/four_agent_ask.py` — 意图解析、SQL 生成、confirm 流程（上帝文件）
- `backend/smartask_engine/intent/resolver.py` — IntentResolver
- `backend/ask_engine_route.py` — 层级词路由（bug#16 承接人层级词登记处）
- `backend/memory/short_term_memory.py` — 多轮追问记忆
- `backend/report_spec_builder.py` — 报告 spec（bug#2/#4 汇总口径修复处）
- `frontend/src/state/smartAskSession.js` — 前端多轮会话状态（bug#13 修复处；QA runner 只覆盖后端半边）
- 三个数据集：商用 id=3、消费者 id=2、电商 id=62
