"""
Report Config API Blueprint — GET / PUT / DELETE for dataset report configuration.
"""

from flask import Blueprint, jsonify, request
import dataset_report_config as drc

report_config_bp = Blueprint("report_config", __name__, url_prefix="/api")


@report_config_bp.route("/datasets/<int:dataset_id>/report-config", methods=["GET"])
def get_report_config(dataset_id):
    cfg = drc.get_config(dataset_id)
    if cfg is None:
        return jsonify({"config": None, "is_default": True, "default_config": drc.get_default_config()})
    return jsonify({"config": cfg, "is_default": False})


@report_config_bp.route("/datasets/<int:dataset_id>/report-config", methods=["PUT"])
def upsert_report_config(dataset_id):
    body = request.get_json(force=True)
    config_json = body.get("config")
    if not config_json or not isinstance(config_json, dict):
        return jsonify({"error": "config must be a JSON object"}), 400
    ok = drc.upsert_config(dataset_id, config_json)
    if ok:
        return jsonify({"message": "saved"})
    return jsonify({"error": "save failed"}), 500


@report_config_bp.route("/datasets/<int:dataset_id>/report-config", methods=["DELETE"])
def delete_report_config(dataset_id):
    drc.delete_config(dataset_id)
    return jsonify({"message": "deleted"})


@report_config_bp.route("/report-config/default", methods=["GET"])
def get_default_config():
    return jsonify({"config": drc.get_default_config()})
