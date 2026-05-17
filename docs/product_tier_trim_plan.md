# Data Agent 产品功能矩阵与代码裁剪计划

> 更新时间：2026-05-16  
> 适用对象：产品、交付、研发，以及负责裁剪代码的 IDE/Agent。  
> 目标：基于当前项目最新状态，沉淀一份可以直接指导代码裁剪的产品矩阵。基础班只展示约 30% 能力，进阶班展示约 50%，高级班展示约 70%，完整版作为内部母版继续迭代。

## 0. 给代码裁剪 IDE 的执行说明

这份文档按“先隐藏、再限制、最后物理删除”的方式设计。不要一上来大面积删除文件，因为当前项目中问数链路、数据集、报告模板、历史快照、权限和配置存在共享依赖。

建议执行顺序：

1. 先按“全量产品功能矩阵”确定目标版本。
2. 修改 `config/feature_flags.json` 或后端默认功能开关，先隐藏导航和按钮。
3. 修改 `frontend/src/App.vue` 的 `menuItems`，移除目标版本不展示的菜单入口。
4. 修改 `frontend/src/router/index.js`，限制目标版本不展示页面的路由。
5. 修改 `backend/app.py` 的蓝图注册或 API 权限中间件，避免隐藏页面仍可直接调用接口。
6. 确认构建和主链路回归通过后，再按“可物理删除清单”删除页面、接口和配置。

裁剪原则：

- 基础班：业务用户能问数、看报告、查历史，后台治理入口基本不可见。
- 进阶班：客户管理员能维护数据源、模型、数据集和报告模板。
- 高级班：生产运营版，开放飞书同步、智能体配置、基础权限、组织树和部分运维能力。
- 完整版：内部母版，不建议直接全部交付普通客户。

## 1. 全量产品功能矩阵

以下矩阵先列出当前项目里的全部产品能力。后续所有版本都以这个矩阵裁剪。

标记说明：

- `保留`：用户可见且可用。
- `简化`：保留主功能，但隐藏高级配置、调试信息或危险操作。
- `只读`：可以查看，不允许新增、编辑、删除。
- `隐藏`：前端不展示入口，后端建议继续加权限保护。
- `交付方`：不开放给客户用户，由交付/运维人员通过脚本或后台配置。
- `内部`：只留在完整版或研发环境。

