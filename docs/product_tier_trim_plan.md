# Data Agent 分版本裁剪计划书

> 目的：在不交付当前完整项目全部能力的前提下，拆出「基础班」「升级版」「80% 功能版」三个可售卖/可交付版本。本文面向开发执行，重点写清楚：删哪些代码、删完需要补哪些兼容代码、怎么确认项目还能正常跑。

## 0. 当前完整版能力基线

当前项目大致由这些模块组成：

| 模块 | 前端入口 | 后端蓝图/模块 | 完整版状态 |
| --- | --- | --- | --- |
| 智能分析工作台 | `frontend/src/views/SmartAsk.vue` | `controllers/smart_chat.py` | 保留核心 |
| 数据书架治理 | `Bookshelves.vue` | `controllers/bookshelf.py` | 完整版保留 |
| 数据资产管理 | `DatasetManagement.vue` | `controllers/bookshelf.py`、配置文件 | 完整版保留 |
| 数据连接管理 | `Databases.vue` | `controllers/datasources.py` | 完整版保留 |
| 模型服务配置 | `AIModels.vue` | `controllers/ai_models.py` | 完整版保留 |
| 智能体编排配置 | `AgentManagement.vue` | `controllers/agents.py` | 完整版保留 |
| 报告模板配置 | `DatasetReportConfig.vue` | `controllers/report_config.py` | 完整版保留 |
| 飞书数据同步 | `FeishuSync.vue` | `controllers/feishu_sync.py`、`feishu_sync_*` | 完整版保留 |
| 角色权限管理/RBAC | `EmployeePermissions.vue` | `controllers/rbac.py`、`auth.py`、`rbac_store.py` | 完整版保留 |
| 系统控制台/权限矩阵/日志 | `AdminConsole.vue` | `feature_flags.py`、`system_logs.py` | 完整版保留 |
| 迁移发布管理 | `RuntimeMigration.vue` | `controllers/runtime_migration.py` | 完整版保留 |

裁剪原则：

1. 智能问数核心链路优先保留：登录、选数据集、提问、SQL/报告生成、结果展示。
2. 管理端能力按版本逐步开放：基础班几乎不开放，升级版开放少量配置，80% 功能版开放大部分运营能力。
3. 不建议第一次就物理删除所有代码。建议先做「版本开关 + 路由隐藏 + 后端 404/403」验证，再进行文件级删除。
4. 真要交付源码时，按本文的「可物理删除」清单删除，然后跑构建和后端 import 检查。

---

## 1. 版本能力矩阵

| 能力 | 基础班 | 升级版 | 80% 功能版 | 当前完整版 |
| --- | --- | --- | --- | --- |
| 智能分析工作台 | 保留 | 保留 | 保留 | 保留 |
| 多数据集选择/常用问题 | 可保留简版 | 保留 | 保留 | 保留 |
| 结果报告卡片 | 保留简版 | 保留 | 保留 | 保留 |
| 数据集管理 | 删除 | 保留基础维护 | 保留完整维护 | 保留 |
| 数据连接管理 | 删除 | 保留 | 保留 | 保留 |
| 模型服务配置 | 删除，配置写死 | 保留 | 保留 | 保留 |
| 智能体编排配置 | 删除 | 删除或只读 | 保留 | 保留 |
| 报告模板配置 | 删除，使用默认模板 | 保留基础模板 | 保留 | 保留 |
| 飞书数据同步 | 删除 | 删除 | 保留 | 保留 |
| RBAC 自定义角色/分组 | 删除 | 删除，保留固定三级角色 | 可保留精简版 | 保留完整 |
| 数据权限视图 | 删除 | 删除 | 保留基础资源授权 | 保留完整双向视图 |
| 系统控制台/权限矩阵 | 删除 | 删除 | 删除或仅内部保留 | 保留 |
| 系统日志审计 | 删除 | 删除 | 保留只读日志 | 保留 |
| 迁移发布管理 | 删除 | 删除 | 删除 | 保留 |
| 自动生成/导入数据集 Copilot | 删除 | 删除 | 可删除 | 保留 |

