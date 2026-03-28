"""
智能路由系统训练数据初始化
为每个数据源添加针对性的训练数据
"""

from datasource_router import router
import time

def init_feishu_training():
    """初始化飞书数据源训练"""
    print("🔧 初始化飞书数据源训练...")
    
    try:
        vn, error = router.get_vanna_for_source(5)  # 飞书数据源ID是5
        if error:
            print(f"   ❌ 获取Vanna实例失败: {error}")
            return False
        
        # 添加DDL
        ddl_statements = [
            """CREATE TABLE angel_group_data (
    id SERIAL PRIMARY KEY,
    record_id VARCHAR(255) UNIQUE,
    fields JSONB,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);""",
            
            """-- angel_group_data表的字段说明
-- fields字段包含以下JSON结构：
-- {
--   "事业部": "商用事业部",
--   "分公司": "北京分公司", 
--   "代表处": "北京代表处",
--   "业务代表": "张三",
--   "当前年": "2026",
--   "总任务（金额）": "1000000",
--   "年度开单金额": "800000"
-- }"""
        ]
        
        # 添加文档
        documentation = [
            "angel_group_data表存储飞书多维表格的同步数据，包含业绩分析相关信息。",
            "数据字段以JSONB格式存储，主要包含事业部、分公司、代表处、业务代表、年份、任务金额、开单金额等信息。",
            "查询时需要使用jsonb_typeof和->>操作符来提取JSON字段值。",
            "金额字段可能包含非数字字符，需要使用regexp_replace清理。",
            "当前数据年份为2026年。"
        ]
        
        # 添加问答对
        qa_pairs = [
            {
                "question": "商用业绩分析",
                "sql": """WITH safe_field AS (
    SELECT d.id, d.fields,
        CASE WHEN jsonb_typeof(d.fields->'事业部') = 'array' 
            THEN d.fields->'事业部'->0->>'text' 
            ELSE d.fields->>'事业部' END AS syb,
        CASE WHEN jsonb_typeof(d.fields->'分公司') = 'array' 
            THEN d.fields->'分公司'->0->>'text' 
            ELSE d.fields->>'分公司' END AS fgs,
        CASE WHEN jsonb_typeof(d.fields->'代表处') = 'array' 
            THEN d.fields->'代表处'->0->>'text' 
            ELSE d.fields->>'代表处' END AS dbc,
        CASE WHEN jsonb_typeof(d.fields->'业务代表') = 'array' 
            THEN d.fields->'业务代表'->0->>'text' 
            ELSE d.fields->>'业务代表' END AS ywdb,
        CASE WHEN jsonb_typeof(d.fields->'当前年') = 'array' 
            THEN d.fields->'当前年'->0->>'text' 
            ELSE d.fields->>'当前年' END AS cur_year,
        COALESCE(
            NULLIF(
                regexp_replace(
                    CASE WHEN jsonb_typeof(d.fields->'总任务（金额）') = 'array' 
                        THEN d.fields->'总任务（金额）'->0->>'text' 
                        ELSE d.fields->>'总任务（金额）' END, 
                    '[^0-9.-]', '', 'g'
                ), ''
            )::NUMERIC, 0
        ) AS task,
        COALESCE(
            NULLIF(
                regexp_replace(
                    CASE WHEN jsonb_typeof(d.fields->'年度开单金额') = 'array' 
                        THEN d.fields->'年度开单金额'->0->>'text' 
                        ELSE d.fields->>'年度开单金额' END, 
                    '[^0-9.-]', '', 'g'
                ), ''
            )::NUMERIC, 0
        ) AS sales
    FROM angel_group_data d
    WHERE cur_year = '2026'
)
SELECT 
    syb as 事业部,
    SUM(task) as 总任务,
    SUM(sales) as 实际销售,
    CASE WHEN SUM(task) > 0 
        THEN ROUND(SUM(sales) / SUM(task) * 100, 2) 
        ELSE 0 END as 完成率
FROM safe_field 
GROUP BY syb
ORDER BY 完成率 DESC;"""
            },
            {
                "question": "查询飞书销售数据",
                "sql": """SELECT 
    id, 
    fields->>'事业部' AS 事业部,
    fields->>'分公司' AS 分公司,
    fields->>'代表处' AS 代表处,
    fields->>'业务代表' AS 业务代表,
    fields->>'当前年' AS 当前年,
    COALESCE(
        NULLIF(
            regexp_replace(
                CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' 
                    THEN fields->'总任务（金额）'->0->>'text' 
                    ELSE fields->>'总任务（金额）' END, 
                '[^0-9.-]', '', 'g'
            ), ''
        )::NUMERIC as 总任务金额,
    COALESCE(
        NULLIF(
            regexp_replace(
                CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' 
                    THEN fields->'年度开单金额'->0->>'text' 
                    ELSE fields->>'年度开单金额' END, 
                '[^0-9.-]', '', 'g'
            ), ''
        )::NUMERIC as 年度开单金额
FROM angel_group_data 
WHERE (fields->>'当前年')::text = '2026'
  AND fields->>'事业部' IS NOT NULL
ORDER BY 年度开单金额 DESC;"""
            },
            {
                "question": "各分公司业绩统计",
                "sql": """SELECT 
    fields->>'分公司' AS 分公司,
    COUNT(*) as 记录数量,
    SUM(
        COALESCE(
            NULLIF(
                regexp_replace(
                    CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' 
                        THEN fields->'年度开单金额'->0->>'text' 
                        ELSE fields->>'年度开单金额' END, 
                    '[^0-9.-]', '', 'g'
                ), ''
            )::NUMERIC, 0
        )
    ) as 总开单金额
FROM angel_group_data 
WHERE fields->>'当前年' = '2026'
  AND fields->>'分公司' IS NOT NULL
GROUP BY fields->>'分公司'
ORDER BY 总开单金额 DESC;"""
            }
        ]
        
        # 执行训练
        for i, ddl in enumerate(ddl_statements):
            try:
                vn.train(ddl=ddl)
                print(f"   ✅ DDL {i+1} 添加成功")
                time.sleep(0.5)
            except Exception as e:
                print(f"   ❌ DDL {i+1} 添加失败: {e}")
        
        for i, doc in enumerate(documentation):
            try:
                vn.train(documentation=doc)
                print(f"   ✅ 文档 {i+1} 添加成功")
                time.sleep(0.5)
            except Exception as e:
                print(f"   ❌ 文档 {i+1} 添加失败: {e}")
        
        for i, qa in enumerate(qa_pairs):
            try:
                vn.train(question=qa["question"], sql=qa["sql"])
                print(f"   ✅ 问答对 {i+1} 添加成功: {qa['question']}")
                time.sleep(0.5)
            except Exception as e:
                print(f"   ❌ 问答对 {i+1} 添加失败: {e}")
        
        print("   🎉 飞书数据源训练完成！")
        return True
        
    except Exception as e:
        print(f"   ❌ 飞书数据源训练失败: {e}")
        return False

