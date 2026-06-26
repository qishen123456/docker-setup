# SmartAsk 端到端测试报告

- 测试时间：2026-06-26 19:07:51
- 问题总数：170
- 异常/待确认数：103
- 服务端点：http://localhost:5002/api/smart-chat

## 汇总

| 类别 | 数量 |
|---|---|
| C | 25 |
| E | 25 |
| I | 30 |
| L | 25 |
| M | 25 |
| R | 20 |
| X | 20 |

## 异常问题索引

| 编号 | 问题 | 预期 | 异常点 |
|---|---|---|---|
| R3 | 电商事业部年度目标营收 | 62 | 结果为空 |
| R4 | 分公司业绩排名 | 需确认 | 执行异常 |
| R6 | 东部分公司业绩 | 3 | 执行异常 |
| R7 | 国内业务部和直营零售部对比 | 62 | 结果为空 |
| R8 | 商用事业部和消费者事业部的总任务金额对比 | 跨数据集 | 未识别跨数据集对比 |
| R11 | 电商事业部的预算 | 62 | 结果为空 |
| R12 | 事业部的达成率 | 需确认 | 未按预期弹确认 |
| R14 | 南部分公司业绩 | 3 | 执行异常 |
| R15 | 跨境业务部业绩 | 62 | 结果为空 |
| R16 | 业务部业绩 | 需确认 | 未按预期弹确认; 结果为空 |
| R18 | 消费者城市分公司排名 | 2 | 卡片标题与问题关联度低 |
| R19 | 电商三大业务部对比 | 62 | 结果为空 |
| R20 | 代表处业绩 | 需确认 | 未按预期弹确认; 结果为空 |
| I1 | 消费者事业部哪个分公司完成率最高 | 2 | 卡片标题与问题关联度低 |
| I3 | 前 3 的分公司 | 2 | 执行异常 |
| I4 | 后 5 的代表处 | 3 | 卡片标题与问题关联度低 |
| I5 | 哪些城市分公司达成率低于 10% | 2 | 卡片标题与问题关联度低 |
| I6 | 电商事业部毛利率为负的细分业务 | 62 | 结果为空 |
| I8 | 消费者事业部各城市分公司业绩排名 | 2 | 卡片标题与问题关联度低 |
| I10 | 所有细分业务按年度开单金额排名 | 62 | 结果为空 |
| I13 | 哪个分公司最低 | 2 | 执行异常 |
| I14 | 商用事业部哪个代表处开单金额最高 | 3 | 卡片标题与问题关联度低 |
| I15 | 电商事业部前 5 的细分业务 | 62 | 结果为空 |
| I16 | 消费者事业部倒数前 3 的城市分公司 | 2 | 卡片标题与问题关联度低 |
| I17 | 商用事业部达成率超过 80% 的分公司 | 3 | 结果为空 |
| I18 | 电商事业部年度开单金额低于 500 万的业务 | 62 | 结果为空 |
| I21 | 电商事业部业绩总览 | 62 | 结果为空 |
| I24 | 电商事业部三大业务部年度目标营收对比 | 62 | 结果为空 |
| I25 | 消费者事业部业绩排名 | 2 | 卡片标题与问题关联度低 |
| I26 | 商用事业部代表处业绩排名 | 3 | 卡片标题与问题关联度低 |
| I27 | 电商事业部业务承接人业绩排名 | 62 | 结果为空 |
| I28 | 消费者事业部缺口最大的分公司 | 2 | 卡片标题与问题关联度低 |
| I29 | 商用事业部剩余任务最少的分公司 | 3 | 卡片标题与问题关联度低 |
| I30 | 电商事业部毛利率最高的业务部 | 62 | 结果为空 |
| M4 | 电商事业部年度目标营收 vs 年度开单金额对比 | 62 | 结果为空 |
| M5 | 商用事业部年度开单金额最高的分公司 | 3 | 卡片标题与问题关联度低 |
| M6 | 消费者事业部缺口最大的分公司 | 2 | 卡片标题与问题关联度低 |
| M7 | 电商事业部年度目标营收完成率 | 62 | 结果为空 |
| M11 | 电商事业部预算完成率 | 62 | 结果为空 |
| M13 | 消费者事业部年度开单金额排名 | 2 | 卡片标题与问题关联度低 |
| M14 | 商用事业部达成率排名 | 3 | 结果为空; 卡片标题与问题关联度低 |
| M15 | 电商事业部年度开单金额排名 | 62 | 结果为空 |
| M18 | 电商事业部目标营收完成率最低的细分业务 | 62 | 结果为空 |
| M19 | 消费者事业部哪个分公司销售额最高 | 2 | 卡片标题与问题关联度低 |
| M21 | 电商事业部哪个业务线利润最高 | 62 | 结果为空 |
| M24 | 电商事业部营收完成情况 | 62 | 结果为空 |
| L4 | 电商事业部净水业务负责人是谁 | 62 | 结果为空 |
| L5 | 商用事业部业务员业绩排名 | 3 | 卡片标题与问题关联度低 |
| L6 | 消费者事业部前 5 的城市分公司 | 2 | 卡片标题与问题关联度低 |
| L8 | 国内业务部各细分业务年度开单金额 | 62 | 结果为空 |
| L9 | 商用事业部东部分公司代表处业绩排名 | 3 | 卡片标题与问题关联度低 |
| L12 | 电商事业部京东直营业绩 | 62 | 结果为空 |
| L15 | 电商事业部直营零售部下属细分业务 | 62 | 结果为空 |
| L17 | 消费者事业部城市分公司排名 | 2 | 卡片标题与问题关联度低 |
| L18 | 电商事业部负责人刘志伟的业绩 | 62 | 结果为空 |
| L22 | 电商事业部三大业务部对比 | 62 | 结果为空 |
| L24 | 消费者事业部山东分公司城市分公司排名 | 2 | 卡片标题与问题关联度低 |
| L25 | 电商事业部国内业务部净水业务负责人 | 62 | 结果为空 |
| E1 | 华北分公司的业绩 | 2 | 执行异常 |
| E2 | 不存在的代表处业绩 | 3 | 结果为空 |
| E3 | 前 100 的分公司 | 2 | 执行异常 |
| E4 | 达成率低于 0% 的分公司 | 2 | 意外弹确认; 卡片标题与问题关联度低 |
| E5 | 2023 年业绩 | 2 | 执行异常 |
| E7 | 哪个分公司最高 5 名 | 2 | 执行异常 |
| E10 | 商用事业部前 0 名的分公司 | 3 | 卡片标题与问题关联度低 |
| E11 | 电商事业部抖音直营和京东直营对比 | 62 | 结果为空 |
| E14 | 消费者事业部达成率最高的 10 个城市分公司 | 2 | 卡片标题与问题关联度低 |
| E15 | 商用事业部最低的代表处 | 3 | 卡片标题与问题关联度低 |
| E16 | 电商事业部毛利率最低的负责人 | 62 | 结果为空 |
| E17 | 消费者事业部业绩最差的分公司 | 2 | 卡片标题与问题关联度低 |
| E18 | 商用事业部业绩最好的分公司 | 3 | 卡片标题与问题关联度低 |
| E19 | 电商事业部年度开单金额最少的业务 | 62 | 结果为空 |
| E22 | 电商事业部所有细分业务年度目标营收总和 | 62 | 结果为空 |
| E23 | 消费者事业部业绩前十 | 2 | 卡片标题与问题关联度低 |
| E24 | 商用事业部后十名代表处 | 3 | 卡片标题与问题关联度低 |
| E25 | 电商事业部达播业绩 | 62 | 结果为空 |
| C3 | 前 3 的分公司 | 2 | 执行异常 |
| C4 | 哪些城市分公司达成率低于 10% | 2 | 卡片标题与问题关联度低 |
| C6 | 电商事业部国内业务部和直营零售部对比 | 62 | 结果为空 |
| C7 | 消费者事业部哪个分公司完成率最高 | 2 | 卡片标题与问题关联度低 |
| C8 | 商用事业部后 3 名的代表处 | 3 | 卡片标题与问题关联度低 |
| C9 | 消费者事业部缺口最大的分公司 | 2 | 卡片标题与问题关联度低 |
| C13 | 电商事业部年度目标营收 | 62 | 结果为空 |
| C14 | 消费者事业部前 5 的城市分公司 | 2 | 卡片标题与问题关联度低 |
| C16 | 电商事业部毛利率最高的 3 个业务 | 62 | 结果为空 |
| C19 | 电商事业部跨境业务部业绩 | 62 | 结果为空 |
| C22 | 电商事业部净水业务和饮水业务对比 | 62 | 结果为空 |
| C25 | 电商事业部各业务部预算完成情况 | 62 | 结果为空 |
| X2 | 商用事业部四大分公司中达成率最高和最低的分别是 | 3 | 卡片标题与问题关联度低 |
| X3 | 电商事业部国内业务部年度开单金额和毛利率是多少 | 62 | 结果为空 |
| X6 | 电商事业部京东直营、天猫直营、抖音直营业绩排名 | 62 | 结果为空 |
| X7 | 消费者事业部哪些分公司达成率低于 50% 且缺口超过 1000 万 | 2 | 卡片标题与问题关联度低 |
| X8 | 商用事业部达成率高于 80% 且开单金额超过 5000 万的代表处 | 3 | 卡片标题与问题关联度低 |
| X9 | 电商事业部直营零售部中毛利率为正且年度开单金额前 5 的细分业务 | 62 | 结果为空 |
| X10 | 消费者事业部业绩排名第 5 的城市分公司 | 2 | 卡片标题与问题关联度低 |
| X11 | 商用事业部达成率排名第 3 的代表处 | 3 | 卡片标题与问题关联度低 |
| X12 | 电商事业部年度开单金额排名第 10 的细分业务 | 62 | 结果为空 |
| X15 | 电商事业部国内业务部下属毛利率最低的承接人 | 62 | 结果为空 |
| X16 | 消费者事业部业绩排名，按年度开单金额排 | 2 | 卡片标题与问题关联度低 |
| X17 | 商用事业部代表处排名，按达成率排 | 3 | 卡片标题与问题关联度低 |
| X18 | 电商事业部细分业务排名，按年度目标营收完成率排 | 62 | 结果为空 |
| X19 | 消费者事业部哪些分公司没达标（达成率低于 60%） | 2 | 卡片标题与问题关联度低 |
| X20 | 商用事业部哪些代表处落后了（达成率低于 50%） | 3 | 卡片标题与问题关联度低 |

## 详细记录

### R1：商用事业部的达成率

- **目标数据集**：3
- **预期行为**：直接命中数据集 3，不弹确认
- **状态**：✅ 成功
- **耗时**：2.87s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部的达成率
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### R2：消费者事业部业绩怎么样

- **目标数据集**：2
- **预期行为**：直接命中数据集 2，不弹确认
- **状态**：✅ 成功
- **耗时**：7.37s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部业绩怎么样
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "178971.0"}, {"title": "年度开单金额", "value": "59346.18"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "119624.82"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
```sql
WITH 源数据 AS (
  SELECT
    fields,
    COALESCE(NULLIF(regexp_replace(fields ->> '总任务（金额）', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 总任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 年度开单原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '线下', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 线下任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '线下-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 线下实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '新零售', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 新零售任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '新零售-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 新零售实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '燃气定制', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 燃气定制任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '燃气定制-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 燃气定制实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '地产', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 地产任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '地产-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 地产实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '总任务达成率', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 达成率原值
  FROM public.feishu_tbl_xioafeizhe
),
标准结果 AS (
  SELECT
    '消费者事业部' AS 条线,
    CASE
      WHEN NULLIF(fields ->> '分公司', '') IS NULL THEN '消费者事业部总体'
      WHEN NULLIF(fields ->> '城市分公司', '') IS NULL THEN '分公司'
      ELSE '城市分公司'
    END AS 层级,
    CASE
      WHEN NULLI
```

### R3：电商事业部年度目标营收

- **目标数据集**：62
- **预期行为**：直接命中数据集 62，不弹确认
- **状态**：✅ 成功
- **耗时**：5.21s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部年度目标营收
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### R4：分公司业绩排名

- **目标数据集**：需确认
- **预期行为**：数据集 2/3 都含“分公司”，应弹确认
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"ranking","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[],
- **耗时**：0.34s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### R5：山东分公司的业绩

- **目标数据集**：2
- **预期行为**：命中消费者事业部数据集 2
- **状态**：✅ 成功
- **耗时**：5.09s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：山东分公司的业绩
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "100420000.0"}, {"title": "年度开单金额", "value": "31661122.99"}, {"title": "达成率", "value": "31.53"}, {"title": "剩余任务金额", "value": "68758877.01"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：临沂城市公司 / 烟台城市公司 / 济南城市公司 / 青岛城市公司 / 淄博城市公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 5 个城市分公司", "第一梯队：临沂城市公司47.37%、烟台城市公司36.24%", "第二梯队：济南城市公司29.90%、青岛城市公司23.32%", "第三梯队：淄博城市公司3.26%"]
- **SQL 样例**：
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
    FROM public.fei
```

### R6：东部分公司业绩

- **目标数据集**：3
- **预期行为**：命中商用事业部数据集 3
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"analysis","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[]
- **耗时**：0.34s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### R7：国内业务部和直营零售部对比

- **目标数据集**：62
- **预期行为**：命中电商数据集 62
- **状态**：✅ 成功
- **耗时**：5.32s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：国内业务部和直营零售部对比
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 业务部 IN ('国内业务部','直营零售部') AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### R8：商用事业部和消费者事业部的总任务金额对比

- **目标数据集**：跨数据集
- **预期行为**：跨数据集对比或提示确认
- **状态**：✅ 成功
- **耗时**：2.76s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部和消费者事业部的总任务金额对比
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "业务部 / 分公司数量", "value": "7"}, {"title": "累计总任务金额", "value": "455000000.0"}, {"title": "累计年度开单金额", "value": "131114522.4527676"}, {"title": "整体达成率", "value": "28.816378561047824"}, {"title": "最高：公共办公业务部", "value": "80.76"}, {"title": "最低：西部分公司", "value": "19.08"}, {"title": "首尾差距", "value": "61.68000000000001"}]
- **章节**：总体判断 / 业务部 / 分公司对比分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 7 个业务部 / 分公司在下方对比表展开。", "首尾差异：公共办公业务部达成率比东部分公司高57.05个百分点", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：未识别跨数据集对比

### R9：商用事业部的业绩

- **目标数据集**：3
- **预期行为**：直接命中数据集 3
- **状态**：✅ 成功
- **耗时**：5.49s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部的业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "95000000.0"}, {"title": "年度开单金额", "value": "22526100.19"}, {"title": "达成率", "value": "23.71"}, {"title": "剩余任务金额", "value": "72473899.81"}]
- **章节**：总体判断 / 代表处下钻分析
- **图表**：各代表处达成率排序
- **折叠面板**：山东代表处 / 湖南代表处 / 粤东代表处 / 津冀代表处 / 黑龙江代表处 / 北京代表处 / 四川代表处 / 新西代表处 / 浙江代表处 / 上海代表处 / 江苏代表处 / 辽宁代表处 / 粤西广西代表处 / 湖北代表处 / 江西代表处 / 陕西代表处 / 云贵代表处 / 晋蒙（蒙西）代表处 / 安徽代表处 / 福建代表处 / 吉林代表处 / 河南代表处 / 重庆代表处 / 餐饮 / 甘青宁代表处
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 25 个代表处", "第一梯队：山东代表处37.63%、湖南代表处34.55%、粤东代表处28.90%、津冀代表处28.86%、黑龙江代表处28.73%、北京代表处26.32%、四川代表处25.98%、新西代表处25.01%、浙江代表处24.09%", "第二梯队：上海代表处24.04%、江苏代表处23.77%、辽宁代表处23.18%、粤西广西代表处22.19%、湖北代表处20.92%、江西代表处20.35%、陕西代表处18.50%、云贵代表处17.84%", "第三梯队：晋蒙（蒙西）代表处17.15%、安徽代表处16.96%、福建代表处15.01%、吉林代表处14.69%、河南代表处13.07%、重庆代表处12.96%、餐饮12.83%、甘青宁代表处11.02%"]
- **SQL 样例**：
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
    AND 分公司 LIKE '%业务部' THEN '业务部' WHEN 业务部 <> '' THEN '业务部' WHEN 分公司 <> '' THEN '分公司' ELSE '事业部' EN
```

### R10：消费者事业部的完成情况

- **目标数据集**：2
- **预期行为**：直接命中数据集 2
- **状态**：✅ 成功
- **耗时**：5.51s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部的完成情况
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### R11：电商事业部的预算

- **目标数据集**：62
- **预期行为**：直接命中数据集 62
- **状态**：✅ 成功
- **耗时**：4.92s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部的预算
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### R12：事业部的达成率

- **目标数据集**：需确认
- **预期行为**：多个事业部数据集，应弹确认
- **状态**：✅ 成功
- **耗时**：5.15s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：事业部的达成率
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 消费者事业部总体下钻分析
- **图表**：各消费者事业部总体达成率排序
- **折叠面板**：消费者事业部
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 1 个消费者事业部总体", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：未按预期弹确认

### R13：粤桂琼分公司业绩

- **目标数据集**：2
- **预期行为**：命中数据集 2
- **状态**：✅ 成功
- **耗时**：5.19s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：粤桂琼分公司业绩
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "197350000.0"}, {"title": "年度开单金额", "value": "53777280.0"}, {"title": "达成率", "value": "27.25"}, {"title": "剩余任务金额", "value": "143572720.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：桂南城市公司 / 东莞城市公司 / 深圳城市公司 / 广州城市公司 / 粤西城市公司 / 桂东城市公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 6 个城市分公司", "第一梯队：桂南城市公司30.66%、东莞城市公司30.04%", "第二梯队：深圳城市公司28.02%、广州城市公司26.88%", "第三梯队：粤西城市公司24.35%、桂东城市公司23.23%"]
- **SQL 样例**：
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
    FROM public.fei
