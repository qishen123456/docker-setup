#!/usr/bin/env python3
import requests
import json

print("🧪 测试简化版分析提示词页面")

# 测试获取提示词列表
try:
    response = requests.get('http://localhost:5000/api/analysis-prompts')
    if response.status_code == 200:
        data = response.json()
        print("✅ API接口正常!")
        print(f"共有 {data['total']} 个提示词:")
        for i, prompt in enumerate(data['prompts'], 1):
            print(f"  {i}. {prompt['name']} ({prompt['category']})")
            print(f"     默认: {'是' if prompt['is_default'] else '否'}")
    else:
        print(f"❌ API接口异常: {response.status_code}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*50)
print("📝 现在你可以:")
print("1. 打开浏览器访问 http://localhost:5173")
print("2. 点击左侧菜单的'分析提示词'")
print("3. 查看和编辑现有的分析提示词")
print("4. 创建新的分析提示词")
print("="*50)
