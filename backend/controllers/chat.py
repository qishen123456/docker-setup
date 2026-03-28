"""
智能聊天控制器
POST /api/chat              - 自然语言 -> SQL -> 执行结果
POST /api/chat/generate-sql - 仅生成 SQL（不执行）
GET  /api/chat/history      - 获取问答历史
"""

from flask import Blueprint, jsonify, request
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vanna_core import get_vanna_instance
from config_manager import add_query_history, get_query_history

chat_bp = Blueprint('chat', __name__)


import time

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    """
    核心问答接口
    请求体: {"question": "查询最近10个客户"}
    返回: {"question", "sql", "columns", "rows", "row_count", "error", "steps"}
    """
    start_time = time.time()
    steps = []
    
    try:
        data = request.get_json()
        if not data or not data.get('question'):
            return jsonify({"error": "问题不能为空"}), 400

        question = data['question'].strip()
        
        # Step 0: 初始化 Vanna
        step0_start = time.time()
        vn, error = get_vanna_instance()
        steps.append({
            "title": "初始化 AI 引擎",
            "duration": round((time.time() - step0_start) * 1000, 2),
            "status": "success" if not error else "error"
        })
        
        if error:
            return jsonify({"error": error, "question": question, "steps": steps}), 503

        # Step 1: 解析问题
        step1_start = time.time()
        steps.append({
            "title": "解析问题",
            "duration": round((time.time() - step1_start) * 1000, 2),
            "status": "success"
        })
        
        # Step 2: 匹配训练问答对
        step2_start = time.time()
        sql = None
        sql_source = "大模型生成"
        
        try:
            # 先尝试从训练数据中查找完全匹配的问题
            training_data = vn.get_training_data()
            matched_sql = None
            
            print(f"🔍 查找训练数据匹配: {question}")
            print(f"📊 训练数据数量: {len(training_data) if training_data is not None else 0}")
            
            if training_data is not None and not training_data.empty:
                # 打印所有训练数据的问题
                print("📋 当前训练数据中的问题:")
                for idx, row in training_data.iterrows():
                    q = row.get('question', '')
                    print(f"  {idx}: {q}")
                
                # 查找完全匹配的问题
                for _, row in training_data.iterrows():
                    train_question = row.get('question', '')
                    print(f"🔄 比较用户问题: '{question}' vs 训练问题: '{train_question}'")
                    if train_question == question:
                        # SQL可能在sql字段或content字段中
                        matched_sql = row.get('sql') or row.get('content', '')
                        print(f"✅ 完全匹配成功! 找到SQL长度: {len(matched_sql)}")
                        break
                
                if matched_sql:
                    sql = matched_sql
                    sql_source = "训练数据匹配"
                    print(f"✅ 从训练数据找到匹配问题: {question}")
                    steps.append({
                        "title": "匹配训练问答对",
                        "duration": round((time.time() - step2_start) * 1000, 2),
                        "status": "success",
                        "content": f"找到匹配的训练数据，SQL长度: {len(sql)}"
                    })
                else:
                    # 尝试模糊匹配（相似度高的）
                    for _, row in training_data.iterrows():
                        train_q = row.get('question', '')
                        # 确保train_q不为None且不为空
                        if train_q and isinstance(train_q, str):
                            # 简单的关键词提取（按字符分割，去除停用词）
                            user_keywords = set()
                            train_keywords = set()
                            
                            # 提取用户问题关键词
                            for word in ['商用', '分公司', '事业部', '业绩', '分析', '今年']:
                                if word in question:
                                    user_keywords.add(word)
                            
                            # 提取训练问题关键词  
                            for word in ['商用', '分公司', '事业部', '业绩', '分析', '今年']:
                                if word in train_q:
                                    train_keywords.add(word)
                            
                            # 计算关键词重叠度
                            if user_keywords and train_keywords:
                                overlap = len(user_keywords.intersection(train_keywords))
                                overlap_ratio = overlap / len(user_keywords)
                                
                                # 如果重叠度超过50%，认为是匹配
                                if overlap_ratio >= 0.5:
                                    # SQL可能在sql字段或content字段中
                                    matched_sql = row.get('sql') or row.get('content', '')
                                    print(f"✅ 模糊匹配成功! 重叠度: {overlap_ratio:.2f}, SQL长度: {len(matched_sql)}")
                                    print(f"   用户关键词: {user_keywords}")
                                    print(f"   训练关键词: {train_keywords}")
                                    break
                    
                    if matched_sql:
                        sql = matched_sql
                        sql_source = "训练数据模糊匹配"
                        print(f"✅ 从训练数据模糊匹配: {question}")
                        steps.append({
                            "title": "匹配训练问答对",
                            "duration": round((time.time() - step2_start) * 1000, 2),
                            "status": "success",
                            "content": f"模糊匹配成功，重叠度: {overlap_ratio:.2f}"
                        })
                    else:
                        steps.append({
                            "title": "匹配训练问答对",
                            "duration": round((time.time() - step2_start) * 1000, 2),
                            "status": "success",
                            "content": "未找到匹配的训练数据"
                        })
            else:
                steps.append({
                    "title": "匹配训练问答对",
                    "duration": round((time.time() - step2_start) * 1000, 2),
                    "status": "success",
                    "content": "无训练数据"
                })
            
            # 如果没有找到匹配的训练数据，使用大模型生成
            if not sql:
                # Step 3: 大模型生成SQL
                step3_start = time.time()
                sql = vn.generate_sql(question=question)
                sql_source = "大模型生成"
                print(f"🤖 使用大模型生成SQL: {question}")
                steps.append({
                    "title": "大模型生成SQL",
                    "duration": round((time.time() - step3_start) * 1000, 2),
                    "status": "success",
                    "content": f"生成SQL长度: {len(sql)}"
                })
            else:
                # 如果找到了匹配的训练数据，标记大模型生成SQL为跳过
                steps.append({
                    "title": "大模型生成SQL",
                    "duration": 0,
                    "status": "skipped",
                    "content": "已找到训练数据匹配，跳过大模型生成"
                })
            
            # Step 4: SQL生成完成
            step4_start = time.time()
            steps.append({
                "title": f"SQL生成完成 ({sql_source})",
                "duration": round((time.time() - step4_start) * 1000, 2),
                "status": "success",
                "content": sql
            })
            
        except Exception as e:
            steps.append({
                "title": "生成SQL",
                "duration": round((time.time() - step1_start) * 1000, 2),
                "status": "error",
                "message": str(e)
            })
            add_query_history(question, '', 'error', f'生成SQL失败: {str(e)}')
            return jsonify({
                "question": question,
                "sql": "",
                "error": f"生成 SQL 失败：{str(e)}",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "steps": steps
            }), 400

        # Step 5: 执行 SQL
        step5_start = time.time()
        try:
            df = vn.run_sql(sql=sql)
            steps.append({
                "title": "执行SQL查询",
                "duration": round((time.time() - step5_start) * 1000, 2),
                "status": "success"
            })
            
            if df is None or df.empty:
                add_query_history(question, sql, 'success')
                return jsonify({
                    "question": question,
                    "sql": sql,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "message": "查询成功，但没有找到匹配的数据",
                    "steps": steps
                })

            # 转换为前端可用的格式
            columns = list(df.columns)
            rows = []
            for idx, row in df.iterrows():
                row_dict = {}
                for col in columns:
                    val = row[col]
                    # 处理不可序列化的类型
                    if hasattr(val, 'isoformat'):  # datetime
                        val = val.isoformat()
                    elif hasattr(val, 'item'):  # numpy types
                        val = val.item()
                    elif isinstance(val, bytes):  # bytes类型
                        try:
                            val = val.decode('utf-8')
                        except UnicodeDecodeError:
                            val = str(val)
                    elif hasattr(val, 'normalize'):  # Decimal类型
                        val = float(val)
                    elif val != val:  # NaN
                        val = None
                    row_dict[col] = val
                rows.append(row_dict)

            add_query_history(question, sql, 'success')
            return jsonify({
                "question": question,
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "steps": steps,
                "total_duration": round((time.time() - start_time) * 1000, 2)
            })

        except Exception as e:
            steps.append({
                "title": "执行 SQL 查询",
                "duration": round((time.time() - step2_start) * 1000, 2),
                "status": "error",
                "message": str(e)
            })
            add_query_history(question, sql, 'error', f'执行SQL失败: {str(e)}')
            return jsonify({
                "question": question,
                "sql": sql,
                "error": f"SQL 执行失败：{str(e)}",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "steps": steps
            }), 400

    except Exception as e:
        return jsonify({"error": f"系统错误：{str(e)}", "steps": steps}), 500


@chat_bp.route('/api/chat/generate-sql', methods=['POST'])
def generate_sql_only():
    """仅生成 SQL，不执行"""
    try:
        data = request.get_json()
        if not data or not data.get('question'):
            return jsonify({"error": "问题不能为空"}), 400

        question = data['question'].strip()
        vn, error = get_vanna_instance()
        if error:
            return jsonify({"error": error}), 503

        sql = vn.generate_sql(question=question)
        return jsonify({"question": question, "sql": sql})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route('/api/chat/history', methods=['GET'])
def get_history():
    try:
        limit = int(request.args.get('limit', 20))
        return jsonify({"history": get_query_history(limit=limit)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route('/api/chat/vanna-status', methods=['GET'])
def vanna_status():
    """检查 Vanna 实例状态"""
    try:
        vn, error = get_vanna_instance()
        if error:
            return jsonify({"ready": False, "message": error}), 503
        return jsonify({"ready": True, "message": "Vanna 已就绪"})
    except Exception as e:
        return jsonify({"ready": False, "message": str(e)}), 500