| 编号 | 一级模块 | 功能点 | 当前入口/关键文件 | 基础班 30% | 进阶班 50% | 高级班 70% | 完整版 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | 账号与登录 | 普通账号登录 | `AuthLogin.vue`, `auth.py` | 保留 | 保留 | 保留 | 保留 |
| F02 | 账号与登录 | 管理员登录 | `auth.py`, `/api/auth/admin/login` | 隐藏 | 保留 | 保留 | 保留 |
| F03 | 账号与登录 | 飞书免登/回调 | `AuthCallback.vue`, `feishu.js`, `auth.py` | 可选隐藏 | 可选 | 保留 | 保留 |
| F04 | 账号与登录 | 修改密码/退出 | `App.vue`, `auth.py` | 保留 | 保留 | 保留 | 保留 |
| F05 | 智能问数 | 智能分析工作台 | `SmartAsk.vue`, `/smart-ask` | 保留 | 保留 | 保留 | 保留 |
| F06 | 智能问数 | 自然语言提问 | `SmartAsk.vue`, `smart_chat.py` | 保留 | 保留 | 保留 | 保留 |
| F07 | 智能问数 | SSE 流式执行轨迹 | `/api/smart-chat/stream` | 简化 | 保留 | 保留 | 保留 |
| F08 | 智能问数 | 口径确认/老板确认 | `/api/smart-chat/confirm-by-boss/stream` | 保留 | 保留 | 保留 | 保留 |
| F09 | 智能问数 | 手动停止执行 | `smart_stop_run` | 保留 | 保留 | 保留 | 保留 |
| F10 | 智能问数 | 新会话 | `smart_new_chat` | 保留 | 保留 | 保留 | 保留 |
| F11 | 智能问数 | 自动数据集路由 | `datasource_router.py`, `four_agent_ask.py` | 保留 | 保留 | 保留 | 保留 |
| F12 | 智能问数 | 多数据集手动选择 | `SmartAsk.vue`, `/api/data-sources` | 简化/只读 | 保留 | 保留 | 保留 |
| F13 | 智能问数 | SQL 展示 | `SqlBlock.vue` | 隐藏或简化 | 保留查看 | 保留查看 | 保留 |
| F14 | 智能问数 | SQL 复制 | `SqlBlock.vue` | 隐藏 | 可选 | 保留 | 保留 |
| F15 | 智能问数 | 执行详情右侧面板 | `LogTimeline`, `SmartAsk.vue` | 简化 | 保留 | 保留 | 保留 |
| F16 | 智能问数 | 问题改写/追问 | `four_agent_ask.py` | 保留 | 保留 | 保留 | 保留 |
| F17 | 经营报告 | 报告摘要卡片 | `ResultDigestCard.vue` | 保留 | 保留 | 保留 | 保留 |
| F18 | 经营报告 | 指标 KPI 卡片 | `report_spec_builder.py` | 保留 | 保留 | 保留 | 保留 |
| F19 | 经营报告 | 图表分析 | `ChartViewer`, `report_spec_builder.py` | 保留 | 保留 | 保留 | 保留 |
| F20 | 经营报告 | 图表放大/全屏 | `chart_viewer`, `report_fullscreen` | 保留 | 保留 | 保留 | 保留 |
| F21 | 经营报告 | 钻取式报告 | `useOrgTree.js`, `DatasetReportConfig.vue` | 保留核心 | 保留 | 保留 | 保留 |
| F22 | 经营报告 | 下级组织/人员明细 | `four_agent_ask.py`, `report_spec_builder.py` | 保留 | 保留 | 保留 | 保留 |
| F23 | 经营报告 | 报告模板匹配 | `dataset_report_config.py` | 使用默认 | 可配置 | 可配置 | 保留 |
| F24 | 经营报告 | 报告健康检查 | `report_contract_health.py` | 后端保留 | 后端保留 | 保留 | 保留 |
| F25 | 历史分析 | 左侧历史问题列表 | `smartAskHistory.js` | 保留 | 保留 | 保留 | 保留 |
| F26 | 历史分析 | 同会话报告快照恢复 | `SmartAsk.vue` | 保留 | 保留 | 保留 | 保留 |
| F27 | 历史分析 | 跨会话报告快照恢复 | `smartask_report_history_store.py` | 保留 | 保留 | 保留 | 保留 |
| F28 | 历史分析 | 历史单条删除 | `app_history_delete` | 保留 | 保留 | 保留 | 保留 |
| F29 | 历史分析 | 历史清空 | `app_history_clear` | 保留 | 保留 | 保留 | 保留 |
| F30 | 数据资产 | 数据集列表 | `/datasets`, `DatasetManagement.vue` | 隐藏 | 保留 | 保留 | 保留 |
| F31 | 数据资产 | 新增/编辑/删除数据集 | `bookshelf.py` | 隐藏 | 保留 | 保留 | 保留 |
| F32 | 数据资产 | 字段字典维护 | `Bookshelves.vue`, `bookshelf.py` | 隐藏 | 保留 | 保留 | 保留 |
| F33 | 数据资产 | Golden SQL/口径维护 | `Bookshelves.vue` | 隐藏 | 保留 | 保留 | 保留 |
| F34 | 数据资产 | 常用问题维护 | `common-questions` | 只读展示 | 保留 | 保留 | 保留 |
| F35 | 数据资产 | 数据集 SQL 预览 | `/sql-preview` | 隐藏 | 保留 | 保留 | 保留 |
| F36 | 数据资产 | 数据集 Copilot 生成 | `generate-from-prompt` | 隐藏 | 隐藏 | 可选 | 保留 |
| F37 | 数据连接 | 数据源列表 | `/databases`, `datasources.py` | 交付方 | 保留 | 保留 | 保留 |
| F38 | 数据连接 | 新增/编辑/删除数据源 | `Databases.vue` | 交付方 | 保留 | 保留 | 保留 |
| F39 | 数据连接 | 数据源连通性测试 | `/api/datasources/<id>/test` | 交付方 | 保留 | 保留 | 保留 |
| F40 | 模型服务 | 模型列表 | `/ai-models`, `ai_models.py` | 交付方 | 保留 | 保留 | 保留 |
| F41 | 模型服务 | 新增/编辑/删除模型 | `AIModels.vue` | 交付方 | 保留 | 保留 | 保留 |
| F42 | 模型服务 | 模型连通性测试 | `/api/ai-models/<id>/test` | 交付方 | 保留 | 保留 | 保留 |
| F43 | 模型服务 | 默认模型设置 | `/set-default` | 交付方 | 保留 | 保留 | 保留 |
| F44 | 报告配置 | 数据集报告模板配置 | `/report-config`, `DatasetReportConfig.vue` | 使用预置 | 保留 | 保留 | 保留 |
| F45 | 报告配置 | 默认报告配置 | `/api/report-config/default` | 后端保留 | 保留 | 保留 | 保留 |
| F46 | 智能体配置 | Agent1-4 Prompt 查看 | `/agents`, `AgentManagement.vue` | 隐藏 | 只读可选 | 保留 | 保留 |
| F47 | 智能体配置 | Agent1-4 Prompt 编辑 | `agents.py` | 隐藏 | 隐藏 | 保留 | 保留 |
| F48 | 飞书同步 | 同步任务列表 | `/feishu-sync`, `feishu_sync.py` | 隐藏 | 隐藏 | 保留 | 保留 |
| F49 | 飞书同步 | 新建/编辑同步任务 | `FeishuSync.vue` | 隐藏 | 隐藏 | 保留 | 保留 |
| F50 | 飞书同步 | 同步启动/暂停/恢复 | `feishu_sync.py` | 隐藏 | 隐藏 | 保留 | 保留 |
| F51 | 飞书同步 | 同步日志与清理 | `feishu_sync.py` | 隐藏 | 隐藏 | 只读/简化 | 保留 |
| F52 | 权限 | 固定三级角色 | `auth.py`, `App.vue` | 简化 | 保留 | 保留 | 保留 |
| F53 | 权限 | 员工身份映射 | `/employee-permissions` | 隐藏 | 隐藏 | 保留 | 保留 |
| F54 | 权限 | RBAC 用户管理 | `rbac.py`, `AdminConsole.vue` | 隐藏 | 隐藏 | 简化 | 保留 |
| F55 | 权限 | 角色/用户组管理 | `rbac.py` | 隐藏 | 隐藏 | 简化或隐藏 | 保留 |
| F56 | 权限 | 数据集权限控制 | `data_permissions.py` | 后端默认 | 简化 | 保留 | 保留 |
| F57 | 权限 | 权限来源追踪 | `AdminConsole.vue` | 隐藏 | 隐藏 | 隐藏 | 保留 |
| F58 | 组织树 | 组织树管理 | `/organization-trees` | 隐藏 | 隐藏 | 可选 | 保留 |
| F59 | 组织树 | 组织节点导入 | `organization_trees.py` | 隐藏 | 隐藏 | 可选 | 保留 |
| F60 | 控制台 | 功能权限矩阵 | `/admin-console` | 隐藏 | 隐藏 | 隐藏 | 保留 |
| F61 | 控制台 | 数据权限控制台 | `AdminConsole.vue` | 隐藏 | 隐藏 | 简化可选 | 保留 |
| F62 | 日志审计 | 系统日志列表 | `system_logs.py` | 后端记录 | 后端记录 | 只读可选 | 保留 |
| F63 | 日志审计 | 日志清理 | `/api/admin/system-logs/clear` | 隐藏 | 隐藏 | 隐藏 | 保留 |
| F64 | 运维迁移 | 运行态导出 | `/runtime-migration` | 交付方脚本 | 交付方脚本 | 可选 | 保留 |
| F65 | 运维迁移 | 运行态导入 | `runtime_migration.py` | 交付方脚本 | 交付方脚本 | 可选 | 保留 |
| F66 | 运维迁移 | 运行态备份 | `runtime_migration.py` | 交付方脚本 | 交付方脚本 | 可选 | 保留 |
| F67 | 部署更新 | Docker 部署 | `docker-compose.yml`, `deploy.sh` | 交付方 | 交付方 | 交付方 | 保留 |
| F68 | 部署更新 | update 保留运行态配置 | `update.sh` | 交付方 | 交付方 | 交付方 | 保留 |
| F69 | 部署更新 | 历史快照持久化文件 | `config/smartask_report_history.json` | 保留 | 保留 | 保留 | 保留 |
| F70 | 诊断工具 | API not found 诊断提示 | `backend/app.py` | 保留 | 保留 | 保留 | 保留 |

