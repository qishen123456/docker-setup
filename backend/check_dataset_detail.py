import json
import psycopg2
from psycopg2.extras import RealDictCursor

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': '请填写你的数据库密码'
}

def check_dataset_detail():
    """检查数据集的详细内容"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 先查看表结构
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'bs_datasets'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print("� bs_datasets 表结构:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']}")
        print()
        
        # 查询数据集详情
        cursor.execute("""
            SELECT * FROM bs_datasets
        """)
        
        datasets = cursor.fetchall()
        
        if not datasets:
            print("❌ 没有找到任何数据集")
            return
        
        print(f"📊 找到 {len(datasets)} 个数据集\n")
        
        for ds in datasets:
            print(f"{'='*60}")
            for key, value in ds.items():
                if key in ['agent_prompt', 'ddl_context', 'synonyms', 'common_questions']:
                    print(f"{key}: 长度 {len(str(value) or '')} 字符")
                    if value and len(str(value)) > 0:
                        print(f"  内容预览: {str(value)[:200]}...")
                else:
                    print(f"{key}: {value}")
            print(f"\n{'='*60}\n")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == '__main__':
    check_dataset_detail()
