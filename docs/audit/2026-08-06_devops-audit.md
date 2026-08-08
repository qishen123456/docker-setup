# SmartAsk 部署运维与可观测性审计报告

- 审计域：运行时形态、容器与编排、可观测性、配置与密钥安全、备份恢复、发布回滚、多端脚本一致性
- 审计人：卜宕机（运维工程师）
- 审计日期：2026-08-06
- 代码基线：分支 `docker-setup`，HEAD `8858bef`（`0805 待确认交互优化`，2026-08-06 16:07:29 +0800）
- 结论：**fail**

## 0. 取证方法与边界

### 0.1 允许的操作

本次为只读审计。实际执行的操作类型仅限：

- 文件读取（Read / Grep / `ls` / `wc` / `sed -n` / `git show`）
- Docker 只读查询（`docker ps -a`、`docker images`、`docker inspect`、`docker volume ls`、`docker info`）
- Git 只读查询（`git log`、`git ls-files`、`git ls-tree`、`git rev-list`、`git branch -a`、`git remote -v`）
- 一次匿名 HTTP HEAD 探测（`curl -o /dev/null -w '%{http_code}'`，仅取状态码）

全程未执行 `docker build` / `up` / `down` / `restart` / `exec`（容器均处于 Exited 状态，无法 exec）、未修改任何被审计文件。唯一写入路径是本文件所在的 `docs/audit/`。

### 0.2 无法取证的项（如实标注）

| 项 | 原因 | 影响 |
|----|------|------|
| `SHOW max_connections` 实测值 | 三容器均 Exited，启动容器属写操作 | 第 4 节以镜像默认值 + 配置覆盖面推导，标注为推断 |
| `SELECT rolsuper FROM pg_roles` 实测值 | 同上 | 第 1 节以 PostgreSQL initdb 语义 + 配置证据推导 |
| `crontab -l` | 沙箱拒绝（`operation not permitted: crontab`） | 无法证实/证伪定时备份任务存在；但产物为零（第 6 节） |
| PG 数据卷内 `postgresql.conf` | `/var/lib/docker/volumes/smartask_pg_data/_data` 在宿主不可见（Docker Desktop VM 内），`docker info` 显示 `DockerRootDir=/var/lib/docker` 属 VM 命名空间 | 同 max_connections |
| 硬编码密钥的具体值 | 门禁要求密钥零外泄 | 全文只报位置、类型、长度，不报值 |

### 0.3 报告规范自检

- 全文无 emoji。涉及源码中 emoji 的条目一律以 Unicode 码位表述（例如 U+26A0、U+FE0F），不粘贴字符本身。
- 未实际运行验证的结论，均在句内显式标注「（推断，未实证）」。
- 手机号形态标识一律脱敏为 `185****4568`。

---

## 1. Q1 — 生产连库账号与权限（B9 定级）

### 1.1 结论先行

**生产连库使用的是 PostgreSQL 超级用户 `postgres`，全仓无任何降权语句。B9 定级建议：P0 可利用。**

### 1.2 证据链

**第一步：内部元数据库连接账号**

`docker-compose.yml:8` 声明 PG 容器初始化用户：

```
POSTGRES_USER: ${SMARTASK_DB_USERNAME:-postgres}
```

`docker-compose.yml:7` 声明库名 `POSTGRES_DB: ${SMARTASK_DB_DATABASE:-postgres}`。

后端容器实际注入值（`docker inspect smartask-backend`，仅取键名与非敏感值）：

```
SMARTASK_DB_TYPE=postgresql
SMARTASK_DB_HOST=postgres
SMARTASK_DB_PORT=5432
SMARTASK_DB_DATABASE=postgres
SMARTASK_DB_USERNAME=postgres
SMARTASK_DB_DRIVER=psycopg2
SMARTASK_DB_PASSWORD 存在, len=7, enc:v1=False
```

两点值得单独记：连接用户是 `postgres`；连接的库也是 `postgres`，即 PostgreSQL 的维护库（maintenance database），业务表直接建在维护库里。

**第二步：业务数据源连接账号**

`config/datasources.json` 实测（结构与账号，密码只报存在性与长度）：

| id | name | type | host | database_name | username | password_b64 | is_default |
|----|------|------|------|---------------|----------|--------------|------------|
| 6 | SQLite Test Database | sqlite | (空) | (空) | (空) | 无 | False |
| 5 | Feishu DTable Sync | postgresql | localhost | postgres | **postgres** | 有(len=12) | True |
| 7 | PG Smart Warehouse | postgresql | localhost | smart_warehouse | **postgres** | 有(len=12) | False |

两个 PostgreSQL 业务数据源的连接账号都是 `postgres`。

**第三步：env 覆盖只作用于默认数据源**

`backend/config_manager.py:253-295` 的 `_apply_env_datasource_overrides`：`:272` 取 `is_default` 的那一条作为 target，`:273-285` 只对 target 覆盖 host/port/database/username 等，`:291-293` 把其余数据源的 `is_default` 置 False 但不改其连接参数。

因此 id=5（`is_default=True`）被容器 env 覆盖为 `host=postgres, user=postgres, database=postgres`；id=7 保留 `host=localhost`，在容器内 `localhost:5432` 无监听（后端容器只监听 5002），该数据源在容器化形态下不可用（推断，未实证 —— 未启动容器发起连接）。

**第四步：全仓无降权语句**

对 `docker/`（6 个 init SQL）与全仓（排除 `node_modules`）检索 `GRANT|REVOKE|CREATE ROLE|CREATE USER|ALTER ROLE|ALTER USER|NOSUPERUSER|ALTER SYSTEM|pg_hba`：

- `docker/` 目录：**0 命中**
- 全仓命中项只有三处，且均非授权语句：
  - `docs/智能问数发版说明与流程图.md:184`（文档里列黑名单词）
  - `backend/ask_engine_sql.py:63`（黑名单词表本身）
  - `backend/smartask_advanced/skills/sql_quality.py:11`（另一份正则黑名单）

即：项目从未创建过独立的只读角色，也从未对 `postgres` 做任何回收。

**第五步：`postgres` 用户即超级用户**

PostgreSQL 官方镜像的 entrypoint 以 `POSTGRES_USER` 作为 `initdb --username` 的 bootstrap 用户，而 initdb bootstrap 用户按 PostgreSQL 定义即 superuser。此处 `POSTGRES_USER=postgres` 正是该 bootstrap 用户。（此为 PostgreSQL 机制层面的必然结论；`SELECT rolsuper FROM pg_roles WHERE rolname='postgres'` 未实际运行，容器已停止，标注为推断，未实证。）

### 1.3 黑名单本身的缺口

`backend/ask_engine_sql.py:50-67` 是全仓**唯一**的 `_is_read_only_sql` 定义（`backend/four_agent_ask.py:354-355` 只是转调；`backend/controllers/bookshelf.py:1068/1280/1343` 是调用点）。

`:61-65` 词表实际为 **16 个词**（总监原文记为 14，此处更正）：

```
insert, update, delete, drop, truncate, alter,
create, replace, grant, revoke, merge, call,
execute, vacuum, analyze, copy
```

`:59-60` 要求语句以 `select` 或 `with` 开头；`:66-67` 用 `\b(?:...)\b` 做整词匹配。

未覆盖且在超级用户下可直接利用的构造（均以 `select` 开头、不含任何黑名单词，故可通过校验）：

| 构造 | 后果 | 是否需要扩展 |
|------|------|--------------|
| `SELECT pg_read_file(...)` | 任意文件读（含 PG 数据目录、`.env` 若可达） | 否，内建函数，superuser 可用 |
| `SELECT pg_ls_dir(...)` | 目录枚举 | 否 |
| `SELECT pg_read_binary_file(...)` | 二进制文件读 | 否 |
| `SELECT lo_import('/path')` | 文件读入大对象 | 否，superuser 可用 |
| `SELECT pg_sleep(N)` | 连接占死，DoS | 否 |
| `SELECT set_config('...', '...', false)` | 会话参数篡改 | 否 |
| `SELECT * INTO new_table FROM x` | **等价于 CREATE TABLE AS，实际写库** | 否 |
| `SELECT dblink_exec(...)` | 外连、绕过网络边界 | 是，需 `dblink` 扩展 |

其中 `SELECT ... INTO` 这条尤其值得注意：它是 PostgreSQL 里 `CREATE TABLE AS` 的等价写法，`into` 不在 16 词黑名单中，`create` 也不会出现在语句里，因此一条以 `SELECT` 开头的语句可以完成建表写入。这使得「只读」这个前提在语法层就不成立。

`COPY ... FROM PROGRAM` 因 `copy` 在词表内、且语句必须以 select/with 开头，被拦住；这一条总监的假设与实测一致。

### 1.4 定级建议

按总监给出的判定标准：

> 如果连的是 superuser 或 owner，B9 就是 P0 可利用

连接账号为 superuser，且黑名单存在多条一等公民级绕过（`pg_read_file` 任意文件读、`SELECT ... INTO` 实际写库），故：

**B9 定级建议：P0 可利用。** 不是理论风险 —— LLM 生成的 SQL 直接进这条校验，只要提示词注入或模型自由发挥产出上述构造之一，就能以超级用户身份读文件或写表。

### 1.5 运维侧修复建议（不在本次执行范围）

1. 建独立只读角色，例如 `smartask_ro`，`GRANT CONNECT/USAGE/SELECT`，显式 `NOSUPERUSER NOCREATEDB NOCREATEROLE`，并 `REVOKE EXECUTE ON FUNCTION pg_read_file/pg_ls_dir/lo_import FROM PUBLIC`。
2. 业务数据源与元数据库拆成两个账号：元数据库需要写（建表、写日志），业务查询只读。当前两者共用一个超级用户。
3. 业务表迁出 `postgres` 维护库，建独立库。
4. 校验从关键字黑名单改为解析后白名单（只允许 SELECT/WITH 语句树，拒绝 `IntoClause`），或至少在 DB 侧加 `default_transaction_read_only=on` 兜底 —— 后者对 superuser 依然可被 `SET` 覆盖，所以降权才是根治。
5. 加语句超时：`SET statement_timeout` 或角色级 `ALTER ROLE ... SET statement_timeout`，直接消掉 `pg_sleep` 类 DoS。

---

## 2. Q2 — 生产并发模型的部署侧确认

### 2.1 结论先行

**单容器、单进程、无副本、无横向扩展能力，且因 `container_name` 固定连 `--scale` 都用不了。前面有 nginx，但只是单上游反代，不提供任何并发放大或隔离。共享状态互踩的触发频率取决于「同时在途的请求数」，不是「用户数」。**

### 2.2 副本与编排证据

对 `docker-compose.yml` 全文检索 `replicas|deploy:|scale|resources:|limits:`：**0 命中**。

项目内 compose 文件唯一（`ls | grep -i compose` 仅返回 `docker-compose.yml`），不存在 override 文件。

`docker-compose.yml:4/38/80` 三个服务全部声明了 `container_name`：

```
4:    container_name: smartask-postgres
38:    container_name: smartask-backend
80:    container_name: smartask-frontend
```

`container_name` 一旦声明，该服务就无法被 `docker compose up --scale` 放大（同名容器冲突），这一点是 Compose 的硬约束。也就是说，当前编排不仅没开多副本，而且**在不改文件的前提下开不了**。

运行时侧证（`docker inspect`）：

```
/smartask-backend  | Restart=unless-stopped | Memory=0 | NanoCpus=0 | PidsLimit=None
/smartask-frontend | Restart=unless-stopped | Memory=0 | NanoCpus=0 | PidsLimit=None
/smartask-postgres | Restart=unless-stopped | Memory=0 | NanoCpus=0 | PidsLimit=None
```

`com.docker.compose.container-number=1`，三个服务各 1 实例。

### 2.3 进程模型证据

`backend/Dockerfile:45`：

