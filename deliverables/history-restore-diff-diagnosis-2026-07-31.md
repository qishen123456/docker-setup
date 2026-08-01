# 历史记录恢复与实时问数界面不一致 — 诊断报告

- 日期：2026-07-31
- 复现问题：「山东分公司的业绩」
- 方式：只读分析 + 真实接口实测，**未修改任何业务代码**
- 环境：docker 三容器均 healthy（backend 5002 / frontend 8888 / postgres 5433）

---

## 0. 前置事实：未提交改动已经在生产运行

`git status` 显示 5 个未提交变更，**全部集中在历史记录链路**：

```
 M backend/smartask_report_history_store.py
 M backend/tests/test_smartask_report_history_store.py
 D backend/tests/test_smartask_report_history_store_self_parent.py
 M frontend/src/composables/useSmartAskReportHistory.js
 M frontend/src/state/smartAskHistory.js
```

经容器内校验，**这批改动已经 build 进两个镜像并正在运行**：

| 校验项 | 容器内实际值 | 结论 |
|---|---|---|
| `MAX_ITEMS_PER_SCOPE` | `20`（旧值 200） | 新代码 |
| `_has_self_parent_anomaly` | 出现 0 次 | 新代码 |
| `focusNodeIsLeaf` | 出现 0 次 | 新代码 |
| 前端 bundle `aggressive compaction` | 命中 | 新代码 |
| 前端 bundle `无权访问的数据集` | 未命中（已删） | 新代码 |

注意 `docker-compose.yml` 的 backend **没有挂载源码目录**（只挂 logs/config/imports/backups），前端是静态构建产物。所以改动是通过 rebuild 生效的，不是热加载。

---

## 1. 数据层实测：完全一致，后端清白

用 `business_admin:18576614568` 的有效 token 直调 `POST /api/smart-chat`（HTTP 200，264KB，33.4s），与 `config/smartask_report_history.json` 里用户 13:15:56 保存的同问题快照做字段级 diff：

| 对比维度 | 结果 |
|---|---|
| `result` 顶层字段 | 21 个，**双向零差异** |
| `dataset_results[0]` 字段 | **双向零差异** |
| SQL | **完全一致** |
| `rows` | 6 行，逐行逐字段**完全一致** |
| `report_spec` | 数值等价 |
| `steps` | 均为 5 步，标题与顺序一致 |

唯一的"差异"是 JSON 浮点序列化噪声：实时 `6105486.0` / `100420000.0`，历史 `6105486` / `100420000`。

成因：前端 `clone = JSON.parse(JSON.stringify(v))` 时 JS 不保留 `.0`，回传后 Python `json.loads` 解析成 int。**在 JS 里两者 `===` 相等，不影响任何渲染。**

`analysis` 文本不同（868 vs 773 字）属 Agent4 每次重新生成，是上一轮已定位的 LLM 非确定性问题，与历史快照机制无关。

> **结论：后端链路、快照存储、数据完整性全部没有问题。差异 100% 发生在前端渲染层。**

---

## 2. 根因链：执行日志从未被持久化

### 断点 1 — 快照根本不保存 logs

`frontend/src/composables/useSmartAskReportHistory.js:60-78` `buildReportHistorySnapshot()` 保存的字段是：

```
version / question / updatedAt / datasetId / datasetName
result / conversationSessionId / messages
```

**`session.state.logs` 不在其中。** 而 logs 是 SSE 流式过程中累积的真实执行轨迹（Agent1 语义路由、规则 SQL 兜底生成、Agent3 全量复核、系统执行 SQL、Agent4 业务解读，各带真实耗时）。

### 断点 2 — 恢复时主动清空 logs

`useSmartAskReportHistory.js:175`：

```js
session.state.logs = []
```

### 断点 3 — 渲染判定被这一行否决

`frontend/src/views/SmartAsk.vue:3929-3942`：

