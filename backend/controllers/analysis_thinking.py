"""
分析思路控制器 - 为Vanna添加分析思路提示词
POST /api/analysis-thinking - 添加分析思路到Vanna
GET /api/analysis-thinking - 获取分析思路列表
"""

from flask import Blueprint, jsonify, request
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vanna_core import get_vanna_instance

analysis_thinking_bp = Blueprint('analysis_thinking', __name__)

# 预置的分析思路模板
ANALYSIS_THINKING_TEMPLATES = [
    {
        "name": "业绩分析思路",
        "category": "业绩分析",
        "content": """
## 业绩分析思路指南

当用户询问业绩相关问题时，请按照以下思路生成SQL：

### 1. 识别分析维度
- **时间维度**: 年度、季度、月度对比
- **组织维度**: 事业部、分公司、代表处、业务代表
- **指标维度**: 任务金额、开单金额、完成率

### 2. SQL生成要点
- 使用jsonb_typeof和->>操作符处理飞书表格JSON字段
- 使用regexp_replace清理金额字段的非数字字符
- 按track（条线类型）进行维度分类
- 计算完成率时处理除零情况

### 3. 常见问题模式
- "今年业绩" → 使用cur_year = '2026'过滤
- "分公司业绩" → 按fgs字段分组
- "完成率分析" → 计算sales/task*100
- "对比分析" → 使用UNION ALL或GROUP BY

### 4. 数据聚合策略
- 事业部层级：按syb分组汇总
- 区域条线：按track_type和fgs分组
- 行业条线：按track_type和业务代表分组

记住：商用事业部的数据主要来自angel_group_data表，字段存储在JSONB格式的fields字段中。
""",
        "is_active": True
    },
    {
        "name": "趋势分析思路", 
        "category": "趋势分析",
        "content": """
## 趋势分析思路指南

当用户询问趋势相关问题时：

### 1. 时间序列分析
- 按时间字段排序（如果有时间戳）
- 计算同比、环比增长率
- 识别趋势拐点和异常点

### 2. SQL模式
- 使用窗口函数计算移动平均
- 使用LAG/LEAD函数计算环比
- 按时间周期分组统计

### 3. 关键指标
- 销售额趋势：SUM(sales) OVER (ORDER BY time)
- 增长率：(current - previous) / previous * 100
- 移动平均：AVG(value) OVER (ROWS BETWEEN n PRECEDING AND CURRENT ROW)
""",
        "is_active": True
    }
]

@analysis_thinking_bp.route('/api/analysis-thinking', methods=['GET'])
def get_analysis_thinking():
    """获取分析思路列表"""
    try:
        return jsonify({
            "templates": ANALYSIS_THINKING_TEMPLATES,
            "total": len(ANALYSIS_THINKING_TEMPLATES)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_thinking_bp.route('/api/analysis-thinking', methods=['POST'])
def add_analysis_thinking():
    """添加分析思路到Vanna"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        content = data.get('content', '')
        name = data.get('name', '')
        category = data.get('category', '')
        
        if not content or not name:
            return jsonify({"error": "内容和建议名称不能为空"}), 400
        
        # 获取Vanna实例
        vn, error = get_vanna_instance()
        if error:
            return jsonify({"error": f"Vanna初始化失败: {error}"}), 503
        
        # 将分析思路作为文档训练到Vanna
        training_content = f"""
# {name} ({category})

{content}

---
训练时间: {request.host}
"""
        
        result_id = vn.train(documentation=training_content)
        
        return jsonify({
            "message": f"分析思路'{name}'已成功添加到Vanna",
            "training_id": result_id,
            "name": name,
            "category": category
        })
        
    except Exception as e:
        return jsonify({"error": f"添加分析思路失败: {str(e)}"}), 500

@analysis_thinking_bp.route('/api/analysis-thinking/train-templates', methods=['POST'])
def train_default_thinking():
    """将预置的分析思路训练到Vanna"""
    try:
        vn, error = get_vanna_instance()
        if error:
            return jsonify({"error": f"Vanna初始化失败: {error}"}), 503
        
        results = []
        for template in ANALYSIS_THINKING_TEMPLATES:
            if template.get('is_active', True):
                training_content = f"""
# {template['name']} ({template['category']})

{template['content']}

---
预置分析思路模板
训练时间: {request.host}
"""
                try:
                    result_id = vn.train(documentation=training_content)
                    results.append({
                        "name": template['name'],
                        "training_id": result_id,
                        "status": "success"
                    })
                except Exception as e:
                    results.append({
                        "name": template['name'], 
                        "status": "failed",
                        "error": str(e)
                    })
        
        success_count = len([r for r in results if r['status'] == 'success'])
        
        return jsonify({
            "message": f"预置分析思路训练完成：成功 {success_count}/{len(results)} 个",
            "results": results,
            "success_count": success_count,
            "total_count": len(results)
        })
        
    except Exception as e:
        return jsonify({"error": f"训练预置思路失败: {str(e)}"}), 500