```
CMD ["python", "bootstrap.py"]
```

`backend/bootstrap.py:454`：

```python
os.execv(sys.executable, [sys.executable, app_path])
```

`backend/app.py:251-255`：

```python
if __name__ == "__main__":
    ...
    app.run(host="0.0.0.0", port=BACKEND_PORT, debug=False, use_reloader=False)
```

`backend/requirements.txt` 全文检索 `gunicorn|uwsgi|waitress|hypercorn|uvicorn|gevent|eventlet`：**0 命中**。依赖里只有 `flask==3.0.3` 与 `flask-cors==4.0.1`。

所以运行形态是：容器内 1 个 Python 进程，跑 Werkzeug 开发服务器。总监已实证 Flask `run()` 内部 `options.setdefault("threaded", True)`，`app.py:255` 未传 `threaded`，因此取默认值 True，即 Werkzeug 的 `ThreadedWSGIServer`，每个连接起一个线程，**无线程上限、无队列上限、无背压**。

结论：并发不是被"配置"限制的，而是被 GIL 和内存自然限制的。请求数上去以后表现为线程数无节制增长，不是排队。

### 2.4 网关与暴露面

`frontend/nginx.conf:9-22`：

```
location /api/ {
    proxy_pass http://backend:5002/api/;
    proxy_http_version 1.1;
    ...
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    chunked_transfer_encoding on;
}
```

没有 `upstream` 块，就一个上游 `backend:5002`（Compose 服务名 DNS）。SSE 相关的 `proxy_buffering off` / `proxy_cache off` / `proxy_read_timeout 300s` 配置正确，这块不用动。

但有一条暴露面问题：`docker-compose.yml:57` 把后端端口直接发布到宿主：

```
ports:
  - "${SMARTASK_BACKEND_PORT:-5002}:5002"
```

`docker-compose.yml:14` 同理把 PG 发布到宿主 `5433:5432`。也就是说客户端可以完全绕过 nginx 直连 5002，nginx 上做的任何限制（`client_max_body_size 200m` 等）都不构成边界。PG 5433 对宿主网络开放，结合第 1 节的超级用户 + 明文密码泄露（第 8 节），这条的实际风险不低。

### 2.5 共享状态互踩的触发频率量级判断

这是总监要的核心结论。分析路径如下。

**互踩的必要条件不是"多进程"，而是"同一进程内多线程同时在途"。** 当前是单进程 + `threaded=True`，所以共享状态（`backend/four_agent_ask.py:55` 的 `self._pending_confirmations`，单例见 `:9063`）在**同一个进程的多个线程之间**共享。多副本会让问题变成"状态不一致"，单副本多线程会让问题变成"竞态读写"。两者都会踩，当前是后者。

**关键放大因子是请求时长，不是用户数。** `backend/controllers/smart_chat.py:793` 与 `:1066` 是 SSE 长连接：

```python
response = Response(stream_with_context(event_stream()), mimetype="text/event-stream")
```

一次 NL2SQL 问答要走多轮 LLM 调用，请求在途时间以十秒到分钟计（推断，未实证 —— 未做端到端计时）。而 nginx `proxy_read_timeout 300s` 说明设计上预期单次请求最长可达 5 分钟。

在途窗口 T 越长，重叠概率越高。设人均提问间隔为 I，同时在线 N 人，则任意时刻在途请求数期望约为 `N * T / I`。

给量级判断（这部分是基于部署形态的估算，非实测，标注为推断，未实证）：

| 场景 | 同时在线 | 单次在途 T | 提问间隔 I | 在途重叠期望 | 互踩频率量级 |
|------|----------|-----------|-----------|--------------|--------------|
| 内部试用 | 3 人 | 30s | 5 min | 约 0.3 | 偶发，每天可能撞 1-2 次 |
| 部门推广 | 15 人 | 30s | 3 min | 约 2.5 | **常态重叠，每天多次** |
| 全公司 | 50 人 | 30s | 3 min | 约 8.3 | 持续重叠，几乎每次都在并发 |

判断依据补充：`config/query_history.json` 实测 `history` 有 **159 条**记录，`config/smartask_report_history.json.bak-20260731` 达 8.9MB 且 `history_by_scope` 只有 2 个 scope 键（`business_admin:185****4568`、`super_admin:admin`）。两个信号合起来说明当前**实际使用者极少（2 个账号量级），但单账号产生的历史量很大**。

所以对 B-1 / B16-a / B16-b 的量级结论是：

> **当前形态（2 个活跃账号）下，属于"偶发，人为很难复现，但一定会在某天出现"。一旦推到部门级（10 人以上同时用），因为单次请求在途时间长达数十秒，在途重叠会变成常态，从偶发升级为每天都在撞。**

这条的运维含义：它不是"等出问题再修"的类型，因为它的触发概率随推广线性上升，而现在正处在"看起来没事"的窗口期。修复窗口就是现在。

### 2.6 单进程带来的额外并发约束

补充三条部署侧才看得见的约束：

1. **Werkzeug 开发服务器无优雅重启**。`bootstrap.py:454` 的 `os.execv` 让 python 成为容器 PID 1，而 PID 1 默认忽略 SIGTERM，全仓无 signal handler。实测三容器 `StopTimeout=1`（秒），backend 无 `StopSignal`（默认 SIGTERM）→ 1 秒后必被 SIGKILL。差分证据：同一次停机，`smartask-postgres` ExitCode=0、`smartask-frontend` ExitCode=0、仅 `smartask-backend` **ExitCode=137**。这意味着**任何一次发布都会硬切断所有在途 SSE 连接**。
2. **单进程即单点**。`restart: unless-stopped` 会拉起，但拉起过程中 `bootstrap.py:400-451` 要重跑 7 个迁移 + 等 PG 健康，冷启动窗口不短（`docker-compose.yml:72` 给了 `start_period: 30s`）。
3. **无资源限制**。`Memory=0 NanoCpus=0`，宿主 Docker 分配 `Mem=8321466368`（约 8.32 GB）、`CPUs=12`。线程无上限增长时，单容器可以吃满整个 8.32 GB。

---

## 3. Q3 — 迁移在真实部署链路里的执行情况（B-23）

### 3.1 结论先行

**一个全新环境按 `docker-compose.yml` 拉起，`bs_common_questions` / `bs_dataset_external_configs` / `bs_regression_cases` 三张表都不存在，直到某个请求恰好打到 `controllers/bookshelf.py:526-570` 的内联 DDL 才被创建。**

**部署链路里没有独立 migrate 步骤。**

**存在一个本该拦住它的门禁（`verify_deployment.py`），但那个门禁挂在一条走不通的路径后面。**

### 3.2 三张表的定义分布

对 `backend/migrations/`（7 个 .sql，见 `bootstrap.py:49-57`）与 `docker/postgres/init/`（6 个 .sql）检索：

| 表名 | backend/migrations 命中文件数 | docker/postgres/init 命中文件数 |
|------|------------------------------|--------------------------------|
| `bs_common_questions` | **0** | **0** |
| `bs_dataset_external_configs` | **0** | **0** |
| `bs_regression_cases` | **0** | **0** |

实际 `CREATE TABLE` 定义处（4 个，全在 Python 里）：

| 文件:行号 | 性质 |
|-----------|------|
| `backend/controllers/bookshelf.py:529` / `:542` / `:557` | **请求路径内联 DDL** |
| `backend/runtime_migration.py:620` / `:633` / `:648` | 管理员手动触发的运行时迁移 |
| `backend/import_bookshelf_bundle.py:42` / `:55` / `:70` | 首次 bundle 导入脚本 |
| `backend/create_consumer_standard_dataset.py:662` / `:675` / `:690` | 一次性数据集构造脚本 |

总监的 B-23 结论成立，且我补充一条：`import_bookshelf_bundle.py` 是**第四条路径**，它本来可以在首次启动时建表 —— 但下一节说明它被默认关掉了。

### 3.3 三条 schema 路径逐条核对

**路径 A：`docker/postgres/init/*.sql`（仅新卷首次）**

`docker-compose.yml:17-19` 注释写得很清楚：

```
# Directory mount: every *.sql in docker/postgres/init runs in alphabetical order
# ONLY the first time the data volume is empty (i.e. fresh DB).
- ./docker/postgres/init:/docker-entrypoint-initdb.d:ro
```

`docker/postgres/init/001_bookshelf_schema.sql` 建 8 张表（`:6 bs_datasets`、`:21 bs_dataset_synonyms`、`:35 bs_lld_documents`、`:52 bs_data_dictionary_items`、`:72 bs_schema_definitions`、`:87 bs_table_relations`、`:104 bs_golden_sql_samples`、`:123 bs_agent_prompt_fragments`），**不含目标三表**。

**路径 B：`bootstrap.py` 启动时全跑 7 个迁移**

`backend/bootstrap.py:420-425`：

```python
for migration in MIGRATIONS:
    try:
        _run_migration(migration)
    except Exception as exc:
        log(f"迁移 {migration} 失败（非致命）: {exc}")
        traceback.print_exc()
```

两个问题：

1. 每个迁移失败都是「非致命」，继续往下走，最后 `:452-454` 照样启动 Flask。schema 不完整不会阻断启动。
2. 更上一层，`:407-408`：

```python
elif not _wait_for_postgres():
    log("⚠️ PostgreSQL 不可达，跳过迁移与首次导入；后端仍将启动以便排错。")
```

PG 不可达时，**整个迁移块被跳过**，后端照常启动。（该行即总监提到的 emoji 位置，见第 9 节。）

而且 7 个迁移里本来也没有目标三表（`bootstrap.py:49-57` 的清单与 `backend/migrations/` 目录一致，检索命中为 0）。

**路径 C：`bookshelf_repository.ensure_schema()`**

`backend/bookshelf_repository.py:60-89`：

```python
def ensure_schema(self) -> None:
    migration_path = os.path.join(..., "migrations", "20260330_bookshelf_schema.sql")   # :61-65 硬编码单文件
    ...
    with self._connect() as conn:                                                        # :69
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT to_regclass('public.bs_datasets') AS table_name;")       # :71
            row = cur.fetchone()
            if row and row.get("table_name"):
                return                                                                   # :73-74 早退
```

`:61-65` 只认 `20260330_bookshelf_schema.sql` 一个文件，另外 6 个迁移经此路径永不应用。`:71-74` 探到 `bs_datasets` 存在就直接 return —— 而 `bs_datasets` 在路径 A 里已经被建出来了，所以在 Docker 部署下 `ensure_schema()` **必然走早退分支**，一行 DDL 都不执行。

总监的判断在此得到确认，并且路径 A 的存在使早退成为必然而非偶然。

**路径 D（我补充的）：首次 bundle 导入 —— 被默认关闭**

`backend/bootstrap.py:427-434`：

```python
existing = _bs_dataset_count()
force_import = os.getenv("SMARTASK_BOOTSTRAP_FORCE_IMPORT", "").lower() in {"1", "true", "yes"}
skip_first_import = os.getenv("SMARTASK_BOOTSTRAP_SKIP_FIRST_IMPORT", "").lower() in {"1", "true", "yes"}
if existing == 0 and skip_first_import and not force_import:
    log("SMARTASK_BOOTSTRAP_SKIP_FIRST_IMPORT=1，跳过首次 bundle 导入，等待手动迁移")
elif existing == 0 or force_import:
    ...
    _import_bookshelf_bundle()      # :434  —— 这里面才有目标三表的 CREATE TABLE
```

`_import_bookshelf_bundle()` 对应 `backend/import_bookshelf_bundle.py:42/55/70`，是唯一会在启动期建出目标三表的路径。

但它被两处默认值关掉了：

- `docker-compose.yml:45`：`SMARTASK_BOOTSTRAP_SKIP_FIRST_IMPORT: ${SMARTASK_BOOTSTRAP_SKIP_FIRST_IMPORT:-1}` —— **默认 1**
- `.env:12`：`SMARTASK_BOOTSTRAP_SKIP_FIRST_IMPORT` 生效，value_len=1（即 `1`）

