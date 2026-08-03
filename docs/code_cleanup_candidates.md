# SmartAsk 代码清理候选清单

> **说明**
> - 本清单基于静态交叉引用分析：检查文件是否被 `import`、路由注册、`app.py` 蓝图挂载、前端组件引用、脚本调用等。
> - 标注为 **safe** 的项有明确未使用证据，删除后基本不会影响运行。
> - 标注为 **verify** 的项是独立诊断/测试/文档工具，删除前请确认团队是否还在用。
> - 标注为 **risky** 的项涉及业务 Demo 或可能的外部引用，需要你最终确认。
> - 动态导入、运行时反射、字符串拼接路由可能无法被静态识别，因此“未引用”不等于“绝对没用”，请做最终判断。

---

## 一、可安全删除（safe）

### 1.1 前端未使用组件与资源

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `frontend/src/components/HelloWorld.vue` | 组件 | Vite/Vue 默认示例组件，未被任何视图/组件引用。 | safe | 删除 |
| `frontend/src/components/smartask/AgentDoneBar.vue` | 组件 | 存在但未被任何文件 import。 | safe | 删除 |
| `frontend/src/components/smartask/ArtifactStrip.vue` | 组件 | 存在但未被任何文件 import。 | safe | 删除 |
| `frontend/src/components/smartask/TabNav.vue` | 组件 | 存在但未被任何文件 import。 | safe | 删除 |
| `frontend/src/assets/hero.png` | 静态资源 | 仅被未使用的 `HelloWorld.vue` 引用。 | safe | 删除 |
| `frontend/src/assets/vite.svg` | 静态资源 | 仅被未使用的 `HelloWorld.vue` 引用。 | safe | 删除 |
| `frontend/src/assets/vue.svg` | 静态资源 | 仅被未使用的 `HelloWorld.vue` 引用。 | safe | 删除 |
| `frontend/public/angel-logo.png` | 静态资源 | 未被引用，活跃 Logo 为 `angel-logowite.png`。 | safe | 删除 |
| `frontend/public/icons.svg` | 静态资源 | 仅被未使用的 `HelloWorld.vue` 引用。 | safe | 删除 |
| `frontend/refactor_angel_final.ps1` | 脚本 | 一次性品牌色替换脚本，已执行完毕。 | safe | 删除 |
| `frontend/README.md` | 文档 | Vite 默认模板，非项目文档。 | safe | 删除或替换为项目前端说明 |

### 1.2 前端未使用的 API 封装

以下函数在 `frontend/src/api/index.js` 中导出，但在 `frontend/src/` 下没有调用方：

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `frontend/src/api/index.js` → `getDashboard` | API 封装 | 前端无调用，后端 `/api/dashboard` 也无活跃调用方。 | safe | 删除该 export |
| `frontend/src/api/index.js` → `adminLogin` | API 封装 | 无调用；登录使用 `passwordLogin`。 | safe | 删除该 export |
| `frontend/src/api/index.js` → `getEmployeePermissions` / `saveEmployeePermissions` | API 封装 | 无调用。 | safe | 删除这两个 export |
| `frontend/src/api/index.js` → `createRbacRole` / `updateRbacRole` / `deleteRbacRole` | API 封装 | 无调用。 | safe | 删除这三个 export |
| `frontend/src/api/index.js` → `createRbacGroup` / `updateRbacGroup` / `deleteRbacGroup` | API 封装 | 无调用。 | safe | 删除这三个 export |
| `frontend/src/api/index.js` → `getRbacUserPermissions` | API 封装 | 无调用。 | safe | 删除该 export |
| `frontend/src/api/index.js` → `getRbacDatasetAccess` | API 封装 | 无调用。 | safe | 删除该 export |
| `frontend/src/api/index.js` → `getRuntimeMigrationBackups` | API 封装 | 无调用。 | safe | 删除该 export |
| `frontend/src/api/index.js` → `getFeishuSyncLogStats` | API 封装 | 无调用。 | safe | 删除该 export |
| `frontend/src/api/index.js` → `getBookshelfHealth` / `getVannaStatus` | API 封装 | 无调用；两者都指向 `/bookshelves/health`，且重复。 | safe | 删除这两个 export |

