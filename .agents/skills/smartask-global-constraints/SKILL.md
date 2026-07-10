---
name: smartask-global-constraints
description: >
  SmartAsk 项目通用约束与踩坑记录。适用于任何涉及 SmartAsk 代码、配置、文档、清理改动的任务。
  核心约束：Docker 运行环境、UTF-8 中文编码、源码在 smartask/ 子目录、代码清理时保护持久化目录。
---

# SmartAsk 项目通用约束

## 1. 项目结构

- 工作目录 `d:\1、工作文件\25.自研项目\13.智能问数v4` 不是项目根目录。
- **真正的项目根目录是 `smartask/`**。
- 前端源码：`smartask/frontend/src/`
- 后端源码：`smartask/backend/`
- 构建产物：`smartask/frontend/dist/`
- Agent Skill 目录：`smartask/.agents/skills/`

任何文件操作、路径引用都要以 `smartask/` 为根，不要直接写 `frontend/src/...`。

## 2. Docker 运行约束

- 项目一直以 Docker 方式运行，包含三个服务：`postgres`、`backend`、`frontend`。
- `docker-compose.yml` 位置：`smartask/docker-compose.yml`。
- **日常部署/全量重建**：
  ```bash
  cd smartask
  docker compose up -d --build
  ```
- **只改前端**：前端 Dockerfile 内部已执行 `pnpm install && pnpm run build`，不需要在宿主机手动 npm/pnpm build，直接重建 frontend 镜像即可：
  ```bash
  cd smartask
  docker compose up -d --build frontend
  ```
- **只改后端**：
  ```bash
  cd smartask
  docker compose up -d --build backend
  ```
- 数据库数据通过 named volume `smartask_pg_data` 持久化，重建容器不会丢失。
- 运行期配置（如 `config/feishu_sync.json`、`config/smartask_report_history.json`）通过 bind mount `./config:/app/config` 持久化，重建镜像后仍然保留。
- 浏览器可能有缓存，前端部署后让用户 **Ctrl+F5 强刷** 或清空缓存再验证。

## 3. 编码约束

- **所有源码、文档、配置文件必须使用 UTF-8 无 BOM 编码**。
- 中文注释、提示文案、日志、错误信息统一使用 UTF-8，禁止 GBK/GB2312/GB18030。
- 提交前检查编码：
  ```bash
  file -i smartask/frontend/src/state/smartAskHistory.js
  # 期望输出包含 charset=utf-8
  ```
- Windows 环境下 git 可能提示 LF 换 CRLF，这不影响运行时，但不要让 BOM 混入文件。

## 4. 修改前必读

- 先确认 `smartask/AGENTS.md`（如果存在）和所在子目录的 `AGENTS.md`。
- 先 grep 定位所有调用点，再动手改接口。
- 优先使用 `Agent(subagent_type="explore")` 做跨文件排查，避免漏掉触发路径。
- 改动后必须运行对应构建/测试验证。本项目以 **Docker 运行**为主，验证方式分两种：

### 4.1 Docker 运行环境（推荐 / 生产一致）

- **只改前端**：前端 Dockerfile 已内置 `pnpm run build`，宿主机无需手动 build，直接重建镜像：
  ```bash
  cd smartask
  docker compose up -d --build frontend
  ```
  部署后让用户 **Ctrl+F5 强刷** 或清空缓存再验证。
- **只改后端**：
  - 想让改动生效：
    ```bash
    cd smartask
    docker compose up -d --build backend
    ```
  - 只想在容器内跑测试（不重建镜像）：
    ```bash
    docker exec -it smartask-backend python -m pytest tests/ -q
    ```

### 4.2 Windows 本地开发环境

仅参考 `README_WINDOWS.md` 在本地启服务时使用：

- 前端：`npm run build`
- 后端：`python -m pytest tests/ -q`（如后端有 pytest）

## 5. 踩坑记录

### 5.1 历史分析「清空」后记录仍出现

**现象**：用户点击「清空」后，刷新页面或稍等片刻，历史记录重新出现。

**根因**：`frontend/src/state/smartAskHistory.js` 中 `clearSmartAskHistory` 未 `await` 后端请求；同时 `syncSmartAskHistoryFromServer` 在请求飞行期间快照了旧数据，清空后该请求返回，把旧记录 merge 回内存并 persist，甚至 `pushHistoryToServer` 污染服务端。

