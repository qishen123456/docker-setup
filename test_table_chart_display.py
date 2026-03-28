#!/usr/bin/env python3
import requests
import json

print("🧪 测试表格和图表代码显示")

# 模拟一个包含表格和图表代码的报告
test_report = """# 2026年商用事业部年度业绩复盘分析报告

## 一、事业部总体业绩看板

### 1.1 全局业绩概览

| 指标 | 数值 | 解读 |
|------|------|------|
| 总任务额 | 4.55亿元 | 全年业绩目标 |
| 累计开单 | 6,130.57万元 | 实际业绩产出 |
| 总体达成率 | 13.47% | 进度严重滞后 |

### 1.2 业绩评价

> 季节性判断：Q1通常为B2B行业淡季，但13.47%的达成率意味着全年时间进度(25%)与业绩进度严重不匹配。

---

## 二、图表展示

### 📊 图表1：事业部总体进度看板

```python
import matplotlib.pyplot as plt
import numpy as np

# 事业部总体数据
labels = ['总任务额', '累计开单', '待分配', '达成率(右轴)']
values = [45500, 6130.57, 14500, 13.47]

fig, ax1 = plt.subplots(figsize=(10, 6))
bars = ax1.bar(labels, values, color=['#4472C4', '#70AD47', '#FFC000', '#5B9BD5'])
ax1.set_ylabel('金额(万元)', fontsize=12)
ax1.set_title('商用事业部2026年业绩进度看板', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('chart1_dashboard.png', dpi=150)
plt.show()
```

### 📊 图表2：四大分公司达成率对比

```python
# 四大分公司数据
companies = ['南部分公司', '东部分公司', '北部分公司', '西部分公司']
achievement_rates = [11.26, 10.78, 10.64, 6.12]
colors = ['#70AD47', '#70AD47', '#70AD47', '#FF6B6B']

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(companies, achievement_rates, color=colors, edgecolor='black', linewidth=1.2)

# 添加目标线
ax.axhline(y=25, color='red', linestyle='--', linewidth=2, label='时间进度线(25%)')
ax.set_ylabel('达成率(%)', fontsize=12)
ax.set_title('四大分公司累计达成率对比', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('chart2_regional_comparison.png', dpi=150)
plt.show()
```

---

## 三、数据表格

### 3.1 四大分公司达成率对比

| 分公司 | 任务额(万元) | 累计开单(万元) | 达成率 | 排名 |
|--------|-------------|---------------|--------|------|
| 南部分公司 | 8,200 | 923.11 | 11.26% | 1 |
| 东部分公司 | 9,500 | 1,024.09 | 10.78% | 2 |
| 北部分公司 | 6,360 | 676.63 | 10.64% | 3 |
| 西部分公司 | 6,940 | 424.47 | 6.12% | 4 |

### 3.2 王牌代表业绩

| 排名 | 姓名 | 所属行业部 | 累计开单(万) | 达成率 |
|------|------|-----------|-------------|--------|
| 1 | 韩晓娇 | 公共办公 | 801.38 | 66.78% |
| 2 | 赵标 | 公共办公 | 407.42 | 58.20% |
| 3 | 靳锋 | 餐饮 | 773.20 | 8.59% |
| 4 | 贾希 | 餐饮 | 368.92 | 36.89% |
| 5 | 陈林 | 工业医疗 | 24.44 | 8.15% |

---

## 四、总结

核心结论：当前业绩表现远低于预期，仅完成全年任务的约1/7，若后续三个季度无强力干预，全年目标达成风险极高。

**关键建议**：
- 立即启动"任务清零行动"
- 实施区域帮扶机制  
- 对工业医疗业务进行战略复盘
"""

# 测试数据
test_data = {
    "query_data": {
        "question": "表格和图表测试",
        "sql": "SELECT * FROM performance_data",
        "rows": [
            {"dept": "销售部", "target": 1000, "actual": 800},
            {"dept": "技术部", "target": 800, "actual": 920}
        ],
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
        
        # 检查表格和代码块
        checks = {
            "Markdown表格": "|" in analysis,
            "代码块": "```" in analysis,
            "Python代码": "import matplotlib" in analysis or "plt." in analysis,
            "图表标题": "图表" in analysis or "chart" in analysis.lower()
        }
        
        print("\n🔍 内容检查:")
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"{status} {check_name}")
        
        print(f"\n📋 报告内容预览（前1000字符）:")
        print("="*60)
        print(analysis[:1000] + "..." if len(analysis) > 1000 else analysis)
        print("="*60)
        
    else:
        print(f"❌ 响应错误: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 前端应该能正确显示:")
print("✅ 美观的Markdown表格（带边框和悬停效果）")
print("✅ 格式化的Python代码块（等宽字体+语法高亮）")
print("✅ 图表生成代码（matplotlib代码）")
print("✅ 层次分明的标题结构")
print("✅ 合理的段落和间距")
print("")
print("💡 关于图表代码:")
print("• 这些是Python matplotlib代码，用于生成图表")
print("• 用户可以看到完整的图表生成逻辑")
print("• 如果需要，可以复制这些代码在本地运行生成图表")
print("• 代码块有专门的样式，便于阅读和复制")
print("="*60)
