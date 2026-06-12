# SmartAsk 文档索引

本目录只保留当前仍有用的部署、交付和专项说明。日常交付优先看下面几份，避免照到旧端口或旧仓库地址。

## 必读

- [SmartAsk_部署与交付手册.md](SmartAsk_部署与交付手册.md)：用户机部署、更新、登录权限、诊断、备份、回退。
- [Linux_Docker部署运维手册.md](Linux_Docker部署运维手册.md)：阿里云 / 宝塔 / Linux Docker 部署与运维。
- [宝塔面板部署说明.md](宝塔面板部署说明.md)：宝塔反向代理、SSL、防火墙和常见故障。
- [SmartAsk_方案归档.md](SmartAsk_方案归档.md)：历史升级方案、火山引擎参考、报告配置、飞书集成等内容的整合摘要。

## 当前发布入口

```text
GitHub remote：https://github.com/qishen123456/docker-setup.git
发布分支：docker-setup
Docker 前端默认端口：8888
后端默认端口：5002
本地开发前端端口：5173
```

宝塔反向代理目标应指向 Docker 前端：

```text
目标 URL：http://127.0.0.1:8888
```

`5173` 只用于开发机运行 `npm run dev`，不要作为宝塔正式反向代理目标。

## 宝塔更新速查

```bash
cd /opt/smartask/smartask
git remote add github https://github.com/qishen123456/docker-setup.git 2>/dev/null || git remote set-url github https://github.com/qishen123456/docker-setup.git
git fetch github
git checkout docker-setup
git branch --set-upstream-to=github/docker-setup docker-setup
bash update.sh --remote github
```

更新完成后在服务器本机检查：

```bash
curl http://127.0.0.1:5002/api/health
curl http://127.0.0.1:8888/api/health
curl -I http://127.0.0.1:8888
```

## 专项保留

- [LangChain_MCP_问数增强行动计划.md](LangChain_MCP_问数增强行动计划.md)：LangChain / MCP 方向的专项增强计划。

## 终端速查

### 一、git推送

打开终端复制下方四行代码，第三行改个名字即可。

```bash
git status
git add .
git commit -m "chore: update smartask LIn aa"
git push -u github docker-setup
```

### 二、强制关闭前后端

用“管理员身份运行”的 PowerShell 执行。

```powershell
taskkill /F /PID 35028
taskkill /F /IM node.exe
taskkill /F /IM python.exe
```

### 三、重启后端

```powershell
cd "D:\万物云\万物云\AI培训\智能问数流程\火山引擎\智能问数项目_v20260330_004926(3)-566fee42a29e\智能问数项目_v20260330_004926"
$env:PYTHONNOUSERSITE="1"
C:\Users\liutq09\AppData\Local\anaconda3\python.exe backend\app.py
```

### 四、重启前端

```powershell
cd "D:\万物云\万物云\AI培训\智能问数流程\火山引擎\智能问数项目_v20260330_004926(3)-566fee42a29e\智能问数项目_v20260330_004926\frontend"
npm run dev
```
