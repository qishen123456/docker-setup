"""
Vanna 核心封装模块
- 支持任意 OpenAI 兼容 API（通义千问、DeepSeek、自定义第三方等）
- 支持动态切换 AI 模型和数据库连接
- 支持 SQLite（无需额外驱动）、MySQL、PostgreSQL、SQL Server
"""

from vanna.base import VannaBase
from vanna.chromadb import ChromaDB_VectorStore
from openai import OpenAI
import os

# 禁用代理设置
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────
# 通用 OpenAI 兼容 LLM 类
# ─────────────────────────────────────────────────────────
class OpenAICompatibleLLM(VannaBase):
    """
    支持所有 OpenAI 兼容 API 的 LLM 类
    通过 base_url 参数可接入：
    - 阿里通义（https://dashscope.aliyuncs.com/compatible-mode/v1）
    - DeepSeek（https://api.deepseek.com/v1）
    - OpenAI 官方（https://api.openai.com/v1）
    - 本地 Ollama（http://localhost:11434/v1）
    - 其他任意第三方 OpenAI 兼容服务
    """

    def __init__(self, config=None):
        if config is None:
            raise ValueError("必须提供 config 配置")

        api_key = config.get('api_key')
        self.model = config.get('model', 'gpt-3.5-turbo')
        base_url = config.get('base_url', 'https://api.openai.com/v1')

        if not api_key:
            raise ValueError("config 中必须包含 api_key")

        # 创建客户端，尝试绕过代理问题
        try:
            import httpx
            # 创建自定义HTTP客户端，禁用代理
            http_client = httpx.Client(
                timeout=30.0,  # 恢复到30秒
                follow_redirects=True
            )
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
        except ImportError:
            # 如果没有httpx，使用默认方式
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )

    def system_message(self, message: str) -> dict:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> dict:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> dict:
        return {"role": "assistant", "content": message}

    def generate_sql(self, question: str, **kwargs) -> str:
        sql = super().generate_sql(question, **kwargs)
        # 修复阿里通义千问转义下划线的 bug
        return sql.replace("\\_", "_")

    def submit_prompt(self, prompt, **kwargs) -> str:
        try:
            print(f"🤖 调用AI模型，模型: {self.model}")
            print(f"📝 消息数量: {len(prompt)}")
            
            # 添加超时控制
            chat_response = self.client.chat.completions.create(
                model=self.model,
                messages=prompt,
                stream=False,
                timeout=180,  # 30秒超时
                max_tokens=8192,  # 设置为8192以内
                temperature=0.1
            )
            
            if not chat_response:
                print("❌ chat_response 为 None")
                return "AI模型响应为空，请检查配置"
            
            if not hasattr(chat_response, 'choices') or len(chat_response.choices) == 0:
                print("❌ chat_response.choices 为空")
                return "AI模型响应格式错误"
            
            if not hasattr(chat_response.choices[0], 'message') or not hasattr(chat_response.choices[0].message, 'content'):
                print("❌ chat_response.choices[0].message.content 为空")
                return "AI模型响应内容缺失"
            
            result = chat_response.choices[0].message.content
            print(f"✅ AI响应成功，长度: {len(result)} 字符")
            return result
            
        except Exception as e:
            error_msg = f"分析报告生成失败：{str(e)}"
            print(f"❌ submit_prompt 错误: {error_msg}")
            return error_msg


# ─────────────────────────────────────────────────────────
# MyVanna：组合 ChromaDB 向量存储 + OpenAI 兼容 LLM
# ─────────────────────────────────────────────────────────
class MyVanna(ChromaDB_VectorStore, OpenAICompatibleLLM):
    def __init__(self, config=None):
        # ChromaDB 持久化存储路径
        chroma_path = config.get('chroma_path', os.path.join(BASE_DIR, 'chroma_db'))
        chroma_config = {**config, 'path': chroma_path}
        ChromaDB_VectorStore.__init__(self, config=chroma_config)
        OpenAICompatibleLLM.__init__(self, config=config)
        
        # 添加llm_client属性，方便流式调用
        self.llm_client = self.client
        
        # 添加系统提示，确保使用正确的年份和数据源
        self._system_prompt = """你是一个SQL专家。重要提示：
1. 当前连接的数据库是：feishu_dtable_sync，只包含 angel_group_data 表
2. angel_group_data 表只包含 2026 年的飞书多维表格数据
3. angel_group_data 表的字段结构：id, record_id, fields(JSONB), created_time, updated_time, sync_time
4. 所有业务数据都存储在 fields 字段中，使用 fields ->> '字段名' 语法访问
5. 当查询涉及"当前年"、"最新年"等时间概念时，请使用 2026 年
6. 字段存储格式为 JSONB，需要使用 jsonb_typeof 和 ->> 操作符
7. 金额字段需要使用 regexp_replace 清理非数字字符
8. 生成简单、直接的SQL，避免过度复杂的CTE结构
9. 优先使用单层查询，只在必要时使用简单的CTE
10. 不要生成其他数据库的表名或字段名
11. 所有查询都应该基于 angel_group_data 表，使用 fields 字段访问数据
12. 确保SQL语法正确且高效，限制返回100行以内"""

    def system_message(self, message: str) -> dict:
        # 合并默认系统提示和自定义提示
        full_message = f"{self._system_prompt}\n\n{message}"
        return {"role": "system", "content": full_message}