**修复要点**：
- `clearSmartAskHistory` 改为 `async`，`await clearSmartAskReportHistory()`，失败回滚。
- 引入 `isClearing`、`syncGeneration`、`lastClearGeneration` 阻止清空期间的并发写入与旧请求回写。
- `upsertSmartAskHistory` 在 `isClearing` 期间跳过。
- `App.vue` 清空按钮加 loading/禁用。

**相关文件**：
- `smartask/frontend/src/state/smartAskHistory.js`
- `smartask/frontend/src/App.vue`

### 5.2 历史会话恢复后回答卡片丢失/布局混乱

**现象**：恢复历史对话后，只显示用户问题，AI 消息气泡为空，图表表格不渲染。

**根因**：`compactHistoryItemForLocal` 把 AI 消息的 `data` 置为 `null`；`mergeHistoryItems` 让本地 compact 版覆盖服务端完整版；`restoreSnapshotMessages` 直接使用丢失 data 的 messages。

**修复要点**：
- 本地 compact 保留 AI `data` 结构，仅递归裁剪大字段。
- `mergeHistoryItems` 服务端完整版优先，本地版本时间严格更晚才覆盖。
- `restoreSnapshotMessages` 中 AI `data` 缺失时用 `reportSnapshot.result` 兜底重建。

**相关文件**：
- `smartask/frontend/src/state/smartAskHistory.js`
- `smartask/frontend/src/composables/useSmartAskReportHistory.js`

### 5.2.1 历史恢复后同一问题显示旧口径

**现象**：实时新问结果已经正确，但点击历史分析恢复后，左侧卡片仍显示旧口径。例如 `电商事业部业绩` 新问返回 3 个业务部，历史恢复却显示成旧的单行事业部或旧摘要。

**根因**：历史快照里同时存在 `reportSnapshot.result` 和 `reportSnapshot.messages[].data`；`result` 是该条历史的权威结果，但恢复消息时若优先使用 `messages[].data`，浏览器本地旧缓存/压缩快照会覆盖完整结果。

**修复要点**：
- `restoreSnapshotMessages` 恢复最后一条 AI 消息时，必须优先用 `reportSnapshot.result` 重建。
- 只有历史中的早期 AI 消息才保留自身 `messages[].data`。
- 排查时同时检查 `reportSnapshot.result.dataset_results[0]` 与最后一条 `messages[].data.dataset_results[0]` 是否一致。

**相关文件**：
- `smartask/frontend/src/composables/useSmartAskReportHistory.js`

### 5.2.2 历史快照本身已经是旧错口径

**现象**：新问已经正确，但点击更早的历史记录仍错。例如 `电商事业部的业绩` 旧历史的 `reportSnapshot.result` 本身就是 1 行事业部；`消费者事业部垫底的5个城市分公司` 旧历史里 `query_intent.top_n=1`，只返回 1 个城市分公司。

**根因**：
- 历史快照是运行态持久化数据，代码修复后不会自动重算旧快照。
- `frontend/src/state/smartAskHistory.js` 会合并 localStorage 与服务端历史；若只清服务端，浏览器本地旧记录可能再次 `pushHistoryToServer` 回灌。

**修复要点**：
- `backend/smartask_report_history_store.py` 读取/保存历史时校验过期快照：
  - `report_spec.scope.focusNodeIsLeaf=true`，但 `config/dataset_node_index.json` 中该节点有下级，且问题没有 `整体/总体/汇总/全部` 等汇总词，则剔除/拒收。
  - ranking 历史中 `query_intent.top_n` 小于用户原话明确数量（如 `垫底的5个` 却保存为 `top_n=1`），则剔除/拒收。
- `frontend/src/state/smartAskHistory.js` 同步本地独有记录时，若后端返回 `stale_history_snapshot`，必须从本地历史中移除，避免刷新后旧记录复活。

**相关文件**：
- `smartask/backend/smartask_report_history_store.py`
- `smartask/backend/controllers/smart_chat.py`
- `smartask/frontend/src/state/smartAskHistory.js`
- `smartask/config/dataset_node_index.json`

### 5.2.3 跨数据集对比误用了单数据集内部对比 KPI

**现象**：例如 `消费者和商用的对比` 已进入跨数据集对比，但页面显示的 `45.36% vs 47.51%` 实际分别来自“消费者 13 个分公司累计达成率”和“商用 10 个分公司/业务部混合集合累计达成率”，不是两个事业部主体本身。