```

### R14：南部分公司业绩

- **目标数据集**：3
- **预期行为**：命中数据集 3
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"analysis","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[]
- **耗时**：0.31s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### R15：跨境业务部业绩

- **目标数据集**：62
- **预期行为**：命中数据集 62
- **状态**：✅ 成功
- **耗时**：5.0s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：跨境业务部业绩
- **报告标题**：
- **SQL 样例**：
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
- **⚠️ 异常点**：结果为空

### R16：业务部业绩

- **目标数据集**：需确认
- **预期行为**：数据集 3/62 都含“业务部”，应弹确认
- **状态**：✅ 成功
- **耗时**：7.66s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：业务部业绩
- **报告标题**：
- **⚠️ 异常点**：未按预期弹确认; 结果为空

### R17：商用四个分公司业绩

- **目标数据集**：3
- **预期行为**：命中数据集 3
- **状态**：✅ 成功
- **耗时**：2.8s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用四个分公司业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "310000000.0"}, {"title": "累计年度开单金额", "value": "71851963.5627677"}, {"title": "整体达成率", "value": "23.17805276218313"}, {"title": "东部分公司达成率", "value": "23.71"}, {"title": "北部分公司达成率", "value": "24.91"}, {"title": "南部分公司达成率", "value": "24.69"}, {"title": "西部分公司达成率", "value": "19.08"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 4 个分公司", "对比对象：东部分公司：开单2253万 / 任务9500万，达成率23.71%，剩余缺口7247万；北部分公司：开单1584万 / 任务6360万，达成率24.91%，剩余缺口4776万；南部分公司：开单2024万 / 任务8200万，达成率24.69%，剩余缺口6176万；西部分公司：开单1324万 / 任务6940万，达成率19.08%，剩余缺口5616万", "首尾差异：北部分公司达成率比西部分公司高5.83个百分点", "第一梯队：北部分公司24.91%、南部分公司24.69%", "第二梯队：东部分公司23.71%", "第三梯队：西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### R18：消费者城市分公司排名

- **目标数据集**：2
- **预期行为**：命中数据集 2
- **状态**：✅ 成功
- **耗时**：5.15s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前3的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "郑州城市公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "曲靖城市公司", "targetLevel": "城市分公司", "text": "已按达成率输出 3 个城市分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["郑州城市公司", "临沂城市公司", "曲靖城市公司"]}
- **叙述**：["本次结果覆盖 3 个城市分公司", "第一梯队：郑州城市公司49.95%", "第二梯队：临沂城市公司47.37%", "第三梯队：曲靖城市公司42.98%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### R19：电商三大业务部对比

- **目标数据集**：62
- **预期行为**：命中数据集 62
- **状态**：✅ 成功
- **耗时**：4.96s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商三大业务部对比
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','国内业务部','直营零售部','跨境业务部') AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### R20：代表处业绩

- **目标数据集**：需确认
- **预期行为**：数据集 3/2 都可能含代表处，需确认
- **状态**：✅ 成功
- **耗时**：7.45s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：代表处业绩
- **报告标题**：
- **⚠️ 异常点**：未按预期弹确认; 结果为空

### I1：消费者事业部哪个分公司完成率最高

- **目标数据集**：2
- **预期行为**：单点极值 / top 1
- **状态**：✅ 成功
- **耗时**：4.99s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率最高的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "110990000.0"}, {"title": "年度开单金额", "value": "37618017.0"}, {"title": "达成率", "value": "33.89"}, {"title": "剩余任务金额", "value": "73371983.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "河北分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "", "targetLevel": "分公司", "text": "最高的分公司是 河北分公司", "title": "最高结果", "topN": 1, "topNames": ["河北分公司"]}
- **叙述**：["本次结果覆盖 1 个分公司", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I2：商用事业部达成率最低的代表处

- **目标数据集**：3
- **预期行为**：单点极值 / bottom 1
- **状态**：✅ 成功
- **耗时**：2.64s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率最低的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "8100000.0"}, {"title": "年度开单金额", "value": "892720.72"}, {"title": "达成率", "value": "11.02"}, {"title": "剩余任务金额", "value": "7207279.28"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：甘青宁代表处
- **答案摘要**：{"bottomNames": [], "direction": "asc", "leader": "甘青宁代表处", "metricLabel": "达成率", "mode": "ranking", "rankSides": "bottom", "tail": "", "targetLevel": "代表处", "text": "最低的代表处是 甘青宁代表处", "title": "最低结果", "topN": 1, "topNames": ["甘青宁代表处"]}
- **叙述**：["本次结果覆盖 1 个代表处", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### I3：前 3 的分公司

- **目标数据集**：2
- **预期行为**：排名 top 3
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"analysis","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[]
- **耗时**：2.69s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### I4：后 5 的代表处

- **目标数据集**：3
- **预期行为**：排名 bottom 5
- **状态**：✅ 成功
- **耗时**：2.55s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名后5的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "8100000.0"}, {"title": "年度开单金额", "value": "892720.72"}, {"title": "达成率", "value": "11.02"}, {"title": "剩余任务金额", "value": "7207279.28"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：甘青宁代表处 / 餐饮 / 重庆代表处 / 河南代表处 / 吉林代表处
- **答案摘要**：{"bottomNames": [], "direction": "asc", "leader": "甘青宁代表处", "metricLabel": "达成率", "mode": "ranking", "rankSides": "bottom", "tail": "吉林代表处", "targetLevel": "代表处", "text": "已按达成率输出 5 个代表处的排序结果", "title": "排名结果", "topN": 5, "topNames": ["甘青宁代表处", "餐饮", "重庆代表处", "河南代表处", "吉林代表处"]}
- **叙述**：["本次结果覆盖 5 个代表处", "第一梯队：吉林代表处14.69%、河南代表处13.07%", "第二梯队：重庆代表处12.96%、餐饮12.83%", "第三梯队：甘青宁代表处11.02%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I5：哪些城市分公司达成率低于 10%

- **目标数据集**：2
- **预期行为**：阈值筛选
- **状态**：✅ 成功
- **耗时**：5.03s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率小于10%的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "25180000.0"}, {"title": "年度开单金额", "value": "0"}, {"title": "达成率", "value": "0.00%"}, {"title": "剩余任务金额", "value": "25180000.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：洛阳城市公司 / 乐山城市公司 / 淄博城市公司 / 上海城市公司
- **答案摘要**：{"matchedCount": 4, "metricLabel": "达成率", "mode": "filter", "operator": "<", "targetLevel": "城市分公司", "text": "命中 4 个城市分公司", "title": "命中结果", "value": 10.0}
- **叙述**：["本次结果覆盖 4 个城市分公司", "第一梯队：上海城市公司6.68%、淄博城市公司3.26%", "第二梯队：洛阳城市公司0.00%", "第三梯队：乐山城市公司0.00%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I6：电商事业部毛利率为负的细分业务

- **目标数据集**：62
- **预期行为**：阈值筛选
- **状态**：✅ 成功
- **耗时**：4.89s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部毛利率为负的细分业务
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### I7：商用事业部整体达成率是多少

- **目标数据集**：3
- **预期行为**：单点总览
- **状态**：✅ 成功
- **耗时**：5.23s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部整体达成率是多少
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
    AND 分公司 LIKE '%业务部' THEN '业务部' WHEN 业务部 <> '' THEN '业务部' WHEN 分公司 <> '' THEN '分公司' ELSE '事业部' EN
```

### I8：消费者事业部各城市分公司业绩排名

