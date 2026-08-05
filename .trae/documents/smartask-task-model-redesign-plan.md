# SmartAsk 任务模型与历史对话交互改造计划

## Context

用户反馈当前 SmartAsk 左侧「历史分析」列表与主区实时对话的交互存在多处不一致：

1. 执行中切换历史对话会中断当前任务或无响应。
2. 执行中/待确认任务在左侧不可见，切走后无法切回。
3. 待确认状态直接弹回实时执行界面，干扰查看历史。
4. 重新问（re-ask）会创建两个任务条目。
5. 历史快照与实时数据偶尔错乱。

本次目标是把左侧从「历史对话框」升级为「任务对话框」，复刻 Workbuddy 的左侧任务列表交互：

- 一次问数 = 一个任务项，生命周期状态：执行中 / 待确认 / 已完成 / 失败。
- 执行中/待确认任务始终可在左侧找到并切回。
- 切换历史对话不中断后台 SSE。
- re-ask 复用同一任务 ID，不重复创建条目。
- 历史视图只读，实时视图与历史视图数据源隔离。

本计划按全栈研发专家团 SOP「增量模式」执行，先完成 Phase 0 项目公约勘察，再进入 Phase 2 架构设计，最终形成可实施的改造方案。

---

## 1. 项目公约摘要（Phase 0）

| 维度 | 现状 |
| --- | --- |
| 技术栈 | Vue 3.5 + Vite 8 + Element Plus + ECharts；状态管理以组合式函数 + reactive/ref 为主；持久化用 localStorage/sessionStorage。 |
| 目录约定 | 业务状态放 `frontend/src/state/`；可复用逻辑放 `frontend/src/composables/`；页面放 `frontend/src/views/`；组件放 `frontend/src/components/`。 |
| 既有模式 | 错误处理：`ElMessage` 提示 + `console.warn`；日志格式：`[module] message`；配置读取走 `featureFlags`；历史同步走 `api/index.js`。 |
| 质量基线 | 前端无显式 lint 脚本；后端用 `pytest`；部署用 `docker-compose up`。 |
| 禁区 | `backend/four_agent_ask.py`（上帝文件）不动；不引入新 npm 包；不改动后端接口契约。 |

---

## 2. 核心设计决策

### 2.1 双态视图（唯一新增全局概念）

新增 `frontend/src/state/smartAskTaskView.js`，职责单一：

- `runningSessionId`：后台正在执行 SSE 的任务 ID。
- `viewingTaskId`：主区当前显示的任务 ID，`'default'` 表示实时视图。
- `inReadonlyMode`：表示当前正在查看历史快照。

切换历史时只改 `viewingTaskId`，绝不调用 `stopAsk/resetSession`。任何会写 `messages / session.state` 的函数开头先判断 `inReadonlyMode`，若是则先 `switchViewToDefault()`。

### 2.2 任务模型

历史条目在现有字段上新增：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string | `running` / `pending_confirmation` / `completed` / `failed` |
| `taskStartedAt` | number/string | 任务开始时间戳 |
| `errorMessage` | string | 失败原因，运行/成功时为空 |
| `reportSnapshot.result` | object \| null | 运行壳任务可为 `null` |

旧历史无 `status` 时由 `normalizeTaskFields` 自动推断：

- `result.error` → `failed`
- `result.requires_confirmation` → `pending_confirmation`
- `result` 存在且无异常 → `completed`
- 无 `result` → `running`

### 2.3 任务 ID 复用

- 新问题：`handleSend` 生成新的 `taskId`（`task-shell-${timestamp}-${random}`）。
- re-ask：`rerunQuestion` 复用 `viewingTaskId !== 'default' ? viewingTaskId : currentTaskId`。
- 确认：`doConfirm` 沿用 `currentTaskId`。
- 完成/失败：`saveCurrentToHistory(result, { preferId: taskId })` 用同一 ID 覆盖壳任务。

### 2.4 左侧任务列表

- 任务按状态优先级排序：`running` > `pending_confirmation` > `failed` > `completed`。
- 当前 `runningSessionId` 对应的任务在固定入口展示，同时在下方列表中过滤掉，避免重复。
- 点击 `running/pending_confirmation`：切回实时视图。
- 点击 `completed/failed`：进入只读历史视图。
- 状态指示器统一用组件 `TaskStatusIndicator.vue`。

