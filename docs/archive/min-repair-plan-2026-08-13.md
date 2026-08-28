# SmartAsk 最小修复 Plan — 2026-08-13

> **目标**：只修"用户可直接感受到"的两个错乱，不引入新语义、不动业务元数据、不重写已对齐的基线。
>
> **核心原则**：
> - 一次只改一个文件
> - 每个文件改完先跑诊断脚本验证
> - 不动 baseline 已对齐的 4 项（整体业绩 / 飞书 type-guard / 部署迁移 / index 健康主体）
> - 严格遵守 `smartask-global-constraints` §6 持久化目录保护 + §6.5 节点索引单一事实源原则
> - 每个修复都加 trace log，便于未来 audit

---

## 1. 修复范围（最小集）

| 序号 | 修复点 | 文件 | 行数估计 | 风险 |
|---|---|---|---|---|
| R1 | entity validation 跨数据集场景误剔实体 | `backend/four_agent_ask.py` | +12 / -8 | 中 |
| R2 | 冷启动兜底不验 `flat_alias_index` 健康度 | `backend/app.py` | +6 / -2 | 低 |
| R3 | 在 `config/confirmed_behaviors_baseline.md` 中追加本次修复对应的 baseline 条目 | `config/confirmed_behaviors_baseline.md` | +18 | 无（仅文档） |

**总改动量**：约 +36 行 / -10 行，2 个 .py 文件 + 1 个 .md 文件，零 SQL 生成器改动、零 synonym 改动、零路由层改动、零前端改动。

**不动项**（明确声明）：
- ❌ `backend/dataset_copilot/syyb_rule_generator.py`（268440c 已对齐 baseline）
- ❌ `backend/build_dataset_node_index.py` 的 source_id fallback hardcode 5（保守）
- ❌ 任何数据集的 synonym（业务元数据由数据集维护者定）
- ❌ agent1.route 层（不动路由逻辑）
- ❌ `frontend/*`（前端无需改动）
- ❌ `config/datasources.local.json` 等运行态配置
- ❌ `dataset_node_index.json`（已健康，不动）

---

## 2. R1 — entity validation 跨数据集场景误剔实体

### 2.1 现象（基于 c84e7e3 + 实测）
- `Q1="商用事业部业绩如何"` → route.dataset_ids=[3] (商用)，存入 short_term_memory
- `Q2="其他消费者事业部的数据"`：
  - `_followup_dataset_hint_from_memory` 取到 hint=[3] ✅
  - `_preferred_dataset_conflicts_with_question` 检测到冲突 ✅，但
  - **`_should_keep_followup_dataset_hint` 返回 True**（因为 Q2 字面"其他消费者事业部"被商用 dataset 的 entity resolver 解析到了"事业部"层级词）
  - preferred_dataset_ids 被保留，路由继续走 [3] 商用
- 实测脚本：`diag_e2e.py` 输出 "Q2 '其他消费者事业部业绩' route.dataset_ids = [62] (电商)"
- **根因**：entity validation 仅过滤当前 dataset context 里的伪实体，没考虑 hint 沿用导致的 dataset 漂移

### 2.2 修复设计

**位置**：`backend/four_agent_ask.py:6131-6159`（c84e7e3 章节附近）

**修复策略**：把 `valid_node_names` 从"当前 dataset context"扩展为"hint 涉及的 dataset + 当前 dataset 的并集"。即在 hint_locked 时，把 hint 的 dataset 也加进有效数据集列表，避免误剔跨数据集的实体。

**关键代码段（修复后）**：
```python
# P1防御性修复：实体合法性校验。
# 旧逻辑：仅查当前 dataset context，会在 hint 跨数据集时误剔实体。
# 新逻辑：取"hint 涉及的 dataset ∪ 当前 dataset"两个 context 的实体并集，
#        再过滤伪实体（事业部前缀+层级词，如"消费者分公司"）。
if entity_names:
    valid_node_names = set()
    try:
        # 取并集（修复核心）：当前 dataset + hint dataset
        hint_dataset_ids = [
            int(ds_id) for ds_id in (followup_dataset_hint or [])
        ]
        relevant_dataset_ids = set(hint_dataset_ids) | (
            {int(dataset_id)} if dataset_id else set()
        )
        for ds_id in relevant_dataset_ids:
            ds_context = self.repository.get_dataset_context(
                ds_id, "entity_validation"
            ) if hasattr(self, "repository") else {}
            valid_node_names.update(
                self._node_index_members_by_level(
                    ds_context, set(generic_level_terms)
                )
            )
        # 把通用层级词加入合法集合
        valid_node_names.update(generic_level_terms)
    except Exception:
        valid_node_names = set(generic_level_terms)
    # ... 后续过滤逻辑保持不变（剥离前缀 + is_pseudo_entity 判断）
```

**回滚**：保留旧分支作为 `legacy_fallback`，新逻辑出错时降级到旧分支。

### 2.3 验证
- 跑 `backend/scripts/diag_e2e.py`：
  - Q1="商用事业部业绩如何"，Q2="其他消费者事业部业绩" → 期望 route.dataset_ids=[2] (消费) 或 wait_boss_confirm
  - Q1="商用事业部业绩如何"，Q2="其他事业部业绩如何" → 期望 wait_boss_confirm，候选 [3, 2, 62]
