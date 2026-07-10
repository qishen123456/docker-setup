---
name: smartask-runtime-migration
description: >
  SmartAsk 运行态配置的导入、导出、备份与迁移。
  适用于：导出 runtime_config_bundle.json、导入运行态配置、备份/恢复 config/*.json、部署后配置丢失、更新 imports/runtime_config_bundle.json、使用 backup_all.py / update.sh / deploy.sh 等场景。
  当用户提到「运行态配置」「runtime bundle」「备份配置」「迁移配置」「config 丢失」「runtime_migration」「导入导出 bundle」时触发。
---

# SmartAsk 运行态配置迁移

## 1. 核心概念

SmartAsk 的运行态配置指 `smartask/config/*.json` 中的一系列 JSON 文件：

- `datasources.json`
- `ai_settings.json`
- `app_config.json`
- `feature_flags.json`
- `feishu_sync.json`
- `advanced_capabilities.json`
- `organization_trees.json`
- `data_permissions.json`
- `rbac_permissions.json`
- `auth_tokens.json`
- `ask_flow.json`
- 以及 `smartask_report_history.json`、`query_history.json` 等本地状态文件

这些文件通过 `docker-compose.yml` 以 bind mount 方式挂载到后端容器 `/app/config/`，因此：

- 重建后端镜像不会丢失这些配置。
- 但新环境首次启动时，若 `config/` 为空，`bootstrap.py` 会从 `backend/imports/runtime_config_bundle.json` 恢复默认配置。

## 2. 核心文件

- 导出/导入逻辑：`smartask/backend/runtime_migration.py`
- 宿主机 CLI：`smartask/scripts/export_runtime_config.py`、`smartask/scripts/import_runtime_config.py`
- 全量备份脚本：`smartask/scripts/backup_all.py`
- 部署脚本：`smartask/deploy.sh`、`smartask/update.sh`
- 默认 bundle（新环境首次恢复用）：`smartask/backend/imports/runtime_config_bundle.json`

## 3. 导出运行态配置

### 3.1 导出到默认位置

```bash
cd smartask
python scripts/export_runtime_config.py
```

默认输出到 `smartask/runtime_config_bundle.json`。

### 3.2 导出到 imports（用于版本库/新环境首次部署）

```bash
cd smartask
python scripts/export_runtime_config.py --output backend/imports/runtime_config_bundle.json
```

### 3.3 容器内导出

```bash
cd smartask
docker compose exec backend python /app/scripts/export_runtime_config.py --output /app/backend/imports/runtime_config_bundle.json
```

## 4. 导入运行态配置

### 4.1 合并模式（默认）

只补充缺失的 key，不覆盖已有文件：

```bash
cd smartask
python scripts/import_runtime_config.py --input backend/imports/runtime_config_bundle.json --mode merge
```

### 4.2 覆盖模式

强制覆盖配置（谨慎使用）：

```bash
cd smartask
python scripts/import_runtime_config.py --input backend/imports/runtime_config_bundle.json --mode replace --overwrite-configs
```

### 4.3 仅预览

```bash
cd smartask
python scripts/import_runtime_config.py --input backend/imports/runtime_config_bundle.json --mode merge --dry-run
```

## 5. 全量备份

```bash
cd smartask
python scripts/backup_all.py
```

输出：

```text
backups/<timestamp>/
  ├── bookshelf_bundle.json
  ├── runtime_config_bundle.json
  ├── angel_group_data_bundle.json
  └── manifest.json
```

## 6. 部署/更新流程中的配置保护

`bootstrap.py` 启动时：

1. 先调用 `init_default_configs()` 初始化默认 JSON（如果文件不存在）。
2. 再调用 `_import_runtime_config()` 从 `backend/imports/runtime_config_bundle.json` 恢复缺失的运行态配置（默认不覆盖已有配置）。
3. 因此，**已有 `config/` 不会被 bundle 冲掉**；但新环境会用它做种子。

`update.sh` 通常会在升级前调用 `backup_all.py` 做备份，升级后通过 `runtime_migration.py` 合并或回滚。

## 7. 常见坑

### 7.1 新环境部署后配置是旧的

原因：`backend/imports/runtime_config_bundle.json` 仍然是旧版本。

处理：在旧环境导出最新 bundle 并替换它，再提交到版本库。

### 7.2 手动改 config/*.json 后重启失效

原因：修改的是容器内文件，而宿主机 bind mount 的 `config/` 没有同步；或修改后没有重建容器。

处理：

1. 确保修改的是 `smartask/config/*.json`。
2. 重建后端容器：

```bash
cd smartask
docker compose up -d --build backend
```

### 7.3 导入后某些配置仍不生效

原因：部分模块在启动时缓存了配置对象，而不是每次读取文件。

处理：修改相关代码，让运行时通过 ID/文件名重新读取；或重启后端容器。

### 7.4 新环境问数节点口径与旧环境不一致

原因：
- `runtime_config_bundle.json` 不包含 `config/dataset_node_index.json`。
- `dataset_node_index.json` 是真实节点、层级、别名、叶子节点事实索引，通常由飞书同步成功后按受影响数据集重建，或通过 `backend/build_dataset_node_index.py` 生成。
- `backend/data/dataset_dimension_profiles.json` 是旧语义画像增强，不应作为迁移后的事实源；恢复旧画像可能让问数口径与最新节点索引冲突。

处理：
- 新环境导入书架与飞书数据后，触发一次对应飞书同步，确认日志出现 `已重建 dataset_node_index.json`。
- 如果不触发飞书同步，需要在新环境运行节点索引重建脚本，或随版本带上确认过的 `config/dataset_node_index.json`。
- 不要通过恢复旧 `backend/data/dataset_dimension_profiles.json` 来修复节点缺失；它只能作为别名/集合口径增强，不能覆盖节点索引。
- 迁移验收至少验证一个排名问题、一个裸节点问题、一个叶子节点问题，确认返回行数和节点名称与旧环境一致。

## 8. 建议的变更流程

1. 改动 `config/*.json` 或相关代码。
2. 本地验证：

```bash
cd smartask
docker compose up -d --build backend
```

3. 确认生效后，导出最新 bundle：

```bash
python scripts/export_runtime_config.py --output backend/imports/runtime_config_bundle.json
```

4. 提交 `config/*.json` 和 `backend/imports/runtime_config_bundle.json`。

如果改动涉及节点口径或飞书数据：

- 确认 `config/dataset_node_index.json` 已按最新数据重建。
- 在新服务器首次部署后，先导入/同步数据，再验证节点索引，不要依赖旧 `dataset_dimension_profiles.json`。
