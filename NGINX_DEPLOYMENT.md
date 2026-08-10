# SmartAsk Nginx 反向代理部署指南

> **最适合你的单公网端口部署方案**
>
> 解决问题：本地测试用双端口（5002+8888），服务器部署用单端口（80）通过Nginx代理

---

## 📋 方案对比

| 特性 | Local 模式（本地开发） | Production 模式（生产环境） |
|------|------------------------|---------------------------|
| **访问方式** | 后端:5002 + 前端:8888 | 统一 :80 (Nginx代理) |
| **适用场景** | 本地开发、调试 | 服务器部署、公网访问 |
| **Nginx** | ❌ 未启用 | ✅ 自动启用 |
| **端口暴露** | 直接暴露给主机 | 仅 Nginx 对外暴露 |
| **配置文件** | .env.local | .env.production |

---

## 🚀 快速开始

### 方式一：使用部署脚本（推荐）

#### Windows PowerShell
```powershell
# 切换到本地开发模式
.\deploy.ps1 -Mode local
docker-compose up -d --build

# 切换到生产环境模式
.\deploy.ps1 -Mode production
docker-compose --profile production -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 查看当前状态
.\deploy.ps1 -Status
```

#### Linux/Mac Bash
```bash
# 赋予执行权限（首次）
chmod +x deploy.sh

# 切换到本地开发模式
./deploy.sh local
docker-compose up -d --build

# 切换到生产环境模式
./deploy.sh production
docker-compose --profile production -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 查看当前状态
./deploy.sh status
```

### 方式二：手动操作

#### 本地开发模式
```bash
# 1. 复制本地配置
cp .env.local .env

# 2. 启动所有服务（包括backend/frontend端口）
docker-compose up -d --build

# 3. 访问地址
# 前端：http://localhost:8888
# 后端API：http://localhost:5002/api/...
```

#### 生产环境模式
```bash
# 1. 修改 .env.production 中的域名
vim .env.production
# 将 PUBLIC_DOMAIN=your-domain.com 改为你的实际域名或IP

# 2. 复制生产配置
cp .env.production .env

# 3. 启动服务（自动加载prod override，禁用直接端口暴露）
docker-compose --profile production -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. 访问地址（统一通过Nginx）
# 前端：http://your-domain.com/
# 后端API：http://your-domain.com/api/...
# 飞书回调：http://your-domain.com/api/auth/feishu/callback
```

---

## 🔧 核心文件说明

### 1. `nginx/nginx.prod.conf` - Nginx 配置
```nginx
server {
    listen ${NGINX_PORT:-80};                    # 默认监听80端口
    server_name ${PUBLIC_DOMAIN:-localhost};      # 你的域名

    # API路由 → backend:5002
    location /api/ {
        proxy_pass http://smartask-backend:5002;
        proxy_buffering off;                      # SSE流式响应支持
        proxy_read_timeout 300s;                  # 长连接超时
        # ... 其他配置
    }

    # 前端路由 → frontend:80
    location / {
        proxy_pass http://smartask-frontend:80;
        try_files $uri $uri/ /index.html;         # Vue Router history模式
    }
}
```

**关键特性：**
- ✅ SSE 支持（智能问数流式响应）
- ✅ WebSocket 支持
- ✅ Vue Router History 模式
- ✅ 真实IP传递（X-Forwarded-For）

### 2. `docker-compose.prod.yml` - 生产覆盖文件
```yaml
services:
  backend:
    ports: []          # ← 关键：清空端口，不对外暴露

  frontend:
    ports: []          # ← 关键：清空端口，不对外暴露

# Nginx 服务已在主配置中定义（profiles: ["production"]）
```

**作用：** 覆盖主配置的`ports`字段，确保production模式下只有Nginx对外暴露端口。

### 3. `.env.production` - 生产环境变量
```ini
DEPLOY_MODE=production
PUBLIC_DOMAIN=your-domain.com   # ⚠️ 必须修改！
NGINX_PORT=80                   # 或443（HTTPS）

# 所有请求统一走Nginx
BACKEND_URL=http://${PUBLIC_DOMAIN}
FRONTEND_URL=http://${PUBLIC_DOMAIN}

# 飞书OAuth回调也走Nginx
FEISHU_REDIRECT_URI=http://${PUBLIC_DOMAIN}/api/auth/feishu/callback
FEISHU_FRONTEND_CALLBACK_URL=http://${PUBLIC_DOMAIN}
```

---

## 🌐 网络架构图

### Local 模式（本地开发）
```
用户浏览器
    ↓
┌─────────────────────────────────────┐
│  Docker Host                        │
│  ┌──────────────┐  ┌────────────┐  │
│  │  Frontend     │  │ Backend    │  │
│  │  :8888       │→ │ :5002      │  │
│  └──────────────┘  └────────────┘  │
│  （端口直连，无Nginx）              │
└─────────────────────────────────────┘
```

