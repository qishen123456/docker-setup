"""
语音转文字控制器（ASR）
GET  /api/asr/config      - 查询语音输入是否启用（前端决定是否渲染麦克风按钮）
POST /api/asr/transcribe  - 语音转文字（当前 provider=feishu，走飞书文件识别接口）

设计说明（docs/voice-input-design-2026-08-26.md）：
- 纯增量模块，不侵入问数主链路；provider 做成配置项，将来可换 OpenAI 兼容转录/私有化 FunASR
- 飞书 file_recognize 只收 16k PCM（base64 放在 JSON body），前端用 AudioWorklet 直接采 PCM
- 踩坑记录：config.file_id 不能太短（实测 "test001" 报 1040101 invalid param，16 位随机串正常）
"""

import base64
import threading
import time
import uuid

import requests
from flask import Blueprint, jsonify, request

from config_manager import read_json
from security import require_login

asr_bp = Blueprint('asr', __name__)

FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_FILE_RECOGNIZE_URL = "https://open.feishu.cn/open-apis/speech_to_text/v1/speech/file_recognize"

# tenant_access_token 有效期 2 小时，模块级缓存（与项目现有单例风格一致）
_token_cache = {"token": "", "expires_at": 0.0}
_token_lock = threading.Lock()


def _asr_settings():
    cfg = read_json('asr_settings.json') or {}
    return cfg


def _get_tenant_token(cfg):
    with _token_lock:
        now = time.time()
        if _token_cache["token"] and now < _token_cache["expires_at"]:
            return _token_cache["token"], None
        app_id = str(cfg.get('app_id') or '').strip()
        secret_b64 = str(cfg.get('app_secret_b64') or '').strip()
        if not app_id or not secret_b64:
            return None, "语音服务未配置应用凭证"
        try:
            secret = base64.b64decode(secret_b64).decode('utf-8')
        except Exception:
            return None, "语音服务凭证配置错误"
        try:
            resp = requests.post(
                FEISHU_TOKEN_URL,
                json={"app_id": app_id, "app_secret": secret},
                timeout=15,
            )
            data = resp.json()
        except Exception as e:
            return None, f"获取飞书访问令牌失败: {e}"
        if data.get("code") != 0:
            return None, f"获取飞书访问令牌失败: {data.get('msg')}"
        token = data.get("tenant_access_token") or ""
        # 官方有效期 2h，提前 5 分钟刷新
        _token_cache["token"] = token
        _token_cache["expires_at"] = now + max(0, int(data.get("expire") or 7200) - 300)
        return token, None


@asr_bp.route('/api/asr/config', methods=['GET'])
def asr_config():
    _, denied = require_login()
    if denied:
        return denied
    cfg = _asr_settings()
    return jsonify({
        "enabled": bool(cfg.get('enabled')),
        "max_duration_sec": int(cfg.get('max_duration_sec') or 60),
    })


@asr_bp.route('/api/asr/transcribe', methods=['POST'])
def asr_transcribe():
    _, denied = require_login()
    if denied:
        return denied

    cfg = _asr_settings()
    if not cfg.get('enabled'):
        return jsonify({"error": "语音输入未启用"}), 403

    data = request.get_json(silent=True) or {}
    audio_b64 = str(data.get('audio_b64') or '')
    audio_format = str(data.get('format') or 'pcm').strip().lower()
    if not audio_b64:
        return jsonify({"error": "音频内容为空"}), 400
    if audio_format not in ("pcm", "wav"):
        return jsonify({"error": "不支持的音频格式"}), 400

    max_kb = int(cfg.get('max_audio_kb') or 3072)
    # base64 膨胀系数约 4/3
    if len(audio_b64) > max_kb * 1024 * 4 // 3:
        return jsonify({"error": f"音频超过 {max_kb}KB 限制"}), 400

    token, err = _get_tenant_token(cfg)
    if err:
        return jsonify({"error": err}), 502

    body = {
        "speech": {"speech": audio_b64},
        "config": {
            # file_id 长度限制 16 位：太短或 uuid 全 32 位都报 1040101 invalid param（2026-08-26/27 实测）
            "file_id": uuid.uuid4().hex[:16],
            "format": audio_format,
            "engine_type": "16k_auto",
        },
    }
    try:
        resp = requests.post(
            FEISHU_FILE_RECOGNIZE_URL,
            json=body,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        data = resp.json()
    except Exception as e:
        return jsonify({"error": f"语音识别服务异常: {e}"}), 502

    if data.get("code") != 0:
        return jsonify({"error": f"语音识别失败: {data.get('msg') or data.get('code')}"}), 502

    text = ((data.get("data") or {}).get("recognition_text") or "").strip()
    return jsonify({"text": text})
