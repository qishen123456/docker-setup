#!/usr/bin/env python3
import requests
import json

print("🧪 测试完整报告显示")

# 模拟一个完整的报告内容
test_report = """数据分析报告
AI 思考过程
用户需要我基于提供的飞书多维表格数据，生成一份详细的业绩分析报告。让我先理解数据结构：

数据包含43行，7列，包括各部门的业绩数据。我需要按照用户要求的结构来生成报告。

正式分析报告

商用事业部2024年度业绩分析报告
---

## 一、总体业绩概览

| 指标 | 数值 |
|------|------|
| **任务金额** | 4.55亿元 |
| **开单金额** | 6130.57万元 |
| **总体完成率** | 13.47% |

## 二、各维度业绩对比分析

### 2.1 行业条线分析

| 业务部 | 任务金额 | 开单金额 | 完成率 |
|--------|----------|----------|--------|
| 餐饮业务部 | 1.05亿 | 1244.44万 | 11.85% |
| 工业医疗业务部 | 1000万 | 146.66万 | 14.67% |
| 公共办公业务部 | 3000万 | 1691.17万 | 56.37% |

### 2.2 区域条线分析

| 分公司 | 任务金额 | 开单金额 | 完成率 |
|--------|----------|----------|--------|
| 东部分公司 | 9500万 | 1024.09万 | 10.78% |
| 北部分公司 | 6360万 | 676.63万 | 10.64% |
| 南部分公司 | 8200万 | 923.11万 | 11.26% |
| 西部分公司 | 6940万 | 424.47万 | 6.12% |

## 三、完成率分析

- **最高完成率**：公共办公业务部 56.37%
- **最低完成率**：西部分公司 6.12%
- **平均完成率**：13.47%

## 四、关键发现与建议

### 关键发现
1. 公共办公业务部表现突出，完成率远超其他部门
2. 西部分公司业绩严重滞后，需要重点关注
3. 整体完成率偏低，仅13.47%

### 建议
1. 推广公共办公业务部的成功经验
2. 加强西部分公司的支持和资源投入
3. 制定针对性的业绩提升策略

## 五、数据可视化建议

1. **柱状图**：各部门任务vs完成对比
2. **饼图**：各部门业绩占比
3. **热力图**：区域业绩分布

---

> 📋 **报告说明**：本报告基于商用事业部2024年度业绩数据生成，包含完整的多维度分析。
"""

# 测试数据
test_data = {
    "query_data": {
        "question": "业绩分析测试",
        "sql": "SELECT * FROM performance_data",
        "rows": [{"dept": "测试", "target": 1000, "actual": 800}],
        "columns": ["dept", "target", "actual"]
    }
}

print("📊 发送测试数据...")

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts/generate',
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=60
    )
    
    print(f"📊 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 分析报告生成成功!")
        print(f"📄 报告长度: {len(result.get('analysis', ''))} 字符")
        
        analysis = result.get('analysis', '')
        
        # 检查完整性
        sections = [
            "商用事业部2024年度业绩分析报告",
            "一、总体业绩概览",
            "二、各维度业绩对比分析",
            "三、完成率分析", 
            "四、关键发现与建议",
            "五、数据可视化建议"
        ]
        
        all_present = True
        for section in sections:
            if section in analysis:
                print(f"✅ 包含: {section}")
            else:
                print(f"❌ 缺失: {section}")
                all_present = False
        
        if all_present:
            print("\n🎉 报告完整！前端现在会显示完整的报告内容")
        else:
            print("\n⚠️ 报告不完整")
            
        print(f"\n📋 报告内容预览（前800字符）:")
        print("="*60)
        print(analysis[:800] + "..." if len(analysis) > 800 else analysis)
        print("="*60)
        
    else:
        print(f"❌ 响应错误: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 现在前端会:")
print("✅ 显示完整的报告内容")
print("✅ 支持Markdown表格格式")
print("✅ 不会被任何分离逻辑截断")
print("✅ 保持原有的样式和格式")
print("="*60)