### 1.3 后端未注册控制器 / 死路由

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `backend/controllers/analysis.py` | 控制器 | 定义了 `analysis_bp`，但 `backend/app.py` 未 import 也未注册。 | safe | 删除 |
| `backend/controllers/analysis_thinking.py` | 控制器 | 定义了 `analysis_thinking_bp`，`backend/app.py` 未注册。 | safe | 删除 |
| `backend/controllers/chat.py` | 控制器 | 定义了 `chat_bp`，已被 `backend/controllers/smart_chat.py` 取代，`app.py` 未注册。 | safe | 删除 |
| `backend/controllers/smart_chat.py` → `/api/data-sources` | 路由 | 路由存在但无前端调用；数据源管理已走 `controllers/datasources.py`。 | safe | 删除该路由 |
| `backend/controllers/smart_chat.py` → `/api/test-source-identification` | 路由 | 调试用路由，无前端/外部调用。 | safe | 删除该路由 |

### 1.4 后端未引用的独立脚本

这些 `.py` 文件未被 `app.py`、`bootstrap.py` 或其他模块 import；属于一次性/遗留脚本：

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `backend/add_dataset_columns.py` | 脚本 | 一次性 schema 辅助脚本，无引用。 | safe | 删除 |
| `backend/create_angel_table.py` | 脚本 | 遗留建表脚本，无引用。 | safe | 删除 |
| `backend/drop_angel_table.py` | 脚本 | 遗留清理脚本，无引用。 | safe | 删除 |
| `backend/regression_report_spec_sort_none.py` | 脚本 | 一次性回归脚本，无引用。 | safe | 删除 |
| `backend/init_smart_training.py` | 脚本 | 在 `.gitignore` 中标记为遗留，无引用。 | safe | 删除 |
| `backend/requirements_utf8.txt` | 配置 | `backend/requirements.txt` 的重复副本，无引用。 | safe | 删除 |
| `backend/scripts/simulate_ranking_ask.py` | 脚本 | 无引用。 | safe | 删除 |

### 1.5 生成产物 / 测试产物 / 重复文件

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `backend/dataset_copilot/output/*.json` | 生成产物 | Dataset Copilot 历史输出，运行代码不引用。 | safe | 删除并加入 `.gitignore` |
| `config/smartask_test_results_20260627_225405.json` | 测试产物 | 批量测试输出，不应纳入版本库。 | safe | 删除并加入 `.gitignore` |
| `config/smartask_test_report_20260627_195912.md` | 测试产物 | 同上。 | safe | 删除并加入 `.gitignore` |
| `config/analyze_report.py` | 脚本 | 硬编码指向已不存在的测试结果文件，无法直接运行。 | safe | 删除 |
| `docs/smartask_test_results.json` | 测试产物 | 旧聚合测试结果，`config/` 下已有新版本。 | safe | 删除 |
| `docs/smartask_test_report.md` | 测试产物 | 旧聚合测试报告。 | safe | 删除 |
| `docs/basic_flow_test_report.md` | 测试产物 | 旧基础流程测试报告。 | safe | 删除 |
| `data/analysis_prompts.json` | 数据文件 | 根 `/data/` 已被 `.gitignore` 标记为遗留，无代码引用。 | safe | 删除 |

### 1.6 根目录一次性脚本与旧前端 / Demo 目录

根目录存在大量一次性的 `*_complete.py` / `*_guide.py` / `debug_*.py` 等脚本，`.gitignore` 已将其标记为 legacy。这些文件均未被引用：