## 2. 产品分层总览

| 档位 | 展示比例 | 产品定位 | 主要用户 | 交付方式 |
| --- | ---: | --- | --- | --- |
| 基础班 | 30% | 业务问数版 | 业务人员、普通管理者 | 预置数据源、模型、数据集和报告模板，只开放问数工作台 |
| 进阶班 | 50% | 客户管理员可配置版 | 客户管理员、数据负责人 | 开放数据源、模型、数据资产、报告模板配置 |
| 高级班 | 70% | 生产运营版 | 客户超管、运营管理员 | 开放权限、飞书同步、智能体配置、组织树和部分运维 |
| 完整版 | 100% | 内部母版/企业定制版 | 内部研发、交付、定制客户 | 全量能力，持续迭代 |

推荐实现方式：

- 初期用功能开关隐藏，而不是直接删文件。
- 面向外部客户的版本，默认关闭内部诊断、迁移发布、日志清理、权限矩阵等高风险入口。
- 三档都保留报告快照，因为这是当前用户体验的关键能力。
- 三档都保留“某组织下面的人/下级怎么样”的钻取报告链路，不能裁掉组织树相关的只读依赖。

## 3. 当前代码入口地图

### 3.1 前端路由

当前路由集中在 `frontend/src/router/index.js`。

| 路由 | 页面 | 基础班 | 进阶班 | 高级班 | 完整版 |
| --- | --- | --- | --- | --- | --- |
| `/smart-ask` | `SmartAsk.vue` | 保留 | 保留 | 保留 | 保留 |
| `/chat` | 重定向到 `/smart-ask` | 保留 | 保留 | 保留 | 保留 |
| `/auth/callback` | `AuthCallback.vue` | 可选 | 可选 | 保留 | 保留 |
| `/agents` | `AgentManagement.vue` | 删除/隐藏 | 隐藏或只读 | 保留 | 保留 |
| `/datasets` | `DatasetManagement.vue` | 删除/隐藏 | 保留 | 保留 | 保留 |
| `/bookshelves` | `Bookshelves.vue` | 删除/隐藏 | 保留 | 保留 | 保留 |
| `/databases` | `Databases.vue` | 删除/隐藏 | 保留 | 保留 | 保留 |
| `/ai-models` | `AIModels.vue` | 删除/隐藏 | 保留 | 保留 | 保留 |
| `/report-config` | `DatasetReportConfig.vue` | 删除/隐藏 | 保留 | 保留 | 保留 |
| `/feishu-sync` | `FeishuSync.vue` | 删除/隐藏 | 删除/隐藏 | 保留 | 保留 |
| `/employee-permissions` | `EmployeePermissions.vue` | 删除/隐藏 | 删除/隐藏 | 保留 | 保留 |
| `/runtime-migration` | `RuntimeMigration.vue` | 删除/隐藏 | 删除/隐藏 | 可选隐藏 | 保留 |
| `/organization-trees` | `OrganizationTrees.vue` | 删除/隐藏 | 删除/隐藏 | 可选保留 | 保留 |
| `/admin-console` | `AdminConsole.vue` | 删除/隐藏 | 删除/隐藏 | 隐藏 | 保留 |

