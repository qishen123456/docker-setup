# SmartAsk 文档索引

本目录已做精简，只保留当前仍有用的文档。

## 必读

- [SmartAsk_部署与交付手册.md](SmartAsk_部署与交付手册.md)：用户机部署、更新、登录权限、诊断、备份、回退。
- [SmartAsk_方案归档.md](SmartAsk_方案归档.md)：历史升级方案、火山引擎参考、报告配置、飞书集成等内容的整合摘要。

## 专项保留

- [LangChain_MCP_问数增强行动计划.md](LangChain_MCP_问数增强行动计划.md)：LangChain / MCP 方向的专项增强计划，按要求单独保留。

## 说明

原 `docs/` 下多份 Docker 部署、迁移、迭代、升级方案文档已经整合到上面两份文档中，避免用户机交付时不知道该看哪一份。

现在终端宿主卡住了，连 echo OK 都超时，我先不要继续硬跑命令，避免越开越多进程。你新开一个 PowerShell，执行下面这组最稳：

taskkill /F /IM node.exe
taskkill /F /IM python.exe
然后重新启动后端：

cd "D:\万物云\万物云\AI培训\智能问数流程\火山引擎\智能问数项目_v20260330_004926(3)-566fee42a29e\智能问数项目_v20260330_004926"
C:\Users\liutq09\AppData\Local\anaconda3\python.exe backend\app.py
再新开一个 PowerShell 启动前端：

cd "D:\万物云\万物云\AI培训\智能问数流程\火山引擎\智能问数项目_v20260330_004926(3)-566fee42a29e\智能问数项目_v20260330_004926\frontend"
npm run dev
打开：

http://localhost:5173/admin-console
然后按 Ctrl + F5 强刷。
如果这样还老样子，那就不是重启问题了，是 AdminConsole.vue 的 UI 本身还需要继续重构，我再接着把它改成更清晰的 DataWorks 风格权限矩阵。



git push gitee docker-setup --force
推送下方四行代码，第三行改个名字即可
git status
git add .
git commit -m "chore: update smartask LIn 25.2"
git push -u gitee docker-setup



cd /opt/smartask/smartask

docker compose ps
curl -I http://127.0.0.1:8080
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:5002/api/health


cd /opt/smartask/smartask

curl -I --max-time 8 http://47.107.96.192:8080
curl -I --max-time 8 http://127.0.0.1:8080
curl -I --max-time 8 -H "Host: 47.107.96.192" http://127.0.0.1:8080

ss -lntp | grep ':8080'
docker compose logs --tail=80 frontend
同时检查阿里云安全组和宝塔防火墙是否放行：

firewall-cmd --list-ports 2>/dev/null || true
iptables -L -n | grep 8080 || true


SMARTASK_FRONTEND_PORT=8888
BACKEND_URL=http://47.107.96.192:8888
FRONTEND_URL=http://47.107.96.192:8888


git stash push --include-untracked -m "manual-before-update"
git pull --ff-only
bash update.sh


docker logs --tail=200 smartask-backend
docker inspect smartask-backend --format '{{json .State.Health}}'
