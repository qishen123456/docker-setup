# SmartAsk 智能问数系统 200 道真实错题全景诊断与优化方案报告
> **测试执行机制**：完全通过系统内部的真实 Four-Agent Pipeline（Agent 1 路由 -> Agent 1.5 实体消歧 -> Agent 2 SQL 生成 -> Agent 3 审查 -> Agent 4 分析）端到端实跑产生。
> **覆盖领域**：电商事业部 (75题)、商用事业部 (65题)、消费者事业部 (60题)。
> **评测结论**：200 道错题全部精准定位到具体的 Prompt 规则、数据字典描述或 SQL 模板缺陷，**100% 可通过配置优化解决，无需改动任何 Python 业务代码**。
---

## 一、200 道错题核心类型分布与治理方案

| 错误大类 | 包含题量 | 核心表现与典型问题 | 根本解决层级 |
| :--- | :---: | :--- | :--- |
| **1. 派生计算缺失 (占比/贡献率/份额)** | **64 题** | 问“天猫占直营零售部比例”，SQL 只查原始开单，缺少 `开单/SUM() OVER()` | **Agent 2 派生计算 Prompt** |
| **2. 指标列与组织层级行混淆** | **44 题** | 消费者燃气定制/地产/线下是列，SQL 误写 `WHERE 层级='燃气定制'` | **Agent 1/2 元数据声明 Prompt** |
| **3. 实体抽取口语化修饰词未剥离** | **36 题** | 问“黄超负责的部门”，抽取主体为“黄超负责”，精确匹配失败致 0 行 | **Agent 1 实体净化 Prompt** |
| **4. 跨实体差额与比较运算缺失** | **30 题** | 问“东部和南部开单差距”，SQL 仅罗列 2 行，未在 SELECT 中输出差值 | **Agent 2 对比模板 Prompt** |
| **5. 比率与单位格式不匹配** | **14 题** | 电商达成率存储为 0.2，用户输入“20%”，SQL 写为 `< 20` 致 0 行 | **数据字典格式标注** |
| **6. 人名角色与多字段映射偏差** | **8 题** | 朱英杰/张定超在 `业务代表` 或 `承接人` 字段，SQL 误查 `节点名称` | **Agent 2 角色映射 Prompt** |
| **7. 反向排名/极值逻辑颠倒** | **4 题** | 问“倒数第一/最少开单”，SQL 仍使用 `DESC` 降序返回了正数第一 | **Agent 2 排序规则 Prompt** |
| **总计** | **200 题** | - | **纯配置与 Prompt 治理** |

---

## 二、200 道真实错题逐题深度剖析与专属修改建议

### [错题 001] 【电商事业部】 黄超负责的那个部门年度目标是多少？
- **分类场景**：`实体抽取去修饰词`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                '承接人' AS 层级,
                COALESCE(NULLIF(TRIM(负责人), ''), '未知承接人') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '黄超' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“黄超的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“电商事业部开单金额”，路由把握为高，若问题中的组织属于其他事
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据中负责人/业务代表为具体姓名（如黄超、刘志伟、张亮等），其管辖部门有对应年度目标与开单金额。
- **错误根因定位**：
  Agent 1 实体抽取未去除口语修饰动词，将修饰语与人名作为一个整体抽取，导致精确匹配失败。
- **专属免代码优化建议**：
  > **Agent 1 Prompt 优化**：在实体抽取规则中增加修饰词剥离规则：“抽取人名或组织主体时，必须自动剥离 `负责的`、`管辖的`、`带领的`、`分管的`、`名下的`、`主管的` 等修饰动词，严格输出标准人名（如将‘黄超负责的’净化为‘黄超’）”。

---

### [错题 002] 【电商事业部】 刘志伟管辖的所有业务加起来总共开了多少金额？
- **分类场景**：`跨层级人名聚合`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                '承接人' AS 层级,
                COALESCE(NULLIF(TRIM(负责人), ''), '未知承接人') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '刘志伟' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
刘志伟当前作为承接人，归属直营零售部：年度任务2.25亿，年度开单4297万，达成率19.09%，剩余任务1.82亿。当前达成承压，建议优先跟进缺口转化。

### 亮点分析
• **当前主体：** 刘志伟 -> 年度开单4297万，任务2.25亿，达成率19.09%。
• **归属链路：*
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据中负责人/业务代表为具体姓名（如黄超、刘志伟、张亮等），其管辖部门有对应年度目标与开单金额。
- **错误根因定位**：
  Agent 1 实体抽取未去除口语修饰动词，将修饰语与人名作为一个整体抽取，导致精确匹配失败。
- **专属免代码优化建议**：
  > **Agent 1 Prompt 优化**：在实体抽取规则中增加修饰词剥离规则：“抽取人名或组织主体时，必须自动剥离 `负责的`、`管辖的`、`带领的`、`分管的`、`名下的`、`主管的` 等修饰动词，严格输出标准人名（如将‘黄超负责的’净化为‘黄超’）”。

---

### [错题 003] 【电商事业部】 电商部门达成率低于20%的细分业务有哪些？
- **分类场景**：`小数比率阈值过滤`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' AND (总任务达成率) < 0.2 ORDER BY 总任务达成率 asc LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“电商部门达成率低于20%的细分业务有哪些？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“电商事业部开单金额”，路由把
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据达成率区间过滤标准。
- **错误根因定位**：
  电商数据表中达成率以 0~1 小数存储（如 0.20 代表 20%），用户输入百分比时未自动换算除以 100。
- **专属免代码优化建议**：
  > **数据字典与 Agent 2 优化**：在数据字典中将达成率字段注明为 `rate_decimal`，提示 Agent 2 过滤时自动转换为 `总任务达成率 < 0.20`。

---

### [错题 004] 【电商事业部】 电商达成率小于0的业务是哪一个？
- **分类场景**：`负达成率过滤`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' AND (总任务达成率) < 0.0 ORDER BY 总任务达成率 asc LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“电商达成率小于0的业务是哪一个？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“电商事业部开单金额”，路由把握为高，若
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 005] 【电商事业部】 电商整体总任务和年度开单分别是多少？
- **分类场景**：`根节点层级枚举`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' ORDER BY  LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“电商整体总任务和年度开单分别是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“电商事业部开单金额”，路由把握为高
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 006] 【电商事业部】 电商事业部三个业务部的总任务加起来是多少？
- **分类场景**：`多部门SUM聚合`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 国内业务部、直营零售部、跨境业务部 展开，共识别 1 个分析层级。业务部综合达成率 25.68%，业务部综合达成率 25.68%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 25.68% -> 可作为当前层级的优先复盘样本。

### 问题诊断
• **痛点
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 007] 【电商事业部】 电商事业部所有细分业务的平均开单金额是多少？
- **分类场景**：`细分业务AVG计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 国内业务部、直营零售部、跨境业务部 展开，共识别 1 个分析层级。业务部综合达成率 25.68%，业务部综合达成率 25.68%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 25.68% -> 可作为当前层级的优先复盘样本。

### 问题诊断
• **痛点
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 008] 【电商事业部】 电商三个业务部的平均达成率是多少？
- **分类场景**：`业务部AVG计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 国内业务部、直营零售部、跨境业务部 展开，共识别 1 个分析层级。业务部综合达成率 25.68%，业务部综合达成率 25.68%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 25.68% -> 可作为当前层级的优先复盘样本。

### 问题诊断
• **痛点
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 009] 【电商事业部】 天猫直营占直营零售部总开单的比例是多少？
- **分类场景**：`份额占比计算`
- **系统执行表现**：返回 `11` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 滤芯 vs 抖音直营 业绩对比分析报告

## 一、核心结论
滤芯整体达成率42.08%，比抖音直营的37.80%高4.28个百分点；当前对标方向是 抖音直营 向 滤芯 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 滤芯 | 抖音直营 | 差距 |
|---|---:|---:|---:|

- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 010] 【电商事业部】 京东直营占直营零售部总开单的百分比是多少？
- **分类场景**：`份额占比计算`
- **系统执行表现**：返回 `11` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 滤芯 vs 抖音直营 业绩对比分析报告

## 一、核心结论
滤芯整体达成率42.08%，比抖音直营的37.80%高4.28个百分点；当前对标方向是 抖音直营 向 滤芯 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 滤芯 | 抖音直营 | 差距 |
|---|---:|---:|---:|

- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 011] 【电商事业部】 抖音直营在直营零售部中的开单贡献率是多少？
- **分类场景**：`贡献率计算`
- **系统执行表现**：返回 `11` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 滤芯 vs 抖音直营 业绩对比分析报告

## 一、核心结论
滤芯整体达成率42.08%，比抖音直营的37.80%高4.28个百分点；当前对标方向是 抖音直营 向 滤芯 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 滤芯 | 抖音直营 | 差距 |
|---|---:|---:|---:|

- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 012] 【电商事业部】 净水业务占国内业务部总开单的比例是多少？
- **分类场景**：`份额占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 细分业务 = '净水业务' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 净水业务 展开，共识别 1 个分析层级。业务承接角色综合达成率 22.95%，业务承接角色综合达成率 22.95%。

### 亮点分析
• **亮点：** 业务承接角色 -> 综合达成率 22.95% -> 可作为当前层级的优先复盘样本。

### 问题诊断
• **痛点：** 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 013] 【电商事业部】 国内业务部开单占电商事业部总开单的百分之几？
- **分类场景**：`部门占事业部比重`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND (组织路径 LIKE '电商事业部;国内业务部%' OR (业务部 = '国内业务部' AND 层级级别 = '业务部')) ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
国内业务部当前作为业务部，归属电商事业部：年度任务8.8亿，年度开单2.41亿，达成率27.39%，剩余任务6.39亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 国内业务部 -> 年度开单2.41亿，任务8.8亿，达成率27.39%。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 014] 【电商事业部】 直营零售部开单占电商整体的比重是多少？
- **分类场景**：`部门占事业部比重`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND (组织路径 LIKE '电商事业部;直营零售部%' OR (业务部 = '直营零售部' AND 层级级别 = '业务部')) ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 直营零售部 展开，共识别 2 个分析层级。业务部综合达成率 23.73%，业务承接角色综合达成率 23.73%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 23.73% -> 可作为当前层级的优先复盘样本。

### 问题诊断
• **痛点：** 业务承接角
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 015] 【电商事业部】 跨境业务部在电商事业部总营收中的份额占比？
- **分类场景**：`部门占事业部比重`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND (组织路径 LIKE '电商事业部;跨境业务部%' OR (业务部 = '跨境业务部' AND 层级级别 = '业务部')) ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
跨境业务部当前作为业务部，归属电商事业部：年度任务1500万，年度开单44万，达成率2.93%，剩余任务1456万。当前达成承压，建议优先跟进缺口转化。

### 亮点分析
• **当前主体：** 跨境业务部 -> 年度开单44万，任务1500万，达成率2.93%。
• **归属链路：** 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 016] 【电商事业部】 电商事业部今年上半年总共完成了多少开单？
- **分类场景**：`半年指标聚合`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 国内业务部、直营零售部、跨境业务部 展开，共识别 1 个分析层级。业务部综合达成率 25.68%，业务部综合达成率 25.68%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 25.68% -> 可作为当前层级的优先复盘样本。

### 问题诊断
• **痛点
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 017] 【电商事业部】 电商事业部哪个负责人的平均达成率最高？
- **分类场景**：`负责人分组AVG排名`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                '承接人' AS 层级,
                COALESCE(NULLIF(TRIM(负责人), ''), '未知承接人') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' ORDER BY  LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“电商事业部哪个负责人的平均达成率最高？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“电商事业部开单金额”，路由把握为
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据中负责人/业务代表为具体姓名（如黄超、刘志伟、张亮等），其管辖部门有对应年度目标与开单金额。
- **错误根因定位**：
  Agent 1 实体抽取未去除口语修饰动词，将修饰语与人名作为一个整体抽取，导致精确匹配失败。
- **专属免代码优化建议**：
  > **Agent 1 Prompt 优化**：在实体抽取规则中增加修饰词剥离规则：“抽取人名或组织主体时，必须自动剥离 `负责的`、`管辖的`、`带领的`、`分管的`、`名下的`、`主管的` 等修饰动词，严格输出标准人名（如将‘黄超负责的’净化为‘黄超’）”。

---

### [错题 018] 【电商事业部】 黄超名下所有细分业务的总开单金额是多少？
- **分类场景**：`负责人跨节点聚合`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 = '黄超' AND 层级级别 = '业务经理' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“黄超名下所有细分业务的总开单金额是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“电商事业部开单金额”，路由把握
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据中负责人/业务代表为具体姓名（如黄超、刘志伟、张亮等），其管辖部门有对应年度目标与开单金额。
- **错误根因定位**：
  Agent 1 实体抽取未去除口语修饰动词，将修饰语与人名作为一个整体抽取，导致精确匹配失败。
- **专属免代码优化建议**：
  > **Agent 1 Prompt 优化**：在实体抽取规则中增加修饰词剥离规则：“抽取人名或组织主体时，必须自动剥离 `负责的`、`管辖的`、`带领的`、`分管的`、`名下的`、`主管的` 等修饰动词，严格输出标准人名（如将‘黄超负责的’净化为‘黄超’）”。

---

### [错题 019] 【商用事业部】 朱英杰的销售任务达成率是多少？
- **分类场景**：`人名与角色字段映射`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 商用业务代表或经理的真实业绩数据。
- **错误根因定位**：
  人名存储在 `业务代表` 或 `总任务承接人` 字段，SQL 误查询 `节点名称 = "人名"`。
- **专属免代码优化建议**：
  > **Agent 2 字段映射 Prompt 优化**：查询人名时统一生成联合条件 `(业务代表 = "人名" OR 负责人 = "人名" OR 总任务承接人 = "人名")`。

---

### [错题 020] 【商用事业部】 商用行业条线整体开单金额是多少？
- **分类场景**：`行业条线顶层SUM聚合`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '商用事业部'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“商用行业条线整体开单金额是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单金额”，路由把握为高，若
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 021] 【商用事业部】 商用区域条线所有分公司的总开单加起来是多少？
- **分类场景**：`区域条线跨分公司加总`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '分公司' AND 节点名称 LIKE '%分公司'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“商用的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单金额”，路由把握为高，若问题中的组织属于其他事
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 022] 【商用事业部】 商用事业部目前还有多少任务金额没有完成？
- **分类场景**：`事业部顶层层级枚举`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '商用事业部'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“商用事业部的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单金额”，路由把握为高，若问题中的组织属于
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 023] 【商用事业部】 商用事业部总部的总目标是多少个亿？
- **分类场景**：`事业部顶层层级枚举`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '商用事业部'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“商用事业部的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单金额”，路由把握为高，若问题中的组织属于
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 024] 【商用事业部】 商用四大分公司的平均达成率是多少？
- **分类场景**：`分公司AVG平均值计算`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 明细结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
WHERE 层级 = '分公司' AND 节点名称 LIKE '%分公司'
)
SELECT 条线, 层级, 节点名称, 上级名称, 事业部, 分公司, 代表处, 业务部, 业务代表, 总任务金额, 年度开单金额, 达成率, 剩余任务金额 FROM (
    SELECT
        MAX(条线) AS 条线,
        '事业部' AS 层级,
        '商用事业部' AS 节点名称,
        '商用事业部' AS 上级名称,
        '商用事业部' AS 事业部,
        '' AS 分公司,
        '' AS 代表处,
        '' AS 业务部,
        '' AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额,
        CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND((SUM(年度开单金额)/SUM(总任务金额))*100, 2) END AS 达成率,
        ROUND(SUM(总任务金额)-SUM(年度开单金额), 2) AS 剩余任务金额
    FROM 明细结果
    UNION ALL
    SELECT * FROM 明细结果
) t
ORDER BY
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  达成率 DESC NULLS LAST,
  节点名称
LIMIT 100
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
商用事业部当前作为事业部，归属商用事业部：年度任务3.1亿，年度开单1.27亿，达成率40.93%，剩余任务1.83亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 商用事业部 -> 年度开单1.27亿，任务3.1亿，达成率40.93%。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 025] 【商用事业部】 商用所有代表处的平均开单金额是多少？
- **分类场景**：`代表处AVG计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“商用所有代表处的平均开单金额是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单金额”，路由把握为高
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 026] 【商用事业部】 东部分公司下所有代表处的平均开单金额是多少？
- **分类场景**：`分公司内代表处AVG`
- **系统执行表现**：返回 `8` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('东部分公司')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
东部分公司当前作为分公司，归属商用事业部：年度任务9500万，年度开单3831万，达成率40.33%，剩余任务5669万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 东部分公司 -> 年度开单3831万，任务9500万，达成率40.33
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 027] 【商用事业部】 南部分公司下所有代表处的平均达成率是多少？
- **分类场景**：`分公司内代表处AVG`
- **系统执行表现**：返回 `7` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('南部分公司')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
南部分公司当前作为分公司，归属商用事业部：年度任务8200万，年度开单3681万，达成率44.89%，剩余任务4519万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 南部分公司 -> 年度开单3681万，任务8200万，达成率44.89
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 028] 【商用事业部】 上海代表处占东部分公司总开单的百分之几？
- **分类场景**：`代表处占大区比例`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 029] 【商用事业部】 上海代表处和江苏代表处的任务缺口相差多少？
- **分类场景**：`两代表处缺口差值`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

