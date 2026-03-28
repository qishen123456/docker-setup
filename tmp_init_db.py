import sqlite3
import datetime
import os

# 确保在项目当前目录创建
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.db')
print(f"正在初始化数据库: {db_path}")

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 创建表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        city TEXT,
        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        price DECIMAL(10,2),
        stock INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        total_amount DECIMAL(10,2),
        order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    ''')

    # 2. 清理旧数据 (可选)
    cursor.execute('DELETE FROM orders')
    cursor.execute('DELETE FROM products')
    cursor.execute('DELETE FROM customers')

    # 3. 插入模拟数据
    # 客户
    customers = [
        ('张三', 'zhangsan@example.com', '北京', '2023-01-15 10:00:00'),
        ('李四', 'lisi@example.com', '上海', '2023-02-20 11:30:00'),
        ('王五', 'wangwu@example.com', '深圳', '2023-03-05 09:15:00'),
        ('赵六', 'zhaoliu@example.com', '杭州', '2023-04-12 14:20:00'),
        ('钱七', 'qianqi@example.com', '成都', '2023-05-18 16:45:00')
    ]
    cursor.executemany('INSERT INTO customers (name, email, city, joined_at) VALUES (?, ?, ?, ?)', customers)

    # 产品
    products = [
        ('iPhone 15', '手机', 5999.00, 50),
        ('MacBook Pro', '电脑', 12999.00, 20),
        ('iPad Air', '平板', 4799.00, 30),
        ('AirPods Pro', '耳机', 1899.00, 100),
        ('Apple Watch', '配件', 2999.00, 40)
    ]
    cursor.executemany('INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)', products)

    # 订单 (随机模拟)
    orders = [
        (1, 1, 1, 5999.00, '2023-06-01 10:00:00'),
        (2, 2, 2, 25998.00, '2023-06-05 14:30:00'),
        (3, 1, 3, 5999.00, '2023-06-10 09:00:00'),
        (1, 4, 2, 3798.00, '2023-06-15 16:20:00'),
        (4, 5, 1, 2999.00, '2023-06-20 11:00:00'),
        (5, 2, 1, 12999.00, '2023-06-25 15:45:00')
    ]
    cursor.executemany('INSERT INTO orders (customer_id, product_id, quantity, total_amount, order_date) VALUES (?, ?, ?, ?, ?)', orders)

    conn.commit()
    conn.close()
    print("数据库初始化完成，数据已注入。")

if __name__ == '__main__':
    init_db()
