import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ask_flow.controller import AskFlowController


ADVANCED_CONFIG = {
    "defaultFlow": "advanced",
    "advancedEnabled": True,
    "advancedRoles": ["super_admin", "admin"],
    "datasetPolicies": {},
    "fallbackToBasicOnError": True,
    "attachMetadata": True,
}


class AskFlowControllerPermissionTest(unittest.TestCase):
    def _decide(self, user, feature_allowed):
        controller = AskFlowController(basic_service=object(), advanced_service=object())
        controller.load_config = lambda: dict(ADVANCED_CONFIG)
        with patch("feature_flags.feature_available", return_value=feature_allowed):
            return controller.decide(user=user)

    def test_admin_without_advanced_flow_feature_uses_basic(self):
        decision = self._decide({"role": "admin"}, feature_allowed=False)
        self.assertEqual(decision.flow, "basic")
        self.assertEqual(decision.reason, "advanced_role_denied")

    def test_super_admin_with_advanced_flow_feature_uses_advanced(self):
        decision = self._decide({"role": "super_admin"}, feature_allowed=True)
        self.assertEqual(decision.flow, "advanced")
        self.assertEqual(decision.reason, "advanced_selected")

    def test_feature_permission_still_respects_gray_role_list(self):
        decision = self._decide({"role": "business_admin"}, feature_allowed=True)
        self.assertEqual(decision.flow, "basic")
        self.assertEqual(decision.reason, "advanced_role_denied")


if __name__ == "__main__":
    unittest.main()
