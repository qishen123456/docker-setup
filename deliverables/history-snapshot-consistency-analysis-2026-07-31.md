# SmartAsk 历史快照与实时查询数据不一致问题——系统性分析与解决方案报告

> **报告日期**：2026-07-31
> **分析阶段**：只读代码分析 + 测试方案设计（**未修改任何代码**）
> **分析对象**：历史记录恢复后界面与实时问数结果不一致
> **复现方式**：问「山东分公司的业绩」→ 刷新前后端 → 从历史记录恢复 → 界面不同

---

## 一、差异概述

### 1.1 现象描述

| 维度 | 实时问数（正常） | 历史恢复（异常） |
|---|---|---|
| 执行步骤卡片 | 真实 5 步 trace，含每步耗时和具体细节 | 3 步硬编码伪步骤，无耗时 |
| 步骤 1 文本 | Agent1 语义路由（xx ms） | 已完成问题理解与执行规划 |
| 步骤 2 文本 | 规则 SQL 兜底生成（xx ms） | 已完成数据检索 目标数据集 |
| 步骤 3 文本 | Agent3 全量复核（xx ms） | **无此步骤** |
| 步骤 4 文本 | 系统执行 SQL（xx ms） | **无此步骤** |
| 步骤 5 文本 | Agent4 业务解读（xx ms） | 已生成经营分析报告 |
| currentSessionAiMessage 分支 | 命中，高亮/进度条正常 | 恒 false，分支走 fallback |
| 实时执行进度标识 | 正确标识当前会话 | 丢失，无法区分历史/当前 |
| AI 消息 content 文本 | 有 LLM 生成的自然语言回复 | **丢失，仅保留结构化 data** |
| detailReportResult | 有缓存可切换详情视图 | 清空，需重新点详情 |
| 执行耗时 startedAt | 可计算总耗时 | 清空，无法展示 |
| 会话 currentSessionId | 可关联后端 trace | 清空，无法追踪 |

### 1.2 差异分类统计

共发现 **11 个差异点**，分为 **A 类关键性差异（影响用户感知/安全/数据完整性）** 6 项，**B 类非关键性差异（体验/性能/边缘）** 5 项。

| 类别 | 数量 | 典型影响 |
|---|---|---|
| A 关键性差异 | 6 | UI 完全不同、越权风险、历史记录永久丢失、刷新前后不一致 |
| B 非关键性差异 | 5 | 体验缺失、性能隐患、脏数据复现 |

---

## 二、详细差异对照表（11 项）

### A 类——关键性差异（6 项）