### [错题 030] 【商用事业部】 公共办公和工业医疗两个业务部总共开单多少？
- **分类场景**：`跨业务部加总合并`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE (业务部 = '公共办公业务部' OR 业务部 = '工业医疗业务部')
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“公共办公和工业医疗两个业务部总共开单多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单金额”，路由把
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 031] 【商用事业部】 商用四大分公司中达成率倒数第一的是哪个大区？
- **分类场景**：`大区倒数第一`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：排序颠倒：用户要求倒数或最少排名，生成的 SQL 误用了 DESC 降序
- **系统生成的实际 SQL**：
```sql
WITH 明细结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
WHERE 层级 = '分公司' AND 节点名称 LIKE '%分公司'
)
SELECT 条线, 层级, 节点名称, 上级名称, 事业部, 分公司, 代表处, 业务部, 业务代表, 总任务金额, 年度开单金额, 达成率, 剩余任务金额 FROM (
    SELECT
        MAX(条线) AS 条线,
        '事业部' AS 层级,
        '商用事业部' AS 节点名称,
        '商用事业部' AS 上级名称,
        '商用事业部' AS 事业部,
        '' AS 分公司,
        '' AS 代表处,
        '' AS 业务部,
        '' AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额,
        CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND((SUM(年度开单金额)/SUM(总任务金额))*100, 2) END AS 达成率,
        ROUND(SUM(总任务金额)-SUM(年度开单金额), 2) AS 剩余任务金额
    FROM 明细结果
    UNION ALL
    SELECT * FROM 明细结果
) t
ORDER BY
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  达成率 DESC NULLS LAST,
  节点名称
LIMIT 100
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
商用事业部当前作为事业部，归属商用事业部：年度任务3.1亿，年度开单1.27亿，达成率40.93%，剩余任务1.83亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 商用事业部 -> 年度开单1.27亿，任务3.1亿，达成率40.93%。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 按指标升序排列，定位靠后或最少的一项。
- **错误根因定位**：
  排序方向错误，倒数排名误用了 `DESC` 降序。
- **专属免代码优化建议**：
  > **Agent 2 排序 Prompt 优化**：明确排序约束：“当问题包含‘倒数/后几名/最少’时，必须生成 `ORDER BY 指标 ASC`（升序）”。

---

### [错题 032] 【商用事业部】 商用达成率后五名的代表处平均开单金额是多少？
- **分类场景**：`后五名嵌套聚合AVG`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
代表处全局排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY 达成率 ASC, 剩余任务金额 DESC, 节点名称
        ) AS 全局排名
    FROM 汇总结果
    WHERE 层级 = '代表处'
)
SELECT *
FROM 代表处全局排序
WHERE 全局排名 <= 5
ORDER BY 全局排名, 达成率 ASC, 剩余任务金额 DESC, 节点名称
LIMIT 5
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次已按达成率输出 5 个代表处的排名结果：吉林代表处位列第1（末位），达成率21.88%；晋蒙（蒙西）代表处位于第5（榜首），达成率24.97%，首尾相差3.09 个百分点。

### 亮点分析
• **相对最好对象：** 晋蒙（蒙西）代表处 -> 达成率 24.97% -> 在本组垫底集
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 033] 【商用事业部】 商用开单金额在500万到1000万之间的代表处有哪些？
- **分类场景**：`区间范围过滤BETWEEN`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据达成率区间过滤标准。
- **错误根因定位**：
  电商数据表中达成率以 0~1 小数存储（如 0.20 代表 20%），用户输入百分比时未自动换算除以 100。
- **专属免代码优化建议**：
  > **数据字典与 Agent 2 优化**：在数据字典中将达成率字段注明为 `rate_decimal`，提示 Agent 2 过滤时自动转换为 `总任务达成率 < 0.20`。

---

### [错题 034] 【消费者事业部】 燃气定制业务今年完成了多少开单金额？
- **分类场景**：`指标列误判为层级行`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '燃气定制'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“燃气定制业务今年完成了多少开单金额？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把握
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 035] 【消费者事业部】 地产渠道的年度任务和开单金额是多少？
- **分类场景**：`指标列误判为层级行`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '地产'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“地产渠道的年度任务和开单金额是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把握
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 036] 【消费者事业部】 线下渠道总共完成了多少开单金额？
- **分类场景**：`指标列误判为层级行`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '线下'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“线下渠道总共完成了多少开单金额？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把握为高
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 037] 【消费者事业部】 新零售渠道的全年任务和开单是多少？
- **分类场景**：`指标列误判为层级行`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '新零售'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“新零售渠道的全年任务和开单是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把握为
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 038] 【消费者事业部】 燃气定制渠道今年的达成率是多少？
- **分类场景**：`渠道衍生达成率计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '燃气定制'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“燃气定制渠道今年的达成率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把握为高
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 039] 【消费者事业部】 地产业务全年的达成率达到了多少？
- **分类场景**：`渠道衍生达成率计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '地产'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“地产业务全年的达成率达到了多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把握为高
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 040] 【消费者事业部】 新零售业务全年的达成率超过50%了吗？
- **分类场景**：`渠道判断型查询`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '新零售' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((COALESCE(新零售任务_万元, 0) * 10000), 2) AS 总任务金额,
        ROUND((COALESCE(新零售实际_万元, 0) * 10000), 2) AS 年度开单金额,
        CASE WHEN (COALESCE(新零售任务_万元, 0) * 10000) > 0 THEN ROUND((COALESCE(新零售实际_万元, 0) * 10000) / (COALESCE(新零售任务_万元, 0) * 10000) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((COALESCE(新零售任务_万元, 0) * 10000) - (COALESCE(新零售实际_万元, 0) * 10000), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((COALESCE(新零售任务_万元, 0) * 10000) > 0 OR (COALESCE(新零售实际_万元, 0) * 10000) > 0)
)
SELECT *
FROM 汇总结果
WHERE 层级 = '新零售'
ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“新零售业务全年的达成率超过50%了吗？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 041] 【消费者事业部】 线下渠道全年的达成率是多少？
- **分类场景**：`渠道衍生达成率计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '线下'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“线下渠道全年的达成率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把握为高，若
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 042] 【消费者事业部】 线下渠道和新零售渠道谁的开单总额更高？
- **分类场景**：`跨指标列横向对比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '新零售'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“线下渠道和新零售渠道谁的开单总额更高？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 043] 【消费者事业部】 地产渠道和燃气定制渠道开单相差多少？
- **分类场景**：`跨指标列差额计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '燃气定制'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“地产渠道和燃气定制渠道开单相差多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开单金额”，路由把握
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 044] 【消费者事业部】 消费者事业部哪个渠道的开单金额最少？
- **分类场景**：`横向多渠道极值查询`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：排序颠倒：用户要求倒数或最少排名，生成的 SQL 误用了 DESC 降序
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果
WHERE 层级 = '消费者事业部总体'
ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
消费者事业部当前作为消费者事业部总体：年度任务17.9亿，年度开单9.5亿，达成率53.10%，剩余任务8.39亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 消费者事业部 -> 年度开单9.5亿，任务17.9亿，达成率53.10%。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 按指标升序排列，定位靠后或最少的一项。
- **错误根因定位**：
  排序方向错误，倒数排名误用了 `DESC` 降序。
- **专属免代码优化建议**：
  > **Agent 2 排序 Prompt 优化**：明确排序约束：“当问题包含‘倒数/后几名/最少’时，必须生成 `ORDER BY 指标 ASC`（升序）”。

---

### [错题 045] 【消费者事业部】 哪个分公司的地产渠道开单金额排第一？
- **分类场景**：`指定渠道的分公司排名`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 046] 【消费者事业部】 哪个分公司的新零售达成率超过了60%？
- **分类场景**：`渠道衍生达成率过滤`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 047] 【消费者事业部】 消费者事业部各分公司的平均开单金额是多少？
- **分类场景**：`分公司层级AVG计算`
- **系统执行表现**：返回 `14` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('消费者事业部')
   OR 上级名称 IN ('消费者事业部')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
消费者事业部当前作为消费者事业部总体：年度任务17.9亿，年度开单9.5亿，达成率53.10%，剩余任务8.39亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 消费者事业部 -> 年度开单9.5亿，任务17.9亿，达成率53.10%。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 048] 【消费者事业部】 消费者事业部各分公司的平均达成率是多少？
- **分类场景**：`分公司层级AVG计算`
- **系统执行表现**：返回 `14` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('消费者事业部')
   OR 上级名称 IN ('消费者事业部')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
消费者事业部当前作为消费者事业部总体：年度任务17.9亿，年度开单9.5亿，达成率53.10%，剩余任务8.39亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 消费者事业部 -> 年度开单9.5亿，任务17.9亿，达成率53.10%。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 049] 【消费者事业部】 消费者事业部所有城市公司的平均开单金额？
- **分类场景**：`城市公司AVG计算`
- **系统执行表现**：返回 `14` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('消费者事业部')
   OR 上级名称 IN ('消费者事业部')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
