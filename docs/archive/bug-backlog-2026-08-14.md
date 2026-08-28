# SmartAsk 问数问题汇总清单（待一次性修复）

> 最后更新：2026-08-16 21:50（经架构师审计 + QA 复测）
> 状态：根因全部定位，等用户确认后分组修复

---

## 一、已确认待修复（14 个）

| # | 问题 | 根因（含精确位置） | 修复位置 | 风险 |
|---|---|---|---|---|
| 1 | 河南代表处业绩 → 95行（单轮也错） | Golden SQL 样本 id=2635 存错误 SQL `LIKE '%代表处%'`（丢"河南"前缀），`same_question_intent`(L1402) 子串匹配命中后 `direct_sample`(L1417) 直接执行 | `direct_sample` 加 guard（样本 SQL 含层级词 LIKE 且 question 点名具体节点 → 不采样本） | 低 |
| 2 | 业务部的业绩，汇总只显示第一个 | ranking 报告 KPI 取 `leader=shown_rows[0]`(L855) 而非全部节点 SUM；top_n=0 走 L910 else 分支仍按"榜首/末位"口径 | `_build_layered_management_report` ranking 分支：top_n=0 改 SUM 汇总口径 | 中 |
| 3 | 商用事业部整体业绩，只4分公司缺业务部 | target_level='商用事业部'（根节点）被 L5142 清空后，兜底链(L5156-5171)无"事业部"分支，落 L5168 else 默认"分公司" | L5168 前加根节点整体 overview 分支 | 低 |
| 4 | 消费者和商用对比，汇总不对 | **answerSummary 空的根因在 `report_spec_builder.py`**：L1432 初始化后仅 filter/ranking/drilldown 三分支，comparison 模式无 answer_summary 构建 → 空 {} | `report_spec_builder.py` comparison 分支补 answer_summary + `_build_layered_management_report`(L1077-1135) comparison 取事业部汇总行 | 中 |
| 5 | 商用和电商对比，崩溃 NoneType.get | `_build_ecommerce_sql:5937` `profile.get("root_nodes")`，profile 为 None（`get_dataset_profile` 因 `dataset_dimension_profiles.json` 0709 被删 → 静默返回 None） | `(profile or {}).get("root_nodes")` 止血 + 评估恢复 profile 数据源（见组C） | 低 |
| 6 | 赵标和靳锋的业绩，只定位到赵标 | `_looks_like_org_subject_question`（**实现在 `ask_engine_entity.py:71`**）True → Agent1 `_agent1_resolve_org_subject` 折叠并列多人名；`_question_subject_names`(L1837) 实际能正确提取 `['赵标','靳锋']` | `ask_engine_entity.py:71` 加"并列多人名"守卫，或 coordinated_names 从原始 question 提取 | 中 |
| 11 | 看下前三的商用分公司 → 弹确认 | 商用 synonyms 只有 7 个、缺"商用"前缀词（消费者也缺"消费者"，电商才有"电商"）；`_dataset_scope_alias_score`(L3175) 对"商用"<90，无法触发 `explicit_dataset_scope_unique`(L3938) | 数据层补 synonym（商用="商用"、消费者="消费者"）+ 承接人（见组E） | 低 |
| 12 | 金额追问"大于5000万的呢"显示为空 | `short_term_memory.resolve_followup`(L93-115) 把上一轮 SQL 全文拼进 effective_question，SQL 文本污染 target_level(→城市分公司)/指标(→燃气定制实际)/阈值(→旧值)，6 个追问变体全挂 | 追问拼接去污染 + 结构化字段透传 | 中 |
| 13 | 城市分公司→追问"低于10%的业务代表"没转商用 | **前端 multi-turn 状态污染**：`smartAskSession.js:1836-1863` 的 `carrySelectedIds` 把 Q1 confirm 选的 selectedDatasetId=[2] 当 Q2 `selected_dataset_ids` → 后端 allowed 锁死 [2] → 跨数据集切换失败 | 前端 `shouldReuseConfirmedDatasetForQuestion` 判断实体归属；后端追问时释放 selected_dataset_ids 限制 | 中 |
| 14 | 业绩最好的分公司，confirm 后返回最差 | confirm_by_boss L9326 追加"先汇总后分析"，「后」命中消费者 ranking.negativeTriggers 的「后」→ resolver.py L755-759 `any(item in text)` direction 反转 asc → SQL ORDER BY ASC 返回最低（江浙沪32.66） | negativeTriggers「后」改精确匹配；或 direction 只基于原始问题、不含 confirm 后缀 | 低 |
| 15 | 无数量排名返回 20 行而非全量（`城市分公司的业绩`/`消费者城市分公司排名`） | `consumer_rank_limit`（four_agent_ask.py:6470-6472）`elif intent_is_ranking: rank_limit = 20`，把"无数量排名"（top_n=0 应全量，§2.1）兜底成 LIMIT 20。这是之前修"哪个最高返回 0 行"加 rank_limit 兜底时的副作用 | `consumer_rank_limit` 区分"全量排名"（top_n=0 → SQL 不加 LIMIT）与"明确数量"（top_n=N → LIMIT N）；或 top_n=0 时返回全量信号 | 中 |
| 16 | "看下前三的业务承接人"（不带前缀）路由到消费者而非电商 | `ask_engine_route.py:94` `_matched_org_level_terms` 的 ordered_terms 漏"承接人/业务承接人"（只有城市分公司/业务代表/代表处/业务部/分公司/条线），导致电商承接人层级无法被识别。而 `four_agent_ask.py:1977` `_GENERIC_LEVEL_ALIASES` 有"业务承接人"→两套层级词表不一致 | `ask_engine_route.py:94` ordered_terms 补"承接人""业务承接人" | 低 |
| 17 | 无数量排名 confirm 后 intent 丢失（`各分公司业绩排名`选消费者 → intent=unknown、rows=82 而非 13 分公司） | confirm 流程污染：confirm 后 refined_query 被追加"补充确认"文本，无数量排名（top_n=0）的 ranking 信号丢失，走默认 SQL 返回全量 | 与 #14 同源：confirm 追加文本不应进入意图解析；意图解析只基于原始问题 | 中 |
| 18 | 消费者排名 confirm 后返回全量（`垫底的三个分公司`选消费者 → top_n=3 对但 rows=82 而非 3） | 消费者排名 SQL 层 top_n=3 未生效，返回"分公司+城市分公司"全量（选商用正常 rows=3） | 消费者 ranking SQL 生成层确认 confirm 路径也应用 top_n LIMIT（与 #15 rank_limit 相关） | 中 |

