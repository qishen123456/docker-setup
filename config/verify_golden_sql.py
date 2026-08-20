"""Golden SQL 样本验证脚本 - 验证三视图变更后样本仍可执行

用法: docker cp 到容器后执行
"""
import sys
sys.path.insert(0, '/app/backend')

import psycopg2

DB = "host=smartask-postgres dbname=postgres user=postgres password=6670326"

def test_view_samples(dataset_id, dataset_name, view_name):
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    
    print(f"\n{'='*60}")
    print(f"📊 {dataset_name} (dataset_id={dataset_id})")
    print(f"{'='*60}")
    
    # 1. 统计总样本数
    cur.execute("SELECT COUNT(*) FROM bs_golden_sql_samples WHERE dataset_id = %s AND is_active = TRUE", (dataset_id,))
    total = cur.fetchone()[0]
    print(f"总活跃样本: {total}")
    
    # 2. 尝试执行每条样本，统计成功/失败
    cur.execute("""
        SELECT id, question, sql_text 
        FROM bs_golden_sql_samples 
        WHERE dataset_id = %s AND is_active = TRUE
        LIMIT 50
    """, (dataset_id,))
    
    success = 0
    fail = 0
    errors = []
    
    for row in cur.fetchall():
        sample_id, question, sql = row
        # 替换视图引用
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
            errors.append((sample_id, question[:50], str(e)[:200]))
    
    print(f"成功: {success}/{success+fail} (抽样)")
    if errors:
        print(f"\n失败样本:")
        for sid, q, err in errors[:10]:
            print(f"  [{sid}] {q}")
            print(f"         {err}")
    
    cur.close()
    conn.close()
    return total, success, fail, errors

def test_view_data():
    """验证三视图数据完整性"""
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    
    print("\n" + "="*60)
    print("🔍 视图数据验证")
    print("="*60)
    
    # 电商
    cur.execute("SELECT COUNT(*) FROM v_feishu_tbldianshang")
    print(f"\n电商视图: {cur.fetchone()[0]} 行")
    
    cur.execute("SELECT 层级级别, COUNT(*) FROM v_feishu_tbldianshang GROUP BY 层级级别 ORDER BY 层级级别")
    print("  层级分布:")
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")
    
    cur.execute("SELECT AVG(年度目标营收), AVG(年度开单金额), AVG(总任务达成率) FROM v_feishu_tbldianshang")
    row = cur.fetchone()
    print(f"  平均目标/开单/达成率: {row}")
    
    # 商用
    cur.execute("SELECT COUNT(*) FROM v_angel_group_data")
    print(f"\n商用视图: {cur.fetchone()[0]} 行")
    
    cur.execute("SELECT 层级级别, COUNT(*) FROM v_angel_group_data GROUP BY 层级级别 ORDER BY 层级级别")
    print("  层级分布:")
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")
    
    cur.execute("SELECT AVG(年度目标营收), AVG(年度开单金额), AVG(剩余任务金额) FROM v_angel_group_data")
    row = cur.fetchone()
    print(f"  平均目标/开单/剩余: {row}")
    
    # 消费者
    cur.execute("SELECT COUNT(*) FROM v_feishu_xiaofeizhe")
    print(f"\n消费者视图: {cur.fetchone()[0]} 行")
    
    cur.execute("SELECT 层级级别, COUNT(*) FROM v_feishu_xiaofeizhe GROUP BY 层级级别 ORDER BY 层级级别")
    print("  层级分布:")
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")
    
    cur.execute("SELECT AVG(年度目标营收), AVG(线下开单金额), AVG(新零售开单金额) FROM v_feishu_xiaofeizhe")
    row = cur.fetchone()
    print(f"  平均目标/线下/新零售: {row}")
    
    # 检查 NULL 关键指标
    cur.execute("""
        SELECT 
            COUNT(*) as 总行数,
            COUNT(年度目标营收) as 有目标,
            COUNT(年度开单金额) as 有开单,
            COUNT(总任务达成率) as 有达成率
        FROM v_angel_group_data
    """)
    row = cur.fetchone()
    print(f"\n商用视图完整性: {row}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_view_data()
    
    # 测试 Golden SQL 样本
    for did, name, view in [(62, "电商", "v_feishu_tbldianshang"), 
                             (3, "商用", "v_angel_group_data"),
                             (2, "消费者", "v_feishu_xiaofeizhe")]:
        test_view_samples(did, name, view)
    
    print("\n" + "="*60)
    print("✅ 验证完成")