所以 `bootstrap.py:430-431` 命中，日志打「跳过首次 bundle 导入，等待手动迁移」，路径 D 不执行。

### 3.4 部署链路里有没有独立 migrate 步骤

`deploy.sh` 全流程 8 步，与迁移相关的只有：

```
540:info "5/8 构建并启动容器"
541:if [[ "$NO_BUILD" -eq 1 ]]; then
542:  docker compose up -d
543:else
544:  docker compose up -d --build
545:fi
546:ok "后端启动时会自动应用 backend/migrations，包括报告阈值与模板配置更新"
```

`deploy.sh:546` 只是一句 `ok` 输出，**没有任何独立的 migrate 命令**，完全依赖路径 B。而路径 B 如 3.3 所述，既不含目标三表，也允许静默失败。

`docker-compose.yml` 的 backend 服务 `command` 未覆盖，走 `backend/Dockerfile:45` 的 `CMD ["python", "bootstrap.py"]`，同样没有独立 migrate 阶段。

### 3.5 全新环境实际结果推演

按 `docker compose up -d` 拉起一个全新环境（空数据卷）：

| 阶段 | 动作 | 三张表状态 |
|------|------|-----------|
| 1 | PG 首启，执行 `docker/postgres/init/001-006` | 不存在（init 里没有） |
| 2 | backend 起，`bootstrap.py:420-425` 跑 7 个迁移 | 不存在（迁移里没有） |
| 3 | `bootstrap.py:430-431`，`SKIP_FIRST_IMPORT=1` 命中，跳过 bundle 导入 | 不存在 |
| 4 | `bootstrap.py:454` execv 启动 Flask，服务对外可用 | **不存在** |
| 5 | 用户访问命中 `controllers/bookshelf.py:526-570` 的接口 | 此刻才被创建 |

**答案：全新环境按当前部署文档拉起来，这三张表不存在。** 服务会正常起、健康检查会过（原因见 3.7），但凡是依赖这三张表却又没走到那段内联 DDL 的代码路径，都会在运行时报表不存在。

（第 5 步「哪些接口会触发内联 DDL、覆盖率多少」属于后端域，我未逐个追调用链，标注为推断，未实证。）

### 3.6 本该拦住它的门禁，挂在走不通的路径后面

这是本节最值得记的一条。

`scripts/deploy/verify_deployment.py:36-46` 的 `REQUIRED_TABLES` **包含全部三张表**：

```python
REQUIRED_TABLES = [
    "bs_datasets",
    "bs_lld_documents",
    "bs_data_dictionary_items",
    "bs_schema_definitions",
    "bs_table_relations",
    "bs_golden_sql_samples",
    "bs_agent_prompt_fragments",
    "bs_common_questions",              # :44
    "bs_dataset_external_configs",      # :45
    "bs_regression_cases",              # :46
]
```

`:96-104` 对每张表跑 `SELECT COUNT(*)`，失败记 False；`:187-191` 任一 False 则 `overall_ok = False`；`:211-212` 返回 1。

`deploy.sh:554` 对返回码做了硬门禁：

```
docker compose exec -T backend python /app/scripts/verify_deployment.py || fail "容器内自检失败。请执行: bash doctor.sh"
```

**也就是说：如果有人真的跑 `deploy.sh`，第 7 步会当场失败并阻断部署。这个门禁是有效的。**

问题在于它永远轮不到执行。`deploy.sh:508`：

```
require_env "SMARTASK_AI_API_KEY"
```

而 `.env:19` 该键处于**被注释**状态（实测：`.env` 共 53 行，第 15-19 行 `SMARTASK_AI_LABEL` / `SMARTASK_AI_PROVIDER` / `SMARTASK_AI_MODEL` / `SMARTASK_AI_BASE_URL` / `SMARTASK_AI_API_KEY` 全部为注释行）。`deploy.sh:109-114` 的 `require_env` 对空值直接 `fail`。

所以 `deploy.sh` 卡在第 3/8 步，永远走不到第 7/8 步的自检。

**旁证（部署路径断裂的实证）**：后端容器的完整环境变量键名清单里，**不存在 `SMARTASK_AI_API_KEY`**。如果实例是 `deploy.sh` 起的，这个键必然存在（否则脚本会 fail）。结合容器标签：

```
com.docker.compose.project.config_files=/Users/ltl123/smartask/sa1.0/smartask/docker-compose.yml
com.docker.compose.project.working_dir=/Users/ltl123/smartask/sa1.0/smartask
```

结论：**当前运行实例是手工 `docker compose up` 起的，不是 `deploy.sh`。** 上一轮我标注为推断的这条，现已实证。

### 3.7 为什么健康检查没有发现

`backend/app.py:225-233`：

```python
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "running",
        "message": "smart analytics backend is running",
        "version": "2.0.0",
    })
```

返回的是硬编码字符串，不查 DB、不查 schema、不查向量库、不查 LLM 可达性。`docker-compose.yml:68` 的 healthcheck 打的就是这个端点。所以只要 Flask 进程活着，健康检查就是绿的 —— schema 缺三张表、审计日志连续 7 天写不进库（第 5 节），健康检查全程无感。

这是典型的安慰剂式健康检查。

### 3.8 B-23 的运维侧背书

**支持将 B-23 放进 P0 止血清单第一梯队。** 部署侧证据链完整：

1. 三张表不在任何声明式 schema 里（migrations 0 命中、init 0 命中）。
2. 部署链路无独立 migrate 步骤（`deploy.sh:540-546` 只有 compose up 加一句 echo）。
3. 唯一能在启动期建表的路径被默认关闭（`docker-compose.yml:45` + `.env:12` 的 `SKIP_FIRST_IMPORT=1`）。
4. 唯一能发现问题的门禁不可达（`deploy.sh:508` 卡在 `.env:19`）。
5. 健康检查不覆盖（`app.py:225-233` 返回固定串）。

五道防线全部失效，全新环境必然带缺陷上线。

修复方向（成本 S，改动小）：把三张表的 DDL 抽成 `backend/migrations/2026xxxx_bookshelf_aux_tables.sql` 并加进 `bootstrap.py:49-57` 的 `MIGRATIONS`，同时把 `bootstrap.py:420-425` 的「非致命」改为可配置严格模式（生产 fail-fast）。

---

## 4. 补充问题 — `ensure_schema()` 调用密度与 `max_connections` 风险

### 4.1 调用点实测（对总监数据的更正）

总监记为 22 个调用点。实测为 **28 个**（排除定义行，检索 `ensure_schema()`）：

| 文件 | 调用次数 | 性质 |
|------|----------|------|
| `backend/controllers/bookshelf.py` | 12 | 请求路径 |
| `backend/system_log_store.py` | **6** | 请求路径（审计日志，总监清单未含） |
| `backend/runtime_migration.py` | 4 | 管理员触发 |
| `backend/import_bookshelf_bundle.py` | 1 | CLI 脚本 |
| `backend/four_agent_ask.py` | 1 | 请求路径 |
| `backend/export_bookshelf_bundle.py` | 1 | CLI 脚本 |
| `backend/create_consumer_standard_dataset.py` | 1 | CLI 脚本 |
| `backend/controllers/rbac.py` | 1 | 请求路径 |
| `backend/controllers/data_permissions.py` | 1 | 请求路径 |

**请求路径上的调用点为 21 个**（12 + 6 + 1 + 1 + 1），CLI 脚本 3 个，管理员触发 4 个。

漏掉的 `system_log_store.py` 那 6 处尤其关键：审计日志是**每个请求都会写**的路径（`backend/app.py:205-222` 的 after_request 钩子里调用），意味着 `ensure_schema()` 的调用频率与请求数同阶，不是偶发。

### 4.2 无连接池，已实证

检索 `ThreadedConnectionPool|SimpleConnectionPool|pool_size|create_engine|pgbouncer|psycopg2\.pool`（范围 `backend/` + `docker-compose.yml`）：**0 命中**。

`psycopg2.connect` 调用点：**15 处**。

`backend/bookshelf_repository.py:41-51` 的 `_connect()` 每次新建原始连接：

```python
def _connect(self):
    datasource = self._pick_metadata_datasource()
    try:
        return psycopg2.connect(
            host=..., port=..., database=..., user=..., password=...,
            connect_timeout=8,
        )
```

`backend/system_log_store.py:60-61` 直接复用它：

```python
def _connect():
    return BookshelfRepository()._connect()
```

### 4.3 连接生命周期写法风险

`with self._connect() as conn` 写法在 `backend/` 内出现 **4 次**；`backend/bookshelf_repository.py` 与 `backend/system_log_store.py` 两个文件中显式 `.close()` 出现 **0 次**。

需要点明一个 psycopg2 语义细节：`with connection` **只管事务边界（提交或回滚），不关闭连接**。连接的实际释放依赖 CPython 引用计数在函数退出时归零后触发析构。

正常路径下这能工作。但有两个场景会让连接滞留（推断，未实证 —— 未做连接数压测）：

1. 异常被捕获后 traceback 被保留（异常对象的 `__traceback__` 持有帧引用，帧持有 `conn` 局部变量），连接生命周期被拉长到异常对象被回收为止。而 `backend/app.py:220-221` 存在 `except Exception: pass` 这类吞异常写法。
2. `bookshelf_repository.py:73-74` 的早退发生在 `with` 块内部，退出 `with` 只做提交，连接靠 return 后引用归零释放 —— 链路上任何一处把 conn 存进对象属性或闭包都会破坏这个假设。

### 4.4 `max_connections` 实际值

- `docker-compose.yml` 中 postgres 服务**无 `command:` 覆盖**（全文已读，`:2-24` 无该键）。
- `docker/postgres/init/*.sql` 检索 `ALTER SYSTEM|max_connections`：**0 命中**。
- 数据卷内 `postgresql.conf` 不可读（见 0.2）。

因此实际值应为 `postgres:16-alpine` 镜像默认的 **`max_connections = 100`**（推断，未实证 —— 未运行 `SHOW max_connections`）。其中 PostgreSQL 默认保留 3 个给超级用户（`superuser_reserved_connections`），普通可用约 97。

### 4.5 会不会打爆 max_connections

**结论：当前形态下打不爆；但这不是因为设计安全，而是因为并发天花板恰好比连接天花板更低。**

推导（标注为推断，未实证 —— 未做并发压测）：

关键点在于 `max_connections` 约束的是**同时存在**的连接数，不是连接创建速率。当前是单进程 + Werkzeug `threaded=True`，同时在途请求数 = 活跃线程数。每个请求内部的多次 `ensure_schema()` 是**串行**发生的（一个请求线程同一时刻只持有 1-2 个连接），所以：

```
峰值并发连接数 ≈ 同时在途请求数 × 单请求同时持有的连接数(1~2) + 常驻连接(飞书同步线程等)
```

要撑到 97，需要约 50-90 个请求同时在途。按第 2.5 节的量级判断，当前 2 个活跃账号、部门级 15 人也只到个位数在途，**远不到连接上限**。

真正的代价不在连接数，而在**每请求的连接建立开销**：

- 每次 `ensure_schema()` = 1 次 TCP 连接 + 1 次认证握手 + 1 次 `to_regclass` 查询。
- 单请求内可能触发多次（例如一次 bookshelf 接口调用 + 一次 after_request 审计日志写入，至少 2 次）。
- 无连接池意味着这些开销无法摊销。
- PostgreSQL 每个连接在服务端 fork 一个 backend 进程，连接建立本身有毫秒级到十毫秒级成本，并且每连接有固定内存开销。

所以现实中的表现不是「连接数报错」，而是「每个请求平白多几十毫秒」和「PG 侧进程频繁创建销毁」。

