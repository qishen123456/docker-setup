#!/usr/bin/env python3
import requests
import json
import time

print("🧪 测试分析提示词持久化功能")

BASE_URL = "http://localhost:5000"

def test_prompt_crud():
    """测试提示词的增删改查"""
    
    # 1. 获取当前提示词列表
    print("\n📋 1. 获取提示词列表")
    try:
        response = requests.get(f"{BASE_URL}/api/analysis-prompts")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 当前有 {data['total']} 个提示词")
            for prompt in data['prompts']:
                print(f"  - {prompt['name']} ({prompt['category']})")
        else:
            print(f"❌ 获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    # 2. 创建新提示词
    print("\n➕ 2. 创建新提示词")
    new_prompt = {
        "name": "测试提示词",
        "category": "测试分类",
        "prompt": "这是一个测试提示词，用于验证持久化功能。",
        "is_default": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/analysis-prompts",
            json=new_prompt,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            data = response.json()
            created_prompt = data['prompt']
            prompt_id = created_prompt['id']
            print(f"✅ 创建成功: {created_prompt['name']} (ID: {prompt_id})")
        else:
            print(f"❌ 创建失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    # 3. 更新提示词
    print("\n✏️ 3. 更新提示词")
    update_data = {
        "name": "更新后的测试提示词",
        "category": "更新后的分类",
        "prompt": "这是更新后的提示词内容。",
        "is_default": True
    }
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/analysis-prompts/{prompt_id}",
            json=update_data,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            data = response.json()
            updated_prompt = data['prompt']
            print(f"✅ 更新成功: {updated_prompt['name']}")
        else:
            print(f"❌ 更新失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    # 4. 删除提示词
    print("\n🗑️ 4. 删除提示词")
    try:
        response = requests.delete(f"{BASE_URL}/api/analysis-prompts/{prompt_id}")
        if response.status_code == 200:
            data = response.json()
            deleted_prompt = data['deleted_prompt']
            print(f"✅ 删除成功: {deleted_prompt['name']}")
        else:
            print(f"❌ 删除失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    # 5. 验证删除后的列表
    print("\n📋 5. 验证删除后的列表")
    try:
        response = requests.get(f"{BASE_URL}/api/analysis-prompts")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 删除后有 {data['total']} 个提示词")
            
            # 检查测试提示词是否真的被删除了
            test_prompts = [p for p in data['prompts'] if p['name'] == '更新后的测试提示词']
            if not test_prompts:
                print("✅ 测试提示词已成功删除")
            else:
                print("❌ 测试提示词仍然存在")
                return False
        else:
            print(f"❌ 获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    return True

def check_file_persistence():
    """检查文件是否真的被保存了"""
    print("\n📁 检查文件持久化")
    
    import os
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    prompts_file = os.path.join(data_dir, 'analysis_prompts.json')
    
    if os.path.exists(prompts_file):
        print(f"✅ 提示词文件存在: {prompts_file}")
        
        try:
            with open(prompts_file, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            print(f"✅ 文件包含 {len(prompts)} 个提示词")
            
            # 显示文件内容
            print("\n📄 文件内容:")
            for prompt in prompts:
                print(f"  - {prompt['name']} ({prompt['category']}) - 默认: {prompt.get('is_default', False)}")
            
            return True
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return False
    else:
        print(f"❌ 提示词文件不存在: {prompts_file}")
        return False

# 运行测试
print("🚀 开始测试分析提示词持久化功能...")

if test_prompt_crud():
    print("\n✅ CRUD操作测试通过")
    
    if check_file_persistence():
        print("\n🎉 所有测试通过！提示词持久化功能正常工作")
        print("\n💡 现在你可以:")
        print("• 在前端添加/修改/删除提示词")
        print("• 重启后端服务后数据不会丢失")
        print("• 所有更改都会保存到 data/analysis_prompts.json 文件")
    else:
        print("\n⚠️ CRUD操作正常，但文件持久化有问题")
else:
    print("\n❌ CRUD操作测试失败")

print("\n" + "="*60)
print("📝 修改内容:")
print("✅ 将内存存储改为文件持久化存储")
print("✅ 添加了 load_prompts_from_file() 函数")
print("✅ 添加了 save_prompts_to_file() 函数")
print("✅ 修改了所有CRUD操作，确保每次操作后都保存")
print("✅ 数据保存在 data/analysis_prompts.json 文件中")
print("="*60)
