# LangChain 与 MCP 问数增强行动计划

更新时间：2026-04-28

适用项目：当前仓库“智能问数项目”

---

## 1. 先说结论

如果你的目标是“尽量少改现有系统、尽快提升问数能力、控制风险”，推荐路线不是重写，而是：

1. 保留当前 `four_agent_ask.py` 四 Agent 主链路
2. 先引入 LangChain 做“工具编排层”和“检索增强层”
3. 再引入 MCP 做“标准化上下文接入层”
4. 最后再决定是否把部分流程升级到 LangGraph

一句话判断：

- LangChain 适合你现在马上增强“问数能力”
- MCP 适合你后面增强“上下文接入能力”
- LangGraph 适合你在链路变复杂之后再上，不建议第一步就引入

---

## 2. 为什么这样做

### 2.1 你当前项目已经有可运行主链路

从当前仓库看，你已经有：

- 自然语言问数主入口：`backend/four_agent_ask.py`
- 数据集元数据：`backend/bookshelf_repository.py`
- 路由能力：`backend/datasource_router.py`
- 前端问数页：`frontend/src/views/SmartAsk.vue`
- 结果链展示、确认链路、执行轨迹展示

这意味着你不是“从零做 Agent”，而是在一个已运行系统上做增强。

所以最忌讳两件事：

- 为了引入 LangChain 把现有四 Agent 主链路推倒重来
- 为了跟风 MCP 一次性接很多 server，结果工具过载、调试困难

---

## 3. 你真正该用 LangChain 做什么

### 3.1 不建议的做法

不建议第一步就做：

- 全链路改成 LangChain Agent
- 把 SQL 生成、复核、执行、分析全部交给一个大 Agent
- 一次性上 LangGraph 持久化工作流

这样会导致：

- 改动面太大
- 现有业务规则容易丢
- 调试复杂度显著上升
- 回归风险高

### 3.2 推荐的做法

LangChain 在你项目里最适合做 4 件事：

1. 统一模型调用接口  
把当前直接调用模型的代码逐步包一层，后续方便切模型、切供应商、切提示词策略。

2. 给 SQL 问数增加“工具化调用”  
把“查 schema、查字段释义、查 Golden SQL、查历史案例、生成 SQL、SQL 检查”变成标准 tools。

3. 做问数前置检索增强  
在模型生成 SQL 前，先检索：
   - 数据集画像
   - 字段别名
   - 指标定义
   - 组织层级规则
   - 历史成功 SQL

4. 做更稳的 SQL 自检与重试  
把错误恢复、SQL checker、重试策略结构化，而不是全靠 prompt 拼接。

---

## 4. 你真正该用 MCP 做什么

### 4.1 MCP 不是“让模型更聪明”的魔法

MCP 的价值不是直接提升模型智力，而是让你的 AI 应用更标准地接入外部上下文和工具。

对你这个项目，MCP 最适合承接的是：

- 数据字典
- 数据集 schema
- 指标定义
- 组织画像
- SQL 样例库
- 文档知识库
- 运维信息

### 4.2 你应该优先接哪类 MCP

优先级建议：

1. `metadata-mcp`
作用：给模型提供数据集、字段、指标、别名、口径说明  
价值：直接提升“问数前理解能力”

2. `sql-knowledge-mcp`
作用：提供 Golden SQL、历史成功案例、常见口径模板  
价值：直接提升 SQL 命中率

3. `org-profile-mcp`
作用：提供商用事业部这种组织层级、分公司/代表处/业务部关系  
价值：直接提升组织类问数表现

4. `docs-mcp`
作用：提供项目规则、业务文档、术语解释  
价值：提升复杂问句的业务理解

不建议第一批就接：

- GitHub MCP
- Slack MCP
- 日历/邮箱类 MCP
- 太多通用联网工具型 MCP

这些对“智能问数”主链路帮助不如元数据类 MCP 直接。

---

## 5. 推荐的总体技术路线

## 阶段 0：先做最小治理

目标：在引入 LangChain/MCP 前，把当前主链路做成“可插拔增强”

任务：

- 把 `four_agent_ask.py` 里的核心阶段显式拆分成：
  - 问题理解
  - 数据集路由
  - 元数据准备
  - SQL 生成
  - SQL 复核
  - 执行与分析
- 明确每阶段输入输出结构
- 给每阶段补 trace 字段
- 给 route 增加统一上下文字段，例如：
  - `retrieved_context`
  - `metadata_context`
  - `tool_trace`
  - `sql_repair_trace`