```js
const isCurrentResult =
  msg.data?.question &&
  session.state.question &&
  msg.data.question === session.state.question &&
  session.state.logs.length > 0        // ← 历史恢复后恒为 0

if (isCurrentResult) {
  return session.state.logs.map(...)   // 真实 trace
}
```

前两个条件在历史恢复后其实**是满足的**（`restoreHistory` 会把 `session.state.question` 设成同一个问题），唯独 `logs.length > 0` 不成立，导致整体恒 false。

### 断点 4 — 落到硬编码伪步骤分支

`SmartAsk.vue:3944-3980` 生成的是与真实执行无关的通用文案：

- 「已完成问题理解与执行规划 / 系统已经确定查询路径与分析重点。」
- 「已完成数据检索 {dataset_name} / 已返回 N 行结果数据。」
- 「已生成经营分析报告 / 报告摘要已经同步写入左侧回复区与右侧结果区。」

**这就是用户肉眼看到的"不一样"：实时是 5 条带真实耗时的执行轨迹，历史是 3 条写死的套话。**

### 连带影响

`SmartAsk.vue:3983-3990` 的 `isCurrentSessionMessage()` 使用完全相同的判定条件，历史恢复后同样恒 false，进而影响 `currentSessionAiMessage`、`activeRequestAiMessage` 等依赖它的 UI 分支。

### 其他次要差异

| 位置 | 现象 |
|---|---|
| `useSmartAskReportHistory.js:130-135` | AI 消息恢复时只写 `data`，**不恢复 `content`**。本例 AI 消息 content 长度为 0，暂未暴露，属隐患 |
| `useSmartAskReportHistory.js:5` | `MAX_SNAPSHOT_MESSAGES = 30`，超长会话只保留最后 30 条 |
| `useSmartAskReportHistory.js:173-178` | `detailReportResult` / `startedAt` / `currentSessionId` 全被清空，用户展开过的详情视图不会恢复 |
| `smartAskHistory.js:133-146` | 本地缓存时 `result.logs` 只保留含 SQL 的最后 10 条 |

---

## 3. 未提交改动引入的新风险

这批「完全保留快照」重构方向是对的（原来本地压缩版覆盖服务端完整版确实是 bug），但落地时带出 5 个新问题。

### 3.1 历史容量 200 → 20，静默永久丢失（高）

`smartask_report_history_store.py:22` `MAX_ITEMS_PER_SCOPE` 从 200 改成 **20**。

`upsert_history()` 每次写入都执行 `[:MAX_ITEMS_PER_SCOPE]` 截断，超出的记录**直接从磁盘消失，不可恢复**。而前端 `getSmartAskReportHistory(50)` 仍按 50 条请求，`MAX_HISTORY_ITEMS = 50`——两边口径不一致，且全程无任何提示。

### 3.2 历史恢复不再做数据集权限过滤（高 / 安全）

`useSmartAskReportHistory.js` 删除了 `filterResultDatasets()`，并移除了三处 `isDatasetVisible()` 校验：

```js
- session.state.selectedDatasetId = restoredSelectedDatasetId && isDatasetVisible(...) ? ... : null
+ session.state.selectedDatasetId = restoredSelectedDatasetId

- datasetId.value = item.datasetId && isDatasetVisible(item.datasetId) ? item.datasetId : null
- if (...) ElMessage.warning('该历史会话包含当前账号无权访问的数据集，已隐藏相关结果。')
+ datasetId.value = item.datasetId || null
```

后果：用户对某数据集的权限被回收后，仍可从历史记录里完整看到该数据集的报告、明细行和 SQL。原有的越权提示也一并删除了。

### 3.3 服务端绝对优先 + 静默吞错 = 刷新即回退（高）

`smartAskHistory.js:326-345` 改成服务端有同 ID 就永远用服务端版本，本地只在服务端缺失时补充。

同时 `pushHistoryToServer()`（347-356）只识别 `stale_history_snapshot`，**其余所有失败（网络抖动、超时、413、500）静默返回 `ok:false`，既不重试也不提示**。

