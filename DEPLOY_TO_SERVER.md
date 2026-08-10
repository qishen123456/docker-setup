# SmartAsk 服务器部署完整指南（超详细版）

> **公网地址：** `https://bifine.angelgroup.com.cn:10899/smart-ask`
>
> **架构：** 外部Nginx/负载均衡 → Docker容器（外部代理模式）
>
> **适用场景：** 已有外部Nginx/负载均衡处理HTTPS和端口映射的服务器环境

---

## 🚀 快速导航（不知道看哪里？点这里！）

### 你是哪种用户？

| 你的情况 | 推荐阅读 | 预计时间 |
|---------|---------|----------|
| **第一次部署，完全不懂Linux** | 👉 [**DEPLOY_QUICK.md**](./DEPLOY_QUICK.md) （5分钟快速上手版） | 5-10分钟 |
| **想快速知道.env怎么写、Nginx怎么配** | 👉 直接跳到 [**三、.env 配置完全指南**](#-env-配置完全指南每个配置项都讲清楚) 和 [**四、Nginx 配置完全指南**](#-nginx-配置完全指南可直接复制使用) | 10-15分钟 |
| **日常更新代码和运维** | 👉 [**QUICK_START_GUIDE.md**](./QUICK_START_GUIDE.md) （小白完全手册） | 先收藏，用的时候查 |
| **遇到问题需要排查** | 👉 直接跳到 [**八、故障排查速查表**](#-故障排查速查表快速定位问题) | 按需查阅 |
| **想了解所有技术细节** | 👉 继续阅读本文档（从上到下） | 30-60分钟 |

### 最常用的3个章节（直接点击跳转）

1. **[📝 .env 配置完全指南](#-env-配置完全指南每个配置项都讲清楚)** - 包含完整的配置示例，可直接复制修改
2. **[🔧 Nginx 配置完全指南](#-nginx-配置完全指南可直接复制使用)** - 包含完整的Nginx配置文件，可直接使用
3. **[🆘 故障排查速查表](#-故障排查速查表快速定位问题)** - 各种问题的快速解决方案

### 📚 文档体系总览

```
SmartAsk 部署文档体系
├── DEPLOY_QUICK.md          ← 新手从这里开始！（5分钟版）
├── QUICK_START_GUIDE.md     ← 日常运维手册（小白友好）
├── DEPLOY_TO_SERVER.md      ← 完整部署指南（本文档，最详细）
└── .env.example             ← 配置文件模板（可直接复制）
```

---

## 📖 详细目录

1. [架构理解](#-架构理解)
2. [完整部署流程](#-完整部署流程从零开始)
3. [.env 配置完全指南](#-env-配置完全指南每个配置项都讲清楚)
4. [Nginx 配置完全指南](#-nginx-配置完全指南可直接复制使用)
5. [飞书 OAuth 配置](#-飞书-oauth-配置必须更新)
6. [部署验证清单](#-部署验证清单逐一确认)
7. [常用运维命令](#-常用运维命令日常必备)
8. [故障排查速查表](#-故障排查速查表快速定位问题)

---

## 📋 架构理解

### 你的部署架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
│         https://bifine.angelgroup.com.cn:10899/smart-ask/    │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS :10899
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              外部 Nginx / 负载均衡（已存在）                  │
│                                                             │
│  server {                                                   │
│      listen 10899 ssl;                                      │
│      server_name bifine.angelgroup.com.cn;                  │
│                                                             │
│      location /smart-ask/       → :8888 (Frontend)          │
│      location /smart-ask/api/   → :5002 (Backend API)       │
│  }                                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Docker 容器                               │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  Frontend (:8888) │  │  Backend (:5002) │                   │
│  │  Vue3 + Vite     │  │  Flask API       │                   │
│  └────────┬──────────┘  └────────┬────────┘                   │
│           │                      │                           │
│           └──────────┬───────────┘                           │
│                      ▼                                       │
│           ┌─────────────────┐                                │
│           │ PostgreSQL(:5433)│                                │
│           └─────────────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

### 关键要点

✅ **外部Nginx负责：**
- SSL/TLS 加密（HTTPS）
- 端口监听（10899）
- 路径前缀处理（/smart-ask）
- 反向代理转发到Docker容器

✅ **Docker容器只负责：**
- 对内暴露端口（5002, 8888, 5433）
- 不直接对外提供HTTPS服务
- 由外部Nginx统一入口

---

## 🚀 完整部署流程（从零开始）

### ⏱️ 预计耗时：10-15分钟

#### 第一步：SSH 登录服务器

```bash
# 使用你的服务器信息登录
ssh root@BISubApp01

# 或者使用其他用户
ssh your-user@your-server-ip
```

---

#### 第二步：进入项目目录并拉取代码

```bash
# 进入项目目录（根据你的实际情况修改路径）
cd /opta/smartask

# 如果是首次部署，先克隆仓库
git clone https://github.com/qishen123456/docker-setup.git .
cd docker-setup

# 切换到正确的分支（docker-setup）
git checkout docker-setup

# 如果已有代码，拉取最新版本
git fetch origin
git pull origin docker-setup
```

**预期输出：**
```
From https://github.com/qishen123456/docker-setup
 * branch            docker-setup -> FETCH_HEAD
Updating 8f93361..337e58f
Fast-forward
 .env.production               |  47 ++++
 DEPLOY_TO_SERVER.md           | 372 +++++++++++++++
 ...
16 files changed, 3061 insertions(+), 713 deletions(-)
```

---

#### 第三步：配置 .env 文件（最关键！）

**⚠️ 这是整个部署过程中最重要的一步！请仔细阅读下一章节**

```bash
# 复制生产环境模板
cp .env.production .env

# 编辑配置文件（使用你喜欢的编辑器）
vi .env        # 或 nano .env 或 vim .env
```

**详细的配置说明见下一节 [.env 配置完全指南](#-env-配置完全指南每个配置项都讲清楚)**

---

#### 第四步：配置外部 Nginx（关键！）

**⚠️ 这一步决定了用户能否通过公网访问你的系统！详见 [Nginx 配置完全指南](#-nginx-配置完全指南可直接复制使用)**

```bash
# 编辑 Nginx 配置文件（根据你的实际路径）
vi /etc/nginx/conf.d/smartask.conf

# 或者如果你用的是 sites-enabled 目录
vi /etc/nginx/sites-available/smartask

# 测试配置语法是否正确
nginx -t

# 重载 Nginx 使配置生效
nginx -s reload
```

---

#### 第五步：启动 Docker 服务

```bash
# 使用外部代理模式启动（推荐！这是你的场景）
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build

# 查看构建和启动过程（首次可能需要几分钟下载镜像）
# ...
# Creating network "smartask-new_smartask-internal" done
# Creating volume "smartask_pg_data" with external driver done
# Creating volume "smartask_chroma" with external driver done
# Creating smartask-postgres ... done
# Creating smartask-backend  ... done
# Creating smartask-frontend ... done
```

**或者使用一键更新脚本（更简单）：**
```bash
# 自动完成备份+拉取+重建+健康检查
bash update.sh
```

---

#### 第六步：验证服务状态

```bash
# 1. 查看所有容器状态（应该都是 Up 状态）
docker-compose ps

# 预期输出：
# NAME                STATUS                      PORTS
# smartask-backend    Up (healthy)                 0.0.0.0:5002->5002/tcp
# smartask-frontend   Up (healthy)                 0.0.0.0:8888->80/tcp
# smartask-postgres   Up (healthy)                 0.0.0.0:5433->5432/tcp


# 2. 测试后端健康检查
curl http://localhost:5002/api/health

# 预期输出：
# {"status":"ok","version":"...","timestamp":"..."}


# 3. 测试前端访问
curl -I http://localhost:8888/

# 预期输出：
# HTTP/1.1 200 OK
# Server: nginx/...
# Content-Type: text/html


# 4. 通过公网地址测试（在本地电脑浏览器打开）
# https://bifine.angelgroup.com.cn:10899/smart-ask/
```

---

#### 第七步：配置飞书 OAuth（如果使用飞书登录）

**详见 [飞书 OAuth 配置](#-飞书-oauth-配置必须更新)**

---

## 📝 .env 配置完全指南（每个配置项都讲清楚）

### 完整的 .env 文件示例（可直接复制使用）

```ini
# ============================================================
# SmartAsk 生产环境配置文件
# 适用场景：https://bifine.angelgroup.com.cn:10899/smart-ask
#
# 创建方式：cp .env.production .env && vi .env
# 注意：标记 [必填] 的项必须填写，[可选] 的按需配置
# ============================================================


# ==================== 一、基础配置 ====================

# 部署模式（固定为 production）
DEPLOY_MODE=production


# ==================== 二、公网访问地址配置 [必填] ====================
# 这些配置决定了用户如何通过浏览器访问你的系统

# 公网域名
PUBLIC_DOMAIN=bifine.angelgroup.com.cn

# 访问协议（http 或 https）
PUBLIC_PROTOCOL=https

# 对外暴露的端口号（你的外部Nginx监听的端口）
PUBLIC_PORT=10899

# URL路径前缀（如果有）
# 例如：https://domain.com/smart-ask -> BASE_PATH=/smart-ask
# 例如：https://domain.com/        -> BASE_PATH=/
BASE_PATH=/smart-ask

# 后端基础URL（自动拼接，一般不需要改）
BACKEND_URL=${PUBLIC_PROTOCOL}://${PUBLIC_DOMAIN}:${PUBLIC_PORT}${BASE_PATH}

# 前端基础URL（自动拼接，一般不需要改）
FRONTEND_URL=${PUBLIC_PROTOCOL}://${PUBLIC_DOMAIN}:${PUBLIC_PORT}${BASE_PATH}


# ==================== 三、Docker端口配置 ====================
# 这些端口只在服务器内部使用，不对外暴露

# 后端API端口（Docker内部使用，外部Nginx转发到这里）
SMARTASK_BACKEND_PORT=5002

# 前端HTTP端口（Docker内部使用，外部Nginx转发到这里）
SMARTASK_FRONTEND_PORT=8888

# PostgreSQL数据库端口（Docker内部使用，不要对外暴露）
SMARTASK_DOCKER_PG_PORT=5433

# 是否启用Docker内部Nginx（false = 使用外部Nginx，true = Docker内再套一层）
ENABLE_NGINX=false


# ==================== 四、数据库配置 [必填] ====================

# 数据库名称
SMARTASK_DB_DATABASE=smartask_db

# 数据库用户名
SMARTASK_DB_USERNAME=smartask_user

# 数据库密码（⚠️ 必须改成强密码！至少32位字符）
# 生成强密码的方法：openssl rand -base64 32
SMARTASK_DB_PASSWORD=YourStrongPasswordHere_ReplaceThisWithRealPassword_AtLeast32Chars

# PostgreSQL超级用户密码（可以和上面一样）
SMARTASK_POSTGRES_PASSWORD=${SMARTASK_DB_PASSWORD}


# ==================== 五、管理员账号配置 [必填] ====================
# ⚠️ 首次部署后立即登录并修改这些密码！

# 管理员用户名
SMARTASK_ADMIN_USERNAME=admin

# 管理员密码（⚠️ 不要用简单的密码如 admin123456）
SMARTASK_ADMIN_PASSWORD=YourAdminPasswordHere_ChangeImmediately

# 管理员显示名称
SMARTASK_ADMIN_DISPLAY_NAME=系统管理员


# ==================== 六、AI模型配置 [必填] ====================
# SmartAsk 核心功能依赖AI模型，必须配置！

# 方式一：使用 OpenAI 官方接口（最稳定但较贵）
SMARTASK_AI_API_KEY=sk-your-openai-api-key-here
SMARTASK_AI_BASE_URL=https://api.openai.com/v1/
SMARTASK_AI_MODEL=gpt-4o

# 方式二：使用 DeepSeek 兼容接口（推荐！性价比高，中文效果好）
# SMARTASK_AI_API_KEY=sk-your-deepseek-api-key-here
# SMARTASK_AI_BASE_URL=https://api.deepseek.com/v1/
# SMARTASK_AI_MODEL=deepseek-chat

# 方式三：使用其他兼容 OpenAI 格式的接口
# SMARTASK_AI_API_KEY=your-api-key
# SMARTASK_AI_BASE_URL=https://your-custom-api-endpoint/v1/
# SMARTASK_AI_MODEL=model-name


# ==================== 七、安全密钥配置 [必填] ====================
# ⚠️ 生产环境必须随机生成，绝对不能使用默认值！

# Flask Session/JWT签名密钥（用于加密用户会话）
# 生成方法：python3 -c "import secrets; print(secrets.token_hex(32))"
SMARTASK_SECRET_KEY=your-random-secret-key-here-at-least-64-characters-long

# Flask Session密钥（另一个随机密钥）
SECRET_KEY=another-random-secret-key-here-different-from-above


# ==================== 八、飞书集成配置 [可选] ====================
# 如果你使用飞书数据同步或飞书登录，必须配置

# 飞书应用的 App ID（在飞书开发者后台获取）
SMARTASK_FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx

# 飞书应用的 App Secret（在飞书开发者后台获取）
SMARTASK_FEISHU_APP_SECRET=your-feishu-app-secret-here

# 飞书 OAuth 回调URL（自动拼接，但要确保和飞书平台配置一致）
FEISHU_REDIRECT_URI=${PUBLIC_PROTOCOL}://${PUBLIC_DOMAIN}:${PUBLIC_PORT}${BASE_PATH}/api/auth/feishu/callback

# 飞书回调后的前端跳转URL
FEISHU_FRONTEND_CALLBACK_URL=${PUBLIC_PROTOCOL}://${PUBLIC_DOMAIN}:${PUBLIC_PORT}${BASE_PATH}


# ==================== 九、Docker构建优化配置 [可选] ====================
# 国内服务器建议配置镜像加速，否则构建会很慢

# APT包管理器镜像源（Debian/Ubuntu系统包）
SMARTASK_APT_MIRROR=https://mirrors.aliyun.com

# NPM镜像源（Node.js包）
SMARTASK_NPM_REGISTRY=https://registry.npmmirror.com

# pip镜像源（Python包）
SMARTASK_PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# pip可信主机
SMARTASK_PIP_TRUSTED_HOST=mirrors.aliyun.com

# Docker Hub镜像加速（多个用逗号分隔）
SMARTASK_DOCKER_REGISTRY_MIRRORS=https://docker.m.daocloud.io,https://docker.1ms.run


# ==================== 十、Bootstrap控制配置 [一般不需要改] ====================
# 是否跳过内置数据集导入（首次部署保持默认即可）
SMARTASK_BOOTSTRAP_SKIP_BUILTINS=1

# 是否跳过首次数据导入
SMARTASK_BOOTSTRAP_SKIP_FIRST_IMPORT=1


# ==================== 十一、高级加密配置 [可选] ====================
# 如果 config/*.json 使用了 enc:v1 密文格式才需要配置

# 加密主密钥（用于解密配置文件中的敏感信息）
# SMARTASK_SECRET_MASTER_KEY=your-master-encryption-key

# 密钥文件路径（如果用文件存储密钥）
# SMARTASK_SECRET_KEY_FILE=config/.secret_master_key
```

---

### 各配置项详细说明

#### 1️⃣ 公网访问地址配置（第二部分）

| 配置项 | 说明 | 示例值 | 是否必填 |
|--------|------|--------|----------|
| `PUBLIC_DOMAIN` | 你的域名或IP地址 | `bifine.angelgroup.com.cn` | ✅ 必填 |
| `PUBLIC_PROTOCOL` | 访问协议 | `https` 或 `http` | ✅ 必填 |
| `PUBLIC_PORT` | 外部Nginx监听端口 | `10899`, `443`, `80` | ✅ 必填 |
| `BASE_PATH` | URL路径前缀 | `/smart-ask`, `/` | ✅ 必填 |

**拼接规则：**
```
最终访问地址 = ${PUBLIC_PROTOCOL}://${PUBLIC_DOMAIN}:${PUBLIC_PORT}${BASE_PATH}
例如：https://bifine.angelgroup.com.cn:10899/smart-ask
```

---

#### 2️⃣ 数据库配置（第四部分）

| 配置项 | 说明 | 示例值 | 安全要求 |
|--------|------|--------|----------|
| `SMARTASK_DB_DATABASE` | 数据库名称 | `smartask_db` | 无特殊要求 |
| `SMARTASK_DB_USERNAME` | 数据库用户名 | `smartask_user` | 不要用 root/postgres |
| `SMARTASK_DB_PASSWORD` | 数据库密码 | `Xk9#mP2$vL5@nQ8...` | ⚠️ 至少32位，包含大小写字母+数字+特殊字符 |

**生成强密码的方法：**
```bash
# 方法1：使用 openssl
openssl rand -base64 32

# 方法2：使用 python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 方法3：使用 pwgen（如果安装了）
pwgen -s 32 1
```

---

#### 3️⃣ AI模型配置（第六部分）

**当前支持的AI服务商：**

| 服务商 | BASE_URL | 推荐模型 | 价格参考 |
|--------|----------|----------|----------|
| **OpenAI** | `https://api.openai.com/v1/` | `gpt-4o` | 较贵 |
| **DeepSeek** | `https://api.deepseek.com/v1/` | `deepseek-chat` | 便宜（推荐！） |
| **通义千问** | `https://dashscope.aliyuncs.com/compatible-mode/v1/` | `qwen-plus` | 中等 |
| **智谱AI** | `https://open.bigmodel.cn/api/paas/v4/` | `glm-4` | 中等 |
| **MiniMax** | `https://api.minimax.chat/v1/` | `abab6.5s-chat` | 便宜 |

**获取API Key的方法：**
1. 注册对应平台的开发者账号
2. 创建应用并获取 API Key
3. 充值额度（大部分平台有免费试用额度）
4. 将 Key 填入 `.env` 文件

**推荐配置（性价比最高）：**
```ini
# DeepSeek（便宜且中文效果好）
SMARTASK_AI_API_KEY=sk-your-deepseek-key
SMARTASK_AI_BASE_URL=https://api.deepseek.com/v1/
SMARTASK_AI_MODEL=deepseek-chat
```

---

#### 4️⃣ 安全密钥配置（第七部分）

**为什么需要两个不同的密钥？**

| 密钥 | 用途 | 泄露后果 |
|------|------|----------|
| `SMARTASK_SECRET_KEY` | JWT Token签名、Session加密 | 攻击者可以伪造任意用户的登录态 |
| `SECRET_KEY` | Flask Session Cookie签名 | 攻击者可以篡改Session数据 |

**⚠️ 绝对不能使用相同的值！必须生成两个不同的随机密钥！**

**生成方法：**
```bash
# 生成 SMARTASK_SECRET_KEY（64位十六进制）
python3 -c "import secrets; print(secrets.token_hex(32))"
# 输出示例：a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456

# 生成 SECRET_KEY（另一个64位十六进制）
python3 -c "import secrets; print(secrets.token_hex(32))"
# 输出示例：f9e8d7c6b5a4123012345678901234567890abcdef1234567890abcdef123456
```

---

#### 5️⃣ 飞书集成配置（第八部分）

**在哪里获取这些值？**

1. 打开 [飞书开放平台](https://open.feishu.cn/app)
2. 登录并选择或创建你的应用
3. 进入「凭证与基础信息」页面
4. 找到 **App ID** 和 **App Secret**

**配置要求：**
- `FEISHU_REDIRECT_URI` 必须和飞书平台「安全设置」中配置的重定向 URL **完全一致**
- 包括协议（https）、域名、端口、路径，一个字符都不能差！

---

## 🔧 Nginx 配置完全指南（可直接复制使用）

### 场景说明

**你的场景：** 已有外部Nginx/负载均衡，需要将请求转发到Docker容器

**目标：**
- 用户访问 `https://bifine.angelgroup.com.cn:10899/smart-ask/` 
- Nginx 将请求转发到 Docker 容器的 `:8888`（前端）和 `:5002`（后端API）

---

### 完整的 Nginx 配置文件（可直接复制）

**文件位置：** `/etc/nginx/conf.d/smartask.conf` （或根据你的Nginx配置规范调整）

```nginx
# ============================================================
# SmartAsk 外部反向代理配置
# 用途：将公网请求转发到 Docker 容器
# 适配地址：https://bifine.angelgroup.com.cn:10899/smart-ask
# ============================================================

# ====== HTTP → HTTPS 强制跳转（可选，推荐开启）======
server {
    listen 10899;
    server_name bifine.angelgroup.com.cn;

    # 将所有 HTTP 请求重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}


# ====== 主配置（HTTPS）======
server {
    # 监听端口（你的外部Nginx端口）
    listen 10899 ssl http2;

    # 域名
    server_name bifine.angelgroup.com.cn;

    # ==================== SSL证书配置 ====================
    # ⚠️ 请替换为你实际的证书路径！

    # 方式一：Let's Encrypt 免费证书（推荐）
    ssl_certificate     /etc/letsencrypt/live/bifine.angelgroup.com.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bifine.angelgroup.com.cn/privkey.pem;

    # 方式二：公司自有证书
    # ssl_certificate     /path/to/your/cert.pem;
    # ssl_certificate_key /path/to/your/key.pem;

    # 方式三：自签名证书（仅测试用，浏览器会警告）
    # ssl_certificate     /etc/nginx/certs/selfsigned.crt;
    # ssl_certificate_key /etc/nginx/certs/selfsigned.key;


    # ==================== SSL优化配置 ====================
    # SSL协议版本（只允许安全的TLS 1.2和1.3）
    ssl_protocols TLSv1.2 TLSv1.3;

    # 加密套件（优先使用强加密）
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # SSL会话缓存（提高HTTPS性能）
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # OCSP Stapling（加速SSL握手）
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;


    # ==================== 日志配置 ====================
    access_log /var/log/nginx/smartask_access.log;
    error_log  /var/log/nginx/smartask_error.log;


    # ==================== Gzip压缩（提高传输速度）====================
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
    gzip_min_length 1000;


    # ==================== SmartAsk 前端路由 ====================
    # 匹配：https://domain:10899/smart-ask/*
    # 转发到：Docker Frontend 容器 (:8888)
    location /smart-ask/ {
        # 转发目标（Docker前端容器）
        proxy_pass http://127.0.0.1:8888/;

        # ⭐ 路径重写（关键！去掉 /smart-ask 前缀）
        # 否则前端会找不到静态资源和API
        rewrite ^/smart-ask/(.*)$ /$1 break;

        # 传递原始请求信息
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # Vue Router history 模式支持
        # 所有未匹配的路由都返回 index.html，让Vue Router处理
        try_files $uri $uri/ /index.html;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }


    # ==================== SmartAsk API路由 ====================
    # 匹配：https://domain:10899/smart-ask/api/*
    # 转发到：Docker Backend 容器 (:5002)
    location /smart-ask/api/ {
        # 转发目标（Docker后端容器）
        proxy_pass http://127.0.0.1:5002/api/;

        # ⭐⭐⭐ SSE流式响应支持（必须关闭缓冲！）
        # SmartAsk的智能问数功能使用Server-Sent Events流式返回结果
        # 如果开启buffering，会导致SSE无法实时推送数据
        proxy_buffering off;
        proxy_cache off;

        # 长连接超时（SSE可能持续较长时间）
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;

        # WebSocket支持（如果未来需要实时通信）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 传递原始请求信息
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # 文件上传大小限制（如果需要大文件上传）
        client_max_body_size 100M;

        # 跨域支持（如果前后端分离部署）
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header Access-Control-Allow-Headers 'DNT,X-Mx-ReqToken,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Authorization' always;

        # 处理 OPTIONS 预检请求
        if ($request_method = OPTIONS) {
            return 204;
        }
    }


    # ==================== 静态资源缓存优化（可选）====================
    # 对JS/CSS/图片等静态资源启用长期缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://127.0.0.1:8888;

        # 缓存30天
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }


    # ==================== 安全头（可选但推荐）====================
    # 防止点击劫持
    add_header X-Frame-Options "SAMEORIGIN" always;

    # 防止MIME类型嗅探
    add_header X-Content-Type-Options "nosniff" always;

    # XSS防护
    add_header X-XSS-Protection "1; mode=block" always;

    # 引用策略
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;


    # ==================== 错误页面 ====================
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
        internal;
    }
}
```

---

### Nginx 配置关键点详解

#### 1️⃣ 路径重写规则（最重要！）

```nginx
location /smart-ask/ {
    proxy_pass http://127.0.0.1:8888/;
    rewrite ^/smart-ask/(.*)$ /$1 break;  # ← 这一行是关键！
}
```

**为什么需要这个？**

假设用户访问：`https://domain:10899/smart-ask/assets/app.js`

**没有 rewrite 时：**
- Nginx 转发给 Frontend：`GET /smart-ask/assets/app.js`
- Frontend 找不到文件（因为实际路径是 `/assets/app.js`）
- 结果：**404 Not Found** ❌

**有 rewrite 时：**
- Nginx 先重写路径：`/smart-ask/assets/app.js` → `/assets/app.js`
- 再转发给 Frontend：`GET /assets/app.js`
- Frontend 成功找到文件
- 结果：**200 OK** ✅

---

#### 2️⃣ SSE流式响应支持（核心功能！）

```nginx
location /smart-ask/api/ {
    proxy_pass http://127.0.0.1:5002/api/;
    
    proxy_buffering off;   # ← 关闭缓冲
    proxy_cache off;       # ← 关闭缓存
    proxy_read_timeout 300s;  # ← 长超时
}
```

**为什么必须关闭 buffering？**

SmartAsk 的"智能问数"功能使用 **Server-Sent Events (SSE)** 技术实时推送查询结果。

**开启 buffering 时：**
- Nginx 会等待后端响应**完全结束**后才一次性返回给前端
- 用户看不到实时的打字机效果
- 如果查询耗时较长，用户会一直看到加载动画
- 结果：**体验极差，甚至超时报错** ❌

**关闭 buffering 时：**
- Nginx 收到后端的每一个数据块就立即推送给前端
- 用户能看到实时的文字逐字出现效果
- 即使长时间查询也不会中断
- 结果：**流畅的实时体验** ✅

---

#### 3️⃣ SSL证书配置

**方式一：Let's Encrypt 免费证书（推荐）**

```bash
# 安装 Certbot 工具
yum install certbot python3-certbot-nginx  # CentOS/RHEL
# 或 apt install certbot python3-certbot-nginx  # Ubuntu/Debian

# 自动申请并配置证书（会自动修改Nginx配置）
certbot --nginx -d bifine.angelgroup.com.cn

# 设置自动续期（Let's Encrypt证书90天过期）
certbot renew --dry-run  # 测试续期是否正常
```

**方式二：使用现有证书**

如果你的服务器已有该域名的SSL证书，直接指定路径即可：

```nginx
ssl_certificate     /path/to/your/fullchain.pem;
ssl_certificate_key /path/to/your/privkey.pem;
```

---

### 应用Nginx配置

```bash
# 1. 测试配置语法是否正确
nginx -t

# 预期输出：
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# 2. 重载 Nginx 使配置生效（不断开现有连接）
nginx -s reload

# 3. 如果报错，查看错误日志
tail -f /var/log/nginx/error.log

# 4. 验证端口监听
netstat -tlnp | grep :10899
# 应该看到：tcp 0 0 0.0.0.0:10899  LISTEN <nginx_pid>
```

---

## 🔐 飞书 OAuth 配置（必须更新）

### 在飞书开放平台操作步骤

#### 第一步：登录飞书开发者后台

👉 **访问地址：** https://open.feishu.cn/app

#### 第二步：选择或创建应用

- 如果已有应用：直接选择
- 如果没有：点击「创建企业自建应用」

#### 第三步：配置重定向 URL

1. 进入应用详情页
2. 左侧菜单找到「安全设置」
3. 找到「重定向 URL」设置项
4. 点击「添加」按钮
5. 输入以下URL：

```
https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/callback
```

6. 点击「保存」

**⚠️ 重要提醒：**
- URL 必须 **完全匹配** `.env` 中的 `FEISHU_REDIRECT_URI` 配置
- 包括协议（https）、域名、端口（10899）、路径，一个字符都不能差！
- 多了或少了一个斜杠都会导致认证失败！

#### 第四步：发布应用版本

**⚠️ 这一步很多人忘记！修改配置后必须发布新版本才生效！**

1. 左侧菜单找到「版本管理与发布」
2. 点击「创建版本」
3. 填写版本号和更新说明
4. 提交审核（如果是企业内部应用通常秒过）
5. 发布成功后，新的回调URL才会生效

---

### 验证飞书登录流程

1. **访问前端页面**
   ```
   https://bifine.angelgroup.com.cn:10899/smart-ask/
   ```

2. **点击「使用飞书组织身份登录」**

3. **应该跳转到飞书授权页面**
   ```
   https://open.feishu.cn/connect/oauth2/authorize?...
   ```

4. **授权后回调到**
   ```
   https://bifine.angelgroup.com.cn:10899/smart-ask/api/auth/feishu/callback?code=xxx&state=xxx
   ```

5. **自动跳转回前端并显示用户信息** ✅

---

### 常见飞书登录问题

| 错误信息 | 原因 | 解决方案 |
|---------|------|----------|
| `飞书 OAuth state 校验失败` | FEISHU_REDIRECT_URI 与飞书平台不一致 | 对比 `.env` 和飞书平台配置，确保完全一致 |
| `502 Bad Gateway` | 外部Nginx未正确转发到Docker容器 | 检查 Nginx 配置和容器状态 |
| `回调地址不匹配` | 飞书平台配置的URL多了/少了字符 | 重新添加正确的URL并发布版本 |
| `应用未上线` | 修改配置后忘记发布新版本 | 到「版本管理与发布」创建并发布新版本 |
| `权限不足` | 应用缺少必要的API权限 | 在「权限管理」中开通所需权限 |

---

## ✅ 部署验证清单

部署完成后，**逐一验证以下每一项**：

### 基础设施验证

- [ ] **Docker 容器全部运行正常**
  ```bash
  docker-compose -f docker-compose.yml -f docker-compose.proxy.yml ps
  ```
  **预期：** 所有服务状态为 `Up (healthy)`

- [ ] **后端健康检查通过**
  ```bash
  curl http://localhost:5002/api/health
  ```
  **预期：** `{"status":"ok","version":"...","timestamp":"..."}`

- [ ] **前端页面可访问（内部）**
  ```bash
  curl -I http://localhost:8888/
  ```
  **预期：** `HTTP/1.1 200 OK`

- [ ] **Nginx 正确监听端口**
  ```bash
  netstat -tlnp | grep :10899
  ```
  **预期：** 显示 nginx 进程在监听 10899 端口

---

### 公网访问验证

- [ ] **前端页面可通过公网访问**
  ```
  浏览器打开：https://bifine.angelgroup.com.cn:10899/smart-ask/
  ```
  **预期：** 看到 SmartAsk 登录页面

- [ ] **API 可通过公网访问**
  ```bash
  curl https://bifine.angelgroup.com.cn:10899/smart-ask/api/health
  ```
  **预期：** `{"status":"ok",...}`

- [ ] **静态资源正常加载**
  ```
  浏览器 F12 打开开发者工具 → Network 标签
  刷新页面，查看 JS/CSS/图片是否全部 200 OK
  ```
  **预期：** 没有红色的 404 错误

---

### 功能验证

- [ ] **账号密码登录成功**
  1. 访问前端页面
  2. 输入管理员账号（`.env` 中配置的 `SMARTASK_ADMIN_USERNAME`）
  3. 输入密码（`SMARTASK_ADMIN_PASSWORD`）
  4. **预期：** 成功进入系统主界面

- [ ] **飞书登录成功（如果配置了飞书）**
  1. 点击「使用飞书组织身份登录」
  2. 完成飞书授权
  3. **预期：** 自动跳转回来并显示飞书用户信息

- [ ] **智能问数功能正常（核心功能！）**
  1. 登录后进入问数界面
  2. 输入测试问题：「上海的业绩是多少？」
  3. **预期：**
     - 看到 SSE 流式响应（文字逐步出现）
     - 最终返回 SQL 和查询结果图表
     - 整个过程不超过 30 秒

- [ ] **模型权限过滤生效（如果配置了）**
  1. 使用受限账号登录（如刘太琳）
  2. 点击 AI 模型下拉框
  3. **预期：** 只显示允许使用的模型（不是全部模型）

---

### 日志验证

- [ ] **后端日志无严重错误**
  ```bash
  docker logs smartask-backend --tail 50
  ```
  **预期：** 没有 ERROR/FATAL 级别的错误

- [ ] **前端日志无报错**
  ```bash
  docker logs smartask-frontend --tail 20
  ```
  **预期：** 只有正常的访问日志

- [ ] **Nginx 日志无大量 4xx/5xx**
  ```bash
  tail -f /var/log/nginx/smartask_error.log
  ```
  **预期：** 没有持续的报错刷屏

---

## 🔄 常用运维命令（日常必备）

### 启动/停止/重启

```bash
# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d

# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml down

# 重启某个服务
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml restart backend

# 重新构建并启动（代码更新后使用）
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build

# 只重启不重建（只改了配置时使用）
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml restart
```

---

### 日志查看

```bash
# 实时查看后端日志（最常用！）
docker logs -f smartask-backend

# 查看最近100行后端日志
docker logs smartask-backend --tail 100

# 查看今天的前端日志
docker logs smartask-frontend --since "2026-08-10T00:00:00"

# 同时查看多个服务的日志
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml logs -f --tail=50 backend frontend
```

---

### 数据备份

```bash
# 导出完整数据库备份
docker exec smartask-postgres pg_dump -U smartask_user smartask_db > backup_db_$(date +%Y%m%d_%H%M%S).sql

# 备份所有配置文件（包括用户权限等）
tar czf backup_config_$(date +%Y%m%d_%H%M%S).tar.gz config/

# 备份向量数据库（ChromaDB）
tar czf backup_chroma_$(date +%Y%m%d_%H%M%S).tar.gz ./volumes/smartask_chroma/_data/
```

---

### 故障排查

```bash
# 检查端口占用情况
netstat -tlnp | grep -E '(5002|8888|5433|10899)'

# 测试 Docker 内部网络连通性
docker exec smartask-frontend wget -qO- http://smartask-backend:5002/api/health

# 进入后端容器调试
docker exec -it smartask-backend bash

# 进入前端容器调试
docker exec -it smartask-frontend sh

# 查看容器资源使用情况
docker stats --no-stream

# 查看 Docker 事件日志
docker events --since "2026-08-10T00:00:00"
```

---

### 一键更新（最常用！）

```bash
# 使用 update.sh 脚本（全自动）
cd /opta/smartask
bash update.sh

# 或者手动执行
git pull origin docker-setup
docker-compose -f docker-compose.yml -f docker-compose.proxy.yml up -d --build
```

---

## 📞 故障排查速查表（快速定位问题）

| 问题现象 | 可能原因 | 快速诊断命令 | 解决方案 |
|---------|---------|-------------|---------|
| **访问页面 502** | Nginx 未启动或配置错误 | `nginx -t && nginx -s reload` | 检查 Nginx 配置语法 |
| **访问页面 404** | 路径重写规则错误 | `curl -I localhost:8888/` | 检查 `rewrite` 规则 |
| **飞书登录失败** | 回调URL不匹配 | 对比 `.env` 和飞书平台 | 确保 URL 完全一致 |
| **SSE 无响应** | Nginx 开启了 buffering | `grep "proxy_buffering" /etc/nginx/conf.d/smartask.conf` | 设置 `off` |
| **登录后白屏** | Vue Router 路径问题 | 浏览器 F12 查看控制台错误 | 检查 `try_files` 配置 |
| **API 跨域错误** | 缺少 CORS 头 | `curl -I -X OPTIONS localhost:5002/api/` | 添加 CORS 相关头 |
| **数据库连不上** | Postgres 容器未启动 | `docker ps \| grep postgres` | 手动启动 Postgres 容器 |
| **容器反复重启** | 配置错误或资源不足 | `docker logs smartask-backend --tail 50` | 查看具体错误信息 |
| **端口被占用** | 其他程序占用了端口 | `netstat -tlnp \| grep :5002` | 停止占用进程或换端口 |
| **SSL 证书错误** | 证书过期或路径错误 | `openssl s_client -connect localhost:10899 -servername domain` | 更新证书或修正路径 |
| **权限配置丢失** | 更新时未恢复配置 | `ls -la backups/runtime_config_*` | 从备份目录恢复 |

---

## 💡 下一步建议

### 首次部署完成后

1. **修改默认密码** - 立即登录并修改管理员密码
2. **配置定期备份** - 设置 cron 任务自动备份数据库
3. **监控告警** - 接入监控系统（Prometheus + Grafana）
4. **日志收集** - 配置 ELK 或 Loki 收集日志

### 高级优化（可选）

1. **性能优化**
   - 开启 HTTP/2
   - 配置 Brotli 压缩（比 Gzip 更高效）
   - CDN 加速静态资源

2. **安全加固**
   - 配置 WAF（Web应用防火墙）
   - 限制 IP 白名单（如果只有内网访问）
   - 定期更新依赖包

3. **高可用架构**
   - 多节点负载均衡
   - Redis 缓存层
   - 数据库主从复制

---

## 📚 相关文件索引

| 文件 | 用途 | 优先级 |
|------|------|--------|
| **[DEPLOY_TO_SERVER.md](./DEPLOY_TO_SERVER.md)** | ⭐ **本文档 - 服务器部署完整指南（必读！）** | ⭐⭐⭐ |
| **[.env.production](./.env.production)** | 生产环境变量模板（已预填你的地址） | ⭐⭐⭐ |
| **[.env.template](./.env.template)** | 完整的环境变量模板（含所有配置项说明） | ⭐⭐⭐ |
| **[docker-compose.proxy.yml](./docker-compose.proxy.yml)** | 外部代理模式 Docker 配置 | ⭐⭐ |
| **[update.sh](./update.sh)** | 一键更新脚本（自动备份+拉取+重建） | ⭐⭐ |
| **[deploy.sh](./deploy.sh)** | 部署模式切换脚本 | ⭐⭐ |
| **[NGINX_DEPLOYMENT.md](./NGINX_DEPLOYMENT.md)** | Nginx 配置通用指南 | ⭐⭐ |
| **[GIT_BRANCH_GUIDE.md](./GIT_BRANCH_GUIDE.md)** | Git 分支管理策略 | ⭐ |
| **[PUSH_TO_GITHUB.md](./PUSH_TO_GITHUB.md)** | 推送代码教程 | ⭐ |

---

## 🆘 遇到问题？

**自查顺序：**
1. 查看本文档的「故障排查速查表」
2. 检查容器日志：`docker logs -f smartask-backend`
3. 检查 Nginx 日志：`tail -f /var/log/nginx/error.log`
4. 对照本文档的配置示例，逐项对比

**如果还是无法解决：**
- 检查 GitHub Issues：https://github.com/qishen123456/docker-setup/issues
- 查看官方文档：项目根目录的 README.md

---

**最后更新：** 2026-08-10
**适用场景：** `https://bifine.angelgroup.com.cn:10899/smart-ask`
**文档版本：** v2.0（超详细版）
