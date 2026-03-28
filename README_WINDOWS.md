# Vanna 智能问数系统 - Windows 启动手册

本系统基于 **Vanna AI** 构建，采用 **Flask + Vue 3 + Element Plus** 的全栈架构，配置文件（JSON）本地化存储，不依赖额外数据库，支持 **SQLite / MySQL / SQL Server** 动态配置。

---

## 🚀 快速启动方案（推荐）

项目根目录下已准备好一键启动脚本：

1.  **启动后端 API**：双击运行 `start_backend.bat`
2.  **启动前端界面**：双击运行 `start_frontend.bat`

打开浏览器访问：`http://localhost:5173`

---

## 🛠️ 环境准备

如果您选择手动启动，请确保已安装以下环境：

- **Python 3.9+** (推荐 3.10+)
- **Node.js 16.0+**
- **pnpm** (已为您通过 npm 全局安装)

---

## 📂 详细启动步骤

### 1. 后端 (backend)
后端使用 Flask 提供 RESTful API，并将 Vanna 的训练数据持久化在 `backend/chroma_db` 中。

```powershell
# 1.1 进入后端目录
cd backend

# 1.2 安装依赖（已为您预装，如失效可运行此命令）
py -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 1.3 启动 Flask
py app.py
```
*后端运行在 `http://localhost:5000`*

### 2. 前端 (frontend)
前端使用 Vue 3 + Vite 构建，通过代理（Proxy）连接后端。

```powershell
# 2.1 进入前端目录
cd frontend

# 2.2 安装依赖（已为您预装）
pnpm install

# 2.3 启动开发服务器
pnpm run dev
```
*前端运行在 `http://localhost:5173`*

---

## 📝 系统初始化指引

首次启动后，请按照以下顺序配置：

1.  **AI模型配置**：
    - 进入【AI模型配置】页面。
    - 添加您的 LLM Key（如阿里通义、DeepSeek 等）。
    - 建议先点【测试】按钮确认连通性。
2.  **数据源管理**：
    - 添加您的数据库连接。
    - 如果没有外部库，可以使用默认创建的 **SQLite** (./test.db) 进行点火测试。
3.  **训练数据**：
    - 至少添加一段 `DDL 建表语句` 或 `问答 SQL 对`。
    - *没有训练数据，AI 无法生成正确的 SQL。*
4.  **智能聊天**：
    - 提问自然语言（如：查一下前5条数据），系统会自动生成 SQL 并执行结果。

---

## 📁 配置文件说明
所有配置存储在 `config/` 目录下（后端启动后自动生成）：
- `datasources.json`: 数据库连接（密码已 Base64 混淆）
- `ai_settings.json`: AI 模型地址及 Key
- `app_config.json`: 系统运行参数
- `query_history.json`: 问答历史记录

---

💡 **遇到连接问题？** 
请检查后端控制台输出，或确保本地 5000/5173 端口未被占用。