**但有三个会让结论翻转的条件，需要写进风险台账：**

1. **一旦按 WSGI 迁移方案开多 worker**（第 6 节 Phase 3），连接数按 worker 数线性放大。4 worker × 每 worker 数十在途 = 直接逼近 100。**换 gunicorn 多 worker 之前，必须先上连接池。**
2. **一旦 `except` 吞异常路径导致连接滞留**（4.3），连接数会缓慢爬升而不回落，属于泄漏型故障，几小时到几天后打爆。这类故障最难查，因为它不与流量峰值同步。
3. **PG 侧无资源限制**（`Memory=0`），连接数上升带来的内存增长没有容器级刹车，可能先 OOM 宿主而不是先报 `too many connections`。

**建议动作（成本 S）：**

- 加 `psycopg2.pool.ThreadedConnectionPool`，`minconn=2, maxconn=10`，全局单例。这一步同时解决开销与泄漏两个问题。
- `ensure_schema()` 加进程内一次性缓存标志：schema 探测的结果在进程生命周期内不会变（表不会自己消失），21 个请求路径调用点里绝大多数是纯浪费。改成模块级 `_SCHEMA_READY = False` 布尔位，首次成功后短路，可以直接砍掉绝大部分连接。
- 在 compose 给 postgres 加 `command: ["postgres", "-c", "max_connections=200"]` 作为缓冲，并配 `deploy.resources.limits.memory`。

---

## 5. 可观测性

### 5.1 审计日志已静默失效（P0）

这是本次审计里唯一一条「已经在生产上坏掉、且无人知晓」的问题。

`backend/logs/system_event_logs.jsonl` 实测：

- 总行数 **126**
- **126 条全部含 `insert_failed` 字段**，即全部为入库失败后的降级落盘
- 时间范围 **2026-07-31 14:33:50 ~ 2026-08-06 08:47:33**（跨 7 天）
- 失败原因分布：
  - x98 `No active PostgreSQL datasource found. Please configure one in 数据源...`
  - x28 `PostgreSQL connection failed: could not translate host name "smart...`
- 事件类型分布：`http_error` 117、`smart_chat_rejected` 9

降级写入点 `backend/system_log_store.py:120-129`，触发点 `:201`：

```python
_fallback_write({"insert_failed": str(exc), **row})
```

根因在 `backend/system_log_store.py:60-61`：

```python
def _connect():
    return BookshelfRepository()._connect()
```

审计日志复用了业务元数据库的连接逻辑，而 `BookshelfRepository._connect()` 走 `_pick_metadata_datasource()` —— 依赖用户在「数据源管理」里配置且**置为启用**的数据源。用户一旦停用数据源，审计日志就跟着断。审计通道不应该依赖一个用户可以在 UI 上关掉的东西。

第二类错误（x28 `could not translate host name "smartask-postgres"`）另有线索：`.env:24` 的 `SMARTASK_DB_HOST` value_len=17，而字符串 `smartask-postgres` 恰为 17 字符（推断，未实证 —— 未打印值）。而 `docker-compose.yml:46` 用 `environment:` 把它覆盖为 `postgres`（`environment` 优先级高于 `env_file`）。也就是说，凡是绕开 compose 注入、直接读 `.env` 的执行上下文，拿到的就是 `smartask-postgres`，在 PG 容器停止时无法解析。

**影响**：安全审计、操作留痕、错误追溯连续 7 天全部丢失（只留在一个无轮转的 jsonl 里）。对内部系统而言，这条属于合规性问题，不只是可观测性问题。

### 5.2 日志现状

| 项 | 实测 | 文件:行号 |
|----|------|-----------|
| 裸 `print(` 数量（backend，排除 tests） | **152 处** | 全域 |
| `import logging` 数量 | **2 处** | 全域 |
| 容器日志驱动 | `json-file` | `docker inspect` |
| 容器日志上限 | **无**（`LogOpts={}`，无 max-size/max-file） | `docker inspect` 三容器一致 |
| 落盘日志文件 | `backend/logs/` 下 3 个 jsonl，共约 370 KB | `smart_chat_controller.jsonl` 3.3KB / `smartask_trace.jsonl` 240KB / `system_event_logs.jsonl` 126KB |
| 日志轮转 | **无** | 无 logrotate 配置，无 RotatingFileHandler |
| 结构化 | 部分（jsonl 是结构化的，152 处 print 不是） | — |
| 请求追踪 ID | **无** | 检索无 request_id 贯穿实现 |

152 处 `print` 对单进程 + `PYTHONUNBUFFERED=1`（`docker-compose.yml:52`）意味着全部直接进 Docker json-file 日志，且该日志无大小上限，长期运行会吃满磁盘。

### 5.3 监控与告警现状

| 能力 | 现状 |
|------|------|
| 指标端点 | 无（检索 `metrics` 无实现） |
| APM / 链路追踪 | 无 |
| 错误上报（Sentry 等） | 无（检索 `sentry` 0 命中） |
| 告警 | 无 |
| 健康检查深度 | 安慰剂，见 3.7 |

### 5.4 最小成本可观测性方案

不引入 Prometheus / Grafana / Sentry / ELK。分三层，按投入产出排序。

**第 0 层 —— 止血（半天，必须做）**

1. `docker-compose.yml` 三个服务各加 4 行：

```yaml
logging:
  driver: json-file
  options:
    max-size: "50m"
    max-file: "3"
```

不加这个，磁盘满是时间问题。

2. 审计日志改用**独立连接配置**，不复用 `BookshelfRepository`。给 `system_log_store.py` 一个只认环境变量的 `_connect()`，与业务数据源解耦。这一条直接修掉 5.1。

3. `backend/logs/*.jsonl` 加尺寸上限与轮转（Python 标准库 `RotatingFileHandler` 即可，无新依赖）。

**第 1 层 —— 能定位问题（1-2 天）**

4. 请求 ID 贯穿：Flask `before_request` 生成 `request_id`（8 位十六进制），塞进 `flask.g`，在 after_request 与所有 jsonl 写入点带上。SSE 场景把 `request_id` 作为首个 event 下发给前端，出问题时用户截图就能定位。

5. `/api/health` 改深度检查，返回各依赖状态与耗时：

```json
{"status":"ok","checks":{"postgres":{"ok":true,"ms":3},
 "chroma":{"ok":true,"ms":11},"llm":{"ok":true,"ms":180}},
 "schema":{"missing_tables":[]},"version":"<git-sha>"}
```

`schema.missing_tables` 直接复用 `verify_deployment.py:36-46` 的 `REQUIRED_TABLES` —— 这样第 3 节的问题会在健康检查里持续暴露，而不是等部署脚本。同时 compose healthcheck 仍只认 HTTP 200，避免深度检查抖动导致容器被反复重启（深度信息给人看，存活判断给编排看，两者分开）。

6. `/api/metrics` 返回纯 JSON（不上 Prometheus 格式，避免引入 exporter 依赖）：进程 uptime、当前活跃线程数、各接口累计调用数与 p95 耗时、DB 连接创建计数、LLM 调用次数与失败数。数据源直接复用已有的 `system_event_logs` 表（`docker/postgres/init/006_system_event_logs.sql` 已建好索引）。

**第 2 层 —— 有人知道出事了（半天）**

7. 一个 20 行的 `watch.sh` + cron，每 5 分钟拉一次 `/api/health` 与 `/api/metrics`，命中阈值就发飞书机器人 webhook（项目已有飞书集成，`.env:43-45` 有 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_BASE_URL`，复用即可，零新依赖）：

| 规则 | 阈值 | 级别 |
|------|------|------|
| `/api/health` 非 200 或超时 | 连续 2 次 | P0 |
| `checks.postgres.ok == false` | 立即 | P0 |
| `schema.missing_tables` 非空 | 立即 | P0 |
| `system_event_logs` 表 5 分钟内零新增但 jsonl 有增长 | 立即 | P0（正是 5.1 的特征） |
| 接口错误率 > 5% | 5 分钟窗口 | P1 |
| p95 > 30s | 5 分钟窗口 | P1 |
| 容器 ExitCode 非 0 | 立即 | P1 |

第 4 条规则是专门为 5.1 那类故障设计的：**降级通道有流量而主通道没有，就是主通道坏了**。这条规则如果早就存在，7 天前就会告警。

总成本：约 3 人天，零新增基础设施，零新增依赖。

---

## 6. 运行时形态与 WSGI 迁移链

### 6.1 现状与危害

`backend/app.py:255` 用 Werkzeug 开发服务器承载生产流量。具体危害（按运维可感知程度排序）：

1. **无优雅停机**：`bootstrap.py:454` 的 `os.execv` 使 python 成为 PID 1，PID 1 默认忽略 SIGTERM，全仓零 signal handler。三容器 `StopTimeout=1` 秒，backend 无 `StopSignal`。差分实证：同次停机 postgres ExitCode=0、frontend ExitCode=0、backend **ExitCode=137**。每次发布硬切在途 SSE。
2. **无进程管理**：主线程崩了整个容器就没了，靠 `restart: unless-stopped` 冷拉，冷启动要重跑 7 个迁移。
3. **无请求上限与背压**：`threaded=True` 每连接一线程，无上限。
4. **无慢请求防护**：单个卡死的 LLM 调用会一直占着线程。
5. **性能**：Werkzeug 未做生产优化，官方文档明确不建议用于生产。

### 6.2 迁移链：必须拆成两件事

关键认知：**「换服务器」和「开多 worker」是两件事，成本和风险差一个数量级。** 前者是配置改动，后者要求先把进程内共享状态全部外置。混在一起做必然翻车。

### 6.3 开多 worker 前必须同批解决的共享状态（7 项）

| # | 状态 | 位置 | 多 worker 下的症状 |
|---|------|------|-------------------|
| 1 | `_pending_confirmations` 内存会话 | `backend/four_agent_ask.py:55`（单例 `:9063`，读写 `:7837/:7839/:7849/:8878/:9058`） | 用户在 worker A 发起待确认，确认请求落到 worker B，找不到会话 |
| 2 | `auth_tokens.json` 令牌存储 | `backend/auth_store.py:20`（`TOKEN_FILE`），保存走 `:56 write_json` | 多 worker 并发写同一 JSON，非原子截断写，令牌表可能被写坏；实测该文件 20KB |
| 3 | config JSON 写入非原子 | `backend/config_manager.py:145-154`（`open(filepath,'w')` + `json.dump`，无 `os.replace`、无 `fcntl`） | 同上；`config/smartask_report_history.json` 实测 **10MB**，写窗口长，与 SIGKILL 叠加时极易截断 |
| 4 | ChromaDB embedded | `backend/vanna_core.py:122`（默认 `BASE_DIR/chroma_db`） | SQLite 后端，多进程同时写会锁冲突 |
| 5 | 分数据源向量库 | `backend/datasource_router.py:214` | 同上，且路径未持久化（见 6.5） |
| 6 | SSE 会话亲和 | `backend/controllers/smart_chat.py:793/:1066` | 多 worker 下 SSE 与后续请求可能落到不同进程 |
| 7 | 飞书同步后台线程 | `backend/controllers/feishu_sync.py:215/:268`（`thread.daemon = True`） | 每个 worker 各起一份，定时任务重复执行 N 次 |

第 3 项要特别强调：一个 10MB 的 JSON 用非原子方式覆盖写，同时容器停机宽限期只有 1 秒 —— 这两个缺陷叠加，等于**每次停机都在赌那一刻没有人在写配置**。这是当前形态下最接近"数据损坏"的组合。

### 6.4 分阶段方案

**Phase 0 —— 止血（半天，强烈建议立即做）**

改 `docker-compose.yml`，不动代码：

```yaml
backend:
  init: true                 # tini 接管 PID 1，正确转发信号
  stop_grace_period: 30s     # 覆盖当前的 StopTimeout=1