---

## 2. 基础班裁剪方案

### 2.1 版本定位

基础班只给客户一个「能问数、能看结果」的最小可用系统。后台配置、权限治理、飞书同步、迁移发布、模型管理全部不交付。

适合：

- 单客户、单环境、少量固定数据集。
- 数据源、模型、提示词由交付方在配置文件中预置。
- 客户只使用前台问数，不维护后台。

### 2.2 保留功能

必须保留：

- 登录：
  - `frontend/src/auth/AuthLogin.vue`
  - `frontend/src/views/AuthCallback.vue`
  - `backend/controllers/auth.py`
  - `backend/auth_store.py`
- 智能分析工作台：
  - `frontend/src/views/SmartAsk.vue`
  - `frontend/src/components/smartask/**`
  - `frontend/src/state/smartAsk*.js`
  - `frontend/src/api/index.js` 中智能问数相关 API
  - `backend/controllers/smart_chat.py`
  - `backend/four_agent_ask.py`
  - `backend/report_*`
  - `backend/disambiguation/**`
  - `backend/memory/**`
- 数据集只读读取能力：
  - `backend/controllers/bookshelf.py` 里只保留问数依赖的只读接口
  - `backend/bookshelf_repository.py`
  - `backend/datasource_router.py`
  - `backend/config_manager.py`
- 健康检查：
  - `backend/app.py` 的 `/api/health`

### 2.3 前端删除清单

#### 2.3.1 可物理删除的页面

删除以下文件：

```text
frontend/src/views/AdminConsole.vue
frontend/src/views/AgentManagement.vue
frontend/src/views/AIModels.vue
frontend/src/views/Bookshelves.vue
frontend/src/views/DatasetManagement.vue
frontend/src/views/DatasetReportConfig.vue
frontend/src/views/Databases.vue
frontend/src/views/EmployeePermissions.vue
frontend/src/views/FeishuSync.vue
frontend/src/views/RuntimeMigration.vue
frontend/src/views/SmartAsk copy.vue
```

保留：

```text
frontend/src/views/SmartAsk.vue
frontend/src/views/AuthCallback.vue
frontend/src/views/NotFound.vue
frontend/src/auth/AuthLogin.vue
frontend/src/components/smartask/**
```

#### 2.3.2 修复路由

修改 `frontend/src/router/index.js`：

只保留：

```js
[
  { path: '/', redirect: '/smart-ask' },
  {
    path: '/smart-ask',
    name: 'SmartAsk',
    component: () => import('../views/SmartAsk.vue'),
    meta: { title: '智能分析工作台', roles: ['super_admin', 'admin', 'user'] }
  },
  {
    path: '/chat',
    redirect: '/smart-ask'
  },
  {
    path: '/auth/callback',
    name: 'AuthCallback',
    component: () => import('../views/AuthCallback.vue'),
    meta: { title: '飞书登录', public: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
    meta: { title: '页面不存在' }
  }
]
```

删除这些路由：

```text
/agents
/datasets
/bookshelves
/databases
/ai-models
/report-config
/feishu-sync
/employee-permissions
/runtime-migration
/admin-console
```

#### 2.3.3 修复侧边栏

修改 `frontend/src/App.vue` 的 `navItems`：

只保留：

```js
const navItems = [
  { path: '/smart-ask', label: '智能分析工作台', icon: ChatLineRound, minRole: 'user', featureKey: 'smart_ask_workspace' }
]
```

同时删除/隐藏：

- 顶部进入系统控制台的入口。
- `from=admin-console` 返回控制台逻辑。
- 与 `featureKey` 强相关的后台菜单展示逻辑可以保留，但基础班建议让 `isFeatureEnabled` 对 `smart_ask_workspace` 永远返回 true。

#### 2.3.4 修复 API 导出

修改 `frontend/src/api/index.js`。

基础班保留：

