"""
分析提示词控制器
GET    /api/analysis-prompts          - 获取分析提示词列表
POST   /api/analysis-prompts          - 添加分析提示词
PUT    /api/analysis-prompts/<id>     - 更新分析提示词
DELETE /api/analysis-prompts/<id>     - 删除分析提示词
POST   /api/analysis-prompts/generate - 生成分析报告
"""

from flask import Blueprint, jsonify, request, Response
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vanna_core import get_vanna_instance
import json
import pandas as pd

analysis_bp = Blueprint('analysis', __name__)

# 文件持久化存储
# 从backend/controllers/analysis.py指向项目根目录的data文件夹
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
PROMPTS_FILE = os.path.join(DATA_DIR, 'analysis_prompts.json')

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 内存缓存
ANALYSIS_PROMPTS_DB = []

def load_prompts_from_file():
    """从文件加载提示词"""
    global ANALYSIS_PROMPTS_DB
    try:
        if os.path.exists(PROMPTS_FILE):
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                ANALYSIS_PROMPTS_DB = json.load(f)
            print(f"✅ 从文件加载了 {len(ANALYSIS_PROMPTS_DB)} 个提示词")
        else:
            ANALYSIS_PROMPTS_DB = []
            print("📝 提示词文件不存在，使用空列表")
    except Exception as e:
        print(f"❌ 加载提示词文件失败: {e}")
        ANALYSIS_PROMPTS_DB = []

def save_prompts_to_file():
    """保存提示词到文件"""
    try:
        print(f"🔍 调试: DATA_DIR = {DATA_DIR}")
        print(f"🔍 调试: PROMPTS_FILE = {PROMPTS_FILE}")
        print(f"🔍 调试: 当前工作目录 = {os.getcwd()}")
        print(f"🔍 调试: 文件目录是否存在 = {os.path.exists(DATA_DIR)}")
        
        with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ANALYSIS_PROMPTS_DB, f, ensure_ascii=False, indent=2)
        print(f"✅ 保存了 {len(ANALYSIS_PROMPTS_DB)} 个提示词到文件")
        return True
    except Exception as e:
        print(f"❌ 保存提示词文件失败: {e}")
        import traceback
        traceback.print_exc()
        return False

# 初始化默认提示词
def init_default_prompts():
    if not ANALYSIS_PROMPTS_DB:
        ANALYSIS_PROMPTS_DB.extend([
            {
                "id": "default-1",
                "name": "业绩分析报告",
                "category": "业绩分析",
                "prompt": """请基于以下数据进行业绩分析，生成一份详细的分析报告：

数据说明：
- 数据来自飞书多维表格的商用业绩数据
- 包含任务金额、开单金额、完成率等关键指标
- 按不同维度（事业部、分公司、代表处等）组织

分析要求：
1. 总体业绩概览
2. 各维度业绩对比分析
3. 完成率分析
4. 关键发现和建议
5. 数据可视化建议

请以专业、简洁的语言生成报告，突出关键洞察。""",
                "is_default": True,
                "created_at": "2026-03-27T12:00:00Z"
            },
            {
                "id": "default-2", 
                "name": "销售趋势分析",
                "category": "趋势分析", 
                "prompt": """基于销售数据分析趋势变化：

分析重点：
1. 销售额变化趋势
2. 季度/月度对比
3. 增长率分析
4. 预测和建议

请提供数据驱动的趋势分析报告。""",
                "is_default": False,
                "created_at": "2026-03-27T12:00:00Z"
            }
        ])
        # 保存默认提示词到文件
        save_prompts_to_file()

# 初始化 - 先从文件加载，如果没有则创建默认
load_prompts_from_file()
if not ANALYSIS_PROMPTS_DB:
    init_default_prompts()

