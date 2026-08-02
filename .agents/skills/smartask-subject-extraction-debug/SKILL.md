---
name: smartask-subject-extraction-debug
description: >
  SmartAsk 主体提取（从用户问句中识别组织节点/人名）效果异常时的快速排查与定位。
  适用于：用户问「迟昊看下这个人的业绩」「商用事业部丁杰的业绩」「查询三明」
  「一位刘志伟的业绩」「这个人的业绩丁杰」「我想知道靳锋的业绩」等问题，
  但系统返回「未查询到匹配数据」、返回错误节点（如把事业部当主体）、
  或追问链路返回垃圾值阻断裸题器等场景。
  当用户反馈「问不出来」「明明有数据却说没有」「名字被吃掉首字」
  「事业部和人名连在一起时取错了」「倒着说就识别不了」时触发使用。
---

# SmartAsk 主体提取排查

## 环境假设

- 后端容器：`smartask-backend`，端口 `5002`
- 代码目录（容器内）：`/app/backend`
- 本地代码目录：`backend/`
- 节点索引：`config/dataset_node_index.json`（334 个 alias，3 个数据集，8 个层级）
- 关键文件：
  - `backend/four_agent_ask.py` — 主体提取核心
    - `_clean_org_subject_candidate`（line ~3252）：正则清洗口语前后缀
    - `_extract_bare_org_subject_by_node_index`（line ~8658）：裸题器，精确+contains+层级优先+raw兜底
    - `_extract_followup_org_target`（line ~8623）：追问链路，**已委托裸题器**
    - `_contains_match_subject`（line ~8680）：contains 匹配 + 层级优先
    - `_looks_like_org_subject_question`（line ~8695）：判断是否走主体追问
  - `backend/report_spec_builder.py` — 报告契约（focusNodeIsLeaf 等）
  - `frontend/src/components/smartask/ResultDigestCard.vue` — 结果展示
  - `config/confirmed_behaviors_baseline.md` — 已确认效果基线

## 两条提取路径

```
用户问句
  │
  ├─ _extract_followup_org_target(question)     ← 追问链路（优先）
  │    └─ 已委托 → _extract_bare_org_subject_by_node_index
  │
  └─ _extract_bare_org_subject_by_node_index(question)  ← 裸题器
       ├─ 1. _clean_org_subject_candidate → 精确匹配 alias
       ├─ 2. _contains_match_subject(cleaned) → contains + 层级优先
       └─ 3. _contains_match_subject(raw_question) → raw 兜底（倒桩）
```

**关键**：追问链路（line 8749: `followup or bare`）优先于裸题器。如果 followup 返回非空（即使错误），裸题器不跑。2026-08-01 修复前这是 "迟昊" 截图的根因。

## 快速验证脚本

### A. fallback 路径（打桩，不触发 LLM）

```bash
cd smartask
docker exec smartask-backend python -c "
from four_agent_ask import FourAgentAskService
import json
with open('/app/config/dataset_node_index.json') as f:
    idx = json.load(f)
svc = FourAgentAskService.__new__(FourAgentAskService)
svc._dataset_node_index = idx
svc._GENERIC_LEVEL_ALIASES = FourAgentAskService._GENERIC_LEVEL_ALIASES
tests = [
    ('迟昊看下这个人的业绩', '迟昊'),
    ('商用事业部丁杰的业绩', '丁杰'),
    ('三明的业绩', '三明'),
]
for q, expected in tests:
    got = svc._extract_followup_org_target(q)
    print(f'  {\"PASS\" if got==expected else \"FAIL\"}  Q={q!r} got={got!r} expected={expected!r}')
"
```

### B. LLM 主路径（必须验证！fallback 对了不代表主路径对）

```bash
docker exec smartask-backend python -c "
import sys; sys.path.insert(0, '/app/backend')
from four_agent_ask import FourAgentAskService
svc = FourAgentAskService()   # 完整实例化，加载 LLM
trace = {'question': '商用事业部丁杰的业绩', 'steps': [], 'stage': 'test', 'live_callback': None}
r = svc._agent1_resolve_org_subject('商用事业部丁杰的业绩', conversation_context=[], trace=trace)
print('subject:', r.get('subject_name'), 'rewritten:', r.get('rewritten_question'))
# 期望：subject='丁杰', rewritten='丁杰的业绩'
"
```