```js
healthCheck
getDashboard // 如果 SmartAsk 不依赖可删除
getCurrentUser
logout
passwordLogin
adminLogin
changePassword
getFeishuLoginUrl // 如果保留飞书登录则保留
feishuInAppAuth   // 如果保留飞书免登则保留
getFeatureFlags   // 可保留简化
getBookshelfHealth
getBookshelfDatasets
getCommonQuestions
getActiveAIModels // 如果 SmartAsk 需要模型下拉
sendSmartChat
sendSmartChatStream
confirmByBoss
confirmByBossStream
getVannaStatus
```

删除这些导出：

```text
getAdminFeatureFlags
saveAdminFeatureFlags
resetAdminFeatureFlags
getDataPermissions
saveDataPermissions
getRbacOverview
createRbacRole / updateRbacRole / deleteRbacRole
createRbacGroup / updateRbacGroup / deleteRbacGroup
createRbacUser / updateRbacUser / resetRbacUserPassword / bulkUpdateRbacUsers
getRbacUserPermissions
getRbacDatasetAccess
getSystemLogs / getSystemLogStats / getSystemLogDetail / clearSystemLogs
getRuntimeMigration*
createRuntimeMigrationBackup
getDataSources / createDataSource / updateDataSource / deleteDataSource / testDataSource
getAIModels / createAIModel / updateAIModel / deleteAIModel / testAIModel / setDefaultAIModel
getReportConfig / upsertReportConfig / deleteReportConfig / getDefaultReportConfig
getFeishuSync*
getBookshelfDatasetFull / saveBookshelfDatasetFull / previewBookshelfDatasetSql
createBookshelfDataset / updateBookshelfDataset / deleteBookshelfDataset
generateBookshelfDatasetFromPrompt
getSourceTables
getAgents / getAgent / updateAgent
```

注意：删除 API 导出前，先用 `rg "createRbacRole|getFeishuSync|getRuntimeMigration" frontend/src` 确认没有基础班保留页面引用。

### 2.4 后端删除清单

#### 2.4.1 `backend/app.py` 删除蓝图注册

基础班建议保留：

```py
from controllers.auth import auth_bp
from controllers.dashboard import dashboard_bp
from controllers.smart_chat import smart_chat_bp
from controllers.bookshelf import bookshelf_bp
from controllers.feature_flags import feature_flags_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(smart_chat_bp)
app.register_blueprint(bookshelf_bp)
app.register_blueprint(feature_flags_bp)
```

删除这些 import 和 register：

```py
from controllers.ai_models import ai_models_bp
from controllers.agents import agents_bp
from controllers.datasources import datasources_bp
from controllers.data_permissions import data_permissions_bp
from controllers.feishu_sync import feishu_bp
from controllers.report_config import report_config_bp
from controllers.runtime_migration import runtime_migration_bp
from controllers.system_logs import system_logs_bp
from controllers.rbac import rbac_bp
```

对应删除：

```py
app.register_blueprint(datasources_bp)
app.register_blueprint(data_permissions_bp)
app.register_blueprint(ai_models_bp)
app.register_blueprint(feishu_bp)
app.register_blueprint(agents_bp)
app.register_blueprint(report_config_bp)
app.register_blueprint(runtime_migration_bp)
app.register_blueprint(system_logs_bp)
app.register_blueprint(rbac_bp)
```

#### 2.4.2 可物理删除的后端文件

```text
backend/controllers/ai_models.py
backend/controllers/agents.py
backend/controllers/data_permissions.py
backend/controllers/datasources.py
backend/controllers/feishu_sync.py
backend/controllers/report_config.py
backend/controllers/runtime_migration.py
backend/controllers/system_logs.py
backend/controllers/rbac.py

backend/ai 模型管理相关测试脚本：backend/test_ai_connection.py
backend/feishu_sync_manager.py
backend/feishu_sync_service.py
backend/feishu_sync_logger.py
backend/feishu_url_parser.py
backend/get_feishu_tables.py
backend/start_feishu_sync.py
backend/start_feishu_sync.bat
backend/rbac_store.py
backend/data_permission_store.py
backend/runtime_migration.py
backend/import_runtime_config.py
backend/export_runtime_config.py
backend/import_bookshelf_bundle.py
backend/export_bookshelf_bundle.py
backend/dataset_copilot/**
backend/create_consumer_standard_dataset.py
backend/fill_syyb_dataset.py
```

