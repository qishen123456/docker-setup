# -*- coding: utf-8 -*-
"""
影子守门员（Shadow Gatekeeper）—— 澄清方案 v4 / P-1 阶段。

只做一件事：在用户无感知的前提下，用独立小模型评估"这个问题若守门员在场会不会拦"，
把判定写入 config/shadow_gatekeeper_log.jsonl，供 1~2 周后离线分析
（误拦率 / 置信度校准 / 真歧义捕获率，见 clarification-design.md 9.1-B3 门槛）。

硬约束（对应方案 9.1-B1 三条红线）：
  1. 禁复用主链路 _chat / 候选模型轮询——这里独立构造 OpenAI client，锁单个模型；
  2. 禁共享 _preferred_model_id 单例——本模块不触碰 FourAgentAskService 任何实例状态；
  3. 必须 fail-open——任何异常（含模型超时/JSON 解析失败/配置缺失）都只记日志，绝不抛出。

用户侧零影响：调用方拿到的是 schedule_shadow_log()，内部 daemon 线程异步执行，
不阻塞问数主流程；即使线程内全部失败，主流程也没有任何感知。

注：user_reasked_within_30s（用户 30s 内改问=可能答错的纠正信号）由离线分析时
按 session_id + timestamp 相邻记录计算，日志侧不实时标注。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_DIR = os.path.join(BACKEND_DIR, "..", "config")

PROMPT_VERSION = "gk-v1"

_SETTINGS_PATH = os.path.join(CONFIG_DIR, "gatekeeper_settings.json")
_NODE_INDEX_PATH = os.path.join(CONFIG_DIR, "dataset_node_index.json")
_AI_SETTINGS_PATH = os.path.join(CONFIG_DIR, "ai_settings.json")

_file_lock = threading.Lock()

_SYSTEM_PROMPT = """你是智能问数系统的"问题理解守门员"。给你用户原始问题和该数据集的书架摘要（组织节点别名、可用指标、层级、业务口径），你要判断：这个问题能否被明确理解并直接作答。

只允许输出 JSON（不要输出任何其他文字）：
{
  "action": "pass" | "suggest" | "block",
  "confidence": 0.0~1.0,
  "reason": "一句话理由",
  "candidates": ["备选理解1", "备选理解2"]
}