### 2.5 渲染数据源隔离

`SmartAsk.vue` 统一使用以下 computed 作为渲染源：

- `displayMessages`
- `displayLogs`
- `displayResult`
- `displayStatus`
- `displayQuestion`

只读模式下指向 `readonlySnapshot`，否则指向实时 `messages / session.state`。

---

## 3. 文件清单与变更范围

| 文件 | 变更 | 职责 |
| --- | --- | --- |
| `frontend/src/state/smartAskTaskView.js` | 新增 | 双态视图全局状态 |
| `frontend/src/state/smartAskHistory.js` | 修改 | 任务状态字段、壳任务 upsert、合并保留本地状态、同步过滤 |
| `frontend/src/composables/useSmartAskReportHistory.js` | 修改 | 只读快照构建、`saveCurrentToHistory(preferId)`、恢复逻辑适配 |
| `frontend/src/views/SmartAsk.vue` | 修改 | 渲染隔离、任务状态同步、历史切换不断 SSE、写前切回实时视图 |
| `frontend/src/App.vue` | 修改 | 左侧任务列表、状态 badge、置顶排序、点击行为区分 |
| `frontend/src/components/TaskStatusIndicator.vue` | 新增 | 任务状态指示器组件 |

后端与接口契约均不改动。

---

## 4. 关键改造点

### 4.1 `smartAskHistory.js`

1. 新增 `TASK_STATUS` 常量。
2. `normalizeHistoryItem`：允许 `reportSnapshot.result === null` 的壳任务通过校验。
3. `normalizeTaskFields`：推断旧记录状态，补齐 `taskStartedAt`、`errorMessage`。
4. `upsertTaskStatus(id, status, opts)`：更新或创建壳任务，保持列表置顶。
5. `mergeHistoryItems`：服务端条目优先保留完整快照，但本地状态字段不被覆盖。
6. `saveHistoryItemInBackground`：非 `completed` 状态不同步到服务端，避免脏数据。
7. 压缩函数兼容 `result` 为 `null` 的壳任务。

### 4.2 `useSmartAskReportHistory.js`

1. `buildReportHistorySnapshot`：不再拦截 `error/requires_confirmation`，允许保存失败/待确认快照。
2. `saveCurrentToHistory(result, options)`：支持 `preferId` 复用任务 ID；自动根据结果设置 `status/errorMessage`。
3. `restoreHistory`：保留现有权限过滤与双写一致修复；若当前有执行中任务，不阻塞，仅切换视图。
4. 新增 `mountReadonlySnapshot(item)` / `clearReadonlySnapshot()` 供 `SmartAsk.vue` 只读模式使用。

### 4.3 `SmartAsk.vue`

1. 引入 `useSmartAskTaskView`。
2. 新增 `currentTaskId`、`readonlySnapshot` 等状态。
3. 新增 `displayMessages`、`displayLogs`、`displayResult`、`displayStatus`、`displayQuestion` computed。
4. 模板渲染统一改用 `display*` 系列。
5. `handleSend`、`rerunQuestion`、`doConfirm`、`handleStop`、`resetForNewChat` 开头加 `if (inReadonlyMode.value) switchViewToDefault()`。
6. `handleSend`：先创建 `RUNNING` 壳任务，再推用户消息，调用 `startAsk`。
7. SSE 结果处理：根据 `requires_confirmation/error/completed` 调用 `upsertTaskStatus` 或 `saveCurrentToHistory(preferId)`。
8. `watch(pendingRestoreId)`：不再调用 `restoreHistory` 覆盖会话状态，改为 `setActiveHistory(historyId); viewingTaskId.value = historyId; readonlySnapshot.value = buildReadonlySnapshot(item)`。
9. 监听 `session.state.logs/result/status` 的自动滚动/展开逻辑：只读模式下跳过。

### 4.4 `App.vue`

1. 引入 `TASK_STATUS`、`useSmartAskTaskView`。
2. `sortedTasks`：按状态优先级 + 时间倒序排序。
3. `currentRunningTask`：取 `runningSessionId` 对应的任务。
4. `historyPreviewList`：过滤掉 `runningSessionId` 对应任务，避免与固定入口重复。
5. 顶部固定入口展示当前 `running/pending_confirmation` 任务，点击切回实时视图。
6. 历史列表项展示状态 badge、数据集、更新时间。
7. 抽屉列表同样排序和过滤。

