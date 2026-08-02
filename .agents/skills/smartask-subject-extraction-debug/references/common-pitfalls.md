# SmartAsk 主体提取已踩过的坑

## 坑 1：首字中文数字/数字被吃掉（Bug A）

**现象**：用户问 `三明的业绩`、`四川代表处的业绩`，系统返回「未查询到匹配数据」。节点索引里明明有 `三明`、`四川代表处`。  
**根因**：`_clean_org_subject_candidate` 的去数量词正则 `^(?:前|第)?\s*(?:三|四|五|六|七|八|九|十|两|几|\d+)\s*(?:个|大|家|者)?` 量词后面的 `?` 让匹配变成可选，导致 "三明" 的 "三" 被当数量词剥掉，cleaned 变成 "明"，节点索引里没有 "明"。  
**影响范围**：所有以 三/四/五/六/七/八/九/十/两/几/数字 开头的节点名。实测 `三明`、`三明城市公司`、`四川`、`四川代表处` 全中招。  
**修复**：去掉量词后面的 `?`（改成 mandatory），同时补 `一|二` 和 `位|名`：
```python
# 旧：r"^(?:前|第)?\s*(?:三|四|五|六|七|八|九|十|两|几|\d+)\s*(?:个|大|家|者)?"
# 新：r"^(?:前|第)?\s*(?:一|二|三|四|五|六|七|八|九|十|两|几|\d+)\s*(?:个|大|家|者|位|名)"
```
计数词必须跟量词（个/位/名...）才剥。"三明"（无量词）不剥，"三个业务部"（有量词）才剥。  
**验证命令**：
```bash
docker exec smartask-backend python -c "
from four_agent_ask import FourAgentAskService
print(FourAgentAskService._clean_org_subject_candidate('三明的业绩'))  # 应为 '三明'，不是 '明'
print(FourAgentAskService._clean_org_subject_candidate('三个业务部的业绩'))  # 应为 '业务部'
"
```

---

## 坑 2：追问链路独立正则阻断裸题器（根因，最严重）

**现象**：用户问 `迟昊看下这个人的业绩`，系统返回「未查询到匹配数据」。裸题器能正确提取 "迟昊"，但追问链路先跑，返回垃圾值 "迟昊看下人"，裸题器根本没机会执行。  
**根因**：`_extract_followup_org_target`（line 8749: `followup or bare`）优先于裸题器。它有自己的独立正则，比 `_clean_org_subject_candidate` 更弱（少 `查询/我想知道/这位` 等词），且没有 contains+层级优先。返回非空（即使错误）后裸题器被阻断。  
**影响范围**：全量跑批 5743/18370 失败（31.3%），其中 5193 条是追问链路返回错误非空阻断裸题器。  
**修复**：追问链路完全委托裸题器，废弃自己的正则和 level_terms 处理：
```python
# 旧：30 行独立正则 + level_terms 处理
# 新：
def _extract_followup_org_target(self, question):
    return self._extract_bare_org_subject_by_node_index(question)
```
同时删掉 `@staticmethod` 装饰器（改成实例方法以调 self）。  
**验证命令**：
```bash
docker exec smartask-backend python -c "
from four_agent_ask import FourAgentAskService
import json
with open('/app/config/dataset_node_index.json') as f:
    idx = json.load(f)
svc = FourAgentAskService.__new__(FourAgentAskService)
svc._dataset_node_index = idx
svc._GENERIC_LEVEL_ALIASES = FourAgentAskService._GENERIC_LEVEL_ALIASES
print(svc._extract_followup_org_target('迟昊看下这个人的业绩'))  # 应为 '迟昊'
"
```

---

## 坑 3：事业部+人名取错，返回事业部而非人名（Bug C）

**现象**：用户问 `商用事业部丁杰的业绩`，系统返回 `商用事业部` 而非 `丁杰`。  
**根因**：裸题器的旧前缀匹配逻辑（`startswith`）挑最长 alias。`"商用事业部丁杰"` 以 `商用事业部` 开头（合法 alias），返回 `商用事业部`。`丁杰` 不在开头，`startswith` 匹配不到。  
**影响范围**：全量跑批 666 条失败（事业部前缀维度 100%）。  
**修复**：新增 `_contains_match_subject` 方法，用 `in`（contains）代替 `startswith`，加层级优先（`_NODE_LEVEL_PRIORITY`：业务代表=1 > 事业部=6）。contains 匹配时取最细层级，不是最长 alias：
```python
# 旧：if normalized_cleaned.startswith(normalized_alias) and len > best_len
# 新：if normalized_alias in normalized_clean，按 (level_priority, -length) 排序
```
"商用事业部丁杰" contains "商用事业部"(prio=6) 和 "丁杰"(prio=1) → 取 prio=1 的 "丁杰"。  
**验证命令**：
```bash
docker exec smartask-backend python -c "
from four_agent_ask import FourAgentAskService
import json
with open('/app/config/dataset_node_index.json') as f:
    idx = json.load(f)
svc = FourAgentAskService.__new__(FourAgentAskService)
svc._dataset_node_index = idx
svc._GENERIC_LEVEL_ALIASES = FourAgentAskService._GENERIC_LEVEL_ALIASES
print(svc._extract_bare_org_subject_by_node_index('商用事业部丁杰的业绩'))  # 应为 '丁杰'
"
```

