"""
Application entry for the smart analytics backend.
"""

import os
import sys

from flask import Flask, jsonify
from flask_cors import CORS

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config_manager import init_default_configs
from controllers.ai_models import ai_models_bp
from controllers.agents import agents_bp
from controllers.bookshelf import bookshelf_bp
from controllers.dashboard import dashboard_bp
from controllers.datasources import datasources_bp
from controllers.feishu_sync import feishu_bp
from controllers.smart_chat import smart_chat_bp


init_default_configs()

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

CORS(
    app,
    origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
)

app.register_blueprint(dashboard_bp)
app.register_blueprint(datasources_bp)
app.register_blueprint(ai_models_bp)
app.register_blueprint(feishu_bp)
app.register_blueprint(smart_chat_bp)
app.register_blueprint(bookshelf_bp)
app.register_blueprint(agents_bp)


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
    print("Smart analytics backend starting at http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
