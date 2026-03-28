#!/usr/bin/env python3
import requests
import json

print("🧪 测试Vanna分析思路训练功能")

# 1. 获取分析思路模板
print("\n1. 获取分析思路模板:")
try:
    response = requests.get('http://localhost:5000/api/analysis-thinking')
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功，共 {data['total']} 个模板")
        for template in data['templates']:
            print(f"  - {template['name']} ({template['category']})")
    else:
        print(f"❌ 获取失败: {response.status_code}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 2. 训练预置思路到Vanna
print("\n2. 训练预置思路到Vanna:")
try:
    response = requests.post('http://localhost:5000/api/analysis-thinking/train-templates')
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 训练完成: {result['message']}")
        print(f"成功: {result['success_count']}/{result['total_count']}")
        
        # 显示详细结果
        for item in result['results']:
            status = "✅" if item['status'] == 'success' else "❌"
            print(f"  {status} {item['name']}")
            if item['status'] == 'failed':
                print(f"    错误: {item.get('error', 'Unknown error')}")
    else:
        print(f"❌ 训练失败: {response.status_code}")
        print(f"错误: {response.text}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 3. 添加自定义分析思路
print("\n3. 添加自定义分析思路:")
custom_thinking = {
    "name": "飞书数据专项分析",
    "category": "业绩分析", 
    "content": """
## 飞书多维表格数据分析指南

### 核心要点：
1. 数据表：angel_group_data
2. 字段格式：JSONB存储在fields字段
3. 年份：2026年数据
4. 关键操作符：jsonb_typeof, ->>, regexp_replace

### SQL模式：
- 时间过滤：WHERE fields->>'当前年' = '2026'
- 金额处理：regexp_replace(fields->>'金额', '[^0-9.-]', '', 'g')::NUMERIC
- 数组字段：fields->'字段名'->0->>'text'
- 分组统计：GROUP BY fields->>'组织字段'

### 业务逻辑：
- 业绩分析：按事业部、分公司、代表处层级
- 完成率：开单金额/任务金额*100
- 对比分析：使用UNION ALL合并不同条线
- 趋势分析：按时间序列排序
"""
}

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-thinking',
        json=custom_thinking,
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 添加成功: {result['message']}")
        print(f"训练ID: {result['training_id']}")
    else:
        print(f"❌ 添加失败: {response.status_code}")
        print(f"错误: {response.text}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 现在你可以:")
print("1. 在前端访问'分析提示词'页面")
print("2. 点击'训练预置思路到Vanna'按钮")
print("3. 创建新的提示词并选择'训练到Vanna'")
print("4. 测试聊天，Vanna会考虑你的分析思路生成SQL")
print("="*60)