---

## 坑 4：倒桩/名字在后半句识别不了（Bug B-T22）

**现象**：用户问 `这个人的业绩丁杰`（名字在尾部），系统返回空。  
**根因**：cleaner 的尾部正则 `业绩.*` 把 "业绩丁杰" 整体吃掉，cleaned 变成 "人"。裸题器对 cleaned 做 contains 匹配找不到 "丁杰"。  
**修复**：裸题器加第 3 步 raw 兜底——cleaned 没命中时对**原始问句**做 contains 匹配：
```python
hit = self._contains_match_subject(cleaned) if len(cleaned) >= 2 else ""
if not hit:
    hit = self._contains_match_subject(text)  # raw 兜底
```
"这个人的业绩丁杰" → cleaned="人"（太短）→ raw 兜底对原文 contains → 找到 "丁杰"。  
**注意**：raw 兜底用 `in`（contains），可能引入假阳性（alias 碰巧出现在问句里）。靠 `GENERIC_LEVEL_ALIASES` 排除通用层级词 + 层级优先缓解。  
**验证命令**：
```bash
docker exec smartask-backend python -c "
from four_agent_ask import FourAgentAskService
import json
with open('/app/config/dataset_node_index.json') as f:
    idx = json.load(f)
svc = FourAgentAskService.__new__(FourAgentAskService)
svc._dataset_node_index = idx
svc._GENERIC_LEVEL_ALIASES = FourAgentAskService._GENERIC_LEVEL_ALIASES
print(svc._extract_bare_org_subject_by_node_index('这个人的业绩丁杰'))  # 应为 '丁杰'
"
```

---

## 坑 5：精确匹配用前缀模糊（`_node_index_matches`）导致返回未清理的垃圾值

**现象**：用户问 `迟昊看下这个人的业绩`，裸题器返回 "迟昊看下人" 而非 "迟昊"。  
**根因**：裸题器的精确匹配用 `self._node_index_matches(cleaned)`，该方法做 `startswith` 模糊匹配——"迟昊看下人".startswith("迟昊") 为 True → 返回非空 → 裸题器直接返回 `cleaned`（"迟昊看下人"），跳过 contains 匹配。  
**修复**：精确匹配改成严格相等（`cleaned in alias_names`），不接受前缀模糊：
```python
# 旧：if self._node_index_matches(cleaned): return cleaned
# 新：alias_names = {alias for ...}; if cleaned in alias_names: return cleaned
```
"迟昊看下人" 不在 alias_names → 走 contains 匹配 → 找到 "迟昊"。  
**验证命令**：
```bash
docker exec smartask-backend python -c "
from four_agent_ask import FourAgentAskService
import json
with open('/app/config/dataset_node_index.json') as f:
    idx = json.load(f)
svc = FourAgentAskService.__new__(FourAgentAskService)
svc._dataset_node_index = idx
svc._GENERIC_LEVEL_ALIASES = FourAgentAskService._GENERIC_LEVEL_ALIASES
print(svc._extract_bare_org_subject_by_node_index('迟昊看下这个人的业绩'))  # 应为 '迟昊'，不是 '迟昊看下人'
"
```

---

## 坑 6：cleaner 前缀/指代/量词正则覆盖不足（Bug B + D + E）

**现象**：`查询丁杰`、`看下这位丁杰的业绩`、`一位丁杰的业绩`、`我想知道丁杰的业绩` 全部返回空。  
**根因**：`_clean_org_subject_candidate` 的正则没覆盖这些口语模式：
- 前缀正则缺 `查询`（只有 `查询下`）、`我想知道`、`帮我看看`、`麻烦帮我查下`
- 指代词缺 `这位`、`那位`（只有 `这个`）
- 量词缺 `位`、`名`（只有 `个/大/家/者`），且 `一` 不在计数词列表  
**修复**：
1. 前缀正则补 `查询|我想知道|我想了解|帮我看看|麻烦帮我查下|麻烦帮我看下`
2. 指代词补 `这位|那位`
3. 计数词补 `一|二`，量词补 `位|名`  
**验证命令**：
```bash
docker exec smartask-backend python -c "
from four_agent_ask import FourAgentAskService
for q in ['查询丁杰', '看下这位丁杰的业绩', '一位丁杰的业绩', '我想知道丁杰的业绩']:
    print(f'{q!r} → {FourAgentAskService._clean_org_subject_candidate(q)!r}')
# 期望：丁杰 / 丁杰 / 丁杰 / 丁杰
"
```

---

## 坑 7：cleaner 里 org-prefix strip 有回归