| 编号 | 差异项 | 实时行为 | 历史恢复行为 | 差异根因代码位置 | 影响评级 |
|---|---|---|---|---|---|
| **A-01** | **执行步骤走硬编码伪分支** | 走 `isCurrentResult=true`，渲染 `session.state.logs` 真实 5 步 trace（每步含耗时/状态/摘要） | 走 `isCurrentResult=false` 分支，硬编码 3 步（理解规划/数据检索/报告生成），无耗时 | **触发条件**：[SmartAsk.vue#L3929-L3933](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/views/SmartAsk.vue#L3929-L3933) `isCurrentResult` 依赖 `session.state.logs.length > 0`；**伪步骤实现**：[SmartAsk.vue#L3944-L3980](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/views/SmartAsk.vue#L3944-L3980) | **⭐P0** 视觉完全不同，用户直接感知"刷新就变样" |
| **A-02** | **session.state.logs 未持久化导致 A-01** | 执行过程中实时写入，含 Agent1~Agent4 每步 trace、SQL、耗时 | **保存时未写入快照**；**恢复时强制置空** | 保存端：[useSmartAskReportHistory.js#L60-L78](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L60-L78) `buildReportHistorySnapshot` snapshot 结构 **无 logs 字段**；恢复端：[useSmartAskReportHistory.js#L175](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L175) `session.state.logs = []` | **⭐P0** 根因性差异，导致 A-01/A-03 直接触发 |
| **A-03** | **isCurrentSessionMessage 恒 false** | `currentSessionAiMessage` 正确命中当前消息，进度/高亮/关联分支正常 | 恒 false，`currentSessionAiMessage` 回退到 `latestAiMessage`，会话关联丢失 | 判定条件：[SmartAsk.vue#L3983-L3989](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/views/SmartAsk.vue#L3983-L3989) 同样依赖 `session.state.logs.length > 0`；下游影响：[SmartAsk.vue#L3998-L3999](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/views/SmartAsk.vue#L3998-L3999) | **⭐P1** 次级渲染分支连锁异常 |
| **A-04** | **前后端历史条数上限不一致——超出静默永久丢失** | 前端请求 `limit=50`，内存状态留 `MAX_HISTORY_ITEMS=50` | 后端实际只留 `MAX_ITEMS_PER_SCOPE=20`，第 21 条起被后端裁掉，前端不知，刷新后永久丢失 | 后端上限：[smartask_report_history_store.py#L22](file:///Users/ltl123/smartask/sa1.0/smartask/backend/smartask_report_history_store.py#L22) `MAX_ITEMS_PER_SCOPE = 20`；前端请求：[api/index.js#L296](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/api/index.js#L296) `limit=50`；前端内存：[smartAskHistory.js#L22-L23](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/state/smartAskHistory.js#L22-L23) `MAX_HISTORY_ITEMS=50 / MAX_LOCAL_HISTORY_ITEMS=20` | **⭐P1** 用户发现"历史少了几条"，无法追查 |
| **A-05** | **历史恢复跳过数据集权限过滤——越权风险** | 实时查询经过 `isDatasetVisible` + `allowed_dataset_ids_for_user` 双校验，无权限数据集被过滤并弹 ElMessage | 历史恢复时**完全没有调用** `filterResultDatasets / isDatasetVisible`，权限回收后仍可从历史看到完整报告 + SQL + 原始数据行 | 实时校验存在：[SmartAsk.vue#L1504-L1508](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/views/SmartAsk.vue#L1504-L1508)（前端 `isDatasetVisible`）、后端 [smart_chat.py#L98-L114](file:///Users/ltl123/smartask/sa1.0/smartask/backend/controllers/smart_chat.py#L98-L114)（`_allowed_dataset_ids` + `_filter_requested_dataset_ids`）；**恢复函数未调用任何校验**：[useSmartAskReportHistory.js#L149-L198](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L149-L198) | **⭐P0 安全** 权限回收≠数据隔离，合规风险 |
| **A-06** | **mergeHistoryItems 服务端绝对优先 + 写入静默失败——刷新前后不一致机制性成因** | 本地新增 → 即时 upsert → 推送服务端 → 下次刷新一致 | ① 服务端完整版无条件覆盖本地 compact 版；② `pushHistoryToServer` 对网络错误/5xx **静默吞掉**（只处理 `stale` 一种错误）；③ 写入失败时本地已更新，下次 `syncFromServer` 拉回服务端旧版，**本地修改永远上不去** | 合并策略：[smartAskHistory.js#L326-L345](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/state/smartAskHistory.js#L326-L345) 服务端 id 存在则本地完全丢弃；写入失败吞：[smartAskHistory.js#L347-L356](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/state/smartAskHistory.js#L347-L356) `catch` 里只判断 `stale`，其余 error 直接返回 `{ok:false,stale:false}`，**无 retry / 无队列 / 无告警** | **⭐P1** 用户直接反馈"刷新前后不一样"的直接成因 |

---

### B 类——非关键性差异（5 项）

| 编号 | 差异项 | 实时行为 | 历史恢复行为 | 差异根因代码位置 | 影响评级 |
|---|---|---|---|---|---|
| **B-01** | AI 消息 content 自然语言文本丢失 | 有 LLM 生成的自然语言描述（问题解析 + 结论摘要） | `restoreSnapshotMessages` 恢复 AI 消息时 **完全不设置 content 字段**，只保留 data | 恢复 AI 消息实现：[useSmartAskReportHistory.js#L119-L135](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L119-L135) 返回结构中无 `content` 字段；对比 user 消息有 content：[L112-L117](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L112-L117) | P2 体验缺失，左侧对话气泡顶部不显示文字摘要 |
| **B-02** | messages 上限 30 条（超长对话截断） | 完整保留会话全量 messages | `normalizeSnapshotMessages` 只留最后 30 条 `slice(-MAX_SNAPSHOT_MESSAGES)` | 截断实现：[useSmartAskReportHistory.js#L42-L58](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L42-L58) `MAX_SNAPSHOT_MESSAGES = 30` | P2 边缘场景（多轮确认/追问）历史恢复后早期上下文丢失 |
| **B-03** | detailReportResult / startedAt / currentSessionId 清空 | 可切换详情视图 + 展示耗时 + 追踪会话 | 强制置空，需用户重新操作 | 清空实现：[useSmartAskReportHistory.js#L173-L178](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L173-L178) | P2 体验缺失（但快照里本来就没持久化 startedAt，合理） |
| **B-04** | `_has_self_parent_anomaly` 校验删除——脏数据快照复现 | 实时数据经过 `_has_self_parent_anomaly` + focusNodeIsLeaf 校验，同名自环脏数据被过滤 | 后端 `_is_stale_history_snapshot` 已**完全注释掉** leaf/self-parent 相关校验（仅保留 ranking top_n 数量校验），之前修过的"每个分公司下挂同名城市公司"脏快照会重新显示 | 后端校验残缺：[smartask_report_history_store.py#L181-L205](file:///Users/ltl123/smartask/sa1.0/smartask/backend/smartask_report_history_store.py#L181-L205) 只校验 ranking top_n，节点 leaf/self-parent 校验在 L203-204 注释说明不再做 | P3 边缘，只有旧历史快照里存在该脏数据时才会出现 |
| **B-05** | 取消 rows/report_spec/messages 裁剪——体积暴涨 + localStorage 超限强压缩 | 原始结果即完整，无额外压缩风险 | ① 单条快照约 385KB，11 条即 7.5MB；② localStorage 上限 ~5MB，必然触发 `compactHistoryItemForLocalAggressive`，"完全保留快照"在本地根本无法达成；③ 后端 JSON 为整文件读写（每次 upsert 全量序列化+重写），7.5MB 多用户并发写入有丢失风险 | 裁剪取消：[smartAskHistory.js#L99-L106](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/state/smartAskHistory.js#L99-L106) `compactDatasetResult` 不再裁剪 rows；强压缩兜底：[L172-L200](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/state/smartAskHistory.js#L172-L200)；后端整文件读写：[smartask_report_history_store.py#L58-L69](file:///Users/ltl123/smartask/sa1.0/smartask/backend/smartask_report_history_store.py#L58-L69) | P2 性能，持续使用后本地必然降级，服务端写入随体积增长变慢 |

---

## 三、数据流程追溯与问题根源分析（全链路 5 环节）

### 3.1 全链路数据流图

```
环节① 实时问数                    环节② 构建快照                    环节③ 服务端存储
┌─────────────────────┐     ┌──────────────────────────┐     ┌──────────────────────────┐
│ SmartAsk.vue        │     │ useSmartAskReportHistory │     │ smartask_report_history_ │
│                     │     │                          │     │ store.py                 │
│ session.state.logs  │────▶│ buildReportHistorySnap-  │────▶│ MAX_ITEMS_PER_SCOPE=20   │
│ session.state.      │     │ shot()                   │     │ _safe_item() 校验        │
│   result (完整)     │     │ ⚠️ 未写入: logs          │     │ _write_store 整文件写     │
│ messages[] (完整)   │     │ ✅ 写入: result,messages │     │                          │
│                     │     │     datasetId,updatedAt  │     │ config/smartask_report_  │
│                     │     │                          │     │ history.json             │
└─────────────────────┘     └──────────────────────────┘     └──────────────────────────┘
                                                                 ▲
                                                                 │ upsert_history 网络请求
环节⑤ 渲染分支               环节④ 历史恢复                      │ (可能静默失败 A-06)
┌─────────────────────┐     ┌──────────────────────────┐     │
│ SmartAsk.vue        │     │ restoreHistory()          │─────┘ syncSmartAskHistoryFromServer()
│                     │     │ ⚠️ session.state.logs=[] │       (服务端绝对优先覆盖本地)
│ isCurrentResult?    │◀────│ ⚠️ 无权限过滤 A-05       │
│   true → 真实5步    │     │ ⚠️ detailReportResult=null│
│   false → 硬编码3步 │     │ ⚠️ startedAt/currentSe-  │
│                     │     │      ssionId=''          │
└─────────────────────┘     └──────────────────────────┘
```

### 3.2 各环节技术因素排查

| 环节 | 是否存在问题 | 具体技术因素 |
|---|---|---|
| **① 实时问数** | ❌ 无问题 | 数据层已实测清白（token 直调 `/api/smart-chat` 与快照同问题对比：result 21 字段全同、SQL 完全一致、rows 内容一致；仅 JSON 浮点序列化噪声 `6105486.0` vs `6105486`） |
| **② 构建快照** | ✅ **问题** | (1) **logs 未持久化**（A-02 根因）；(2) messages slice(-30)（B-02）；(3) content 未写入 messages[].data 的对应 AI 消息（B-01）；(4) rows/messages 完全不裁剪 → 体积暴涨（B-05） |
| **③ 服务端存储** | ✅ **问题** | (1) MAX_ITEMS_PER_SCOPE=20 < 前端请求 50（A-04）；(2) 整文件读写，7.5MB 体积增长慢 + 并发理论丢失风险（B-05）；(3) stale 校验只保留 ranking top_n，leaf/self-parent 注释（B-04）；(4) list_history GET 路由**零权限过滤**，返回 dataset_results 原始行，无数据集权限校验（A-05 后端端） |
| **④ 历史恢复** | ✅ **问题** | (1) 强制 `session.state.logs = []`（A-01/A-02 触发点）；(2) restore AI 消息丢 content（B-01）；(3) 无 `isDatasetVisible` / filterResultDatasets（A-05 前端端）；(4) detailReportResult/startedAt/currentSessionId 清空（B-03） |
| **⑤ 渲染层** | ✅ **问题（连锁）** | (1) `isCurrentResult` 判定包含 `logs.length>0`，与"历史恢复必然 logs=[]"形成死锁（A-01 判定逻辑不合理）；(2) `isCurrentSessionMessage` 同样依赖 logs，双重锁死（A-03） |

### 3.3 核心根源归纳（3 条结构性根因）

#### 根因 R1：**持久化契约与恢复契约不对称——判定条件过度依赖运行态内存字段**
- 快照构建时不写 `logs`，但渲染分支判定 `isCurrentResult` 要求 `logs.length>0`
- 恢复时为了"区分历史 vs 当前"粗暴清空 logs，导致历史恢复的渲染**必然**走伪步骤分支
- **本质**：恢复后想表达"这是历史快照，不是当前正在执行的"，但选中的信号载体（logs）恰好又是步骤卡片渲染的数据源——一鱼两吃冲突

#### 根因 R2：**写入可靠性设计缺陷（无 retry/无队列/无用户反馈）+ 合并策略单边倾向**
- `pushHistoryToServer` 作为后台 fire-and-forget，网络抖动/5xx 时完全无兜底（本地已写 localStorage，下次 `syncFromServer` 拉回旧版 → "刷新就变回去"）
- `mergeHistoryItems` 服务端绝对优先，是配合"完全保留快照"重构引入的新策略，但未配套写入可靠机制
- **本质**：分布式最终一致性的常见错——"相信服务端一定写成功，但实际上并未保证"

#### 根因 R3：**权限校验只在写入路径，未对称覆盖读取/恢复路径**
- 实时问数：数据集选择 → `isDatasetVisible` 前端过滤 → `_allowed_dataset_ids` 后端过滤（双保险）
- 历史 GET：`list_report_history` 直接按 scope 全量返回 → 用户拿到 JSON 就能看到任何 dataset_id 的结果行
- 历史恢复：前端完全不做权限比对 → 即使 datasets.value 中已无该 dataset_id，快照 result 仍然完整渲染
- **本质**：新增功能（历史恢复）时只考虑"存/取"流程，未将现有权限矩阵对称纳入

---

## 四、测试验证方案（不修改任何代码，可立即执行）

### 4.1 测试环境配置

| 项目 | 配置要求 |
|---|---|
| 部署方式 | Docker compose 三服务（postgres/backend/frontend），与生产一致 |
| 浏览器 | Chrome 最新版 + DevTools 打开 Network + Application 面板 |
| 测试账号 | 2 个：① super_admin（全数据集权限）；② 普通角色（仅数据集 2 权限） |
| DevTools 预设 | Application → Local Storage 监控 `smartask_history_sessions_v2:*`；Network → 筛选 `/smart-chat/report-history`；Console 保留日志 `Preserve log` 勾选 |

### 4.2 测试用例总览（10 用例，覆盖 A/B 类全部差异点）

| TC 编号 | 目标差异 | 测试场景 | 预期（验证存在此问题） | 关联差异 |
|---|---|---|---|---|
| TC-01 | A-01 伪步骤 | 问「山东分公司的业绩」→ 完成 → 截图步骤卡片 → 刷新 → 点击历史恢复 → 截图对比 | 实时 = 5 步真实 trace（带耗时）；历史恢复 = 3 步硬编码 | A-01, A-02 |
| TC-02 | A-02 logs 持久化 | 同 TC-01，DevTools → Application → LocalStorage → 查看对应快照 JSON | 快照 `reportSnapshot` 下**没有 logs 字段**，或 `logs = []` | A-02 |
| TC-03 | A-03 isCurrentSessionMessage | 同 TC-01，DevTools → Vue Devtools → 查看 `currentSessionAiMessage` 计算属性 | 实时 = 最后一条 AI 消息 id；历史恢复 = 回退到 latestAiMessage | A-03 |
| TC-04 | A-04 条数上限 | 用 super_admin 连续问 25 个不同问题 → 刷新 → 数左侧历史列表条数 | 服务端实际只返回 20 条，第 21-25 条永久丢失（即使前端 localStorage 里有 25 条） | A-04 |
| TC-05 | A-05 越权（前置：2 账号） | ① super_admin 问数据集 3「商用事业部的业绩」→ 保存；② 登出换普通账号（仅数据集 2）→ 打开历史列表 | 普通账号仍能看到 super_admin 的历史（scope 隔离保证）→ **进阶测试**：手动把同一 scope 下用户权限从"数据集 3"降级为"数据集 2"，再打开历史 | 降级后历史仍显示数据集 3 完整报告 + SQL + rows（A-05 验证） | A-05 |
| TC-06 | A-06 静默失败刷新不一致 | 在 TC-01 保存后，DevTools → Network → 对 `/report-history` POST 设置 Block request domain → 新增 1 条问题 → 刷新页面 | 新增那条在刷新后消失（本地写了但服务端没写，syncFromServer 拉回无它，mergeHistoryItems 服务端优先覆盖本地） | A-06 |
| TC-07 | B-01 AI content 丢失 | 同 TC-01，对比左侧对话气泡顶部 AI 自然语言文本 | 实时有文字；历史恢复后气泡顶部**无自然语言文字**，直接显示卡片 | B-01 |
| TC-08 | B-02 messages 截断 | 追问 35 轮（每轮提一个子问题，如「那粤桂琼呢？」「那山东呢？」…）→ 保存 → 恢复 → DevTools 看 messages 长度 | 恢复后 messages 长度 = 30，非 35+ | B-02 |
| TC-09 | B-03 三项清空 | 同 TC-01，Vue Devtools 查看 detailReportResult / session.state.startedAt / session.state.currentSessionId | 实时三项均有值；历史恢复三项 = null / '' / '' | B-03 |
| TC-10 | B-05 体积暴涨 | 连续问 10 个包含 80+ rows 的结果（如"消费者所有城市分公司业绩"）→ DevTools → Application → LocalStorage → 查看 JSON 大小；同时看后端 `config/smartask_report_history.json` 大小 | localStorage 对应 key 体积 > 4.5MB 后，下次写入必然触发 aggressive 压缩（Console 有 warn）；服务端 JSON ≥ 3MB，每次 upsert 有体感延迟 | B-05 |

### 4.3 测试执行步骤模板（以 TC-01 为例）

```
【TC-01 执行步骤】
1. docker compose up -d --build  （确保三服务 healthy）
2. 浏览器打开 http://localhost，用 super_admin 登录
3. DevTools: Network tab → 筛选 Fetch/XHR → 选 Preserve log；Application tab → 展开 Local Storage
4. 截图 1（基准）：首页空状态截图，记录时间戳 T0
5. 输入「山东分公司的业绩」→ 回车 → 等待执行完成
6. 截图 2（实时步骤卡）：完整页面截图，重点保留 AI 气泡中的 5 步执行步骤列表
7. DevTools → Vue → 选中 SmartAsk 组件 → 记录 session.state.logs 的数量和摘要（应 ≈5 条，含 Agent1/Agent3/执行 SQL 等 key）→ 截图 3
8. DevTools → Application → Local Storage → 找到最新写入的历史条目 JSON → 展开 reportSnapshot → 确认无 logs 字段 → 截图 4
9. Ctrl+F5 强刷新页面
10. 左侧历史列表找到刚那条「山东分公司的业绩」→ 点击
11. 截图 5（历史恢复步骤卡）：完整页面截图，AI 气泡中步骤卡
12. 对比截图 2 vs 截图 5 → 应能观察到 A-01（步骤数和文案不同）
13. DevTools → Vue → 查看 session.state.logs → 应 = [] → 截图 6
14. 报告输出：6 张截图 + 对比结论

【TC-01 判定规则】
- PASS（差异存在）：步骤卡片 = 硬编码 3 条，session.state.logs=[]
- N/A：如果快照中成功写入 logs 且历史恢复 logs≠[]，则 A-01/A-02 不成立
```

### 4.4 截图证据保存规范

每张截图文件名：

```
deliverables/screenshots/TC-{编号}-{序号}-{说明}.png
例：deliverables/screenshots/TC-01-02-实时5步步骤卡.png
```

在报告对应 TC 中嵌入，同时在 JSON 证据目录中保存原始快照 diff：

```
deliverables/evidence/TC-{编号}-{快照键}.json
```

---

## 五、解决方案与实施步骤（代码级详细方案，等待确认后实施）

> **说明**：本章节方案为纯设计稿，**本轮不执行任何代码修改**。用户确认方案后进入下一阶段排期实施。

### 5.1 方案优先级矩阵

| 编号 | 方案项 | 对应根因/差异 | 优先级 | 风险 | 预估人天 |
|---|---|---|---|---|---|
| S1 | 拆分「是否为当前执行信号」与「步骤卡数据源」——新增 `session.state.isHistoricalSnapshot` bool | R1 / A-01, A-02, A-03 | P0 必做 | 低（纯前端渲染判定重构） | 1d |
| S2 | logs 对称持久化：快照写入 + 恢复还原 | A-02 / 连锁解决 A-01 | P0 必做 | 中（快照体积增大，需配套裁剪策略） | 0.5d |
| S3 | 历史恢复路径数据集权限双校验（前端 + 后端） | R3 / A-05 安全 | P0 必做 | 低（复用现有 isDatasetVisible 与 allowed_dataset_ids_for_user） | 1d |
| S4 | 写入可靠性：retry + 队列 + syncGeneration 保护 | R2 / A-06 | P1 重要 | 中（状态机变复杂，需加单元测试） | 1.5d |
| S5 | 前后端历史条数上限对齐 + 告警 | A-04 | P1 重要 | 低（常量统一 + 前端超量提示） | 0.3d |
| S6 | restore AI 消息 content 还原 | B-01 | P2 体验 | 低 | 0.3d |
| S7 | 快照体积策略：服务端 2MB 单条上限 + 分层裁剪（先截 prompt/trace 再截 rows 前 200） | B-05 | P2 体验 | 中（需要真实数据做体积回归） | 1d |
| S8 | MAX_SNAPSHOT_MESSAGES 提升到 100 + 长对话告警 | B-02 | P3 边缘 | 低 | 0.2d |
| S9 | detailReportResult 历史恢复时用 result.dataset_results[0] 预填充 | B-03 | P3 边缘 | 低 | 0.2d |
| S10 | 后端 stale 校验补回 focusNode leaf + 自环（可配置开关） | B-04 | P3 边缘 | 低（加开关，默认关闭，保留历史） | 0.5d |

### 5.2 关键方案 S1/S2 详细设计（解决 R1 核心死锁）

#### S1 设计稿

**目标**：历史恢复后，步骤卡显示真实 5 步，但不被误认为是"当前正在执行的会话"。

**改动点设计**：

```
[SmartAsk.vue] 判定重构：
- 新增 session.state.isHistoricalSnapshot: bool（默认 false）
- restoreHistory() 末尾写 session.state.isHistoricalSnapshot = true
- 新问数 / 清空时写 session.state.isHistoricalSnapshot = false

isCurrentResult（用于步骤卡数据源选择）判定调整：
const isCurrentResult =
  msg.data?.question &&
  session.state.question &&
  msg.data.question === session.state.question &&
  session.state.logs.length > 0                        // ← 只要有 logs 就展示真实步骤，不区分历史/当前

isCurrentSessionRunningMessage（用于"执行中"相关分支，区分历史 vs 当前）：
const isCurrentSessionMessage = (msg) =>
  !session.state.isHistoricalSnapshot &&               // ← 新增：只有非快照会话才标记"当前会话"
  msg?.data?.question &&
  session.state.question &&
  msg.data.question === session.state.question &&
  session.state.logs.length > 0

视觉辅助：历史快照的步骤卡容器加 .sa-historical-steps 类，
          CSS 降一级透明度/加"历史快照"角标，保留可读性同时视觉可区分。
```

#### S2 设计稿（logs 对称持久化 + 体积友好裁剪）

```
[useSmartAskReportHistory.js]
buildReportHistorySnapshot(result) 新增字段：
  logs: (session.state.logs || [])
    .map(log => ({                                // 只保留渲染必要字段，丢弃 rawDebug/prompt 等
      key: log.key,
      title: log.title,
      summary: log.summary,
      status: log.status,
      durationMs: log.durationMs,
      sql: log.sql ? log.sql.slice(0, 4000) : undefined,   // SQL 超长截断
      detailLines: Array.isArray(log.detailLines)
        ? log.detailLines.slice(0, 5).map(line => String(line).slice(0, 500))
        : undefined,
    }))
    .slice(0, 50)                                 // 最多 50 步，极端场景上限

restoreHistory(item)：
  session.state.logs = clone(
    reportSnapshot.logs || item.sessionState?.logs || []
  )
  // 不再强制 = []
```

#### S3 设计稿（权限对称）

```
[前端 useSmartAskReportHistory.js#restoreHistory] 恢复前校验：
const result = reportSnapshot.result
if (result?.dataset_results?.length) {
  const visible = result.dataset_results.filter(ds => isDatasetVisible(ds?.dataset_id))
  if (visible.length === 0) {
    ElMessage.warning('当前账号没有访问该历史记录数据集的权限，已隐藏报告内容。')
    session.state.result = { ...clone(result), dataset_results: [], error: '权限不足，历史报告已隔离。' }
    // 只保留 question 元信息，不展示数据行
  } else if (visible.length < result.dataset_results.length) {
    ElMessage.info(`${result.dataset_results.length - visible.length} 个无权限数据集已从历史报告中过滤。`)
    session.state.result = { ...clone(result), dataset_results: visible }
  }
}

[后端 smart_chat.py#get_report_history] 返回前按权限裁剪：
user = get_current_user()
allowed = set(_allowed_dataset_ids(user))
history = list_report_history(user, limit=limit)
history = history.map(item => {
  const snapshot = item.reportSnapshot
  if (snapshot?.result?.dataset_results) {
    const filtered = snapshot.result.dataset_results.filter(ds => allowed.has(ds.dataset_id))
    // 全被过滤则删除 result.dataset_results，保留元信息
    snapshot.result = { ...snapshot.result, dataset_results: filtered }
  }
  return { ...item, reportSnapshot: snapshot }
})
```

### 5.3 实施顺序建议（分两期）

**一期——P0 必做（2.5 人天，立即排）**：S1 → S2 → S3
- 完成后：用户感知"恢复后显示真实步骤 + 权限不越界"，核心视觉/安全问题解决
- A-01/A-02/A-03/A-05 全部解决

**二期——P1/P2/P3（~4 人天，下个迭代）**：S4 → S5 → S6 → S7 → S8 → S9 → S10
- 完成后：刷新前后一致、条数上限对齐、写入可靠、体积可控
- A-04/A-06/B-01/B-02/B-03/B-04/B-05 全部解决

---

## 六、长效数据一致性保障机制

### 6.1 契约测试（新增 CI 任务，每次 PR 跑）

| 测试名 | 校验内容 | 失败场景 |
|---|---|---|
| `test_snapshot_restore_contract_symmetry` | ① 实时 result → `buildReportHistorySnapshot` → 反序列化 → `restoreHistory` → 最终 session.state.result 与原始 result 做字段级 diff（允许白名单字段差异：startedAt/currentSessionId/logs 裁剪/content 压缩噪声）；② logs 字段必须非空；③ dataset_results 数量/每行前 5 列一致 | 快照保存/恢复契约任何字段回归立即失败 |
| `test_snapshot_backward_compat_v1_v2` | 注入 v1（无 logs 字段）旧快照，断言 restoreHistory 不崩且走伪步骤 fallback | 重构时误删旧快照兼容 |
| `test_history_restore_permission_matrix` | 4 组数据集权限组合 × 3 组历史快照包含的 dataset_ids 交叉，断言返回的 dataset_results ≤ 权限集的幂集 | A-05 回归立即失败 |

### 6.2 写入可靠性监控（运维侧）

- `pushHistoryToServer` 连续 3 次失败：Console error + ElMessage 右下角静默提示"有 N 条历史记录暂未同步到服务器"（不打断用户）
- 后端 `_write_store` 前后 JSON 体积差 > 512KB：system_log_store 记 warn event
- 后端 `MAX_ITEMS_PER_SCOPE` 裁剪：每次裁掉条目时 system_log_store 记 info，附带裁掉的 question/updatedAt 便于用户反馈时溯源

### 6.3 数据健康巡检（周级 cron）

后端 `audit_history_store.py` 每周跑一次，输出：
1. 各 scope 条数分布、最大/95 分位单条体积
2. stale 快照数量（top_n 不符 / leaf 不符 / 自环）
3. 权限漂移快照数量（以当前 dataset_permission.json 回扫历史，列出已回收权限但仍存在完整 rows 的快照 id 清单）

### 6.4 版本契约（前后端兼容）

- `reportSnapshot.version`：当前 v2。任何一次快照字段结构变更必须 +1
- `restoreHistory` 根据 version 走不同解码器，禁止直接改 v2 字段语义
- v3 引入字段：`logs`, `isHistoricalSnapshot: true`, `schema_version: 'v3'`

---

## 七、风险与未决事项（需用户确认）

| 编号 | 事项 | 对方案影响 | 建议 |
|---|---|---|---|
| D1 | 「完全保留快照」重构的原始诉求是否仍成立？ | S2/S7 重新引入 rows/logs 裁剪会和该诉求冲突；B-05 已证实"完全保留"在 localStorage 5MB 上限下**物理不可行** | 建议改为"分层保留"：SQL/步骤卡/核心结论 100%；rows 留前 500 行；prompt/trace/debug 字段裁剪 |
| D2 | 历史记录条数上限取多少？ | 前后端需统一。当前后端 20 过于激进、前端 50 对服务端 JSON 体积压力大 | 建议统一为 30 条，并在前端超量时弹「已满 30 条，最旧一条已归档至下载文件」的导出兜底 |
| D3 | S3 权限裁剪后老历史如何处理？ | 两种策略：① 读取时即时裁剪（不破坏存储，兼容权限恢复）；② 后端巡检脚本物理清理已无权限快照 | 推荐 ①，不丢用户数据；若合规要求严格则执行 ② 前先导出备份 |

---

## 八、附：差异代码引用索引（全文可点击）

| 主题 | 文件与行号 |
|---|---|
| isCurrentResult 判定（死锁源头） | [SmartAsk.vue#L3929-L3933](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/views/SmartAsk.vue#L3929-L3933) |
| 硬编码伪步骤实现 | [SmartAsk.vue#L3944-L3980](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/views/SmartAsk.vue#L3944-L3980) |
| isCurrentSessionMessage 判定 | [SmartAsk.vue#L3983-L3989](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/views/SmartAsk.vue#L3983-L3989) |
| buildReportHistorySnapshot（未写 logs） | [useSmartAskReportHistory.js#L60-L78](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L60-L78) |
| restoreHistory（logs=[] 触发点 + 无权限过滤 + 三字段清空） | [useSmartAskReportHistory.js#L149-L198](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L149-L198) |
| AI 消息恢复未写 content | [useSmartAskReportHistory.js#L119-L135](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L119-L135) |
| MAX_SNAPSHOT_MESSAGES=30 截断 | [useSmartAskReportHistory.js#L42-L58](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/composables/useSmartAskReportHistory.js#L42-L58) |
| mergeHistoryItems 服务端绝对优先 | [smartAskHistory.js#L326-L345](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/state/smartAskHistory.js#L326-L345) |
| pushHistoryToServer 静默吞错误 | [smartAskHistory.js#L347-L356](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/state/smartAskHistory.js#L347-L356) |
| 前后端条数上限 50 vs 20 | 前端 [smartAskHistory.js#L22-L23](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/state/smartAskHistory.js#L22-L23)；后端 [smartask_report_history_store.py#L22](file:///Users/ltl123/smartask/sa1.0/smartask/backend/smartask_report_history_store.py#L22) |
| 后端 stale 校验仅保留 ranking top_n | [smartask_report_history_store.py#L181-L205](file:///Users/ltl123/smartask/sa1.0/smartask/backend/smartask_report_history_store.py#L181-L205) |
| 后端 GET 历史零权限过滤返回路径 | [smart_chat.py#L48-L52](file:///Users/ltl123/smartask/sa1.0/smartask/backend/controllers/smart_chat.py#L48-L52) |
| 实时问数路径权限校验参考实现 | 前端 [SmartAsk.vue#L1504-L1508](file:///Users/ltl123/smartask/sa1.0/smartask/frontend/src/views/SmartAsk.vue#L1504-L1508)；后端 [smart_chat.py#L98-L114](file:///Users/ltl123/smartask/sa1.0/smartask/backend/controllers/smart_chat.py#L98-L114) |

---

> **报告完毕**。本阶段产出：
> 1. 11 项差异对照表（A 类 6 项 / B 类 5 项）
> 2. 全链路 5 环节追溯 + 3 条结构性根因
> 3. 10 条可立即执行的测试用例（无需改代码），附步骤模板 + 截图规范
> 4. 10 个方案项（S1~S10），分两期实施，附 3 条结构性核心方案的伪代码设计稿
> 5. 4 项长效保障机制 + 3 项待确认决策