---

## 二、待重测 → 已复测 PASS（4 个，QA 复测 4/4 通过，后端逻辑正常）

| # | 问题 | 复测 | 结论 |
|---|---|---|---|
| 7 | 电商→江浙沪城市分公司，取电商数据 | ✅ 切消费者 ds=2，7 行 | **后端正常**，之前是环境问题（PG 连接失败） |
| 8 | 东部分公司和南部分公司对比 | ✅ 切商用 ds=3，56 行 | **后端正常** |
| 9 | 达成率低于50%的城市分公司 | ✅ ds=2，49 行 | **后端正常** |
| 13 | 低于10%的业务代表追问 | ✅ 切商用 ds=3，9 行（**不传 selected_dataset_ids 时**） | **后端正常**；唯一问题是前端 carrySelectedIds 把 Q1 selectedDatasetId 污染给 Q2（见 #13 已升格待修复） |

> 注：#13 后端逻辑正确，问题纯在前端 multi-turn 状态传递。

---

## 三、数据事实 / 配置项（非代码 bug）

| # | 项 | 结论 |
|---|---|---|
| 10 | 开单金额超过一个亿的代表处，都是0 | **数据事实**：商用代表处年度开单最大粤东 3055 万，无超 1 亿（分公司才有：东部分公司1.18亿/南部分公司1.04亿）。SQL 解析正确，非 bug |
| A | LLM token 失效 InvalidToken(403) | 8/15 发现 Agent4 调 MiniMax-M2.5 报 403 InvalidToken，规则报告兜底不崩，但 Agent4 智能分析降级。**需换 token** |
| C | 业务经理层级缺失 | 电商数据无"业务经理"层级，追问"业务经理"漏切。需确认是否补数据/别名 |

---

## 四、修复分组（同族合并）

| 组 | 族名 | 成员 | 风险 |
|---|---|---|---|
| A | Golden 样本劫持 | #1 | 低 |
| B | 层级 overview / 报告 KPI 口径 | #2 + #3 + #4（强耦合：修#3后SQL多汇总行，#2/#4口径须配套） | 中 |
| C | profile 依赖残留 | #5 + **get_dataset_profile 静默失效(10+处)** + **_followup_dataset_hint 永远返回[]** | 低→中 |
| D | 追问/confirm 后缀污染意图解析 | #12 + #14（强耦合：同一原则"意图解析只基于原始问题，不含追问SQL/confirm后缀"） | 中 |
| E | synonym / 层级别名配置 | #11 + **承接人层级漏登记**（`_GENERIC_LEVEL_ALIASES`=L1977、`_matched_org_level_terms`=ask_engine_route.py:92） | 低 |
| F | org_subject 拦截器 / 并列多人名 | #6 | 中 |
| G | 前端 multi-turn 状态污染 | #13 | 中 |

---

## 五、修复顺序（先低风险止血 → 再核心重构）

1. **组C #5** — `(profile or {}).get("root_nodes")` 止血崩溃，最低风险；同步评估恢复 profile 数据源
2. **组A #1** — `direct_sample` 加 guard，纯防御
3. **组B-1 #3** — 根节点整体兜底分支，SQL 层单点
4. **组E #11 + 承接人** — 纯 synonym/别名配置
5. **组D-1 #14** — negativeTriggers「后」改精确匹配，单点止血
6. **组B-2 #2 + #4** — 报告 KPI 汇总口径（`_build_layered_management_report` + `report_spec_builder.py`），需回归
7. **组D-2 #12** — 追问结构化字段透传（去 SQL 污染），重构较大
8. **组F #6** — 并列多人名守卫，中风险
9. **组G #13** — 前端 multi-turn 状态污染（前端 + 后端追问释放 selected_dataset_ids）

---

## 六、每步验证（照旧）

- 改完 docker cp 同步容器 + `docker compose restart backend`
- 跑对应诊断脚本 + 全量基线回归
- 每个问题独立 commit

---

## 附：详细诊断报告（按时间）

- `amount-followup-diagnosis-2026-08-15.md` — #12 金额追问（专家团）
- `multiturn-summary-diagnosis-2026-08-14.md` — #1/#2/#3/#4/#5 多轮+汇总
- `comparison-overview-diagnosis-2026-08-14.md` — #3/#4/#5 对比+整体业绩
- `july-fix-restoration-report-2026-08-14.md` — 7月修复还原（#6 并列多人名等）
- 工作日志 `.workbuddy/memory/2026-08-14.md` — 全部问题的完整根因链 + 代码行号
