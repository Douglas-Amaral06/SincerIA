import json
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest


class FrontendTests(unittest.TestCase):
    def test_short_message_renders_without_blank_page(self):
        def fake_request(method, url, **_):
            if method == "GET" and url.endswith("/api/conversations"):
                payload = []
            elif method == "POST" and url.endswith("/api/conversations"):
                payload = {"id": "new-chat"}
            elif method == "POST" and url.endswith("/api/chat"):
                payload = {"response": "Oi!", "provider": "test", "model": "test", "route": "conversation"}
            else:
                raise AssertionError(f"Requisição inesperada: {method} {url}")
            response = requests.Response()
            response.status_code = 200
            response._content = json.dumps(payload).encode()
            return response

        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "frontend" / "app.py"), default_timeout=15).run()
            self.assertFalse(app.exception)
            app.chat_input[0].set_value("Oi").run()
            self.assertFalse(app.exception)
            self.assertEqual([item["content"] for item in app.session_state["messages"]], ["Oi", "Oi!"])
            self.assertIsNone(app.session_state["pending"])


if __name__ == "__main__":
    unittest.main()