两者叠加：只要某次 POST 失败，那条本地更新就永远同步不上去，下次刷新必然回退到服务端旧版本——**这正是"刷新前后不一样"的机制性成因**。

### 3.4 快照体积失控，本地必然降级（中高）

取消 rows / report_spec / messages 裁剪后：

```
config/smartask_report_history.json  =  7.5 MB / 11 条记录
单条平均 385 KB，最大 753.9 KB
```

两个问题：

1. **后端**：`read_json` / `write_json` 是整文件读写，每次 upsert 都要全量重写 7.5MB，且在 `_LOCK` 内串行。
2. **前端**：本地保 20 条预估 **7.5MB**，远超 localStorage 约 5MB 上限 → `persistSmartAskHistory()` 每次都先失败一次、再降级到 `compactHistoryItemForLocalAggressive`。

也就是说「完全保留快照」这个目标**在本地存储上根本达不成**，只是把裁剪从"一开始就做"改成了"先撞墙再做"。

### 3.5 脏数据校验被移除，旧 bug 会复现（中）

删除了 `_has_self_parent_anomaly()` 和 `focusNodeIsLeaf` 冲突检测，同时删掉配套测试 `test_smartask_report_history_store_self_parent.py`。

该函数原本拦截的是「层级=城市分公司，节点名称=山东分公司，上级名称=山东分公司」这类飞书字段污染产生的自环脏数据。移除后，这类快照会被正常保存和恢复，此前修掉的「每个分公司下都挂着一个同名城市公司」会在历史记录里重新出现。

---

## 4. 修复方向（未实施，待确认）

### 4.1 解决界面不一致（本次主诉）

| 优先级 | 做法 | 说明 |
|---|---|---|
| 首选 | `buildReportHistorySnapshot` 增加 `logs: session.state.logs`，`restoreHistory` 改为 `session.state.logs = reportSnapshot.logs \|\| []` | 历史恢复即可显示真实 trace，与实时完全一致。logs 体积小，不构成负担 |
| 备选 | 把 `isCurrentResult` 的 `logs.length > 0` 换成显式的 `isHistoryRestored` 标志 | 只解决判定，仍显示不了真实 trace |
| 配套 | 删除 `SmartAsk.vue:3944-3980` 的硬编码伪步骤分支，改为「本次会话未保留执行日志」的明确空态 | 编造步骤比留空更容易误导 |
| 配套 | AI 消息恢复时补回 `content` 字段 | 消除隐患 |

### 4.2 回收未提交改动的风险

| 优先级 | 做法 |
|---|---|
| 高 | `MAX_ITEMS_PER_SCOPE` 恢复到 200（或与前端 `MAX_HISTORY_ITEMS` 统一为同一常量），避免静默丢历史 |
| 高 | 恢复 `isDatasetVisible()` 权限过滤与越权提示——这是安全边界，不能因为"保留快照"就放开 |
| 高 | `pushHistoryToServer` 失败要落日志 + 有限重试；`mergeHistoryItems` 增加"本地有未同步标记时优先本地"的兜底，避免刷新回退 |
| 中 | 快照瘦身：`report_spec.provenance`、`accordions[].chart.rows` 与 `dataset_results[].rows` 高度重复，可只存一份并在渲染时引用；后端历史改为按 scope 分文件或落库，避免整文件读写 7.5MB |
| 中 | 恢复 `_has_self_parent_anomaly` 校验及其测试。若确实希望保留脏数据快照，应改为「保留但打标提示」，而非直接删除检测 |

---

## 5. 一句话总结

数据没错，SQL 没错，快照也没丢——**错在执行日志从来没被存进快照，恢复时又被清成空数组，于是前端判定"这不是当前会话"，转而渲染一段写死的假步骤**。而这批未提交的"完全保留快照"改动，在修好旧 bug 的同时，把历史上限砍到 20、删掉了数据集权限过滤、并让同步失败变成静默回退。
