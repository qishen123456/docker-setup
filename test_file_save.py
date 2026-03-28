#!/usr/bin/env python3
import json
import os

print("🧪 直接测试文件保存功能")

# 模拟数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
PROMPTS_FILE = os.path.join(DATA_DIR, 'analysis_prompts.json')

print(f"📁 数据目录: {DATA_DIR}")
print(f"📄 文件路径: {PROMPTS_FILE}")

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
print(f"✅ 目录创建成功")

# 测试数据
test_data = [
    {
        "id": "test-1",
        "name": "测试提示词1",
        "category": "测试分类",
        "prompt": "这是测试内容",
        "is_default": False,
        "created_at": "2026-03-27T12:00:00Z"
    }
]

try:
    # 保存到文件
    with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    print("✅ 文件保存成功")
    
    # 检查文件是否存在
    if os.path.exists(PROMPTS_FILE):
        print("✅ 文件存在")
        
        # 读取文件
        with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        print(f"✅ 文件读取成功，包含 {len(loaded_data)} 个项目")
        
        # 显示内容
        print("\n📄 文件内容:")
        print(json.dumps(loaded_data, ensure_ascii=False, indent=2))
        
    else:
        print("❌ 文件不存在")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print(f"\n📊 当前目录列表:")
if os.path.exists(DATA_DIR):
    for item in os.listdir(DATA_DIR):
        print(f"  - {item}")
else:
    print("  目录不存在")