判定标准：
- pass：理解唯一明确（含对比、排名、筛选、追问等正常问法），直接作答。大多数问题应是 pass。
- suggest：能给出一种最合理解释，但存在另一种合理理解（如"最不好的还有第二不好的"→最差1家还是末2家）。candidates 给备选理解。
- block：完全无法理解，任何解释都给不出合理结果（乱码、主体残缺到无法定位）。candidates 给可能的补全方向。
- 实体名必须与书架别名表对应；指标必须在书架指标清单内。数据集里没有的口径不要编。
- 错字纠正：若疑似错字能在别名表中找到近音/近形候选，action=suggest 并在 candidates 中给出纠正后的问题。
- 数据集已有默认口径时，泛指词按默认口径理解：书架定义了主指标（如默认"业绩"=达成率）时，"业绩如何""情况怎么样"这类泛词判 pass，不要为泛词本身弹 suggest。
- confidence 表示你对 action 判断的把握，不是对答案的把握。"""


def _load_settings() -> Dict[str, Any]:
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _load_bookshelf_summary(dataset_ids: List[int], all_datasets: bool = False) -> str:
    """从书架资产（节点索引 + 报告配置）拼一段摘要喂给守门员。失败返回空串。

    all_datasets=True 时别名表扩到全部数据集（按数据集名分组标注）——
    用于路由落空（0 行结果）的错字纠正：错字可能导致路由选错数据集，
    只在被路由的数据集里找候选永远纠不回来（2026-08-28 "商泳事业部"实测）。
    """
    parts: List[str] = []
    try:
        with open(_NODE_INDEX_PATH, "r", encoding="utf-8") as fh:
            index = json.load(fh)
        for ds in index.get("datasets") or []:
            if not all_datasets and ds.get("dataset_id") not in (dataset_ids or []):
                continue
            aliases: List[str] = []
            for node in ds.get("nodes") or []:
                aliases.extend(str(a) for a in (node.get("aliases") or []) if a)
            if aliases:
                label = str(ds.get("dataset_name") or ds.get("dataset_id") or "")
                if all_datasets:
                    parts.append(f"组织节点别名表（{label}）：" + "、".join(aliases[:60]))
                else:
                    parts.append("组织节点别名表：" + "、".join(aliases[:60]))
    except Exception:
        pass
    try:
        import sys
        if BACKEND_DIR not in sys.path:
            sys.path.insert(0, BACKEND_DIR)
        from dataset_report_config import get_config
        for ds_id in (dataset_ids or [])[:1]:
            cfg = get_config(int(ds_id))
            if not cfg:
                continue
            metrics = [str(m.get("label") or m.get("column") or "") for m in (cfg.get("metrics") or [])]
            levels = [str(l.get("name") or "") for l in (cfg.get("levels") or [])]
            biz = str(cfg.get("businessContext") or "")[:400]
            if metrics:
                parts.append("可用指标：" + "、".join(m for m in metrics if m))
            if levels:
                parts.append("层级：" + "、".join(l for l in levels if l))
            if biz:
                parts.append("业务口径：" + biz)
    except Exception:
        pass
    return "\n".join(parts)


def _load_model_config(model_id: int) -> Optional[Dict[str, Any]]:
    try:
        with open(_AI_SETTINGS_PATH, "r", encoding="utf-8") as fh:
            settings = json.load(fh)
        import sys
        if BACKEND_DIR not in sys.path:
            sys.path.insert(0, BACKEND_DIR)
        from config_manager import decode_secret
        for item in settings.get("models") or []:
            if item.get("id") == model_id and item.get("is_active"):
                config = dict(item)
                config["api_key"] = decode_secret(str(config.pop("api_key_b64", "") or ""))
                return config
    except Exception:
        pass
    return None


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        import re
        match = re.search(r"\{[\s\S]*\}", text or "")
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return None


def _call_gatekeeper(question: str, bookshelf: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """同步调用守门员模型。返回结构化判定；任何失败转异常由上层 fail-open 捕获。"""
    from openai import OpenAI

    model_id = int(settings.get("model_id") or 0)
    model_cfg = _load_model_config(model_id)
    if not model_cfg:
        raise RuntimeError(f"gatekeeper model_id={model_id} not found or inactive")

    timeout = float(settings.get("timeout_seconds") or 4)
    max_tokens = int(settings.get("max_tokens") or 256)
    client = OpenAI(
        api_key=model_cfg.get("api_key") or "",
        base_url=model_cfg.get("base_url") or "https://api.openai.com/v1",
        timeout=timeout,
        max_retries=0,  # B1：零重试
    )
    user_prompt = f"用户问题：{question}\n\n书架摘要：\n{bookshelf or '（无书架信息）'}"
    # reasoning 模型（MiniMax 系）思考会烧 max_tokens 导致正文截断/为空——
    # 若模型配置开了 reasoning_split（如 MiniMax-M3 官方），思考分流到 reasoning_details，正文干净（2026-08-28）。
    extra_body = {"reasoning_split": True} if model_cfg.get("reasoning_split") else None
    resp = client.chat.completions.create(
        model=model_cfg.get("model") or "",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        stream=False,
        max_tokens=max_tokens,
        temperature=0,
        extra_body=extra_body,
    )
    content = (resp.choices[0].message.content or "").strip()
    parsed = _extract_json(content)
    if not parsed:
        raise RuntimeError(f"gatekeeper returned non-JSON: {content[:120]}")
    return parsed


def _append_log(record: Dict[str, Any], log_path: str) -> None:
    line = json.dumps(record, ensure_ascii=False)
    with _file_lock:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def run_shadow_log(
    question: str,
    result: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    session_id: str = "",
) -> None:
    """同步执行影子判定并写日志。任何异常吞掉（fail-open）。"""
    settings = _load_settings()
    if not settings.get("enabled"):
        return
    log_path = str(settings.get("log_path") or os.path.join(CONFIG_DIR, "shadow_gatekeeper_log.jsonl"))
    started = time.time()
    route = (result or {}).get("route") or {}
    dataset_ids = route.get("dataset_ids") or []
    record: Dict[str, Any] = {
        "question": question,
        "session_id": session_id or "",
        "user_id": str((user or {}).get("username") or (user or {}).get("id") or ""),
        "timestamp": int(started),
        "dataset_id": (dataset_ids or [None])[0],
        "intent_parse": {
            "intent": route.get("intent"),
            "refined_query": route.get("refined_query"),
            "requires_confirmation": bool(route.get("requires_confirmation")),
        },
        "prompt_version": PROMPT_VERSION,
        "sql_status": "error" if (result or {}).get("error") else "ok",
        "rows_returned": int((result or {}).get("row_count") or 0),
        "model_id": settings.get("model_id"),
        "gk_status": "ok",
        "gk_latency_ms": 0,
    }
    try:
        bookshelf = _load_bookshelf_summary([int(d) for d in dataset_ids if d])
        parsed = _call_gatekeeper(question, bookshelf, settings)
        action = str(parsed.get("action") or "pass").strip().lower()
        record.update(
            {
                "would_block": action in ("suggest", "block"),
                "block_reason": str(parsed.get("reason") or "")[:200],
                "self_confidence": parsed.get("confidence"),
                "candidate_options_topN": [str(c)[:120] for c in (parsed.get("candidates") or [])][:3],
                "gk_action": action,
            }
        )
    except Exception as exc:  # fail-open：超时/解析失败/配置缺失都落日志
        record.update(
            {
                "would_block": None,
                "block_reason": "",
                "self_confidence": None,
                "candidate_options_topN": [],
                "gk_status": "error",
                "gk_error": str(exc)[:200],
            }
        )
    record["gk_latency_ms"] = int((time.time() - started) * 1000)
    try:
        _append_log(record, log_path)
    except Exception as exc:
        logger.warning("shadow gatekeeper log write failed: %s", exc)


def schedule_shadow_log(
    question: str,
    result: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    session_id: str = "",
) -> None:
    """入口：daemon 线程异步执行，主流程零阻塞。自身也绝不抛异常。"""
    try:
        settings = _load_settings()
        if not settings.get("enabled"):
            return
        # 需要 JSON 可序列化的轻量拷贝，避免线程持有主流程大对象
        safe_result = {
            "route": (result or {}).get("route") or {},
            "error": (result or {}).get("error"),
            "row_count": (result or {}).get("row_count"),
        }
        thread = threading.Thread(
            target=_safe_run,
            args=(str(question or ""), safe_result, dict(user or {}), str(session_id or "")),
            daemon=True,
            name="shadow-gatekeeper",
        )
        thread.start()
    except Exception as exc:
        logger.warning("shadow gatekeeper schedule failed: %s", exc)


def _safe_run(question: str, result: Dict[str, Any], user: Dict[str, Any], session_id: str) -> None:
    try:
        run_shadow_log(question, result, user=user, session_id=session_id)
    except Exception as exc:
        logger.warning("shadow gatekeeper run failed: %s", exc)


# ---------------------------------------------------------------------------
# 提前可见版纠正条（P0 预览，默认仅超管可见）
# 与影子模式共用同一个守门员调用，差别：同步执行、把判定附加到结果里给前端渲染。
# 依旧 fail-open：任何异常返回 None，前端就当没有纠正条。
# ---------------------------------------------------------------------------

def is_visible_user(user: Optional[Dict[str, Any]] = None) -> bool:
    """当前用户是否在纠正条可见角色内（控制器据此决定走同步可见路径还是异步影子路径）。"""
    try:
        settings = _load_settings()
        if not settings.get("visible_enabled"):
            return False
        roles = set(settings.get("visible_roles") or [])
        return not roles or str((user or {}).get("role") or "") in roles
    except Exception:
        return False


def build_correction(
    question: str,
    result: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    session_id: str = "",
) -> Optional[Dict[str, Any]]:
    """若当前用户在 visible_roles 内且守门员判定 suggest/block，返回纠正条数据，否则 None。

    可见路径自身也写影子日志（gk_source=inline_visible），因此控制器对可见用户
    不应再调 schedule_shadow_log——一次提问只调一次守门员，避免并发双调撞 429 限流。
    """
    settings = _load_settings()
    started = time.time()
    parsed: Optional[Dict[str, Any]] = None
    gk_error = ""
    try:
        if not is_visible_user(user):
            return None
        if (result or {}).get("error"):
            return None
        route = (result or {}).get("route") or {}
        # B2 仲裁：本轮已有阻断式确认时，不叠加纠正条
        if route.get("requires_confirmation"):
            return None
        # 注意：不能用 row_count>0 做门槛——错字题恰恰大多返回 0 行（"未查询到匹配数据"），
        # 那正是纠正条最有价值的场景（2026-08-28 实测"商泳事业部业绩"被此门槛误杀）。

        dataset_ids = [int(d) for d in (route.get("dataset_ids") or []) if d]
        # 0 行结果（路由很可能被错字带偏）→ 书架扩到全部数据集别名，让纠正能跨数据集找回正确实体
        no_rows = not (result or {}).get("row_count")
        bookshelf = _load_bookshelf_summary(dataset_ids, all_datasets=no_rows)
        parsed = _call_gatekeeper(question, bookshelf, settings)
        action = str(parsed.get("action") or "pass").strip().lower()
        candidates = [str(c).strip() for c in (parsed.get("candidates") or []) if str(c).strip()][:3]
        if action not in ("suggest", "block") or not candidates:
            return None

        interpretation = str(route.get("refined_query") or question or "").strip()
        return {
            "action": action,
            "interpretation": interpretation,
            "reason": str(parsed.get("reason") or "")[:200],
            "candidates": candidates,
            "confidence": parsed.get("confidence"),
        }
    except Exception as exc:
        gk_error = str(exc)[:200]
        logger.warning("build_correction failed (fail-open): %s", exc)
        return None
    finally:
        # 可见路径的影子日志（与 run_shadow_log 同字段，多一个 gk_source 标记）
        try:
            if settings.get("enabled") and is_visible_user(user):
                route = (result or {}).get("route") or {}
                action = str((parsed or {}).get("action") or "").lower() if parsed else ""
                record = {
                    "question": question,
                    "session_id": session_id or "",
                    "user_id": str((user or {}).get("username") or (user or {}).get("id") or ""),
                    "timestamp": int(started),
                    "dataset_id": ((route.get("dataset_ids") or [None])[0]),
                    "intent_parse": {
                        "intent": route.get("intent"),
                        "refined_query": route.get("refined_query"),
                        "requires_confirmation": bool(route.get("requires_confirmation")),
                    },
                    "prompt_version": PROMPT_VERSION,
                    "sql_status": "error" if (result or {}).get("error") else "ok",
                    "rows_returned": int((result or {}).get("row_count") or 0),
                    "model_id": settings.get("model_id"),
                    "gk_source": "inline_visible",
                    "gk_latency_ms": int((time.time() - started) * 1000),
                    "gk_status": "ok" if parsed else "error",
                    "gk_action": action or None,
                    "gk_error": gk_error or None,
                    "would_block": (action in ("suggest", "block")) if parsed else None,
                    "block_reason": str((parsed or {}).get("reason") or "")[:200] if parsed else "",
                    "self_confidence": (parsed or {}).get("confidence") if parsed else None,
                    "candidate_options_topN": [str(c)[:120] for c in ((parsed or {}).get("candidates") or [])][:3],
                }
                log_path = str(settings.get("log_path") or os.path.join(CONFIG_DIR, "shadow_gatekeeper_log.jsonl"))
                _append_log(record, log_path)
        except Exception:
            pass