谨慎删除：

```text
backend/controllers/bookshelf.py
backend/bookshelf_repository.py
backend/datasource_router.py
backend/sql_prompt_manager.py
backend/report_spec_builder.py
backend/report_scene_registry.py
backend/report_contract_health.py
```

这些通常被 `smart_chat` 或报告生成链路依赖，基础班也要保留。

### 2.5 删除后必须修复的地方

#### 2.5.1 `SmartAsk.vue` 的管理入口

检查 `SmartAsk.vue` 中是否存在：

```text
数据集配置入口
报告模板配置入口
模型配置入口
智能体配置入口
查看详情跳转后台
```

基础班处理方式：

- 跳转后台的按钮隐藏。
- 数据集下拉保留，但只展示已配置数据集。
- 模型下拉可隐藏，固定使用默认模型。

#### 2.5.2 `feature_flags.py`

基础班有两种做法：

推荐做法：保留 `feature_flags.py`，但只开放最小 key：

```py
smart_ask_workspace = True
```

其他 key 即使存在也不影响，因为页面和路由已经删除。

更彻底做法：删除 feature flag 管理接口，只保留 `/api/feature-flags` 返回：

```json
{
  "success": true,
  "features": {
    "smart_ask_workspace": true
  }
}
```

#### 2.5.3 登录和权限

基础班建议保留简单登录，不交付 RBAC：

- 保留 `auth.py`。
- 删除或隐藏员工权限维护接口：
  - `/api/auth/employee-permissions`
  - `/api/admin/rbac/**`
- `auth_me` 仍返回用户基础角色即可。

如果保留飞书扫码登录：

- 可以保留当前「飞书首次登录自动创建普通用户」逻辑。
- 不给前端维护页面，只允许交付方改 `config/employee_permissions.json`。

### 2.6 基础班验收

执行：

```powershell
cd frontend
npm run build
```

执行：

```powershell
cd ..
& 'C:\Users\liutq09\AppData\Local\anaconda3\python.exe' -c "import sys; sys.path.insert(0,'backend'); import app; print('APP_IMPORT_OK')"
```

手工验收：

1. 打开系统后只看到「智能分析工作台」。
2. 登录后能选择默认数据集。
3. 能发送问题。
4. 能收到分析结果、SQL 或报告卡片。
5. 访问 `/datasets`、`/admin-console`、`/employee-permissions` 返回 404 或跳转无权限页。

---

## 3. 升级版裁剪方案

### 3.1 版本定位

升级版比基础班多开放「数据源、数据集、模型、报告模板」这类交付配置能力，但不开放复杂治理能力。

适合：

- 客户有少量管理员。
- 允许客户维护数据连接、数据集、模型配置。
- 不给 RBAC 自定义角色、不开放系统控制台、不开放迁移发布。

### 3.2 保留功能

在基础班基础上额外保留：

前端：

```text
frontend/src/views/DatasetManagement.vue
frontend/src/views/Databases.vue
frontend/src/views/AIModels.vue
frontend/src/views/DatasetReportConfig.vue
frontend/src/views/Bookshelves.vue   # 可选，建议保留为数据书架治理
```

后端：

```text
backend/controllers/datasources.py
backend/controllers/ai_models.py
backend/controllers/report_config.py
backend/controllers/bookshelf.py
backend/dataset_report_config.py
backend/sql_prompt_manager.py
backend/bookshelf_repository.py
```

### 3.3 前端删除清单

升级版删除：

```text
frontend/src/views/AdminConsole.vue
frontend/src/views/AgentManagement.vue
frontend/src/views/EmployeePermissions.vue
frontend/src/views/FeishuSync.vue
frontend/src/views/RuntimeMigration.vue
frontend/src/views/SmartAsk copy.vue
```

升级版保留路由：