- **目标数据集**：2
- **预期行为**：排名
- **状态**：✅ 成功
- **耗时**：5.72s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前3的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "郑州城市公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "曲靖城市公司", "targetLevel": "城市分公司", "text": "已按达成率输出 3 个城市分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["郑州城市公司", "临沂城市公司", "曲靖城市公司"]}
- **叙述**：["本次结果覆盖 3 个城市分公司", "第一梯队：郑州城市公司49.95%", "第二梯队：临沂城市公司47.37%", "第三梯队：曲靖城市公司42.98%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I9：商用事业部四大分公司业绩整体盘点

- **目标数据集**：3
- **预期行为**：总览 / 对比
- **状态**：✅ 成功
- **耗时**：2.54s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部四大分公司业绩整体盘点
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "310000000.0"}, {"title": "累计年度开单金额", "value": "71851963.5627677"}, {"title": "整体达成率", "value": "23.17805276218313"}, {"title": "东部分公司达成率", "value": "23.71"}, {"title": "北部分公司达成率", "value": "24.91"}, {"title": "南部分公司达成率", "value": "24.69"}, {"title": "西部分公司达成率", "value": "19.08"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 4 个分公司", "对比对象：东部分公司：开单2253万 / 任务9500万，达成率23.71%，剩余缺口7247万；北部分公司：开单1584万 / 任务6360万，达成率24.91%，剩余缺口4776万；南部分公司：开单2024万 / 任务8200万，达成率24.69%，剩余缺口6176万；西部分公司：开单1324万 / 任务6940万，达成率19.08%，剩余缺口5616万", "首尾差异：北部分公司达成率比西部分公司高5.83个百分点", "第一梯队：北部分公司24.91%、南部分公司24.69%", "第二梯队：东部分公司23.71%", "第三梯队：西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### I10：所有细分业务按年度开单金额排名

- **目标数据集**：62
- **预期行为**：排名
- **状态**：✅ 成功
- **耗时**：4.89s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：所有细分业务按年度开单金额排名
- **报告标题**：
- **SQL 样例**：
```sql
SELECT '电商业务' AS 条线,
                '业务承接角色' AS 层级,
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 3;
```
- **⚠️ 异常点**：结果为空

### I11：消费者事业部达成率在 30%~50% 之间的分公司

- **目标数据集**：2
- **预期行为**：区间筛选
- **状态**：✅ 成功
- **耗时**：5.18s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率在 30%~50% 之间的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### I12：商用事业部南部分公司下属代表处业绩

- **目标数据集**：3
- **预期行为**：下钻
- **状态**：✅ 成功
- **耗时**：2.62s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部南部分公司下属代表处业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 分公司 / 代表处下钻分析
- **图表**：各分公司 / 代表处达成率排序
- **折叠面板**：湖南代表处 / 粤东代表处 / 北部分公司 / 南部分公司 / 东部分公司 / 粤西广西代表处 / 江西代表处 / 西部分公司 / 福建代表处 / 餐饮
- **答案摘要**：{"childCount": 10, "focusNode": "商用事业部", "mode": "drilldown", "targetLevel": "分公司 / 代表处", "text": "已定位到 商用事业部，当前展示其下一级 10 个分公司 / 代表处", "title": "下钻结果"}
- **叙述**：["本次结果覆盖 10 个分公司 / 代表处", "第一梯队：湖南代表处34.55%、粤东代表处28.90%、北部分公司24.91%、南部分公司24.69%", "第二梯队：东部分公司23.71%、粤西广西代表处22.19%、江西代表处20.35%", "第三梯队：西部分公司19.08%、福建代表处15.01%、餐饮12.83%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### I13：哪个分公司最低

- **目标数据集**：2
- **预期行为**：单点极值
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"ranking","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[],
- **耗时**：2.56s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### I14：商用事业部哪个代表处开单金额最高

- **目标数据集**：3
- **预期行为**：单点极值
- **状态**：✅ 成功
- **耗时**：2.55s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部开单金额最高的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "28500000.0"}, {"title": "年度开单金额", "value": "8236409.04"}, {"title": "达成率", "value": "28.9"}, {"title": "剩余任务金额", "value": "20263590.96"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处年度开单金额排序
- **折叠面板**：粤东代表处
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "粤东代表处", "metricLabel": "年度开单金额", "mode": "ranking", "rankSides": "top", "tail": "", "targetLevel": "代表处", "text": "最高的代表处是 粤东代表处", "title": "最高结果", "topN": 1, "topNames": ["粤东代表处"]}
- **叙述**：["本次结果覆盖 1 个代表处", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I15：电商事业部前 5 的细分业务

- **目标数据集**：62
- **预期行为**：排名
- **状态**：✅ 成功
- **耗时**：4.85s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部前 5 的细分业务
- **报告标题**：
- **SQL 样例**：
```sql
SELECT '电商业务' AS 条线,
                '业务承接角色' AS 层级,
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 总任务达成率 DESC LIMIT 5;
```
- **⚠️ 异常点**：结果为空

### I16：消费者事业部倒数前 3 的城市分公司

- **目标数据集**：2
- **预期行为**：排名 bottom 3
- **状态**：✅ 成功
- **耗时**：5.02s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前3的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司 / 淄博城市公司 / 洛阳城市公司 / 乐山城市公司
- **答案摘要**：{"bottomNames": ["乐山城市公司", "洛阳城市公司", "淄博城市公司"], "direction": "desc", "leader": "郑州城市公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "both", "tail": "淄博城市公司", "targetLevel": "城市分公司", "text": "已按达成率输出前3和后3个城市分公司的排序结果", "title": "排名结果", "topN": 6, "topNames": ["郑州城市公司", "临沂城市公司", "曲靖城市公司"]}
- **叙述**：["本次结果覆盖 6 个城市分公司", "第一梯队：郑州城市公司49.95%、临沂城市公司47.37%", "第二梯队：曲靖城市公司42.98%、淄博城市公司3.26%", "第三梯队：洛阳城市公司0.00%、乐山城市公司0.00%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I17：商用事业部达成率超过 80% 的分公司

- **目标数据集**：3
- **预期行为**：阈值筛选
- **状态**：✅ 成功
- **耗时**：2.54s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率大于80%的分公司
- **报告标题**：经营分析报告
- **章节**：总体判断 / 下一层级对比分析
- **答案摘要**：{"matchedCount": 0, "metricLabel": "达成率", "mode": "filter", "operator": ">", "targetLevel": "下一层级", "text": "未命中符合条件的下一层级", "title": "命中结果", "value": 80.0}
- **叙述**：["当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：结果为空

### I18：电商事业部年度开单金额低于 500 万的业务

- **目标数据集**：62
- **预期行为**：阈值筛选
- **状态**：✅ 成功
- **耗时**：5.22s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部年度开单金额低于 500 万的业务
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' AND (年度开单金额) < 5000000.0 ORDER BY 年度开单金额 asc LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### I19：消费者事业部业绩总览

- **目标数据集**：2
- **预期行为**：总览
- **状态**：✅ 成功
- **耗时**：5.02s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部业绩总览
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### I20：商用事业部业绩总览

- **目标数据集**：3
- **预期行为**：总览
- **状态**：✅ 成功
- **耗时**：2.66s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部业绩总览
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### I21：电商事业部业绩总览

- **目标数据集**：62
- **预期行为**：总览
- **状态**：✅ 成功
- **耗时**：5.12s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部业绩总览
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### I22：消费者事业部各分公司达成率对比

- **目标数据集**：2
- **预期行为**：对比
- **状态**：✅ 成功
- **耗时**：5.58s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部各分公司达成率对比
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "分公司数量", "value": "13"}, {"title": "累计总任务金额", "value": "1789710000.0"}, {"title": "累计年度开单金额", "value": "521218325.99"}, {"title": "整体达成率", "value": "29.12306049527577"}, {"title": "最高：河北分公司", "value": "33.89"}, {"title": "最低：江浙沪分公司", "value": "19.03"}, {"title": "首尾差距", "value": "14.86"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 13 个分公司在下方对比表展开。", "首尾差异：河北分公司达成率比京津分公司高5.95个百分点", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### I23：商用事业部各分公司年度开单金额对比

- **目标数据集**：3
- **预期行为**：对比
- **状态**：✅ 成功
- **耗时**：2.8s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部各分公司年度开单金额对比
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "业务部 / 分公司数量", "value": "7"}, {"title": "累计总任务金额", "value": "455000000.0"}, {"title": "累计年度开单金额", "value": "131114522.4527676"}, {"title": "整体达成率", "value": "28.816378561047824"}, {"title": "最高：公共办公业务部", "value": "80.76"}, {"title": "最低：西部分公司", "value": "19.08"}, {"title": "首尾差距", "value": "61.68000000000001"}]
- **章节**：总体判断 / 业务部 / 分公司对比分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 7 个业务部 / 分公司在下方对比表展开。", "首尾差异：公共办公业务部达成率比东部分公司高57.05个百分点", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### I24：电商事业部三大业务部年度目标营收对比

- **目标数据集**：62
- **预期行为**：对比
- **状态**：✅ 成功
- **耗时**：5.07s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部三大业务部年度目标营收对比
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','国内业务部','直营零售部','跨境业务部') AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### I25：消费者事业部业绩排名

- **目标数据集**：2
- **预期行为**：排名
- **状态**：✅ 成功
- **耗时**：7.77s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前3的消费者事业部
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "11099.0"}, {"title": "年度开单金额", "value": "3761.8"}, {"title": "达成率", "value": "33.89"}, {"title": "剩余任务金额", "value": "7337.2"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "河北分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "黑吉辽分公司", "targetLevel": "分公司", "text": "已按达成率输出 3 个分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["河北分公司", "豫晋分公司", "黑吉辽分公司"]}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
```sql
WITH 源数据 AS (
  SELECT
    fields,
    COALESCE(NULLIF(regexp_replace(fields ->> '总任务（金额）', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 总任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 年度开单原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '线下', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 线下任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '线下-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 线下实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '新零售', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 新零售任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '新零售-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 新零售实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '燃气定制', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 燃气定制任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '燃气定制-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 燃气定制实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '地产', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 地产任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '地产-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 地产实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '总任务达成率', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 达成率原值
  FROM public.feishu_tbl_xioafeizhe
),
标准结果 AS (
  SELECT
    '消费者事业部' AS 条线,
    CASE
      WHEN NULLIF(fields ->> '分公司', '') IS NULL THEN '消费者事业部总体'
      WHEN NULLIF(fields ->> '城市分公司', '') IS NULL THEN '分公司'
      ELSE '城市分公司'
    END AS 层级,
    CASE
      WHEN NULLI
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I26：商用事业部代表处业绩排名

- **目标数据集**：3
- **预期行为**：排名
- **状态**：✅ 成功
- **耗时**：2.59s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名前10的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "12200000.0"}, {"title": "年度开单金额", "value": "4590966.97999999"}, {"title": "达成率", "value": "37.63"}, {"title": "剩余任务金额", "value": "7609033.02"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：山东代表处 / 湖南代表处 / 粤东代表处 / 津冀代表处 / 黑龙江代表处 / 北京代表处 / 四川代表处 / 新西代表处 / 浙江代表处 / 上海代表处 / 粤西广西代表处 / 陕西代表处
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "山东代表处", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "上海代表处", "targetLevel": "代表处", "text": "已按达成率输出 10 个代表处的排序结果", "title": "排名结果", "topN": 10, "topNames": ["山东代表处", "湖南代表处", "粤东代表处", "津冀代表处", "黑龙江代表处", "北京代表处", "四川代表处", "新西代表处", "浙江代表处", "上海代表处"]}
- **叙述**：["本次结果覆盖 12 个代表处", "第一梯队：山东代表处37.63%、湖南代表处34.55%、粤东代表处28.90%、津冀代表处28.86%", "第二梯队：黑龙江代表处28.73%、北京代表处26.32%、四川代表处25.98%、新西代表处25.01%", "第三梯队：浙江代表处24.09%、上海代表处24.04%、粤西广西代表处22.19%、陕西代表处18.50%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I27：电商事业部业务承接人业绩排名

- **目标数据集**：62
- **预期行为**：排名
- **状态**：✅ 成功
- **耗时**：5.12s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部业务承接人业绩排名
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 总任务达成率 DESC LIMIT 3;
```
- **⚠️ 异常点**：结果为空

### I28：消费者事业部缺口最大的分公司

- **目标数据集**：2
- **预期行为**：极值
- **状态**：✅ 成功
- **耗时**：5.26s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部剩余任务金额排名前3的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "219040000.0"}, {"title": "年度开单金额", "value": "62561778.0"}, {"title": "达成率", "value": "28.56"}, {"title": "剩余任务金额", "value": "156478222.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司剩余任务金额排序
- **折叠面板**：鄂皖分公司 / 粤桂琼分公司 / 豫晋分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "鄂皖分公司", "metricLabel": "剩余任务金额", "mode": "ranking", "rankSides": "top", "tail": "豫晋分公司", "targetLevel": "分公司", "text": "已按剩余任务金额输出 3 个分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["鄂皖分公司", "粤桂琼分公司", "豫晋分公司"]}
- **叙述**：["本次结果覆盖 3 个分公司", "第一梯队：豫晋分公司32.69%", "第二梯队：鄂皖分公司28.56%", "第三梯队：粤桂琼分公司27.25%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I29：商用事业部剩余任务最少的分公司

- **目标数据集**：3
- **预期行为**：极值
- **状态**：✅ 成功
- **耗时**：2.65s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部剩余任务金额排名后10的分公司
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "95000000.0"}, {"title": "年度开单金额", "value": "22526100.19"}, {"title": "达成率", "value": "23.71"}, {"title": "剩余任务金额", "value": "72473899.81"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司剩余任务金额排序
- **折叠面板**：东部分公司
- **答案摘要**：{"bottomNames": [], "direction": "asc", "leader": "东部分公司", "metricLabel": "剩余任务金额", "mode": "ranking", "rankSides": "top", "tail": "", "targetLevel": "分公司", "text": "最低的分公司是 东部分公司", "title": "最低结果", "topN": 1, "topNames": ["东部分公司"]}
- **叙述**：["本次结果覆盖 1 个分公司", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### I30：电商事业部毛利率最高的业务部

- **目标数据集**：62
- **预期行为**：极值
- **状态**：✅ 成功
- **耗时**：4.96s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部毛利率最高的业务部
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务部' ORDER BY 总任务达成率 DESC LIMIT 1;
```
- **⚠️ 异常点**：结果为空

### M1：消费者事业部总任务金额

- **目标数据集**：2
- **预期行为**：金额单位应为“万元”
- **状态**：✅ 成功
- **耗时**：5.28s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部总任务金额
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### M2：消费者事业部完成率

- **目标数据集**：2
- **预期行为**：指标应为达成率，不能错用开单金额
- **状态**：✅ 成功
- **耗时**：5.07s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部完成率
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### M3：商用事业部剩余任务金额

- **目标数据集**：3
- **预期行为**：缺口口径，金额单位正确
- **状态**：✅ 成功
- **耗时**：2.67s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部剩余任务金额
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### M4：电商事业部年度目标营收 vs 年度开单金额对比

- **目标数据集**：62
- **预期行为**：双指标对比，字段不能混用
- **状态**：✅ 成功
- **耗时**：5.09s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部年度目标营收 vs 年度开单金额对比
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部') AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### M5：商用事业部年度开单金额最高的分公司

- **目标数据集**：3
- **预期行为**：按金额排序，非达成率
- **状态**：✅ 成功
- **耗时**：2.69s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部开单金额最高的分公司
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "95000000.0"}, {"title": "年度开单金额", "value": "22526100.19"}, {"title": "达成率", "value": "23.71"}, {"title": "剩余任务金额", "value": "72473899.81"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司年度开单金额排序
- **折叠面板**：东部分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "东部分公司", "metricLabel": "年度开单金额", "mode": "ranking", "rankSides": "top", "tail": "", "targetLevel": "分公司", "text": "最高的分公司是 东部分公司", "title": "最高结果", "topN": 1, "topNames": ["东部分公司"]}
- **叙述**：["本次结果覆盖 1 个分公司", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### M6：消费者事业部缺口最大的分公司

- **目标数据集**：2
- **预期行为**：按剩余任务/缺口排序
- **状态**：✅ 成功
- **耗时**：5.1s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部剩余任务金额排名前3的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "219040000.0"}, {"title": "年度开单金额", "value": "62561778.0"}, {"title": "达成率", "value": "28.56"}, {"title": "剩余任务金额", "value": "156478222.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司剩余任务金额排序
- **折叠面板**：鄂皖分公司 / 粤桂琼分公司 / 豫晋分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "鄂皖分公司", "metricLabel": "剩余任务金额", "mode": "ranking", "rankSides": "top", "tail": "豫晋分公司", "targetLevel": "分公司", "text": "已按剩余任务金额输出 3 个分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["鄂皖分公司", "粤桂琼分公司", "豫晋分公司"]}
- **叙述**：["本次结果覆盖 3 个分公司", "第一梯队：豫晋分公司32.69%", "第二梯队：鄂皖分公司28.56%", "第三梯队：粤桂琼分公司27.25%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### M7：电商事业部年度目标营收完成率

- **目标数据集**：62
- **预期行为**：自定义指标组合
- **状态**：✅ 成功
- **耗时**：5.08s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部年度目标营收完成率
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### M8：商用事业部 q1 目标金额

- **目标数据集**：3
- **预期行为**：季度目标口径
- **状态**：✅ 成功
- **耗时**：2.71s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部 q1 目标金额
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### M9：消费者事业部完成金额

- **目标数据集**：2
- **预期行为**：应指向年度开单金额
- **状态**：✅ 成功
- **耗时**：5.31s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部完成金额
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### M10：商用事业部任务完成率

- **目标数据集**：3
- **预期行为**：应指向达成率
- **状态**：✅ 成功
- **耗时**：2.61s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部任务完成率
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### M11：电商事业部预算完成率

- **目标数据集**：62
- **预期行为**：年度目标营收完成率
- **状态**：✅ 成功
- **耗时**：5.2s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部预算完成率
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### M12：商用事业部总任务金额

- **目标数据集**：3
- **预期行为**：金额口径
- **状态**：✅ 成功
- **耗时**：2.52s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部总任务金额
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### M13：消费者事业部年度开单金额排名

- **目标数据集**：2
- **预期行为**：金额排序
- **状态**：✅ 成功
- **耗时**：5.06s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部开单金额排名前3的消费者事业部
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司年度开单金额排序
- **折叠面板**：豫晋分公司 / 鄂皖分公司 / 粤桂琼分公司 / 赣闽分公司 / 湖南分公司 / 西北分公司 / 云贵渝分公司 / 河北分公司 / 山东分公司 / 川藏分公司 / 黑吉辽分公司 / 江浙沪分公司 / 京津分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "豫晋分公司", "metricLabel": "年度开单金额", "mode": "ranking", "rankSides": "top", "tail": "粤桂琼分公司", "targetLevel": "分公司", "text": "已按年度开单金额输出 3 个分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["豫晋分公司", "鄂皖分公司", "粤桂琼分公司"]}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### M14：商用事业部达成率排名

- **目标数据集**：3
- **预期行为**：率排序
- **状态**：✅ 成功
- **耗时**：2.76s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名前10的商用事业部
- **报告标题**：经营分析报告
- **章节**：总体判断 / 下一层级对比分析
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "", "targetLevel": "下一层级", "text": "当前没有可排序的下一层级结果", "title": "排名结果", "topN": 0, "topNames": []}
- **叙述**：["当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：结果为空; 卡片标题与问题关联度低

### M15：电商事业部年度开单金额排名

- **目标数据集**：62
- **预期行为**：金额排序
- **状态**：✅ 成功
- **耗时**：5.12s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部年度开单金额排名
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 3;
```
- **⚠️ 异常点**：结果为空

### M16：消费者事业部实际完成情况

- **目标数据集**：2
- **预期行为**：金额或率需明确
- **状态**：✅ 成功
- **耗时**：5.5s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部实际完成情况
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### M17：商用事业部还差多少任务

- **目标数据集**：3
- **预期行为**：缺口口径
- **状态**：✅ 成功
- **耗时**：2.53s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部还差多少任务
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：西部分公司 / 东部分公司 / 南部分公司 / 北部分公司 / 餐饮业务部 / 工业医疗业务部 / 公共办公业务部
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### M18：电商事业部目标营收完成率最低的细分业务

- **目标数据集**：62
- **预期行为**：率排序
- **状态**：✅ 成功
- **耗时**：5.02s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部目标营收完成率最低的细分业务
- **报告标题**：
- **SQL 样例**：
```sql
SELECT '电商业务' AS 条线,
                '业务承接角色' AS 层级,
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 总任务达成率 ASC LIMIT 1;
```
- **⚠️ 异常点**：结果为空

### M19：消费者事业部哪个分公司销售额最高

- **目标数据集**：2
- **预期行为**：年度开单金额
- **状态**：✅ 成功
- **耗时**：4.97s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部开单金额最高的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "204400000.0"}, {"title": "年度开单金额", "value": "66824890.0"}, {"title": "达成率", "value": "32.69"}, {"title": "剩余任务金额", "value": "137575110.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司年度开单金额排序
- **折叠面板**：豫晋分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "豫晋分公司", "metricLabel": "年度开单金额", "mode": "ranking", "rankSides": "top", "tail": "", "targetLevel": "分公司", "text": "最高的分公司是 豫晋分公司", "title": "最高结果", "topN": 1, "topNames": ["豫晋分公司"]}
- **叙述**：["本次结果覆盖 1 个分公司", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### M20：商用事业部哪个分公司完成进度最快

- **目标数据集**：3
- **预期行为**：达成率
- **状态**：✅ 成功
- **耗时**：2.74s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部哪个分公司完成进度最快
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "310000000.0"}, {"title": "累计年度开单金额", "value": "71851963.5627677"}, {"title": "整体达成率", "value": "23.17805276218313"}, {"title": "东部分公司达成率", "value": "23.71"}, {"title": "北部分公司达成率", "value": "24.91"}, {"title": "南部分公司达成率", "value": "24.69"}, {"title": "西部分公司达成率", "value": "19.08"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 4 个分公司", "对比对象：东部分公司：开单2253万 / 任务9500万，达成率23.71%，剩余缺口7247万；北部分公司：开单1584万 / 任务6360万，达成率24.91%，剩余缺口4776万；南部分公司：开单2024万 / 任务8200万，达成率24.69%，剩余缺口6176万；西部分公司：开单1324万 / 任务6940万，达成率19.08%，剩余缺口5616万", "首尾差异：北部分公司达成率比西部分公司高5.83个百分点", "第一梯队：北部分公司24.91%、南部分公司24.69%", "第二梯队：东部分公司23.71%", "第三梯队：西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### M21：电商事业部哪个业务线利润最高

- **目标数据集**：62
- **预期行为**：毛利/利润口径
- **状态**：✅ 成功
- **耗时**：5.08s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部哪个业务线利润最高
- **报告标题**：
- **SQL 样例**：
```sql
SELECT '电商业务' AS 条线,
                '业务承接角色' AS 层级,
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 细分业务 IN ('电商事业部') AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### M22：消费者事业部任务达成率

- **目标数据集**：2
- **预期行为**：达成率
- **状态**：✅ 成功
- **耗时**：5.44s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部任务达成率
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### M23：商用事业部开单金额

- **目标数据集**：3
- **预期行为**：年度开单金额
- **状态**：✅ 成功
- **耗时**：2.57s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部开单金额
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### M24：电商事业部营收完成情况

- **目标数据集**：62
- **预期行为**：年度目标营收完成率
- **状态**：✅ 成功
- **耗时**：5.23s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部营收完成情况
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### M25：商用事业部代表处人均业绩

- **目标数据集**：3
- **预期行为**：需聚合后计算，可能不支持但看兜底
- **状态**：✅ 成功
- **耗时**：2.73s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部代表处人均业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 代表处下钻分析
- **图表**：各代表处达成率排序
- **折叠面板**：山东代表处 / 湖南代表处 / 粤东代表处 / 津冀代表处 / 黑龙江代表处 / 北京代表处 / 四川代表处 / 新西代表处 / 浙江代表处 / 上海代表处 / 江苏代表处 / 辽宁代表处 / 粤西广西代表处 / 湖北代表处 / 江西代表处 / 陕西代表处 / 云贵代表处 / 晋蒙（蒙西）代表处 / 安徽代表处 / 福建代表处 / 吉林代表处 / 河南代表处 / 重庆代表处 / 餐饮 / 甘青宁代表处
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 25 个代表处", "第一梯队：山东代表处37.63%、湖南代表处34.55%、粤东代表处28.90%、津冀代表处28.86%、黑龙江代表处28.73%、北京代表处26.32%、四川代表处25.98%、新西代表处25.01%、浙江代表处24.09%", "第二梯队：上海代表处24.04%、江苏代表处23.77%、辽宁代表处23.18%、粤西广西代表处22.19%、湖北代表处20.92%、江西代表处20.35%、陕西代表处18.50%、云贵代表处17.84%", "第三梯队：晋蒙（蒙西）代表处17.15%、安徽代表处16.96%、福建代表处15.01%、吉林代表处14.69%、河南代表处13.07%、重庆代表处12.96%、餐饮12.83%、甘青宁代表处11.02%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### L1：商用事业部东部分公司下有哪些代表处

- **目标数据集**：3
- **预期行为**：事业部 → 分公司 → 代表处
- **状态**：✅ 成功
- **耗时**：2.55s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部东部分公司下有哪些代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 分公司 / 代表处下钻分析
- **图表**：各分公司 / 代表处达成率排序
- **折叠面板**：山东代表处 / 北部分公司 / 南部分公司 / 浙江代表处 / 上海代表处 / 江苏代表处 / 东部分公司 / 湖北代表处 / 西部分公司 / 安徽代表处 / 河南代表处
- **答案摘要**：{"childCount": 11, "focusNode": "商用事业部", "mode": "drilldown", "targetLevel": "分公司 / 代表处", "text": "已定位到 商用事业部，当前展示其下一级 11 个分公司 / 代表处", "title": "下钻结果"}
- **叙述**：["本次结果覆盖 11 个分公司 / 代表处", "第一梯队：山东代表处37.63%、北部分公司24.91%、南部分公司24.69%、浙江代表处24.09%", "第二梯队：上海代表处24.04%、江苏代表处23.77%、东部分公司23.71%、湖北代表处20.92%", "第三梯队：西部分公司19.08%、安徽代表处16.96%、河南代表处13.07%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### L2：商用事业部餐饮业务部业绩

- **目标数据集**：3
- **预期行为**：事业部 → 业务部
- **状态**：✅ 成功
- **耗时**：2.7s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部餐饮业务部业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "145000000.0"}, {"title": "累计年度开单金额", "value": "59262558.8899999"}, {"title": "整体达成率", "value": "40.870730268965445"}, {"title": "公共办公业务部达成率", "value": "80.76"}, {"title": "工业医疗业务部达成率", "value": "63.68"}, {"title": "餐饮业务部达成率", "value": "27.3"}]
- **章节**：总体判断 / 业务部下钻分析
- **图表**：各业务部达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 3 个业务部", "对比对象：公共办公业务部：开单2423万 / 任务3000万，达成率80.76%，剩余缺口577万；工业医疗业务部：开单637万 / 任务1000万，达成率63.68%，剩余缺口363万；餐饮业务部：开单2867万 / 任务1.05亿，达成率27.30%，剩余缺口7633万", "首尾差异：公共办公业务部达成率比餐饮业务部高53.46个百分点", "第一梯队：公共办公业务部80.76%", "第二梯队：工业医疗业务部63.68%", "第三梯队：餐饮业务部27.30%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### L3：消费者事业部粤桂琼分公司下属城市分公司业绩

- **目标数据集**：2
- **预期行为**：事业部 → 分公司 → 城市分公司
- **状态**：✅ 成功
- **耗时**：5.59s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部粤桂琼分公司下属城市分公司业绩
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司 / 城市分公司下钻分析
- **图表**：各分公司 / 城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司 / 西安城市公司 / 晋城城市公司 / 烟台城市公司 / 贵阳城市公司 / 太原城市公司 / 赣州城市公司 / 哈尔滨城市公司 / 保定城市公司 / 石家庄城市公司 / 廊坊城市公司 / 河北分公司 / 沈阳城市公司 / 天津城市公司 / 甘青宁城市公司 / 川西城市公司 / 武汉城市公司 / 宝鸡城市公司 / 豫晋分公司 / 南昌城市公司 / 长沙城市公司 / 唐山城市公司 / 遵义城市公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 襄阳城市公司 / 鄂尔多斯城市公司 / 桂南城市公司 / 湖南分公司 / 大连城市公司 / 东莞城市公司 / 济南城市公司 / 大理城市公司 / 驻马店城市公司 / 赣闽分公司 / 绵阳城市公司 / 宜昌城市公司 / 榆林城市公司 / 重庆城市公司 / 川南城市公司 / 长春城市公司 / 鄂皖分公司 / 宜春城市公司 / 大同城市公司 / 深圳城市公司 / 厦门城市公司 / 京津分公司 / 新乡城市公司 / 粤桂琼分公司 / 广州城市公司 / 昆明城市公司 / 成都城市公司 / 黄石城市公司 / 北京城市公司 / 三明城市公司 / 浙东城市公司 / 粤西城市公司 / 邵阳城市公司 / 川藏分公司 / 青岛城市公司 / 桂东城市公司 / 苏中城市公司 / 万州城市公司 / 皖北城市公司 / 皖南城市公司 / 新疆城市公司 / 福州城市公司 / 苏北城市公司 / 江浙沪分公司 / 浙西城市公司 / 苏南城市公司 / 常德城市公司 / 川北城市公司 / 衡阳城市公司 / 上海城市公司 / 淄博城市公司 / 洛阳城市公司 / 乐山城市公司
- **答案摘要**：{"childCount": 82, "focusNode": "消费者事业部", "mode": "drilldown", "targetLevel": "分公司 / 城市分公司", "text": "已定位到 消费者事业部，当前展示其下一级 82 个分公司 / 城市分公司", "title": "下钻结果"}
- **叙述**：["本次结果覆盖 82 个分公司 / 城市分公司", "第一梯队：郑州城市公司49.95%、临沂城市公司47.37%、曲靖城市公司42.98%、西安城市公司37.64%、晋城城市公司37.30%、烟台城市公司36.24%、贵阳城市公司35.71%、太原城市公司35.62%、赣州城市公司35.06%、哈尔滨城市公司34.68%、保定城市公司34.64%、石家庄城市公司34.50%、廊坊城市公司34.18%、河北分公司33.89%、沈阳城市公司33.88%、天津城市公司33.73%、甘青宁城市公司33.46%、川西城市公司33.13%、武汉城市公司33.05%、宝鸡城市公司32.86%、豫晋分公司32.69%、南昌城市公司32.48%、长沙城市公司32.21%、唐山城市公司32.18%、遵义城市公司32.14%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、襄阳城市公司31.02%、鄂尔多斯城市公司30.79%、桂南城市公司30.66%、湖南分公司30.27%、大连城市公司30.20%、东莞城市公司30.04%、济南城市
- **SQL 样例**：
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
    FROM public.fei
```

### L4：电商事业部净水业务负责人是谁

- **目标数据集**：62
- **预期行为**：细分业务 → 承接人
- **状态**：✅ 成功
- **耗时**：5.2s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部净水业务负责人是谁
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 IN ('电商事业部','净水业务') AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### L5：商用事业部业务员业绩排名

- **目标数据集**：3
- **预期行为**：业务员层级
- **状态**：✅ 成功
- **耗时**：2.78s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名前10的业务代表
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "12000000.0"}, {"title": "年度开单金额", "value": "11211139.62"}, {"title": "达成率", "value": "93.43"}, {"title": "剩余任务金额", "value": "788860.38"}]
- **章节**：总体判断 / 业务代表对比分析
- **图表**：各业务代表达成率排序
- **折叠面板**：韩晓娇 / 张松 / 赵标
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "韩晓娇", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "赵标", "targetLevel": "业务代表", "text": "已按达成率输出 3 个业务代表的排序结果", "title": "排名结果", "topN": 3, "topNames": ["韩晓娇", "张松", "赵标"]}
- **叙述**：["本次结果覆盖 3 个业务代表", "第一梯队：韩晓娇93.43%", "第二梯队：张松83.38%", "第三梯队：赵标68.95%"]
- **SQL 样例**：
```sql
WITH 业务代表原始 AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        '' AS 业务部,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
业务代表汇总 AS (
    SELECT
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '业务代表' AS 层级,
        业务代表 AS 节点名称,
        COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部') AS 
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### L6：消费者事业部前 5 的城市分公司

- **目标数据集**：2
- **预期行为**：城市分公司层级
- **状态**：✅ 成功
- **耗时**：5.21s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前5的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司 / 西安城市公司 / 晋城城市公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "郑州城市公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "晋城城市公司", "targetLevel": "城市分公司", "text": "已按达成率输出 5 个城市分公司的排序结果", "title": "排名结果", "topN": 5, "topNames": ["郑州城市公司", "临沂城市公司", "曲靖城市公司", "西安城市公司", "晋城城市公司"]}
- **叙述**：["本次结果覆盖 5 个城市分公司", "第一梯队：郑州城市公司49.95%、临沂城市公司47.37%", "第二梯队：曲靖城市公司42.98%、西安城市公司37.64%", "第三梯队：晋城城市公司37.30%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### L7：商用事业部北部分公司业务代表业绩

- **目标数据集**：3
- **预期行为**：代表处/业务员层级
- **状态**：✅ 成功
- **耗时**：2.61s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部北部分公司业务代表业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "业务部 / 分公司数量", "value": "7"}, {"title": "累计总任务金额", "value": "455000000.0"}, {"title": "累计年度开单金额", "value": "131114522.4527676"}, {"title": "整体达成率", "value": "28.816378561047824"}, {"title": "最高：公共办公业务部", "value": "80.76"}, {"title": "最低：西部分公司", "value": "19.08"}, {"title": "首尾差距", "value": "61.68000000000001"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 7 个业务部 / 分公司在下方对比表展开。", "首尾差异：公共办公业务部达成率比东部分公司高57.05个百分点", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### L8：国内业务部各细分业务年度开单金额

- **目标数据集**：62
- **预期行为**：业务部 → 细分业务
- **状态**：✅ 成功
- **耗时**：5.13s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：国内业务部各细分业务年度开单金额
- **报告标题**：
- **SQL 样例**：
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
- **⚠️ 异常点**：结果为空

### L9：商用事业部东部分公司代表处业绩排名

- **目标数据集**：3
- **预期行为**：分公司 → 代表处
- **状态**：✅ 成功
- **耗时**：2.68s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名前10的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "12200000.0"}, {"title": "年度开单金额", "value": "4590966.97999999"}, {"title": "达成率", "value": "37.63"}, {"title": "剩余任务金额", "value": "7609033.02"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：山东代表处 / 湖南代表处 / 粤东代表处 / 津冀代表处 / 黑龙江代表处 / 北京代表处 / 四川代表处 / 新西代表处 / 浙江代表处 / 上海代表处 / 粤西广西代表处 / 陕西代表处
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "山东代表处", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "上海代表处", "targetLevel": "代表处", "text": "已按达成率输出 10 个代表处的排序结果", "title": "排名结果", "topN": 10, "topNames": ["山东代表处", "湖南代表处", "粤东代表处", "津冀代表处", "黑龙江代表处", "北京代表处", "四川代表处", "新西代表处", "浙江代表处", "上海代表处"]}
- **叙述**：["本次结果覆盖 12 个代表处", "第一梯队：山东代表处37.63%、湖南代表处34.55%、粤东代表处28.90%、津冀代表处28.86%", "第二梯队：黑龙江代表处28.73%、北京代表处26.32%、四川代表处25.98%、新西代表处25.01%", "第三梯队：浙江代表处24.09%、上海代表处24.04%、粤西广西代表处22.19%、陕西代表处18.50%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### L10：消费者事业部华南分公司下属城市公司

- **目标数据集**：2
- **预期行为**：分公司 → 城市分公司
- **状态**：✅ 成功
- **耗时**：5.46s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部华南分公司下属城市公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司 / 城市分公司下钻分析
- **图表**：各分公司 / 城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司 / 西安城市公司 / 晋城城市公司 / 烟台城市公司 / 贵阳城市公司 / 太原城市公司 / 赣州城市公司 / 哈尔滨城市公司 / 保定城市公司 / 石家庄城市公司 / 廊坊城市公司 / 河北分公司 / 沈阳城市公司 / 天津城市公司 / 甘青宁城市公司 / 川西城市公司 / 武汉城市公司 / 宝鸡城市公司 / 豫晋分公司 / 南昌城市公司 / 长沙城市公司 / 唐山城市公司 / 遵义城市公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 襄阳城市公司 / 鄂尔多斯城市公司 / 桂南城市公司 / 湖南分公司 / 大连城市公司 / 东莞城市公司 / 济南城市公司 / 大理城市公司 / 驻马店城市公司 / 赣闽分公司 / 绵阳城市公司 / 宜昌城市公司 / 榆林城市公司 / 重庆城市公司 / 川南城市公司 / 长春城市公司 / 鄂皖分公司 / 宜春城市公司 / 大同城市公司 / 深圳城市公司 / 厦门城市公司 / 京津分公司 / 新乡城市公司 / 粤桂琼分公司 / 广州城市公司 / 昆明城市公司 / 成都城市公司 / 黄石城市公司 / 北京城市公司 / 三明城市公司 / 浙东城市公司 / 粤西城市公司 / 邵阳城市公司 / 川藏分公司 / 青岛城市公司 / 桂东城市公司 / 苏中城市公司 / 万州城市公司 / 皖北城市公司 / 皖南城市公司 / 新疆城市公司 / 福州城市公司 / 苏北城市公司 / 江浙沪分公司 / 浙西城市公司 / 苏南城市公司 / 常德城市公司 / 川北城市公司 / 衡阳城市公司 / 上海城市公司 / 淄博城市公司 / 洛阳城市公司 / 乐山城市公司
- **答案摘要**：{"childCount": 82, "focusNode": "消费者事业部", "mode": "drilldown", "targetLevel": "分公司 / 城市分公司", "text": "已定位到 消费者事业部，当前展示其下一级 82 个分公司 / 城市分公司", "title": "下钻结果"}
- **叙述**：["本次结果覆盖 82 个分公司 / 城市分公司", "第一梯队：郑州城市公司49.95%、临沂城市公司47.37%、曲靖城市公司42.98%、西安城市公司37.64%、晋城城市公司37.30%、烟台城市公司36.24%、贵阳城市公司35.71%、太原城市公司35.62%、赣州城市公司35.06%、哈尔滨城市公司34.68%、保定城市公司34.64%、石家庄城市公司34.50%、廊坊城市公司34.18%、河北分公司33.89%、沈阳城市公司33.88%、天津城市公司33.73%、甘青宁城市公司33.46%、川西城市公司33.13%、武汉城市公司33.05%、宝鸡城市公司32.86%、豫晋分公司32.69%、南昌城市公司32.48%、长沙城市公司32.21%、唐山城市公司32.18%、遵义城市公司32.14%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、襄阳城市公司31.02%、鄂尔多斯城市公司30.79%、桂南城市公司30.66%、湖南分公司30.27%、大连城市公司30.20%、东莞城市公司30.04%、济南城市
- **SQL 样例**：
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
    FROM public.fei
```

### L11：商用事业部工业医疗业务部业务员业绩

- **目标数据集**：3
- **预期行为**：业务部 → 业务员
- **状态**：✅ 成功
- **耗时**：2.56s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部工业医疗业务部业务员业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "业务部 / 业务代表数量", "value": "6"}, {"title": "累计总任务金额", "value": "155000000.0"}, {"title": "累计年度开单金额", "value": "59506939.8899999"}, {"title": "整体达成率", "value": "38.39157412258058"}, {"title": "最高：公共办公业务部", "value": "80.76"}, {"title": "最低：董峰", "value": "0.00%"}, {"title": "首尾差距", "value": "80.76"}]
- **章节**：总体判断 / 业务部 / 业务代表下钻分析
- **图表**：各业务部 / 业务代表达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 陈林 / 张坤 / 董峰
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 6 个业务部 / 业务代表", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 6 个业务部 / 业务代表在下方对比表展开。", "首尾差异：公共办公业务部达成率比张坤高80.76个百分点", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%", "第二梯队：餐饮业务部27.30%、陈林8.15%", "第三梯队：张坤0.00%、董峰0.00%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### L12：电商事业部京东直营业绩