# ─────────────────────────────────────────────────────────
# Vanna 实例管理器（单例 + 热重载）
# ─────────────────────────────────────────────────────────
_vanna_instance = None
_current_model_id = None
_current_db_id = None
_needs_reinit = True  # 标志位：配置有变化时，下次请求重新初始化


def mark_reinit():
    """配置发生变化时调用，标记需要重新初始化 Vanna"""
    global _needs_reinit
    _needs_reinit = True


def get_vanna_instance():
    """
    获取 Vanna 实例（懒加载 + 热重载）
    - 首次调用时初始化
    - 配置变更后会自动重新初始化
    返回 (vn, error_message)
    """
    global _vanna_instance, _current_model_id, _current_db_id, _needs_reinit

    if _vanna_instance is not None and not _needs_reinit:
        return _vanna_instance, None

    try:
        from config_manager import get_default_ai_model, get_default_datasource

        # 获取默认 AI 模型配置
        ai_model = get_default_ai_model()
        if not ai_model:
            return None, "未找到可用的 AI 模型配置，请先在【AI模型配置】页面添加"

        # 获取默认数据源配置
        db_config = get_default_datasource()
        if not db_config:
            return None, "未找到可用的数据源配置，请先在【数据源管理】页面添加"

        chroma_path = os.path.join(BASE_DIR, 'chroma_db')

        # 初始化 Vanna
        vn_config = {
            'api_key': ai_model['api_key'],
            'model': ai_model['model'],
            'base_url': ai_model['base_url'],
            'chroma_path': chroma_path
        }
        vn = MyVanna(config=vn_config)

        # 连接数据库
        _connect_database(vn, db_config)

        _vanna_instance = vn
        _current_model_id = ai_model['id']
        _current_db_id = db_config['id']
        _needs_reinit = False

        print(f"✅ Vanna 初始化成功：模型={ai_model['model']}，数据库={db_config['name']}")
        return vn, None

    except Exception as e:
        _vanna_instance = None
        _needs_reinit = True
        return None, f"Vanna 初始化失败：{str(e)}"


def _connect_database(vn: MyVanna, db_config: dict):
    """根据数据源配置连接数据库"""
    db_type = db_config.get('type', 'sqlite')

    if db_type == 'sqlite':
        sqlite_path = db_config.get('sqlite_path', ':memory:')
        # 如果是相对路径，转换为绝对路径
        if sqlite_path and not os.path.isabs(sqlite_path):
            sqlite_path = os.path.join(BASE_DIR, sqlite_path)
        vn.connect_to_sqlite(sqlite_path)
        print(f"  📂 SQLite 已连接：{sqlite_path}")

    elif db_type == 'mysql':
        try:
            host = db_config.get('host', 'localhost')
            port = int(db_config.get('port', 3306))
            database = db_config.get('database_name', '')
            username = db_config.get('username', '')
            password = db_config.get('password', '')
            vn.connect_to_mysql(host=host, dbname=database, user=username,
                                password=password, port=port)
            print(f"  🐬 MySQL 已连接：{host}:{port}/{database}")
        except ImportError:
            raise Exception("MySQL 需要 pymysql，请运行：pip install pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple")

    elif db_type == 'postgresql':
        try:
            host = db_config.get('host', 'localhost')
            port = int(db_config.get('port', 5432))
            database = db_config.get('database_name', '')
            username = db_config.get('username', '')
            password = db_config.get('password', '')
            vn.connect_to_postgres(host=host, dbname=database, user=username,
                                  password=password, port=port)
            print(f"  🐘 PostgreSQL 已连接：{host}:{port}/{database}")
        except ImportError:
            raise Exception("PostgreSQL 需要 psycopg2，请运行：pip install psycopg2-binary -i https://pypi.tuna.tsinghua.edu.cn/simple")

    elif db_type == 'sqlserver':
        try:
            import pyodbc
            driver = db_config.get('driver', 'ODBC Driver 17 for SQL Server')
            server = db_config.get('host', '')
            database = db_config.get('database_name', '')
            username = db_config.get('username', '')
            password = db_config.get('password', '')
            odbc_conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password}"
            )
            vn.connect_to_mssql(odbc_conn_str=odbc_conn_str)
            print(f"  🗄️ SQL Server 已连接：{server}/{database}")
        except ImportError:
            raise Exception("SQL Server 需要 pyodbc + ODBC Driver 17，请参考 README 安装")

    else:
        raise Exception(f"不支持的数据库类型：{db_type}")