### 3.2 左侧菜单

菜单集中在 `frontend/src/App.vue` 的 `menuItems`。

| 菜单名 | featureKey | 基础班 | 进阶班 | 高级班 |
| --- | --- | --- | --- | --- |
| 智能分析工作台 | `smart_ask_workspace` | 开 | 开 | 开 |
| 智能体编排配置 | `agent_management` | 关 | 关/只读 | 开 |
| 数据资产管理 | `dataset_management` | 关 | 开 | 开 |
| 数据连接管理 | `database_management` | 关 | 开 | 开 |
| 模型服务配置 | `ai_model_config` | 关 | 开 | 开 |
| 报告模板配置 | `report_config` | 关 | 开 | 开 |
| 飞书数据同步 | `feishu_sync` | 关 | 关 | 开 |
| 迁移发布管理 | `runtime_migration` | 关 | 关 | 可选关 |
| 组织树管理 | `organization_tree_management` | 关 | 关 | 可选开 |
| 角色权限管理 | `employee_permissions` | 关 | 关 | 开 |
| 系统控制台 | `admin_console` | 关 | 关 | 关 |

基础班建议只保留一个菜单：

```js
{ path: '/smart-ask', label: '智能分析工作台', icon: ChatLineRound, minRole: 'user', featureKey: 'smart_ask_workspace' }
```

进阶班建议保留：

```text
smart_ask_workspace
dataset_management
database_management
ai_model_config
report_config
```

高级班建议保留：

```text
smart_ask_workspace
agent_management
dataset_management
database_management
ai_model_config
report_config
feishu_sync
employee_permissions
data_permissions
organization_tree_management   # 可选
runtime_migration              # 可选，默认不放菜单
```

### 3.3 后端蓝图

后端蓝图集中在 `backend/app.py`。

| 蓝图 | 文件 | 基础班 | 进阶班 | 高级班 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `auth_bp` | `controllers/auth.py` | 保留 | 保留 | 保留 | 登录、当前用户、修改密码 |
| `dashboard_bp` | `controllers/dashboard.py` | 可选 | 可选 | 可选 | 当前主界面依赖弱 |
| `smart_chat_bp` | `controllers/smart_chat.py` | 保留 | 保留 | 保留 | 智能问数和历史快照 |
| `bookshelf_bp` | `controllers/bookshelf.py` | 只读保留 | 保留 | 保留 | 基础班仍依赖数据集列表、常用问题 |
| `feature_flags_bp` | `controllers/feature_flags.py` | 只读保留 | 保留 | 保留 | 控制菜单和按钮 |
| `datasources_bp` | `controllers/datasources.py` | 隐藏/交付方 | 保留 | 保留 | 数据源管理 |
| `ai_models_bp` | `controllers/ai_models.py` | 隐藏/交付方 | 保留 | 保留 | 模型管理 |
| `report_config_bp` | `controllers/report_config.py` | 后端保留 | 保留 | 保留 | 基础班用预置模板 |
| `agents_bp` | `controllers/agents.py` | 隐藏 | 隐藏/只读 | 保留 | Prompt 管理 |
| `feishu_bp` | `controllers/feishu_sync.py` | 隐藏 | 隐藏 | 保留 | 同步任务 |
| `data_permissions_bp` | `controllers/data_permissions.py` | 后端默认 | 简化 | 保留 | 数据集权限 |
| `rbac_bp` | `controllers/rbac.py` | 隐藏 | 隐藏 | 简化保留 | 用户、角色、授权 |
| `organization_trees_bp` | `controllers/organization_trees.py` | 只读依赖或隐藏 | 只读依赖或隐藏 | 可选保留 | 钻取报告可能依赖组织层级 |
| `system_logs_bp` | `controllers/system_logs.py` | 后端记录 | 后端记录 | 只读可选 | 不建议给基础/进阶 |
| `runtime_migration_bp` | `controllers/runtime_migration.py` | 交付方 | 交付方 | 可选 | 导入导出、备份 |

重要提醒：

- 不建议基础班删除 `bookshelf.py`，因为智能问数需要数据集、字段、常用问题等只读能力。
- 不建议基础班删除 `report_config.py` 和 `dataset_report_config.py`，因为经营报告需要模板和展示规范。
- 不建议任何版本删除 `smartask_report_history_store.py`，否则服务端历史报告快照会失效。
- 不建议删除 `organization_trees.py` 的底层组织数据能力，钻取报告和“下级人员”问题会受影响；可以隐藏页面入口。