> ⚠️ 打桩（`__new__`）只测 fallback，不触发 LLM。主体提取改动必须同时验证 LLM 主路径。

## 排查清单

### 1. 返回「未查询到匹配数据」？

- 检查 `_extract_followup_org_target` 是否返回了错误非空值（阻断裸题器）
- 检查 `_clean_org_subject_candidate` 是否把名字吃了（如 "三明"→"明"）
- 检查节点索引 `config/dataset_node_index.json` 是否包含该节点

### 2. 名字首字被吃掉？

- 检查 `_clean_org_subject_candidate` 的数量词正则（line ~3262）
- 正则 `^(?:前|第)?\s*(?:一|二|三|...|\d+)\s*(?:个|大|家|者|位|名)` — 计数词**必须跟量词**才剥
- 如果量词后面的 `?` 被加回来（变成可选），"三明"的"三"会被吃

### 3. 事业部+人名取错（返回事业部而非人名）？

- 检查 `_contains_match_subject` 的层级优先逻辑
- `_NODE_LEVEL_PRIORITY`：业务代表(1) > 城市分公司(3) > 分公司(4) > 事业部(6)
- contains 匹配时取**最细层级**，不是最长 alias

### 4. 倒桩/名字在后半句识别不了？

- 检查裸题器第 3 步 `_contains_match_subject(text)` 是否对**原始问句**做兜底
- cleaner 的 `业绩.*` 正则会把 "这个人的业绩丁杰" 里的 "业绩丁杰" 吃掉，留 "人"
- raw 兜底绕过 cleaner，直接对原文做 contains 匹配

### 5. 追问场景（有对话上文）失败？

- 检查 `_extract_followup_org_target` 是否已委托裸题器
- 旧实现有独立正则（比 cleaner 弱），会返回垃圾值阻断裸题器
- 修复后追问链路 = 裸题器，不再有独立正则

### 6. fallback 对了但用户反馈仍不对？（LLM 主路径问题）

- **最关键**：`_agent1_resolve_org_subject`（line ~8742）是主路径，先调 LLM；`_extract_followup_org_target` / `_extract_bare_org_subject_by_node_index` 只是 fallback
- 原 `result.get("subject_name") or fallback_name` 直接采信 LLM 非空结果——LLM 返回错误非空时 fallback 没机会执行
- 检查 `_pick_finer_subject(llm_subject, fallback_name)` 是否生效：LLM 返回上层组织单元（事业部/分公司）而 fallback 提取到更细节点（业务代表/城市公司）时取更细的
- 检查 rewritten_question 一致性：subject 被纠正后 rewritten_question 是否同步重写
- **必须用脚本 B（真实 LLM）验证，不能只用脚本 A（打桩）**

## 修复后必做

1. 跑全量回归测试（334 节点 × 55 模板）：
   ```bash
   python3 /tmp/smartask_batch_v2.py  # 裸题器路径
   python3 /tmp/smartask_followup_batch.py  # 追问路径
   ```
2. 重建后端镜像：
   ```bash
   docker compose up -d --build backend
   ```
3. 容器内验证关键问句——**同时跑脚本 A（fallback）和脚本 B（LLM 主路径）**
4. 更新 `config/confirmed_behaviors_baseline.md`

## 架构口径

主体提取的长期方向（详见 2026-08-01 工作记录）：

- **cleaner 只负责剥口语前后缀**，不做主体识别
- **主体识别交给提取器的 contains 匹配 + 层级优先**，不动 cleaned 字符串
- **追问链路委托裸题器**，不再维护独立正则
- 残留 ~0.4% 失败走 Layer 5 失败反问（不静默返回 0 行）
- 测试集是活的：发现新问法 → 加模板 → 重跑

## 参考

- 已踩过的具体坑与修复记录：见 [references/common-pitfalls.md](references/common-pitfalls.md)
