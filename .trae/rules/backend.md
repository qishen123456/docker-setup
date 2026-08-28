<!-- AUTO-GENERATED from .agents/rules/ - DO NOT EDIT. Edit the source and rerun scripts/sync-ide-rules.ps1 -->
---
# Trae rule - backend only
alwaysApply: false
globs:
  - "backend/**/*.py"
---

# SmartAsk 后端开发规范

> Antigravity 工作区规则 - 处理 `backend/` 下的 Python 文件时自动生效。
> 激活方式建议设为 Glob: `backend/**/*.py`

## 关键文件改动规则

### `backend/four_agent_ask.py`（9063行，单类 FourAgentAskService / 156方法）

> 2026-08-06 审计修正：旧文档称 ~10748 行，实际 9063 行（2026-08-03 删除 1685 行后行号整体漂移，所有旧行号引用失效）。

- **改前必须全局搜索目标函数/规则位置**，确认所有调用方
- 不要在这个文件里新增大类，尽量外移到 `ask_flow/` 或 `ask_engine_*.py`
- 改后必须跑 `cd backend && python -m pytest`

审计关键发现（2026-08-06，详见 `docs/audit/2026-08-06_final-audit-report.md`）：
- **58% 零状态依赖**：35 个方法 / 5215 行不引用 `self.<属性>`，三套规则 SQL 引擎合计 2112 行实例属性引用=0（被误写成方法的纯函数，外提是机械操作不是架构手术）
- **安全护栏方向反置**：approved=True 不校验直落执行（`:8225-8263`），approved=False 才过校验（`:8238`），物理执行点零护栏（`datasource_router.py:192-199`）
- **LLM 状态共享**：模块级单例（`:9063`）+ `ask()` 每请求写共享 `_preferred_model_id`（`:8487`），并发请求互相覆盖模型选择
- **agent1.org_subject 重复调用**：`:8493` 与 `:8656` 入参完全相同且条件为严格子集，第二次纯冗余；temperature=0.1 非零致同输入不同输出 = 非确定性路由，占全部 LLM 耗时 99.4%

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