**根因**：
- `frontend/src/views/SmartAsk.vue` 的跨集对比卡片默认优先读取 `report_spec.kpis`。
- `backend/smartask_advanced/service.py::_dataset_overview()` 的跨集结论也优先读取相同 KPI。
- 这些 KPI 在 `backend/report_spec_builder.py` 是按单数据集 `comparison_nodes` 生成的，用于单数据集内部对比，不等于跨数据集主体总览。

**修复要点**：
- 在 `backend/smartask_advanced/service.py` 的 `cross_dataset_compare` 路径中，依据 `route.organization_mentions` 为每个 dataset_result 注入 `comparison_subject_name / comparison_subject_level / cross_dataset_subject_overview`。
- `cross_dataset_subject_overview` 必须从真实主体节点行抽取；若同名主体出现多行，优先选主体层级、空上级、任务/开单更完整的那条。
- 前端跨集卡片和后端跨集结论优先读取 `cross_dataset_subject_overview`，只有缺失时才回退到旧 KPI。

**相关文件**：
- `smartask/backend/smartask_advanced/service.py`
- `smartask/frontend/src/views/SmartAsk.vue`
- `smartask/backend/tests/test_advanced_cross_dataset.py`

### 5.3 飞书数据同步更换链接后仍同步旧表

**现象**：在「飞书数据同步」页面修改了飞书链接并保存，但同步任务实际执行的仍是旧链接对应的表。

**根因**：
- `.env` 中的 `SMARTASK_FEISHU_BASE_ID / TABLE_ID / VIEW_ID / TARGET_TABLE / SYNC_MODE / SYNC_FREQUENCY` 会覆盖 `config/feishu_sync.json` 中第 1 条配置的链接字段。
- `feishu_sync_manager.update_sync_status()` 读取的是被 `.env` 覆盖后的配置，更新状态时会把它写回 JSON，进一步把新链接冲掉。
- 前端编辑已有配置时，`parseFeishuLink()` 使用 `||` 短路，`base_id/table_id` 无法覆盖旧值；`view_id` 为空时也保留旧值。
- 定时调度器 `feishu_sync_service.start_scheduler()` 把启动时的 `config` 对象作为闭包传入 `schedule`，修改配置后定时任务仍用旧配置。

**修复要点**：
- `config_manager.apply_env_feishu_overrides` 只让 `.env` 覆盖 `app_id / app_secret / is_active` 等全局/敏感字段，不再覆盖链接字段。
- `feishu_sync_manager` 的增删改查/状态更新使用 `read_feishu_config_raw()`，写入时不经过 `.env` 覆盖。
- `feishu_sync_service` 定时任务传 `config_id`，执行时重新读取最新配置。
- 前端 `parseFeishuLink()` 无条件覆盖 `base_id/table_id`，`view_id` 为空时显式清空。

**迁移注意**：
- 修复后在前端保存新链接，确认 `config/feishu_sync.json` 已更新，再重新导出运行态包。
- `backend/imports/runtime_config_bundle.json` 若仍包含旧链接，新环境首次部署会自动导入旧链接；建议用新导出的运行态包替换它。

**相关文件**：
- `smartask/backend/config_manager.py`
- `smartask/backend/feishu_sync_manager.py`
- `smartask/backend/feishu_sync_service.py`
- `smartask/frontend/src/views/FeishuSync.vue`

## 6. 代码清理安全守则

基于 `docs/code_cleanup_candidates.md` 进行清理时，必须区分 **「可删除的运行时产物」** 和 **「必须保留的 Docker bind-mount 持久化数据」**，不要把后者物理删除。

### 6.1 必须保留的持久化目录（DO NOT DELETE）

这些目录被 `docker-compose.yml` bind mount 进容器，或代码运行时会写入业务数据。它们可以被 `.gitignore`，但工作区目录必须存在：

| 目录 | 用途 | 删除后果 |
|---|---|---|
| `config/` | 运行态 JSON 配置（AI 模型、数据源、飞书同步、权限、功能开关等） | 所有配置丢失 |
| `logs/` | 飞书同步日志 `feishu_sync_*.log`、系统日志 fallback | 飞书同步历史日志消失 |
| `backend/logs/` | 后端系统日志 fallback | 系统日志 fallback 丢失 |
| `backend/data/` | `agent_registry.json`、可选旧画像 `dataset_dimension_profiles.json` | 智能体配置丢失；旧画像若存在可能影响语义增强 |
| `backups/` | 运行态备份包 | 备份丢失 |
| `backend/imports/` | 首次导入的元数据/业务数据 bundle | 新环境首次部署无法自动导入 |

