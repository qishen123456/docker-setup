"""
数据源智能路由器
根据用户问题自动识别应该使用哪个数据源
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from vanna_core import get_vanna_instance
import json

class DataSourceRouter:
    def __init__(self):
        self.data_sources = {}
        self.keywords = {}
        self.load_data_source_config()
    
    def load_data_source_config(self):
        """加载数据源配置"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'datasources.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            for db in config.get('databases', []):
                if db.get('is_active'):
                    ds_id = db['id']
                    ds_name = db['name']
                    ds_type = db['type']
                    
                    self.data_sources[ds_id] = {
                        'name': ds_name,
                        'type': ds_type,
                        'config': db
                    }
                    
                    # 根据数据源名称和类型设置关键词
                    self.keywords[ds_id] = self._generate_keywords(ds_name, ds_type)
                    
        except Exception as e:
            print(f"加载数据源配置失败: {e}")
    
    def _generate_keywords(self, name: str, db_type: str) -> List[str]:
        """根据数据源名称生成关键词"""
        keywords = []
        
        # 从名称中提取关键词
        name_lower = name.lower()
        
        # 飞书相关关键词
        if '飞书' in name or 'feishu' in name_lower or '多维表格' in name:
            keywords.extend(['飞书', '多维表格', '事业', '事业部', '分公司', '代表处', '业务代表', '业绩', '任务', '开单', '销售', '商用'])
        
        # CRM相关关键词  
        if 'crm' in name_lower or '客户' in name or '生产' in name:
            keywords.extend(['客户', '用户', '销售', '线索', '商机', '合同', '订单', 'crm', '生产'])
        
        # 会员相关关键词
        if '会员' in name_lower or 'member' in name_lower:
            keywords.extend(['会员', '用户', '积分', '等级', '权益'])
        
        # 测试相关关键词
        if '测试' in name or 'test' in name_lower or '本地' in name:
            keywords.extend(['测试', '本地', 'test'])
        
        # 年份关键词
        for year in ['2023', '2024', '2025', '2026']:
            if year in name:
                keywords.append(year)
        
        # 数据库类型关键词
        if db_type == 'postgresql':
            keywords.append('postgresql')
        elif db_type == 'mysql':
            keywords.append('mysql')
        elif db_type == 'sqlite':
            keywords.append('sqlite')
        elif db_type == 'sqlserver':
            keywords.extend(['sqlserver', 'sql server'])
        
        return keywords
    
    def identify_data_source(self, question: str) -> Tuple[Optional[int], float]:
        """
        识别问题应该使用哪个数据源
        返回: (数据源ID, 置信度)
        """
        question_lower = question.lower()
        scores = {}
        
        # 计算每个数据源的匹配分数
        for ds_id, keywords in self.keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in question_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                scores[ds_id] = {
                    'score': score,
                    'keywords': matched_keywords,
                    'confidence': score / len(keywords)  # 置信度 = 匹配关键词数 / 总关键词数
                }
        
        if not scores:
            return None, 0.0
        
        # 返回分数最高的数据源
        best_ds_id = max(scores.keys(), key=lambda k: scores[k]['score'])
        best_score = scores[best_ds_id]
        
        print(f"🔍 识别数据源: {self.data_sources[best_ds_id]['name']}")
        print(f"   匹配关键词: {best_score['keywords']}")
        print(f"   置信度: {best_score['confidence']:.2f}")
        
        return best_ds_id, best_score['confidence']
    
    def get_vanna_for_source(self, source_id: int) -> Tuple[object, str]:
        """获取指定数据源的Vanna实例"""
        if source_id not in self.data_sources:
            return None, "数据源不存在"
        
        source_config = self.data_sources[source_id]
        
        # 为每个数据源创建独立的训练数据路径
        chroma_path = f"chroma_db_source_{source_id}"
        
        # 获取针对该数据源的Vanna实例
        try:
            from vanna_core import MyVanna
            import os
            
            # 获取AI模型配置
            from config_manager import get_default_ai_model
            ai_model = get_default_ai_model()
            if not ai_model:
                return None, "未找到AI模型配置"
            
            vn_config = {
                'api_key': ai_model['api_key'],
                'model': ai_model['model'],
                'base_url': ai_model['base_url'],
                'chroma_path': os.path.join(os.path.dirname(__file__), chroma_path)
            }
            
            vn = MyVanna(config=vn_config)
            
            # 连接到对应的数据库
            self._connect_vanna_to_database(vn, source_config['config'])
            
            # 添加数据源特定的系统提示
            vn._system_prompt = self._generate_system_prompt(source_config)
            
            return vn, None
            
        except Exception as e:
            return None, f"创建Vanna实例失败: {e}"
    
    def _connect_vanna_to_database(self, vn, db_config):
        """连接Vanna到指定数据库"""
        db_type = db_config['type']
        
        if db_type == 'postgresql':
            vn.connect_to_postgres(
                host=db_config['host'],
                dbname=db_config['database_name'],
                user=db_config['username'],
                password=self._decode_password(db_config['password_b64']),
                port=db_config['port']
            )
        elif db_type == 'mysql':
            vn.connect_to_mysql(
                host=db_config['host'],
                dbname=db_config['database_name'],
                user=db_config['username'],
                password=self._decode_password(db_config['password_b64']),
                port=db_config['port']
            )
        elif db_type == 'sqlite':
            vn.connect_to_sqlite(db_config['sqlite_path'])
        elif db_type == 'sqlserver':
            import pyodbc
            odbc_conn_str = (
                f"DRIVER={{{db_config['driver']}}};"
                f"SERVER={db_config['host']};"
                f"DATABASE={db_config['database_name']};"
                f"UID={db_config['username']};"
                f"PWD={self._decode_password(db_config['password_b64'])}"
            )
            vn.connect_to_mssql(odbc_conn_str=odbc_conn_str)
    
    def _decode_password(self, password_b64):
        """解码密码"""
        import base64
        return base64.b64decode(password_b64).decode('utf-8')
    
    def _generate_system_prompt(self, source_config):
        """为数据源生成特定的系统提示"""
        from sql_prompt_manager import sql_prompt_manager
        
        name = source_config['name']
        db_type = source_config['type']
        
        # 根据数据源类型选择合适的提示词
        prompt_id = 'default'
        if '飞书' in name or 'feishu' in name.lower():
            prompt_id = 'feishu_specific'
        elif 'crm' in name.lower() or '客户' in name:
            prompt_id = 'crm_specific'
        
        # 使用SQL提示词管理器获取格式化的提示词
        prompt = sql_prompt_manager.format_prompt(
            prompt_id=prompt_id,
            database_name=name,
            database_type=db_type
        )
        
        # 如果没有找到特定提示词，使用默认逻辑
        if not prompt or prompt == sql_prompt_manager.get_prompt('default').get('content', ''):
            prompt = f"""你是一个SQL专家。重要提示：
1. 当前连接的数据库是：{name} ({db_type})
2. 请根据这个数据源的特点生成SQL
3. 如果是飞书数据，注意字段是JSONB格式
4. 如果是CRM数据，注意标准的客户管理表结构
5. 确保生成的SQL只包含这个数据库中存在的表和字段
6. 不要引用其他数据库的表名或字段名"""
        
        return prompt
    
    def smart_chat(self, question: str) -> Dict:
        """
        智能聊天：自动识别数据源并生成SQL
        优化：优先检查训练数据，如果有匹配则直接使用
        """
        # 1. 识别数据源
        source_id, confidence = self.identify_data_source(question)
        
        if source_id is None:
            return {
                'error': '无法识别您要查询的数据源，请明确指定要查询的数据类型',
                'suggestions': list(self.data_sources.values())
            }
        
        if confidence < 0.05:  # 置信度太低
            return {
                'error': f'识别到可能的数据源：{self.data_sources[source_id]["name"]}，但置信度较低({confidence:.2f})',
                'suggestion': '请更明确地指定要查询的数据类型或表名'
            }
        
        # 2. 获取对应的Vanna实例
        vn, error = self.get_vanna_for_source(source_id)
        if error:
            return {'error': f'数据源连接失败: {error}'}
        
        # 3. 优先检查训练数据中的匹配问答对
        try:
            print(f"🔍 检查训练数据中是否有匹配的问题...")
            
            # 获取训练数据
            training_data = vn.get_training_data()
            if training_data is not None and not training_data.empty:
                # 查找完全匹配的问题
                exact_matches = training_data[training_data['question'].str.strip() == question.strip()]
                
                if not exact_matches.empty:
                    # 找到完全匹配的训练数据
                    matched_row = exact_matches.iloc[0]
                    matched_sql = matched_row.get('sql', '')
                    
                    print(f"✅ 找到训练数据匹配！直接使用已训练的SQL")
                    print(f"   问题: {question}")
                    print(f"   匹配问题: {matched_row.get('question', '')}")
                    print(f"   SQL长度: {len(matched_sql)} 字符")
                    
                    # 执行匹配的SQL
                    df = vn.run_sql(matched_sql)
                    
                    # 格式化结果
                    if df is None or df.empty:
                        return {
                            'question': question,
                            'data_source': self.data_sources[source_id]['name'],
                            'sql': matched_sql,
                            'confidence': 1.0,  # 训练数据匹配，置信度最高
                            'from_training': True,
                            'columns': [],
                            'rows': [],
                            'row_count': 0,
                            'message': '查询成功，但没有找到匹配的数据'
                        }
                    
                    # 转换数据格式
                    columns = list(df.columns)
                    rows = []
                    for idx, row in df.iterrows():
                        row_dict = {}
                        for col in columns:
                            val = row[col]
                            if hasattr(val, 'isoformat'):  # datetime
                                val = val.isoformat()
                            elif hasattr(val, 'item'):  # numpy types
                                val = val.item()
                            elif hasattr(val, 'normalize'):  # Decimal
                                val = float(val)
                            elif val != val:  # NaN
                                val = None
                            row_dict[col] = val
                        rows.append(row_dict)
                    
                    return {
                        'question': question,
                        'data_source': self.data_sources[source_id]['name'],
                        'sql': matched_sql,
                        'confidence': 1.0,  # 训练数据匹配，置信度最高
                        'from_training': True,
                        'columns': columns,
                        'rows': rows,
                        'row_count': len(rows)
                    }
                
                # 查找相似问题（包含关键词）
                question_lower = question.lower()
                similar_matches = []
                
                for idx, row in training_data.iterrows():
                    train_question = str(row.get('question', '')).lower()
                    # 计算相似度（简单的关键词匹配）
                    common_words = set(question_lower.split()) & set(train_question.split())
                    if len(common_words) >= 2:  # 至少有2个共同词
                        similarity = len(common_words) / max(len(question_lower.split()), len(train_question.split()))
                        if similarity > 0.99:  # 相似度超过99%
                            similar_matches.append((idx, similarity, row))
                
                # 按相似度排序
                similar_matches.sort(key=lambda x: x[1], reverse=True)
                
                if similar_matches:
                    best_match = similar_matches[0]
                    matched_sql = best_match[2].get('sql', '')
                    
                    print(f"🎯 找到相似问题训练数据！")
                    print(f"   原问题: {question}")
                    print(f"   相似问题: {best_match[2].get('question', '')}")
                    print(f"   相似度: {best_match[1]:.2f}")
                    print(f"   SQL长度: {len(matched_sql)} 字符")
                    
                    # 如果相似度很高（>0.99），直接使用训练数据
                    if best_match[1] > 0.99:
                        print(f"   ✅ 相似度很高，使用训练数据")
                        
                        # 执行匹配的SQL
                        df = vn.run_sql(matched_sql)
                        
                        # 格式化结果
                        if df is None or df.empty:
                            return {
                                'question': question,
                                'data_source': self.data_sources[source_id]['name'],
                                'sql': matched_sql,
                                'confidence': best_match[1],
                                'from_training': True,
                                'similar_question': best_match[2].get('question', ''),
                                'columns': [],
                                'rows': [],
                                'row_count': 0,
                                'message': '查询成功，但没有找到匹配的数据'
                            }
                        
                        # 转换数据格式
                        columns = list(df.columns)
                        rows = []
                        for idx, row in df.iterrows():
                            row_dict = {}
                            for col in columns:
                                val = row[col]
                                if hasattr(val, 'isoformat'):  # datetime
                                    val = val.isoformat()
                                elif hasattr(val, 'item'):  # numpy types
                                    val = val.item()
                                elif hasattr(val, 'normalize'):  # Decimal
                                    val = float(val)
                                elif val != val:  # NaN
                                    val = None
                                row_dict[col] = val
                            rows.append(row_dict)
                        
                        return {
                            'question': question,
                            'data_source': self.data_sources[source_id]['name'],
                            'sql': matched_sql,
                            'confidence': best_match[1],
                            'from_training': True,
                            'similar_question': best_match[2].get('question', ''),
                            'columns': columns,
                            'rows': rows,
                            'row_count': len(rows)
                        }
                    else:
                        print(f"   ⚠️ 相似度不够高，继续生成新SQL")
            
            print(f"📝 没有找到匹配的训练数据，生成新SQL...")
            
        except Exception as e:
            print(f"⚠️ 训练数据检查失败，继续生成新SQL: {e}")
        
        # 4. 生成新的SQL（如果没有匹配的训练数据）
        try:
            print(f"🤖 开始生成新的SQL...")
            sql = vn.generate_sql(question)
            
            print(f"✅ SQL生成完成，长度: {len(sql)} 字符")
            
            # 5. 执行SQL
            df = vn.run_sql(sql)
            
            # 6. 格式化结果
            if df is None or df.empty:
                return {
                    'question': question,
                    'data_source': self.data_sources[source_id]['name'],
                    'sql': sql,
                    'confidence': confidence,
                    'from_training': False,
                    'columns': [],
                    'rows': [],
                    'row_count': 0,
                    'message': '查询成功，但没有找到匹配的数据'
                }
            
            # 转换数据格式
            columns = list(df.columns)
            rows = []
            for idx, row in df.iterrows():
                row_dict = {}
                for col in columns:
                    val = row[col]
                    if hasattr(val, 'isoformat'):  # datetime
                        val = val.isoformat()
                    elif hasattr(val, 'item'):  # numpy types
                        val = val.item()
                    elif hasattr(val, 'normalize'):  # Decimal
                        val = float(val)
                    elif val != val:  # NaN
                        val = None
                    row_dict[col] = val
                rows.append(row_dict)
            
            return {
                'question': question,
                'data_source': self.data_sources[source_id]['name'],
                'sql': sql,
                'confidence': confidence,
                'from_training': False,
                'columns': columns,
                'rows': rows,
                'row_count': len(rows)
            }
            
        except Exception as e:
            return {
                'error': f'SQL生成或执行失败: {str(e)}',
                'data_source': self.data_sources[source_id]['name'],
                'confidence': confidence
            }

# 全局路由器实例
router = DataSourceRouter()
