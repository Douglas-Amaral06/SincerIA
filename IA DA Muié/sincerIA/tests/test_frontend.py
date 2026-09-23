import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import requests
from streamlit.testing.v1 import AppTest

from backend.data.database import Database
from backend.data.repositories import ConversationRepository, MemoryRepository
from backend.memory.manager import MemoryManager
from backend.orchestration.types import OrchestratorResult, RouteType


class FrontendTests(unittest.TestCase):
    def test_embedded_backend_replies_without_port_8000(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = Database(root / "chat.db")
            database.initialize()
            conversations = ConversationRepository(database, root / "uploads")
            memories = MemoryManager(MemoryRepository(database))

            async def answer(**_):
                return OrchestratorResult("Oi!", "test", "test-model", RouteType.CONVERSATION)

            with patch.dict(os.environ, {"BACKEND_URL": ""}), \
                 patch("backend.main.database", database), \
                 patch("backend.main.conversations", conversations), \
                 patch("backend.main.memory_manager", memories), \
                 patch("backend.main.orchestrator.chat", new=AsyncMock(side_effect=answer)), \
                 patch("requests.request", side_effect=AssertionError("HTTP externo inesperado")):
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "frontend" / "app.py"), default_timeout=15).run()
                self.assertFalse(app.exception)
                app.chat_input[0].set_value("Oi").run()
                self.assertFalse(app.exception)
                self.assertEqual([item["content"] for item in app.session_state["messages"]], ["Oi", "Oi!"])

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

        with patch.dict(os.environ, {"BACKEND_URL": "https://backend.example.test"}), patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "frontend" / "app.py"), default_timeout=15).run()
            self.assertFalse(app.exception)
            app.chat_input[0].set_value("Oi").run()
            self.assertFalse(app.exception)
            self.assertEqual([item["content"] for item in app.session_state["messages"]], ["Oi", "Oi!"])
            self.assertIsNone(app.session_state["pending"])


if __name__ == "__main__":
    unittest.main()