## 4. 基础班 30% 裁剪方案

### 4.1 产品定位

基础班是“业务问数版”。用户只看到智能分析工作台，能问问题、看执行过程、看经营报告、恢复历史报告。数据源、模型、数据集和模板由交付方提前配置。

### 4.2 基础班保留功能

| 模块 | 保留内容 | 展示方式 |
| --- | --- | --- |
| 登录 | 普通登录、退出、修改密码 | 正常展示 |
| 智能问数 | 提问、新会话、停止执行、口径确认 | 正常展示 |
| 数据集 | 默认自动路由，或只读选择一个数据集 | 不展示管理入口 |
| 常用问题 | 推荐问题列表 | 只读展示 |
| 执行轨迹 | 关键步骤、完成状态、结果可信度 | 简化展示 |
| 经营报告 | 摘要、KPI、图表、钻取报告 | 正常展示 |
| 历史分析 | 最近历史、报告快照恢复、删除/清空 | 正常展示 |
| 持久化 | `config/smartask_report_history.json` | 后台保存，不展示文件路径 |

### 4.3 基础班隐藏功能

| 模块 | 隐藏内容 |
| --- | --- |
| 数据资产 | 数据集新增、编辑、删除、字段字典、Golden SQL |
| 数据连接 | 数据源新增、编辑、删除、连通性测试 |
| 模型服务 | 模型 Key、模型新增编辑、默认模型切换 |
| 报告配置 | 报告模板配置页面 |
| 智能体配置 | Agent Prompt 编辑 |
| 飞书同步 | 同步任务和日志 |
| 权限 | 员工权限、RBAC、数据权限后台 |
| 组织树 | 组织树管理页面 |
| 系统 | 系统控制台、日志审计、迁移发布 |

### 4.4 基础班前端裁剪指令

必须保留：

```text
frontend/src/views/SmartAsk.vue
frontend/src/views/AuthCallback.vue                  # 如果保留飞书登录
frontend/src/views/NotFound.vue
frontend/src/auth/AuthLogin.vue
frontend/src/components/smartask/**
frontend/src/state/smartAskSession.js
frontend/src/state/smartAskHistory.js
frontend/src/state/featureFlags.js
frontend/src/api/index.js
frontend/src/router/index.js
frontend/src/App.vue
```

菜单处理：

- `frontend/src/App.vue` 只保留 `智能分析工作台`。
- 其他菜单从 `menuItems` 删除，或通过 `featureKey` 默认关闭。
- 左侧“历史分析”区域保留。
- 顶部角色切换、超管标识等管理味道较重的展示可以隐藏或弱化。

路由处理：

- 保留 `/smart-ask`、`/chat`、`/auth/callback`、`/:pathMatch(.*)*`。
- 其他管理路由全部移除，或保留但跳转到无权限页。

建议关闭的 featureKey：

```text
agent_management
dataset_management
database_management
ai_model_config
report_config
feishu_sync
runtime_migration
organization_tree_management
employee_permissions
admin_console
data_permissions
```

建议保留的 featureKey：

```text
smart_ask_workspace
smart_send_question
smart_stop_run
smart_new_chat
smart_confirm_scope
smart_submit_note
chart_viewer
report_fullscreen
app_history_delete
app_history_clear
```

### 4.5 基础班后端裁剪指令

必须保留：

```text
backend/controllers/auth.py
backend/controllers/smart_chat.py
backend/controllers/bookshelf.py
backend/controllers/feature_flags.py
backend/four_agent_ask.py
backend/report_spec_builder.py
backend/report_scene_registry.py
backend/report_contract_health.py
backend/dataset_report_config.py
backend/datasource_router.py
backend/bookshelf_repository.py
backend/config_manager.py
backend/smartask_report_history_store.py
backend/app.py
```

可以隐藏但不建议立即删除：

```text
backend/controllers/datasources.py
backend/controllers/ai_models.py
backend/controllers/report_config.py
```

原因：

- 数据源、模型、报告模板可由交付方配置，用户界面隐藏即可。
- 问数运行时可能读取这些配置。

基础班可物理删除或不注册蓝图：

```text
backend/controllers/agents.py
backend/controllers/feishu_sync.py
backend/controllers/rbac.py
backend/controllers/data_permissions.py       # 如果不做数据集授权
backend/controllers/runtime_migration.py
backend/controllers/system_logs.py
```

谨慎处理：

```text
backend/controllers/organization_trees.py
```

可以隐藏页面，但如果下钻报告依赖组织树 API 或组织配置，不要删除底层能力。

### 4.6 基础班验收清单

- 登录后左侧只看到“智能分析工作台”和“历史分析”。
- 可以发起普通经营分析问题。
- 可以发起“某代表处下面的人/业务代表怎么样”这类下钻问题。
- 右侧能看到经营报告，而不是只看到普通图表。
- 同一会话点击旧报告“查看详情”能恢复当时报告。
- 刷新页面或重启后端后，历史报告快照仍能恢复。
- 删除某条历史后，该条报告快照不能再恢复。
- 直接访问 `/datasets`、`/databases`、`/ai-models` 等管理路由应被拦截。

