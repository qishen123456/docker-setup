# 智能问数项目换电脑与 Docker 化迁移计划

更新时间：2026-04-28

适用项目：当前仓库“智能问数项目”

---

## 1. 先说结论

如果你的目标是：

- 换一台电脑继续开发
- 不想每次都重新装 Python、Node、依赖
- 不想再手动装本地 PostgreSQL
- 希望项目能更稳定地启动和迁移

那么这件事是完全可行的，而且我建议尽快做。

但我不建议你第一步就追求“100% 全部容器化、所有数据库都塞进 Docker”。

对你这个项目，最稳的路线是：

1. 把前端、后端、Bookshelf 元数据 PostgreSQL 先容器化
2. 把配置、日志、Chroma 向量库做卷挂载
3. 把业务数据库连接保留为“可外部接入”
4. 等这一版稳定后，再决定是否把业务测试库也容器化

一句话判断：

- 可行，而且值得做
- 推荐做“半容器化到全容器化”的渐进迁移
- 不建议一开始就把所有内容一起重构

---

## 2. 结合你当前项目，为什么值得做

从当前项目看，你现在的运行方式还有几个明显痛点：

### 2.1 启动方式还是本机脚本型

当前根目录存在：

- `start_all.bat`
- `start_backend.bat`
- `start_frontend.bat`

这说明当前还是：

- 本机 Python 环境
- 本机 Node 环境
- 本机端口占用治理
- 本机依赖版本一致性靠手工维护

问题：

- 换电脑时重复配置成本高
- 很难保证多台电脑环境一致
- 很难快速恢复开发现场

### 2.2 Bookshelf 元数据依赖 PostgreSQL

当前 `backend/bookshelf_repository.py` 里可以看出：

- `BookshelfRepository` 会自动挑选“活动中的 PostgreSQL 数据源”
- `bs_*` 元数据表必须存在
- 如果没有可用 PostgreSQL，主链路会直接受影响

也就是说：

- 虽然项目某些部分支持 SQLite / MySQL / SQL Server
- 但你现在的智能问数主链路，实际上已经对 PostgreSQL 有强依赖

所以你不想再手工装本地 PG，这个诉求是合理的。

### 2.3 项目有明显“状态数据”

当前项目里至少有这些运行状态：

- `config/*.json`
- `logs/`
- `backend/logs/`
- `chroma_db/`
- `backend/chroma_db_source_*`
- PostgreSQL `bs_*` 元数据表

这意味着项目不是纯前端静态项目，也不是纯无状态 API。

所以 Docker 化时，核心不是“能跑起来”，而是：

- 数据要持久
- 配置要持久
- 卷挂载要设计好

---

## 3. 推荐的迁移目标形态

我建议你的目标架构是：

### 3.1 推荐架构

用 `docker compose` 管理下面这些服务：

1. `frontend`
   - Vue + Vite
   - 开发态容器

2. `backend`
   - Flask + Python
   - 智能问数主服务

3. `postgres`
   - 只负责 Bookshelf 元数据
   - 保存 `bs_*` 表

4. `optional-adminer` 或 `pgadmin`
   - 仅开发时使用
   - 便于直接看 PostgreSQL 数据

### 3.2 建议先不要容器化的部分

第一阶段不建议强行容器化：

- 飞书同步的所有外部联调依赖
- SQL Server ODBC 场景
- 你真实业务生产数据库

原因：

- 这些部分通常更依赖外部网络环境
- Docker 化成本和调试成本更高
- 并不是换电脑的第一痛点

### 3.3 你的最佳目标不是“全本地”

更合理的是：

- 项目本身容器化
- 元数据 PG 容器化
- 业务数据源通过配置接外部数据库

这样你就不需要在新电脑本地装 PostgreSQL，也不需要反复装依赖。

---

## 4. 三种可选方案

## 方案 A：仅换电脑，不做 Docker

做法：

- 新电脑安装 Python、Node、pnpm
- 安装本地 PostgreSQL
- 复制代码和配置文件
- 重新跑依赖安装和服务启动

优点：

- 改造最少

缺点：

- 你最痛的地方几乎没解决
- 后续还会继续反复配环境

结论：

不推荐。

## 方案 B：推荐方案，项目容器化 + 元数据 PG 容器化

做法：

- `frontend` 容器
- `backend` 容器
- `postgres` 容器
- `config/logs/chroma_db` 卷挂载
- 业务数据库通过配置连接外部地址

优点：

