"""补充 Golden SQL 样本中的人员查询示例

目标：为商用和消费者视图补充"按人查询"的样本
- 商用：按业务代表查询（业绩、排名、对比）
- 消费者：按负责人查询（业绩、排名、对比）

用法: docker cp 到容器后执行
"""

import sys
import json
sys.path.insert(0, '/app/backend')

import psycopg2

DB = "host=smartask-postgres dbname=postgres user=postgres password=6670326"

def add_commercial_personnel_samples(cur):
    """补充商用视图的人员查询样本"""
    samples = [
        # 单业务代表业绩
        {
            "question": "丁杰的年度目标和开单金额是多少？",
            "sql_text": "SELECT 节点名称 AS 业务代表, 年度目标营收 AS 年度目标, 年度开单金额 AS 开单金额, 总任务达成率 AS 达成率 FROM v_angel_group_data WHERE 层级级别 = '业务经理' AND 业务代表 = '丁杰'",
            "dataset_id": 3,
            "intent": "aggregation",
            "description": "按业务代表查询业绩"
        },
        {
            "question": "丁杰的任务完成率是多少？",
            "sql_text": "SELECT 业务代表, ROUND(总任务达成率 * 100, 2) AS 完成率百分比 FROM v_angel_group_data WHERE 业务代表 = '丁杰' AND 层级级别 = '业务经理'",
            "dataset_id": 3,
            "intent": "aggregation",
            "description": "查询业务代表达成率"
        },
        {
            "question": "丁杰还有多少任务没完成？",
            "sql_text": "SELECT 业务代表, (年度目标营收 - 年度开单金额) AS 剩余任务金额 FROM v_angel_group_data WHERE 业务代表 = '丁杰' AND 层级级别 = '业务经理'",
            "dataset_id": 3,
            "intent": "aggregation",
            "description": "查询业务代表剩余任务"
        },
        # 业务代表排名
        {
            "question": "所有业务代表的开单金额排名",
            "sql_text": "SELECT 业务代表, 年度开单金额 AS 开单金额 FROM v_angel_group_data WHERE 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC",
            "dataset_id": 3,
            "intent": "ranking",
            "description": "业务代表开单排名"
        },
        {
            "question": "业务代表完成率排行榜",
            "sql_text": "SELECT 业务代表, ROUND(总任务达成率 * 100, 2) AS 完成率 FROM v_angel_group_data WHERE 层级级别 = '业务经理' ORDER BY 总任务达成率 DESC",
            "dataset_id": 3,
            "intent": "ranking",
            "description": "业务代表完成率排名"
        },
        {
            "question": "开单金额最高的前5位业务代表",
            "sql_text": "SELECT 业务代表, 年度开单金额 FROM v_angel_group_data WHERE 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC LIMIT 5",
            "dataset_id": 3,
            "intent": "ranking",
            "description": "Top5业务代表"
        },
        {
            "question": "达成率最低的业务代表有哪些",
            "sql_text": "SELECT 业务代表, ROUND(总任务达成率 * 100, 2) AS 完成率 FROM v_angel_group_data WHERE 层级级别 = '业务经理' ORDER BY 总任务达成率 ASC LIMIT 10",
            "dataset_id": 3,
            "intent": "ranking",
            "description": "最低达成率业务代表"
        },
        # 业务代表对比
        {
            "question": "丁杰和于翔彦谁的开单金额更高？",
            "sql_text": "SELECT 业务代表, 年度开单金额 FROM v_angel_group_data WHERE 业务代表 IN ('丁杰', '于翔彦') AND 层级级别 = '业务经理' ORDER BY 年度开单金额 DESC",
            "dataset_id": 3,
            "intent": "comparison",
            "description": "两位业务代表对比"
        },
        {
            "question": "丁杰和于翔彦的达成率对比",
            "sql_text": "SELECT 业务代表, ROUND(总任务达成率 * 100, 2) AS 达成率 FROM v_angel_group_data WHERE 业务代表 IN ('丁杰', '于翔彦') AND 层级级别 = '业务经理' ORDER BY 总任务达成率 DESC",
            "dataset_id": 3,
            "intent": "comparison",
            "description": "达成率对比"
        },
        # 按负责人查询
        {
            "question": "丁杰负责的代表处有哪些？",
            "sql_text": "SELECT 业务代表, 代表处, 分公司 FROM v_angel_group_data WHERE 业务代表 = '丁杰'",
            "dataset_id": 3,
            "intent": "filter",
            "description": "查询业务代表管辖范围"
        },
        {
            "question": "丁杰的详细业绩数据",
            "sql_text": "SELECT 业务代表, 层级级别, 节点名称, 年度目标营收, 年度开单金额, 总任务达成率, 当前年 FROM v_angel_group_data WHERE 业务代表 = '丁杰'",
            "dataset_id": 3,
            "intent": "drilldown",
            "description": "业务代表明细数据"
        },
    ]
    
    count = 0
    for s in samples:
        cur.execute("""
            INSERT INTO bs_golden_sql_samples 
            (dataset_id, question, sql_text, intent_type, tags, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, TRUE, NOW())
        """, (
            s["dataset_id"],
            s["question"],
            s["sql_text"],
            s["intent"],
            json.dumps([s["description"]])
        ))
        count += 1
    
    return count