## 5. 进阶班 50% 裁剪方案

### 5.1 产品定位

进阶班是“客户管理员可配置版”。它在基础班之上，开放数据源、模型、数据资产和报告模板，让客户管理员能自己维护问数基础配置。

### 5.2 进阶班新增开放功能

| 模块 | 开放内容 | 不开放内容 |
| --- | --- | --- |
| 数据资产 | 数据集、字段字典、Golden SQL、常用问题 | Copilot 自动生成可先隐藏 |
| 数据连接 | 数据源 CRUD、连通性测试 | 高级同步任务仍隐藏 |
| 模型服务 | 模型 CRUD、连通性测试、默认模型 | 模型成本审计暂不开放 |
| 报告配置 | 数据集报告模板、默认报告规范 | 内部健康诊断隐藏 |
| 数据权限 | 可选简单数据集授权 | 完整 RBAC 隐藏 |

### 5.3 进阶班前端裁剪指令

保留页面：

```text
frontend/src/views/SmartAsk.vue
frontend/src/views/DatasetManagement.vue
frontend/src/views/Bookshelves.vue
frontend/src/views/Databases.vue
frontend/src/views/AIModels.vue
frontend/src/views/DatasetReportConfig.vue
frontend/src/views/AuthCallback.vue
frontend/src/views/NotFound.vue
```

菜单保留：

```text
智能分析工作台
数据资产管理
数据连接管理
模型服务配置
报告模板配置
```

继续隐藏：

```text
智能体编排配置
飞书数据同步
迁移发布管理
组织树管理
角色权限管理
系统控制台
```

路由保留：

```text
/smart-ask
/chat
/datasets
/bookshelves
/databases
/ai-models
/report-config
/auth/callback
```

### 5.4 进阶班后端裁剪指令

保留蓝图：

```text
auth_bp
smart_chat_bp
bookshelf_bp
datasources_bp
ai_models_bp
report_config_bp
feature_flags_bp
dashboard_bp
```

隐藏或不注册：

```text
agents_bp
feishu_bp
rbac_bp
runtime_migration_bp
system_logs_bp
organization_trees_bp     # 如无组织树配置需求
```

`data_permissions_bp` 有两种策略：

- 简单版：隐藏页面，只在后端用默认规则控制。
- 管理版：开放简单数据集授权，但不要开放完整权限矩阵。

### 5.5 进阶班验收清单

- 普通用户登录后只能问数。
- 管理员登录后能看到数据资产、数据连接、模型服务、报告模板。
- 管理员能新增/编辑/测试数据源。
- 管理员能新增/编辑/测试模型，并设置默认模型。
- 管理员能维护数据集字段、常用问题和报告模板。
- 飞书同步、角色权限、系统控制台、迁移发布入口不可见。
- 问数链路仍能生成钻取报告和恢复历史快照。

## 6. 高级班 70% 裁剪方案

### 6.1 产品定位

高级班是“生产运营版”。它面向真实生产部署，允许客户做同步、权限、智能体 Prompt 和组织树相关配置，但仍不默认开放完整系统控制台和危险运维能力。

### 6.2 高级班新增开放功能

| 模块 | 开放内容 | 建议限制 |
| --- | --- | --- |
| 智能体配置 | Agent1-4 Prompt 查看和编辑 | 保留恢复默认/审计提示 |
| 飞书同步 | 同步任务、状态、启动/暂停/恢复 | 日志清理按钮默认隐藏 |
| 角色权限 | 用户、固定角色、重置密码 | 多级用户组可隐藏 |
| 数据权限 | 数据集授权 | 权限来源追踪可隐藏 |
| 组织树 | 组织树查看、导入、节点维护 | 可作为选配 |
| 日志审计 | 只读日志、统计 | 清理操作隐藏 |
| 运维迁移 | 导出/备份可选 | 导入操作交付方使用 |

### 6.3 高级班前端裁剪指令

保留页面：

```text
SmartAsk.vue
DatasetManagement.vue
Bookshelves.vue
Databases.vue
AIModels.vue
DatasetReportConfig.vue
AgentManagement.vue
FeishuSync.vue
EmployeePermissions.vue
OrganizationTrees.vue      # 可选
RuntimeMigration.vue       # 可选，默认不展示菜单
NotFound.vue
AuthCallback.vue
```

默认仍隐藏：

```text
AdminConsole.vue
```

如果要开放系统控制台，建议只开放 `data` 或只读视图，不开放完整 `permissions` 矩阵。

### 6.4 高级班后端裁剪指令

保留蓝图：

```text
auth_bp
dashboard_bp
smart_chat_bp
bookshelf_bp
datasources_bp
ai_models_bp
report_config_bp
agents_bp
feishu_bp
data_permissions_bp
rbac_bp
organization_trees_bp
feature_flags_bp
system_logs_bp             # 只读可选
runtime_migration_bp       # 可选
```

后端限制建议：

- `system_logs_bp` 只允许 GET，隐藏清理接口。
- `runtime_migration_bp` 对客户只开放 summary/export/backup，import 只给交付方。
- `rbac_bp` 可以保留用户和角色分配，隐藏复杂用户组。
- `organization_trees_bp` 如开放导入，必须保留预览再应用的流程。