```text
/smart-ask
/chat
/auth/callback
/datasets
/bookshelves
/databases
/ai-models
/report-config
```

升级版删除路由：

```text
/agents
/feishu-sync
/employee-permissions
/runtime-migration
/admin-console
```

修改 `frontend/src/App.vue` 的 `navItems`：

保留：

```js
[
  { path: '/smart-ask', label: '智能分析工作台', featureKey: 'smart_ask_workspace' },
  { path: '/datasets', label: '数据资产管理', featureKey: 'dataset_management' },
  { path: '/bookshelves', label: '数据书架治理', featureKey: 'bookshelf_management' },
  { path: '/databases', label: '数据连接管理', featureKey: 'database_management' },
  { path: '/ai-models', label: '模型服务配置', featureKey: 'ai_model_config' },
  { path: '/report-config', label: '报告模板配置', featureKey: 'report_config' }
]
```

删除：

```text
智能体编排配置
飞书数据同步
迁移发布管理
角色权限管理
系统控制台
```

### 3.4 后端删除清单

`backend/app.py` 保留：

```py
auth_bp
dashboard_bp
datasources_bp
ai_models_bp
smart_chat_bp
bookshelf_bp
report_config_bp
feature_flags_bp
```

删除：

```py
data_permissions_bp
feishu_bp
agents_bp
runtime_migration_bp
system_logs_bp
rbac_bp
```

可物理删除：

```text
backend/controllers/agents.py
backend/controllers/data_permissions.py
backend/controllers/feishu_sync.py
backend/controllers/runtime_migration.py
backend/controllers/system_logs.py
backend/controllers/rbac.py

backend/feishu_sync_manager.py
backend/feishu_sync_service.py
backend/feishu_sync_logger.py
backend/feishu_url_parser.py
backend/get_feishu_tables.py
backend/start_feishu_sync.py
backend/rbac_store.py
backend/data_permission_store.py
backend/runtime_migration.py
backend/import_runtime_config.py
backend/export_runtime_config.py
```

可选删除：

```text
backend/dataset_copilot/**
backend/create_consumer_standard_dataset.py
backend/fill_syyb_dataset.py
```

如果升级版不提供「自然语言生成数据集」能力，建议删除 `dataset_copilot`。

### 3.5 删除后必须修复的地方

#### 3.5.1 权限退化为固定三级角色

升级版不交付完整 RBAC。处理方式：

- 保留 `auth.py` 中固定角色：
  - `super_admin`
  - `admin`
  - `user`
- 删除前端 RBAC 页面。
- 后端删除 `/api/admin/rbac/**`。
- 菜单权限继续用 `minRole` 控制。

#### 3.5.2 功能开关接口降级

`feature_flags.py` 可以保留，但不要开放控制台编辑。

建议默认开启：

```text
smart_ask_workspace
dataset_management
bookshelf_management
database_management
ai_model_config
report_config
```

默认关闭或删除：

```text
agent_management
feishu_sync
runtime_migration
employee_permissions
admin_console
system_logs
data_permissions
```

#### 3.5.3 `api/index.js`

保留基础班 API，加上：

```text
getDataSources / createDataSource / updateDataSource / deleteDataSource / testDataSource
getAIModels / getActiveAIModels / createAIModel / updateAIModel / deleteAIModel / testAIModel / setDefaultAIModel
getReportConfig / upsertReportConfig / deleteReportConfig / getDefaultReportConfig
getBookshelfHealth
getBookshelfDatasets
createBookshelfDataset
updateBookshelfDataset
deleteBookshelfDataset
getBookshelfDatasetFull
saveBookshelfDatasetFull
previewBookshelfDatasetSql
getSourceTables
getCommonQuestions
```

删除：

```text
RBAC APIs
System log APIs
Runtime migration APIs
Feishu sync APIs
Agent APIs
Data permission APIs
Admin feature flag save/reset APIs
```

#### 3.5.4 页面里的跨模块入口

检查并隐藏：

```powershell
rg "/agents|/feishu-sync|/employee-permissions|/runtime-migration|/admin-console" frontend/src
```