### 6.2 可以删除的运行时产物

这些只影响构建/缓存，删除后可重建：

- `frontend/dist/`
- `frontend/node_modules/`
- `frontend/.vite/`、`frontend/.vite-cache/`、`frontend/node_modules/.vite-smartask/`
- `backend/.pytest_cache/`
- `backend/**/__pycache__/`
- 单个 `*.log` 文件

### 6.3 清理后验证 checklist

- `docker compose build` 成功
- `docker compose up -d` 后三服务 healthy
- 访问 `/api/health` 返回 200
- 打开各管理配置页面，确认列表能加载、保存不报错
- 飞书同步页面「统一运行日志」tab 能正常显示（如已删除历史日志，后续同步会重新生成）

### 6.4 踩坑记录：误删 `logs/` 导致飞书同步日志清空

**现象**：按 `code_cleanup_candidates.md` 清理 safe 项后，飞书同步页面的「统一运行日志」显示为空，历史同步记录丢失。

**根因**：飞书同步日志存在 `smartask/logs/feishu_sync_{config_id}.log` 文件中，清理时把 `logs/` 目录作为运行时产物整体删除了。

**修复要点**：
- 重建 `smartask/logs/` 和 `smartask/backend/logs/` 目录。
- 在 `.gitignore` 中明确标注这些目录为 Docker bind-mount 持久化数据。
- 后续清理时只删单个 `*.log` 文件或真正的构建/缓存产物，不要删目录。

**相关文件**：
- `smartask/docker-compose.yml`
- `smartask/.gitignore`
- `smartask/backend/feishu_sync_logger.py`
- `smartask/backend/system_log_store.py`

### 6.5 踩坑记录：旧维度画像与自动节点索引口径混用

**现象**：同一句排名或下钻问题，在不同环境表现不一致。例如 `消费者事业部垫底的5个城市分公司` 在某环境只返回 1 条，或因为旧 `dataset_dimension_profiles.json` 存在/缺失导致 Agent1.5 是否参与不同。

**根因**：
- `backend/data/dataset_dimension_profiles.json` 是早期手工维护的语义画像增强，不是当前真实节点事实源。
- `config/dataset_node_index.json` 才是由真实数据生成的节点、层级、别名、叶子节点索引。
- 若把旧画像当事实源，或让 TopN 数量识别依赖旧画像是否存在，迁移到其他服务器时容易出现口径漂移。

**处理原则**：
- 大模型负责自然语言拆解；`dataset_node_index.json` 负责事实校验；规则只做 schema、范围、安全和冲突裁判。
- 不要为了恢复旧效果而随意恢复 `dataset_dimension_profiles.json` 并让它覆盖节点索引。
- 若必须维护 `dataset_dimension_profiles.json`，只能作为别名/集合口径增强，不能覆盖自动节点索引中的真实节点关系。
- 迁移新服务器时，优先确保飞书数据、书架数据和 `config/dataset_node_index.json` 的生成链路一致，而不是依赖旧画像文件。

**相关文件**：
- `smartask/config/dataset_node_index.json`
- `smartask/backend/build_dataset_node_index.py`
- `smartask/backend/dataset_dimension_profiles.py`
- `smartask/backend/four_agent_ask.py`

## 7. 本项目已封装的技能索引

处理对应主题时，优先加载相关 SKILL，不要把细节重新推理一遍：

- `smartask-global-constraints`（本技能）：通用约束、Docker/UTF-8、代码清理安全守则、上述踩坑记录。
- `smartask-ranking-debug`：排名/TopN 类问数效果异常排查。
- `smartask-feishu-sync-ops`：飞书同步配置、手动同步、全量清表、链接不生效等运维排查。
- `smartask-runtime-migration`：运行态配置导入导出、backup_all、部署后配置恢复。
- `smartask-skill-maintenance`：代码改动后判断并更新对应 SKILL。
- `smartask-skill-usage-guide`：SKILL 使用与维护操作指引（人类用户和 AI 都读）。

当用户明确提到某技能名称或对应主题时，先读取对应 SKILL.md，再执行操作。