### 6.5 高级班验收清单

- 包含进阶班全部能力。
- 超管能维护智能体 Prompt。
- 超管能配置飞书同步任务，并查看同步状态。
- 超管能维护用户、角色和数据集授权。
- 组织树管理按项目需要开放。
- 系统日志可查看但不能随意清理。
- 迁移导入、权限矩阵、内部诊断不默认开放。

## 7. 完整版/内部母版

完整版继续作为研发和定制交付母版，不建议作为普通客户默认版本。

完整版保留：

- 系统控制台。
- 功能权限矩阵。
- 数据权限双向视图。
- 系统日志审计与清理。
- 迁移发布管理。
- 运行态导入导出。
- 数据集 Copilot。
- 组织树管理。
- 内部诊断和验证脚本。
- 所有后台蓝图和管理页面。

完整版职责：

- 作为后续功能迭代源头。
- 作为定制项目二次开发母版。
- 作为基础班、进阶班、高级班的上游代码。

## 8. 代码裁剪详细清单

### 8.1 基础班可删除/隐藏页面

优先隐藏，确认无依赖后再删除：

```text
frontend/src/views/AgentManagement.vue
frontend/src/views/DatasetManagement.vue
frontend/src/views/Bookshelves.vue
frontend/src/views/Databases.vue
frontend/src/views/AIModels.vue
frontend/src/views/DatasetReportConfig.vue
frontend/src/views/FeishuSync.vue
frontend/src/views/EmployeePermissions.vue
frontend/src/views/RuntimeMigration.vue
frontend/src/views/OrganizationTrees.vue
frontend/src/views/AdminConsole.vue
```

基础班不要删除：

```text
frontend/src/components/smartask/**
frontend/src/state/smartAskHistory.js
frontend/src/state/smartAskSession.js
frontend/src/api/index.js
```

### 8.2 进阶班可删除/隐藏页面

```text
frontend/src/views/AgentManagement.vue        # 可只读保留
frontend/src/views/FeishuSync.vue
frontend/src/views/EmployeePermissions.vue
frontend/src/views/RuntimeMigration.vue
frontend/src/views/OrganizationTrees.vue
frontend/src/views/AdminConsole.vue
```

### 8.3 高级班可隐藏页面

```text
frontend/src/views/AdminConsole.vue
frontend/src/views/RuntimeMigration.vue       # 可隐藏菜单，仅交付方访问
```

### 8.4 基础班后端接口策略

保留并可被前端调用：

```text
/api/auth/me
/api/auth/login
/api/auth/logout
/api/auth/change-password
/api/smart-chat
/api/smart-chat/stream
/api/smart-chat/confirm-by-boss
/api/smart-chat/confirm-by-boss/stream
/api/smart-chat/report-history
/api/data-sources
/api/bookshelves/datasets
/api/bookshelves/common-questions
/api/feature-flags
```

基础班应禁止客户直接调用：

```text
/api/datasources
/api/ai-models
/api/agents
/api/feishu-sync
/api/admin/rbac
/api/admin/data-permissions
/api/admin/system-logs
/api/runtime-migration
/api/admin/organization-trees
```

### 8.5 进阶班后端接口策略

在基础班基础上开放：

```text
/api/datasources
/api/ai-models
/api/bookshelves/datasets/<id>/full
/api/bookshelves/datasets/<id>/sql-preview
/api/datasets/<id>/report-config
/api/report-config/default
```

继续禁止：

```text
/api/agents
/api/feishu-sync
/api/admin/rbac
/api/admin/system-logs
/api/runtime-migration
/api/admin/organization-trees
```

### 8.6 高级班后端接口策略

在进阶班基础上开放：

```text
/api/agents
/api/feishu-sync
/api/admin/rbac/overview
/api/admin/rbac/users
/api/admin/rbac/users/<id>/permissions
/api/admin/rbac/datasets/<dataset_id>/access
/api/admin/data-permissions
/api/admin/organization-trees
/api/admin/system-logs              # GET only 建议
```

谨慎开放：

```text
/api/runtime-migration/import
/api/admin/system-logs/clear
/api/bookshelves/datasets/generate-from-prompt
```

## 9. 运行态配置与持久化

当前项目有一批运行态配置不应该随代码更新被覆盖。裁剪代码时也要保留这些文件的更新策略。

建议保留的运行态文件：

```text
config/app_config.json
config/ai_settings.json
config/datasources.json
config/feishu_sync.json
config/feature_flags.json
config/rbac_permissions.json
config/data_permissions.json
config/smartask_report_history.json
backend/data/agent_registry.json
```

历史报告快照说明：

- 前端本地历史：`frontend/src/state/smartAskHistory.js`。
- 后端持久化：`backend/smartask_report_history_store.py`。
- 持久化文件：`config/smartask_report_history.json`。
- 文件不是启动时自动生成，而是在第一次成功保存报告历史后生成。
- 如果服务器更新代码，必须确保 `update.sh`、`runtime_migration.py`、`export_runtime_config.py` 都把该文件纳入备份/迁移。

部署提醒：

