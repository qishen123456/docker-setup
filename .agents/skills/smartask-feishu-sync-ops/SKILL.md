---
name: smartask-feishu-sync-ops
description: >
  SmartAsk 飞书多维表数据同步的运维、配置与排查。
  适用于：新增/修改飞书同步配置、手动触发同步、验证同步结果、处理「改了链接仍同步旧表」、全量同步清表、同步重复数据、定时任务不更新、同步状态异常等问题。
  当用户提到「飞书同步」「feishu_sync」「同步任务」「清表」「TRUNCATE」「同步链接改了没用」「同步重复」「靳锋重复」时触发。
---

# SmartAsk 飞书同步运维

## 1. 核心文件

- 运行时配置：`smartask/config/feishu_sync.json`（bind mount 到容器 `/app/config/feishu_sync.json`）
- 默认 bundle（新环境首次部署用）：`smartask/backend/imports/runtime_config_bundle.json`
- 管理模块：`smartask/backend/feishu_sync_manager.py`
- 服务/调度：`smartask/backend/feishu_sync_service.py`
- 前端页面：`smartask/frontend/src/views/FeishuSync.vue`
- 链接解析：`smartask/backend/feishu_url_parser.py`

## 2. 配置字段说明

`config/feishu_sync.json` 中 `sync_configs` 每项关键字段：

| 字段 | 含义 |
|---|---|
| `base_id` | 飞书多维表 base ID |
| `table_id` | 飞书 table ID |
| `view_id` | 飞书 view ID（可选） |
| `target_table` | PostgreSQL 目标表名 |
| `sync_mode` | `full`（全量，先 TRUNCATE） / `incremental`（增量，按 record_id upsert） |
| `sync_frequency` | 调度周期（分钟） |
| `app_id` / `app_secret` | 飞书应用凭证 |
| `is_active` | 是否启用定时调度 |

## 3. 手动触发同步

### 3.1 通过后端容器直接调用（无需登录）

```bash
cd smartask
docker compose exec -T backend python - <<'PY'
import sys
sys.path.insert(0, '/app/backend')
from feishu_sync_service import sync_service
sync_service.sync_single_config(<config_id>)
PY
```

`<config_id>` 是 `config/feishu_sync.json` 中的 `id`。

### 3.2 通过 API

```bash
curl -X POST http://localhost:5002/api/feishu-sync/<config_id>/start \
  -H "Authorization: Bearer <token>"
```

## 4. 全量同步清表

`sync_mode == 'full'` 时，`feishu_sync_service.sync_data_to_postgres()` 会先执行：

```python
cursor.execute(sql.SQL("TRUNCATE TABLE {table}").format(table=sql.Identifier(table_name)))
```

然后再插入飞书拉取的数据。因此：

- 修改 `table_id`/`view_id` 后不会再留下旧 record_id 导致的重复。
- 但 **full 模式不会保留历史数据**，目标表始终与当前飞书视图一致。

## 5. 修改链接/视图后仍同步旧表

### 5.1 根因

- `.env` 中的 `SMARTASK_FEISHU_BASE_ID`/`TABLE_ID`/`VIEW_ID`/`TARGET_TABLE`/`SYNC_MODE`/`SYNC_FREQUENCY` 曾会覆盖 JSON 配置。
- `feishu_sync_manager.update_sync_status()` 读取的是被 `.env` 覆盖后的配置，更新状态时会把它写回 JSON，冲掉新链接。
- 定时调度 `start_scheduler()` 把启动时的 config 对象作为闭包传入，修改配置后仍用旧对象。

### 5.2 当前约束（已修复）

- `config_manager.apply_env_feishu_overrides()` 只让 `.env` 覆盖 `app_id/app_secret/is_active/label/description`，不再覆盖链接字段。
- `feishu_sync_manager` 写入时使用 `read_feishu_config_raw()`，绕过 `.env` 覆盖。
- 定时任务传 `config_id`，执行时重新读取最新配置。
- 前端 `parseFeishuLink()` 无条件覆盖 `base_id`/`table_id`，`view_id` 为空时显式清空。

### 5.3 排查步骤

1. 打开 `smartask/config/feishu_sync.json`，确认 `base_id/table_id/view_id/target_table/sync_mode` 是预期值。
2. 修改配置后**必须重新 build backend** 使代码变更生效（若本次改动只涉及 JSON 配置则不需要，但涉及后端代码时需要）。
3. 手动触发一次同步，观察日志是否拉取新表/视图。
4. 若新环境首次部署，检查 `backend/imports/runtime_config_bundle.json` 是否仍包含旧链接；若是，用新导出的 bundle 替换。

## 6. 验证同步结果 / 排查重复

```sql
-- 目标表总条数
SELECT COUNT(*) FROM <target_table>;

-- 按某个业务键查重复（示例）
SELECT <业务键>, COUNT(*) FROM <target_table> GROUP BY <业务键> HAVING COUNT(*) > 1;
```

## 7. 修改后必须重建后端

任何 `feishu_sync_manager.py` / `feishu_sync_service.py` / `config_manager.py` 的改动：

