# Vanna 智能问数系统 - 任务清单

## 一、规划阶段
- [x] 读取现有 vanna01.py 代码
- [x] 读取现有 pages 参考页面（React/TSX）
- [x] 制定实施计划文档

## 二、后端构建（Flask）
### 2.1 项目结构初始化
- [ ] 创建 `backend/` 目录结构
- [ ] 创建 `backend/requirements.txt`

### 2.2 配置文件模块
- [ ] 创建 `backend/config/app_config.json`（默认模板）
- [ ] 创建 `backend/config/datasources.json`（默认模板）
- [ ] 创建 `backend/config/ai_settings.json`（默认模板）
- [ ] 创建 `backend/config_manager.py`（配置读写工具类）

### 2.3 Vanna 核心封装
- [ ] 创建 `backend/vanna_core.py`（MyVanna 类，动态读配置）

### 2.4 Flask 路由控制器
- [ ] 创建 `backend/controllers/dashboard.py`（/api/dashboard）
- [ ] 创建 `backend/controllers/datasources.py`（/api/datasources CRUD + test）
- [ ] 创建 `backend/controllers/ai_models.py`（/api/ai-models CRUD + test）
- [ ] 创建 `backend/controllers/training.py`（/api/training CRUD + vn.train）
- [ ] 创建 `backend/controllers/chat.py`（/api/chat 问答接口）

### 2.5 Flask 主入口
- [ ] 创建 `backend/app.py`（注册蓝图、CORS、启动）

## 三、前端构建（Vue3 + Element Plus）
### 3.1 初始化 Vue 项目
- [ ] 在 `frontend/` 目录用 pnpm 初始化 Vite + Vue3 项目
- [ ] 安装 Element Plus、axios、vue-router、echarts

### 3.2 公共配置
- [ ] 创建 `frontend/src/api/index.js`（axios 封装，baseURL）
- [ ] 创建 `frontend/src/router/index.js`（6个路由配置）
- [ ] 创建 `frontend/src/App.vue`（主布局：侧边栏+内容区）

### 3.3 6个页面组件
- [ ] `frontend/src/views/Dashboard.vue`（仪表盘，真实API数据）
- [ ] `frontend/src/views/Databases.vue`（数据源管理，CRUD）
- [ ] `frontend/src/views/AIModels.vue`（AI模型配置）
- [ ] `frontend/src/views/Training.vue`（训练数据管理）
- [ ] `frontend/src/views/Chat.vue`（智能聊天核心页面）
- [ ] `frontend/src/views/NotFound.vue`（404页面）

## 四、验证
- [ ] 启动后端，验证所有API接口返回正常
- [ ] 启动前端，验证6个页面UI正常
- [ ] 验证前后端完整联通（CRUD + 测试连接 + 问答）
- [ ] 创建 `README_WINDOWS.md` 启动文档

## 五、交付
- [ ] 创建 walkthrough.md 记录验证结果
