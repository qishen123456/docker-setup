# SmartAsk 问数系统 — 长期架构笔记

## 入口与编排
- `backend/app.py`：Flask 入口，端口 5002，18 blueprint，全局访问日志钩子。
- `backend/controllers/smart_chat.py`：问数主路由。同步 + SSE 两版；SSE = 单 worker 线程 + 内存 queue + 帧转发（ready/trace/summary/heartbeat/result/done）。确认分支 confirm-by-boss（同步/SSE）。
- `backend/ask_flow/controller.py`：AskFlowController 是 basic/advanced 引擎总开关。decide() 优先级 入参→datasetPolicies→defaultFlow；advanced 需 advancedEnabled + feature_flag advanced_ask_flow + role∈advancedRoles（默认 super_admin），否则 basic；advanced 出错按 fallbackToBasicOnError 回退 basic。
- 核心编排在 `backend/four_agent_ask.py`（~10748 行上帝文件）：四智能体流水线 + 三套硬编码规则 SQL 引擎。

## 升级关键事实
- 默认 advanced 关闭，流量全走 basic 引擎。
- SSE 本质同步，无并发/任务队列；确认会话与短期记忆存进程内存，多 worker 部署丢状态。
- contracts.py 的 AskRequest/ConfirmRequest/FlowDecision 是改动边界。
- 升级路线见 `nl2sql_improvement_plan.md`（商用 18%/消费者 7.5% 通过率，目标 70%+，五层改造）。

## 用户协作约定
- 用户要求：只读不改，理解项目后再升级；方向由我（专家角色）定，确认后再动手。
