"""
Application entry for the smart analytics backend.
"""

import os
import sys
import time
import threading

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

BASE_DIR = os.path.dirname(CURRENT_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)
load_dotenv(os.path.join(BASE_DIR, ".env.local"), override=True)


def _make_console_safe():
    """
    Prevent startup crashes on Windows terminals when imported modules print
    characters that are not representable in the active code page.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="ignore")
            except Exception:
                pass


_make_console_safe()

from config_manager import get_app_config, init_default_configs
from secret_codec import decrypt_secret_value
from controllers.ai_models import ai_models_bp
from controllers.agents import agents_bp
from controllers.auth import auth_bp
from controllers.bookshelf import bookshelf_bp
from controllers.dashboard import dashboard_bp
from controllers.datasources import datasources_bp
from controllers.data_permissions import data_permissions_bp
from controllers.dataset_transforms import dataset_transform_bp
from controllers.feishu_sync import feishu_bp
from controllers.feature_flags import feature_flags_bp
from controllers.ask_flow import ask_flow_bp
from controllers.advanced_capabilities import advanced_capabilities_bp
from controllers.smart_chat import smart_chat_bp
from controllers.report_config import report_config_bp
from controllers.runtime_migration import runtime_migration_bp
from controllers.system_logs import system_logs_bp
from controllers.rbac import rbac_bp
from controllers.organization_trees import organization_trees_bp
from feature_flags import ensure_feature_flags
from auth_store import get_current_user
from system_log_store import log_event, request_snapshot


init_default_configs()
ensure_feature_flags()
APP_CONFIG = get_app_config()
BACKEND_PORT = int(APP_CONFIG.get("port") or os.getenv("SMARTASK_BACKEND_PORT", "5002"))

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
# 历史快照 rows 等 dict 必须保持原始列序返回：
# jsonify 默认按字母序重排键，会把「上级名称」排到「节点名称」前，
# 导致前端按键序找名称列时恢复历史后显示上级组织名而不是节点名。
app.json.sort_keys = False
app.json.ensure_ascii = False
app.secret_key = str(APP_CONFIG.get("secret_key") or decrypt_secret_value(os.getenv("SMARTASK_SECRET_KEY", "vanna-local-secret-2026")))

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    os.getenv("FRONTEND_URL", ""),
    os.getenv("BACKEND_URL", ""),
    os.getenv("SMARTASK_FRONTEND_URL", ""),
    os.getenv("SMARTASK_BACKEND_URL", ""),
]

CORS(
    app,
    origins=[origin for origin in CORS_ORIGINS if origin],
    supports_credentials=True,
)

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(datasources_bp)
app.register_blueprint(data_permissions_bp)
app.register_blueprint(dataset_transform_bp)
app.register_blueprint(ai_models_bp)
app.register_blueprint(feishu_bp)
app.register_blueprint(smart_chat_bp)
app.register_blueprint(bookshelf_bp)
app.register_blueprint(agents_bp)
app.register_blueprint(report_config_bp)
app.register_blueprint(runtime_migration_bp)
app.register_blueprint(feature_flags_bp)
app.register_blueprint(ask_flow_bp)
app.register_blueprint(advanced_capabilities_bp)
app.register_blueprint(system_logs_bp)
app.register_blueprint(rbac_bp)
app.register_blueprint(organization_trees_bp)


def _skip_access_log(path: str) -> bool:
    return (
        not path.startswith("/api/")
        or path == "/api/health"
        or path == "/api/auth/me"
        or path == "/api/feature-flags"
        or path.startswith("/api/admin/system-logs")
    )


def _http_error_guidance(path: str, status_code: int, error_message: str) -> dict:
    if path.startswith("/api/bookshelves/datasets/generate-from-prompt"):
        return {
            "event_name": "提示词生成数据集接口失败",
            "what_happened": "前端请求后端根据大段提示词生成新数据集，但接口返回失败。",
            "suggested_action": "检查默认 AI 模型/API Key、模型服务是否可用、提示词是否过长；如果是 404，重启后端让新路由生效。",
            "code_hint": "backend/controllers/bookshelf.py::generate_bookshelf_dataset_from_prompt；backend/dataset_copilot/payload_generator.py。",
        }
    if "/full" in path and path.startswith("/api/bookshelves/datasets/"):
        return {
            "event_name": "数据集书架保存失败",
            "what_happened": "数据集基础信息可能已创建，但 LLD、DDL、字段字典、Golden SQL 或 Agent Prompt 保存失败。",
            "suggested_action": "查看返回 details，重点检查 schema_definition.source_id、agent_prompts 是否包含 Agent1-4、Golden SQL 是否至少 3 条。",
            "code_hint": "backend/controllers/bookshelf.py::save_bookshelf_dataset_full 和 _validate_full_payload。",
        }
    if path.startswith("/api/admin/system-logs"):
        return {
            "event_name": "日志管理接口失败",
            "what_happened": "控制台日志列表、统计或详情接口返回失败。",
            "suggested_action": "确认当前账号是超管；如果是 500，检查 system_event_logs 表或数据库连接。",
            "code_hint": "backend/controllers/system_logs.py；backend/system_log_store.py。",
        }
    if status_code == 404:
        return {
            "event_name": "接口不存在",
            "what_happened": "前端访问了后端没有注册的 API。",
            "suggested_action": "确认后端已重启并加载最新代码；核对 frontend/src/api/index.js 中的路径和 backend/app.py 蓝图注册。",
            "code_hint": "backend/app.py 的 register_blueprint；对应 controllers/*.py 路由。",
        }
    if status_code == 403:
        return {
            "event_name": "权限不足",
            "what_happened": "当前登录身份没有访问这个接口的权限。",
            "suggested_action": "切换超管账号，或到系统控制台检查对应功能权限。",
            "code_hint": "backend/auth_store.py；backend/controllers/feature_flags.py；前端路由权限配置。",
        }
    return {
        "event_name": "接口报错",
        "what_happened": f"接口返回 HTTP {status_code}。{error_message or ''}".strip(),
        "suggested_action": "先看详细报错和请求路径，再到对应 controller 搜索该路径定位代码。",
        "code_hint": "backend/controllers 下对应路由文件；frontend/src/api/index.js 对应调用。",
    }


@app.before_request
def _mark_request_start():
    request._smartask_started_at = time.time()


@app.after_request
def _record_access_log(response):
    path = request.path or ""
    if _skip_access_log(path):
        return response
    try:
        duration_ms = int((time.time() - getattr(request, "_smartask_started_at", time.time())) * 1000)
        status_code = int(response.status_code or 0)
        if status_code >= 400 and getattr(request, "_smartask_event_logged", False):
            return response
        if status_code >= 400:
            category = "error"
            level = "error" if status_code >= 500 else "warning"
            event_type = "http_error"
            error_message = (response.get_json(silent=True) or {}).get("error", "") if response.is_json else ""
            guidance = _http_error_guidance(path, status_code, error_message)
            title = guidance["event_name"]
        else:
            category = "access"
            level = "info"
            event_type = "api_access"
            title = f"{request.method} {path}"
            error_message = ""
            guidance = {
                "event_name": "接口访问",
                "what_happened": "接口请求成功。",
                "suggested_action": "",
                "code_hint": "",
            }
        log_event(
            category=category,
            event_type=event_type,
            level=level,
            title=title,
            user=get_current_user(),
            request_info=request_snapshot(request),
            status_code=status_code,
            duration_ms=duration_ms,
            error_message=error_message,
            details={
                **guidance,
                "endpoint": request.endpoint or "",
                "request_args": request.args.to_dict(flat=True),
            },
        )
    except Exception:
        pass
    return response


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify(
        {
            "status": "running",
            "message": "smart analytics backend is running",
            "version": "2.0.0",
        }
    )


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "API not found", "detail": str(error)}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed", "detail": str(error)}), 405


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error", "detail": str(error)}), 500


def _start_feishu_sync_scheduler():
    """后台守护线程启动飞书同步调度器，不阻塞Flask主线程"""
    try:
        from feishu_sync_service import sync_service
        print("启动飞书同步调度器后台线程...")
        sync_service.start_scheduler()
    except Exception as e:
        print(f"飞书同步调度器启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 启动飞书同步后台调度线程（守护线程，随Flask进程退出）
    feishu_sync_thread = threading.Thread(target=_start_feishu_sync_scheduler, daemon=True)
    feishu_sync_thread.start()

    print("=" * 60)
    print(f"Smart analytics backend starting at http://localhost:{BACKEND_PORT}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=BACKEND_PORT, debug=False, use_reloader=False)
