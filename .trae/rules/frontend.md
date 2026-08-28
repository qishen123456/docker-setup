<!-- AUTO-GENERATED from .agents/rules/ - DO NOT EDIT. Edit the source and rerun scripts/sync-ide-rules.ps1 -->
---
# Trae rule - frontend only
alwaysApply: false
globs:
  - "frontend/**/*.{vue,js,ts,css}"
---

# SmartAsk 前端开发规范

> Antigravity 工作区规则 - 处理 `frontend/` 下的文件时自动生效。
> 激活方式建议设为 Glob: `frontend/**/*.{vue,js,ts,css}`

## 技术栈

- Vue 3.5 (`<script setup>`) + Vite 8 + Element Plus 2.x + ECharts 6
- 路由：vue-router 4 | HTTP：axios | Markdown：marked + highlight.js

## 目录约定

| 目录 | 放什么 |
|---|---|
| `frontend/src/views/` | 页面级组件 |
| `frontend/src/components/` | 可复用组件 |
| `frontend/src/api/` | API 调用封装（统一走这层） |

## 规范

- 组件用 `<script setup>` 语法，不用 Options API
- 用 Element Plus，不引入其他 UI 库
- 图表用 ECharts，封装成独立组件放 `components/`
- API 调用统一走 `api/` 层，组件不直接调 axios
- 响应式样式用项目既有断点，不引入 Tailwind 或其他 CSS 框架
- 构建：`cd frontend && npm run dev` / `npm run build`

## SmartAsk 前端对话核心约束（AI 快速上手版）

> 只列 AI 改代码时必须知道的硬约束，团队执行细节见对应 SKILL.md。

### 1. 双态视图（切历史不打断 SSE）
- `runningSessionId`：后台正在执行的任务（SSE 绑定），切历史绝不调用 stopAsk/abort/resetSession。
- `viewingTaskId`：主区正在查看的任务（`'default'`=实时视图，其他 id=只读历史快照）。
- 只要 `inReadonlyMode.value === true`，所有写 messages / session.state 的函数开头必须先 `switchViewToDefault()` 切回实时视图。

### 2. 渲染数据源切换（禁止直读原始 messages / session.state）
- 渲染层统一用 SmartAsk.vue 的 3 个 computed：`displayMessages` / `displayLogs` / `displayResult`。
- 3 个 computed 会自动判断是否只读模式：只读时指向 readonlySnapshot，否则指向实时 session/messages，互不污染。

### 3. 任务状态 & 同 ID 复用
- 统一状态枚举 `TASK_STATUS`：`RUNNING` → `PENDING_CONFIRMATION` → `COMPLETED` / `FAILED`；左侧任务列表按此状态置顶排序（执行中/待确认永远最上面）。
- 问数流程关键节点必须调 `upsertTaskStatus(shellId, status)` 同步到左侧：startAsk 前=RUNNING、返回 requires_confirmation=PENDING、error 或 用户主动停止=FAILED、最终成功=saveCurrentToHistory(preferId=shellId) 复用同 ID。
- 旧历史记录无 status 字段时由 `normalizeTaskFields()` 自动推断，不用迁移数据。

### 4. 新增 UI 中文统一加 i18n 占位
- 行尾加 `<!-- i18n: module.scope.key -->` 或 `/* i18n: module.scope.key */`，后续脚本可批量替换接入 vue-i18n。