def init_crm_training():
    """初始化CRM数据源训练"""
    print("🔧 初始化CRM数据源训练...")
    
    try:
        vn, error = router.get_vanna_for_source(4)  # CRM数据源ID是4
        if error:
            print(f"   ❌ 获取Vanna实例失败: {error}")
            return False
        
        # 添加CRM相关的训练数据
        documentation = [
            "CRM系统包含客户管理、销售管理、订单管理等核心业务数据。",
            "主要表包括：Account(客户)、Contact(联系人)、Opportunity(商机)、Lead(线索)、Order(订单)等。",
            "客户信息包含客户名称、行业、规模、联系人信息等。",
            "销售数据包含销售金额、阶段、概率、预计成交时间等。"
        ]
        
        qa_pairs = [
            {
                "question": "查看客户信息",
                "sql": """SELECT TOP 10 
    AccountId, Name, AccountNumber, 
    Industry, Revenue, NumberOfEmployees
FROM Account 
WHERE StateCode = 0 
ORDER BY CreatedOn DESC;"""
            },
            {
                "question": "查看销售订单",
                "sql": """SELECT TOP 10 
    OrderId, Name, TotalAmount, 
    CreatedOn, CloseDate, StatusCode
FROM SalesOrder 
WHERE StateCode = 0 
ORDER BY TotalAmount DESC;"""
            },
            {
                "question": "查询销售机会",
                "sql": """SELECT TOP 10 
    OpportunityId, Name, EstimatedRevenue, 
    Probability, StageName, CreatedOn
FROM Opportunity 
WHERE StateCode = 0 
ORDER BY EstimatedRevenue DESC;"""
            }
        ]
        
        # 执行训练
        for i, doc in enumerate(documentation):
            try:
                vn.train(documentation=doc)
                print(f"   ✅ 文档 {i+1} 添加成功")
                time.sleep(0.5)
            except Exception as e:
                print(f"   ❌ 文档 {i+1} 添加失败: {e}")
        
        for i, qa in enumerate(qa_pairs):
            try:
                vn.train(question=qa["question"], sql=qa["sql"])
                print(f"   ✅ 问答对 {i+1} 添加成功: {qa['question']}")
                time.sleep(0.5)
            except Exception as e:
                print(f"   ❌ 问答对 {i+1} 添加失败: {e}")
        
        print("   🎉 CRM数据源训练完成！")
        return True
        
    except Exception as e:
        print(f"   ❌ CRM数据源训练失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始初始化智能路由系统训练数据...")
    print("=" * 50)
    
    # 初始化各个数据源
    success_count = 0
    
    if init_feishu_training():
        success_count += 1
    
    if init_crm_training():
        success_count += 1
    
    print("=" * 50)
    print(f"🎉 初始化完成！成功训练 {success_count} 个数据源")
    
    # 测试智能路由
    print("\n🧪 测试智能路由功能:")
    
    test_questions = [
        ("商用业绩分析", "飞书多维表格"),
        ("查看客户信息", "生产库CRM"),
        ("查询销售订单", "生产库CRM")
    ]
    
    for question, expected_source in test_questions:
        print(f"\n问题: {question}")
        result = router.smart_chat(question)
        
        if 'error' in result:
            print(f"   ❌ 失败: {result['error']}")
        else:
            actual_source = result.get('data_source', '未知')
            status = "✅" if actual_source == expected_source else "⚠️"
            print(f"   {status} 数据源: {actual_source}")
            print(f"   置信度: {result.get('confidence', 0):.2f}")
            print(f"   返回行数: {result.get('row_count', 0)}")

if __name__ == "__main__":
    main()
