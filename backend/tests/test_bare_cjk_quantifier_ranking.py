"""裸中文基数词+量词（四大/三个/五家/三家公司）的排名识别回归测试。

背景：原 _rank_limit_match 与 _looks_like_org_subject_question 的排名排除正则
都要求"前/后/倒数/top/最X/第"前缀，导致"四大分公司..."被误判为组织主体问法、
进 _agent1_resolve_org_subject 改写成"分公司的业绩"丢掉"四"，top_n 回落默认值。
本测试锁定修复后行为：裸基数词+量词既要被 _rank_limit_match 识别，又要在
_looks_like_org_subject_question 里被排除（不进损耗式改写）。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ask_engine_sql import _rank_limit_match, _parse_cn_int
from ask_engine_entity import _looks_like_org_subject_question

try:
    from four_agent_ask import FourAgentAskService

    _HAS_SERVICE = True
    _IMPORT_ERROR = None
except Exception as _e:  # 环境依赖缺失时降级，仅跳过端到端 _rank_request_spec
    _HAS_SERVICE = False
    _IMPORT_ERROR = _e


class BareCjkQuantifierDetectionTest(unittest.TestCase):
    """纯函数级：裸基数词+量词的识别与排除。"""

    def test_bare_cjk_quantifier_not_treated_as_org_subject(self):
        for q in (
            "四大分公司区域业绩整体盘点",
            "三个代表处业绩",
            "五家城市公司业绩",
            "三家公司业绩",
            "4个事业部业绩",
            "十大分公司业绩",
        ):
            with self.subTest(question=q):
                self.assertFalse(
                    _looks_like_org_subject_question(q),
                    msg=f"裸基数词问题不应判为组织主体问法: {q}",
                )

    def test_no_quantifier_not_over_excluded(self):
        # 无数量词的具体节点仍应是主体问法；纯层级词仍走 level-only
        self.assertTrue(_looks_like_org_subject_question("郑州城市公司业绩"))
        self.assertTrue(_looks_like_org_subject_question("江浙沪分公司业绩"))
        self.assertFalse(_looks_like_org_subject_question("分公司业绩"))
        self.assertFalse(_looks_like_org_subject_question("城市分公司的业绩"))

    def test_rank_limit_match_bare_cjk_quantifier(self):
        cases = {
            "四大分公司区域业绩整体盘点": 4,
            "三个代表处": 3,
            "五家城市公司": 5,
            "三家公司业绩": 3,
            "4个事业部": 4,
            "十大分公司": 10,
        }
        for q, expected in cases.items():
            with self.subTest(question=q):
                m = _rank_limit_match(q)
                self.assertIsNotNone(m, msg=f"应匹配到数量词: {q}")
                self.assertEqual(_parse_cn_int(m.group(1), 0), expected)

    def test_rank_limit_match_no_quantifier(self):
        for q in ("分公司业绩", "业务部情况", "城市分公司的业绩", "郑州城市公司业绩"):
            with self.subTest(question=q):
                self.assertIsNone(_rank_limit_match(q), msg=f"无数量词不应误判: {q}")

    def test_rank_limit_match_prefix_still_works(self):
        self.assertIsNotNone(_rank_limit_match("前三的代表处"))
        self.assertIsNotNone(_rank_limit_match("倒数2个代表处"))
        self.assertIsNotNone(_rank_limit_match("Top5事业部"))
        self.assertEqual(_parse_cn_int(_rank_limit_match("前十名").group(1), 0), 10)


@unittest.skipUnless(
    _HAS_SERVICE,
    f"four_agent_ask 导入失败，跳过端到端 _rank_request_spec: {_IMPORT_ERROR}" if not _HAS_SERVICE else "",
)
class BareCjkQuantifierRankRequestSpecTest(unittest.TestCase):
    """端到端：_rank_request_spec 对裸中文基数词得到正确 limit。"""

    def setUp(self):
        self.service = object.__new__(FourAgentAskService)

    def test_bare_cjk_quantifier_limit(self):
        self.assertEqual(self.service._rank_request_spec("四大分公司区域业绩整体盘点")["limit"], 4)
        self.assertEqual(self.service._rank_request_spec("三个代表处")["limit"], 3)
        self.assertEqual(self.service._rank_request_spec("五家城市公司")["limit"], 5)

    def test_prefix_rank_spec_unchanged(self):
        spec = self.service._rank_request_spec("前3和倒数2个代表处")
        self.assertEqual(spec["limit"], 3)
        self.assertEqual(spec["top_limit"], 3)
        self.assertEqual(spec["bottom_limit"], 2)
        self.assertEqual(self.service._rank_request_spec("前十名")["limit"], 10)


if __name__ == "__main__":
    unittest.main()
