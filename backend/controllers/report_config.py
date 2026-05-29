"""
Report Config API Blueprint — GET / PUT / DELETE for dataset report configuration.
"""

from flask import Blueprint, jsonify, request
import dataset_report_config as drc
from security import require_feature

report_config_bp = Blueprint("report_config", __name__, url_prefix="/api")


@report_config_bp.route("/datasets/<int:dataset_id>/report-config", methods=["GET"])
def get_report_config(dataset_id):
    _, denied = require_feature("report_config", "当前账号没有查看报告模板配置权限")
    if denied:
        return denied
    cfg = drc.get_config(dataset_id)
    if cfg is None:
        return jsonify({"config": None, "is_default": True, "default_config": drc.get_default_config()})
    return jsonify({"config": cfg, "is_default": False})


@report_config_bp.route("/datasets/<int:dataset_id>/report-config", methods=["PUT"])
def upsert_report_config(dataset_id):
    _, denied = require_feature("report_template_edit", "当前账号没有编辑报告模板权限")
    if denied:
        return denied
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
    _, denied = require_feature("report_template_delete", "当前账号没有删除报告模板权限")
    if denied:
        return denied
    drc.delete_config(dataset_id)
    return jsonify({"message": "deleted"})


@report_config_bp.route("/report-config/default", methods=["GET"])
def get_default_config():
    _, denied = require_feature("report_config", "当前账号没有查看报告模板配置权限")
    if denied:
        return denied
    return jsonify({"config": drc.get_default_config()})