`add_pause_button_guide.py`, `analysis_control_complete.py`, `analysis_format_complete.py`, `analysis_loading_optimization.py`, `analysis_revert_complete.py`, `analysis_scrollbar_complete.py`, `check_backend_response.py`, `check_frontend_syntax.py`, `check_training.py`, `clean_vue_file.py`, `clear_cache_guide.py`, `compact_sql_table_display.py`, `compact_steps_display.py`, `complete_steps_process.py`, `debug_keywords.py`, `debug_report.py`, `debug_test_guide.py`, `debug_thinking_filter.html`, `diagnose_frontend_error.py`, `diagnose_vanna_init.py`, `error_logic_fix_complete.py`, `final_test_report.py`, `fix_analysis_cancel_and_style.py`, `fix_regex_error.py`, `fix_sql_data_buttons.py`, `frontend_fix_complete.py`, `git_setup_complete.py`, `pause_feature_complete.py`, `recover_datasources.py`, `remove_thinking_expand.py`, `restart_guide.py`, `skipped_step_feature.py`, `sql_data_inline_display.py`, `sql_scrollbar_limit.py`, `step_definition_fixed.py`, `step_status_fixed.py`, `streaming_fix_complete.py`, `streaming_output_fixed.py`, `test_filter.js`, `test_guide.py`, `test_thinking_filter.html`, `text_steps_display.py`, `thinking_process_filter.py`, `thinking_process_improvements.py`, `tmp_init_db.py`, `vanna01.py`。

以及：
- `implementation_plan.md`
- `task.md`
- `consumer_test_report.md`
- `test_report.md`

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| 上述所有根目录 `*_complete.py` / `*_guide.py` / `debug_*.py` / `test_*.js` 等 | 脚本 | `.gitignore` 已标记为 legacy，无引用。 | safe | 删除 |
| `components/` | 旧前端 | React 遗留目录（`Layout/MainLayout.tsx`），Vue 前端不再使用。 | safe | 删除 |
| `pages/` | 旧前端 | React 遗留页面（`Chat.tsx`、`Dashboard.tsx` 等），已被 `frontend/src/views/` 取代。 | safe | 删除 |
| `火山引擎/` | Demo 资料 | 火山引擎 Demo 截图与分析文档，不属于当前应用。 | risky | 归档或删除（需你确认） |
| `火山引擎demo/` | Demo 项目 | 独立的火山引擎 Demo 工程。 | risky | 归档或删除（需你确认） |

---

## 二、建议归档或需确认（verify）

### 2.1 后端诊断与批量测试脚本（可能本地调试仍在用）

这些脚本未被主程序 import，但可能是日常排障/回归时手动运行的：

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `scripts/tests/analyze_batch_results.py` | 脚本 | 独立批量结果分析器。 | 已迁移 | 保留在统一测试脚本目录 |
| `scripts/tests/batch_test_questions.py` | 脚本 | 手动批量测试运行器。 | 已迁移 | 保留在统一测试脚本目录 |
| `scripts/tests/batch_test_consumer_questions.py` | 脚本 | 消费者数据集批量测试。 | 已迁移 | 保留在统一测试脚本目录 |
| `scripts/tests/batch_test_ecommerce_questions.py` | 脚本 | 电商数据集批量测试。 | 已迁移 | 保留在统一测试脚本目录 |
| `backend/build_dataset_node_index.py` | 脚本 | 生成 `config/dataset_node_index.json`，目前手动运行。 | verify | 保留工具脚本 / 或归档 |
| `backend/check_all_dbs.py` | 脚本 | 数据库连通性诊断。 | verify | 归档 |
| `backend/check_angel_structure.py` | 脚本 | 结构诊断。 | verify | 归档 |
| `backend/check_datasets.py` | 脚本 | 数据集诊断。 | verify | 归档 |
| `backend/check_dataset_detail.py` | 脚本 | 数据集详情诊断。 | verify | 归档 |
| `backend/check_fields_data.py` | 脚本 | 字段数据诊断。 | verify | 归档 |
| `backend/check_tables.py` | 脚本 | 表检查诊断。 | verify | 归档 |
| `backend/check_table_structure.py` | 脚本 | 表结构诊断。 | verify | 归档 |
| `backend/consumer_single_test.py` | 脚本 | 单条测试。 | verify | 归档 |
| `backend/encrypt_env_secrets.py` | 脚本 | 加密环境变量 CLI 工具。 | verify | 保留 / 归档 |
| `backend/fill_syyb_dataset.py` | 脚本 | 遗留数据集填充脚本。 | verify | 归档 |
| `backend/get_feishu_tables.py` | 脚本 | 飞书表列表获取工具。 | verify | 归档 |
| `backend/regenerate_dataset_from_doc.py` | 脚本 | 从文档重新生成数据集 payload。 | verify | 保留 / 归档 |
| `backend/single_test.py` | 脚本 | 单条测试运行器。 | verify | 归档 |
| `backend/update_dataset_config.py` | 脚本 | 遗留数据集更新脚本。 | verify | 归档 |
| `backend/update_dataset_content.py` | 脚本 | 遗留数据集更新脚本。 | verify | 归档 |
| `config/run_smartask_tests.py` | 脚本 | 批量测试执行器，生成 `config/smartask_test_results_*.json`。 | verify | 保留 / 归档 |