验收标准：

- 任何一个增强能力都能以前置/旁路方式插入
- 不改变现有前端接口结构

## 阶段 1：只引入 LangChain，不改前端协议

目标：先把 LangChain 当成后端增强库，而不是重写框架

建议接入点：

- 新增文件：
  - `backend/llm_gateway.py`
  - `backend/langchain_tools.py`
  - `backend/langchain_retrieval.py`
  - `backend/sql_guardrails.py`

### 阶段 1.1 统一模型层

把当前各处模型调用统一封装，暴露：

- `chat_complete(messages, config)`
- `structured_invoke(schema, prompt, context)`
- `tool_agent_invoke(question, tools, state)`

收益：

- 降低后续替换模型成本
- 让 LangChain 只进入一层，不污染整个项目

### 阶段 1.2 做问数前检索增强

先检索再生成 SQL，检索源包括：

- `bookshelf_repository.py` 里的元数据
- `dataset_dimension_profiles.json`
- 历史 Golden SQL
- 你已有分析提示词与规则文件

推荐产出结构：

```json
{
  "dataset_context": [],
  "metric_context": [],
  "dimension_context": [],
  "golden_sql_context": [],
  "org_context": []
}
```

### 阶段 1.3 做 SQL 生成前工具集

先做 5 个工具就够：

1. `search_dataset_metadata`
2. `search_metric_definition`
3. `search_dimension_profile`
4. `search_golden_sql`
5. `check_sql_safety`

这些工具不需要一开始就通过 Agent 自主循环调用。  
第一版可以先由你程序显式调用，再把结果塞给模型。

验收标准：

- 商用事业部问题的首轮 SQL 成功率提升
- 组织类问数的口径偏差减少
- 不引入前端接口变更

## 阶段 2：引入最小 MCP

目标：先验证 MCP 对“元数据接入”是否真有帮助

建议只做一个自建 MCP Server：

- 名称建议：`smartask-metadata-mcp`

第一版只暴露 3 类能力：

- Resources
  - 数据集定义
  - 字段说明
  - 指标口径
- Tools
  - 按关键字查字段
  - 按数据集查指标
  - 按问题查推荐 schema
- Prompts
  - “组织类问数分析提示词”
  - “SQL 修复提示词”

为什么先做这版：

- 实现成本最低
- 对问数价值最大
- 最容易验证成效

验收标准：

- 通过 MCP 获取元数据的效果不弱于当前本地 JSON/数据库直连方案
- 日志里能看清楚“模型到底拿到了什么上下文”

## 阶段 3：把组织类问数做成专项增强

你当前业务里，组织问题非常关键，尤其是：

- 事业部
- 分公司
- 代表处
- 业务部
- 业务员

这类问题优先做专项增强，收益最高。

建议专项路线：

1. 先用 LangChain 检索组织画像
2. 再用 MCP 统一暴露组织结构资源
3. 生成 SQL 时显式传入：
   - 当前节点
   - 下钻层级
   - 成员范围
   - 统计口径

重点不是“让模型猜”，而是“先检索出组织结构，再让模型生成 SQL”。

验收标准：

- “4大分公司”
- “东部分公司”
- “某代表处”
- “某业务部”

这 4 类问题都能稳定识别当前层级，并给出合理的下钻结果。

## 阶段 4：再评估是否上 LangGraph

只有在下面情况成立时，再考虑 LangGraph：

- 你要长期保存 Agent 状态
- 要支持中断恢复
- 要多阶段人工确认
- 要做复杂分支工作流
- 要把多个工具调用和人工审批串成长期任务

如果只是增强问数，不一定要立刻上 LangGraph。

建议判断线：

- 当前四 Agent 已经够稳定：先不上
- 链路开始变复杂、需要状态机：再上

---

## 6. 具体到你这个项目，推荐的文件改造顺序

### 第 1 批，只做增强骨架

- `backend/four_agent_ask.py`
  - 增加统一的 `context_bundle`
  - 增加检索前置插槽
- `backend/bookshelf_repository.py`
  - 提供更细粒度元数据查询函数
- `backend/dataset_dimension_profiles.py`
  - 对外暴露标准查询接口

新增：

- `backend/llm_gateway.py`
- `backend/langchain_retrieval.py`
- `backend/langchain_tools.py`
- `backend/sql_guardrails.py`