- **目标数据集**：62
- **预期行为**：细分业务
- **状态**：✅ 成功
- **耗时**：5.2s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部京东直营业绩
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','京东直营') AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### L13：消费者事业部山东分公司业绩

- **目标数据集**：2
- **预期行为**：分公司
- **状态**：✅ 成功
- **耗时**：5.63s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部山东分公司业绩
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "分公司数量", "value": "13"}, {"title": "累计总任务金额", "value": "1789710000.0"}, {"title": "累计年度开单金额", "value": "521218325.99"}, {"title": "整体达成率", "value": "29.12306049527577"}, {"title": "最高：河北分公司", "value": "33.89"}, {"title": "最低：江浙沪分公司", "value": "19.03"}, {"title": "首尾差距", "value": "14.86"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 13 个分公司在下方对比表展开。", "首尾差异：河北分公司达成率比京津分公司高5.95个百分点", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### L14：商用事业部西部分公司代表处业绩

- **目标数据集**：3
- **预期行为**：分公司 → 代表处
- **状态**：✅ 成功
- **耗时**：2.7s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部西部分公司代表处业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "分公司 / 代表处数量", "value": "10"}, {"title": "累计总任务金额", "value": "379400000.0"}, {"title": "累计年度开单金额", "value": "85115546.78276767"}, {"title": "整体达成率", "value": "22.43425060167835"}, {"title": "最高：四川代表处", "value": "25.98"}, {"title": "最低：甘青宁代表处", "value": "11.02"}, {"title": "首尾差距", "value": "14.96"}]
- **章节**：总体判断 / 分公司 / 代表处下钻分析
- **图表**：各分公司 / 代表处达成率排序
- **折叠面板**：四川代表处 / 新西代表处 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司 / 陕西代表处 / 云贵代表处 / 重庆代表处 / 甘青宁代表处
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 10 个分公司 / 代表处", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 10 个分公司 / 代表处在下方对比表展开。", "首尾差异：四川代表处达成率比云贵代表处高8.14个百分点", "第一梯队：四川代表处25.98%、新西代表处25.01%、北部分公司24.91%、南部分公司24.69%", "第二梯队：东部分公司23.71%、西部分公司19.08%、陕西代表处18.50%", "第三梯队：云贵代表处17.84%、重庆代表处12.96%、甘青宁代表处11.02%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### L15：电商事业部直营零售部下属细分业务