- 跑 `backend/scripts/diag_e2e_2.py`：原有 10 条 followup case 全部回归通过
- 跑回归：`东部分公司的业绩怎么样` / `商用事业部整体业绩` / `消费者和商用的对比`（baseline §1.1 / §1.2.1 案例）

### 2.4 回滚
- 单 commit，单文件，3 行内 revert 即可回到旧行为
- trace log 输出 `entity_validation.source_dataset_ids` 方便定位是哪条 dataset 的 context 被纳入

---

## 3. R2 — 冷启动兜底不验 flat_alias_index 健康度

### 3.1 现象
- 当前 `_ensure_dataset_node_index()` (backend/app.py:273-301) 仅在 `datasets` 字段缺失/为空/损坏时才触发 rebuild
- 但 `flat_alias_index` 也可能因 build 失败 / 磁盘截断 / JSON 部分损坏而变空
- 后果：冷启动加载"半个 index"，运行时 `_dataset_node_index["flat_alias_index"]=[]`，所有 alias 解析 fallback 到 generic level terms，业务实体全部失效
- **严重度**：高（潜在 P1），但**目前未触发**（实测 `flat_alias_index` 334 条完好）

### 3.2 修复设计

**位置**：`backend/app.py:273-301`

**修复策略**：把"flat_alias_index 长度 < 50"也作为 invalid 标志（健康 index 应有 200+ 条）；rebuild 后写回磁盘时打印新文件大小，便于 audit。

**关键代码段（修复后）**：
```python
def _ensure_dataset_node_index():
    index_path = os.path.join(os.path.dirname(__file__), "..", "config", "dataset_node_index.json")
    need_rebuild = False

    if not os.path.exists(index_path):
        print("[dataset_node_index] 文件不存在，自动重建")
        need_rebuild = True
    else:
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("root not dict")
            datasets = data.get("datasets") or []
            flat_alias = data.get("flat_alias_index") or []
            # 修复核心：datasets 非空 + flat_alias_index 健康阈值
            if not datasets:
                print("[dataset_node_index] datasets 为空，自动重建")
                need_rebuild = True
            elif len(flat_alias) < 50:
                # datasets 看似完整但 flat_alias_index 损坏（截断/写一半）
                print(
                    f"[dataset_node_index] datasets={len(datasets)} 但 "
                    f"flat_alias_index={len(flat_alias)} 过小，自动重建"
                )
                need_rebuild = True
        except Exception as e:
            print(f"[dataset_node_index] 文件损坏 ({e})，自动重建")
            need_rebuild = True

    if need_rebuild:
        try:
            from build_dataset_node_index import build_dataset_node_index, write_dataset_node_index
            payload = build_dataset_node_index()
            write_dataset_node_index(payload)
            flat_size = len(payload.get("flat_alias_index", []))
            print(
                f"[dataset_node_index] 重建完成：{len(payload.get('datasets', []))} 数据集，"
                f"flat_alias_index={flat_size} 条"
            )
        except Exception as e:
            print(f"[dataset_node_index] 自动重建失败（不影响启动，飞书同步后会增量构建）: {e}")
```

### 3.3 验证
- 容器内运行 `python -c "import json; json.dump({'datasets': [...], 'flat_alias_index': []}, open('/tmp/broken.json','w'))"` 模拟半损坏 → 启动 backend → 期望日志 `[dataset_node_index] datasets=N 但 flat_alias_index=0 过小，自动重建`
- 跑 `python diag_e2e.py` 跑通
- `/api/health` 返回 200

### 3.4 回滚
- 单 commit，单文件，2 行内 revert
- 阈值 `50` 可在出错时上调/下调，不影响其他逻辑

---

## 4. R3 — baseline 文档补条目

### 4.1 追加位置
`config/confirmed_behaviors_baseline.md` 新增章节「8. 实体合法性与多轮数据集选择」（编号根据实际章节动态调整）

### 4.2 内容（建议文字）

```markdown
## 8. 实体合法性与多轮数据集选择（2026-08-13 增补）

### 8.1 跨数据集实体校验必须取 hint 涉及的 dataset 并集

适用范围：
- 多轮对话（short_term_memory 已有 hint）
- hint 涉及的 dataset 与当前 question 字面命中的 dataset 不一致

代表问题：
- Q1: `商用事业部业绩如何`，Q2: `其他消费者事业部业绩`
- Q1: `商用分公司业绩`，Q2: `看下消费者事业部`

已确认行为：
- entity validation 在跨数据集场景应取"hint 涉及的 dataset ∪ 当前 dataset"两个 context 的实体并集
- 不应仅查当前 dataset context，否则 hint 跨数据集时合法实体被误剔

不允许行为：
- 把 hint 涉及的 dataset 中的合法实体当成伪实体剔除
- 沿用旧 `valid_node_names = self._node_index_members_by_level(context, ...)` 单 dataset 逻辑

当前修复点：
- `backend/four_agent_ask.py` 的 entity validation 段（c84e7e3 章节 + R1 补丁）

### 8.2 冷启动索引健康度必须同时验证 datasets 与 flat_alias_index

适用范围：
- 服务冷启动
- 索引文件被截断 / 部分损坏

已确认行为：
- `_ensure_dataset_node_index()` 必须同时验证 `datasets` 非空 + `flat_alias_index` 长度健康
- 不应仅验证 `datasets`，否则磁盘半损坏会导致运行时加载坏数据

不允许行为：
- 磁盘 datasets=228 节点但 flat_alias_index=0 时仍接受为健康索引
```