**现象**：初版在 cleaner 里加 org-prefix strip（剥 "商用事业部" 前缀），导致 `万州城市公司咋样了` 的主体 "万州城市公司" 被吃掉，cleaned 变成 "咋样了"。  
**根因**：org-prefix strip 的 lookahead `(?=[\u4e00-\u9fa5]{2,})` 只检查后面有没有 2 字以上中文，但 "咋样了" 是 3 字中文 → lookahead 通过 → 误剥。cleaner 不知道 "万州城市公司" 本身就是主体。  
**修复**：**撤掉 cleaner 里的 org-prefix strip**，改在提取器层用 contains+层级优先解决 Bug C。  
**教训**：cleaner 只负责剥口语前后缀，不做主体识别。主体识别交给提取器的 contains 匹配，不动 cleaned 字符串。  
**验证命令**：
```bash
docker exec smartask-backend python -c "
from four_agent_ask import FourAgentAskService
print(FourAgentAskService._clean_org_subject_candidate('万州城市公司咋样了'))  # 应为 '万州城市公司'，不是 '咋样了'
"
```

---

## 坑 8：LLM(Agent1) 主体解析层级错误（最隐蔽——fallback 修了但主路径没修）

**现象**：用户问 `商用事业部丁杰的业绩`，系统查的是「商用事业部」而不是「丁杰」。坑 1-7 全修完后，fallback（regex）已能正确返回 `丁杰`，但用户反馈仍然不对。  
**根因**：主体解析的**主路径**是 `_agent1_resolve_org_subject`（line 8742），它**先调 LLM**(DeepSeek-V4-Pro)，`_extract_followup_org_target` / `_extract_bare_org_subject_by_node_index` 只是 LLM 失败时的 **fallback**（line 8748）。原逻辑 `result.get("subject_name") or fallback_name` 直接采信 LLM 非空结果——LLM 返回 `商用事业部`（事业部层，非空），fallback 的 `丁杰`（业务代表层）根本没被用。  
**容器内真实 LLM 验证**：
```
Q="商用事业部丁杰的业绩"
LLM 返回: subject_name='商用事业部', rewritten='商用事业部的业绩'  ← 错
fallback: '丁杰'  ← 对，但没被用
```
**影响范围**：所有"事业部/分公司 + 下属人名/城市公司"连写的问法。LLM 倾向取句首的上层组织单元，忽略尾部更具体的下属节点。  
**修复**（2 处编辑）：
1. 新增 `_subject_node_level(name)` + `_pick_finer_subject(llm_subject, fallback_subject)`：查两者节点层级，按 `_NODE_LEVEL_PRIORITY`（业务代表=1 > 城市公司=3 > 分公司=4 > 事业部=6）比较，取更细的；层级相同尊重 LLM
2. `_agent1_resolve_org_subject` line 8802 改为 `subject_name = self._pick_finer_subject(llm_subject, fallback_name)`，并加 rewritten_question 一致性校验（subject 被纠正时同步重写 `f"{subject_name}的{metric}"`）

```python
# 旧：直接采信 LLM
subject_name = self._clean_org_subject_candidate(result.get("subject_name") or fallback_name)
# ...
if subject_name and not rewritten_question:
    rewritten_question = f"{subject_name}的{metric}"

# 新：层级择优 + 一致性校验
llm_subject = self._clean_org_subject_candidate(result.get("subject_name") or fallback_name)
subject_name = self._pick_finer_subject(llm_subject, fallback_name)
# ...
if subject_name and (not rewritten_question or subject_name not in rewritten_question):
    rewritten_question = f"{subject_name}的{metric}"
```
**验证命令**（必须走真实 LLM，不能打桩）：
```bash
docker exec smartask-backend python -c "
import sys; sys.path.insert(0, '/app/backend')
from four_agent_ask import FourAgentAskService
svc = FourAgentAskService()
trace = {'question': '商用事业部丁杰的业绩', 'steps': [], 'stage': 'test', 'live_callback': None}
r = svc._agent1_resolve_org_subject('商用事业部丁杰的业绩', conversation_context=[], trace=trace)
print('subject:', r.get('subject_name'), 'rewritten:', r.get('rewritten_question'))
# 期望：subject='丁杰', rewritten='丁杰的业绩'
# 纯事业部场景 '商用事业部的业绩' → subject='商用事业部'（不过度纠正）
"
```
**教训**：
1. **fallback 修好不等于主路径修好**——必须确认改动在哪条路径生效。坑 1-7 全是 fallback 路径，主路径（LLM）一直没动
2. **LLM 非确定性，不能盲信**——必须有确定性校验层（节点索引层级比较）兜底
3. **打桩验证 ≠ 真实验证**——必须在容器内走真实 LLM 调用，打桩（`__new__`）只测了 fallback，没触发 LLM
4. 用户反馈"没解决"时，第一时间在真实调用链复现，不能只在打桩环境验证
