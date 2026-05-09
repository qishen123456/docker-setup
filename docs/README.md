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

git status
git add .
git commit -m "chore: update smartask deployment"
git push -u gitee docker-setup



