# SmartAsk 排名类问题已踩过的坑

## 坑 1：ranking 问题被 `_looks_like_org_subject_question` 误判为组织主体

**现象**：用户问 `看下前三的业务承接人`，confirm 后返回 15 行，标题变成 `的业务承接人的业绩`。  
**根因**：`_looks_like_org_subject_question` 只检查 `has_org_level` 和 `has_spoken_style`，未排除排名关键词。`看下` 命中口语词，`业务承接人` 命中层级词，于是 Agent1 把问题重写成 `业务承接人的业绩`，丢失了 `前三`。  
**修复**：在 `_looks_like_org_subject_question` 开头排除含 `前3/前三/排名/排行/top/最高/最低` 等词的问题。

**验证命令**：
```bash
docker exec smartask-backend python - <<PY
from four_agent_ask import FourAgentAskService
print(FourAgentAskService._looks_like_org_subject_question("看下前三的业务承接人"))  # 应为 False
print(FourAgentAskService._looks_like_org_subject_question("国内业务部的业绩如何"))   # 应为 True
PY
```

---

## 坑 2：confirm 后 `route.refined_query` 引入中间层级，覆盖 `承接人`

**现象**：`看下前三的业务承接人` confirm 后，SQL 变成 `层级级别 = '业务部'`。  
**根因**：`confirm_by_boss` 把 `refined_query` 改写成 `国内业务部的业绩`，与 `original_question` 拼接后，`_resolve_query_intent` 先命中 `业务部`，target_level 被覆盖。  
**修复**：在 `_resolve_query_intent` 中，电商场景下只要文本含 `业务承接人/承接人/负责人/任务承接人`，就把 `target_level` 强制设为 `承接人`，优先级高于 `resolve_target_level_from_text` 的中间层级命中。

---

## 坑 3：`_build_display_title` 基于错误的 `question` 生成重复标题

**现象**：卡片标题显示 `经营分析报告的业务承接人的业务承接人`。  
**根因**：`display_title` 由 `_run_pipeline` 末尾的 `_build_display_title(question, primary)` 生成，如果 `question` 已被改写成 `业务承接人的业绩`，兜底分支会保留错误文本；前端 `ResultDigestCard.vue` 的 kicker `经营分析报告` 再与之拼接，形成重复。  
**修复**：先保证 `question` 不被改写（见坑 1），`display_title` 走 ranking 分支即可生成 `排名前3的承接人`。

---

## 坑 4：SQL 走了 agent_generate，未使用规则 SQL

**现象**：返回列名/层级与预期不符，或没有 LIMIT。  
**根因**：`_select_sql_strategy` 在 `rule_based_sql` 为空时会 fallback 到 Agent2 生成。  
**检查点**：
- 电商数据集 `_build_ecommerce_sql` 是否返回非空字符串
- `_resolve_query_intent` 是否给出 `intent=ranking` 和正确 `target_level`
- 若 `intent=unknown`，`_build_ecommerce_sql` 兜底分支不会加 LIMIT

---

## 坑 5：容器内代码不是最新

**现象**：本地改了代码、测试通过，但现场效果不变。  
**根因**：backend 代码通过 `COPY backend /app/backend` 进入镜像，不是 bind mount。必须重建镜像。  
**修复**：
```bash
docker compose up -d --build backend
```
验证：
```bash
docker exec smartask-backend grep -n "排名/TopN 类问题不应被当作组织主体追问处理" four_agent_ask.py
```

---

## 坑 6：端口复用导致请求打到非 Docker 后端

**现象**：效果时好时坏。  
**根因**：Windows 上 `[::1]:5002` 可能由 `wslrelay.exe` 监听，与 Docker 的 `0.0.0.0:5002` 不是同一进程。  
**排查**：
```powershell
netstat -ano | findstr :5002
```
若出现多个 PID，确认 Docker 进程在 `0.0.0.0:5002`，并检查前端配置的 API 地址。