def test_db_connection(db_config: dict) -> tuple[bool, str]:
    """
    测试数据库连接（不影响全局 Vanna 实例）
    返回 (success, message)
    """
    db_type = db_config.get('type', 'sqlite')

    if db_type == 'sqlite':
        import sqlite3
        sqlite_path = db_config.get('sqlite_path', ':memory:')
        if sqlite_path and sqlite_path != ':memory:' and not os.path.isabs(sqlite_path):
            sqlite_path = os.path.join(BASE_DIR, sqlite_path)
        try:
            conn = sqlite3.connect(sqlite_path)
            conn.execute("SELECT 1")
            conn.close()
            return True, f"SQLite 连接成功：{sqlite_path}"
        except Exception as e:
            return False, f"SQLite 连接失败：{str(e)}"

    elif db_type == 'mysql':
        try:
            import pymysql
            conn = pymysql.connect(
                host=db_config.get('host', 'localhost'),
                port=int(db_config.get('port', 3306) or 3306),
                user=db_config.get('username', ''),
                password=db_config.get('password', ''),
                database=db_config.get('database_name', ''),
                connect_timeout=10
            )
            conn.close()
            return True, "MySQL 连接成功"
        except ImportError:
            return False, "请先安装 pymysql：pip install pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple"
        except Exception as e:
            return False, f"MySQL 连接失败：{str(e)}"

    elif db_type == 'postgresql':
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=db_config.get('host', 'localhost'),
                port=int(db_config.get('port', 5432) or 5432),
                user=db_config.get('username', ''),
                password=db_config.get('password', ''),
                database=db_config.get('database_name', ''),
                connect_timeout=10
            )
            conn.close()
            return True, "PostgreSQL 连接成功"
        except ImportError:
            return False, "请先安装 psycopg2-binary：pip install psycopg2-binary -i https://pypi.tuna.tsinghua.edu.cn/simple"
        except Exception as e:
            return False, f"PostgreSQL 连接失败：{str(e)}"

    elif db_type == 'sqlserver':
        try:
            import pyodbc
            driver = db_config.get('driver', 'ODBC Driver 17 for SQL Server')
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={db_config.get('host', '')};"
                f"DATABASE={db_config.get('database_name', '')};"
                f"UID={db_config.get('username', '')};"
                f"PWD={db_config.get('password', '')};"
                "Connect Timeout=10"
            )
            conn = pyodbc.connect(conn_str)
            conn.close()
            return True, "SQL Server 连接成功"
        except ImportError:
            return False, "请先安装 pyodbc 并安装 ODBC Driver 17（参考 README）"
        except Exception as e:
            return False, f"SQL Server 连接失败：{str(e)}"

    else:
        return False, f"不支持的数据库类型：{db_type}"


def test_ai_model(model_config: dict) -> tuple[bool, str, float]:
    """
    测试 AI 模型连通性（发送简单 Prompt）
    返回 (success, message, response_time_ms)
    """
    import time
    try:
        client = OpenAI(
            api_key=model_config.get('api_key', ''),
            base_url=model_config.get('base_url', 'https://api.openai.com/v1')
        )
        start = time.time()
        response = client.chat.completions.create(
            model=model_config.get('model', 'gpt-3.5-turbo'),
            messages=[{"role": "user", "content": "回复数字1，不要其他内容"}],
            max_tokens=10
        )
        elapsed = round((time.time() - start) * 1000)
        content = response.choices[0].message.content
        return True, f"模型响应正常，返回：{content}", elapsed
    except Exception as e:
        return False, f"模型测试失败：{str(e)}", 0
