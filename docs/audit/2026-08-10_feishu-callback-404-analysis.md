# 飞书网页登录回调 404「页面不存在」根因分析

- 日期：2026-08-10
- 现象：部署到 `https://bifine.angelgroup.com.cn:10899/smart-ask` 后，点「使用飞书组织身份登录」→ 飞书授权后浏览器被重定向到
  `https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/callback?code=...&state=...`
  页面停在**登录界面**并显示「页面不存在」（Vue 的 404 兜底页），无法进入系统。
- 结论：**SmartAsk 代码本身没有问题，缺陷在部署用的反向代理（外部 Nginx）没有把 `/smart-ask/api/...` 正确转发到后端**，回调请求落到了前端 SPA 兜底页。另外发现一个紧跟其后的二级缺陷（回跳地址默认值错误）。

---

## 1. 已验证：代码侧是正确的

| 检查项 | 位置 | 结论 |
|---|---|---|
| 飞书回调路由存在 | `backend/controllers/auth.py:822` `@auth_bp.route("/api/auth/feishu/callback")` | ✅ 路由存在 |
| 子路径前缀处理 | `backend/app.py:78-97` `PrefixMiddleware`，`BASE_PATH` 非空时自动剥离 `/smart-ask` | ✅ 配置正确即可命中 |
| 蓝图注册（无多余前缀） | `backend/app.py:118` `app.register_blueprint(auth_bp)` | ✅ 裸 `/api/...` |
| 前端 SPA 兜底 | `frontend/nginx.conf:37-41` `location / { try_files $uri $uri/ /index.html; }` | ⚠️ 会把未匹配的请求吐回 `index.html` |
| 前端路由 base | `frontend/src/router/index.js:130` `createWebHistory()`（无 base，根级），兜底 `NotFound`（`:122-125`，meta 标题「页面不存在」） | ⚠️ 根因之一 |
| 前端构建 base | `frontend/vite.config.js:13` `base: process.env.BASE_PATH || '/'`（`/smart-ask/`） | ⚠️ 决定静态资源与 SPA 挂载点 |

---

## 2. 根因一（导致当前症状）：反向代理未剥离 `/smart-ask` 前缀，回调请求命中前端 SPA

### 链路还原
浏览器地址 = `...:10899/smart-ask/api/auth/feishu/callback`。要让后端命中该路由，请求必须**最终**以 `/api/auth/feishu/callback` 的形式到达 Flask（要么外部 Nginx 直接剥离前缀转发给后端，要么前端容器再剥离一次）。

但部署架构是：**外部 Nginx（`bifine.angelgroup.com.cn:10899` 的 `/smart-ask`）→ Docker 服务**（backend:5002、frontend:8888→容器:80）。Docker 内部的前端容器用的 `frontend/nginx.conf` 只有**根级**两条规则：
- `location /api/ { proxy_pass http://backend:5002/api/; }` ← 只在路径以 `/api/` 开头时生效
- `location / { try_files ... /index.html; }` ← SPA 兜底

如果外部 Nginx 把 `/smart-ask/`（或 `/smart-ask/api/`）**带着 `/smart-ask` 前缀**转给前端容器（例如 `proxy_pass http://frontend:8888;` 或 `.../smart-ask/`），那么前端容器收到的是 `/smart-ask/api/auth/feishu/callback`——它**不匹配** `location /api/`，于是落入 `location /` 的 SPA 兜底，返回 `index.html`。

`index.html` 加载 Vue 后，`createWebHistory()`（根级 base）看到完整路径 `/smart-ask/api/auth/feishu/callback`，没有任何路由匹配 → 命中 catch-all `NotFound` → 显示「页面不存在」。这与用户看到的现象**完全一致**。

> 一句话：回调请求没进后端，被前端 SPA 兜底吃掉了。

### 正确的反向代理配置（二选一，推荐 A）

**方案 A（推荐，与仓库 `docker-compose.proxy.yml` 注释一致，补全即可）：外部 Nginx 把 `/smart-ask/api/` 直接剥离前缀转发给后端**