凡是升级版删除的路由，都要删除跳转按钮或改为不可见。

### 3.6 升级版验收

1. 菜单只出现：
   - 智能分析工作台
   - 数据资产管理
   - 数据书架治理
   - 数据连接管理
   - 模型服务配置
   - 报告模板配置
2. 管理员能新增/编辑数据源。
3. 管理员能维护模型配置。
4. 管理员能维护数据集和报告模板。
5. 用户能正常问数。
6. 访问 `/employee-permissions`、`/admin-console`、`/runtime-migration` 返回 404 或无权限。

构建检查：

```powershell
cd frontend
npm run build
```

后端检查：

```powershell
cd ..
& 'C:\Users\liutq09\AppData\Local\anaconda3\python.exe' -c "import sys; sys.path.insert(0,'backend'); import app; print('APP_IMPORT_OK')"
```

---

## 4. 80% 功能版裁剪方案

### 4.1 版本定位

80% 功能版保留大多数客户可感知价值，但删除内部运维、迁移发布、系统控制台、过深的权限治理能力。

适合：

- 客户需要自行管理数据源、模型、数据集、飞书同步。
- 客户需要基本账号和数据权限。
- 不希望交付完整系统控制台、迁移工具、权限矩阵、内部诊断能力。

### 4.2 保留功能

前端保留：

```text
SmartAsk.vue
DatasetManagement.vue
Bookshelves.vue
Databases.vue
AIModels.vue
AgentManagement.vue
DatasetReportConfig.vue
FeishuSync.vue
EmployeePermissions.vue   # 精简版
AuthCallback.vue
NotFound.vue
```

后端保留：

```text
auth.py
smart_chat.py
bookshelf.py
datasources.py
ai_models.py
agents.py
report_config.py
feishu_sync.py
feature_flags.py
rbac.py                 # 精简版
data_permissions.py     # 可保留资源授权
```

### 4.3 删除清单

80% 功能版删除：

```text
frontend/src/views/AdminConsole.vue
frontend/src/views/RuntimeMigration.vue
frontend/src/views/SmartAsk copy.vue

backend/controllers/runtime_migration.py
backend/controllers/system_logs.py   # 如不提供审计日志
backend/runtime_migration.py
backend/import_runtime_config.py
backend/export_runtime_config.py
backend/import_bookshelf_bundle.py   # 如不提供导入导出
backend/export_bookshelf_bundle.py
```

可选删除内部脚本：

```text
backend/dataset_copilot/output/**
backend/create_consumer_standard_dataset.py
backend/fill_syyb_dataset.py
backend/regenerate_dataset_from_doc.py
backend/export_angel_group_data.py
backend/import_angel_group_data.py
backend/drop_angel_table.py
backend/check_*.py
backend/test_*.py
```

前端路由删除：

```text
/admin-console
/runtime-migration
```

侧边栏删除：

```text
系统控制台
迁移发布管理
```

后端 `app.py` 删除：

```py
from controllers.runtime_migration import runtime_migration_bp
from controllers.system_logs import system_logs_bp

app.register_blueprint(runtime_migration_bp)
app.register_blueprint(system_logs_bp)
```

如果 80% 版还想保留只读审计日志，则不要删除 `system_logs.py`，只删除清空日志、控制台入口。

### 4.4 RBAC 精简建议

当前完整版 RBAC 包含：

- 自定义角色
- 用户分组
- 功能权限
- 数据集资源权限
- 用户视角
- 资源视角
- 批量授权
- 用户启停
- 重置密码
- 审计追踪

80% 功能版建议保留：

```text
用户列表
新建用户
启用/停用用户
重置密码
角色分配
数据集资源授权
```

80% 功能版建议删除或隐藏：

```text
多级用户分组
双向权限视图
权限矩阵
高级批量授权
系统控制台跳转治理入口
权限健康度统计
高风险权限提示
```

前端处理：

在 `EmployeePermissions.vue`：

