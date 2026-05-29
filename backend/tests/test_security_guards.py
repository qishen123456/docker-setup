import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from feature_flags import feature_available


class SecurityGuardsTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _request(self, method: str, path: str):
        return getattr(self.client, method)(path, json={})

    def test_anonymous_user_has_no_feature_permissions(self):
        self.assertFalse(feature_available("smart_send_question", {}))
        self.assertFalse(feature_available("smart_send_question", None))

    def test_management_routes_require_login(self):
        routes = [
            ("get", "/api/ai-models"),
            ("post", "/api/ai-models"),
            ("get", "/api/datasources"),
            ("post", "/api/datasources"),
            ("get", "/api/agents"),
            ("put", "/api/agents/1"),
            ("get", "/api/datasets/1/report-config"),
            ("put", "/api/datasets/1/report-config"),
            ("get", "/api/report-config/default"),
            ("get", "/api/ai-models/active"),
            ("get", "/api/feishu-sync"),
            ("get", "/api/feishu-sync/1/status"),
            ("get", "/api/bookshelves/source-tables?source_id=1"),
        ]
        for method, path in routes:
            with self.subTest(method=method, path=path):
                response = self._request(method, path)
                self.assertEqual(response.status_code, 401)

    def test_smart_chat_requires_login_after_feature_gate_hardening(self):
        response = self.client.post("/api/smart-chat", json={"question": "看一下业绩"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