```

postgres 同样加 `stop_grace_period: 30s`（当前也是 1 秒，数据量涨上去后 1 秒内完成检查点无法保证，届时会被 SIGKILL 打断，触发下次启动 crash recovery —— 推断，未实证）。

回滚点：删掉这两行，`docker compose up -d` 即回到原状。零代码风险。

**Phase 1 —— 换 WSGI 服务器，仍单进程（1 天）**

1. `backend/requirements.txt` 加 `gunicorn==22.0.0`。
2. `backend/Dockerfile:45` 的 CMD 保持 `bootstrap.py`（迁移逻辑要保留），改 `bootstrap.py:454` 的 execv 目标为 gunicorn：

```
gunicorn --worker-class gthread \
         --workers ${SMARTASK_WEB_WORKERS:-1} \
         --threads ${SMARTASK_WEB_THREADS:-8} \
         --timeout ${SMARTASK_WEB_TIMEOUT:-600} \
         --graceful-timeout 30 \
         --bind 0.0.0.0:5002 \
         app:app
```

三个关键点：

- **workers 做成环境变量且默认 1**。这样 Phase 1 与 Phase 3 之间不需要再改镜像，只改一个 env。
- **`--timeout` 必须放大到 600**。gunicorn 默认 30 秒，而本系统单次 NL2SQL 可能跑数十秒到数分钟（nginx 那边已经给到 `proxy_read_timeout 300s`）。用默认值会把正常的长查询当成卡死 worker 杀掉，这是最容易踩的坑。
- **worker-class 必须是 `gthread` 而非 `sync`**。SSE 是长连接，`sync` worker 会被一个 SSE 连接完全占死。

3. gunicorn master 原生处理 SIGTERM，Phase 0 的 `init: true` 可以保留（无害）。

回滚点：`bootstrap.py:454` 改回 `os.execv(sys.executable, [sys.executable, app_path])`，重建镜像。建议保留上一版镜像 tag 以便直接切回（当前零镜像版本化，见第 7 节）。

**Phase 2 —— 状态外置（3-5 天）**

按 6.3 表逐项处理：

- 第 1 项：`_pending_confirmations` 迁到 PG 表（已有 PG，不引 Redis），带 TTL 字段与清理任务。
- 第 2、3 项：`config_manager.write_json` 改原子写 —— 写临时文件 + `os.replace()`，加 `fcntl.flock` 跨进程互斥。这一步即使不开多 worker 也应该做，因为它同时修掉 SIGKILL 截断风险。
- 第 4、5 项：ChromaDB 走 client/server 模式，或确认单 worker 独占。
- 第 6 项：SSE 需要会话亲和 —— 注意 `ip_hash` 在容器网络里全部来源 IP 相同，会失效，必须用 cookie 或把会话状态外置。
- 第 7 项：飞书同步拆成独立容器或加分布式锁。

**Phase 3 —— 开多 worker（Phase 2 完成后，1 天）**

改一个环境变量 `SMARTASK_WEB_WORKERS=4`。**前置条件：连接池必须先上（见 4.5），否则 4 worker 会把连接数直接推向 100。**

### 6.5 建议

**Phase 0 + Phase 1 立即做，Phase 2 排进下个迭代，Phase 3 暂不做。**

理由：按第 2.5 节的量级判断，当前活跃账号只有 2 个，单进程 + 8 线程完全够用。Phase 3 的收益在当前规模下接近于零，风险却最高。先把「不能优雅停机」「无请求上限」这两个每天都在发生的问题解决掉。

---

## 7. 容器与编排质量

| 项 | 现状 | 证据 |
|----|------|------|
| 后端镜像分层 | **单阶段**，`build-essential` 与 `libpq-dev` 装了未卸 | `backend/Dockerfile`，实测镜像 **1.52GB**（对比 `python:3.11-slim` 基础镜像 189MB） |
| 前端镜像分层 | 多阶段（node:20-alpine → nginx:1.27-alpine），实测 80.4MB | `frontend/Dockerfile` |
| 运行用户 | **root**（无 `USER` 指令，`docker inspect` 的 `User=[]` 为空） | `backend/Dockerfile` 无 USER；inspect 实测 |
| 资源限制 | **无**（三容器 `Memory=0 NanoCpus=0 PidsLimit=None`） | `docker inspect` |
| 重启策略 | `unless-stopped`（三容器一致） | `docker-compose.yml:5/39/81` |
| 停机宽限 | **1 秒**（三容器一致） | `docker inspect` `StopTimeout=1` |
| PID 1 处理 | 无 `init:`（`Init=None`） | `docker-compose.yml` 无该键 |
| 健康检查 | 三个都有，但后端是安慰剂 | `docker-compose.yml:20-24/67-72/87-92`；`app.py:225-233` |
| 依赖顺序 | 正确（`postgres:service_healthy` → `backend:service_healthy` → frontend） | `docker-compose.yml:53-55/82-84` |
| 端口暴露面 | **PG 5433、后端 5002 直接发布到宿主**，可绕过 nginx | `docker-compose.yml:14/57` |
| 镜像版本化 | **无**，全部 `:latest` | `docker images` 实测 `smartask-backend:latest` / `smartask-frontend:latest` |
| 日志上限 | **无** | `docker inspect` `LogOpts={}` |

### 7.1 环境一致性漂移

三个容器由三次独立操作创建：

| 容器 | Created | compose 版本 |
|------|---------|-------------|
| smartask-postgres | 2026-07-08T07:18:11 | 5.1.4 |
| smartask-backend | 2026-08-06T01:26:59 | 5.1.4 |
| smartask-frontend | 2026-08-06T08:01:56 | **5.3.0** |

backend 与 frontend 带 `com.docker.compose.replace` 标签（被替换重建过）。三者 `config-hash` 各不相同。

含义：**不存在一次"整栈同时起"的基线状态**，问题复现困难。

### 7.2 数据持久化：分源向量库未挂载（P1）

后端容器完整挂载清单（`docker inspect`）：

```
bind   ./config          -> /app/config           RW
bind   ./logs            -> /app/logs             RW
bind   ./backend/imports -> /app/backend/imports  RW
bind   ./backend/logs    -> /app/backend/logs     RW
bind   ./backups         -> /app/backups          RW
volume smartask_chroma   -> /app/chroma_db        RW
```

`backend/datasource_router.py:214` 的落盘目标：

```python
chroma_path = os.path.join(os.path.dirname(__file__), f"chroma_db_source_{source_id}")
```

即 `/app/backend/chroma_db_source_<id>` —— **没有任何挂载覆盖这个路径**，落在容器可写层。

宿主侧验证：`ls -d backend/chroma_db*` → `no matches found`；`ls -d chroma_db` → `No such file or directory`。即分源向量库在宿主和命名卷里都不存在。

结合 backend 容器带 `com.docker.compose.replace` 标签（说明被重建过），分源向量库至少已经丢过一次（推断，无法回溯当时目录内容）。

对比 `backend/vanna_core.py:122` 的默认路径 `BASE_DIR/chroma_db`（`:17` BASE_DIR 为项目根的父级 → 容器内 `/app/chroma_db`）是挂在命名卷 `smartask_chroma` 上的，是安全的。两条路径规则不统一，是这个问题的根源。

---

## 8. 配置与密钥安全

### 8.1 仓库公网可读（P0，最高优先级）

```
git remote -v
origin  https://github.com/qishen123456/docker-setup.git (fetch/push)
```

匿名探测（未认证）：

```
https://github.com/qishen123456/docker-setup            -> HTTP 200
https://api.github.com/repos/qishen123456/docker-setup  -> HTTP 200
```

匿名可读即公开仓库。本地与远程完全同步：

```
git rev-list --left-right --count origin/docker-setup...HEAD
落后origin=0 领先origin=0
```

仓库共 **212 个提交**，远程分支只有 `origin/docker-setup`（`origin/HEAD -> origin/docker-setup`）。

**一个内部 NL2SQL 系统的完整代码，此刻就在公网上。**

### 8.2 git 历史中的明文凭据（P0）

按提交统计密钥字段（**仅统计数量，未输出任何值**）：

| 文件 | 提交 | 日期 | 非空密钥字段数 | 已加密(`enc:v1`) |
|------|------|------|----------------|------------------|
| `config/ai_settings.json` | a4e6e54 | 2026-04-28 | **4** | 0 |
| | 6d8b804 | 2026-03-30 | 2 | 0 |
| | d428112 | 2026-03-29 | 2 | 0 |
| | d689f9a | 2026-03-28 | 2 | 0 |
| `config/datasources.json` | a4e6e54 | 2026-04-28 | **2** | 0 |
| | 6d8b804 | 2026-03-30 | 2 | 0 |
| | d428112 | 2026-03-29 | 1 | 0 |
| | d689f9a | 2026-03-28 | 1 | 0 |
| `config/feishu_sync.json` | a4e6e54 / 6d8b804 / 668a5dd / d689f9a | 2026-03-28 ~ 04-28 | 各 1 | 0 |

清理提交 `23aeea5`（`chore: move local secrets to env file`，2026-04-28）对应 `bytes=0`，即**只删除了工作区文件，历史 blob 全部保留**。

可达性验证：

```
git branch -a --contains d689f9a / d428112 / 6d8b804 / a4e6e54
  -> 全部返回 remotes/origin/docker-setup