- 最大程度解决换电脑问题
- 不需要再本机安装 PostgreSQL
- 改造成本可控
- 适合你当前项目阶段

缺点：

- 第一次要补 Dockerfile、compose、环境变量治理

结论：

这是我最推荐的方案。

## 方案 C：全栈完全容器化

做法：

- 前后端容器
- 元数据 PG 容器
- 所有测试数据库容器
- 所有脚本也切容器运行

优点：

- 环境最统一

缺点：

- 初期成本最高
- 你现在项目还在快速改动期，容易把迁移工作做过重

结论：

第二阶段再考虑，不建议第一步就上。

---

## 5. 推荐目标目录与容器设计

建议新增目录：

- `docker/`
  - `backend/`
  - `frontend/`
  - `postgres/`
- `docker-compose.yml`
- `.env.example`
- `.dockerignore`

建议新增文件：

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `docs/Docker启动说明.md`

---

## 6. 需要持久化的内容

这部分非常关键，不能漏。

## 6.1 必须挂载卷的目录

建议持久化：

- `./config`
- `./logs`
- `./backend/logs`
- `./chroma_db`
- `./backend/chroma_db_source_*`

如果你后面统一 Chroma 目录，也可以收敛成一个主目录。

## 6.2 PostgreSQL 必须持久化

容器里的 PostgreSQL 数据目录必须挂卷，例如：

- `pgdata:/var/lib/postgresql/data`

否则：

- 一删容器，Bookshelf 元数据就没了

## 6.3 不建议直接写进镜像的内容

下面这些不要 bake 进镜像：

- `config/*.json`
- API Key
- 数据源密码
- 日志文件
- Chroma 训练数据

这些都应该：

- 走挂载卷
- 或走 `.env`

---

## 7. 环境变量治理建议

你当前项目很多配置还在 JSON 里，本身没问题，但 Docker 化以后建议做“分层治理”。

推荐分层：

### 7.1 `.env`

用于容器运行基础参数，例如：

- `BACKEND_PORT`
- `FRONTEND_PORT`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

### 7.2 `config/*.json`

继续存：

- 数据源
- AI 模型
- 飞书同步配置
- SQL prompt 配置

### 7.3 长期建议

后面逐步把下面这些改成可环境变量覆盖：

- 默认 PostgreSQL 连接
- 默认日志目录
- 默认 Chroma 路径
- 默认模型 base_url

---

## 8. Docker 化对当前项目的真实难点

这部分我直接替你提前踩坑判断。

## 8.1 难点一：PostgreSQL 既是元数据库，又可能是业务数据库

当前 `BookshelfRepository` 会从“活动中的 PostgreSQL 数据源”里选元数据库。

风险：

- 如果你把业务 PostgreSQL 和元数据 PostgreSQL 混成一个，会增加迁移复杂度

建议：

- 明确分开：
  - 一个 `metadata postgres` 专门放 `bs_*`
  - 业务数据源按项目需要外接

## 8.2 难点二：Chroma / Vanna 数据目录

当前项目明显依赖：

- `chroma_db`
- `backend/chroma_db_source_*`

风险：

- 不挂卷会导致训练数据或向量索引丢失

建议：

- Docker 化第一天就把这部分持久化

## 8.3 难点三：Windows 与路径编码问题

你当前路径里有中文目录，之前也出现过 PowerShell / Python stdin 编码问题。

风险：

- 新电脑上若继续混用本机脚本和容器脚本，编码问题更难排

建议：

- Docker 化后尽量通过容器命令运行后端与前端
- 减少依赖本机 BAT 和长中文路径脚本

## 8.4 难点四：飞书同步与外部接口

飞书同步、外部模型接口、外部数据库都需要网络联通。

风险：

- 容器里可能出现代理、DNS、网络策略问题

建议：

- 第一阶段先验证核心问数链路
- 飞书同步单独验

---

## 9. 推荐迁移步骤

## 第 0 步：先做迁移前盘点

目标：

- 确认哪些数据必须保
- 确认哪些配置必须迁

清单：

- `config/`
- `logs/`
- `chroma_db/`
- `backend/chroma_db_source_*`
- PostgreSQL `bs_*` 表
- 当前活跃数据源配置
- 当前 AI 模型配置

交付：

- 一份迁移资产清单

## 第 1 步：先把 PostgreSQL 职责拆清楚

目标：

- 不再让“哪个 PostgreSQL 是元数据库”含糊不清

建议：

- 新增一个专门的 metadata 数据源配置
- `BookshelfRepository` 后续优先读一个明确的 metadata datasource 标记

