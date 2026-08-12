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
- 项目有两套平级 AI 专家资产：`.ai-team/`（代码开发，9角色）+ `.ai-data/`（数据分析/研究/金融，10角色，从平台12个专家包70个角色整合而来）。后者当前仅知识储备，尚未集成到系统。

## 部署架构变更（2026-08-10 bootstrap 解耦 BugFix）
- `backend/bootstrap.py` 已不再做自动初始化（main 简化为 `os.execv app.py`）；`backend/Dockerfile` 默认 stage CMD = `python app.py`。
- 新建 `backend/migrate.py`：一次性迁移脚本（等 PG → 默认配置/runtime config → 8 个 schema 迁移；exit 0/1）；`backend/Dockerfile` 有独立 `migrate` stage（CMD `python migrate.py`）。
- ✅ **2026-08-12 已修复（commit 6f31c4c）**：docker-compose 新增 `migrate` 服务（`target: migrate` + `restart: "no"` + `networks: smartask-internal + default`），backend 加 `depends_on: migrate: service_completed_successfully`，实现 PG healthy → migrate 退 0 → backend healthy → frontend 的全自动依赖链。postgres 顺手补了双 networks 声明。Dockerfile:53-57 注释与新用法一致；update.sh:677 假陈述改为事实陈述。**单条 `docker compose up -d --build` 全自动完成部署**。已实测：8 个迁移全应用，/api/health 200。
- ⚠️ **2026-08-12 Phase 4 复审曝数据源配置脏值**：本机 `config/datasources.local.json` 是某次手工调试残留，叠加 `config_manager._env_text` 的 env 覆盖机制，导致 `get_datasources()` 返回畸形 sqlite（type=sqlite 但 host=pgsql）。症状：飞书 auto 模式启动检查抛"未找到活跃数据源"，auto 优化在这台机器从未真正生效（永远走保守全量）。详见 `.workbuddy/artifacts/feishu-startup-sync-review-2026-08-12.md` §5。合入生产前必修：①删脏 datasources.local.json ②env 合并逻辑加 type=sqlite 拒改写 ③数据源 schema validation sanity check ④`get_postgres_connection` 加 type-guard。
- bootstrap 保留的 5 个 sync helpers（`_sync_builtin_datasets` / `_sync_default_dataset_transforms` / `_sync_ecommerce_common_questions` / `_import_bookshelf_bundle` / `_import_angel_bundle`）与首次 bundle 自动导入**不再被自动调用**，仅作手动工具保留。
- 关键安全护栏：`create_consumer_standard_dataset.py:792` 的 DELETE+全插内置模板逻辑保留但**不再自动触发**——用户的 golden sql / 数据字典 / agent prompt 走文件迁移导入导出，部署不再覆盖。
- 部署：**一条命令** `docker compose up -d --build`（postgres → migrate → backend → frontend 全自动）。旧 `python bootstrap.py` 路径仍兼容（仅 execv app.py），但走 compose 是默认推荐。
- 已知遗留（QA 标的 tech-debt，与本次解耦）：`.env.example` / `.env.template` / `DEPLOY_TO_SERVER.md` 中 dead env vars（SMARTASK_BOOTSTRAP_SKIP_BUILTINS 等）；`app.py` 启动期无 PG 重试。详细分析与 QA 报告见 `.workbuddy/memory/2026-08-10.md`。