- **目标数据集**：62
- **预期行为**：业务部 → 细分业务
- **状态**：✅ 成功
- **耗时**：5.23s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部直营零售部下属细分业务
- **报告标题**：
- **SQL 样例**：
```sql
SELECT '电商业务' AS 条线,
                '业务承接角色' AS 层级,
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 细分业务 IN ('电商事业部','直营零售部') AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### L16：商用事业部北部分公司有哪些业务部

- **目标数据集**：3
- **预期行为**：分公司 → 业务部
- **状态**：✅ 成功
- **耗时**：2.64s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部北部分公司有哪些业务部
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{"childCount": 7, "focusNode": "商用事业部", "mode": "drilldown", "targetLevel": "业务部 / 分公司", "text": "已定位到 商用事业部，当前展示其下一级 7 个业务部 / 分公司", "title": "下钻结果"}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### L17：消费者事业部城市分公司排名

- **目标数据集**：2
- **预期行为**：城市分公司
- **状态**：✅ 成功
- **耗时**：5.18s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前3的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "郑州城市公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "曲靖城市公司", "targetLevel": "城市分公司", "text": "已按达成率输出 3 个城市分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["郑州城市公司", "临沂城市公司", "曲靖城市公司"]}
- **叙述**：["本次结果覆盖 3 个城市分公司", "第一梯队：郑州城市公司49.95%", "第二梯队：临沂城市公司47.37%", "第三梯队：曲靖城市公司42.98%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### L18：电商事业部负责人刘志伟的业绩

- **目标数据集**：62
- **预期行为**：承接人
- **状态**：✅ 成功
- **耗时**：5.77s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部负责人刘志伟的业绩
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 IN ('电商事业部','刘志伟') AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### L19：商用事业部餐饮业务部代表处业绩

- **目标数据集**：3
- **预期行为**：业务部 → 代表处
- **状态**：✅ 成功
- **耗时**：2.53s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部餐饮业务部代表处业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "145000000.0"}, {"title": "累计年度开单金额", "value": "59262558.8899999"}, {"title": "整体达成率", "value": "40.870730268965445"}, {"title": "公共办公业务部达成率", "value": "80.76"}, {"title": "工业医疗业务部达成率", "value": "63.68"}, {"title": "餐饮业务部达成率", "value": "27.3"}]
- **章节**：总体判断 / 业务部下钻分析
- **图表**：各业务部达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 3 个业务部", "对比对象：公共办公业务部：开单2423万 / 任务3000万，达成率80.76%，剩余缺口577万；工业医疗业务部：开单637万 / 任务1000万，达成率63.68%，剩余缺口363万；餐饮业务部：开单2867万 / 任务1.05亿，达成率27.30%，剩余缺口7633万", "首尾差异：公共办公业务部达成率比餐饮业务部高53.46个百分点", "第一梯队：公共办公业务部80.76%", "第二梯队：工业医疗业务部63.68%", "第三梯队：餐饮业务部27.30%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### L20：消费者事业部粤桂琼与山东分公司对比

- **目标数据集**：2
- **预期行为**：分公司集合对比
- **状态**：✅ 成功
- **耗时**：5.34s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部粤桂琼与山东分公司对比
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "分公司数量", "value": "13"}, {"title": "累计总任务金额", "value": "1789710000.0"}, {"title": "累计年度开单金额", "value": "521218325.99"}, {"title": "整体达成率", "value": "29.12306049527577"}, {"title": "最高：河北分公司", "value": "33.89"}, {"title": "最低：江浙沪分公司", "value": "19.03"}, {"title": "首尾差距", "value": "14.86"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 13 个分公司在下方对比表展开。", "首尾差异：河北分公司达成率比京津分公司高5.95个百分点", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### L21：商用事业部四大分公司业绩对比

- **目标数据集**：3
- **预期行为**：分公司集合对比
- **状态**：✅ 成功
- **耗时**：2.71s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部四大分公司业绩对比
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "310000000.0"}, {"title": "累计年度开单金额", "value": "71851963.5627677"}, {"title": "整体达成率", "value": "23.17805276218313"}, {"title": "东部分公司达成率", "value": "23.71"}, {"title": "北部分公司达成率", "value": "24.91"}, {"title": "南部分公司达成率", "value": "24.69"}, {"title": "西部分公司达成率", "value": "19.08"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 4 个分公司", "对比对象：东部分公司：开单2253万 / 任务9500万，达成率23.71%，剩余缺口7247万；北部分公司：开单1584万 / 任务6360万，达成率24.91%，剩余缺口4776万；南部分公司：开单2024万 / 任务8200万，达成率24.69%，剩余缺口6176万；西部分公司：开单1324万 / 任务6940万，达成率19.08%，剩余缺口5616万", "首尾差异：北部分公司达成率比西部分公司高5.83个百分点", "第一梯队：北部分公司24.91%、南部分公司24.69%", "第二梯队：东部分公司23.71%", "第三梯队：西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### L22：电商事业部三大业务部对比

- **目标数据集**：62
- **预期行为**：业务部集合对比
- **状态**：✅ 成功
- **耗时**：5.23s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部三大业务部对比
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','国内业务部','直营零售部','跨境业务部') AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### L23：商用事业部南部分公司餐饮业务部业绩

- **目标数据集**：3
- **预期行为**：分公司 + 业务部组合
- **状态**：✅ 成功
- **耗时**：2.73s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部南部分公司餐饮业务部业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "业务部 / 分公司数量", "value": "7"}, {"title": "累计总任务金额", "value": "455000000.0"}, {"title": "累计年度开单金额", "value": "131114522.4527676"}, {"title": "整体达成率", "value": "28.816378561047824"}, {"title": "最高：公共办公业务部", "value": "80.76"}, {"title": "最低：西部分公司", "value": "19.08"}, {"title": "首尾差距", "value": "61.68000000000001"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 7 个业务部 / 分公司在下方对比表展开。", "首尾差异：公共办公业务部达成率比东部分公司高57.05个百分点", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### L24：消费者事业部山东分公司城市分公司排名

- **目标数据集**：2
- **预期行为**：分公司 → 城市分公司排名
- **状态**：✅ 成功
- **耗时**：5.15s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前3的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "郑州城市公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "曲靖城市公司", "targetLevel": "城市分公司", "text": "已按达成率输出 3 个城市分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["郑州城市公司", "临沂城市公司", "曲靖城市公司"]}
- **叙述**：["本次结果覆盖 3 个城市分公司", "第一梯队：郑州城市公司49.95%", "第二梯队：临沂城市公司47.37%", "第三梯队：曲靖城市公司42.98%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### L25：电商事业部国内业务部净水业务负责人

- **目标数据集**：62
- **预期行为**：业务部 → 细分业务 → 承接人
- **状态**：✅ 成功
- **耗时**：5.19s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部国内业务部净水业务负责人
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 IN ('电商事业部','国内业务部','净水业务') AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### E1：华北分公司的业绩

- **目标数据集**：2
- **预期行为**：无该节点或给出合理提示
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"analysis","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[]
- **耗时**：2.72s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### E2：不存在的代表处业绩

- **目标数据集**：3
- **预期行为**：友好兜底，不报错
- **状态**：✅ 成功
- **耗时**：2.69s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：不存在的代表处业绩
- **报告标题**：经营分析报告
- **章节**：总体判断 / 下一层级对比分析
- **答案摘要**：{}
- **叙述**：["当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```
- **⚠️ 异常点**：结果为空

### E3：前 100 的分公司

- **目标数据集**：2
- **预期行为**：N 超过实际数量时按实际返回
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"analysis","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[]
- **耗时**：2.6s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### E4：达成率低于 0% 的分公司

- **目标数据集**：2
- **预期行为**：无结果/空状态
- **状态**：✅ 成功
- **耗时**：0.21s
- **路由决策**：
- **意图**：
- **是否需要确认**：True
- **命中数据集**：[]
- **显示标题**：
- **报告标题**：
- **⚠️ 异常点**：意外弹确认; 卡片标题与问题关联度低

### E5：2023 年业绩

- **目标数据集**：2
- **预期行为**：时间维度不支持时应说明
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"analysis","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[]
- **耗时**：2.58s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### E6：商用事业部和消费者事业部的分公司对比

- **目标数据集**：3
- **预期行为**：跨数据集口径不一致提示
- **状态**：✅ 成功
- **耗时**：2.81s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部和消费者事业部的分公司对比
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "业务部 / 分公司数量", "value": "7"}, {"title": "累计总任务金额", "value": "455000000.0"}, {"title": "累计年度开单金额", "value": "131114522.4527676"}, {"title": "整体达成率", "value": "28.816378561047824"}, {"title": "最高：公共办公业务部", "value": "80.76"}, {"title": "最低：西部分公司", "value": "19.08"}, {"title": "首尾差距", "value": "61.68000000000001"}]
- **章节**：总体判断 / 业务部 / 分公司对比分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 7 个业务部 / 分公司在下方对比表展开。", "首尾差异：公共办公业务部达成率比东部分公司高57.05个百分点", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### E7：哪个分公司最高 5 名

- **目标数据集**：2
- **预期行为**：语义纠错为 top 5
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"ranking","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[],
- **耗时**：2.71s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### E8：商用事业部达成率大于 100% 的代表处

