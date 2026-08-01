---
kind: build_system
name: SmartAsk 智能问数系统构建与部署体系
category: build_system
scope:
    - '**'
source_files:
    - docker-compose.yml
    - backend/Dockerfile
    - frontend/Dockerfile
    - deploy.sh
    - update.sh
    - backup.sh
    - doctor.sh
    - backend/requirements.txt
    - frontend/package.json
    - DEPLOY.md
---

## 1. 构建系统与工具链

项目采用 **Docker Compose** 作为核心编排工具，统一构建、启动和运行 PostgreSQL、Flask 后端与 Vue 前端三个服务。构建流程通过 `deploy.sh`（Linux/macOS）和 `deploy.ps1`（Windows）两个入口脚本统一封装，实现一键部署。

- **后端构建**: 基于 `python:3.11-slim` 镜像，使用 `requirements.txt` 管理 Python 依赖，支持阿里云镜像加速
- **前端构建**: 基于 `node:20-alpine` + `pnpm@9.15.9`，通过 Vite 构建静态资源后由 Nginx 托管
- **数据库初始化**: PostgreSQL 容器首次启动时自动执行 `docker/postgres/init/*.sql` 中的 SQL 文件

## 2. 核心构建文件与配置

### Docker 镜像定义
- `backend/Dockerfile`: 后端镜像构建，包含 APT 源配置、Python 依赖安装、应用代码复制
- `frontend/Dockerfile`: 前端多阶段构建，分离 pnpm 依赖安装和构建阶段，最终使用 nginx:1.27-alpine
- `docker-compose.yml`: 三服务编排，定义端口映射、环境变量、数据卷挂载和健康检查

### 部署与运维脚本
- `deploy.sh`: Linux 一键部署，包含环境检查、镜像源配置、容器构建、健康验证
- `update.sh`: 增量更新脚本，支持 Git 分支切换、备份恢复、集成测试
- `backup.sh`: 完整备份脚本，导出 config、日志、数据库 dump 和 Git 状态
- `doctor.sh`: 诊断包生成器，收集系统信息、容器状态、服务日志并脱敏敏感信息

### 依赖管理
- `backend/requirements.txt`: Python 依赖声明，固定 Flask 3.0.3、vanna 0.7.9 等关键版本
- `frontend/package.json`: Node.js 依赖，使用 Vue 3.5.30、Element Plus 2.13.6、Vite 8.0.1

## 3. 构建架构与设计决策

### 容器化策略
- **服务解耦**: 每个组件独立容器，通过 Docker 网络通信
- **数据持久化**: 使用 Docker volumes 存储 PostgreSQL 数据和 ChromaDB 向量数据
- **健康检查**: 每个服务定义 healthcheck，确保依赖关系正确启动
- **环境变量驱动**: 所有配置通过 `.env` 文件和 Docker 环境变量注入

### 构建优化
- **多阶段构建**: 前端使用 node 构建，nginx 运行，减小最终镜像体积
- **缓存优化**: pnpm 依赖安装与代码构建分离，利用 Docker 层缓存
- **镜像源加速**: 支持阿里云 APT、PyPI、NPM 镜像配置，提升构建速度

### 部署流程设计
- **幂等性保证**: 数据库迁移和配置导入均支持幂等执行
- **安全校验**: 部署前检查 `.env` 中是否仍为占位符或弱密码
- **加密支持**: 支持 `enc:v1:` 格式的运行时密钥加密，通过主密钥文件解密
- **回滚机制**: 更新前自动备份，支持 git stash 暂存本地修改

## 4. 构建约定与约束

### 环境变量规范
- 所有外部配置通过 `SMARTASK_*` 前缀的环境变量管理
- 敏感信息支持 `enc:v1:` 加密格式，需配合主密钥文件使用
- 端口配置通过 `SMARTASK_FRONTEND_PORT`、`SMARTASK_BACKEND_PORT`、`SMARTASK_DOCKER_PG_PORT` 自定义

### 构建参数约定
- 镜像源通过 `SMARTASK_APT_MIRROR`、`SMARTASK_PIP_INDEX_URL`、`SMARTASK_NPM_REGISTRY` 配置
- 网络超时通过 `SMARTASK_PIP_TIMEOUT`、`SMARTASK_PIP_RETRIES` 控制
- 构建选项通过命令行参数控制，如 `--no-build`、`--run-tests`、`--skip-verify`

### 数据目录结构
- `config/`: 运行时配置文件，包括数据源、AI模型、权限策略等
- `backups/`: 备份文件输出目录
- `logs/`: 应用日志输出
- `docker/postgres/init/`: 数据库初始化 SQL 脚本

### 安全约束
- 禁止在 `.env` 中使用模板占位值或弱密码
- 生产环境必须提供 `config/.secret_master_key` 用于解密敏感配置
- 诊断脚本自动对 Key、Secret、Password 等敏感字段进行脱敏处理
- PostgreSQL 密码明文要求，容器无法解密 enc:v1 格式的密码

### 版本管理策略
- 默认使用 `docker-setup` 分支作为稳定发布分支
- 支持通过 `--remote` 参数指定 Git 远端名称
- 更新脚本强制 `git pull --ff-only` 确保线性历史
- 内置数据集模板通过 `create_consumer_standard_dataset.py` 同步更新