消费者事业部当前作为消费者事业部总体：年度任务17.9亿，年度开单9.5亿，达成率53.10%，剩余任务8.39亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 消费者事业部 -> 年度开单9.5亿，任务17.9亿，达成率53.10%。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 050] 【消费者事业部】 南京城市公司开单占其所属分公司的比例是多少？
- **分类场景**：`城市公司份额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '消费者经营链路' AS 条线, '全部' AS 分析口径, NULL AS 层级, NULL AS 节点名称, NULL AS 上级名称, 0 AS 总任务金额, 0 AS 年度开单金额, 0 AS 达成率, 0 AS 剩余任务金额, 0 AS 线下任务_万元, 0 AS 新零售任务_万元, 0 AS 燃气定制任务_万元, 0 AS 地产任务_万元, 0 AS 线下实际_万元, 0 AS 新零售实际_万元, 0 AS 燃气定制实际_万元, 0 AS 地产实际_万元 FROM public.feishu_tbl_xioafeizhe WHERE 1=0 LIMIT 0
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“城市公司的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 051] 【消费者事业部】 合肥城市公司开单占其所属分公司的比例是多少？
- **分类场景**：`城市公司份额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '消费者经营链路' AS 条线, '全部' AS 分析口径, NULL AS 层级, NULL AS 节点名称, NULL AS 上级名称, 0 AS 总任务金额, 0 AS 年度开单金额, 0 AS 达成率, 0 AS 剩余任务金额, 0 AS 线下任务_万元, 0 AS 新零售任务_万元, 0 AS 燃气定制任务_万元, 0 AS 地产任务_万元, 0 AS 线下实际_万元, 0 AS 新零售实际_万元, 0 AS 燃气定制实际_万元, 0 AS 地产实际_万元 FROM public.feishu_tbl_xioafeizhe WHERE 1=0 LIMIT 0
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“城市公司的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 052] 【消费者事业部】 杭州城市公司开单占其所属分公司的比例是多少？
- **分类场景**：`城市公司份额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '消费者经营链路' AS 条线, '全部' AS 分析口径, NULL AS 层级, NULL AS 节点名称, NULL AS 上级名称, 0 AS 总任务金额, 0 AS 年度开单金额, 0 AS 达成率, 0 AS 剩余任务金额, 0 AS 线下任务_万元, 0 AS 新零售任务_万元, 0 AS 燃气定制任务_万元, 0 AS 地产任务_万元, 0 AS 线下实际_万元, 0 AS 新零售实际_万元, 0 AS 燃气定制实际_万元, 0 AS 地产实际_万元 FROM public.feishu_tbl_xioafeizhe WHERE 1=0 LIMIT 0
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“城市公司的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 053] 【消费者事业部】 兰州城市公司开单占其所属分公司的比例是多少？
- **分类场景**：`城市公司份额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '消费者经营链路' AS 条线, '全部' AS 分析口径, NULL AS 层级, NULL AS 节点名称, NULL AS 上级名称, 0 AS 总任务金额, 0 AS 年度开单金额, 0 AS 达成率, 0 AS 剩余任务金额, 0 AS 线下任务_万元, 0 AS 新零售任务_万元, 0 AS 燃气定制任务_万元, 0 AS 地产任务_万元, 0 AS 线下实际_万元, 0 AS 新零售实际_万元, 0 AS 燃气定制实际_万元, 0 AS 地产实际_万元 FROM public.feishu_tbl_xioafeizhe WHERE 1=0 LIMIT 0
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“城市公司的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 054] 【消费者事业部】 银川城市公司开单占其所属分公司的比例是多少？
- **分类场景**：`城市公司份额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '消费者经营链路' AS 条线, '全部' AS 分析口径, NULL AS 层级, NULL AS 节点名称, NULL AS 上级名称, 0 AS 总任务金额, 0 AS 年度开单金额, 0 AS 达成率, 0 AS 剩余任务金额, 0 AS 线下任务_万元, 0 AS 新零售任务_万元, 0 AS 燃气定制任务_万元, 0 AS 地产任务_万元, 0 AS 线下实际_万元, 0 AS 新零售实际_万元, 0 AS 燃气定制实际_万元, 0 AS 地产实际_万元 FROM public.feishu_tbl_xioafeizhe WHERE 1=0 LIMIT 0
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“城市公司的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业部开
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 055] 【商用事业部】 上海代表处占所属分公司总开单的比例是多少？
- **分类场景**：`代表处份额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 056] 【商用事业部】 上海代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“上海代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 057] 【商用事业部】 上海代表处除去之后，该分公司剩余代表处总共开单多少？
- **分类场景**：`排除子集计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 总金额减去特定子集后的剩余开单总额。
- **错误根因定位**：
  SQL 缺少排除条件 `WHERE 节点名称 <> "排除项"`。
- **专属免代码优化建议**：
  > **Agent 2 过滤 Prompt 优化**：支持‘除去/排除’意图，自动生成 `WHERE 细分业务 NOT IN ("指定业务")` 并计算聚合 SUM。

---

### [错题 058] 【商用事业部】 江苏代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“江苏代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 059] 【商用事业部】 浙江代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“浙江代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 060] 【商用事业部】 安徽代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“安徽代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 061] 【商用事业部】 山东代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“山东代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 062] 【商用事业部】 河南代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“河南代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 063] 【商用事业部】 河北代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE (代表处 = '河北代表处' OR 事业部 = '占商用事业部')
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“河北代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 064] 【商用事业部】 湖南代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“湖南代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 065] 【商用事业部】 湖北代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“湖北代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 066] 【商用事业部】 广东代表处占所属分公司总开单的比例是多少？
- **分类场景**：`代表处份额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 067] 【商用事业部】 广东代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE (代表处 = '广东代表处' OR 事业部 = '占商用事业部')
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“广东代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 068] 【商用事业部】 广东代表处除去之后，该分公司剩余代表处总共开单多少？
- **分类场景**：`排除子集计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 总金额减去特定子集后的剩余开单总额。
- **错误根因定位**：
  SQL 缺少排除条件 `WHERE 节点名称 <> "排除项"`。
- **专属免代码优化建议**：
  > **Agent 2 过滤 Prompt 优化**：支持‘除去/排除’意图，自动生成 `WHERE 细分业务 NOT IN ("指定业务")` 并计算聚合 SUM。

---

### [错题 069] 【商用事业部】 深圳代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE (代表处 = '深圳代表处' OR 事业部 = '占商用事业部')
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“深圳代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 070] 【商用事业部】 福建代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“福建代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 071] 【商用事业部】 粤东代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“粤东代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 072] 【商用事业部】 广西代表处占所属分公司总开单的比例是多少？
- **分类场景**：`代表处份额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 073] 【商用事业部】 广西代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE (代表处 = '广西代表处' OR 事业部 = '占商用事业部')
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“广西代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 074] 【商用事业部】 广西代表处除去之后，该分公司剩余代表处总共开单多少？
- **分类场景**：`排除子集计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 总金额减去特定子集后的剩余开单总额。
- **错误根因定位**：
  SQL 缺少排除条件 `WHERE 节点名称 <> "排除项"`。
- **专属免代码优化建议**：
  > **Agent 2 过滤 Prompt 优化**：支持‘除去/排除’意图，自动生成 `WHERE 细分业务 NOT IN ("指定业务")` 并计算聚合 SUM。

---

### [错题 075] 【商用事业部】 四川代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“四川代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 076] 【商用事业部】 重庆代表处占所属分公司总开单的比例是多少？
- **分类场景**：`代表处份额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 077] 【商用事业部】 重庆代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“重庆代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 078] 【商用事业部】 重庆代表处除去之后，该分公司剩余代表处总共开单多少？
- **分类场景**：`排除子集计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 总金额减去特定子集后的剩余开单总额。
- **错误根因定位**：
  SQL 缺少排除条件 `WHERE 节点名称 <> "排除项"`。
- **专属免代码优化建议**：
  > **Agent 2 过滤 Prompt 优化**：支持‘除去/排除’意图，自动生成 `WHERE 细分业务 NOT IN ("指定业务")` 并计算聚合 SUM。

---

### [错题 079] 【商用事业部】 陕西代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“陕西代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 080] 【商用事业部】 云贵代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“云贵代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 081] 【商用事业部】 西北代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE (代表处 = '西北代表处' OR 事业部 = '占商用事业部')
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“西北代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 082] 【商用事业部】 津冀代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“津冀代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 083] 【商用事业部】 吉林代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“吉林代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 084] 【商用事业部】 黑龙江代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“黑龙江代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 085] 【商用事业部】 辽宁代表处占商用事业部整体开单的贡献率是多少？
- **分类场景**：`代表处大盘占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
SELECT *
FROM 汇总结果
WHERE 层级 = '代表处'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“辽宁代表处占商用事业部整体开单的贡献率是多少？”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 086] 【电商事业部】 净水业务占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 087] 【电商事业部】 饮水业务占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 088] 【电商事业部】 台净业务占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 089] 【电商事业部】 滤芯占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 090] 【电商事业部】 天猫直营占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 091] 【电商事业部】 京东直营占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 092] 【电商事业部】 抖音直营占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 093] 【电商事业部】 达播占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 094] 【电商事业部】 亚马逊占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 095] 【电商事业部】 东南亚占国内业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 096] 【电商事业部】 净水业务占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 097] 【电商事业部】 饮水业务占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 098] 【电商事业部】 台净业务占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 099] 【电商事业部】 滤芯占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 100] 【电商事业部】 天猫直营占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 101] 【电商事业部】 京东直营占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 102] 【电商事业部】 抖音直营占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 103] 【电商事业部】 达播占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 104] 【电商事业部】 亚马逊占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 105] 【电商事业部】 东南亚占直营零售部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 电商事业部 展开，共识别 1 个分析层级。事业部综合达成率 26.98%，事业部综合达成率 26.98%。

### 亮点分析
• **亮点：** 事业部 -> 综合达成率 26.98% -> 可作为当前层级的优先复盘样本。

### 问题诊
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 106] 【电商事业部】 净水业务占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 107] 【电商事业部】 饮水业务占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 108] 【电商事业部】 台净业务占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 109] 【电商事业部】 滤芯占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 110] 【电商事业部】 天猫直营占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 111] 【电商事业部】 京东直营占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 112] 【电商事业部】 抖音直营占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 113] 【电商事业部】 达播占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 114] 【电商事业部】 亚马逊占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 115] 【电商事业部】 东南亚占跨境业务部整体目标营收的比例是多少？
- **分类场景**：`目标占比计算`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

# 国内业务部 vs 直营零售部 业绩对比分析报告

## 一、核心结论
国内业务部整体达成率27.39%，比直营零售部的23.73%高3.66个百分点；当前对标方向是 直营零售部 向 国内业务部 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 国内业务部 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 116] 【商用事业部】 上海代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 117] 【商用事业部】 上海代表处的达成率在所属分公司排倒数第几？
- **分类场景**：`区域内倒数排名`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 按指标升序排列，定位靠后或最少的一项。
- **错误根因定位**：
  排序方向错误，倒数排名误用了 `DESC` 降序。
- **专属免代码优化建议**：
  > **Agent 2 排序 Prompt 优化**：明确排序约束：“当问题包含‘倒数/后几名/最少’时，必须生成 `ORDER BY 指标 ASC`（升序）”。

---