def add_consumer_personnel_samples(cur):
    """补充消费者视图的人员查询样本"""
    samples = [
        # 单负责人业绩
        {
            "question": "程琳的年度目标和开单金额是多少？",
            "sql_text": "SELECT 负责人, 事业部, 年度目标营收 AS 年度目标, 年度开单金额 AS 开单金额, 总任务达成率 AS 达成率 FROM v_feishu_xiaofeizhe WHERE 负责人 = '程琳' AND 层级级别 = '事业部'",
            "dataset_id": 2,
            "intent": "aggregation",
            "description": "按负责人查询业绩"
        },
        {
            "question": "程琳的任务完成率是多少？",
            "sql_text": "SELECT 负责人, ROUND(总任务达成率 * 100, 2) AS 完成率百分比 FROM v_feishu_xiaofeizhe WHERE 负责人 = '程琳'",
            "dataset_id": 2,
            "intent": "aggregation",
            "description": "查询负责人达成率"
        },
        {
            "question": "程琳还有多少任务没完成？",
            "sql_text": "SELECT 负责人, (年度目标营收 - 年度开单金额) AS 剩余任务金额 FROM v_feishu_xiaofeizhe WHERE 负责人 = '程琳'",
            "dataset_id": 2,
            "intent": "aggregation",
            "description": "查询负责人剩余任务"
        },
        # 分公司负责人
        {
            "question": "云贵渝分公司的负责人邓金阳的业绩如何？",
            "sql_text": "SELECT 负责人, 销售大区, 年度目标营收, 年度开单金额, 总任务达成率 FROM v_feishu_xiaofeizhe WHERE 销售大区 = '云贵渝分公司' AND 负责人 = '邓金阳'",
            "dataset_id": 2,
            "intent": "aggregation",
            "description": "分公司负责人业绩"
        },
        {
            "question": "邓金阳的开单金额在所有分公司中排名第几？",
            "sql_text": "SELECT 负责人, 销售大区, 年度开单金额 FROM v_feishu_xiaofeizhe WHERE 层级级别 = '分公司' ORDER BY 年度开单金额 DESC",
            "dataset_id": 2,
            "intent": "ranking",
            "description": "分公司负责人排名"
        },
        # 负责人排名
        {
            "question": "所有分公司负责人的开单金额排名",
            "sql_text": "SELECT 负责人, 销售大区, 年度开单金额 AS 开单金额 FROM v_feishu_xiaofeizhe WHERE 层级级别 = '分公司' ORDER BY 年度开单金额 DESC",
            "dataset_id": 2,
            "intent": "ranking",
            "description": "分公司负责人开单排名"
        },
        {
            "question": "分公司负责人完成率排行榜",
            "sql_text": "SELECT 负责人, 销售大区, ROUND(总任务达成率 * 100, 2) AS 完成率 FROM v_feishu_xiaofeizhe WHERE 层级级别 = '分公司' ORDER BY 总任务达成率 DESC",
            "dataset_id": 2,
            "intent": "ranking",
            "description": "分公司负责人完成率排名"
        },
        {
            "question": "开单金额最高的前5位分公司负责人",
            "sql_text": "SELECT 负责人, 销售大区, 年度开单金额 FROM v_feishu_xiaofeizhe WHERE 层级级别 = '分公司' ORDER BY 年度开单金额 DESC LIMIT 5",
            "dataset_id": 2,
            "intent": "ranking",
            "description": "Top5分公司负责人"
        },
        # 负责人对比
        {
            "question": "邓金阳和侯建国谁的开单金额更高？",
            "sql_text": "SELECT 负责人, 销售大区, 年度开单金额 FROM v_feishu_xiaofeizhe WHERE 负责人 IN ('邓金阳', '侯建国') ORDER BY 年度开单金额 DESC",
            "dataset_id": 2,
            "intent": "comparison",
            "description": "两位负责人对比"
        },
        {
            "question": "邓金阳和侯建国的达成率对比",
            "sql_text": "SELECT 负责人, 销售大区, ROUND(总任务达成率 * 100, 2) AS 达成率 FROM v_feishu_xiaofeizhe WHERE 负责人 IN ('邓金阳', '侯建国') ORDER BY 总任务达成率 DESC",
            "dataset_id": 2,
            "intent": "comparison",
            "description": "达成率对比"
        },
        # 线下/新零售渠道
        {
            "question": "邓金阳的线下开单金额是多少？",
            "sql_text": "SELECT 负责人, 销售大区, 线下开单金额, 新零售开单金额, 燃气定制开单金额, 地产开单金额 FROM v_feishu_xiaofeizhe WHERE 负责人 = '邓金阳'",
            "dataset_id": 2,
            "intent": "aggregation",
            "description": "负责人渠道开单"
        },
        {
            "question": "成都城市公司负责人何美棋的详细数据",
            "sql_text": "SELECT 负责人, 销售大区, 城市公司, 层级级别, 年度目标营收, 年度开单金额, 线下开单金额, 新零售开单金额 FROM v_feishu_xiaofeizhe WHERE 城市公司 = '成都城市公司' AND 负责人 = '何美棋'",
            "dataset_id": 2,
            "intent": "drilldown",
            "description": "城市公司负责人明细"
        },
        # 按负责人筛选
        {
            "question": "何美棋负责哪些区域？",
            "sql_text": "SELECT 负责人, 销售大区, 城市公司, 层级级别 FROM v_feishu_xiaofeizhe WHERE 负责人 = '何美棋'",
            "dataset_id": 2,
            "intent": "filter",
            "description": "查询负责人管辖范围"
        },
        {
            "question": "何美棋的新零售开单情况",
            "sql_text": "SELECT 负责人, 销售大区, 城市公司, 新零售开单金额 FROM v_feishu_xiaofeizhe WHERE 负责人 = '何美棋' AND 新零售开单金额 IS NOT NULL",
            "dataset_id": 2,
            "intent": "filter",
            "description": "负责人渠道筛选"
        },
    ]
    
    count = 0
    for s in samples:
        cur.execute("""
            INSERT INTO bs_golden_sql_samples 
            (dataset_id, question, sql_text, intent_type, tags, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, TRUE, NOW())
        """, (
            s["dataset_id"],
            s["question"],
            s["sql_text"],
            s["intent"],
            json.dumps([s["description"]])
        ))
        count += 1
    
    return count