### 2.2 文档与演示材料

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `docs/smartask_issue_analysis.md` | 文档 | 与 `config/smartask_issue_analysis.md` 内容高度重复。 | verify | 合并或删除其中一份 |
| `docs/smartask_test_question_list.md` | 文档 | 与 `config/smartask_test_question_list.md` 内容高度重复。 | verify | 合并或删除其中一份 |
| `docs/presentation/` | 文档 | 旧演讲稿/PPT 大纲，多个版本。 | verify | 归档 / 确认是否再用 |
| `docs/project_report_materials/`、`docs/project_report_materials.md` | 文档 | 旧项目汇报材料。 | verify | 归档 |
| `docs/product_tier_trim_plan.md` | 文档 | 旧产品规划文档，可能已过时。 | verify | 确认是否再用 |
| `PPT大纲_NotebookLM适配.md` | 文档 | 旧 PPT 大纲。 | verify | 归档 |
| `培训演讲稿与常见问题预演.md` | 文档 | 培训演讲稿。 | verify | 归档 |
| `提示词.md` | 文档 | `.gitignore` 已标记为 legacy。 | verify | 归档 |
| `nl2sql_improvement_plan.md` | 文档 | 旧改进计划。 | verify | 确认是否再用 |
| `改造计划_AIModels_ReportConfig.md` | 文档 | 旧改造计划。 | verify | 确认是否再用 |

### 2.3 重复 / 可被合并的脚本

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `backend/export_runtime_config.py` | 脚本 | 功能与 `scripts/export_runtime_config.py` 重复；`scripts/` 版本被 `backup_all.py` 和文档使用。 | verify | 删除 backend 版本，并更新 `DEPLOY.md` 中的引用 |

### 2.4 可能未使用的 Python 依赖

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `backend/requirements.txt` → `plotly>=5.20.0` | 依赖 | 未在任意 `.py` 中 import。 | verify | 确认无动态使用后移除 |
| `backend/requirements.txt` → `typing-inspection>=0.4.2` | 依赖 | 未在任意 `.py` 中 import。 | verify | 确认无动态/传递使用后移除 |
| `backend/requirements.txt` → `requests>=2.31.0` 重复行 | 依赖 | 第 23 行与第 33 行重复。 | safe | 删除重复行 |

### 2.5 工作区运行时产物（已被 `.gitignore`，但物理存在）

| 路径 | 类别 | 删除理由 | 风险 | 建议操作 |
|---|---|---|---|---|
| `frontend/dist/` | 构建产物 | Gitignored，不应提交。 | safe | 从工作区删除 |
| `frontend/node_modules/` | 依赖目录 | Gitignored。 | safe | 从工作区删除 |
| `backend/.pytest_cache/` | 缓存 | Gitignored。 | safe | 从工作区删除 |
| `backend/**/__pycache__/` | 缓存 | Gitignored。 | safe | 从工作区删除 |
| `logs/` | 日志 | Gitignored；**飞书同步日志和系统日志 fallback 写入此处，属于运行时持久化数据**。 | verify | 保留目录，仅删除过期单日志文件 |
| `backend/logs/` | 日志 | Gitignored；**后端系统日志 fallback 写入此处**。 | verify | 保留目录 |
| `backend/data/` | 运行时数据 | `agent_registry.json` 写入此处；`dataset_dimension_profiles.json` 若存在仅作为旧语义画像增强。 | verify | 保留目录；不要用旧画像覆盖 `config/dataset_node_index.json` |
| `backups/` | 备份 | Gitignored；可保留近期备份。 | verify | 制定保留策略后清理旧备份 |