- 新增接口后，必须重启或重建后端容器，否则前端会出现 `API not found`。
- 如果只更新前端，服务端历史接口不会生效，只会回退到本地历史。
- 推荐更新命令：`docker compose up -d --build backend frontend`。

## 10. 功能开关模板

### 10.1 基础班功能开关

```json
{
  "smart_ask_workspace": true,
  "smart_send_question": true,
  "smart_stop_run": true,
  "smart_new_chat": true,
  "smart_confirm_scope": true,
  "smart_submit_note": true,
  "chart_viewer": true,
  "report_fullscreen": true,
  "app_history_delete": true,
  "app_history_clear": true,
  "agent_management": false,
  "dataset_management": false,
  "database_management": false,
  "ai_model_config": false,
  "report_config": false,
  "feishu_sync": false,
  "runtime_migration": false,
  "organization_tree_management": false,
  "employee_permissions": false,
  "admin_console": false,
  "data_permissions": false
}
```

### 10.2 进阶班功能开关

```json
{
  "smart_ask_workspace": true,
  "dataset_management": true,
  "database_management": true,
  "ai_model_config": true,
  "report_config": true,
  "agent_management": false,
  "feishu_sync": false,
  "runtime_migration": false,
  "organization_tree_management": false,
  "employee_permissions": false,
  "admin_console": false,
  "data_permissions": false
}
```

### 10.3 高级班功能开关

```json
{
  "smart_ask_workspace": true,
  "dataset_management": true,
  "database_management": true,
  "ai_model_config": true,
  "report_config": true,
  "agent_management": true,
  "feishu_sync": true,
  "employee_permissions": true,
  "data_permissions": true,
  "organization_tree_management": true,
  "runtime_migration": false,
  "admin_console": false
}
```

## 11. 后续功能迭代路线

| 阶段 | 迭代重点 | 下放版本 |
| --- | --- | --- |
| V1 | 稳定问数、报告快照、历史恢复、基础钻取报告 | 基础班 |
| V2 | 数据源、模型、数据集、报告模板自助配置 | 进阶班 |
| V3 | 飞书同步、智能体配置、数据集权限 | 高级班 |
| V4 | 组织树管理、只读审计、运行态备份 | 高级班 |
| V5 | 系统控制台、权限矩阵、迁移发布、Copilot | 完整版/增购 |
| V6 | 多租户、语义层、指标血缘、自动回归测试 | 完整版/企业版 |

## 12. 版本交付验收

### 12.1 基础班验收

- 登录后只看到智能分析工作台。
- 可以发送问题并生成经营报告。
- 可以查看执行轨迹。
- 可以查看钻取式报告。
- 可以恢复历史报告快照。
- 删除历史后，对应报告快照一起消失。
- 访问管理页面不可见或无权限。
- 后端重启后，`config/smartask_report_history.json` 中的历史快照仍可恢复。

### 12.2 进阶班验收

- 包含基础班所有能力。
- 管理员可以维护数据源。
- 管理员可以维护模型。
- 管理员可以维护数据集。
- 管理员可以维护常用问题。
- 管理员可以维护报告模板。
- 不出现系统控制台、飞书同步、角色权限、迁移发布入口。

### 12.3 高级班验收

- 包含进阶班所有能力。
- 可以维护智能体 Prompt。
- 可以配置飞书同步。
- 可以做基础用户和数据集授权。
- 可以按需管理组织树。
- 可以查看只读日志或运维状态。
- 不默认开放完整系统控制台、迁移导入和日志清理。

## 13. 构建与回归命令

前端构建：

```powershell
cd frontend
npm run build
```

后端语法检查：

```powershell
cd ..
$env:PYTHONDONTWRITEBYTECODE='1'
python - <<'PY'
import ast
from pathlib import Path
for name in [
    'backend/app.py',
    'backend/controllers/smart_chat.py',
    'backend/four_agent_ask.py',
    'backend/smartask_report_history_store.py',
]:
    ast.parse(Path(name).read_text(encoding='utf-8-sig'), filename=name)
    print('OK', name)
PY
```

Docker 验证：

```bash
docker compose config
docker compose up -d --build backend frontend
docker compose ps
docker compose logs -f backend
```

重点业务回归：

1. 普通经营问题能生成报告。
2. “某代表处下面的人/业务代表怎么样”能返回下级明细并渲染钻取报告。
3. 同一会话连续提问后，旧问题报告能通过“查看详情”恢复。
4. 历史分析点击后能恢复当时报告快照。
5. 删除历史后，对应报告快照不再恢复。
6. `config/smartask_report_history.json` 在后端重启后仍保留。

## 14. 对外交付话术

基础班：

> 面向业务人员的智能经营分析工作台，预置数据集和模型，开箱即可问数、看报告、查历史。

进阶班：

> 在智能问数基础上，开放数据源、数据集、模型和报告模板维护，适合客户管理员自行配置。

高级班：

> 覆盖问数、数据治理、模型配置、报告模板、飞书同步和基础权限管理，适合生产环境长期运营。

完整版：

> 内部研发和企业定制母版，包含系统控制台、权限矩阵、迁移发布、审计和自动化数据集生成等高级能力。