这一步非常重要，因为它决定 Docker 后的 PG 是否稳定。

## 第 2 步：补 Dockerfile 与 Compose

目标：

- 让新电脑只需要 Docker Desktop 就能起项目

需要产出：

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.env.example`

推荐 Compose 服务：

- `frontend`
- `backend`
- `postgres`
- `pgadmin` 可选

## 第 3 步：把配置和状态目录挂载出来

目标：

- 防止删除容器即丢数据

挂载建议：

- `./config:/app/config`
- `./logs:/app/logs`
- `./backend/logs:/app/backend/logs`
- `./chroma_db:/app/chroma_db`
- `./backend/chroma_db_source_*:/app/backend/chroma_db_source_*`

## 第 4 步：先在当前电脑本地跑通 Docker

目标：

- 不要直接在新电脑首发

先在当前机器验证：

- `docker compose up`
- 后端健康检查
- 前端打开
- PostgreSQL 可连接
- 问数主链路可跑
- 老板确认可跑

## 第 5 步：导出 PostgreSQL 元数据

目标：

- 把现有 `bs_*` 元数据迁入 Docker PG

建议方式：

- `pg_dump`
- 或者导出指定 schema/table

优先导：

- `bs_datasets`
- `bs_dataset_synonyms`
- `bs_lld_documents`
- `bs_data_dictionary_items`
- `bs_schema_definitions`
- `bs_table_relations`
- `bs_golden_sql_samples`
- `bs_agent_prompt_fragments`

## 第 6 步：迁移到新电脑

新电脑需要安装的内容建议只保留：

- Git
- Docker Desktop
- 浏览器

理想状态下，不再需要手装：

- 本地 PostgreSQL
- 本地 Python 运行环境
- 本地 Node 运行环境

## 第 7 步：新电脑验证

新电脑上重点验证：

1. `docker compose up` 是否一次启动成功
2. 前端页面是否能打开
3. 后端 `/api/health` 是否正常
4. Bookshelf 数据集是否可见
5. 问数是否能生成结果
6. 老板确认是否能继续链路
7. Chroma / 历史数据是否保留

---

## 10. 推荐的实施顺序

## 第一阶段：最低成本可迁移

目标：

- 先解决“换电脑重复配环境”

做法：

- Docker 化前端
- Docker 化后端
- Docker 化 metadata PostgreSQL
- 配置目录挂载

这一步完成后，你已经基本摆脱本地 Python / Node / PG 安装依赖。

## 第二阶段：稳定化

目标：

- 解决元数据库职责不清、卷散落、配置管理分散

做法：

- 明确 metadata datasource
- 整理卷路径
- 整理 `.env` 与 `config` 边界

## 第三阶段：完全工程化

目标：

- 让项目更适合团队交接与长期维护

做法：

- 补迁移脚本
- 补数据库备份恢复脚本
- 补 Docker 启动文档
- 补 CI 基础检查

---

## 11. 我给你的专业建议

如果我是你这个项目的负责人，我会明确建议：

### 立即值得做

1. 把项目做成 `docker compose` 一键启动
2. 把 Bookshelf 元数据 PostgreSQL 容器化
3. 把配置、日志、Chroma 全部卷持久化

### 暂时不要做

1. 一开始就把所有业务数据库都塞进容器
2. 一开始就追求生产级 Kubernetes
3. 一开始就把飞书同步、模型代理、业务数据接入全部一锅端

### 最合理的目标

你应该把这个项目做成：

“换一台电脑后，只需要 `git clone + docker compose up` 就能把开发环境恢复出来。”

这才是这次迁移的真正成功标准。

---

## 12. 具体行动清单

你接下来可以按这个顺序推进：

1. 先决定采用“推荐方案 B”
2. 梳理当前 metadata PostgreSQL 的真实连接信息
3. 设计 metadata PG 容器与卷
4. 给前后端补 Dockerfile
5. 写 `docker-compose.yml`
6. 在当前电脑先跑通
7. 导出旧 `bs_*` 数据
8. 在新电脑恢复并验证

---

## 13. 最终判断

可行，而且非常值得做。

如果你继续保持现在这种方式：

- 本地 Python
- 本地 Node
- 本地 PostgreSQL
- BAT 启动脚本

那你每换一次电脑、每交给别人一次、每重装一次环境，都会重复掉进同一个坑。

如果你按这份计划做完：

- 迁移成本会大幅下降
- 环境一致性会显著提升
- 以后继续做 LangChain / MCP / 组织问数增强也会轻松很多