---

## 三、已核实仍在使用（请勿删除）

以下文件曾被 `.gitignore` 或初步扫描误标为 legacy，但实际仍在运行链路中：

| 路径 | 使用位置 | 说明 |
|---|---|---|
| `backend/dataset_dimension_profiles.py` | `four_agent_ask.py`、`disambiguation/llm_arbiter.py`、`report_spec_builder.py`、`smartask_advanced/skills/dataset_route.py` | 旧维度画像读取逻辑仍在使用；画像只能做别名/集合口径增强，真实节点事实以 `config/dataset_node_index.json` 为准。 |
| `scripts/deploy/verify_deployment.py` | `scripts/verify_deployment.py`、`deploy.sh`、`update.sh` | 部署自检脚本已迁移到统一部署脚本目录，兼容 shim 继续可用。 |
| `backend/create_consumer_standard_dataset.py` | `bootstrap.py` | 内置消费者标准数据集同步。 |
| `backend/import_runtime_config.py` / `import_bookshelf_bundle.py` / `import_angel_group_data.py` | `bootstrap.py` | 启动时导入 bundle。 |
| `backend/export_bookshelf_bundle.py` / `export_angel_group_data.py` | `scripts/backup_all.py` | 备份脚本使用。 |
| `backend/start_feishu_sync.py` | `start_feishu_sync.bat` | Windows 下手动启动飞书同步的入口。 |
| `backend/dataset_copilot/`（除 `output/`） | `controllers/bookshelf.py`、`four_agent_ask.py`、`regenerate_dataset_from_doc.py` | AI 生成数据集能力仍在使用。 |
| `backend/smartask_advanced/` | `ask_flow/controller.py`、`controllers/advanced_capabilities.py`、多个测试文件 | 高级问数能力（skills）仍在使用。 |
| `backend/disambiguation/` | `four_agent_ask.py`、测试文件 | 路由确认仲裁仍在使用。 |

---

## 四、建议的清理顺序

1. **先删 safe 项**：根目录 legacy 脚本、旧 React 目录、未使用组件/资源、未注册控制器、死路由、生成产物。
2. **更新 `.gitignore`**：
   - 移除仍在使用的项：`backend/dataset_dimension_profiles.py`、`scripts/deploy/verify_deployment.py`。
   - 加入生成产物：`config/smartask_test_results_*.json`、`config/smartask_test_report_*.md`、`backend/dataset_copilot/output/*.json`。
3. **处理 verify 项**：将诊断/批量测试脚本统一移到 `tools/` 或 `scripts/archive/`，不要散落在 `backend/` 根目录。
4. **文档合并**：决定 `docs/` 与 `config/` 中重复文档的权威版本。
5. **依赖清理**：移除 `plotly`、`typing-inspection` 并验证容器构建与运行。
6. **删除工作区运行时产物**：`frontend/dist/`、`frontend/node_modules/`、`__pycache__/`、`.pytest_cache/`、过期 `backups/`。注意：`logs/` 目录本身不能删除（飞书同步日志持久化在此），仅可删除过期单日志文件。

---

## 五、统计

| 操作分类 | 数量估算 |
|---|---|
| safe → 直接删除 | 约 80+ 个文件/目录 |
| verify → 归档 / 确认 | 约 40+ 个文件/目录 |
| keep → 仍在使用 | 9 个核心文件/目录 |

---

**下一步**：请过一遍本清单，把 `risky` / `verify` 中你希望保留的项告诉我，我可以据此生成一份最终的删除脚本或 PR 级变更计划。