@analysis_bp.route('/api/analysis-prompts', methods=['GET'])
def get_analysis_prompts():
    """获取分析提示词列表"""
    try:
        return jsonify({
            "prompts": ANALYSIS_PROMPTS_DB,
            "total": len(ANALYSIS_PROMPTS_DB)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/api/analysis-prompts', methods=['POST'])
def create_analysis_prompt():
    """创建分析提示词"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        required_fields = ['name', 'category', 'prompt']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} 不能为空"}), 400
        
        # 如果设为默认，取消其他默认
        if data.get('is_default', False):
            for prompt in ANALYSIS_PROMPTS_DB:
                prompt['is_default'] = False
        
        # 创建新提示词
        new_prompt = {
            "id": f"custom-{len(ANALYSIS_PROMPTS_DB) + 1}",
            "name": data['name'],
            "category": data['category'],
            "prompt": data['prompt'],
            "is_default": data.get('is_default', False),
            "created_at": "2026-03-27T12:00:00Z"
        }
        
        ANALYSIS_PROMPTS_DB.append(new_prompt)
        
        # 保存到文件
        if save_prompts_to_file():
            return jsonify({
                "message": "分析提示词创建成功",
                "prompt": new_prompt
            })
        else:
            return jsonify({"error": "保存失败"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/api/analysis-prompts/<prompt_id>', methods=['PUT'])
def update_analysis_prompt(prompt_id):
    """更新分析提示词"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        # 查找提示词
        prompt_index = None
        for i, prompt in enumerate(ANALYSIS_PROMPTS_DB):
            if prompt['id'] == prompt_id:
                prompt_index = i
                break
        
        if prompt_index is None:
            return jsonify({"error": "提示词不存在"}), 404
        
        # 如果设为默认，取消其他默认
        if data.get('is_default', False):
            for prompt in ANALYSIS_PROMPTS_DB:
                prompt['is_default'] = False
        
        # 更新提示词
        ANALYSIS_PROMPTS_DB[prompt_index].update({
            "name": data.get('name', ANALYSIS_PROMPTS_DB[prompt_index]['name']),
            "category": data.get('category', ANALYSIS_PROMPTS_DB[prompt_index]['category']),
            "prompt": data.get('prompt', ANALYSIS_PROMPTS_DB[prompt_index]['prompt']),
            "is_default": data.get('is_default', ANALYSIS_PROMPTS_DB[prompt_index]['is_default'])
        })
        
        # 保存到文件
        if save_prompts_to_file():
            return jsonify({
                "message": "分析提示词更新成功",
                "prompt": ANALYSIS_PROMPTS_DB[prompt_index]
            })
        else:
            return jsonify({"error": "保存失败"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/api/analysis-prompts/<prompt_id>', methods=['DELETE'])
def delete_analysis_prompt(prompt_id):
    """删除分析提示词"""
    try:
        # 查找并删除提示词
        prompt_index = None
        for i, prompt in enumerate(ANALYSIS_PROMPTS_DB):
            if prompt['id'] == prompt_id:
                prompt_index = i
                break
        
        if prompt_index is None:
            return jsonify({"error": "提示词不存在"}), 404
        
        deleted_prompt = ANALYSIS_PROMPTS_DB.pop(prompt_index)
        
        # 保存到文件
        if save_prompts_to_file():
            return jsonify({
                "message": "分析提示词删除成功",
                "deleted_prompt": deleted_prompt
            })
        else:
            return jsonify({"error": "保存失败"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/api/analysis-prompts/generate', methods=['POST'])
def generate_analysis():
    """生成数据分析报告"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        # 获取数据
        query_data = data.get('query_data', {})
        question = query_data.get('question', '')
        sql = query_data.get('sql', '')
        rows = query_data.get('rows', [])
        columns = query_data.get('columns', [])
        
        if not rows or not columns:
            return jsonify({"error": "缺少分析数据"}), 400
        
        # 创建DataFrame
        df = pd.DataFrame(rows, columns=columns)
        
        # 获取分析提示词
        if data.get('prompt'):
            prompt_template = data['prompt']
        else:
            # 使用默认提示词
            default_prompt = next((p for p in ANALYSIS_PROMPTS_DB if p.get('is_default')), ANALYSIS_PROMPTS_DB[0])
            prompt_template = default_prompt['prompt']
        
        # 准备分析数据
        # 限制数据样本大小以提高性能
        sample_size = min(100, len(df))
        df_sample = df.head(sample_size)
        
        data_summary = f"""
原始问题：{question}
SQL查询：{sql[:200]}...
数据行数：{len(df)}
数据列：{', '.join(columns)}

数据样本（前{sample_size}行）：
{df_sample.to_string(max_cols=10)}

数据统计：
{df_sample.describe().to_string()}
"""
        
        # 构建完整提示词
        full_prompt = f"{prompt_template}\n\n{data_summary}"
        
        print(f"🔍 开始生成分析报告...")
        print(f"📝 使用提示词长度: {len(prompt_template)} 字符")
        print(f"📊 数据行数: {len(df)}, 列数: {len(columns)}")
        
        # 调用AI模型生成分析
        vn, error = get_vanna_instance()
        if error:
            return jsonify({"error": f"AI模型初始化失败: {error}"}), 503
        
        # 构建消息数组
        messages = [
            {"role": "system", "content": "你是一个专业的数据分析师，擅长基于数据生成洞察性分析报告。"},
            {"role": "user", "content": full_prompt}
        ]
        
        print(f"🤖 调用AI模型生成分析...")
        
        # 使用Vanna的submit_prompt方法调用AI
        analysis_result = vn.submit_prompt(messages)
        
        print(f"✅ 分析报告生成完成，长度: {len(analysis_result)} 字符")
        
        return jsonify({
            "analysis": analysis_result,
            "data_summary": {
                "question": question,
                "row_count": len(df),
                "columns": columns,
                "data_preview": df.head().to_dict('records')
            }
        })
        
    except Exception as e:
        print(f"❌ 生成分析报告失败: {e}")
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/api/analysis-prompts/generate-stream', methods=['POST'])
def generate_analysis_stream():
    """流式生成数据分析报告"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        # 获取数据
        query_data = data.get('query_data', {})
        question = query_data.get('question', '')
        sql = query_data.get('sql', '')
        rows = query_data.get('rows', [])
        columns = query_data.get('columns', [])
        
        if not rows or not columns:
            return jsonify({"error": "缺少分析数据"}), 400
        
        # 创建DataFrame
        df = pd.DataFrame(rows, columns=columns)
        
        # 获取分析提示词
        if data.get('prompt'):
            prompt_template = data['prompt']
        else:
            # 使用默认提示词
            default_prompt = next((p for p in ANALYSIS_PROMPTS_DB if p.get('is_default')), ANALYSIS_PROMPTS_DB[0])
            prompt_template = default_prompt['prompt']
        
        # 准备分析数据
        sample_size = min(100, len(df))
        df_sample = df.head(sample_size)
        
        data_summary = f"""
原始问题：{question}
SQL查询：{sql[:200]}...
数据行数：{len(df)}
数据列：{', '.join(columns)}

数据样本（前{sample_size}行）：
{df_sample.to_string(max_cols=10)}

数据统计：
{df_sample.describe().to_string()}
"""
        
        # 构建完整提示词
        full_prompt = f"{prompt_template}\n\n{data_summary}"
        
        print(f"🔍 开始流式生成分析报告...")
        
        # 获取AI模型实例
        vn, error = get_vanna_instance()
        if error:
            return jsonify({"error": f"AI模型初始化失败: {error}"}), 503
        
        # 构建消息数组
        messages = [
            {"role": "system", "content": "你是一个专业的数据分析师，擅长基于数据生成洞察性分析报告。"},
            {"role": "user", "content": full_prompt}
        ]
        
        def generate():
            try:
                # 调用AI模型的流式接口
                client = vn.llm_client
                
                print(f"🤖 开始流式调用AI模型...")
                
                # 发送流式请求
                stream = client.chat.completions.create(
                    model=vn.model,
                    messages=messages,
                    stream=True,
                    timeout=180,
                    max_tokens=8192,
                    temperature=0.1
                )
                
                full_content = ""
                
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        
                        # 发送内容块
                        yield f"data: {json.dumps({'type': 'content', 'content': content}, ensure_ascii=False)}\n\n"
                
                # 发送完成信号
                yield f"data: {json.dumps({'type': 'done', 'analysis': full_content}, ensure_ascii=False)}\n\n"
                
                print(f"✅ 流式分析报告生成完成，总长度: {len(full_content)} 字符")
                
            except Exception as e:
                print(f"❌ 流式生成失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return Response(generate(), mimetype='text/plain', headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        })
        
    except Exception as e:
        print(f"❌ 流式分析报告失败: {e}")
        return jsonify({"error": str(e)}), 500