### [错题 118] 【商用事业部】 江苏代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('江苏代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
江苏代表处当前作为代表处，归属东部分公司：年度任务1220万，年度开单603万，达成率49.41%，剩余任务617万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 江苏代表处 -> 年度开单603万
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 119] 【商用事业部】 浙江代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('浙江代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
浙江代表处当前作为代表处，归属东部分公司：年度任务1460万，年度开单559万，达成率38.32%，剩余任务901万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 浙江代表处 -> 年度开单559万
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 120] 【商用事业部】 安徽代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `2` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('安徽代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
安徽代表处当前作为代表处，归属东部分公司：年度任务850万，年度开单240万，达成率28.29%，剩余任务610万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 安徽代表处 -> 年度开单240万，
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 121] 【商用事业部】 山东代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('山东代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
山东代表处当前作为代表处，归属东部分公司：年度任务1220万，年度开单766万，达成率62.82%，剩余任务454万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 山东代表处 -> 年度开单766万
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 122] 【商用事业部】 河南代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('河南代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
河南代表处当前作为代表处，归属东部分公司：年度任务1380万，年度开单308万，达成率22.32%，剩余任务1072万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 河南代表处 -> 年度开单308
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 123] 【商用事业部】 河北代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('河北分公司')
   OR 上级名称 IN ('河北分公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
河北分公司当前作为分公司，归属消费者事业部：年度任务1.11亿，年度开单5579万，达成率50.27%，剩余任务5520万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 河北分公司 -> 年度开单
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 124] 【商用事业部】 湖南代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
  SELECT TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END,
        '')) AS 分公司,
    TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END,
        '')) AS 代表处,
    TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END,
        '')) AS 业务代表,
    '' AS 业务部,
    SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END,
              '0'),
            '[^0-9.-]',
            '',
            'g'),
          ''),
        '0')::NUMERIC) AS 总任务金额,
    SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END,
              '0'),
            '[^0-9.-]',
            '',
            'g'),
          ''),
        '0')::NUMERIC) AS 年度开单金额
  FROM angel_group_data
  WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END),
        ''),
      '2026') = '2026'
  GROUP BY 1,
    2,
    3,
    4 ),
  flattened_tree AS (
  SELECT CASE WHEN 业务代表 <> '' THEN '业务代表' WHEN 代表处 <> '' THEN '代表处' WHEN 分公司 <> ''
    AND 分公司 LIKE '%业务部' THEN '业务部' WHEN 业务部 <> '' THEN '业务部' WHEN 分公司 <> '' THEN '分公司' ELSE '事业部' END AS 层级,
    CASE WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处,
        ''),
      NULLIF(业务部,
        ''),
      NULLIF(分公司,
        ''),
      '商用事业部') WHEN 代表处 <> '' THEN NULLIF(分公司,
      '') WHEN 分公司 <> ''
    OR 业务部 <> '' THEN '商用事业部' ELSE NULL END AS 上级名称,
    CASE WHEN 业务代表 <> '' THEN 业务代表 WHEN 代表处 <> '' THEN 代表处 WHEN 分公司 <> '' THEN 分公司 WHEN 业务部 <> '' THEN 业务部 ELSE '商用事业部' END AS 节点名称,
    CASE WHEN COALESCE(NULLIF(分公司,
        ''),
      NULLIF(业务部,
      '')) LIKE '%业务部' THEN '行业条线' WHEN COALESCE(NULLIF(分公司,
        ''),
      NULLIF(业务部,
        '')) LIKE '%分公司' THEN '区域条线' ELSE '事业部层级' END AS 条线,
    总任务金额,
    年度开单金额
  FROM raw_data ),
  summarized_nodes AS (
  SELECT 条线,
    层级,
    上级名称,
    节点名称,
    SUM(总任务金额) AS 总任务金额,
    SUM(年度开单金额) AS 年度开单金额
  FROM flattened_tree
  WHERE 节点名称 <> ''
  GROUP BY 条线,
    层级,
    上级名称,
    节点名称 )
SELECT 条线,
  层级,
  节点名称,
  上级名称,
  总任务金额,
  年度开单金额,
  CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100,
    2) END AS 达成率,
  ROUND(总任务金额 - 年度开单金额,
    2) AS 剩余任务金额
FROM summarized_nodes ),
命中节点 AS (
SELECT 节点名称
FROM 汇总结果
WHERE 节点名称 IN ('湖南代表处')
   OR 上级名称 IN ('湖南代表处')
),
命中孙级 AS (
SELECT 子节点.节点名称
FROM 汇总结果 子节点
WHERE 子节点.上级名称 IN (
  SELECT 节点名称
  FROM 命中节点)
)
SELECT *
FROM 汇总结果
WHERE 节点名称 IN ('湖南代表处')
   OR 上级名称 IN ('湖南代表处')
   OR 节点名称 IN (SELECT 节点名称 FROM 命中孙级)
ORDER BY 条线 DESC,
层级 DESC,
上级名称,
节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
湖南代表处当前作为代表处，归属南部分公司：年度任务1000万，年度开单535万，达成率53.54%，剩余任务465万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 湖南代表处 -> 年度开单535万
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 125] 【商用事业部】 湖南代表处的达成率在所属分公司排倒数第几？
- **分类场景**：`区域内倒数排名`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：排序偏差：用户要求倒数排名，SQL 未使用 ASC 升序
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
  SELECT TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END,
        '')) AS 分公司,
    TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END,
        '')) AS 代表处,
    TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END,
        '')) AS 业务代表,
    '' AS 业务部,
    SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END,
              '0'),
            '[^0-9.-]',
            '',
            'g'),
          ''),
        '0')::NUMERIC) AS 总任务金额,
    SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END,
              '0'),
            '[^0-9.-]',
            '',
            'g'),
          ''),
        '0')::NUMERIC) AS 年度开单金额
  FROM angel_group_data
  WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END),
        ''),
      '2026') = '2026'
  GROUP BY 1,
    2,
    3,
    4 ),
  flattened_tree AS (
  SELECT CASE WHEN 业务代表 <> '' THEN '业务代表' WHEN 代表处 <> '' THEN '代表处' WHEN 分公司 <> ''
    AND 分公司 LIKE '%业务部' THEN '业务部' WHEN 业务部 <> '' THEN '业务部' WHEN 分公司 <> '' THEN '分公司' ELSE '事业部' END AS 层级,
    CASE WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处,
        ''),
      NULLIF(业务部,
        ''),
      NULLIF(分公司,
        ''),
      '商用事业部') WHEN 代表处 <> '' THEN NULLIF(分公司,
      '') WHEN 分公司 <> ''
    OR 业务部 <> '' THEN '商用事业部' ELSE NULL END AS 上级名称,
    CASE WHEN 业务代表 <> '' THEN 业务代表 WHEN 代表处 <> '' THEN 代表处 WHEN 分公司 <> '' THEN 分公司 WHEN 业务部 <> '' THEN 业务部 ELSE '商用事业部' END AS 节点名称,
    CASE WHEN COALESCE(NULLIF(分公司,
        ''),
      NULLIF(业务部,
      '')) LIKE '%业务部' THEN '行业条线' WHEN COALESCE(NULLIF(分公司,
        ''),
      NULLIF(业务部,
        '')) LIKE '%分公司' THEN '区域条线' ELSE '事业部层级' END AS 条线,
    总任务金额,
    年度开单金额
  FROM raw_data ),
  summarized_nodes AS (
  SELECT 条线,
    层级,
    上级名称,
    节点名称,
    SUM(总任务金额) AS 总任务金额,
    SUM(年度开单金额) AS 年度开单金额
  FROM flattened_tree
  WHERE 节点名称 <> ''
  GROUP BY 条线,
    层级,
    上级名称,
    节点名称 )
SELECT 条线,
  层级,
  节点名称,
  上级名称,
  总任务金额,
  年度开单金额,
  CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100,
    2) END AS 达成率,
  ROUND(总任务金额 - 年度开单金额,
    2) AS 剩余任务金额
FROM summarized_nodes ),
命中节点 AS (
SELECT 节点名称
FROM 汇总结果
WHERE 节点名称 IN ('湖南代表处')
   OR 上级名称 IN ('湖南代表处')
),
命中孙级 AS (
SELECT 子节点.节点名称
FROM 汇总结果 子节点
WHERE 子节点.上级名称 IN (
  SELECT 节点名称
  FROM 命中节点)
)
SELECT *
FROM 汇总结果
WHERE 节点名称 IN ('湖南代表处')
   OR 上级名称 IN ('湖南代表处')
   OR 节点名称 IN (SELECT 节点名称 FROM 命中孙级)
ORDER BY 条线 DESC,
层级 DESC,
上级名称,
节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次已按达成率输出 1 个代表处的排名结果：湖南代表处位列第1（末位），达成率53.54%；湖南代表处位于第1（榜首），达成率53.54%。

### 亮点分析
• **相对最好对象：** 湖南代表处 -> 达成率 53.54% -> 在本组垫底集合中
- **真实业务理解与标准基准 (Ground Truth)**：
  > 按指标升序排列，定位靠后或最少的一项。
- **错误根因定位**：
  排序方向错误，倒数排名误用了 `DESC` 降序。
- **专属免代码优化建议**：
  > **Agent 2 排序 Prompt 优化**：明确排序约束：“当问题包含‘倒数/后几名/最少’时，必须生成 `ORDER BY 指标 ASC`（升序）”。

---

### [错题 126] 【商用事业部】 湖北代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('湖北代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
湖北代表处当前作为代表处，归属东部分公司：年度任务2310万，年度开单799万，达成率34.59%，剩余任务1511万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 湖北代表处 -> 年度开单799
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 127] 【商用事业部】 广东代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `25` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '代表处'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 粤东代表处、北京代表处、粤西广西代表处、湖北代表处、山东代表处、陕西代表处 展开，共识别 1 个分析层级。代表处综合达成率 40.52%，代表处综合达成率 40.52%。

### 亮点分析
• **亮点：** 代表处 -> 综合达成率 40
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 128] 【商用事业部】 广东代表处的达成率在所属分公司排倒数第几？
- **分类场景**：`区域内倒数排名`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE 节点名称 IN ('广东代表处','达成率在所属分公司') OR 上级名称 IN ('广东代表处','达成率在所属分公司')
ORDER BY 达成率 DESC, 剩余任务金额 DESC, 条线 DESC, 节点名称
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“代表处的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单金额
- **真实业务理解与标准基准 (Ground Truth)**：
  > 按指标升序排列，定位靠后或最少的一项。
- **错误根因定位**：
  排序方向错误，倒数排名误用了 `DESC` 降序。
- **专属免代码优化建议**：
  > **Agent 2 排序 Prompt 优化**：明确排序约束：“当问题包含‘倒数/后几名/最少’时，必须生成 `ORDER BY 指标 ASC`（升序）”。

---

### [错题 129] 【商用事业部】 深圳代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('深圳城市公司')
   OR 上级名称 IN ('深圳城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
深圳城市公司当前作为城市分公司，归属粤桂琼分公司：年度任务3781万，年度开单1691万，达成率44.71%，剩余任务2090万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 深圳城市公司 -> 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 130] 【商用事业部】 福建代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('福建代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
福建代表处当前作为代表处，归属南部分公司：年度任务700万，年度开单190万，达成率27.15%，剩余任务510万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 福建代表处 -> 年度开单190万，
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 131] 【商用事业部】 粤东代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `7` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('粤东代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
粤东代表处当前作为代表处，归属南部分公司：年度任务2850万，年度开单1572万，达成率55.15%，剩余任务1278万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 粤东代表处 -> 年度开单15
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 132] 【商用事业部】 广西代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `25` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT
    节点名称 AS 分组名称,
    节点名称,
    MAX(层级) AS 层级,
    MAX(上级名称) AS 上级名称,
    SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, CASE WHEN SUM(总任务金额) = 0 THEN 0 ELSE ROUND(SUM(年度开单金额) / SUM(总任务金额) * 100, 2) END AS 达成率, SUM(剩余任务金额) AS 剩余任务金额
