import sqlite3

conn = sqlite3.connect('D:/1、工作文件/22.智能问数项目/anti02/anti02/test.db')
cursor = conn.cursor()

# 查看所有表
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

if tables:
    # 查看第一个表的结构
    cursor.execute(f'PRAGMA table_info({tables[0][0]})')
    columns = cursor.fetchall()
    print(f'Columns in {tables[0][0]}:', columns)
    
    # 查看前几条数据
    cursor.execute(f'SELECT * FROM {tables[0][0]} LIMIT 3')
    rows = cursor.fetchall()
    print(f'Sample data from {tables[0][0]}:', rows)

conn.close()