- 保留用户列表。
- 保留角色列表。
- 保留数据集授权。
- 删除或隐藏分组列表。
- 删除「用户视角 · 权限来源」复杂卡片。
- 删除「数据集/资源视角」复杂详情，或改成简单表格。

后端处理：

在 `controllers/rbac.py`：

保留：

```text
GET /api/admin/rbac/overview
POST /api/admin/rbac/users
PUT /api/admin/rbac/users/<id>
POST /api/admin/rbac/users/<id>/reset-password
POST /api/admin/rbac/users/bulk
POST /api/admin/rbac/roles
PUT /api/admin/rbac/roles/<id>
DELETE /api/admin/rbac/roles/<id>
```

可删除：

```text
GET /api/admin/rbac/users/<id>/permissions
GET /api/admin/rbac/datasets/<id>/access
POST /api/admin/rbac/groups
PUT /api/admin/rbac/groups/<id>
DELETE /api/admin/rbac/groups/<id>
```

删除后修复：

- `load_rbac()` 中若依赖 groups，保留空数组默认值：

```py
data.setdefault("groups", [])
```

- 前端不要再请求：

```js
getRbacUserPermissions
getRbacDatasetAccess
createRbacGroup
updateRbacGroup
deleteRbacGroup
```

### 4.5 飞书同步保留但降级

80% 功能版可以保留飞书同步，但建议删除高级能力：

保留：

```text
新建飞书同步配置
解析飞书链接
测试连接
启动/暂停/恢复同步
查看最近日志
```

删除或隐藏：

```text
清空所有日志
复杂 schema preview
历史字段差异对比
运行迁移包
全局同步统计面板
```

前端：

在 `FeishuSync.vue` 隐藏高阶按钮。

后端：

可保留 `feishu_sync.py` 全部接口，前端不暴露即可；如果要物理裁剪，再删除：

```text
/feishu-sync/schema-preview
/feishu-sync/logs/clear
```

并删除 `api/index.js` 对应导出：

```js
previewFeishuSchema
clearAllFeishuSyncLogs
clearFeishuSyncLogs
```

### 4.6 系统日志处理

两种选择：

方案 A：80% 功能版不交付日志。

删除：

```text
frontend/src/views/AdminConsole.vue
backend/controllers/system_logs.py
backend/system_log_store.py
```

修复：

- `auth.py`、`rbac.py`、`feishu_sync.py` 里如果 import `system_log_store`，需要保留一个轻量 shim。
- 更稳的做法是不要删除 `system_log_store.py`，只删除前端日志页面和 API。

推荐方案 B：保留后端日志工具，不开放页面。

保留：

```text
backend/system_log_store.py
```

删除：

```text
backend/controllers/system_logs.py
frontend/src/views/AdminConsole.vue
api/index.js 中 getSystemLogs* / clearSystemLogs
```

### 4.7 80% 功能版验收

1. 菜单不出现：
   - 系统控制台
   - 迁移发布管理
2. 菜单可以出现：
   - 智能分析工作台
   - 智能体编排配置
   - 数据资产管理
   - 数据连接管理
   - 模型服务配置
   - 报告模板配置
   - 飞书数据同步
   - 角色权限管理
3. 飞书同步能新增配置、测试、启动。
4. 用户能新建、停用、重置密码。
5. 能配置数据集访问权限。
6. 访问 `/admin-console` 和 `/runtime-migration` 不可用。
7. 智能问数正常。

构建：

```powershell
cd frontend
npm run build
```

后端：

```powershell
cd ..
& 'C:\Users\liutq09\AppData\Local\anaconda3\python.exe' -c "import sys; sys.path.insert(0,'backend'); import app; print('APP_IMPORT_OK')"
```

---

## 5. 通用裁剪步骤

### 5.1 推荐执行顺序

1. 先改前端路由。
2. 再改侧边栏 `navItems`。
3. 再删页面文件。
4. 再删 `api/index.js` 中不用的导出。
5. 再改 `backend/app.py` 蓝图注册。
6. 最后删后端 controller 和服务文件。
7. 跑构建和后端 import。
8. 再清理配置文件和脚本。