### 4.3 验证
- baseline 文件 git diff 仅 +18 行
- 新条目遵循 baseline 文件已有风格（小节编号 / 适用范围 / 代表问题 / 已确认行为 / 不允许行为 / 修复点）

### 4.4 回滚
- 仅文档，可直接 revert commit

---

## 5. 实施顺序（按风险递增）

| Step | Commit | 内容 | 验证 |
|---|---|---|---|
| S1 | `fix: 冷启动索引健康度同时验证 datasets 与 flat_alias_index` | R2 + trace log | 容器重启 + 模拟半损坏 + diag_e2e.py |
| S2 | `fix: entity validation 在 hint 跨数据集时取并集` | R1 + trace log | diag_e2e.py + diag_e2e_2.py + baseline §1 回归 |
| S3 | `docs: baseline 增补跨数据集实体校验 + 索引健康度两条目` | R3 | git diff + baseline 文件无 BOM UTF-8 |

> **关键纪律**：
> - S1、S2 必须**独立 commit**，互不影响
> - S1 先做是因为它影响所有后续诊断脚本的基线
> - S2 后做是因为它需要 S1 的索引健康作底
> - 每个 S 后跑诊断脚本 + 强刷前端 + 用户视觉验证
> - 任何一步失败，立即停止后续 commit，不要叠加

---

## 6. 不在本次修复范围的（明确延后）

| 风险 | 延后原因 |
|---|---|
| source_id fallback hardcode 5 | 当前 index 已正常，且无重现 case；改 fallback 必须先有 fallback 失败的实证 |
| id=62 "刘志伟" 6 节点歧义 | 业务真实（一人跨多业务部），需要数据集维护者确认 dedup 策略 |
| 多轮 "其他事业部" 误命中电商 (id=62) | 这是 routing + synonym 双层问题，触及业务元数据；必须先开 dataset 元数据变更讨论 |
| syyb_rule_generator 注释 lock | 低优，依赖底表结构不演进 |
| dead env vars (`.env.example`) | 不影响运行 |
| 临时 test_*.py / diag_*.py gitignore | 工作树清理，单独 PR |

---

## 7. 回滚预案（单 commit 单 revert）

```bash
# 如果 S1 引发问题
git revert <S1-commit-hash>

# 如果 S2 引发问题
git revert <S2-commit-hash>

# 如果 R3 文档需要调整
git revert <S3-commit-hash>
```

每个 commit 都是单一文件改动 + 单一目的，revert 不影响其他修复。

---

## 8. 验证矩阵（用户视角）

| 用户问题 | 修复后预期 | 修复前实际 | 状态 |
|---|---|---|---|
| `商用事业部整体业绩` | 1 行（底表预置汇总） | ✅ 已对齐 | R0 不动 |
| `其他消费者事业部业绩`（多轮沿用） | 路由到 id=2 或 confirm | 路由到 id=62 电商 | R1 待修 |
| `东部分公司的业绩` | 含东部分公司 + 下级 | ✅ 已对齐 | R0 不动 |
| `刘志伟业绩`（id=62） | confirm 6 候选（业务真实） | 同 | 延后 |
| `冷启动加载半损坏索引` | 自动 rebuild | 加载坏数据 | R2 待修 |
| `其他事业部业绩如何` | confirm 多候选 | 命中 id=62 电商 | 延后（业务元数据） |
| 飞书 sync auto 模式 | type-guard | ✅ 已对齐 | R0 不动 |

---

## 9. 与 SKILL 维护同步

按 `smartask-skill-maintenance` §3，本修复**不需要新增 SKILL**，但需更新 `smartask-global-constraints` §5 踩坑记录，追加一条：

```
### 5.6 entity validation 跨数据集误剔 + 冷启动索引半损坏

**现象**：
- 多轮 follow-up "其他消费者事业部业绩" 在 Q1 是商用事业部时，路由到电商事业部（id=62）
- 冷启动索引半损坏时仍加载坏数据

**根因**：
- entity validation 仅查当前 dataset context，hint 跨数据集时合法实体被误剔
- `_ensure_dataset_node_index()` 只验 datasets 不验 flat_alias_index

**修复要点**：
- entity validation 取 hint dataset ∪ 当前 dataset 并集
- 冷启动索引健康度同时验 datasets + flat_alias_index 长度
- 见 .workbuddy/artifacts/min-repair-plan-2026-08-13.md R1/R2
```

---

**Plan 完成。** 等你拍板后按 S1 → S2 → S3 顺序执行。