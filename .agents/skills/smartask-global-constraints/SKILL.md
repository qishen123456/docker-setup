---
name: smartask-global-constraints
description: >
  SmartAsk 项目通用约束与踩坑记录。适用于任何涉及 SmartAsk 代码、配置、文档改动的任务。
  核心约束：Docker 运行环境、UTF-8 中文编码、源码在 smartask/ 子目录。
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

## 6. 本项目已封装的技能索引

处理对应主题时，优先加载相关 SKILL，不要把细节重新推理一遍：

- `smartask-global-constraints`（本技能）：通用约束、Docker/UTF-8、上述踩坑记录。
- `smartask-ranking-debug`：排名/TopN 类问数效果异常排查。
- `smartask-feishu-sync-ops`：飞书同步配置、手动同步、全量清表、链接不生效等运维排查。
- `smartask-runtime-migration`：运行态配置导入导出、backup_all、部署后配置恢复。
- `smartask-skill-maintenance`：代码改动后判断并更新对应 SKILL。
- `smartask-skill-usage-guide`：SKILL 使用与维护操作指引（人类用户和 AI 都读）。

当用户明确提到某技能名称或对应主题时，先读取对应 SKILL.md，再执行操作。
