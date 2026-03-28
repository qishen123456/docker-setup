#!/usr/bin/env python3
import requests
import json

print("🧪 测试分析提示词管理功能")

# 测试获取提示词列表
try:
    response = requests.get('http://localhost:5000/api/analysis-prompts')
    if response.status_code == 200:
        data = response.json()
        print("✅ 获取提示词列表成功!")
        print(f"共有 {data['total']} 个提示词:")
        for i, prompt in enumerate(data['prompts'], 1):
            print(f"  {i}. {prompt['name']} ({prompt['category']})")
            print(f"     默认: {'是' if prompt['is_default'] else '否'}")
            print(f"     内容预览: {prompt['prompt'][:50]}...")
            print()
    else:
        print(f"❌ 获取失败: {response.status_code}")
        print(f"错误: {response.text}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("="*60)

# 测试创建新提示词
new_prompt = {
    "name": "销售业绩深度分析",
    "category": "业绩分析",
    "prompt": """请基于以下销售数据进行深度分析：

分析维度：
1. 销售额趋势分析
2. 区域业绩对比
3. 产品线表现
4. 客户满意度关联
5. 市场份额变化

要求：
- 提供数据驱动的洞察
- 识别关键机会点
- 给出具体行动建议
- 预测未来趋势

请用专业的商业分析语言撰写报告。""",
    "is_default": False
}

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts',
        json=new_prompt,
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code == 200:
        result = response.json()
        print("✅ 创建新提示词成功!")
        print(f"提示词名称: {result['prompt']['name']}")
    else:
        print(f"❌ 创建失败: {response.status_code}")
        print(f"错误: {response.text}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("="*60)
print("📝 现在你可以在前端访问分析提示词管理页面了!")
print("   1. 打开浏览器访问 http://localhost:5173")
print("   2. 点击左侧菜单的'分析提示词'")
print("   3. 查看、编辑或创建新的分析提示词")