### 4.5 `TaskStatusIndicator.vue`

- 支持 `running/pending_confirmation/completed/failed` 四种状态。
- `running/pending_confirmation` 共用绿色旋转动画（与 Workbuddy 对齐）。
- `completed` 为绿色实心点。
- `failed` 为红色感叹号。
- 可选显示文字标签或耗时。

---

## 5. 任务执行顺序

| # | 任务 | 依赖 | 说明 |
| --- | --- | --- | --- |
| 1 | 新增 `smartAskTaskView.js` | 无 | 先确定全局双态 API |
| 2 | 扩展 `smartAskHistory.js` 任务模型 | #1 | 状态常量、壳任务 upsert、合并同步 |
| 3 | 改造 `useSmartAskReportHistory.js` | #2 | 只读快照、saveCurrentToHistory(preferId) |
| 4 | 新增 `TaskStatusIndicator.vue` | 无 | 独立状态组件 |
| 5 | 改造 `SmartAsk.vue` 渲染隔离与状态同步 | #1, #2, #3 | display* computed、写前切视图、任务状态流转 |
| 6 | 改造 `App.vue` 左侧任务列表 | #1, #2, #4 | 置顶排序、固定入口、状态 badge |
| 7 | 回归测试与边界修复 | #5, #6 | 验证 5+ 场景 |

---

## 6. 验收标准（回归测试场景）

1. **执行中切换历史不中断**
   - 发送问题后左侧出现「执行中」任务。
   - 点击已完成历史，主区进入只读历史视图。
   - 后台 SSE 继续推进，左侧「执行中」任务仍在。
   - 再次点击「执行中」任务，回到实时视图，结果正常返回。

2. **re-ask 不复用新 ID**
   - 对某条用户问题点击「重新问」。
   - 左侧同一个任务 ID 的状态从 `completed` 变 `running`，完成后仍是同一 ID。
   - 列表无重复条目。

3. **待确认不自动跳转**
   - 问一个会触发口径确认的问题。
   - 在确认出现前切到历史视图。
   - 左侧任务变为「待确认」，主区仍停留在历史视图。
   - 点击左侧「待确认」任务才回到实时视图显示确认卡片。

4. **停止/失败后状态正确**
   - 执行中点击停止，左侧该任务变为「失败」。
   - 再次发送新问题，生成新的任务 ID，旧失败条目保留。

5. **刷新后无残留「执行中」**
   - 刷新页面前有运行中任务。
   - `runningSessionId` 为空后，左侧把残留 `running` 显示为「失败」或过滤，不会永久卡住。

6. **历史视图只读隔离**
   - 查看历史时，实时 session 的 `messages / logs / result` 不被污染。
   - 在历史视图发送新问题，先切回实时视图，且作为新任务执行。

7. **新建会话/清除历史**
   - 点击「新会话」后当前任务高亮清空，主区回到实时视图。
   - 清空历史后，若正在查看某条历史，自动切回实时视图。

---

## 7. 风险与回退

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| `SmartAsk.vue` 体积大，渲染 computed 遗漏 | 中 | 模板中以顶层 `display*` 收口，grep 复核所有 `session.state.result/logs` 引用。 |
| 服务端同步覆盖本地状态 | 中 | `mergeHistoryItems` 显式保留本地 `status` 等字段；非 completed 任务不同步到服务端。 |
| 运行中壳任务只存本地，清浏览器数据丢失 | 低 | 运行中任务 ephemeral 是预期行为；完成后会同步到服务端。 |

回退策略：所有改动集中在前端 5 个文件，可单独回滚 `SmartAsk.vue` 与 `App.vue`，`smartAskHistory.js` 新增字段不会破坏旧逻辑。

---

## 8. 验证方式

1. 本地静态检查：确认无新增依赖、无语法错误。
2. Docker 构建：`docker-compose up -d --build`（前端镜像 `--no-cache`）。
3. 健康检查：前后端容器启动正常，登录后可进入智能分析工作台。
4. 功能验证：按第 6 节 7 个场景逐一验证。
5. 浏览器缓存：提示用户强制刷新 `Ctrl+Shift+R` / `Cmd+Shift+R`。