def main():
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    
    print("=" * 60)
    print("🚀 补充 Golden SQL 人员查询样本")
    print("=" * 60)
    
    # 商用
    print("\n[1/2] 补充商用视图人员查询样本 ...")
    count_commercial = add_commercial_personnel_samples(cur)
    conn.commit()
    print(f"  ✅ 新增 {count_commercial} 条样本")
    
    # 消费者
    print("\n[2/2] 补充消费者视图人员查询样本 ...")
    count_consumer = add_consumer_personnel_samples(cur)
    conn.commit()
    print(f"  ✅ 新增 {count_consumer} 条样本")
    
    # 验证
    print("\n[3/3] 验证新样本 ...")
    cur.execute("""
        SELECT dataset_id, COUNT(*) as 总样本,
               SUM(CASE WHEN sql_text LIKE '%业务代表%' OR sql_text LIKE '%负责人%' THEN 1 ELSE 0 END) as 涉及人员
        FROM bs_golden_sql_samples 
        WHERE is_active = TRUE
        GROUP BY dataset_id
        ORDER BY dataset_id
    """)
    print("\n各数据集人员查询统计:")
    for row in cur.fetchall():
        print(f"  dataset_id={row[0]}: 总{row[1]}条, 涉及人员{row[2]}条")
    
    # 验证新样本SQL可执行
    print("\n[4/4] 验证新样本SQL可执行 ...")
    cur.execute("""
        SELECT id, question, sql_text 
        FROM bs_golden_sql_samples 
        WHERE is_active = TRUE 
          AND (tags::text LIKE '%业务代表%' OR tags::text LIKE '%负责人%')
        ORDER BY id DESC
        LIMIT 10
    """)
    
    success = 0
    fail = 0
    for row in cur.fetchall():
        sid, question, sql = row
        try:
            test_conn = psycopg2.connect(DB)
            test_cur = test_conn.cursor()
            test_cur.execute(sql)
            test_cur.fetchall()
            test_cur.close()
            test_conn.close()
            success += 1
        except Exception as e:
            fail += 1
            print(f"  ❌ [{sid}] {question[:30]}: {str(e)[:100]}")
    
    print(f"\n  执行成功: {success}/{success+fail}")
    
    cur.close()
    conn.close()
    
    print("\n✅ 补充完成！")


if __name__ == "__main__":
    main()
