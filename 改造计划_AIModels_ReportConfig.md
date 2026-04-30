# 改造计划：AIModels CherryStudio 双栏布局 + 报告配置修复

> 日期：2026-04-30
> 状态：执行中

---

## 问题清单

| # | 问题 | 根因 | 严重度 |
|---|------|------|--------|
| 1 | AIModels 模型无法全部展示（只展开一个通道） | `expandedChannel` 只允许一个展开，且默认只展开第一个 | 高 |
| 2 | AIModels 删除按钮不生效 | `el-popconfirm` 嵌套可能有渲染问题 | 高 |
| 3 | AIModels 布局与 CherryStudio 完全不同 | 当前是单列卡片列表，CherryStudio 是左列表+右详情双栏 | 高 |
| 4 | 报告配置页面数据集选择为空 | 前端调用 `/api/bookshelf/datasets`，后端路由是 `/api/bookshelves/datasets`（少了 s） | 高 |
| 5 | 报告配置页面UI粗糙 | 需要优化布局和交互 | 中 |
| 6 | 数据库表 `bs_dataset_report_config` 未创建 | 迁移 SQL 未执行 | 高 |
| 7 | 默认 syyb 报告配置未填入 | 依赖表创建后执行 INSERT | 高 |

---

## 执行计划

### Step 1: AIModels.vue — CherryStudio 双栏布局重写
- **左栏**（240px）：供应商/通道列表，每项显示 icon + 名称 + 在线状态
- **右栏**（flex）：选中通道的详情面板
  - 顶部：供应商图标 + 名称
  - API 密钥输入行（带"检测"按钮）
  - API 地址输入行
  - 模型列表（全部展开，每行显示模型名 + ID + 操作按钮）
- **底部**：左栏底部固定 "+ 添加" 按钮
- 所有模型默认全部可见（无折叠）
- 删除使用 `el-popconfirm` 正确嵌套

### Step 2: 修复报告配置页面
- 前端路由从 `/api/bookshelf/datasets` 改为 `/api/bookshelves/datasets`
- 优化 DatasetReportConfig.vue UI
- 数据集选择改为带图标和描述

### Step 3: 数据库迁移 + 填充默认数据
- 执行 CREATE TABLE
- 查询 syyb 数据集 ID
- INSERT 默认配置

### Step 4: 验证
- 前端构建通过
- 后端启动正常
- AIModels 页面功能正常（增删改测）
- 报告配置页面数据集加载正常

### Step 5: Git + Docker 推送