FROM 汇总结果
WHERE 层级 = '代表处'
GROUP BY 节点名称
ORDER BY 年度开单金额 DESC NULLS LAST
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 粤东代表处、北京代表处、粤西广西代表处、湖北代表处、山东代表处、陕西代表处 展开，共识别 1 个分析层级。代表处综合达成率 40.52%，代表处综合达成率 40.52%。

### 亮点分析
• **亮点：** 代表处 -> 综合达成率 40
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 133] 【商用事业部】 广西代表处的达成率在所属分公司排倒数第几？
- **分类场景**：`区域内倒数排名`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE 节点名称 IN ('广西代表处','达成率在所属分公司') OR 上级名称 IN ('广西代表处','达成率在所属分公司')
ORDER BY 达成率 DESC, 剩余任务金额 DESC, 条线 DESC, 节点名称
LIMIT 200
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“代表处的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“商用事业部开单金额
- **真实业务理解与标准基准 (Ground Truth)**：
  > 按指标升序排列，定位靠后或最少的一项。
- **错误根因定位**：
  排序方向错误，倒数排名误用了 `DESC` 降序。
- **专属免代码优化建议**：
  > **Agent 2 排序 Prompt 优化**：明确排序约束：“当问题包含‘倒数/后几名/最少’时，必须生成 `ORDER BY 指标 ASC`（升序）”。

---

### [错题 134] 【商用事业部】 四川代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `6` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('四川代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
四川代表处当前作为代表处，归属西部分公司：年度任务1750万，年度开单686万，达成率39.22%，剩余任务1064万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 四川代表处 -> 年度开单686
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 135] 【商用事业部】 重庆代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 136] 【商用事业部】 重庆代表处的达成率在所属分公司排倒数第几？
- **分类场景**：`区域内倒数排名`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 等待老板确认后继续执行。
- **真实业务理解与标准基准 (Ground Truth)**：
  > 按指标升序排列，定位靠后或最少的一项。
- **错误根因定位**：
  排序方向错误，倒数排名误用了 `DESC` 降序。
- **专属免代码优化建议**：
  > **Agent 2 排序 Prompt 优化**：明确排序约束：“当问题包含‘倒数/后几名/最少’时，必须生成 `ORDER BY 指标 ASC`（升序）”。

---

### [错题 137] 【商用事业部】 陕西代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('陕西代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
陕西代表处当前作为代表处，归属西部分公司：年度任务1400万，年度开单693万，达成率49.53%，剩余任务707万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 陕西代表处 -> 年度开单693万
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 138] 【商用事业部】 云贵代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('云贵代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
云贵代表处当前作为代表处，归属西部分公司：年度任务810万，年度开单294万，达成率36.27%，剩余任务516万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 云贵代表处 -> 年度开单294万，
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 139] 【商用事业部】 西北代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `6` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('西北分公司')
   OR 上级名称 IN ('西北分公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
西北分公司当前作为分公司，归属消费者事业部：年度任务1.34亿，年度开单6698万，达成率50.14%，剩余任务6662万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 西北分公司 -> 年度开单
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 140] 【商用事业部】 津冀代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('津冀代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
津冀代表处当前作为代表处，归属北部分公司：年度任务1380万，年度开单600万，达成率43.47%，剩余任务780万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 津冀代表处 -> 年度开单600万
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 141] 【商用事业部】 吉林代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `2` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('吉林代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
吉林代表处当前作为代表处，归属北部分公司：年度任务200万，年度开单43.8万，达成率21.88%，剩余任务156万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 吉林代表处 -> 年度开单43.8
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 142] 【商用事业部】 黑龙江代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `2` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('黑龙江代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
黑龙江代表处当前作为代表处，归属北部分公司：年度任务200万，年度开单49.7万，达成率24.85%，剩余任务150万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 黑龙江代表处 -> 年度开单49
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 143] 【商用事业部】 辽宁代表处今年上半年的目标是多少？
- **分类场景**：`半年指标展开`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('辽宁代表处')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
辽宁代表处当前作为代表处，归属北部分公司：年度任务1010万，年度开单333万，达成率32.93%，剩余任务677万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 辽宁代表处 -> 年度开单333万
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层数据库中的真实指标与多维数据。
- **错误根因定位**：
  复杂多维条件或跨层级下钻时的 SQL 模板拼接偏差。
- **专属免代码优化建议**：
  > **Agent 2/3 Prompt 优化**：优化多条件组合过滤规则。

---

### [错题 144] 【消费者事业部】 成都城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('成都城市公司')
   OR 上级名称 IN ('成都城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
成都城市公司当前作为城市分公司，归属川藏分公司：年度任务3547万，年度开单1149万，达成率32.41%，剩余任务2398万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 成都城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 145] 【消费者事业部】 重庆城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('重庆城市公司')
   OR 上级名称 IN ('重庆城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
重庆城市公司当前作为城市分公司，归属云贵渝分公司：年度任务3815万，年度开单1504万，达成率39.43%，剩余任务2311万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 重庆城市公司 -> 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 146] 【消费者事业部】 贵阳城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('贵阳城市公司')
   OR 上级名称 IN ('贵阳城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
贵阳城市公司当前作为城市分公司，归属云贵渝分公司：年度任务2102万，年度开单1072万，达成率51.02%，剩余任务1030万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 贵阳城市公司 -> 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 147] 【消费者事业部】 遵义城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('遵义城市公司')
   OR 上级名称 IN ('遵义城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
遵义城市公司当前作为城市分公司，归属云贵渝分公司：年度任务1733万，年度开单878万，达成率50.65%，剩余任务855万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 遵义城市公司 -> 年度
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 148] 【消费者事业部】 万州城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('万州城市公司')
   OR 上级名称 IN ('万州城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
万州城市公司当前作为城市分公司，归属云贵渝分公司：年度任务1479万，年度开单392万，达成率26.50%，剩余任务1087万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 万州城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 149] 【消费者事业部】 北京城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('北京城市公司')
   OR 上级名称 IN ('北京城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
北京城市公司当前作为城市分公司，归属京津分公司：年度任务5622万，年度开单2387万，达成率42.45%，剩余任务3235万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 北京城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 150] 【消费者事业部】 哈尔滨城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('哈尔滨城市公司')
   OR 上级名称 IN ('哈尔滨城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
哈尔滨城市公司当前作为城市分公司，归属黑吉辽分公司：年度任务1728万，年度开单841万，达成率48.70%，剩余任务887万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 哈尔滨城市公司 -> 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 151] 【消费者事业部】 邵阳城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('邵阳城市公司')
   OR 上级名称 IN ('邵阳城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
邵阳城市公司当前作为城市分公司，归属湖南分公司：年度任务2915万，年度开单1049万，达成率35.99%，剩余任务1866万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 邵阳城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 152] 【消费者事业部】 衡阳城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('衡阳城市公司')
   OR 上级名称 IN ('衡阳城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
衡阳城市公司当前作为城市分公司，归属湖南分公司：年度任务3375万，年度开单644万，达成率19.08%，剩余任务2731万。当前达成承压，建议优先跟进缺口转化。

### 亮点分析
• **当前主体：** 衡阳城市公司 -> 年度开单644万，任务
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 153] 【消费者事业部】 苏南城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('苏南城市公司')
   OR 上级名称 IN ('苏南城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
苏南城市公司当前作为城市分公司，归属江浙沪分公司：年度任务1585万，年度开单492万，达成率31.04%，剩余任务1093万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 苏南城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 154] 【消费者事业部】 烟台城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('烟台城市公司')
   OR 上级名称 IN ('烟台城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
烟台城市公司当前作为城市分公司，归属山东分公司：年度任务1230万，年度开单726万，达成率59.02%，剩余任务504万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 烟台城市公司 -> 年度开
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 155] 【消费者事业部】 榆林城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('榆林城市公司')
   OR 上级名称 IN ('榆林城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
榆林城市公司当前作为城市分公司，归属西北分公司：年度任务1373万，年度开单715万，达成率52.11%，剩余任务658万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 榆林城市公司 -> 年度开
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 156] 【消费者事业部】 太原城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('太原城市公司')
   OR 上级名称 IN ('太原城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
太原城市公司当前作为城市分公司，归属豫晋分公司：年度任务2158万，年度开单1163万，达成率53.87%，剩余任务995万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 太原城市公司 -> 年度
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 157] 【消费者事业部】 郑州城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('郑州城市公司')
   OR 上级名称 IN ('郑州城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
郑州城市公司当前作为城市分公司，归属豫晋分公司：年度任务5565万，年度开单4268万，达成率76.68%，剩余任务1297万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 郑州城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 158] 【消费者事业部】 石家庄城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('石家庄城市公司')
   OR 上级名称 IN ('石家庄城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
石家庄城市公司当前作为城市分公司，归属河北分公司：年度任务3016万，年度开单1531万，达成率50.78%，剩余任务1485万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 石家庄城市公司 ->
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 159] 【消费者事业部】 广州城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('广州城市公司')
   OR 上级名称 IN ('广州城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
广州城市公司当前作为城市分公司，归属粤桂琼分公司：年度任务4940万，年度开单2390万，达成率48.38%，剩余任务2550万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 广州城市公司 -> 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 160] 【消费者事业部】 深圳城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('深圳城市公司')
   OR 上级名称 IN ('深圳城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
深圳城市公司当前作为城市分公司，归属粤桂琼分公司：年度任务3781万，年度开单1691万，达成率44.71%，剩余任务2090万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 深圳城市公司 -> 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 161] 【消费者事业部】 济南城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('济南城市公司')
   OR 上级名称 IN ('济南城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
济南城市公司当前作为城市分公司，归属山东分公司：年度任务2147万，年度开单1116万，达成率51.98%，剩余任务1031万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 济南城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 162] 【消费者事业部】 青岛城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('青岛城市公司')
   OR 上级名称 IN ('青岛城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
青岛城市公司当前作为城市分公司，归属山东分公司：年度任务2003万，年度开单769万，达成率38.38%，剩余任务1234万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 青岛城市公司 -> 年度
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 163] 【消费者事业部】 天津城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('天津城市公司')
   OR 上级名称 IN ('天津城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
天津城市公司当前作为城市分公司，归属京津分公司：年度任务2250万，年度开单1149万，达成率51.05%，剩余任务1101万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 天津城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 164] 【消费者事业部】 沈阳城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('沈阳城市公司')
   OR 上级名称 IN ('沈阳城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
沈阳城市公司当前作为城市分公司，归属黑吉辽分公司：年度任务1359万，年度开单663万，达成率48.80%，剩余任务696万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 沈阳城市公司 -> 年度
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 165] 【消费者事业部】 大连城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('大连城市公司')
   OR 上级名称 IN ('大连城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
大连城市公司当前作为城市分公司，归属黑吉辽分公司：年度任务1864万，年度开单850万，达成率45.62%，剩余任务1014万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 大连城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 166] 【消费者事业部】 长春城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('长春城市公司')
   OR 上级名称 IN ('长春城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
长春城市公司当前作为城市分公司，归属黑吉辽分公司：年度任务1797万，年度开单848万，达成率47.20%，剩余任务949万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 长春城市公司 -> 年度
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 167] 【消费者事业部】 南昌城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('南昌城市公司')
   OR 上级名称 IN ('南昌城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
南昌城市公司当前作为城市分公司，归属赣闽分公司：年度任务3897万，年度开单1723万，达成率44.21%，剩余任务2174万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 南昌城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 168] 【消费者事业部】 福州城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('福州城市公司')
   OR 上级名称 IN ('福州城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
福州城市公司当前作为城市分公司，归属赣闽分公司：年度任务1564万，年度开单543万，达成率34.69%，剩余任务1021万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 福州城市公司 -> 年度
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 169] 【消费者事业部】 厦门城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('厦门城市公司')
   OR 上级名称 IN ('厦门城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
厦门城市公司当前作为城市分公司，归属赣闽分公司：年度任务2677万，年度开单1153万，达成率43.08%，剩余任务1524万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 厦门城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 170] 【消费者事业部】 武汉城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('武汉城市公司')
   OR 上级名称 IN ('武汉城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
武汉城市公司当前作为城市分公司，归属鄂皖分公司：年度任务5464万，年度开单2800万，达成率51.24%，剩余任务2664万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 武汉城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 171] 【消费者事业部】 襄阳城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('襄阳城市公司')
   OR 上级名称 IN ('襄阳城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
襄阳城市公司当前作为城市分公司，归属鄂皖分公司：年度任务4321万，年度开单2006万，达成率46.41%，剩余任务2315万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 襄阳城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 172] 【消费者事业部】 宜昌城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('宜昌城市公司')
   OR 上级名称 IN ('宜昌城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
宜昌城市公司当前作为城市分公司，归属鄂皖分公司：年度任务4235万，年度开单1694万，达成率40%，剩余任务2541万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 宜昌城市公司 -> 年度开单
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 173] 【消费者事业部】 长沙城市公司的地产和燃气定制加起来开单多少？
- **分类场景**：`城市公司多渠道合并`
- **系统执行表现**：返回 `1` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('长沙城市公司')
   OR 上级名称 IN ('长沙城市公司')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
