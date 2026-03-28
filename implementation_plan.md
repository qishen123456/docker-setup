# Vanna 智能问数系统 — 完整实施计划

## 背景

您现有 [vanna01.py](file:///d:/1.%E6%99%BA%E8%83%BD%E9%97%AE%E6%95%B0%E9%A1%B9%E7%9B%AE/anti02/vanna01.py) 包含：
- [DeepSeekChat](file:///d:/1.%E6%99%BA%E8%83%BD%E9%97%AE%E6%95%B0%E9%A1%B9%E7%9B%AE/anti02/vanna01.py#3-38) 类（基于 OpenAI 兼容 API，当前接通阿里通义千问）
- [MyVanna](file:///d:/1.%E6%99%BA%E8%83%BD%E9%97%AE%E6%95%B0%E9%A1%B9%E7%9B%AE/anti02/vanna01.py#40-44) 类（继承 ChromaDB_VectorStore + DeepSeekChat）
- 完整的 Vanna Flask App 认证逻辑

现有参考前端（React/TSX）有 Dashboard、SQLServer/MySQL 数据源配置、AI 模型配置、训练数据等页面设计，**将移植并重构为 Vue3 + Element Plus**。

目标：**从零构建**一个全新的、可在 Windows 本地直接运行的前后端分离系统。

---

## 项目目录结构

```
d:\1.智能问数项目\anti02\
├── backend/
│   ├── app.py                  # Flask 入口，注册所有蓝图，启用 CORS
│   ├── vanna_core.py           # MyVanna 类封装，动态读取配置
│   ├── config_manager.py       # JSON 配置文件读写工具
│   ├── requirements.txt
│   └── controllers/
│       ├── __init__.py
│       ├── dashboard.py        # GET /api/dashboard
│       ├── datasources.py      # CRUD /api/datasources + /test
│       ├── ai_models.py        # CRUD /api/ai-models + /test
│       ├── training.py         # CRUD /api/training + vn.train()
│       └── chat.py             # POST /api/chat
├── frontend/
│   ├── index.html
│   ├── vite.config.js          # 代理 /api -> localhost:5000
│   ├── package.json
│   └── src/
│       ├── main.js
│       ├── App.vue             # 主布局：侧边栏 + <router-view>
│       ├── api/
│       │   └── index.js        # axios 封装，统一 baseURL
│       ├── router/
│       │   └── index.js        # 6 个路由
│       └── views/
│           ├── Dashboard.vue
│           ├── Databases.vue
│           ├── AIModels.vue
│           ├── Training.vue
│           ├── Chat.vue
│           └── NotFound.vue
├── config/                     # 持久化配置目录（后端自动创建）
│   ├── app_config.json
│   ├── datasources.json
│   └── ai_settings.json
└── README_WINDOWS.md
```

---

## 配置文件设计

### `config/datasources.json`
```json
{
  "databases": [
    {
      "id": 1,
      "name": "CRM 生产库",
      "type": "sqlserver",
      "host": "your-server",
      "port": 1433,
      "database_name": "CRM01_MSCRM",
      "username": "dc",
      "password_b64": "base64加密密码",
      "driver": "ODBC Driver 17 for SQL Server",
      "is_active": true,
      "is_default": true,
      "created_at": "..."
    }
  ]
}
```

### `config/ai_settings.json`
```json
{
  "models": [
    {
      "id": 1,
      "name": "通义千问 qwen-max",
      "provider": "dashscope",
      "model": "qwen-max",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key": "sk-xxx",
      "is_active": true,
      "is_default": true
    }
  ]
}
```

---

## 后端 API 设计

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /api/dashboard | 统计数据 + 最近5条问答 |
| GET | /api/datasources | 获取所有数据源 |
| POST | /api/datasources | 新增数据源 |
| PUT | /api/datasources/{id} | 更新数据源 |
| DELETE | /api/datasources/{id} | 删除数据源 |
| POST | /api/datasources/{id}/test | 测试连接 |
| GET | /api/ai-models | 获取所有 AI 模型 |
| POST | /api/ai-models | 新增模型 |
| PUT | /api/ai-models/{id} | 更新模型 |
| DELETE | /api/ai-models/{id} | 删除模型 |
| POST | /api/ai-models/{id}/test | 测试模型连通性 |
| GET | /api/training | 获取训练数据列表 |
| POST | /api/training | 添加训练数据（DDL/文档/问答对）|
| DELETE | /api/training/{id} | 删除训练数据 |
| POST | /api/training/train | 触发 vn.train() |
| POST | /api/chat | 自然语言问答，返回 SQL+结果 |

---

## 前端页面设计

| 页面 | 路由 | Element Plus 组件 |
|------|------|-------------------|
| Dashboard | / | el-statistic, el-table, el-card |
| 数据源管理 | /databases | el-table, el-dialog, el-form |
| AI模型配置 | /ai-models | el-table, el-dialog, el-tabs |
| 训练数据 | /training | el-tabs, el-upload, el-table |
| 智能聊天 | /chat | 自定义消息气泡, el-input |
| 404 | /404 | el-result |

---

## 技术决策说明

1. **密码混淆**：密码使用 Base64 存储（非真正加密，但比明文安全），前端传输依赖 HTTPS 或本地环境
2. **Vanna 实例热重载**：配置修改后，下次 `/api/chat` 请求会自动用新配置重新初始化 Vanna 实例（通过全局标志位控制）
3. **ChromaDB**：持久化存储在 `backend/chroma_db/` 目录，无需额外数据库服务
4. **前端代理**：Vite dev server 配置 `/api` 代理到 `localhost:5000`，避免跨域问题
5. **pnpm**：前端使用 pnpm + 淘宝镜像

---

## 验证计划

### 后端 API 验证（手动）
依次在 PowerShell 中执行：
```powershell
cd d:\1.智能问数项目\anti02\backend
python app.py
# 另开终端：
curl http://localhost:5000/api/dashboard
curl http://localhost:5000/api/datasources
curl http://localhost:5000/api/ai-models
```

### 前端验证（浏览器）
```powershell
cd d:\1.智能问数项目\anti02\frontend
pnpm run dev
# 打开浏览器访问：http://localhost:5173
```
逐一点击侧边栏菜单，确认6个页面正常加载。

### 联调验证
1. 在"数据源管理"页面点击"添加"，填写测试信息后保存 → 确认列表显示
2. 在"AI模型配置"页面添加您的真实 API Key → 点击"测试" → 确认弹出成功提示
3. 在"智能聊天"页面输入"查询5条数据" → 确认返回 SQL 和结果表格