- **目标数据集**：3
- **预期行为**：可能无结果
- **状态**：✅ 成功
- **耗时**：2.61s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率大于100%的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "30000000.0"}, {"title": "年度开单金额", "value": "24226834.3199999"}, {"title": "达成率", "value": "80.76"}, {"title": "剩余任务金额", "value": "5773165.68"}]
- **章节**：总体判断 / 下一层级对比分析
- **答案摘要**：{"matchedCount": 0, "metricLabel": "达成率", "mode": "filter", "operator": ">", "targetLevel": "下一层级", "text": "未命中符合条件的下一层级", "title": "命中结果", "value": 100.0}
- **叙述**：["当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### E9：消费者事业部所有城市分公司的总任务金额

- **目标数据集**：2
- **预期行为**：聚合求和
- **状态**：✅ 成功
- **耗时**：5.04s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部所有城市分公司的总任务金额
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司 / 城市分公司下钻分析
- **图表**：各分公司 / 城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司 / 西安城市公司 / 晋城城市公司 / 烟台城市公司 / 贵阳城市公司 / 太原城市公司 / 赣州城市公司 / 哈尔滨城市公司 / 保定城市公司 / 石家庄城市公司 / 廊坊城市公司 / 河北分公司 / 沈阳城市公司 / 天津城市公司 / 甘青宁城市公司 / 川西城市公司 / 武汉城市公司 / 宝鸡城市公司 / 豫晋分公司 / 南昌城市公司 / 长沙城市公司 / 唐山城市公司 / 遵义城市公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 襄阳城市公司 / 鄂尔多斯城市公司 / 桂南城市公司 / 湖南分公司 / 大连城市公司 / 东莞城市公司 / 济南城市公司 / 大理城市公司 / 驻马店城市公司 / 赣闽分公司 / 绵阳城市公司 / 宜昌城市公司 / 榆林城市公司 / 重庆城市公司 / 川南城市公司 / 长春城市公司 / 鄂皖分公司 / 宜春城市公司 / 大同城市公司 / 深圳城市公司 / 厦门城市公司 / 京津分公司 / 新乡城市公司 / 粤桂琼分公司 / 广州城市公司 / 昆明城市公司 / 成都城市公司 / 黄石城市公司 / 北京城市公司 / 三明城市公司 / 浙东城市公司 / 粤西城市公司 / 邵阳城市公司 / 川藏分公司 / 青岛城市公司 / 桂东城市公司 / 苏中城市公司 / 万州城市公司 / 皖北城市公司 / 皖南城市公司 / 新疆城市公司 / 福州城市公司 / 苏北城市公司 / 江浙沪分公司 / 浙西城市公司 / 苏南城市公司 / 常德城市公司 / 川北城市公司 / 衡阳城市公司 / 上海城市公司 / 淄博城市公司 / 洛阳城市公司 / 乐山城市公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 82 个分公司 / 城市分公司", "第一梯队：郑州城市公司49.95%、临沂城市公司47.37%、曲靖城市公司42.98%、西安城市公司37.64%、晋城城市公司37.30%、烟台城市公司36.24%、贵阳城市公司35.71%、太原城市公司35.62%、赣州城市公司35.06%、哈尔滨城市公司34.68%、保定城市公司34.64%、石家庄城市公司34.50%、廊坊城市公司34.18%、河北分公司33.89%、沈阳城市公司33.88%、天津城市公司33.73%、甘青宁城市公司33.46%、川西城市公司33.13%、武汉城市公司33.05%、宝鸡城市公司32.86%、豫晋分公司32.69%、南昌城市公司32.48%、长沙城市公司32.21%、唐山城市公司32.18%、遵义城市公司32.14%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、襄阳城市公司31.02%、鄂尔多斯城市公司30.79%、桂南城市公司30.66%、湖南分公司30.27%、大连城市公司30.20%、东莞城市公司30.04%、济南城市
- **SQL 样例**：
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
    FROM public.fei
```

### E10：商用事业部前 0 名的分公司

- **目标数据集**：3
- **预期行为**：非法数量处理
- **状态**：✅ 成功
- **耗时**：2.78s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率的分公司
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "63600000.0"}, {"title": "年度开单金额", "value": "15840997.5799999"}, {"title": "达成率", "value": "24.91"}, {"title": "剩余任务金额", "value": "47759002.42"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司 / 南部分公司 / 东部分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "北部分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "东部分公司", "targetLevel": "分公司", "text": "已按达成率输出 3 个分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["北部分公司", "南部分公司", "东部分公司"]}
- **叙述**：["本次结果覆盖 3 个分公司", "第一梯队：北部分公司24.91%", "第二梯队：南部分公司24.69%", "第三梯队：东部分公司23.71%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### E11：电商事业部抖音直营和京东直营对比

- **目标数据集**：62
- **预期行为**：细分业务对比
- **状态**：✅ 成功
- **耗时**：5.21s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部抖音直营和京东直营对比
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','抖音直营','京东直营') AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### E12：消费者事业部粤桂琼分公司和山东分公司业绩对比

- **目标数据集**：2
- **预期行为**：同数据集分公司对比
- **状态**：✅ 成功
- **耗时**：5.31s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部粤桂琼分公司和山东分公司业绩对比
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "分公司数量", "value": "13"}, {"title": "累计总任务金额", "value": "1789710000.0"}, {"title": "累计年度开单金额", "value": "521218325.99"}, {"title": "整体达成率", "value": "29.12306049527577"}, {"title": "最高：河北分公司", "value": "33.89"}, {"title": "最低：江浙沪分公司", "value": "19.03"}, {"title": "首尾差距", "value": "14.86"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 13 个分公司在下方对比表展开。", "首尾差异：河北分公司达成率比京津分公司高5.95个百分点", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### E13：商用事业部东部分公司和南部分公司对比

- **目标数据集**：3
- **预期行为**：同数据集分公司对比
- **状态**：✅ 成功
- **耗时**：2.74s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部东部分公司和南部分公司对比
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "310000000.0"}, {"title": "累计年度开单金额", "value": "71851963.5627677"}, {"title": "整体达成率", "value": "23.17805276218313"}, {"title": "东部分公司达成率", "value": "23.71"}, {"title": "北部分公司达成率", "value": "24.91"}, {"title": "南部分公司达成率", "value": "24.69"}, {"title": "西部分公司达成率", "value": "19.08"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 4 个分公司", "对比对象：东部分公司：开单2253万 / 任务9500万，达成率23.71%，剩余缺口7247万；北部分公司：开单1584万 / 任务6360万，达成率24.91%，剩余缺口4776万；南部分公司：开单2024万 / 任务8200万，达成率24.69%，剩余缺口6176万；西部分公司：开单1324万 / 任务6940万，达成率19.08%，剩余缺口5616万", "首尾差异：北部分公司达成率比西部分公司高5.83个百分点", "第一梯队：北部分公司24.91%、南部分公司24.69%", "第二梯队：东部分公司23.71%", "第三梯队：西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### E14：消费者事业部达成率最高的 10 个城市分公司

- **目标数据集**：2
- **预期行为**：N 大于实际时返回全部
- **状态**：✅ 成功
- **耗时**：5.27s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前10的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司 / 西安城市公司 / 晋城城市公司 / 烟台城市公司 / 贵阳城市公司 / 太原城市公司 / 赣州城市公司 / 哈尔滨城市公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "郑州城市公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "哈尔滨城市公司", "targetLevel": "城市分公司", "text": "已按达成率输出 10 个城市分公司的排序结果", "title": "排名结果", "topN": 10, "topNames": ["郑州城市公司", "临沂城市公司", "曲靖城市公司", "西安城市公司", "晋城城市公司", "烟台城市公司", "贵阳城市公司", "太原城市公司", "赣州城市公司", "哈尔滨城市公司"]}
- **叙述**：["本次结果覆盖 10 个城市分公司", "第一梯队：郑州城市公司49.95%、临沂城市公司47.37%、曲靖城市公司42.98%、西安城市公司37.64%", "第二梯队：晋城城市公司37.30%、烟台城市公司36.24%、贵阳城市公司35.71%", "第三梯队：太原城市公司35.62%、赣州城市公司35.06%、哈尔滨城市公司34.68%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### E15：商用事业部最低的代表处

- **目标数据集**：3
- **预期行为**：单点最低
- **状态**：✅ 成功
- **耗时**：2.54s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率最低的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "8100000.0"}, {"title": "年度开单金额", "value": "892720.72"}, {"title": "达成率", "value": "11.02"}, {"title": "剩余任务金额", "value": "7207279.28"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：甘青宁代表处
- **答案摘要**：{"bottomNames": [], "direction": "asc", "leader": "甘青宁代表处", "metricLabel": "达成率", "mode": "ranking", "rankSides": "bottom", "tail": "", "targetLevel": "代表处", "text": "最低的代表处是 甘青宁代表处", "title": "最低结果", "topN": 1, "topNames": ["甘青宁代表处"]}
- **叙述**：["本次结果覆盖 1 个代表处", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### E16：电商事业部毛利率最低的负责人

- **目标数据集**：62
- **预期行为**：个人层级聚合
- **状态**：✅ 成功
- **耗时**：5.11s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部毛利率最低的负责人
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 总任务达成率 ASC LIMIT 1;
```
- **⚠️ 异常点**：结果为空

### E17：消费者事业部业绩最差的分公司

- **目标数据集**：2
- **预期行为**：最低极值
- **状态**：✅ 成功
- **耗时**：5.76s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率最低的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "117400000.0"}, {"title": "年度开单金额", "value": "22338010.0"}, {"title": "达成率", "value": "19.03"}, {"title": "剩余任务金额", "value": "95061990.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：江浙沪分公司
- **答案摘要**：{"bottomNames": [], "direction": "asc", "leader": "江浙沪分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "bottom", "tail": "", "targetLevel": "分公司", "text": "最低的分公司是 江浙沪分公司", "title": "最低结果", "topN": 1, "topNames": ["江浙沪分公司"]}
- **叙述**：["本次结果覆盖 1 个分公司", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### E18：商用事业部业绩最好的分公司

- **目标数据集**：3
- **预期行为**：最高极值
- **状态**：✅ 成功
- **耗时**：2.86s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率最高的分公司
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "63600000.0"}, {"title": "年度开单金额", "value": "15840997.5799999"}, {"title": "达成率", "value": "24.91"}, {"title": "剩余任务金额", "value": "47759002.42"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "北部分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "", "targetLevel": "分公司", "text": "最高的分公司是 北部分公司", "title": "最高结果", "topN": 1, "topNames": ["北部分公司"]}
- **叙述**：["本次结果覆盖 1 个分公司", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### E19：电商事业部年度开单金额最少的业务

- **目标数据集**：62
- **预期行为**：最低极值
- **状态**：✅ 成功
- **耗时**：5.01s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部年度开单金额最少的业务
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 年度开单金额 ASC LIMIT 3;
```
- **⚠️ 异常点**：结果为空

### E20：消费者事业部所有分公司业绩总和

- **目标数据集**：2
- **预期行为**：聚合
- **状态**：✅ 成功
- **耗时**：5.93s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部所有分公司业绩总和
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### E21：商用事业部所有代表处业绩总和

- **目标数据集**：3
- **预期行为**：聚合
- **状态**：✅ 成功
- **耗时**：2.8s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部所有代表处业绩总和
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 代表处下钻分析
- **图表**：各代表处达成率排序
- **折叠面板**：山东代表处 / 湖南代表处 / 粤东代表处 / 津冀代表处 / 黑龙江代表处 / 北京代表处 / 四川代表处 / 新西代表处 / 浙江代表处 / 上海代表处 / 江苏代表处 / 辽宁代表处 / 粤西广西代表处 / 湖北代表处 / 江西代表处 / 陕西代表处 / 云贵代表处 / 晋蒙（蒙西）代表处 / 安徽代表处 / 福建代表处 / 吉林代表处 / 河南代表处 / 重庆代表处 / 餐饮 / 甘青宁代表处
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 25 个代表处", "第一梯队：山东代表处37.63%、湖南代表处34.55%、粤东代表处28.90%、津冀代表处28.86%、黑龙江代表处28.73%、北京代表处26.32%、四川代表处25.98%、新西代表处25.01%、浙江代表处24.09%", "第二梯队：上海代表处24.04%、江苏代表处23.77%、辽宁代表处23.18%、粤西广西代表处22.19%、湖北代表处20.92%、江西代表处20.35%、陕西代表处18.50%、云贵代表处17.84%", "第三梯队：晋蒙（蒙西）代表处17.15%、安徽代表处16.96%、福建代表处15.01%、吉林代表处14.69%、河南代表处13.07%、重庆代表处12.96%、餐饮12.83%、甘青宁代表处11.02%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### E22：电商事业部所有细分业务年度目标营收总和

- **目标数据集**：62
- **预期行为**：聚合
- **状态**：✅ 成功
- **耗时**：5.29s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部所有细分业务年度目标营收总和
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### E23：消费者事业部业绩前十

- **目标数据集**：2
- **预期行为**：语义为 top 10
- **状态**：✅ 成功
- **耗时**：5.38s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前10的消费者事业部
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "河北分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "京津分公司", "targetLevel": "分公司", "text": "已按达成率输出 10 个分公司的排序结果", "title": "排名结果", "topN": 10, "topNames": ["河北分公司", "豫晋分公司", "黑吉辽分公司", "山东分公司", "西北分公司", "云贵渝分公司", "湖南分公司", "赣闽分公司", "鄂皖分公司", "京津分公司"]}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### E24：商用事业部后十名代表处

- **目标数据集**：3
- **预期行为**：语义为 bottom 10
- **状态**：✅ 成功
- **耗时**：2.66s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名后10的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "8100000.0"}, {"title": "年度开单金额", "value": "892720.72"}, {"title": "达成率", "value": "11.02"}, {"title": "剩余任务金额", "value": "7207279.28"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：甘青宁代表处 / 餐饮 / 重庆代表处 / 河南代表处 / 吉林代表处 / 福建代表处 / 安徽代表处 / 晋蒙（蒙西）代表处 / 云贵代表处 / 陕西代表处
- **答案摘要**：{"bottomNames": [], "direction": "asc", "leader": "甘青宁代表处", "metricLabel": "达成率", "mode": "ranking", "rankSides": "bottom", "tail": "陕西代表处", "targetLevel": "代表处", "text": "已按达成率输出 10 个代表处的排序结果", "title": "排名结果", "topN": 10, "topNames": ["甘青宁代表处", "餐饮", "重庆代表处", "河南代表处", "吉林代表处", "福建代表处", "安徽代表处", "晋蒙（蒙西）代表处", "云贵代表处", "陕西代表处"]}
- **叙述**：["本次结果覆盖 10 个代表处", "第一梯队：陕西代表处18.50%、云贵代表处17.84%、晋蒙（蒙西）代表处17.15%、安徽代表处16.96%", "第二梯队：福建代表处15.01%、吉林代表处14.69%、河南代表处13.07%", "第三梯队：重庆代表处12.96%、餐饮12.83%、甘青宁代表处11.02%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### E25：电商事业部达播业绩

- **目标数据集**：62
- **预期行为**：细分业务
- **状态**：✅ 成功
- **耗时**：5.23s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部达播业绩
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','达播') AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### C1：消费者事业部业绩怎么样

- **目标数据集**：2
- **预期行为**：标题/摘要应围绕“消费者事业部整体达成率”
- **状态**：✅ 成功
- **耗时**：7.43s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部业绩怎么样
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "178971.0"}, {"title": "年度开单金额", "value": "59346.18"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "119624.82"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
```sql
WITH 源数据 AS (
  SELECT
    fields,
    COALESCE(NULLIF(regexp_replace(fields ->> '总任务（金额）', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 总任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 年度开单原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '线下', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 线下任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '线下-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 线下实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '新零售', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 新零售任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '新零售-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 新零售实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '燃气定制', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 燃气定制任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '燃气定制-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 燃气定制实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '地产', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 地产任务原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '地产-年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 地产实际原值,
    COALESCE(NULLIF(regexp_replace(fields ->> '总任务达成率', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 达成率原值
  FROM public.feishu_tbl_xioafeizhe
),
标准结果 AS (
  SELECT
    '消费者事业部' AS 条线,
    CASE
      WHEN NULLIF(fields ->> '分公司', '') IS NULL THEN '消费者事业部总体'
      WHEN NULLIF(fields ->> '城市分公司', '') IS NULL THEN '分公司'
      ELSE '城市分公司'
    END AS 层级,
    CASE
      WHEN NULLI
```

### C2：商用事业部整体达成率是多少

- **目标数据集**：3
- **预期行为**：核心结论应给出具体数值，KPI 卡标题贴合问题
- **状态**：✅ 成功
- **耗时**：5.33s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部整体达成率是多少
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
    AND 分公司 LIKE '%业务部' THEN '业务部' WHEN 业务部 <> '' THEN '业务部' WHEN 分公司 <> '' THEN '分公司' ELSE '事业部' EN
```

### C3：前 3 的分公司

- **目标数据集**：2
- **预期行为**：排名结果卡标题应为“前 3 名分公司”或类似
- **状态**：❌ 异常 - {"diagnostics":{"advanced":{"answer_contract":{"evidence":{},"mode":"analysis","ok":true,"suggestions":[],"warning_count":0,"warnings":[]},"asset_count":0,"assets":[],"conclusion_advice":{"bullets":[]
- **耗时**：2.6s
- **路由决策**：-
- **意图**：-
- **是否需要确认**：-
- **命中数据集**：-
- **显示标题**：-
- **报告标题**：-
- **⚠️ 异常点**：执行异常

### C4：哪些城市分公司达成率低于 10%

- **目标数据集**：2
- **预期行为**：筛选结果卡应说明条件，条形图颜色语义一致
- **状态**：✅ 成功
- **耗时**：5.21s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率小于10%的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "25180000.0"}, {"title": "年度开单金额", "value": "0"}, {"title": "达成率", "value": "0.00%"}, {"title": "剩余任务金额", "value": "25180000.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：洛阳城市公司 / 乐山城市公司 / 淄博城市公司 / 上海城市公司
- **答案摘要**：{"matchedCount": 4, "metricLabel": "达成率", "mode": "filter", "operator": "<", "targetLevel": "城市分公司", "text": "命中 4 个城市分公司", "title": "命中结果", "value": 10.0}
- **叙述**：["本次结果覆盖 4 个城市分公司", "第一梯队：上海城市公司6.68%、淄博城市公司3.26%", "第二梯队：洛阳城市公司0.00%", "第三梯队：乐山城市公司0.00%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### C5：商用事业部四大分公司业绩整体盘点

- **目标数据集**：3
- **预期行为**：对比分析卡应列出四大分公司
- **状态**：✅ 成功
- **耗时**：2.62s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部四大分公司业绩整体盘点
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "310000000.0"}, {"title": "累计年度开单金额", "value": "71851963.5627677"}, {"title": "整体达成率", "value": "23.17805276218313"}, {"title": "东部分公司达成率", "value": "23.71"}, {"title": "北部分公司达成率", "value": "24.91"}, {"title": "南部分公司达成率", "value": "24.69"}, {"title": "西部分公司达成率", "value": "19.08"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 4 个分公司", "对比对象：东部分公司：开单2253万 / 任务9500万，达成率23.71%，剩余缺口7247万；北部分公司：开单1584万 / 任务6360万，达成率24.91%，剩余缺口4776万；南部分公司：开单2024万 / 任务8200万，达成率24.69%，剩余缺口6176万；西部分公司：开单1324万 / 任务6940万，达成率19.08%，剩余缺口5616万", "首尾差异：北部分公司达成率比西部分公司高5.83个百分点", "第一梯队：北部分公司24.91%、南部分公司24.69%", "第二梯队：东部分公司23.71%", "第三梯队：西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### C6：电商事业部国内业务部和直营零售部对比

- **目标数据集**：62
- **预期行为**：对比卡应显示两个业务部，结论针对对比对象
- **状态**：✅ 成功
- **耗时**：5.17s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部国内业务部和直营零售部对比
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','国内业务部','直营零售部') AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### C7：消费者事业部哪个分公司完成率最高

- **目标数据集**：2
- **预期行为**：最高结果卡应突出答案分公司
- **状态**：✅ 成功
- **耗时**：5.07s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率最高的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "110990000.0"}, {"title": "年度开单金额", "value": "37618017.0"}, {"title": "达成率", "value": "33.89"}, {"title": "剩余任务金额", "value": "73371983.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "河北分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "", "targetLevel": "分公司", "text": "最高的分公司是 河北分公司", "title": "最高结果", "topN": 1, "topNames": ["河北分公司"]}
- **叙述**：["本次结果覆盖 1 个分公司", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### C8：商用事业部后 3 名的代表处

- **目标数据集**：3
- **预期行为**：排名卡不应出现“领先”等正向标签
- **状态**：✅ 成功
- **耗时**：2.73s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名后3的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "8100000.0"}, {"title": "年度开单金额", "value": "892720.72"}, {"title": "达成率", "value": "11.02"}, {"title": "剩余任务金额", "value": "7207279.28"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：甘青宁代表处 / 餐饮 / 重庆代表处
- **答案摘要**：{"bottomNames": [], "direction": "asc", "leader": "甘青宁代表处", "metricLabel": "达成率", "mode": "ranking", "rankSides": "bottom", "tail": "重庆代表处", "targetLevel": "代表处", "text": "已按达成率输出 3 个代表处的排序结果", "title": "排名结果", "topN": 3, "topNames": ["甘青宁代表处", "餐饮", "重庆代表处"]}
- **叙述**：["本次结果覆盖 3 个代表处", "第一梯队：重庆代表处12.96%", "第二梯队：餐饮12.83%", "第三梯队：甘青宁代表处11.02%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### C9：消费者事业部缺口最大的分公司

- **目标数据集**：2
- **预期行为**：结论方向应为“缺口/承压”
- **状态**：✅ 成功
- **耗时**：4.97s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部剩余任务金额排名前3的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "219040000.0"}, {"title": "年度开单金额", "value": "62561778.0"}, {"title": "达成率", "value": "28.56"}, {"title": "剩余任务金额", "value": "156478222.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司剩余任务金额排序
- **折叠面板**：鄂皖分公司 / 粤桂琼分公司 / 豫晋分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "鄂皖分公司", "metricLabel": "剩余任务金额", "mode": "ranking", "rankSides": "top", "tail": "豫晋分公司", "targetLevel": "分公司", "text": "已按剩余任务金额输出 3 个分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["鄂皖分公司", "粤桂琼分公司", "豫晋分公司"]}
- **叙述**：["本次结果覆盖 3 个分公司", "第一梯队：豫晋分公司32.69%", "第二梯队：鄂皖分公司28.56%", "第三梯队：粤桂琼分公司27.25%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### C10：商用事业部东部分公司业绩

- **目标数据集**：3
- **预期行为**：下钻卡片标题应包含“东部分公司”
- **状态**：✅ 成功
- **耗时**：5.01s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部东部分公司业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "95000000.0"}, {"title": "年度开单金额", "value": "22526100.19"}, {"title": "达成率", "value": "23.71"}, {"title": "剩余任务金额", "value": "72473899.81"}]
- **章节**：总体判断 / 代表处下钻分析
- **图表**：各代表处达成率排序
- **折叠面板**：山东代表处 / 浙江代表处 / 上海代表处 / 江苏代表处 / 湖北代表处 / 安徽代表处 / 河南代表处
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个代表处", "第一梯队：山东代表处37.63%、浙江代表处24.09%、上海代表处24.04%", "第二梯队：江苏代表处23.77%、湖北代表处20.92%", "第三梯队：安徽代表处16.96%、河南代表处13.07%"]
- **SQL 样例**：
```sql
WITH RECURSIVE 汇总结果 AS (
WITH 字段提取 AS (
    SELECT
        CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END AS 分公司,
        CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END AS 代表处,
        CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END AS 业务代表,
        CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END AS 任务原始,
        CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END AS 开单原始,
        CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END AS 当前年
    FROM angel_group_data
),
基础数据 AS (
    SELECT
        分公司, 代表处, 业务代表,
        COALESCE(NULLIF(regexp_replace(任务原始, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 任务金额,
        COALESCE(NULLIF(regexp_replace(开单原始, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 开单金额,
        CASE WHEN 分公司 LIKE '%分公司' THEN '区域条线' WHEN 分公司 LIKE '%业务部' THEN '行业条线' ELSE '事业部层级' END AS 条线类型
    FROM 字段提取
    WHERE COALESCE(NULLIF(当前年, ''), '2026') = '2026'
),
维度汇总 AS (
    SELECT '区域条线' AS 条线, 分公司 AS 上级名称, 代表处 AS 节点名称, '代表处' AS 层级, 任务金额, 开单金额
    FROM 基础数据 WHERE 条线类型='区域条线' AND 代表处<>'' AND (业务代表 IS NULL OR 业务代表='')
    UNION ALL
    SELECT '区域条线','商用事业部',分公司,'分公司',任务金额,开单金额
    FROM 基础数据 WHERE 条线类型='区域条线' AND (代表处 IS NULL OR 
```

### C11：消费者事业部总任务金额

- **目标数据集**：2
- **预期行为**：KPI 卡标题应含“总任务金额”
- **状态**：✅ 成功
- **耗时**：5.42s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部总任务金额
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### C12：商用事业部年度开单金额

- **目标数据集**：3
- **预期行为**：KPI 卡标题应含“年度开单金额”
- **状态**：✅ 成功
- **耗时**：2.59s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部年度开单金额
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 业务部 / 分公司下钻分析
- **图表**：各业务部 / 分公司达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部 / 北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 7 个业务部 / 分公司", "第一梯队：公共办公业务部80.76%、工业医疗业务部63.68%、餐饮业务部27.30%", "第二梯队：北部分公司24.91%、南部分公司24.69%", "第三梯队：东部分公司23.71%、西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### C13：电商事业部年度目标营收

- **目标数据集**：62
- **预期行为**：KPI 卡标题应含“年度目标营收”
- **状态**：✅ 成功
- **耗时**：5.24s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部年度目标营收
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### C14：消费者事业部前 5 的城市分公司

- **目标数据集**：2
- **预期行为**：标题应含“城市分公司”
- **状态**：✅ 成功
- **耗时**：4.97s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前5的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司 / 西安城市公司 / 晋城城市公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "郑州城市公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "晋城城市公司", "targetLevel": "城市分公司", "text": "已按达成率输出 5 个城市分公司的排序结果", "title": "排名结果", "topN": 5, "topNames": ["郑州城市公司", "临沂城市公司", "曲靖城市公司", "西安城市公司", "晋城城市公司"]}
- **叙述**：["本次结果覆盖 5 个城市分公司", "第一梯队：郑州城市公司49.95%、临沂城市公司47.37%", "第二梯队：曲靖城市公司42.98%、西安城市公司37.64%", "第三梯队：晋城城市公司37.30%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### C15：商用事业部达成率低于 50% 的代表处

- **目标数据集**：3
- **预期行为**：筛选卡标题应含条件与层级
- **状态**：✅ 成功
- **耗时**：2.47s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率小于50%的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "69400000.0"}, {"title": "年度开单金额", "value": "13240968.1199999"}, {"title": "达成率", "value": "19.08"}, {"title": "剩余任务金额", "value": "56159031.88"}]
- **章节**：总体判断 / 下一层级对比分析
- **答案摘要**：{"matchedCount": 0, "metricLabel": "达成率", "mode": "filter", "operator": "<", "targetLevel": "下一层级", "text": "未命中符合条件的下一层级", "title": "命中结果", "value": 50.0}
- **叙述**：["当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### C16：电商事业部毛利率最高的 3 个业务

- **目标数据集**：62
- **预期行为**：排名卡标题应含“毛利率”
- **状态**：✅ 成功
- **耗时**：4.96s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部毛利率最高的 3 个业务
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '事业部' ORDER BY 总任务达成率 DESC LIMIT 3;
```
- **⚠️ 异常点**：结果为空

### C17：消费者事业部山东分公司业绩

- **目标数据集**：2
- **预期行为**：标题应含“山东分公司”
- **状态**：✅ 成功
- **耗时**：5.4s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部山东分公司业绩
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "分公司数量", "value": "13"}, {"title": "累计总任务金额", "value": "1789710000.0"}, {"title": "累计年度开单金额", "value": "521218325.99"}, {"title": "整体达成率", "value": "29.12306049527577"}, {"title": "最高：河北分公司", "value": "33.89"}, {"title": "最低：江浙沪分公司", "value": "19.03"}, {"title": "首尾差距", "value": "14.86"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 13 个分公司在下方对比表展开。", "首尾差异：河北分公司达成率比京津分公司高5.95个百分点", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### C18：商用事业部餐饮业务部业绩

- **目标数据集**：3
- **预期行为**：标题应含“餐饮业务部”
- **状态**：✅ 成功
- **耗时**：2.76s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部餐饮业务部业绩
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "145000000.0"}, {"title": "累计年度开单金额", "value": "59262558.8899999"}, {"title": "整体达成率", "value": "40.870730268965445"}, {"title": "公共办公业务部达成率", "value": "80.76"}, {"title": "工业医疗业务部达成率", "value": "63.68"}, {"title": "餐饮业务部达成率", "value": "27.3"}]
- **章节**：总体判断 / 业务部下钻分析
- **图表**：各业务部达成率排序
- **折叠面板**：公共办公业务部 / 工业医疗业务部 / 餐饮业务部
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 3 个业务部", "对比对象：公共办公业务部：开单2423万 / 任务3000万，达成率80.76%，剩余缺口577万；工业医疗业务部：开单637万 / 任务1000万，达成率63.68%，剩余缺口363万；餐饮业务部：开单2867万 / 任务1.05亿，达成率27.30%，剩余缺口7633万", "首尾差异：公共办公业务部达成率比餐饮业务部高53.46个百分点", "第一梯队：公共办公业务部80.76%", "第二梯队：工业医疗业务部63.68%", "第三梯队：餐饮业务部27.30%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### C19：电商事业部跨境业务部业绩

- **目标数据集**：62
- **预期行为**：标题应含“跨境业务部”
- **状态**：✅ 成功
- **耗时**：5.09s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部跨境业务部业绩
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','跨境业务部') AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### C20：消费者事业部粤桂琼与山东分公司对比

- **目标数据集**：2
- **预期行为**：对比结论应提及两个分公司
- **状态**：✅ 成功
- **耗时**：5.15s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部粤桂琼与山东分公司对比
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "分公司数量", "value": "13"}, {"title": "累计总任务金额", "value": "1789710000.0"}, {"title": "累计年度开单金额", "value": "521218325.99"}, {"title": "整体达成率", "value": "29.12306049527577"}, {"title": "最高：河北分公司", "value": "33.89"}, {"title": "最低：江浙沪分公司", "value": "19.03"}, {"title": "首尾差距", "value": "14.86"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 13 个分公司在下方对比表展开。", "首尾差异：河北分公司达成率比京津分公司高5.95个百分点", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### C21：商用事业部南北分公司对比

- **目标数据集**：3
- **预期行为**：对比结论应提及具体分公司
- **状态**：✅ 成功
- **耗时**：2.68s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部南北分公司对比
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "累计总任务金额", "value": "310000000.0"}, {"title": "累计年度开单金额", "value": "71851963.5627677"}, {"title": "整体达成率", "value": "23.17805276218313"}, {"title": "东部分公司达成率", "value": "23.71"}, {"title": "北部分公司达成率", "value": "24.91"}, {"title": "南部分公司达成率", "value": "24.69"}, {"title": "西部分公司达成率", "value": "19.08"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司 / 南部分公司 / 东部分公司 / 西部分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 4 个分公司", "对比对象：东部分公司：开单2253万 / 任务9500万，达成率23.71%，剩余缺口7247万；北部分公司：开单1584万 / 任务6360万，达成率24.91%，剩余缺口4776万；南部分公司：开单2024万 / 任务8200万，达成率24.69%，剩余缺口6176万；西部分公司：开单1324万 / 任务6940万，达成率19.08%，剩余缺口5616万", "首尾差异：北部分公司达成率比西部分公司高5.83个百分点", "第一梯队：北部分公司24.91%、南部分公司24.69%", "第二梯队：东部分公司23.71%", "第三梯队：西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### C22：电商事业部净水业务和饮水业务对比

- **目标数据集**：62
- **预期行为**：对比结论应提及两个细分业务
- **状态**：✅ 成功
- **耗时**：5.14s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部净水业务和饮水业务对比
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','净水业务','饮水业务') AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### C23：消费者事业部达成率分布

- **目标数据集**：2
- **预期行为**：总览/对比卡
- **状态**：✅ 成功
- **耗时**：5.18s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率分布
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司达成率排序
- **折叠面板**：河北分公司 / 豫晋分公司 / 黑吉辽分公司 / 山东分公司 / 西北分公司 / 云贵渝分公司 / 湖南分公司 / 赣闽分公司 / 鄂皖分公司 / 京津分公司 / 粤桂琼分公司 / 川藏分公司 / 江浙沪分公司
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### C24：商用事业部各代表处达成率分布

- **目标数据集**：3
- **预期行为**：总览/对比卡
- **状态**：✅ 成功
- **耗时**：2.48s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部各代表处达成率分布
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "455000000.0"}, {"title": "年度开单金额", "value": "126286318.012767"}, {"title": "达成率", "value": "27.76"}, {"title": "剩余任务金额", "value": "328713681.99"}]
- **章节**：总体判断 / 代表处下钻分析
- **图表**：各代表处达成率排序
- **折叠面板**：山东代表处 / 湖南代表处 / 粤东代表处 / 津冀代表处 / 黑龙江代表处 / 北京代表处 / 四川代表处 / 新西代表处 / 浙江代表处 / 上海代表处 / 江苏代表处 / 辽宁代表处 / 粤西广西代表处 / 湖北代表处 / 江西代表处 / 陕西代表处 / 云贵代表处 / 晋蒙（蒙西）代表处 / 安徽代表处 / 福建代表处 / 吉林代表处 / 河南代表处 / 重庆代表处 / 餐饮 / 甘青宁代表处
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 25 个代表处", "第一梯队：山东代表处37.63%、湖南代表处34.55%、粤东代表处28.90%、津冀代表处28.86%、黑龙江代表处28.73%、北京代表处26.32%、四川代表处25.98%、新西代表处25.01%、浙江代表处24.09%", "第二梯队：上海代表处24.04%、江苏代表处23.77%、辽宁代表处23.18%、粤西广西代表处22.19%、湖北代表处20.92%、江西代表处20.35%、陕西代表处18.50%、云贵代表处17.84%", "第三梯队：晋蒙（蒙西）代表处17.15%、安徽代表处16.96%、福建代表处15.01%、吉林代表处14.69%、河南代表处13.07%、重庆代表处12.96%、餐饮12.83%、甘青宁代表处11.02%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN C
```

### C25：电商事业部各业务部预算完成情况

- **目标数据集**：62
- **预期行为**：总览/对比卡
- **状态**：✅ 成功
- **耗时**：5.35s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部各业务部预算完成情况
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 组织路径 LIKE '电商事业部%' ORDER BY 层级级别, 年度开单金额 DESC LIMIT 200;
```
- **⚠️ 异常点**：结果为空

### X1：消费者事业部达成率最高和最低的分公司分别是哪个

- **目标数据集**：2
- **预期行为**：同时返回最高和最低
- **状态**：✅ 成功
- **耗时**：5.0s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率最高和最低的分公司分别是哪个
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "110990000.0"}, {"title": "年度开单金额", "value": "37618017.0"}, {"title": "达成率", "value": "33.89"}, {"title": "剩余任务金额", "value": "73371983.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：江浙沪分公司 / 川藏分公司 / 粤桂琼分公司 / 黑吉辽分公司 / 豫晋分公司 / 河北分公司
- **答案摘要**：{"bottomNames": [], "direction": "asc", "leader": "江浙沪分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "", "tail": "河北分公司", "targetLevel": "分公司", "text": "已按达成率输出 6 个分公司的排序结果", "title": "排名结果", "topN": 6, "topNames": ["江浙沪分公司", "川藏分公司", "粤桂琼分公司", "黑吉辽分公司", "豫晋分公司", "河北分公司"]}
- **叙述**：["本次结果覆盖 6 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%", "第二梯队：黑吉辽分公司31.55%、粤桂琼分公司27.25%", "第三梯队：川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### X2：商用事业部四大分公司中达成率最高和最低的分别是

- **目标数据集**：3
- **预期行为**：集合内极值
- **状态**：✅ 成功
- **耗时**：2.7s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名前10的分公司
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "63600000.0"}, {"title": "年度开单金额", "value": "15840997.5799999"}, {"title": "达成率", "value": "24.91"}, {"title": "剩余任务金额", "value": "47759002.42"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：北部分公司 / 西部分公司
- **答案摘要**：{"bottomNames": ["西部分公司", "北部分公司"], "direction": "desc", "leader": "北部分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "both", "tail": "西部分公司", "targetLevel": "分公司", "text": "已按达成率输出前2和后2个分公司的排序结果", "title": "排名结果", "topN": 2, "topNames": ["北部分公司", "西部分公司"]}
- **叙述**：["本次结果覆盖 2 个分公司", "领先主体：北部分公司24.91%", "承压主体：西部分公司19.08%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### X3：电商事业部国内业务部年度开单金额和毛利率是多少

- **目标数据集**：62
- **预期行为**：双指标
- **状态**：✅ 成功
- **耗时**：4.95s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部国内业务部年度开单金额和毛利率是多少
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','国内业务部') AND 层级级别 = '业务部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### X4：消费者事业部前 3 分公司和倒数前 3 分公司对比

- **目标数据集**：2
- **预期行为**：双向排名对比
- **状态**：✅ 成功
- **耗时**：5.01s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部前 3 分公司和倒数前 3 分公司对比
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "110990000.0"}, {"title": "年度开单金额", "value": "37618017.0"}, {"title": "达成率", "value": "33.89"}, {"title": "剩余任务金额", "value": "73371983.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：江浙沪分公司 / 川藏分公司 / 粤桂琼分公司 / 黑吉辽分公司 / 豫晋分公司 / 河北分公司
- **答案摘要**：{"bottomNames": [], "direction": "asc", "leader": "江浙沪分公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "", "tail": "河北分公司", "targetLevel": "分公司", "text": "已按达成率输出 6 个分公司的排序结果", "title": "排名结果", "topN": 6, "topNames": ["江浙沪分公司", "川藏分公司", "粤桂琼分公司", "黑吉辽分公司", "豫晋分公司", "河北分公司"]}
- **叙述**：["本次结果覆盖 6 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%", "第二梯队：黑吉辽分公司31.55%、粤桂琼分公司27.25%", "第三梯队：川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```

### X5：商用事业部东部分公司和南部分公司代表处业绩对比

- **目标数据集**：3
- **预期行为**：跨分公司下钻对比
- **状态**：✅ 成功
- **耗时**：2.63s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部东部分公司和南部分公司代表处业绩对比
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "分公司 / 代表处数量", "value": "17"}, {"title": "累计总任务金额", "value": "487000000.0"}, {"title": "累计年度开单金额", "value": "113862350.70553568"}, {"title": "整体达成率", "value": "23.38035948778967"}, {"title": "最高：山东代表处", "value": "37.63"}, {"title": "最低：餐饮", "value": "12.83"}, {"title": "首尾差距", "value": "24.800000000000004"}]
- **章节**：总体判断 / 分公司 / 代表处下钻分析
- **图表**：各分公司 / 代表处达成率排序
- **折叠面板**：山东代表处 / 湖南代表处 / 粤东代表处 / 北部分公司 / 南部分公司 / 浙江代表处 / 上海代表处 / 江苏代表处 / 东部分公司 / 粤西广西代表处 / 湖北代表处 / 江西代表处 / 西部分公司 / 安徽代表处 / 福建代表处 / 河南代表处 / 餐饮
- **答案摘要**：{}
- **叙述**：["本次结果覆盖 17 个分公司 / 代表处", "对比对象较多，关键指标区聚焦整体、最高和最低，完整 17 个分公司 / 代表处在下方对比表展开。", "首尾差异：山东代表处达成率比西部分公司高18.55个百分点", "第一梯队：山东代表处37.63%、湖南代表处34.55%、粤东代表处28.90%、北部分公司24.91%、南部分公司24.69%、浙江代表处24.09%", "第二梯队：上海代表处24.04%、江苏代表处23.77%、东部分公司23.71%、粤西广西代表处22.19%、湖北代表处20.92%、江西代表处20.35%", "第三梯队：西部分公司19.08%、安徽代表处16.96%、福建代表处15.01%、河南代表处13.07%、餐饮12.83%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### X6：电商事业部京东直营、天猫直营、抖音直营业绩排名

- **目标数据集**：62
- **预期行为**：多对象排名
- **状态**：✅ 成功
- **耗时**：5.39s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部京东直营、天猫直营、抖音直营业绩排名
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ('电商事业部','京东直营','天猫直营','抖音直营') AND 层级级别 = '事业部' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### X7：消费者事业部哪些分公司达成率低于 50% 且缺口超过 1000 万

- **目标数据集**：2
- **预期行为**：多条件筛选
- **状态**：✅ 成功
- **耗时**：5.06s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率小于50%的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "117400000.0"}, {"title": "年度开单金额", "value": "22338010.0"}, {"title": "达成率", "value": "19.03"}, {"title": "剩余任务金额", "value": "95061990.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：江浙沪分公司 / 川藏分公司 / 粤桂琼分公司 / 京津分公司 / 鄂皖分公司 / 赣闽分公司 / 湖南分公司 / 云贵渝分公司 / 西北分公司 / 山东分公司 / 黑吉辽分公司 / 豫晋分公司 / 河北分公司
- **答案摘要**：{"matchedCount": 13, "metricLabel": "达成率", "mode": "filter", "operator": "<", "targetLevel": "分公司", "text": "命中 13 个分公司", "title": "命中结果", "value": 50.0}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### X8：商用事业部达成率高于 80% 且开单金额超过 5000 万的代表处

- **目标数据集**：3
- **预期行为**：多条件筛选
- **状态**：✅ 成功
- **耗时**：2.7s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率大于80%的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "30000000.0"}, {"title": "年度开单金额", "value": "24226834.3199999"}, {"title": "达成率", "value": "80.76"}, {"title": "剩余任务金额", "value": "5773165.68"}]
- **章节**：总体判断 / 下一层级对比分析
- **答案摘要**：{"matchedCount": 0, "metricLabel": "达成率", "mode": "filter", "operator": ">", "targetLevel": "下一层级", "text": "未命中符合条件的下一层级", "title": "命中结果", "value": 80.0}
- **叙述**：["当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### X9：电商事业部直营零售部中毛利率为正且年度开单金额前 5 的细分业务

- **目标数据集**：62
- **预期行为**：复合筛选+排名
- **状态**：✅ 成功
- **耗时**：5.13s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部直营零售部中毛利率为正且年度开单金额前 5 的细分业务
- **报告标题**：
- **SQL 样例**：
```sql
SELECT '电商业务' AS 条线,
                '业务承接角色' AS 层级,
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 细分业务 IN ('电商事业部','直营零售部') AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### X10：消费者事业部业绩排名第 5 的城市分公司

- **目标数据集**：2
- **预期行为**：指定名次
- **状态**：✅ 成功
- **耗时**：4.83s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率排名前5的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司 / 西安城市公司 / 晋城城市公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "郑州城市公司", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "晋城城市公司", "targetLevel": "城市分公司", "text": "已按达成率输出 5 个城市分公司的排序结果", "title": "排名结果", "topN": 5, "topNames": ["郑州城市公司", "临沂城市公司", "曲靖城市公司", "西安城市公司", "晋城城市公司"]}
- **叙述**：["本次结果覆盖 5 个城市分公司", "第一梯队：郑州城市公司49.95%、临沂城市公司47.37%", "第二梯队：曲靖城市公司42.98%、西安城市公司37.64%", "第三梯队：晋城城市公司37.30%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### X11：商用事业部达成率排名第 3 的代表处

- **目标数据集**：3
- **预期行为**：指定名次
- **状态**：✅ 成功
- **耗时**：2.64s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名前3的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "12200000.0"}, {"title": "年度开单金额", "value": "4590966.97999999"}, {"title": "达成率", "value": "37.63"}, {"title": "剩余任务金额", "value": "7609033.02"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：山东代表处 / 湖南代表处 / 粤东代表处
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "山东代表处", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "粤东代表处", "targetLevel": "代表处", "text": "已按达成率输出 3 个代表处的排序结果", "title": "排名结果", "topN": 3, "topNames": ["山东代表处", "湖南代表处", "粤东代表处"]}
- **叙述**：["本次结果覆盖 3 个代表处", "第一梯队：山东代表处37.63%", "第二梯队：湖南代表处34.55%", "第三梯队：粤东代表处28.90%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### X12：电商事业部年度开单金额排名第 10 的细分业务

- **目标数据集**：62
- **预期行为**：指定名次
- **状态**：✅ 成功
- **耗时**：5.15s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部年度开单金额排名第 10 的细分业务
- **报告标题**：
- **SQL 样例**：
```sql
SELECT '电商业务' AS 条线,
                '业务承接角色' AS 层级,
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 10;
```
- **⚠️ 异常点**：结果为空

### X13：消费者事业部粤桂琼分公司下属达成率最高的城市分公司

- **目标数据集**：2
- **预期行为**：分组极值
- **状态**：✅ 成功
- **耗时**：5.52s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部粤桂琼分公司下属达成率最高的城市分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "55650000.0"}, {"title": "年度开单金额", "value": "27795355.0"}, {"title": "达成率", "value": "49.95"}, {"title": "剩余任务金额", "value": "27854645.0"}]
- **章节**：总体判断 / 城市分公司对比分析
- **图表**：各城市分公司达成率排序
- **折叠面板**：郑州城市公司 / 临沂城市公司 / 曲靖城市公司
- **答案摘要**：{"childCount": 3, "focusNode": "", "mode": "drilldown", "targetLevel": "城市分公司", "text": "当前展示 3 个城市分公司下级节点", "title": "下钻结果"}
- **叙述**：["本次结果覆盖 3 个城市分公司", "第一梯队：郑州城市公司49.95%", "第二梯队：临沂城市公司47.37%", "第三梯队：曲靖城市公司42.98%"]
- **SQL 样例**：
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
    FROM public.fei
```

### X14：商用事业部东部分公司下属开单金额最高的代表处

- **目标数据集**：3
- **预期行为**：分组极值
- **状态**：✅ 成功
- **耗时**：2.67s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部东部分公司下属开单金额最高的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "28500000.0"}, {"title": "年度开单金额", "value": "8236409.04"}, {"title": "达成率", "value": "28.9"}, {"title": "剩余任务金额", "value": "20263590.96"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：粤东代表处
- **答案摘要**：{"childCount": 1, "focusNode": "粤东代表处", "mode": "drilldown", "targetLevel": "代表处", "text": "已定位到 粤东代表处，当前展示其下一级 1 个代表处", "title": "下钻结果"}
- **叙述**：["本次结果覆盖 1 个代表处", "当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```

### X15：电商事业部国内业务部下属毛利率最低的承接人

- **目标数据集**：62
- **预期行为**：分组极值
- **状态**：✅ 成功
- **耗时**：4.95s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部国内业务部下属毛利率最低的承接人
- **报告标题**：
- **SQL 样例**：
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 负责人 IN ('电商事业部','国内业务部') AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 50;
```
- **⚠️ 异常点**：结果为空

### X16：消费者事业部业绩排名，按年度开单金额排

- **目标数据集**：2
- **预期行为**：明确排序指标
- **状态**：✅ 成功
- **耗时**：5.33s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部开单金额排名前3的消费者事业部
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "1789710000.0"}, {"title": "年度开单金额", "value": "593461787.79"}, {"title": "达成率", "value": "33.16"}, {"title": "剩余任务金额", "value": "1196248212.21"}]
- **章节**：总体判断 / 分公司下钻分析
- **图表**：各分公司年度开单金额排序
- **折叠面板**：豫晋分公司 / 鄂皖分公司 / 粤桂琼分公司 / 赣闽分公司 / 湖南分公司 / 西北分公司 / 云贵渝分公司 / 河北分公司 / 山东分公司 / 川藏分公司 / 黑吉辽分公司 / 江浙沪分公司 / 京津分公司
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "豫晋分公司", "metricLabel": "年度开单金额", "mode": "ranking", "rankSides": "top", "tail": "粤桂琼分公司", "targetLevel": "分公司", "text": "已按年度开单金额输出 3 个分公司的排序结果", "title": "排名结果", "topN": 3, "topNames": ["豫晋分公司", "鄂皖分公司", "粤桂琼分公司"]}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### X17：商用事业部代表处排名，按达成率排

- **目标数据集**：3
- **预期行为**：明确排序指标
- **状态**：✅ 成功
- **耗时**：2.64s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率排名前10的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "12200000.0"}, {"title": "年度开单金额", "value": "4590966.97999999"}, {"title": "达成率", "value": "37.63"}, {"title": "剩余任务金额", "value": "7609033.02"}]
- **章节**：总体判断 / 代表处对比分析
- **图表**：各代表处达成率排序
- **折叠面板**：山东代表处 / 湖南代表处 / 粤东代表处 / 津冀代表处 / 黑龙江代表处 / 北京代表处 / 四川代表处 / 新西代表处 / 浙江代表处 / 上海代表处 / 粤西广西代表处 / 陕西代表处
- **答案摘要**：{"bottomNames": [], "direction": "desc", "leader": "山东代表处", "metricLabel": "达成率", "mode": "ranking", "rankSides": "top", "tail": "上海代表处", "targetLevel": "代表处", "text": "已按达成率输出 10 个代表处的排序结果", "title": "排名结果", "topN": 10, "topNames": ["山东代表处", "湖南代表处", "粤东代表处", "津冀代表处", "黑龙江代表处", "北京代表处", "四川代表处", "新西代表处", "浙江代表处", "上海代表处"]}
- **叙述**：["本次结果覆盖 12 个代表处", "第一梯队：山东代表处37.63%、湖南代表处34.55%、粤东代表处28.90%、津冀代表处28.86%", "第二梯队：黑龙江代表处28.73%、北京代表处26.32%、四川代表处25.98%、新西代表处25.01%", "第三梯队：浙江代表处24.09%、上海代表处24.04%、粤西广西代表处22.19%、陕西代表处18.50%"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### X18：电商事业部细分业务排名，按年度目标营收完成率排

- **目标数据集**：62
- **预期行为**：明确排序指标
- **状态**：✅ 成功
- **耗时**：4.96s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[62]
- **显示标题**：电商事业部细分业务排名，按年度目标营收完成率排
- **报告标题**：
- **SQL 样例**：
```sql
SELECT '电商业务' AS 条线,
                '业务承接角色' AS 层级,
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
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额 FROM v_feishu_tbldianshang WHERE 当前年 = '2026' AND 层级级别 = '业务经理' ORDER BY 总任务达成率 DESC LIMIT 3;
```
- **⚠️ 异常点**：结果为空

### X19：消费者事业部哪些分公司没达标（达成率低于 60%）

- **目标数据集**：2
- **预期行为**：否定式筛选
- **状态**：✅ 成功
- **耗时**：5.24s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[2]
- **显示标题**：消费者事业部达成率小于60%的分公司
- **报告标题**：消费者事业部业绩分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "117400000.0"}, {"title": "年度开单金额", "value": "22338010.0"}, {"title": "达成率", "value": "19.03"}, {"title": "剩余任务金额", "value": "95061990.0"}]
- **章节**：总体判断 / 分公司对比分析
- **图表**：各分公司达成率排序
- **折叠面板**：江浙沪分公司 / 川藏分公司 / 粤桂琼分公司 / 京津分公司 / 鄂皖分公司 / 赣闽分公司 / 湖南分公司 / 云贵渝分公司 / 西北分公司 / 山东分公司 / 黑吉辽分公司 / 豫晋分公司 / 河北分公司
- **答案摘要**：{"matchedCount": 13, "metricLabel": "达成率", "mode": "filter", "operator": "<", "targetLevel": "分公司", "text": "命中 13 个分公司", "title": "命中结果", "value": 60.0}
- **叙述**：["本次结果覆盖 13 个分公司", "第一梯队：河北分公司33.89%、豫晋分公司32.69%、黑吉辽分公司31.55%、山东分公司31.53%、西北分公司31.19%", "第二梯队：云贵渝分公司31.07%、湖南分公司30.27%、赣闽分公司29.73%、鄂皖分公司28.56%", "第三梯队：京津分公司27.94%、粤桂琼分公司27.25%、川藏分公司23.80%、江浙沪分公司19.03%"]
- **SQL 样例**：
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
    FROM public.fei
```
- **⚠️ 异常点**：卡片标题与问题关联度低

### X20：商用事业部哪些代表处落后了（达成率低于 50%）

- **目标数据集**：3
- **预期行为**：否定式筛选
- **状态**：✅ 成功
- **耗时**：2.63s
- **路由决策**：generate_sql
- **意图**：detail
- **是否需要确认**：False
- **命中数据集**：[3]
- **显示标题**：商用事业部达成率小于50%的代表处
- **报告标题**：经营分析报告
- **KPI 卡**：[{"title": "总任务金额", "value": "69400000.0"}, {"title": "年度开单金额", "value": "13240968.1199999"}, {"title": "达成率", "value": "19.08"}, {"title": "剩余任务金额", "value": "56159031.88"}]
- **章节**：总体判断 / 下一层级对比分析
- **答案摘要**：{"matchedCount": 0, "metricLabel": "达成率", "mode": "filter", "operator": "<", "targetLevel": "下一层级", "text": "未命中符合条件的下一层级", "title": "命中结果", "value": 50.0}
- **叙述**：["当前可比对象不足 2 个，不做横向好坏对比。"]
- **SQL 样例**：
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
            WHEN 业务代表 <> '' THEN COALESCE(NU
```
- **⚠️ 异常点**：卡片标题与问题关联度低
