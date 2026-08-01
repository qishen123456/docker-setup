---
kind: dependency_management
name: 依赖管理 — Python/Node 双栈与 Docker 镜像构建
category: dependency_management
scope:
    - '**'
source_files:
    - backend/requirements.txt
    - frontend/package.json
    - frontend/pnpm-lock.yaml
    - backend/Dockerfile
    - frontend/Dockerfile
    - docker-compose.yml
---

## 1. 使用的系统与工具
- **后端（Python）**：使用 `pip` + `requirements.txt` 声明依赖，通过 Dockerfile 中的 `PIP_INDEX_URL`、`PIP_TRUSTED_HOST`、`PIP_TIMEOUT`、`PIP_RETRIES` 等构建参数指向阿里云 PyPI 镜像，实现国内加速与超时重试。
- **前端（Node.js）**：使用 `pnpm`（Corepack 管理 pnpm@9.15.9）+ `package.json` + `pnpm-lock.yaml` 锁定版本，Dockerfile 中通过 `NPM_REGISTRY` 环境变量切换为 npmmirror，并启用 `--prefer-offline` 提升构建速度。
- **容器编排**：`docker-compose.yml` 统一编排 PostgreSQL、Flask 后端与 Nginx 静态前端三服务，并通过 `depends_on` + healthcheck 保证启动顺序。

## 2. 关键文件与位置
- `backend/requirements.txt`：Python 依赖清单，包含 Flask、vanna[chromadb]、openai、pandas、plotly、飞书同步库、数据库驱动（MySQL/PostgreSQL）、pytest 等。
- `frontend/package.json`：前端依赖与脚本定义（Vue3、Element Plus、ECharts、Vite 等）。
- `frontend/pnpm-lock.yaml`：pnpm 锁文件，记录精确解析后的包树与 integrity 校验值。
- `backend/Dockerfile`：基于 `python:3.11-slim`，安装系统依赖后通过 pip 安装 requirements，暴露 5002 端口，默认执行 `bootstrap.py`。
- `frontend/Dockerfile`：多阶段构建，Node 20 Alpine 编译产物后由 nginx:alpine 托管静态资源。
- `docker-compose.yml`：定义 postgres/backend/frontend 三个 service，挂载数据卷、配置健康检查与环境变量。

## 3. 架构与约定
- **分层依赖声明**：后端以单文件 `requirements.txt` 集中声明；前端以 `dependencies` / `devDependencies` 分离运行期与开发期依赖。
- **镜像内依赖安装**：所有第三方包均在 Docker 构建阶段安装，不依赖宿主机环境，确保可重复构建。
- **镜像源可配置**：通过构建参数/环境变量在 CI/本地均可切换镜像源（阿里云 PyPI、npmmirror），便于跨国或内网部署。
- **运行时配置与代码分离**：应用配置（datasources、auth_tokens、feature_flags 等）放在 `config/` 目录并通过 volume 挂载到容器 `/app/config`，避免将敏感配置打入镜像。
- **数据库初始化顺序**：`docker/postgres/init/*.sql` 按字母序自动执行，仅首次空数据卷时生效，配合迁移脚本 `backend/migrations/` 实现增量升级。

## 4. 约定与约束
- **Python 依赖必须通过 requirements.txt 管理**，不得在代码中动态 `pip install`；镜像构建时使用 `--timeout` 与 `--retries` 参数保障网络不稳定时的可靠性。
- **前端依赖必须通过 pnpm 安装并保留 pnpm-lock.yaml**，禁止直接修改 `node_modules`；构建命令使用 `--no-frozen-lockfile --prefer-offline` 允许锁文件更新但优先使用缓存。
- **数据库驱动按需安装**：`pyodbc`（SQL Server）被注释掉，说明仅在需要时手动开启，避免不必要的依赖膨胀。
- **环境变量命名规范**：所有可外部注入的配置均使用 `SMARTASK_*` 前缀（如 `SMARTASK_DB_HOST`、`SMARTASK_BACKEND_PORT`、`SMARTASK_NPM_REGISTRY`），并在 docker-compose 中提供默认值。
- **健康检查作为依赖关系前提**：backend 依赖 postgres 健康就绪后才启动，frontend 依赖 backend 健康就绪，形成严格的启动顺序链。
- **日志与数据持久化**：`logs/`、`backups/`、`config/` 通过 bind mount 映射到宿主机，确保容器重建不丢失运行时状态。
