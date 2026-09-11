# -*- coding: utf-8 -*-
"""统一确认卡候选生成器单测（disambiguation/unified_confirm.py）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from disambiguation import unified_confirm as uc  # noqa: E402


def test_shanghai_multi_dataset_ambiguous():
    """上海 → 消费者·上海城市公司 + 商用·上海代表处（多数据集歧义）。"""
    cands = uc.build_unified_candidates(["上海"])
    assert uc.is_multi_node_ambiguous(cands) is True
    assert len(cands) == 2
    by_ds = {c["dataset_id"]: c for c in cands}
    assert by_ds[2]["node_name"] == "上海城市公司"
    assert by_ds[2]["node_level"] == "城市分公司"
    assert by_ds[3]["node_name"] == "上海代表处"
    assert by_ds[3]["node_level"] == "代表处"
    assert "上海城市公司" in by_ds[2]["full_question"]
    assert "上海代表处" in by_ds[3]["full_question"]


def test_nanbu_unique_not_ambiguous():
    """南部 → 唯一节点，不歧义（应直出不弹卡）。"""
    cands = uc.build_unified_candidates(["南部"])
    assert uc.is_multi_node_ambiguous(cands) is False
    assert len(cands) == 1
    assert cands[0]["node_name"] == "南部分公司"


def test_nb_expanded_two_branches():
    """拼音首字母 nb 展开 [南部, 北部] → 两个候选。"""
    cands = uc.build_unified_candidates(["南部", "北部"])
    assert uc.is_multi_node_ambiguous(cands) is True
    names = {c["node_name"] for c in cands}
    assert names == {"南部分公司", "北部分公司"}


def test_permission_filter():
    """权限过滤：上海 仅允许 ds=3 → 只剩商用·上海代表处。"""
    cands = uc.build_unified_candidates(["上海"], allowed_dataset_ids=[3])
    assert len(cands) == 1
    assert cands[0]["dataset_id"] == 3
    assert cands[0]["node_name"] == "上海代表处"


def test_nonexistent_object_empty():
    """不存在对象 → 空列表（fail-open）。"""
    assert uc.build_unified_candidates(["火星分公司"]) == []


def test_full_question_format():
    """完整问句格式：'数据集业务名 · 节点全名的指标'。"""
    cands = uc.build_unified_candidates(["上海"])
    for c in cands:
        assert c["business_name"] in c["full_question"]
        assert c["node_name"] in c["full_question"]
        assert "的业绩" in c["full_question"]


def test_metric_hint_custom():
    """指标维度：metric_hint 可定制（达成率）。"""
    cands = uc.build_unified_candidates(["南部"], metric_hint="达成率")
    assert "达成率" in cands[0]["full_question"]