### 第 2 批，补最小 MCP

新增：

- `backend/mcp_servers/metadata_server.py`
- `backend/mcp_servers/org_profile_server.py`

### 第 3 批，补评估与观测

新增：

- `backend/evals/question_regression_set.json`
- `backend/evals/run_eval.py`
- `docs/问数回归用例清单.md`

---

## 7. 你应该优先验证的 10 个问题

不要一接完就靠感觉判断效果，建议固定回归题集：

1. 东部分公司当前年达成率和剩余任务是多少
2. 商用事业部整体达成率是多少
3. 4大分公司分别完成情况如何
4. 哪个分公司达成率最低
5. 东部分公司下属代表处完成情况
6. 某业务部当前年完成情况
7. 某代表处下属业务员完成情况
8. 某指标字段别名问法
9. 跨口径模糊问法
10. 带时间条件和组织条件的组合问法

评估指标建议：

- 数据集路由命中率
- 组织层级识别命中率
- SQL 首次执行成功率
- SQL 修复后成功率
- 最终答案可用率
- 老板确认触发准确率

---

## 8. 成本与“免费”判断

### 8.1 免费的部分

下面这些本身是开源/免费可用的：

- LangChain 框架本身
- LangGraph 框架本身
- MCP 协议本身
- 你自己写的 MCP server

### 8.2 不免费的部分

真正可能持续花钱的是：

- 模型调用
- 云向量库
- 云日志与评估平台
- 远程 MCP 服务

所以“免费引入 LangChain/MCP”这句话，准确说法应该是：

“可以先用免费开源框架增强系统，但推理成本仍主要取决于模型调用。”

---

## 9. 我的专业建议

如果我是这个项目的主设计人，我会这样做：

### 优先级 A：马上做

1. 不重写四 Agent，只加增强层
2. 先接 LangChain 检索与 SQL 工具
3. 先做一个自建 metadata MCP
4. 先把组织类问数做成专项场景

### 优先级 B：有了稳定回归集后再做

1. LangGraph 状态化工作流
2. 多 MCP server 编排
3. 自动评估体系
4. 多轮规划 Agent

### 暂时不要做

1. 一次性接太多 MCP
2. 一次性把所有链路 Agent 化
3. 为了“看起来先进”而重构现有主链路

---

## 10. 可执行的 3 周计划

## 第 1 周：LangChain 最小接入

目标：

- 完成模型统一封装
- 完成元数据检索前置
- 完成 SQL 检查工具

输出：

- `llm_gateway.py`
- `langchain_retrieval.py`
- `langchain_tools.py`

## 第 2 周：组织类问数专项增强

目标：

- 商用事业部组织画像接入检索层
- “4大分公司/分公司/代表处/业务部”识别稳定
- SQL 生成前显式注入组织结构

输出：

- 组织专项回归集
- 组织专项 trace

## 第 3 周：最小 MCP PoC

目标：

- 完成 `metadata-mcp`
- 让主链路可从 MCP 拉取数据集与指标定义
- 与现有直连方式做 A/B 对比

输出：

- `metadata_server.py`
- 对比结论文档

---

## 11. 最终建议

你的项目最合适的顺序是：

1. 先用 LangChain 增强“问数前检索 + SQL 工具化”
2. 再用 MCP 标准化“元数据与组织画像接入”
3. 最后才考虑是否用 LangGraph 重做复杂工作流

不要把 LangChain 当“重构理由”，要把它当“增强工具”。  
不要把 MCP 当“流行协议”，要把它当“上下文接入标准”。

这条路线最稳，也最符合你当前项目阶段。

---

## 12. 参考资料

以下是这份计划主要参考的官方资料：

- LangChain Overview  
  https://docs.langchain.com/oss/python/langchain/overview

- LangGraph Overview  
  https://docs.langchain.com/oss/python/langgraph/overview

- LangChain SQLDatabase Toolkit  
  https://docs.langchain.com/oss/python/integrations/tools/sql_database/

- MCP Architecture Overview  
  https://modelcontextprotocol.io/docs/learn/architecture

- MCP Server Concepts  
  https://modelcontextprotocol.io/docs/learn/server-concepts

- MCP Client Best Practices  
  https://modelcontextprotocol.io/docs/develop/clients/client-best-practices

- MCP Transports  
  https://modelcontextprotocol.io/specification/2025-03-26/basic/transports

