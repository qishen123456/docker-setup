import requests

response = requests.get('http://localhost:5000/api/training')
data = response.json()

print('训练数据总数:', data.get('total', 0))

for item in data.get('training_data', []):
    if item.get('training_data_type') == 'ddl':
        print(f'DDL数据 - ID: {item.get("id", "N/A")}')
        print(f'内容长度: {len(item.get("content", ""))} 字符')
        print(f'内容预览: {item.get("content", "")[:100]}...')
        print(f'所有字段: {list(item.keys())}')
        break
else:
    print('没有找到DDL类型的数据')
