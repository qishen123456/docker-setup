# -*- coding: utf-8 -*-
"""结构化解析条聚合（parse-bar-design.md v1，响应层拼装，fail-open）。

把问句解析结果透给用户：数据集 / 对象 / 指标 三槽位 + 原句 span 定位（框选片段用）。
不进流水线、不改任何路由决策——纯响应层只读聚合，任何异常返回 None。

span 定位三来源（§3.2）：
  1. typo 滑窗 offset（Phase 0.1 透出，错字纠正场景）
  2. 书架别名 find()（matched_phrase 找不到时，用 flat_alias_index 反查该节点别名）
  3. resolved_entities.matched_phrase（优先，是消解器实际命中的片段）
红线：定位失败即丢弃该 span，宁可缺不可错框；弃用 LLM 返回 span（幻觉不可靠）。

多轮追问（§3.5）：实体来自上下文继承、原句无字面出现时，标 inherited=True，
不硬找 span（"继承自上文"），覆盖率验收分母仅统计有 dataset_results 的消息。

出条铁律（§1.3）：触发确认卡/纠正卡/early_clarify/错误的消息不出解析条。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(CURRENT_DIR, "..", "..", "config")
_SETTINGS_PATH = os.path.join(CONFIG_DIR, "parse_bar_settings.json")
_NODE_INDEX_PATH = os.path.join(CONFIG_DIR, "dataset_node_index.json")

_settings_cache: Dict[str, Any] = {"mtime": 0.0, "data": {}}
_alias_cache: Dict[str, Any] = {"mtime": 0.0, "by_node": {}}


def _load_settings() -> Dict[str, Any]:
    """读 parse_bar_settings.json，mtime 缓存。任何失败返回 {"enabled": False}。"""
    try:
        mtime = os.path.getmtime(_SETTINGS_PATH)
        if mtime != _settings_cache["mtime"]:
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as fh:
                _settings_cache["data"] = json.load(fh)
            _settings_cache["mtime"] = mtime
        return _settings_cache["data"]
    except Exception:
        return {"enabled": False}


def _load_alias_by_node() -> Dict[str, List[str]]:
    """flat_alias_index 反查表：node_name -> [别名...]（含节点全名），按别名长度降序。"""
    try:
        mtime = os.path.getmtime(_NODE_INDEX_PATH)
        if mtime != _alias_cache["mtime"]:
            with open(_NODE_INDEX_PATH, "r", encoding="utf-8") as fh:
                index = json.load(fh)
            by_node: Dict[str, List[str]] = {}
            for entry in index.get("flat_alias_index") or []:
                alias = str(entry.get("alias") or "").strip()
                if not alias:
                    continue
                for m in entry.get("matches") or []:
                    node = str(m.get("node_name") or "").strip()
                    if node:
                        by_node.setdefault(node, [])
                        if alias not in by_node[node]:
                            by_node[node].append(alias)
            for node in by_node:
                by_node[node].sort(key=len, reverse=True)  # 长别名优先（先框"南部分公司"再框"南部"）
            _alias_cache["by_node"] = by_node
            _alias_cache["mtime"] = mtime
        return _alias_cache["by_node"]
    except Exception:
        return _alias_cache.get("by_node") or {}


def is_enabled() -> bool:
    try:
        return bool(_load_settings().get("enabled"))
    except Exception:
        return False


def is_visible_user(user: Optional[Dict[str, Any]] = None) -> bool:
    """当前用户是否在解析条可见角色内。fail-closed：读不到配置不显示（宁可缺）。"""
    try:
        roles = set(_load_settings().get("visible_roles") or [])
        return bool(roles) and str((user or {}).get("role") or "") in roles
    except Exception:
        return False


def _find_unoccupied(question: str, needle: str, occupied: List[tuple]) -> Optional[tuple]:
    """在 question 里找 needle，跳过与已占用区间重叠的位置。返回 (start, end) 或 None。"""
    try:
        if not needle:
            return None
        start = 0
        while True:
            pos = question.find(needle, start)
            if pos < 0:
                return None
            end = pos + len(needle)
            if not any(pos < e and end > s for s, e in occupied):
                return (pos, end)
            start = pos + 1
    except Exception:
        return None


def _extract_node_slots(question: str, dsr0: Dict[str, Any]) -> List[Dict[str, Any]]:
    """对象槽：resolved_entities → members。span 定位：matched_phrase → 别名反查 → 继承。"""
    slots: List[Dict[str, Any]] = []
    occupied: List[tuple] = []
    re_ = dsr0.get("resolved_entities") or {}
    by_node = _load_alias_by_node()
    for ent in re_.get("entities") or []:
        if not isinstance(ent, dict):
            continue
        matched_phrase = str(ent.get("matched_phrase") or "").strip()
        for member in ent.get("members") or []:
            member = str(member or "").strip()
            if not member:
                continue
            slot: Dict[str, Any] = {"slot": "node", "resolved_value": member, "confidence": re_.get("confidence")}
            span = None
            # 来源 3：matched_phrase 优先（消解器实际命中的片段，可能等于节点全名）
            if matched_phrase:
                span = _find_unoccupied(question, matched_phrase, occupied)
            # 来源 2：书架别名反查（matched_phrase 是解析后全名，原句里可能是别名"南部"）
            if span is None:
                for alias in by_node.get(member) or []:
                    span = _find_unoccupied(question, alias, occupied)
                    if span:
                        break
            if span is not None:
                slot["span_text"] = question[span[0]:span[1]]
                slot["start"], slot["end"] = span
                occupied.append(span)
            else:
                # §3.5：原句无字面出现 → 上下文继承，不硬找 span
                slot["inherited"] = True
            slots.append(slot)
    return slots


def _extract_metric_slot(question: str, occupied: List[tuple]) -> Optional[Dict[str, Any]]:
    """指标槽：保守词表 find（长词优先），find 不到不显示该槽。"""
    aliases = _load_settings().get("metric_aliases") or {}
    # 长词优先（"开单金额"先于"金额"命中）
    for word in sorted(aliases.keys(), key=len, reverse=True):
        span = _find_unoccupied(question, str(word), occupied)
        if span is not None:
            occupied.append(span)
            return {
                "slot": "metric",
                "resolved_value": str(aliases[word]),
                "span_text": question[span[0]:span[1]],
                "start": span[0],
                "end": span[1],
            }
    return None


def _build_text(dataset_names: List[str], node_values: List[str], metric_value: str, inherited_nodes: List[str]) -> str:
    """转述条文案（Power BI Q&A 式自然语言，非工程师语言）。"""
    parts: List[str] = []
    if dataset_names:
        parts.append("在[" + "、".join(dataset_names) + "]里")
    if node_values:
        text = "".join(parts) + "查[" + "、".join(node_values) + "]"
        if metric_value:
            text += "的[" + metric_value + "]"
        return "我理解为：" + text
    if metric_value:
        return "我理解为：" + "".join(parts) + "查[" + metric_value + "]"
    if parts:
        return "我理解为：" + "".join(parts) + "查询"
    return ""


def build_parse_bar(
    question: str,
    result: Optional[Dict[str, Any]] = None,
    user: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """聚合解析条。不满足出条条件或任何异常 → None（fail-open，主流程零感知）。"""
    try:
        if not is_enabled() or not is_visible_user(user):
            return None
        result = result or {}
        question = str(question or "").strip()
        if not question:
            return None
        # 出条铁律：确认卡/纠正卡/early_clarify/错误消息不出解析条（两套候选 UI 不同屏）
        route = result.get("route") or {}
        if result.get("error"):
            return None
        if result.get("requires_confirmation") or route.get("requires_confirmation"):
            return None
        if result.get("early_clarify") or result.get("clarify_suggestion"):
            return None
        dataset_results = [d for d in (result.get("dataset_results") or []) if isinstance(d, dict)]
        if not dataset_results:
            return None

        dsr0 = dataset_results[0]
        dataset_names = []
        for d in dataset_results:
            name = str(d.get("dataset_name") or "").strip()
            if name and name not in dataset_names:
                dataset_names.append(name)
        dataset_slots = [
            {"slot": "dataset", "resolved_value": name}  # 数据集名一般不出现原句，无 span
            for name in dataset_names
        ]

        node_slots = _extract_node_slots(question, dsr0)
        occupied = [(s["start"], s["end"]) for s in node_slots if s.get("start") is not None]
        metric_slot = _extract_metric_slot(question, occupied)
        slots = dataset_slots + node_slots + ([metric_slot] if metric_slot else [])
        if not slots:
            return None

        node_values = [s["resolved_value"] for s in node_slots]
        inherited_nodes = [s["resolved_value"] for s in node_slots if s.get("inherited")]
        text = _build_text(
            dataset_names,
            node_values,
            str(metric_slot["resolved_value"]) if metric_slot else "",
            inherited_nodes,
        )
        bar: Dict[str, Any] = {
            "text": text,
            "slots": slots,
            "spans": [s for s in slots if s.get("start") is not None],
            "source": "parse_bar",
        }
        if inherited_nodes:
            bar["inherited_note"] = "「" + "、".join(inherited_nodes) + "」继承自上文"
        return bar
    except Exception:
        return None  # fail-open：任何异常都不出条，主流程零感知


# ============ Phase 2：原位编辑（候选 + 编译重跑 + bar 改写） ============
# 实现机制（诚实偏离设计文档 §3.3 的说明）：不在 four_agent_ask 开结构化旁路，
# 改为「编译重跑 + 三重锚定」——把结构化修正编译成确定性问句（书架全名+标准词），
# 用 preferred_dataset_ids 锚定数据集，走正常 ask() 全流程。
# 等效达到文档目标：防 LLM 漂移（锚定后无解释空间）+ 权限过滤（ask() 全链路照常）；
# 同时零侵入上帝文件 four_agent_ask.py、不动 AskRequest 契约。

_datasets_cache: Dict[str, Any] = {"mtime": 0.0, "data": []}


def _load_datasets() -> List[Dict[str, Any]]:
    """dataset_node_index 的 datasets 结构（含 nodes），mtime 缓存。"""
    try:
        mtime = os.path.getmtime(_NODE_INDEX_PATH)
        if mtime != _datasets_cache["mtime"]:
            with open(_NODE_INDEX_PATH, "r", encoding="utf-8") as fh:
                index = json.load(fh)
            _datasets_cache["data"] = index.get("datasets") or []
            _datasets_cache["mtime"] = mtime
        return _datasets_cache["data"]
    except Exception:
        return _datasets_cache.get("data") or []


def node_belongs_to_dataset(node_name: str, dataset_id: int) -> bool:
    """书架归属校验（rerun 权限红线用）：node_name 是否为该数据集的节点。"""
    try:
        for ds in _load_datasets():
            if int(ds.get("dataset_id") or 0) != int(dataset_id):
                continue
            for n in ds.get("nodes") or []:
                if str(n.get("node_name") or "") == str(node_name):
                    return True
        return False
    except Exception:
        return False


def list_slot_candidates(
    slot: str,
    current_value: Any = None,
    dataset_id: Optional[int] = None,
    allowed_dataset_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """槽位候选（原位下拉用）。任何失败返回 []。

    - node：同数据集同 parent 同 level 的兄弟节点（书架第一层；拼音索引层 v2.5 再加）
    - dataset：用户有权限的数据集列表
    - metric：指标词表白名单值域（去重）
    """
    try:
        slot = str(slot or "")
        if slot == "node":
            if not dataset_id:
                return []
            current = str(current_value or "").strip()
            for ds in _load_datasets():
                if int(ds.get("dataset_id") or 0) != int(dataset_id):
                    continue
                nodes = ds.get("nodes") or []
                cur = next((n for n in nodes if str(n.get("node_name") or "") == current), None)
                if not cur:
                    return []
                level, parent = cur.get("node_level"), cur.get("parent_name")
                out = []
                for n in nodes:
                    name = str(n.get("node_name") or "")
                    if not name or name == current:
                        continue
                    if n.get("node_level") == level and n.get("parent_name") == parent:
                        out.append({"value": name, "label": name, "level": str(level or "")})
                return out
            return []
        if slot == "dataset":
            allowed = set(int(d) for d in (allowed_dataset_ids or []) if d)
            out = []
            for ds in _load_datasets():
                ds_id = int(ds.get("dataset_id") or 0)
                if allowed and ds_id not in allowed:
                    continue
                name = str(ds.get("dataset_name") or "").strip()
                if ds_id and name:
                    out.append({"value": ds_id, "label": name})
            return out
        if slot == "metric":
            seen, out = set(), []
            for v in (_load_settings().get("metric_aliases") or {}).values():
                v = str(v or "").strip()
                if v and v not in seen:
                    seen.add(v)
                    out.append({"value": v, "label": v})
            return out
        return []
    except Exception:
        return []


def compile_question(
    question: str,
    original_bar: Dict[str, Any],
    override: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """把单槽修正编译成确定性问句 + 数据集锚定。失败返回 None。

    返回 {"question": 编译后问句, "dataset_id": 锚定数据集}。
    - node/metric：原句 span 片段替换为 书架全名/标准指标词（确定性文本，路由规则直达）
    - dataset：问句不动，仅换锚定数据集（语义=确认卡换数据集）
    """
    try:
        question = str(question or "").strip()
        override = override or {}
        slot = str(override.get("slot") or "")
        new_value = override.get("new_value")
        bar = original_bar or {}
        slots = bar.get("slots") or []
        if slot == "dataset":
            ds_id = int(new_value)
            if ds_id <= 0:
                return None
            return {"question": question, "dataset_id": ds_id}
        if slot in ("node", "metric"):
            target = next((s for s in slots if s.get("slot") == slot and s.get("start") is not None), None)
            if not target:
                return None  # 继承槽位无 span，无法编译（前端应禁用此类槽的编辑）
            new_text = str(new_value or "").strip()
            if not new_text:
                return None
            start, end = int(target["start"]), int(target["end"])
            compiled = question[:start] + new_text + question[end:]
            ds_id = int(override.get("dataset_id") or 0) or None
            return {"question": compiled, "dataset_id": ds_id}
        return None
    except Exception:
        return None


def apply_override_to_bar(
    original_bar: Dict[str, Any],
    override: Dict[str, Any],
    new_dataset_name: str = "",
) -> Optional[Dict[str, Any]]:
    """原解析条应用单槽修正：spans 保留原句 offset，被改槽位标 corrected=True。"""
    try:
        bar = original_bar or {}
        override = override or {}
        slot = str(override.get("slot") or "")
        new_value = override.get("new_value")
        slots = []
        for s in bar.get("slots") or []:
            s2 = dict(s)
            if s2.get("slot") == slot:
                if slot == "dataset":
                    s2["resolved_value"] = str(new_dataset_name or new_value or "")
                else:
                    s2["resolved_value"] = str(new_value or "")
                s2["corrected"] = True
                s2.pop("inherited", None)
            slots.append(s2)
        if not slots:
            return None
        dataset_names = [s["resolved_value"] for s in slots if s.get("slot") == "dataset"]
        node_values = [s["resolved_value"] for s in slots if s.get("slot") == "node"]
        metric_value = next((str(s["resolved_value"]) for s in slots if s.get("slot") == "metric"), "")
        new_bar: Dict[str, Any] = {
            "text": _build_text(dataset_names, node_values, metric_value, []),
            "slots": slots,
            "spans": [s for s in slots if s.get("start") is not None],
            "source": "parse_bar",
            "based_on": "corrected",
        }
        return new_bar
    except Exception:
        return None