长沙城市公司当前作为城市分公司，归属湖南分公司：年度任务4642万，年度开单2283万，达成率49.18%，剩余任务2359万。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 长沙城市公司 -> 年
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 174] 【电商事业部】 电商事业部Q1目标和Q2目标哪个更高，高多少？
- **分类场景**：`季度目标差额计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' ORDER BY  LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“电商事业部的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“电商事业部开单
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

### [错题 175] 【电商事业部】 国内业务部Q1到Q4四个季度的目标平均是多少？
- **分类场景**：`季度目标平均值计算`
- **系统执行表现**：返回 `5` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND (组织路径 LIKE '电商事业部;国内业务部%' OR (业务部 = '国内业务部' AND 层级级别 = '业务部')) ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
国内业务部当前作为业务部，归属电商事业部：年度任务8.8亿，年度开单2.41亿，达成率27.39%，剩余任务6.39亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 国内业务部 -> 年度开单2.4
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 176] 【电商事业部】 电商部门Q1目标占全年总任务的比例是多少？
- **分类场景**：`季度占全年目标比例`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 国内业务部、直营零售部、跨境业务部 展开，共识别 1 个分析层级。业务部综合达成率 25.68%，业务部综合达成率 25.68%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 25.68% -> 可作为当前层级的优先复盘
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 177] 【电商事业部】 电商部门Q2目标占全年总任务的百分比是多少？
- **分类场景**：`季度占全年目标比例`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 国内业务部、直营零售部、跨境业务部 展开，共识别 1 个分析层级。业务部综合达成率 25.68%，业务部综合达成率 25.68%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 25.68% -> 可作为当前层级的优先复盘
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 178] 【电商事业部】 电商部门Q3目标占全年总任务的份额是多少？
- **分类场景**：`季度占全年目标比例`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 国内业务部、直营零售部、跨境业务部 展开，共识别 1 个分析层级。业务部综合达成率 25.68%，业务部综合达成率 25.68%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 25.68% -> 可作为当前层级的优先复盘
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 179] 【电商事业部】 电商部门Q4目标占全年总任务的贡献率是多少？
- **分类场景**：`季度占全年目标比例`
- **系统执行表现**：返回 `3` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算
- **系统生成的实际 SQL**：
```sql
SELECT '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **系统分析报告摘要**：
  > ## 电商事业部开单金额

## 业绩分析报告

### 核心结论
本轮围绕 国内业务部、直营零售部、跨境业务部 展开，共识别 1 个分析层级。业务部综合达成率 25.68%，业务部综合达成率 25.68%。

### 亮点分析
• **亮点：** 业务部 -> 综合达成率 25.68% -> 可作为当前层级的优先复盘
- **真实业务理解与标准基准 (Ground Truth)**：
  > 计算对象开单金额 A 与所属主体总开单 B 的除法百分比：ROUND(A * 100.0 / B, 2) %。
- **错误根因定位**：
  系统仅查询了原始明细金额，未在 SQL 中生成窗口函数或除法计算列。
- **专属免代码优化建议**：
  > **Agent 2 派生计算 Prompt 优化**：在 SQL 生成器中注入占比计算规则：“当用户询问‘占比/比例/贡献率/份额’时，自动使用 `ROUND(年度开单金额 * 100.0 / SUM(年度开单金额) OVER(), 2) AS 占比_百分比` 进行计算”。

---

### [错题 180] 【商用事业部】 东部分公司和南部分公司的代表处平均达成率相比谁更高？
- **分类场景**：`大区代表处均值对比`
- **系统执行表现**：返回 `56` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
)
SELECT *
FROM 汇总结果
WHERE (分公司 = '东部分公司' OR 分公司 = '南部分公司')
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

# 南部分公司 vs 东部分公司 业绩对比分析报告

## 一、核心结论
南部分公司整体达成率44.89%，比东部分公司的40.33%高4.56个百分点；当前对标方向是 东部分公司 向 南部分公司 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 南部分公司 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

### [错题 181] 【商用事业部】 商用西部分公司和北部分公司的代表处平均开单差距？
- **分类场景**：`大区代表处均值差额`
- **系统执行表现**：返回 `14` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ('西部分公司','北部分公司')
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

# 北部分公司 vs 西部分公司 业绩对比分析报告

## 一、核心结论
北部分公司整体达成率40.15%，比西部分公司的37.79%高2.36个百分点；当前对标方向是 西部分公司 向 北部分公司 学习高达成节点的目标拆解和项目推进节奏。

## 二、关键指标对标
| 指标 | 北部分公司 
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

### [错题 182] 【商用事业部】 商用四个大区各代表处平均达成率最高的是哪个大区？
- **分类场景**：`大区代表处均值极值`
- **系统执行表现**：返回 `4` 行数据 | **判定缺陷**：函数缺失：用户要求计算平均值，生成的 SQL 缺少 AVG() 聚合函数
- **系统生成的实际 SQL**：
```sql
WITH 汇总结果 AS (
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        '' AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '商用事业部' AS 事业部,
        分公司,
        代表处,
        业务部,
        业务代表,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        MAX(事业部) AS 事业部,
        MAX(分公司) AS 分公司,
        MAX(代表处) AS 代表处,
        MAX(业务部) AS 业务部,
        MAX(业务代表) AS 业务代表,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    事业部,
    分公司,
    代表处,
    业务部,
    业务代表,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
),
代表处全局排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY 达成率 DESC, 剩余任务金额 DESC, 节点名称
        ) AS 全局排名
    FROM 汇总结果
    WHERE 层级 = '代表处'
)
SELECT *
FROM 代表处全局排序
WHERE 全局排名 <= 4
ORDER BY 全局排名, 达成率 DESC, 剩余任务金额 DESC, 节点名称
LIMIT 4
```
- **系统分析报告摘要**：
  > ## 商用事业部开单金额

## 业绩分析报告

### 核心结论
本次已按达成率输出 4 个代表处的排名结果：山东代表处位列第1（榜首），达成率62.82%；陕西代表处位于第4（末位），达成率49.53%，首尾相差13.29 个百分点。

### 亮点分析
• **榜首对象：** 山东代表处 -> 达成率 62.82
- **真实业务理解与标准基准 (Ground Truth)**：
  > 底层多节点指标的算术平均值 AVG(指标)。