### 5.2 每删一个模块都要检查

用 `rg` 查引用：

```powershell
rg "AdminConsole|RuntimeMigration|EmployeePermissions|FeishuSync|AgentManagement" frontend/src backend
rg "/admin-console|/runtime-migration|/employee-permissions|/feishu-sync|/agents" frontend/src backend
rg "runtime_migration_bp|system_logs_bp|rbac_bp|feishu_bp|agents_bp" backend
```

如果 `rg` 还能搜到被删除模块的 import、路由或 API 调用，必须处理。

### 5.3 构建失败常见修复

#### 前端报 `Failed to resolve import`

原因：路由、组件或 API 还引用已删除文件。

处理：

```powershell
rg "被删除文件名或组件名" frontend/src
```

删除 import、删除路由、删除按钮入口。

#### 后端 import app 失败

原因：`backend/app.py` 还 import 已删除 controller。

处理：

检查：

```powershell
rg "from controllers" backend/app.py
```

删除对应 import 和 `app.register_blueprint(...)`。

#### 运行时报 404

原因：前端还请求了已删除 API。

处理：

打开浏览器控制台，看 404 URL，然后在前端查：

```powershell
rg "接口路径关键字" frontend/src
```

删除调用或替换为简化接口。

#### 权限判断异常

原因：删除 RBAC 后，前端或后端仍依赖 feature flag / role ids。

处理：

- 基础班：所有登录用户默认 `role=user`，管理员账号 `role=super_admin`。
- 升级版：保留固定三级角色，不读取自定义 role_ids。
- 80% 功能版：保留 role_ids，但删除 group 继承时要保证 `groups=[]`。

### 5.4 配置文件裁剪

基础班建议只保留：

```text
config/app_config.json
config/ai_settings.json
config/datasources.json
config/employee_permissions.json
```

升级版建议保留：

```text
config/app_config.json
config/ai_settings.json
config/datasources.json
config/employee_permissions.json
config/dataset_report_config.json
config/agent_registry.json
```

80% 功能版建议保留：

```text
config/app_config.json
config/ai_settings.json
config/datasources.json
config/employee_permissions.json
config/dataset_report_config.json
config/agent_registry.json
config/feishu_sync.json
config/rbac.json
config/feature_flags.json
```

删除配置文件前，先确认 `config_manager.py` 的默认构造逻辑能自动补默认值。

---

## 6. 交付建议

### 6.1 基础班交付话术

交付定位：

> 面向业务使用者的智能经营分析工作台，预置数据集和模型，由交付方统一维护配置。

不要暴露：

- 后台配置
- RBAC
- 飞书同步
- 迁移发布
- 系统控制台

### 6.2 升级版交付话术

交付定位：

> 支持客户管理员维护数据连接、数据集、模型和报告模板，适合小规模 BI 智能问数落地。

不要暴露：

- 自定义角色/分组
- 系统控制台
- 迁移发布
- 飞书同步自动化

### 6.3 80% 功能版交付话术

交付定位：

> 覆盖问数、数据资产、模型、报告、飞书同步和基础权限管理，满足大多数生产使用场景。

不要暴露：

- 系统控制台
- 迁移发布工具
- 内部诊断脚本
- 完整权限矩阵和高级审计能力

---

## 7. 最终检查清单

每个裁剪版本都必须通过：

```powershell
cd frontend
npm run build
```

```powershell
cd ..
& 'C:\Users\liutq09\AppData\Local\anaconda3\python.exe' -c "import sys; sys.path.insert(0,'backend'); import app; print('APP_IMPORT_OK')"
```

建议额外检查：

```powershell
rg "TODO|FIXME|AdminConsole|RuntimeMigration|EmployeePermissions|FeishuSync" frontend/src backend
```

基础班允许搜到 `Feishu` 仅限登录；升级版不应搜到 `RuntimeMigration/AdminConsole/RBAC` 页面引用；80% 功能版不应搜到 `RuntimeMigration` 运行入口。