### Production 模式（生产环境）
```
用户浏览器
    ↓
┌─────────────────────────────────────┐
│  Docker Host                        │
│  ┌──────────────┐                  │
│  │  Nginx (:80) │ ← 唯一对外端口   │
│  │  ┌────────┐  │                  │
│  │  │/api/*  │→ │ Backend:5002    │
│  │  ├────────┤  │ （内部通信）     │
│  │  │/*      │→ │ Frontend:80     │
│  │  └────────┘  │ （内部通信）     │
│  └──────────────┘                  │
└─────────────────────────────────────┘
```

---

## ⚙️ 高级配置

### HTTPS 支持（可选）
1. 准备SSL证书（Let's Encrypt 或自签名）
2. 创建证书目录：
   ```bash
   mkdir -p nginx/certs
   # 放入 fullchain.pem 和 privkey.pem
   ```
3. 取消注释 `docker-compose.yml` 中的SSL配置：
   ```yaml
   nginx:
     ports:
       - "${NGINX_PORT:-80}:80"
       - "${NGINX_SSL_PORT:-443}:443"  # 取消注释
     volumes:
       - ./nginx/certs:/etc/nginx/certs:ro  # 取消注释
   ```
4. 取消注释 `nginx/nginx.prod.conf` 中的HTTPS server块

### 自定义端口
修改 `.env.production`：
```ini
NGINX_PORT=8080  # 改为任意未占用端口
```

### 多域名支持
如果需要多个域名指向同一实例，修改 `nginx/nginx.prod.conf`：
```nginx
server_name your-domain.com www.your-domain.com api.your-domain.com;
```

---

## 🔍 故障排查

### 问题1：Nginx启动失败
**症状：** `docker-compose ps` 显示 nginx 容器 Exit 1

**解决步骤：**
```bash
# 查看日志
docker logs smartask-nginx

# 常见原因：
# 1. 端口被占用 → lsof -i :80 或 netstat -ano | findstr :80
# 2. 配置语法错误 → docker exec smartask-nginx nginx -t
# 3. backend/frontend未就绪 → docker-compose ps 检查依赖服务
```

### 问题2：502 Bad Gateway
**症状：** 访问页面显示 502 错误

**原因：** Nginx无法连接到后端容器

**解决：**
```bash
# 检查后端是否运行
docker ps | grep smartask-backend

# 测试内部网络连通性
docker exec smartask-nginx wget -qO- http://smartask-backend:5002/api/health

# 检查网络
docker network ls | grep smartask
docker network inspect smartask_smartask-internal
```

### 问题3：飞书OAuth回调失败
**症状：** `飞书 OAuth state 校验失败`

**原因：** 回调URL与配置不一致

**检查清单：**
1. `.env` 中 `FEISHU_REDIRECT_URI` = `http://域名/api/auth/feishu/callback`
2. 飞书开放平台 → 应用配置 → 重定向URL 一致
3. 使用HTTPS时确保证书有效

### 问题4：前端刷新404
**症状：** Vue Router页面刷新后404

**原因：** Nginx未配置 `try_files`

**确认：** `nginx/nginx.prod.conf` 包含：
```nginx
location / {
    try_files $uri $uri/ /index.html;  # 必须有这行
}
```

---

## 📊 性能优化建议

### 1. 静态资源缓存
取消注释 `nginx/nginx.prod.conf` 中的缓存配置：
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### 2. Gzip压缩
在 `nginx/nginx.prod.conf` 的 `server` 块前添加：
```gzip
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
gzip_min_length 1000;
```

### 3. 安全头
取消注释安全头配置：
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
```

---

## ✅ 部署检查清单

部署完成后，逐一验证：

- [ ] `docker-compose ps` 所有容器状态 Up
- [ ] 访问 `http://域名/` 显示登录页
- [ ] 访问 `http://域名/api/health` 返回健康检查
- [ ] 登录后能正常提问（SSE流式响应）
- [ ] 飞书登录跳转正常
- [ ] 刷新页面不404（Vue Router）
- [ ] 控制台无CORS错误
- [ ] 日志无报错：`docker logs smartask-nginx --tail 50`

---

## 📞 常用命令速查

```bash
# 查看所有容器状态
docker-compose ps

# 查看Nginx日志（实时）
docker logs -f smartask-nginx

# 重启Nginx（修改配置后）
docker restart smartask-nginx

# 测试Nginx配置语法
docker exec smartask-nginx nginx -t

# 进入Nginx容器调试
docker exec -it smartask-nginx sh

# 查看端口占用
netstat -tlnp | grep :80  # Linux
netstat -ano | findstr :80  # Windows

# 完全停止并清理
docker-compose down --remove-orphans

# 重新构建并启动
docker-compose --profile production -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 💡 最佳实践

1. **版本控制**：将 `.env` 加入 `.gitignore`，只提交 `.env.local` 和 `.env.production` 模板
2. **备份策略**：切换环境时脚本会自动备份旧 `.env` 文件
3. **监控告警**：建议配置 `docker logs` 监控和容器健康检查
4. **滚动更新**：生产环境更新时使用 `--no-recreate` 先更新后端，验证后再更新前端
5. **安全加固**：生产环境务必修改 `.env.production` 中的密码相关配置

---

**最后更新时间：** 2026-08-10
**适用版本：** SmartAsk v2.0+