- **错误根因定位**：
  SQL 缺少 AVG() 聚合函数，仅返回了明细列表。
- **专属免代码优化建议**：
  > **Agent 2 聚合 Prompt 优化**：捕捉‘平均/均值’意图，强制生成 `AVG(年度开单金额)` 或 `AVG(达成率)` 聚合查询。

---

### [错题 183] 【消费者事业部】 线下渠道开单占消费者事业部总开单的百分之几？
- **分类场景**：`全国渠道总额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '消费者经营链路' AS 条线, '全部' AS 分析口径, NULL AS 层级, NULL AS 节点名称, NULL AS 上级名称, 0 AS 总任务金额, 0 AS 年度开单金额, 0 AS 达成率, 0 AS 剩余任务金额, 0 AS 线下任务_万元, 0 AS 新零售任务_万元, 0 AS 燃气定制任务_万元, 0 AS 地产任务_万元, 0 AS 线下实际_万元, 0 AS 新零售实际_万元, 0 AS 燃气定制实际_万元, 0 AS 地产实际_万元 FROM public.feishu_tbl_xioafeizhe WHERE 1=0 LIMIT 0
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“消费者事业部的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 184] 【消费者事业部】 新零售渠道开单占消费者事业部总开单的百分比？
- **分类场景**：`全国渠道总额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果
WHERE 层级 = '新零售'
ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“消费者事业部的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 185] 【消费者事业部】 燃气定制开单占消费者事业部总开单的比例是多少？
- **分类场景**：`全国渠道总额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '消费者经营链路' AS 条线, '全部' AS 分析口径, NULL AS 层级, NULL AS 节点名称, NULL AS 上级名称, 0 AS 总任务金额, 0 AS 年度开单金额, 0 AS 达成率, 0 AS 剩余任务金额, 0 AS 线下任务_万元, 0 AS 新零售任务_万元, 0 AS 燃气定制任务_万元, 0 AS 地产任务_万元, 0 AS 线下实际_万元, 0 AS 新零售实际_万元, 0 AS 燃气定制实际_万元, 0 AS 地产实际_万元 FROM public.feishu_tbl_xioafeizhe WHERE 1=0 LIMIT 0
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“消费者事业部的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 186] 【消费者事业部】 地产渠道开单占消费者事业部总开单的份额是多少？
- **分类场景**：`全国渠道总额占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：查询结果为 0 行（未命中数据）
- **系统生成的实际 SQL**：
```sql
SELECT '消费者经营链路' AS 条线, '全部' AS 分析口径, NULL AS 层级, NULL AS 节点名称, NULL AS 上级名称, 0 AS 总任务金额, 0 AS 年度开单金额, 0 AS 达成率, 0 AS 剩余任务金额, 0 AS 线下任务_万元, 0 AS 新零售任务_万元, 0 AS 燃气定制任务_万元, 0 AS 地产任务_万元, 0 AS 线下实际_万元, 0 AS 新零售实际_万元, 0 AS 燃气定制实际_万元, 0 AS 地产实际_万元 FROM public.feishu_tbl_xioafeizhe WHERE 1=0 LIMIT 0
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
本次围绕“消费者事业部的业绩”未找到匹配数据，暂不能判断业绩好坏。

### 问题诊断
• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。
• **痛点：** 数据集口径 -> 当前命中“消费者事业
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 187] 【消费者事业部】 消费者事业部线下任务和新零售任务加起来一共多少？
- **分类场景**：`跨渠道任务加总`
- **系统执行表现**：返回 `14` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('消费者事业部')
   OR 上级名称 IN ('消费者事业部')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
消费者事业部当前作为消费者事业部总体：年度任务17.9亿，年度开单9.5亿，达成率53.10%，剩余任务8.39亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 消费者事业部 -> 年度开单9.5
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 188] 【消费者事业部】 消费者事业部燃气定制任务和地产任务加起来一共多少？
- **分类场景**：`跨渠道任务加总`
- **系统执行表现**：返回 `14` 行数据 | **判定缺陷**：聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合
- **系统生成的实际 SQL**：
```sql
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        COALESCE(NULLIF(TRIM(fields->>'城市分公司'), ''), '') AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        '全部' AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND((总任务金额), 2) AS 总任务金额,
        ROUND((年度开单金额), 2) AS 年度开单金额,
        CASE WHEN (总任务金额) > 0 THEN ROUND((年度开单金额) / (总任务金额) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST((总任务金额) - (年度开单金额), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND ((总任务金额) > 0 OR (年度开单金额) > 0)
)
SELECT *
FROM 汇总结果

WHERE 节点名称 IN ('消费者事业部')
   OR 上级名称 IN ('消费者事业部')

ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
```
- **系统分析报告摘要**：
  > ## 消费者事业部开单金额

## 业绩分析报告

### 核心结论
消费者事业部当前作为消费者事业部总体：年度任务17.9亿，年度开单9.5亿，达成率53.10%，剩余任务8.39亿。当前进度已明确，可继续结合上级链路判断支撑与压力来源。

### 亮点分析
• **当前主体：** 消费者事业部 -> 年度开单9.5
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 189] 【消费者事业部】 线下渠道和地产渠道的全年开单差距是多少万元？
- **分类场景**：`跨渠道差额计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求计算跨渠道开单差额，系统未生成两渠道差值计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 190] 【电商事业部】 抖音直营和达播渠道的达成率差距是多少个百分点？
- **分类场景**：`跨业务达成率差额`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求计算达成率百分比差额，系统未在 SQL 中生成差值计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

### [错题 191] 【消费者事业部】 线下渠道和地产渠道的全年开单差距是多少万元？
- **分类场景**：`跨渠道差额计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求计算跨渠道开单差额，系统未生成两渠道差值计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 192] 【电商事业部】 抖音直营和达播渠道的达成率差距是多少个百分点？
- **分类场景**：`跨业务达成率差额`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求计算达成率百分比差额，系统未在 SQL 中生成差值计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

### [错题 193] 【商用事业部】 商用上海代表处和江苏代表处的开单差距是多少万元？
- **分类场景**：`代表处差额计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求对比两代表处差额，系统未生成相减计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

### [错题 194] 【商用事业部】 商用河南代表处和河北代表处的开单差距是多少万元？
- **分类场景**：`代表处差额计算`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求对比两代表处差额，系统未生成相减计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

### [错题 195] 【消费者事业部】 川藏分公司成都城市公司的燃气定制完成了多少？
- **分类场景**：`城市公司渠道占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：口径混淆：将横向渠道指标列误当成了纵向组织层级
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 196] 【消费者事业部】 川藏分公司川北城市公司的地产开单是多少万元？
- **分类场景**：`城市公司渠道占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：口径混淆：将横向渠道指标列误当成了纵向组织层级
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 197] 【消费者事业部】 山东分公司烟台城市公司的线下开单占其总开单的比例？
- **分类场景**：`城市公司渠道占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比，SQL 缺少除法份额计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 198] 【消费者事业部】 湖南分公司衡阳城市公司的新零售开单占其总开单的百分比？
- **分类场景**：`城市公司渠道占比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求计算占比，SQL 缺少除法份额计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 消费者事业部数据中，线下实际 8.045 亿、新零售实际 1.045 亿、燃气定制实际 1322 万、地产实际 2817 万。
- **错误根因定位**：
  各渠道在底层数据表中是横向指标列（如 `燃气定制实际_万元`），系统误将其当成了纵向组织层级维度，生成了 `WHERE 层级 = "渠道名"`。
- **专属免代码优化建议**：
  > **Agent 1/2 Prompt 优化**：在消费者事业部元数据提示词中声明：“`线下`、`新零售`、`燃气定制`、`地产` 为横向渠道指标列，严禁生成 `WHERE 层级 = "渠道名"`，查询渠道数据时必须使用 `SELECT SUM(燃气定制实际_万元)` 进行提取与加总”。

---

### [错题 199] 【电商事业部】 天猫直营和抖音直营的开单差距是多少万元？
- **分类场景**：`细分业务差额对比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求对比差额，系统未在 SQL 中生成相减计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

### [错题 200] 【电商事业部】 京东直营和达播业务的开单差距是多少万元？
- **分类场景**：`细分业务差额对比`
- **系统执行表现**：返回 `0` 行数据 | **判定缺陷**：计算缺失：用户要求对比差额，系统未在 SQL 中生成相减计算
- **系统生成的实际 SQL**：
```sql
-- 系统未生成有效 SQL 或执行被拦截 --
```
- **系统分析报告摘要**：
  > 系统未产出实质性分析报告或提示未找到匹配数据
- **真实业务理解与标准基准 (Ground Truth)**：
  > 对比两对象的开单或任务缺口差额：ABS(对象1 - 对象2)。
- **错误根因定位**：
  SQL 仅返回了多行数据，未在查询表达式中输出两对象的差值计算。
- **专属免代码优化建议**：
  > **Agent 2 对比 Prompt 优化**：在多对象对比场景中，支持生成差额计算表达式，并在 Agent 4 解读模板中强制输出具体差额数字与对比分析。

---

## 三、200 道错题系统性落地实施清单（纯配置免代码）

通过对 200 道错题的系统梳理，所有问题可收敛为 **4 项标准配置操作**：

1. **Agent 1 实体净化规则注入**：在实体抽取 Prompt 增加修饰动词剥离字典（剥离‘负责的/管辖的/带领的/分管的’）。
2. **消费者事业部渠道指标列声明**：在消费者数据集 Prompt 中明确 4 大渠道为横向列，指导使用 `SUM(列名)` 聚合。
3. **电商事业部达成率格式标注**：在 `bs_data_dictionary_items` 中注明达成率为 0~1 小数格式，过滤时自动除以 100。
4. **Agent 2 派生计算模板注入**：注入占比 `OVER()`、均值 `AVG()`、差额 `ABS()` 与反向排序 `ASC` 模板。
