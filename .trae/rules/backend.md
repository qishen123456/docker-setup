---
# Trae 项目规则 - 后端专属
# 生效方式：Apply to Specific Files
alwaysApply: false
globs:
  - "backend/**/*.py"
---

# SmartAsk 后端开发规范

## 关键文件改动规则

### `backend/four_agent_ask.py`（上帝文件，~10748行）
- **改前必须全局搜索目标函数/规则位置**，确认所有调用方
- 不要在这个文件里新增大类，尽量外移到 `ask_flow/` 或 `ask_engine_*.py`
- 改后必须跑 `cd backend && python -m pytest`

### `backend/controllers/smart_chat.py`（问数主路由）
- 改 SSE 逻辑时注意帧序列：ready -> trace -> summary -> heartbeat -> result -> done
- 内存 queue 是单线程约束，不要假设并发安全
- 确认会话存进程内存，多 worker 部署会丢状态

### `backend/ask_flow/controller.py`（引擎开关）
- decide() 优先级：入参 -> datasetPolicies -> defaultFlow
- advanced 需 advancedEnabled + feature_flag advanced_ask_flow + role∈advancedRoles
- advanced 出错按 fallbackToBasicOnError 回退 basic
- 改动边界：`contracts.py` 的 AskRequest/ConfirmRequest/FlowDecision

## 通用后端规范

- 框架：Flask 3.0.3 + Vanna[chromadb] 0.7.9 + openai SDK
- 配置：新增数据集策略写 `config/` 下 json；功能开关走 feature_flag；角色权限写 advancedRoles
- 测试：pytest + pytest-asyncio，新功能至少配单测
- 数据库：MySQL/PostgreSQL + ChromaDB(向量)，建表 SQL 在 `docker/*.sql`
- 日志：用项目既有的日志中间件模式，不要引入新的日志框架
