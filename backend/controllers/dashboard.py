"""
Dashboard 控制器
GET /api/dashboard - 返回统计数据和最近问答记录
"""

from flask import Blueprint, jsonify
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import (
    get_datasources, get_ai_models, get_query_stats, get_query_history
)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    try:
        # 统计数据
        databases = get_datasources()
        ai_models = get_ai_models()
        query_stats = get_query_stats()
        recent_history = get_query_history(limit=5)

        # 数据源状态
        active_db_count = sum(1 for db in databases if db.get('is_active'))

        return jsonify({
            "stats": {
                "total_queries": query_stats['total_queries'],
                "today_queries": query_stats['today_queries'],
                "db_count": len(databases),
                "active_db_count": active_db_count,
                "ai_model_count": len(ai_models),
                "active_ai_count": sum(1 for m in ai_models if m.get('is_active'))
            },
            "recent_queries": recent_history,
            "system_status": {
                "backend": "running",
                "database": "connected" if active_db_count > 0 else "no_active",
                "ai_model": "configured" if any(m.get('is_active') for m in ai_models) else "not_configured"
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