```bash
cd smartask
docker compose build backend && docker compose up -d backend
```

## 8. 导出运行态 bundle

修改并保存配置后，建议导出 bundle 纳入版本库：

```bash
cd smartask
python scripts/export_runtime_config.py --output backend/imports/runtime_config_bundle.json
```

或容器内：

```bash
docker compose exec backend python /app/scripts/export_runtime_config.py --output /app/backend/imports/runtime_config_bundle.json
```

## 9. 同步后自动生成业务视图（数据集转换）

### 9.1 正确做法

不要再把 `CREATE VIEW` 硬编码到 `feishu_sync_service.py` 的同步流程里。

SmartAsk 提供通用「数据集转换」机制：

- 任务表：`bs_dataset_transforms`（由迁移 `backend/migrations/20260630_dataset_transforms.sql` 创建）
- 业务服务：`backend/dataset_transform_service.py`
- API 控制器：`backend/controllers/dataset_transforms.py`
- 前端管理：数据集管理页面 →「数据转换」标签页
- 默认任务配置：`backend/imports/default_dataset_transforms.json`
- 自动触发点：`feishu_sync_service.sync_data_to_postgres()` 在 `conn.commit()` 之后调用 `transform_service.run_transforms_by_source_table(table_name)`

### 9.2 新增默认视图的步骤

1. 在 `backend/imports/default_dataset_transforms.json` 中新增一条任务，例如：

```json
{
  "dataset_code": "angel_business_2026_phase1",
  "name": "商用事业部标准视图",
  "source_table": "angel_group_data",
  "target_type": "view",
  "target_name": "v_angel_group_data",
  "transform_sql": "SELECT ... FROM {{source_table}} WHERE ...",
  "is_active": true,
  "auto_run_on_sync": true
}
```

2. `transform_sql` 只能是以 `SELECT` 或 `WITH` 开头的单条语句，可用 `{{source_table}}` 占位符。
3. 重新 build backend 并重启容器：

```bash
cd smartask
docker compose up -d --build backend
```

4. Bootstrap 会根据 `dataset_code` 找到对应数据集，自动插入任务；如果源表已有数据会立即执行生成视图；否则等飞书同步成功后自动生成。

### 9.3 已踩过的坑

1. **feature flag 被 legacy 集合清理**：`backend/feature_flags.py` 顶层的 `_DATASET_LEGACY_MAINTENANCE_KEYS` 会在模块加载时 pop 掉 `_edit` 后缀的 flag。新增的数据转换开关 `dataset_transform_edit` 不能放在这个集合里，否则前端按钮和接口权限校验会失效。

2. **`{{source_table}}` 占位符未替换**：`execute_transform` 必须显式把 `{{source_table}}` 替换成任务中的 `source_table`，否则执行 SQL 会报 `syntax error at or near "{"`。

3. **已存在视图刷新失败**：`CREATE OR REPLACE VIEW` 不支持减少列。`view` 类型的 DDL 要先 `DROP VIEW IF EXISTS ... CASCADE;` 再创建，才能保证源表字段变化后视图仍能刷新。

4. **测试 SQL 也要传 source_table**：前端「测试 SQL」按钮必须把 `source_table` 一起传给 `/api/dataset-transforms/test-sql`，否则含占位符的模板测试会失败。

5. **view 类型用 DROP CASCADE**：刷新视图时会级联删除依赖它的对象。如果要在转换出的视图之上再建视图，建议使用 `table` 或 `materialized_view` 类型。

## 10. 删除转换任务会自动清理视图

删除 `bs_dataset_transforms` 中的任务时，`delete_transform()` 会先根据 `target_type` + `target_name` 执行对应的 DROP 语句：

- `view` → `DROP VIEW IF EXISTS <target_name> CASCADE;`
- `table` → `DROP TABLE IF EXISTS <target_name> CASCADE;`
- `materialized_view` → `DROP MATERIALIZED VIEW IF EXISTS <target_name> CASCADE;`

清理目标对象失败不会影响任务记录的删除，只会记录 warning 日志。

因此管理视图的方式就是管理转换任务：

- **前端**：数据集管理 → 数据转换 → 删除任务，视图一起删掉。
- **API**：`DELETE /api/dataset-transforms/<id>`
- **数据库兜底**：`DROP VIEW/TABLE/MATERIALIZED VIEW IF EXISTS <name> CASCADE;`

## 11. 数据转换任务已纳入运行态迁移

`bs_dataset_transforms` 已加入 `backend/runtime_migration.py` 的 `BOOKSHELF_TABLES` / `DATASET_REFERENCE_TABLES` / `NATURAL_KEY_COLUMNS`：

- 导出运行态包时会包含数据转换任务。
- 导入时会根据 `dataset_id` + `target_name` 去重/更新。
- `dataset_id` 会随 `bs_datasets` 的导入自动映射到新环境生成的 ID。

因此：

- 老环境导出运行态包 → 新环境导入 → 转换任务跟着过来。
- 如果新环境源表已有数据，bootstrap 会立即执行生成视图。
- 如果源表还没数据，等飞书同步成功后自动触发。