```

四个含密钥的提交都在公网可达的分支上。

另需注意 `a4e6e54` 的提交信息是 `chore: initial sync to gitee`，说明带密钥的历史**至少同步过两个代码托管平台**。

`enc:v1` 命中数全程为 0 —— 项目自带 `backend/secret_codec.py`（`:20 SECRET_PREFIX = "enc:v1:"`，`:23 DEFAULT_KEY_FILE`，`:35` 支持 `SMARTASK_SECRET_MASTER_KEY`）但**从未启用**。写了没用。

### 8.3 当前 HEAD 上的活体硬编码密钥（P0）

`backend/get_feishu_tables.py:8`：key=`app_secret`，value_len=**32**，非空、非加密（值未打印）。

`git ls-files --error-unmatch backend/get_feishu_tables.py` → **TRACKED**，即公网可见。

长度 32 与 `config/feishu_sync.json` 中 `sync_configs[*].app_secret`、以及 `.env:44` 的 `FEISHU_APP_SECRET`（value_len=32）一致，极可能为同一凭据（推断，未做值比对 —— 门禁禁止读取密钥值）。

全仓被跟踪文件的密钥模式扫描（`api_key|apikey|password|passwd|app_secret|secret_key|access_key|private_key|token` 后跟 12 位以上字面量）：命中仅此 1 个文件 1 处。

### 8.4 公网可见的业务数据与 PII（P0）

`git ls-files config/` 返回 **10 个被跟踪文件**（`.gitignore:83-99` 声明忽略但对已跟踪文件无效）：

| 文件 | 大小 | 结构实测 | 敏感性 |
|------|------|----------|--------|
| `config/query_history.json` | 492K | `history` **159 条**，字段 `[created_at, error, id, question, sql, status]` | 真实业务提问 + 真实生成 SQL |
| `config/dataset_node_index.json` | 312K | `datasets` 3 个、`flat_alias_index` **334 条** | 完整业务数据字典与字段别名 |
| `config/rbac_permissions.json` | 16K | `roles` 6 个、`groups` 2 个（含 `user_ids`） | 权限模型与用户组 |
| `config/data_permissions.json` | 4.0K | `rules` 键为数据源 id `2/3/62` | 行级数据权限规则 |
| `config/smartask_report_history.json.bak-20260731` | 8.5M | `history_by_scope` 2 个键：`business_admin:185****4568`、`super_admin:admin` | **手机号形态账号标识（已脱敏）** |
| `config/sql_prompts.json` | 12K | — | 提示词工程 |
| `config/confirmed_behaviors_baseline.md` | 28K | — | 内部行为基线 |
| `config/smartask_issue_analysis.md` | 20K | — | 内部问题分析 |
| `config/smartask_test_question_list.md` | 20K | — | 测试问题清单 |
| `config/run_smartask_tests.py` | 16K | — | 测试脚本 |

这 10 个文件的密钥模式命中均为 0，但表结构、指标口径、真实查询、权限模型、账号标识全部公开。手机号形态标识涉个人信息合规。

### 8.5 工作区密钥清单（仅位置与类型）

| 位置 | 类型 | 状态 | 是否入库 |
|------|------|------|----------|
| `.env`（53 行） | 混合 | 未加密 | 未跟踪（`git log` commits=0） |
| `.env:19 SMARTASK_AI_API_KEY` | AI 密钥 | **被注释**（导致 `deploy.sh:508` 必 fail） | — |
| `.env:44 FEISHU_APP_SECRET` | 飞书密钥 | 生效，len=32 | — |
| `.env:52 SMARTASK_ADMIN_PASSWORD` | 管理员口令 | 生效，len=11 | — |
| `.env:28 SMARTASK_DB_PASSWORD` | 库密码 | 生效，len=7 | — |
| `config/ai_settings.json` | 3 个 `models[*].api_key_b64` | base64，**非加密**（`startswith("enc:")` 全 False） | 工作区未跟踪，历史有 |
| `config/datasources.json` | 2 个 `databases[*].password_b64` | base64，非加密，len=12 | 同上 |
| `config/feishu_sync.json` | `sync_configs[*].app_secret` | **裸明文**，len=32 | 同上 |
| `config/.secret_master_key` | 主密钥 | 43 字节，权限 **`-rw-r--r--` (0644)** | 未跟踪 |
| `config/auth_tokens.json` | 会话令牌 | 20K | 未跟踪 |
| `backend/get_feishu_tables.py:8` | 硬编码 `app_secret` | len=32 | **TRACKED，公网可见** |
| backend 容器 env | `SMARTASK_DB_PASSWORD` / `SMARTASK_ADMIN_PASSWORD` / `SMARTASK_SECRET_KEY` / `FEISHU_APP_SECRET` | 明文注入 | — |

`config/.secret_master_key` 权限 0644 意味着同宿主任何用户可读，等于主密钥没有保护 —— 即便启用了 `enc:v1`，密文与密钥放在同一目录且同为可读，加密收益接近零。

正例记一笔：`doctor.sh:70-83` 对输出做了脱敏处理，是项目里对的做法，可以作为其它脚本的模板。

### 8.6 处置顺序（轮换 > 清理 > 收敛）

顺序不能颠倒。已公开的内容，删除历史不能撤回已被 clone / fork / 被代码搜索与第三方爬虫收录的副本。

**第 1 步（按小时计，最迟今天内）—— 凭据轮换**

- `ai_settings.json` 涉及的 3 个模型 API Key：服务商控制台重新签发并**吊销旧 key**。
- `datasources.json` 涉及的库账号：改密；同时确认这些库是否开放公网端口（`docker-compose.yml:14` 已把 PG 发布到宿主 5433，需一并评估）。
- 飞书 `app_secret`：重置，并检查飞书后台该应用的调用记录有无异常来源。
- `SMARTASK_ADMIN_PASSWORD` / `SMARTASK_SECRET_KEY`：虽然值不在版本库，但部署脚本与端口配置已公开，建议一并轮换。
- 轮换后核对 `backend/get_feishu_tables.py:8` 是否还有残留。

**第 2 步（今天到明天）—— 止血与收敛**

- 仓库改为 private。这不撤回已泄露内容，但阻断继续扩散。
- 内部系统代码从个人账号迁到公司组织账号（流程问题，需管理层推动）。
- `config/` 下 10 个跟踪文件 `git rm --cached`，落实 `.gitignore`。

**第 3 步（本周）—— 历史清理与防复发**

- `git-filter-repo` 清除 `ai_settings.json` / `datasources.json` / `feishu_sync.json` / `query_history.json` / `smartask_report_history.json.bak-20260731` / `dataset_node_index.json` 的全部历史 blob，强推并通知所有 clone 方重新拉取。212 个提交，一次可做完。
- 接 pre-commit 密钥扫描（gitleaks 单二进制，不引入平台）。
- 启用 `backend/secret_codec.py` 的 `enc:v1`，并把 `config/.secret_master_key` 权限收到 0600、迁出 `config/` 目录（当前 `config/` 是 bind mount 且与密文同目录）。

---

## 9. 日志规范：源码 emoji 使用（对总监数据的更正）

总监指出 `backend/bootstrap.py:408` 的日志文案带 U+26A0 U+FE0F，并称"全仓唯一一处"。

实测（扫描 `.py` / `.sh` / `.ps1` / `.bat`，排除 `node_modules` / `.git` / `dist` / `__pycache__` / `.venv`）：**12 个文件、73 行命中**，不是 1 处。

分布：

| 文件 | 命中行数 |
|------|----------|
| `scripts/tests/quick_accuracy_check.py` | 16 |
| `backend/report_spec_builder.py` | 13 |
| `backend/vanna_core.py` | 12 |
| `backend/get_feishu_tables.py` | 7 |
| `backend/config_manager.py` | 5 |
| `config/run_smartask_tests.py` | 4 |
| `backend/update_dataset_config.py` | 4 |
| `backend/four_agent_ask.py` | 3 |
| `backend/start_feishu_sync.py` | 3 |
| `scripts/sync-from-expert-pack.sh` | 3 |
| `backend/update_dataset_content.py` | 2 |
| `backend/bootstrap.py` | 1（即 `:408`） |

码位频次（只报码位，不粘字符）：

```
U+274C x29   U+2705 x26   U+FE0F x11   U+26A0 x10
U+1F7E0 x4   U+1F535 x3   U+1F7E1 x3   U+1F9EA x2
U+2713 x2    U+1F534 x1   U+1F680 x1   U+1F4E1 x1
```

`backend/bootstrap.py:408` 原文：

```python
log("<U+26A0><U+FE0F> PostgreSQL 不可达，跳过迁移与首次导入；后端仍将启动以便排错。")
```

（此处以码位占位符表示，原文件中为实际字符。）

**运维影响**：不只是规范问题。

1. 这些字符全部出现在 `print` / `log` 输出中，最终进 Docker json-file 日志。容器日志在非 UTF-8 locale 的采集侧（部分日志代理、Windows 终端）会出现乱码或截断。`backend/Dockerfile` 已设 `LANG` / `LC_ALL`，容器内无碍，但日志导出后不受控。
2. `U+2705` 与 `U+274C`（共 55 处）被当作成功/失败的**状态标记**使用，这正是团队 P0 规则禁止的"emoji 作为功能图标"。日志的成功失败应该用 `[OK]` / `[FAIL]` 这类可 grep 的 ASCII 标记 —— 现在想 grep 失败行，得输入一个 emoji。`scripts/deploy/verify_deployment.py:188/202` 用的就是 `PASS` / `FAIL` 字符串，是项目内的正确示范。

**建议**：在 CI 加一条 emoji 扫描（正则覆盖 `U+1F300-U+1FAFF`、`U+2600-U+27BF`、`U+FE0F`、`U+2B00-U+2BFF`），对 `.py` / `.sh` / `.ps1` / `.bat` 命中即失败。成本 S。

---

## 10. 备份与恢复

### 10.1 实测零备份产物（P0）

```
find backups -type f   ->  文件总数 1
```

唯一文件：`backups/runtime/runtime_backup_20260708_153227.json`（10,068,478 字节，2026-07-08 15:32）—— 由 `runtime_migration` 产出，**不是 `backup.sh` 的产物**。

`backup.sh` 应产出的时间戳打包文件数量：**0**。

`du -sh backups/` = 9.6M，全部来自那一个 json。

**实测 RPO = 从未备份。RTO 无从谈起。**

### 10.2 backup.sh 永不失败

`backup.sh` 共 115 行。

`backup.sh:2`：

```
set -uo pipefail
```

**没有 `-e`**。

`|| true` 出现 **5 次**：

```
56:  } >"$BACKUP_DIR/$name.txt" 2>&1 || true
61:  tar -czf "$BACKUP_DIR/config.tar.gz" config || true
64:  tar -czf "$BACKUP_DIR/logs.tar.gz" logs || true
67:  tar -czf "$BACKUP_DIR/backend_logs.tar.gz" backend/logs || true
87:  >"$BACKUP_DIR/postgres.sql" 2>"$BACKUP_DIR/postgres_dump_error.txt" || true
```

`:86-87` 的 `pg_dump` 失败也只写错误文件，不改变退出码。

结果：**`backup.sh` 的退出码恒为 0**，无论备份是否真的产生了内容。

### 10.3 假门禁

`update.sh:494`：

```
bash "$SCRIPT_DIR/backup.sh" || fail "备份失败，已停止更新以保护生产数据"
```

这行代码的意图是对的 —— 备份失败就不许更新。但因为 10.2 的原因，`backup.sh` 永远返回 0，**这个门禁不可达**。

也就是说，`update.sh` 一直在"备份成功"的假象下执行生产更新。

### 10.4 备份范围缺口

`backup.sh:61-73` 打包范围：`config/`、`logs/`、`backend/logs/`、`.env`、`.env.example`，加 `:86-87` 的 `pg_dump`。

- `grep -cin 'chroma' backup.sh` → **0**
- `grep -cin 'chroma' restore.sh` → **0**

**ChromaDB 向量库完全不在备份与恢复范围内。** 结合 7.2（分源向量库连持久化都没有），向量库的 RPO 是无穷大：命名卷里的丢了没备份，容器可写层里的连卷都没有。

另外 `backup.sh:70` 直接 `cp .env "$BACKUP_DIR/.env"` —— 备份目录里会有一份明文密钥，而 `backups/` 是 bind mount 到容器的（`docker inspect` 实测 `./backups -> /app/backups RW`）。备份产物的权限与生命周期需要单独管理。

### 10.5 恢复能力

`restore.sh:79-125` 恢复 `config/`、`.env`、PG，不恢复 chroma。

Windows 侧：有 `backup.ps1`，**没有 `restore.ps1`**（根目录脚本清单实测：`backup.ps1` / `deploy.ps1` / `doctor.ps1` / `reset.ps1` / `update.ps1`，无 restore）。Windows 环境备份得了、恢复不了。

**从未做过恢复演练**（无演练记录文件，无相关日志；推断，未实证 —— 无法证实是否曾在别处演练）。

### 10.6 修复建议

1. `backup.sh:2` 改 `set -euo pipefail`，去掉 5 处 `|| true`，关键步骤（pg_dump）失败即非零退出。这一步做完，`update.sh:494` 的门禁自动生效。
2. 备份范围加 chroma：`docker run --rm -v smartask_chroma:/data -v $PWD/backups:/b alpine tar -czf /b/chroma.tar.gz /data`（离线备份命名卷的标准做法）。
3. `restore.sh` 同步加 chroma 恢复；补 `restore.ps1`。
4. 备份完成后加校验：`test -s postgres.sql && head -5 postgres.sql | grep -q 'PostgreSQL database dump'`，不通过即失败。
5. 定义并写进 DEPLOY.md：目标 RPO 24 小时、RTO 2 小时；每月一次恢复演练并留记录。
6. `.env` 备份单独加密或排除，`backups/` 目录权限收紧到 0700。

---

## 11. 发布与回滚

| 项 | 现状 | 证据 |
|----|------|------|
| 发布脚本 | `deploy.sh` 8 步流程 | `deploy.sh:485-562` |
| 实际发布方式 | **手工 `docker compose up`**（deploy.sh 不可用） | 容器 env 无 `SMARTASK_AI_API_KEY`；compose 标签 `config_files=...docker-compose.yml` |
| 阻断点 | `deploy.sh:508 require_env "SMARTASK_AI_API_KEY"` 对 `.env:19`（已注释）必 fail | `deploy.sh:109-114` 空值即 fail |
| Windows 侧 | `deploy.ps1:92 Test-EnvRequired -Key "SMARTASK_AI_API_KEY"` 同样 throw | 同一问题两端一致 |
| 独立 migrate 步骤 | **无** | `deploy.sh:540-546` |
| 部署自检 | 有且有效，但不可达 | `scripts/deploy/verify_deployment.py:36-46/187-191/211-212`；`deploy.sh:554` |
| 灰度 | 无 | 单副本，无流量切分能力 |
| 回滚机制 | **无** | 镜像全 `:latest`，无 tag、无 digest 记录 |
| 版本标识 | `app.py:231` 硬编码 `"version": "2.0.0"`，与 git sha 无关联 | — |
| 迁移版本管理 | 无版本表，`bootstrap.py:420` 每次启动全跑 7 个 | 靠 `IF NOT EXISTS` 幂等兜底 |
| 迁移事务 | `bootstrap.py:140 conn.autocommit = True`；`:145 _strip_transaction_keywords` 强剥 BEGIN/COMMIT | 迁移中途失败会留下半应用状态 |

### 11.1 零镜像版本化 = 零回滚能力

`docker images` 实测：

```
smartask-frontend:latest   80.4MB   8 hours ago
smartask-backend:latest    1.52GB   2 days ago
python:3.11-slim           189MB    3 weeks ago
postgres:16-alpine         420MB    7 weeks ago
```

只有 `:latest`。`deploy.sh:544` 的 `docker compose up -d --build` 会就地覆盖 `smartask-backend:latest`，**上一个版本的镜像不复存在**。

回滚只能靠 `git checkout` 旧 commit + 重新 build。这意味着：

- 回滚耗时 = 一次完整构建时间（后端镜像 1.52GB 单阶段构建，含 `build-essential` 编译，耗时不短）
- 如果旧版本依赖已从上游消失（`requirements.txt` 大量用 `>=` 而非 `==`，实测 `openai>=1.30.0`、`pandas>=2.0.0`、`requests>=2.31.0` 等 8 处），重新 build 出来的**不是原来那个版本**

**建议（成本 S，收益最高）**：`docker compose up -d --build` 前打 tag：

```
docker tag smartask-backend:latest smartask-backend:$(git rev-parse --short HEAD)
```

保留最近 5 个 tag。回滚就是改 compose 的 image 字段 + `up -d`，秒级。同时把 `app.py:231` 的 version 改为构建时注入 git sha。

### 11.2 docker/init 与 backend/migrations 双轨冗余

两套 SQL 各 6-7 个文件，内容大面积重复但不完全一致：

- `docker/postgres/init/` 独有 `002_angel_group_data.sql`
- `backend/migrations/` 独有 `20260627_ecommerce_standard_view.sql`、`20260630_dataset_transforms.sql`
- `005` / `006` 与对应 migrations 仅注释差异
- `system_event_logs` 表在 **3 处**定义：`docker/postgres/init/006_system_event_logs.sql`、`backend/migrations/20260512_system_event_logs.sql`、`backend/system_log_store.py:23-56`

新卷走 init、已有卷走 migrations，两条路径产出的 schema 不完全等价。这是第 3 节问题的结构性土壤。

**建议**：删掉 `docker/postgres/init/`，统一走 `backend/migrations/`（把 `002_angel_group_data.sql` 先迁过去），单一真相源。

---

## 12. 多端脚本一致性

根目录脚本清单实测（18 个）：

```
backup.ps1        backup.sh         check-release.sh
deploy.bat        deploy.ps1        deploy.sh
doctor.ps1        doctor.sh         reset.ps1
restore.sh        start_all.bat     start_backend.bat
start_feishu_sync.bat               start_frontend.bat
stop_all.bat      update.bat        update.ps1        update.sh
```

漂移点：

| 功能 | sh | ps1 | bat | 问题 |
|------|----|----|-----|------|
| deploy | 有 | 有 | 有 | 三套并存，`.bat` 与 `.ps1` 职责重叠 |
| backup | 有 | 有 | 无 | — |
| **restore** | **有** | **无** | 无 | **Windows 能备份不能恢复** |
| doctor | 有 | 有 | 无 | — |
| update | 有 | 有 | 有 | — |
| reset | **无** | 有 | 无 | Linux 无对应能力 |
| check-release | 有 | 无 | 无 | 仅 Linux |
| start_* | 无 | 无 | 4 个 | 仅 Windows，且是非容器化启动路径 |

`start_backend.bat` / `start_frontend.bat` / `start_feishu_sync.bat` / `start_all.bat` 是一套**绕开 Docker 的本地直起路径**。这解释了 5.1 中 `could not translate host name "smartask-postgres"` 的来源 —— 非容器上下文读 `.env:24` 拿到容器主机名，自然解析不了（推断，未实证）。

**建议**：确定唯一部署路径（容器化），把 `.bat` 直起脚本标注为"仅开发调试，不可用于生产"或直接移除；补 `restore.ps1`；`reset.sh` 与 `reset.ps1` 对齐。

---

## 13. Findings 总表

严重度 P0-P3，成本 S/M/L。

| ID | 严重度 | 类别 | 问题 | 证据 | 影响 | 修复方向 | 成本 |
|----|--------|------|------|------|------|----------|------|
| OPS-25 | P0 | 密钥泄露 | 仓库公网可匿名读取 | `git remote -v` → github.com/qishen123456/docker-setup；匿名 curl HTTP 200；`git rev-list --left-right --count` 领先/落后均 0 | 内部系统全部代码在公网 | 第 8.6 节三步处置 | L |
| OPS-26 | P0 | 密钥管理 | HEAD 上活体硬编码密钥 | `backend/get_feishu_tables.py:8`，key=app_secret，len=32，TRACKED | 飞书凭据可被任意人取走 | 改 env 读取 + 轮换 | S |
| OPS-27 | P0 | 密钥管理 | git 历史含明文凭据，`enc:v1` 命中全 0 | 见 8.2 表；清理提交 23aeea5 bytes=0 | 删文件不撤回历史 blob | 轮换 → filter-repo → 转 private | L |
| OPS-28 | P0 | 数据泄露 | 公网可见业务数据与 PII | `git ls-files config/` 10 文件；`query_history.json` 159 条；`smartask_report_history.json.bak-20260731` 8.5M，含 `185****4568` | 数据字典/权限模型/账号标识公开 | `git rm --cached` + 历史清理 | M |
| OPS-01 | P0 | 运行时 | Flask 开发服务器承载生产 | `app.py:255`；`requirements.txt` 无任何 WSGI 服务器 | 无优雅停机/无背压/无进程管理 | 第 6 节 Phase 0+1 | M |
| OPS-02 | P0 | 可观测性 | 审计日志静默失效 7 天 | `system_event_logs.jsonl` 126 条全 insert_failed，2026-07-31~08-06，x98 + x28；根因 `system_log_store.py:60-61` | 审计留痕丢失，合规风险 | 审计通道独立连接 | S |
| OPS-35 | P0 | 数据安全 | 连库账号为超级用户，SQL 黑名单可绕过 | `docker-compose.yml:8`；容器 env `SMARTASK_DB_USERNAME=postgres`；`datasources.json` 两个 PG 源 user=postgres；全仓 GRANT/CREATE ROLE 0 命中；`ask_engine_sql.py:50-67` 16 词黑名单不含 pg_read_file / pg_sleep / SELECT INTO | 任意文件读 + 实际写库 | 建只读角色 + AST 白名单 + statement_timeout | M |
| OPS-36 | P0 | Schema | 三张表不在任何声明式 schema，全新环境必缺 | migrations/init 检索 0 命中；定义仅在 `controllers/bookshelf.py:529/542/557` 等 4 个 Python 处；`docker-compose.yml:45` + `.env:12` 关闭 bundle 导入 | 全新环境带缺陷上线 | 抽 SQL 进 migrations | S |
| OPS-37 | P0 | 发布门禁 | 有效门禁挂在不可达路径后 | `verify_deployment.py:36-46` 含三表、`:211-212` 返回 1、`deploy.sh:554` 硬门禁；但 `deploy.sh:508` 卡 `.env:19`（已注释） | 门禁形同虚设 | 补 `.env` 或改文档 | S |
| OPS-30 | P0 | 备份 | 实测零备份产物 | `find backups -type f` = 1，唯一文件为 runtime_migration 产出 | RPO = 从未备份 | 见 10.6 | M |
| OPS-04 | P0 | 备份 | `backup.sh` 永不失败，`update.sh` 门禁不可达 | `backup.sh:2 set -uo pipefail`（无 -e）；5 处 `|| true`；`update.sh:494` | 在假象下执行生产更新 | `set -euo` + 去 `\|\| true` | S |
| OPS-05 | P0 | 备份 | ChromaDB 不在备份/恢复范围 | `grep -cin chroma backup.sh` = 0；restore.sh = 0 | 向量库 RPO 无穷 | 加卷备份 | S |
| OPS-03 | P1 | 发布 | 文档部署路径与实际不符（已实证） | 容器 env 无 `SMARTASK_AI_API_KEY`；compose 标签 config_files | 回滚演练基于错误前提 | 二选一收敛 | S |
| OPS-29 | P1 | 停机 | 停机宽限仅 1 秒，backend 必被 SIGKILL | 三容器 `StopTimeout=1`；backend `StopSignal=None`、`Init=None`；ExitCode 差分 137/0/0 | 每次发布硬切 SSE；PG 未来有损坏窗口 | `init: true` + `stop_grace_period: 30s` | S |
| OPS-33 | P1 | 持久化 | 分源向量库落容器可写层 | 挂载清单无 `/app/backend/chroma_db_source_*`；`datasource_router.py:214`；宿主 `ls` 无匹配 | 容器重建即丢，需重训 | 加卷或统一路径 | S |
| OPS-38 | P1 | 数据库 | 无连接池 + `ensure_schema()` 21 个请求路径调用点 | 池检索 0 命中；`psycopg2.connect` 15 处；调用点实测 28（请求路径 21）；`bookshelf_repository.py:69` `with` 不关连接、两文件 `.close()` 0 次 | 每请求额外建连开销；多 worker 后会打爆 | 连接池 + schema 探测缓存 | S |
| OPS-39 | P1 | 暴露面 | 后端 5002 与 PG 5433 直接发布到宿主 | `docker-compose.yml:14/57` | 可绕过 nginx；PG 结合超级用户风险高 | 改 `127.0.0.1:` 绑定或移除 | S |
| OPS-06 | P1 | 数据完整性 | 10MB JSON 非原子写 + 1 秒 SIGKILL | `config_manager.py:145-154`（无 os.replace/fcntl）；`config/smartask_report_history.json` 10M | 停机时截断风险 | 原子写 + flock | S |
| OPS-31 | P1 | 发布 | 无独立 migrate 步骤 | `deploy.sh:540-546` 只有 compose up + echo | schema 正确性无保障 | 加独立 migrate 阶段 | S |
| OPS-40 | P1 | 可观测性 | 健康检查为安慰剂 | `app.py:225-233` 返回固定串；`docker-compose.yml:68` 打该端点 | 故障期间健康检查全绿 | 深度 health，见 5.4 | S |
| OPS-41 | P1 | 回滚 | 零镜像版本化 | `docker images` 全 `:latest`；`deploy.sh:544 --build` 就地覆盖；`requirements.txt` 8 处 `>=` | 无法快速回滚，重建版本不可复现 | 构建打 git sha tag | S |
| OPS-32 | P2 | 一致性 | 三容器三次独立创建，compose 版本漂移 | Created 07-08/08-06T01/08-06T08；version 5.1.4 vs 5.3.0；replace 标签 | 无整栈基线，复现困难 | 一次完整重建 | S |
| OPS-34 | P2 | 资源 | 无资源限制、无日志上限 | 三容器 `Memory=0 NanoCpus=0 PidsLimit=None`、`LogOpts={}`；宿主 8.32GB/12CPU | 单容器可吃满宿主；日志撑满磁盘 | 加 limits + max-size | S |
| OPS-42 | P2 | 镜像 | 后端单阶段构建 1.52GB，root 运行 | `backend/Dockerfile` 装 build-essential 未卸、无 USER；`docker inspect` `User=[]` | 攻击面大，拉取慢 | 多阶段 + 非 root | M |
| OPS-43 | P2 | Schema | init 与 migrations 双轨，`system_event_logs` 三处定义 | `docker/postgres/init/006`、`migrations/20260512`、`system_log_store.py:23-56` | 两条路径 schema 不等价 | 删 init，单一真相源 | M |
| OPS-44 | P2 | 日志规范 | 源码 emoji 73 行 12 文件，含 55 处状态标记 | 见第 9 节分布表与码位统计 | 违反团队 P0 规则；日志不可 grep | CI 加 emoji 扫描 | S |
| OPS-45 | P2 | 日志 | 152 处裸 print，2 处 logging，无轮转无 request_id | 全域检索 | 无法结构化检索与追踪 | 见 5.4 第 1 层 | M |
| OPS-46 | P2 | 密钥 | `.secret_master_key` 权限 0644 | `ls -l config/.secret_master_key` → `-rw-r--r--`，43 字节 | 同宿主任意用户可读 | 改 0600 并迁出 config/ | S |
| OPS-47 | P2 | 多端一致性 | Windows 无 `restore.ps1`；`.bat` 提供非容器直起路径 | 根目录 18 脚本清单 | Windows 能备份不能恢复 | 补齐并标注 | S |
| OPS-48 | P3 | 迁移 | 无版本表，每次启动全跑；autocommit 剥离事务 | `bootstrap.py:420`、`:140`、`:145` | 中途失败留半应用状态 | 引入版本表 | M |
| OPS-49 | P3 | 配置 | 业务表建在 `postgres` 维护库 | 容器 env `SMARTASK_DB_DATABASE=postgres` | 与系统库混用 | 建独立库 | M |

P0 合计 **11 条**，P1 **9 条**，P2 **8 条**，P3 **2 条**。

---

## 14. Baseline Review（对既有结论的更正）

### 14.1 对总监提供数据的更正

| 项 | 原述 | 实测 | 依据 |
|----|------|------|------|
| `_is_read_only_sql` 黑名单词数 | 14 个 | **16 个** | `ask_engine_sql.py:61-65` |
| `ensure_schema()` 调用点 | 22 个 | **28 个**（请求路径 21） | 全域检索，遗漏 `system_log_store.py` 6 处 |
| 源码 emoji | `bootstrap.py:408` 全仓唯一 | **12 文件 73 行** | 第 9 节 |
| 三张表的建表路径 | 唯一定义处为 `bookshelf.py:526-570` | 共 **4 处**，另有 `import_bookshelf_bundle.py:42/55/70` 等；但后者被 `SKIP_FIRST_IMPORT=1` 默认关闭 | 第 3.2/3.3 节 |

上述更正不改变总监结论的方向，只是把边界划准。其中 `system_log_store.py` 那 6 个调用点值得单独看 —— 它在 after_request 路径上，是频率最高的那一类。

### 14.2 对我上一轮结论的更正

| 项 | 上一轮 | 本轮 |
|----|--------|------|
| 部署路径断裂 | 标注「推断」 | **已实证**（容器 env 无 AI Key + compose 标签），去掉推断标记 |
| ChromaDB 备份 | 仅指出不在备份范围 | 扩大：分源向量库连持久化都没有（OPS-33） |
| 密钥审计范围 | 只查工作区文件 | **漏了 git 历史与远程可达性**，这是我的盲点，本轮补上，且严重度高于我上一轮列的任何一条 |
| stop_grace_period | 仅指出 compose 未配 | 量化为 `StopTimeout=1` 秒，且 postgres 同样只有 1 秒，风险面更宽 |
| backup.sh | 机制推断「永不失败」 | 结果实证：产物为 0 个文件 |

### 14.3 对基线报告的纠正（沿用上一轮）

基线称 `feishu_sync.py:214/267` 线程缺 `daemon=True` 导致无法优雅退出。实测 `backend/controllers/feishu_sync.py:215` 与 `:268` 明确写了 `thread.daemon = True`，归因错误。

真因是 `bootstrap.py:454` 的 `os.execv` 让 python 成为 PID 1，PID 1 默认忽略 SIGTERM，全仓零 signal handler。差分证据见 OPS-29。

---

## 15. 盲点清单

以下问题在既有基线报告中未被覆盖，本次审计新增：

1. 审计日志已静默失效 7 天，且**没有任何机制会发现它**（健康检查不查、无告警）。
2. `backup.sh` 是假门禁，`update.sh:494` 一直在假象下放行生产更新。
3. `verify_deployment.py` 是**有效**门禁却不可达 —— 这类"防线存在但被前置故障屏蔽"的模式，比"没有防线"更危险，因为它会给人已有保障的错觉。
4. `auth_tokens.json`（`auth_store.py:20`）是多 worker 迁移中被漏掉的第二个阻塞项，第一个是 `_pending_confirmations`。
5. 零镜像版本化 —— 回滚能力实际为零，而不是"回滚慢"。
6. 分源向量库 RPO 无穷（既不备份也不持久化）。
7. 前端存在三套包管理器痕迹（`frontend/Dockerfile` 用 pnpm 且 `rm -f pnpm-workspace.yaml`、`--no-frozen-lockfile`），构建不可复现（属前端域，仅记录）。
8. `docker/postgres/init/` 与 `backend/migrations/` 双轨冗余是 Schema 问题的结构性土壤。
9. Windows 无 `restore.ps1`。
10. 零 RTO / RPO 定义，无恢复演练记录。
11. 后端 5002 与 PG 5433 直连宿主，nginx 不构成边界。
12. `.bat` 直起脚本是绕开容器的第二条运行路径，与 `.env` 中的容器主机名冲突，很可能是审计日志 x28 类错误的来源。
13. `SELECT ... INTO` 可绕过只读校验实际写库 —— 这条使"只读"在语法层就不成立，而不只是"黑名单不全"。

---

## 16. 生产就绪档位判定

知识库记分卡文件 `references/01-standards/production-readiness-scorecard.md` 在本机与项目内均不存在（已检索），故按自有基线判定。

| 维度 | 档位 | 依据 |
|------|------|------|
| 运行时形态 | Bronze 以下 | 开发服务器 + 无优雅停机 |
| 容器与编排 | Bronze | 无资源限制、root 运行、无版本化 |
| 可观测性 | Bronze 以下 | 审计日志已坏 7 天无人知 |
| 配置与密钥 | **不入档** | 凭据在公网可取 |
| 备份与恢复 | **不入档** | 实测零备份产物 |
| 发布与回滚 | Bronze 以下 | 无回滚能力，发布路径与文档不符 |
| 多端一致性 | Bronze | Windows 恢复能力缺失 |

**总档（取各维最低）：不入档。**

一个凭据在公网可取、且从未产生过任何备份的系统，谈不上生产就绪档位。建议在 OPS-25/26/27/28（密钥与数据泄露）与 OPS-30/04/05（备份）处置完成前，不讨论上线、扩容或推广议题。

---

## 17. 建议动手顺序

按"止血 → 恢复能力 → 正确性 → 长期"排列。前六项约 3 天可完成，做完后总档可脱离"不入档"进入 Bronze，再补 Phase 1 与可观测性第 1 层可达 Silver（推断，未实证 —— 无标准记分卡可对照）。

| 序 | 动作 | 对应 ID | 成本 | 前置 |
|----|------|---------|------|------|
| 1 | 轮换全部已泄露凭据（AI Key / 库密码 / 飞书 secret / 管理员口令） | OPS-25/26/27 | M | 无 |
| 2 | 仓库转 private，`config/` 10 文件 `git rm --cached` | OPS-25/28 | S | 1 |
| 3 | `backup.sh` 改 `set -euo pipefail` + 去 5 处 `\|\| true` + 加 chroma + 加校验 | OPS-04/05/30 | S | 无 |
| 4 | compose 加 `init: true` / `stop_grace_period: 30s` / `logging.max-size` / `resources.limits` | OPS-29/34 | S | 无 |
| 5 | 审计日志改独立连接，脱离业务数据源 | OPS-02 | S | 无 |
| 6 | 三张表 DDL 抽进 `backend/migrations/` 并加入 `MIGRATIONS` | OPS-36 | S | 无 |
| 7 | 建 PG 只读角色，业务查询与元数据库账号分离 | OPS-35 | M | 1 |
| 8 | 构建打 git sha tag，保留最近 5 版 | OPS-41 | S | 无 |
| 9 | 补 `.env:19` 或改 DEPLOY.md，让 `deploy.sh` 与 `verify_deployment.py` 门禁生效 | OPS-03/37 | S | 1 |
| 10 | 连接池 + `ensure_schema()` 进程内缓存 | OPS-38 | S | 无 |
| 11 | 端口绑定收到 `127.0.0.1:` | OPS-39 | S | 无 |
| 12 | Phase 1：换 gunicorn gthread 单进程 | OPS-01 | M | 4 |
| 13 | 可观测性第 1 层：request_id + 深度 health + metrics | OPS-40/45 | M | 5 |
| 14 | 可观测性第 2 层：watch.sh + 飞书告警 | OPS-02/40 | S | 13 |
| 15 | git 历史 filter-repo 清理 + pre-commit gitleaks + CI emoji 扫描 | OPS-27/44 | L | 1,2 |
| 16 | `config_manager.write_json` 改原子写 + flock | OPS-06 | S | 无 |
| 17 | 后端镜像多阶段 + 非 root | OPS-42 | M | 8 |
| 18 | 删 `docker/postgres/init/`，统一 migrations | OPS-43 | M | 6 |
| 19 | 补 `restore.ps1`，标注 `.bat` 直起脚本用途 | OPS-47 | S | 3 |
| 20 | Phase 2 状态外置（7 项） | OPS-01 | L | 12 |

Phase 3（多 worker）暂不排期，理由见 6.5。

---

## 附录 A：本次实际执行的取证命令清单

只读命令，按执行顺序，可复现：

```
git log -1 --format='%h %ad %s' --date=short
git remote -v
git rev-list --all --count
git branch -r
git branch -a --contains <sha>
git ls-files config/
git ls-files --error-unmatch <path>
git ls-tree -r --name-only <sha>
git show <sha>:<path>
git rev-list --left-right --count origin/docker-setup...HEAD
curl -s -o /dev/null -w '%{http_code}' -m 12 https://github.com/qishen123456/docker-setup
docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Image}}'
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'
docker inspect smartask-backend smartask-frontend smartask-postgres
docker volume ls
docker info --format 'Driver={{.Driver}} ... Mem={{.MemTotal}} CPUs={{.NCPU}}'
find backups -type f
du -sh backups/
ls -l config/.secret_master_key
wc -l <file>
grep -n / grep -rn / grep -c（多处，详见正文各节）
python3（JSON 结构解析、emoji 码位统计、密钥字段计数 —— 均只输出计数与长度）
```

未执行：`docker build` / `docker compose up|down|restart|stop|start` / `docker exec` / `docker run` / 任何写文件操作（`docs/audit/` 除外）/ 任何数据库连接。

## 附录 B：密钥处理声明

本报告涉及密钥的全部位置，一律只记录：文件路径、行号、字段名、值长度、是否加密前缀、是否被版本库跟踪。

**全文未输出任何密钥、口令、令牌的实际值。** git 历史核查采用"按提交统计非空密钥字段数量"的方式，未打印任何 blob 内容。手机号形态的账号标识统一脱敏为 `185****4568`。
