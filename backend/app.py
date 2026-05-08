"""
Application entry for the smart analytics backend.
"""

import os
import sys

from flask import Flask, jsonify
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
from controllers.ai_models import ai_models_bp
from controllers.agents import agents_bp
from controllers.auth import auth_bp
from controllers.bookshelf import bookshelf_bp
from controllers.dashboard import dashboard_bp
from controllers.datasources import datasources_bp
from controllers.feishu_sync import feishu_bp
from controllers.smart_chat import smart_chat_bp
from controllers.report_config import report_config_bp
from controllers.runtime_migration import runtime_migration_bp


init_default_configs()
APP_CONFIG = get_app_config()
BACKEND_PORT = int(APP_CONFIG.get("port") or os.getenv("SMARTASK_BACKEND_PORT", "5002"))

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.secret_key = str(APP_CONFIG.get("secret_key") or os.getenv("SMARTASK_SECRET_KEY", "vanna-local-secret-2026"))

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
app.register_blueprint(ai_models_bp)
app.register_blueprint(feishu_bp)
app.register_blueprint(smart_chat_bp)
app.register_blueprint(bookshelf_bp)
app.register_blueprint(agents_bp)
app.register_blueprint(report_config_bp)
app.register_blueprint(runtime_migration_bp)


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


if __name__ == "__main__":
    print("=" * 60)
    print(f"Smart analytics backend starting at http://localhost:{BACKEND_PORT}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=BACKEND_PORT, debug=False, use_reloader=False)
