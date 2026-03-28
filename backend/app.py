"""
Flask 主入口
- 注册所有蓝图
- 启用 CORS（前端 5173 端口可跨域访问）
- 后端启动时初始化默认配置文件
- 运行在 5000 端口
"""

import sys
import os

# 确保 backend 目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify
from flask_cors import CORS

# 初始化默认配置文件（如不存在则创建）
from config_manager import init_default_configs
init_default_configs()

# 创建 Flask 应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文 JSON 输出

# 启用 CORS（允许前端 5173 和 5174 端口访问）
CORS(app, origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"])

# ─────────────────────────────────────────────────────────
# 注册路由蓝图
# ─────────────────────────────────────────────────────────
from controllers.dashboard import dashboard_bp
from controllers.datasources import datasources_bp
from controllers.ai_models import ai_models_bp
from controllers.training import training_bp
from controllers.chat import chat_bp
from controllers.feishu_sync import feishu_bp
from controllers.smart_chat import smart_chat_bp
from controllers.analysis import analysis_bp
from controllers.analysis_thinking import analysis_thinking_bp
from controllers.sql_prompt import sql_prompt_bp

app.register_blueprint(dashboard_bp)
app.register_blueprint(datasources_bp)
app.register_blueprint(ai_models_bp)
app.register_blueprint(training_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(feishu_bp)
app.register_blueprint(smart_chat_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(analysis_thinking_bp)
app.register_blueprint(sql_prompt_bp)


# ─────────────────────────────────────────────────────────
# 健康检查接口
# ─────────────────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "running",
        "message": "Vanna 智能问数系统后端正常运行",
        "version": "1.0.0"
    })


# ─────────────────────────────────────────────────────────
# 全局错误处理
# ─────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "接口不存在", "path": str(e)}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "请求方法不允许"}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "服务器内部错误", "detail": str(e)}), 500


# ─────────────────────────────────────────────────────────
# 启动
# ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Vanna 智能问数系统 — 后端启动")
    print("=" * 50)
    print("📡 API 地址: http://localhost:5000")
    print("📋 健康检查: http://localhost:5000/api/health")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