```nginx
# 飞书回调 / 所有后端 API：剥离 /smart-ask 前缀
location /smart-ask/api/ {
    proxy_pass http://<backend-host>:5002/api/;   # 末尾 /api/ 会把 /smart-ask/api/ 重写成 /api/
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /smart-ask;   # 重要：供后端拼接回跳地址
    proxy_buffering off;          # SSE 支持
    proxy_read_timeout 300s;
}

# 前端静态资源 / SPA
location /smart-ask/ {
    proxy_pass http://<frontend-host>:8888/;   # 末尾 / 剥离 /smart-ask
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

**方案 B（备用）：外部 Nginx 只转发 `/smart-ask/` 到前端容器并剥离前缀，由前端容器自己的 `location /api/` 二次转发给后端**
```nginx
location /smart-ask/ {
    proxy_pass http://<frontend-host>:8888/;   # 末尾 / 剥离 /smart-ask
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```
此方案下 `/smart-ask/api/...` → 前端容器收到 `/api/...` → 命中 `location /api/` → 后端。同样可用。

> 注意：仓库自带 `nginx/nginx.prod.conf` 是**根路径**部署配置（无 `/smart-ask`），不适用于当前 `/smart-ask` 子路径场景；当前生效的是你服务器上的**外部 Nginx**。

---

## 3. 根因二（路由修好后立刻暴露）：回跳地址默认值错误

`backend/controllers/auth.py:59`：
```python
"frontend_url": _env("FRONTEND_URL", "SMARTASK_FRONTEND_URL", default="http://localhost:5173").rstrip("/"),
```
回调成功后（`auth.py:844-854`）用它拼 `redirect_target = f"{frontend_url}/?token={session_token}"`。由于默认值**永远非空**（`http://localhost:5173`），下面的 `if not frontend_url:` 兜底（读 `X-Forwarded-*` 自动推断）**是死代码**，生产环境只要没显式设置 `SMARTASK_FRONTEND_URL`，登录成功后浏览器会被重定向到**用户本机的 `http://localhost:5173`**，而不是线上地址。

### 修复（配置优先，无需改代码）
在后端环境变量（`.env`）中显式设置：
```
SMARTASK_FRONTEND_URL=https://bifine.angelgroup.com.cn:10899/smart-ask
```
这样回跳目标 = `https://bifine.angelgroup.com.cn:10899/smart-ask/?token=...`，正确进入系统。

> 代码侧建议（可选，留待后续）：把 `auth.py:59` 的默认值从 `http://localhost:5173` 改为 `""`，让 `X-Forwarded-Prefix` 兜底真正生效，避免同类误配置再次踩坑。

---

## 4. 在服务器上自证（不改任何代码）

```bash
# 1) 看 API 是否真的到了后端（应返回 JSON，含 "url" 字段）
curl -sS -i "https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/login-url"

# 2) 看回调是否到了后端（应返回 HTML "登录成功，正在跳转..." 或 JSON，而不是 SPA 的 index.html）
curl -sS -i "https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/callback?code=test&state=test"
```
- 若返回内容里出现 `<div id="app">` 或「页面不存在」→ 证实命中前端 SPA（根因一）。
- 若返回 JSON 错误（如「缺少飞书 OAuth code」）→ 后端已命中，根因一已排除，问题只在根因二。

---

## 5. 下一步

1. 先按第 4 节在服务器上跑两条 `curl` 确认根因一是否命中。
2. 按第 2 节修正外部 Nginx（推荐方案 A），重载 Nginx。
3. 按第 3 节在 `.env` 设置 `SMARTASK_FRONTEND_URL`，重启后端容器。
4. 重走飞书登录流程验证。

## 6. 用户提供实际 Nginx 配置复核（2026-08-10 更新）

用户提供了实际生效的 Nginx（`bifine.angelgroup.com.cn:10899`，`listen 10899 ssl`）：

- `location ^~ /smart-ask/api/ { proxy_pass http://127.0.0.1:5002/api/; ... }` —— **正确**。匹配前缀 `/smart-ask/api/` 被 `proxy_pass` 末尾的 `/api/` 替换为 `/api/`，回调最终以 `/api/auth/feishu/callback` 到达后端，路由可命中。
- `location ^~ /smart-ask/ { proxy_pass http://127.0.0.1:8888/; rewrite ^/smart-ask/(.*)$ /$1 break; ... }` —— 负责前端 SPA（注意：`try_files` 在此为冗余且略危险——nginx 级 `try_files` 的兜底 `/index.html` 指向本机文件，代理失败时反而 404；SPA 兜底已由前端容器自身处理，建议删掉这行）。

**结论修正**：第 2 节担心的「反向代理未剥离前缀 → 命中 SPA」在用户这份配置下**不成立**（API 路由正确）。因此若当前仍看到 SPA 的「页面不存在」，最可能是这份 Nginx **尚未 `reload` / 尚未生效**（旧配置仍把回调送到了前端），请先 `nginx -t && nginx -s reload` 后再用第 4 节 curl 自证。

**真正会阻断登录完成的 bug 仍是第 3 节的 `localhost:5173` 默认值**：即便 Nginx 正确，回调成功后后端会把浏览器重定向到 `http://localhost:5173/?token=...`（本机 5173，而非线上地址），导致"登录完却没进系统"。必须设置 `SMARTASK_FRONTEND_URL`。

> 未改动任何 SmartAsk 源码（按用户要求先分析）。修复均为**部署侧**操作（Nginx reload + 环境变量）。
> 若 curl 自证后确认是 `localhost:5173` 回跳问题，可后续顺手把 `auth.py:59` 默认值改为 `""` 让 `X-Forwarded-Prefix` 兜底生效（代码侧加固）。

## 7. 用户提供实际 .env 复核（2026-08-10）
- `FRONTEND_URL` / `BACKEND_URL` 均已设为 `https://bifine.angelgroup.com.cn:10899/smart-ask` → 第 3 节的 `localhost:5173` 回跳坑**在本 .env 下不存在**，无需再加 `SMARTASK_FRONTEND_URL`（代码优先读 `FRONTEND_URL`）。
- **真实 .env 缺陷**：末尾 `SMARTASK_ADMIN_DISPLAY_NAME=超级管理员PUBLIC_PROTOCOL=https` 两行被合并，导致 `PUBLIC_PROTOCOL` 未生效。须拆成两行：`SMARTASK_ADMIN_DISPLAY_NAME=超级管理员` 与 `PUBLIC_PROTOCOL=https`。
- 另存在两套飞书凭证：`FEISHU_*`(cli_a970...) 与 `SMARTASK_FEISHU_*`(cli_a94a...)，`_feishu_config` 优先取 `FEISHU_*`，需确认该 app 在飞书开放平台登记的 redirect_uri 正是 `https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/callback`。
- 结论：本 nginx + 本 .env 理论上回调可通；若仍「页面不存在」，多半是配置未 reload（nginx -s reload + 重启后端容器加载 .env），用第 4 节 curl 自证。

## 8. 二级缺陷发现：后端回跳路径与前端 token 消费路由不匹配（2026-08-10）

- 复核前端路由与 token 消费点后发现：即便 Nginx 正确、回调请求到达后端并鉴权成功，登录仍**无法完成**——存在第二处缺陷。
  - 后端 `auth.py:854` 回调成功后拼：`redirect_target = f"{frontend_url}/?token={session_token}"` → 浏览器被重定向到 `{frontend_url}/?token=...` = `https://bifine.angelgroup.com.cn:10899/smart-ask/?token=...`
  - 但前端**只在路由 `/auth/callback`** 消费 token：
    - `frontend/src/router/index.js:44` 注册 `path: '/auth/callback'` → 实际 URL = `/smart-ask/auth/callback`（router base 为 `/smart-ask/`）
    - `frontend/src/views/AuthCallback.vue:21` 通过 `route.query.token` 读取并 `setAuthToken` 写入 localStorage，随后 `window.location.replace('/smart-ask')`（:27，绝对路径，与本部署子路径一致）
  - 主视图 `SmartAsk.vue`、根组件 `App.vue`、`main.js`、路由守卫（`router/index.js` 仅有 `afterEach` 设标题，无 `beforeEach`）**均不读取 URL 中的 `?token`**。
  - 因此重定向到 `/smart-ask/?token=...` 后，token 被丢弃，用户停在登录态之外（不会"页面不存在"，但也不会登录成功，等于"登录完没进去"）。
- 症状映射：
  - **Bug A（部署）**：回调请求没进后端 → 浏览器停在 `/smart-ask/api/auth/feishu/callback` 显示「页面不存在」（用户当前现象）。
  - **Bug B（代码）**：后端回跳路径 `/?token` 与前端 token 路由 `/auth/callback` 不匹配 → 即便 A 修好，登录仍无法完成。
- 修复（需改代码，待用户批准，遵循"先不动代码"）：将 `auth.py:854` 改为
  `redirect_target = f"{frontend_url}/auth/callback?token={session_token}"`，使其命中前端 `AuthCallback` 路由。`AuthCallback.vue:27` 的绝对路径 `/smart-ask` 无需改。

## 9. 修复清单（按优先级）

1. **[必做/部署] Bug A**：`nginx -t && nginx -s reload` 让 `/smart-ask/api/` 真正转到后端；重启后端容器加载 .env。用第 4 节两条 curl 自证。
2. **[必做/代码] Bug B**：改 `auth.py:854` 回跳到 `/auth/callback?token=...`（待批准）。
3. **[建议/.env]** 拆分末尾合并行 `SMARTASK_ADMIN_DISPLAY_NAME=超级管理员PUBLIC_PROTOCOL=https` → 两行（注：`PUBLIC_PROTOCOL` 后端未读取，属死配置，但 `SMARTASK_ADMIN_DISPLAY_NAME` 被污染，须拆干净）。
4. **[确认/飞书后台]** `FEISHU_*`(cli_a970...) 在开放平台登记的 redirect_uri 须为 `https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/callback`。
5. **[可选/Nginx]** 删掉 `location ^~ /smart-ask/` 里的 `try_files $uri $uri/ /index.html;`（冗余且危险）。

## 10. 本地 ngrok 根路径 vs 公网 /smart-ask 子路径（2026-08-10 23:22，关键转折）

用户回忆本地 ngrok 方案（已验证能跑通）：单端口暴露前端 8888，`BASE_PATH` 空，`FRONTEND_URL`/`BACKEND_URL`=ngrok 根域名，前端容器内部 nginx `location /api/`→backend:5002、`location /`→SPA。**根路径模式**。

### 两种模式的架构差异

| 维度 | 本地 ngrok（能跑通） | 公网 bifine（页面不存在） |
|---|---|---|
| BASE_PATH | 空 | `/smart-ask` |
| 前端 router base | `/`（vite base=BASE_PATH=`/`） | `/smart-ask/` |
| nginx 层数 | 单层（前端容器内部） | 两层（外部 nginx 剥前缀 + 前端容器内部） |
| 前缀剥离责任 | 无前缀 | 外部 nginx 剥离（`proxy_pass .../api/`） |
| 前端 base 来源 | **构建时** `vite.config.js:13 base=BASE_PATH` | 同左，构建时定 |

**关键**：前端 base 是**构建时**由 `BASE_PATH` 决定的，运行时改 `.env` 的 BASE_PATH 对前端静态资源路径与 router base **无效**。公网若用 base=`/` 的前端镜像部署在 `/smart-ask` 下，静态资源与路由全错位 → "页面不存在"。

### PrefixMiddleware 幂等性（app.py:84-91）

```python
if path.startswith(self.prefix):   # 只在路径真带前缀时才剥离
    environ['PATH_INFO'] = path[len(self.prefix):] or '/'
```
外部 nginx 已剥离前缀时，Flask 收到的路径无 `/smart-ask`，`startswith` 为 False，**不剥离、不报错**。故公网后端路由能命中（前提：nginx reload 生效）。**不会双重剥离出错**。

### Bug B 在两种模式下都存在

- 根路径模式：后端回跳 `{frontend_url}/?token` → URL `/` → router `{path:'/', redirect:'/smart-ask'}` → `/smart-ask?token` → SmartAsk 视图**不读 token**。
- 子路径模式：回跳 `/smart-ask/?token` → URL 去 base → `/` → 同上 redirect → SmartAsk 不读 token。
- 唯一读 token 的是 `/auth/callback` 路由（`AuthCallback.vue:21`）。后端回跳 `/?token` 永远到不了 `/auth/callback`。
- **推论**：若用户本地"完美正常工作"指的是飞书**网页 OAuth** 登录，则与代码矛盾，需复核（可能本地测的是密码登录或飞书**内嵌**登录 `/api/feishu/auth`，那条路 `utils/feishu.js` 走 JSON 不走回跳）。若如此，网页 OAuth 回调这条路**从未端到端跑通**，Bug B 是真 bug。

### 两条修复路

**路 A（推荐，最省事）——公网也用根路径，复用本地 ngrok 架构**
- 前提：`bifine:10899` 端口能给 smartask 独占（不与其他服务共享 `/smart-ask`）。
- 外部 nginx：
  ```nginx
  location /api/ { proxy_pass http://127.0.0.1:5002/api/; ... }
  location / { proxy_pass http://127.0.0.1:8888/; ... }
  ```
- `.env`：`BASE_PATH=`（空），`FRONTEND_URL`/`BACKEND_URL`=`https://bifine.angelgroup.com.cn:10899`（无 `/smart-ask`）。
- 前端用 `BASE_PATH` 空**构建**（base=`/`）。
- 飞书 redirect_uri = `https://bifine.angelgroup.com.cn:10899/api/auth/feishu/callback`。
- 收益：避开子路径三层前缀坑（Bug A 不触发），架构与本地 ngrok 完全一致。Bug B 仍需修（auth.py:854 → `/auth/callback?token`），但子路径相关的所有部署坑全部消失。

**路 B——必须用 /smart-ask 子路径时**
- 前端用 `BASE_PATH=/smart-ask` **重新构建**镜像（关键，运行时改无效）。
- 外部 nginx `nginx -t && nginx -s reload`（修 Bug A）。
- `auth.py:854` 改 `redirect_target = f"{frontend_url}/auth/callback?token={session_token}"`（修 Bug B）。
- 飞书 redirect_uri = `https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/callback`。
- 后端 BASE_PATH 设 `/smart-ask`（PrefixMiddleware 幂等，安全）。

> 决策点：`bifine:10899` 是否 smartask 独占？独占走路 A；必须共享子路径走路 B。

## 11. Bug B 回归根因确认（2026-08-10 23:22，决定性证据）

git 历史对比三个版本的飞书回调回跳路径：

| 版本 | 时间 | 回跳路径 | 状态 |
|---|---|---|---|
| `8f93361`（老代码，**本地容器跑的**） | 08-10 早 | `redirect(f"{frontend_url}/auth/callback?token=...")` | ✅ 正确，命中前端 AuthCallback |
| `54802b79`（"彻底修复飞书回调跳转"） | 08-10 17:07 | `redirect_target = f"{frontend_url}/?token=..."` | ❌ **回归**——把 `/auth/callback` 改成 `/?token` |
| `64016a15`（HEAD） | 08-10 17:25 | `f"{frontend_url}/?token=..."` + X-Forwarded 兜底 | ❌ 延续回归 |

### 链路还原

- 用户本地容器是 **24 小时前**（08-09 晚）起的，跑 `8f93361` 老代码，回跳 `/auth/callback?token` → 前端 `AuthCallback.vue:21` 读 `route.query.token` → 写 localStorage → 登录成功。**网页 OAuth 端到端跑通**。
- 08-10 17:07 提交 `54802b79` 标题"彻底修复飞书回调跳转问题"，实际把回跳从 `/auth/callback` 改成 `/?token`。开发者本意是兼容反向代理子路径，但**改错了路径**——前端 token 消费点仍在 `/auth/callback`（`router/index.js:44`），`/?token` 永远到不了那里。这是典型的"修一个问题引入另一个"。
- 公网若用 17:07 之后构建的镜像，就吃到这个回归 → Bug B 触发 → 登录完进不去系统。叠加 Bug A（nginx 未 reload）→ 当前"页面不存在"。

### 修复（恢复老代码正确路径，保留新兜底）

`backend/controllers/auth.py:854`：
```python
# 当前（回归）:
redirect_target = f"{frontend_url}/?token={session_token}"
# 修复（恢复 8f93361 的正确路径，保留 64016a15 的 X-Forwarded 兜底拼 frontend_url）:
redirect_target = f"{frontend_url}/auth/callback?token={session_token}"
```

- 根路径模式（路 A）：`frontend_url=https://bifine...:10899` → 回跳 `.../auth/callback?token` → router base=`/` → 命中 `/auth/callback` → ✅
- 子路径模式（路 B）：`frontend_url=https://bifine...:10899/smart-ask` → 回跳 `.../smart-ask/auth/callback?token` → router base=`/smart-ask/` → 去 base 得 `/auth/callback` → ✅

**两种模式都通**，且是恢复老代码的正确行为，风险极低。

### 最终方案

用户确认 `bifine:10899` 端口 smartask 独占（域名不独占）→ **走路 A（根路径）+ 修 Bug B**：
1. 公网外部 nginx 改根路径：`location /api/`→backend、`location /`→frontend，`BASE_PATH` 空，前端 base=`/` 构建，飞书 redirect_uri=`https://bifine...:10899/api/auth/feishu/callback`。
2. `auth.py:854` `/?token` → `/auth/callback?token`（修 Bug B，恢复老代码）。
3. 路 A 下 Bug A（子路径前缀）自动消失，无需处理。

## 12. 修复完成 + QA 独立验证 PASS（2026-08-10 23:34，BugFix 团队流程）

- **工程师寇豆码**修复 `auth.py:854`：`/?token` → `/auth/callback?token`。`git diff HEAD` 确认**仅 1 行变动**，无夹带、无格式调整、无重构。下游 HTML 模板（856-873 `{redirect_target}` 占位）未改；全后端 grep 确认只有这一处重定向构造点。
- **QA 严过关**独立验证 **PASS**：改动正确、最小、两种模式逻辑通、其他分支（830-833 缺 code/state 校验、838-840 账号停用、875-877 except）未动。无相关单测（`backend/tests/` 24 个文件无飞书回调重定向覆盖），以静态验证为主。路由决策 NoOne，可合入。
- git 溯源独立核实：`8f93361`(`/auth/callback?token`) → `54802b7`(改为 `/?token`，**引入回归**) → `HEAD`(`/?token`) → 工作区修复(`/auth/callback?token`)。工程师叙事准确。修复保留了 54802b7 的 HTML 跳转页机制（兼容反代+手动点击兜底），仅修正路径后缀，未回退到 8f93361 的纯 302，最小且合理。

### router base 澄清（QA fresh-eyes，修正第 10 节表述）
- `router/index.js:130` 为 `createWebHistory()`**无 base 参数** → Vue Router 4 下 router base 恒为 `/`。
- 第 10 节"子路径模式 router base=/smart-ask/"系对机制的误述。实际：子路径模式能通是因为**外部 nginx 已剥离 /smart-ask 前缀**，前端容器始终收到根相对路径（如 `/auth/callback`），router base=`/` 反而正确且自洽。
- `vite.config.js:13 base=BASE_PATH` 只影响**浏览器侧静态资源 URL 前缀**（让 `/smart-ask/assets/...` 命中外部 nginx 的 `/smart-ask/` location），与 router base 无关。
- **结论不变**：路 A（根路径）前端镜像须用 `BASE_PATH` 空构建（vite base=`/`，匹配外部 nginx `location /`）；路 B（子路径）前端镜像须用 `BASE_PATH=/smart-ask` 构建（vite base=`/smart-ask/`，匹配外部 nginx `location /smart-ask/`）。

### 遗留（部署侧，非本次代码引入，非阻塞）
1. 子路径模式依赖外部 nginx 正确剥离前缀（即 Bug A），与本次一行修复无关。
2. `AuthCallback.vue:27/33` 登录后落地用硬编码 `window.location.replace('/smart-ask')`（根路径/子路径模式均可用，未改）。
3. 飞书登录回调重定向链路无自动化测试覆盖，依赖静态验证 + 部署后手工验证。

> 代码侧已就绪。待用户在服务器配置路 A（nginx 根路径 + .env + 前端 `BASE_PATH` 空重建镜像 + 飞书 redirect_uri 去掉 `/smart-ask`）后端到端验证。
