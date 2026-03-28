import requests

response = requests.get('http://localhost:5000/api/training')
data = response.json()

print('训练数据总数:', data.get('total', 0))
print('=' * 50)

for i, item in enumerate(data.get('training_data', []), 1):
    print(f'{i}. 类型: {item.get("training_data_type", "N/A")}')
    print(f'   ID: {item.get("id", "N/A")}')
    
    if item.get('training_data_type') == 'ddl':
        print(f'   DDL内容: {item.get("content", "")}')
    elif item.get('training_data_type') == 'documentation':
        print(f'   文档内容: {item.get("content", "")}')
    elif item.get('training_data_type') == 'sql':
        print(f'   问题: {item.get("question", "")}')
        print(f'   SQL字段: {item.get("sql", "")}')
        print(f'   Content字段: {item.get("content", "")}')
    
    print(f'   所有字段: {list(item.keys())}')
    print('-' * 30)
