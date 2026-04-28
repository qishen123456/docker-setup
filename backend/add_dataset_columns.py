import psycopg2

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': '请填写你的数据库密码'
}

def add_missing_columns():
    """添加缺失的字段到bs_datasets表"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 添加缺失的字段
        columns_to_add = [
            "agent_prompt TEXT",
            "ddl_context TEXT", 
            "synonyms TEXT",
            "common_questions TEXT"
        ]
        
        for column_def in columns_to_add:
            column_name = column_def.split()[0]
            try:
                cursor.execute(f"ALTER TABLE bs_datasets ADD COLUMN IF NOT EXISTS {column_def}")
                print(f"✅ 添加字段: {column_name}")
            except Exception as e:
                print(f"⚠️  字段 {column_name} 可能已存在: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ 字段添加完成")
        
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == '__main__':
    add_missing_columns()
