import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.data.database import Database
from backend.data.repositories import ConversationRepository, MemoryRepository
from backend.main import app
from backend.memory.manager import MemoryManager
from backend.orchestration.types import OrchestratorResult, RouteType


class ChatApiTests(unittest.TestCase):
    def test_text_and_photo_are_answered_and_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = Database(root / "chat.db")
            database.initialize()
            conversations = ConversationRepository(database, root / "uploads")
            memory_manager = MemoryManager(MemoryRepository(database))

            async def answer(*, messages, images, **_):
                return OrchestratorResult(
                    "Vi a imagem." if images else "Oi!",
                    "test", "test-model",
                    RouteType.VISION if images else RouteType.CONVERSATION,
                )

            with patch("backend.main.database", database), \
                 patch("backend.main.conversations", conversations), \
                 patch("backend.main.memory_manager", memory_manager), \
                 patch("backend.main.orchestrator.chat", new=AsyncMock(side_effect=answer)):
                with TestClient(app) as client:
                    created = client.post("/api/conversations", json={"mode": "normal"})
                    self.assertEqual(created.status_code, 201)
                    conversation_id = created.json()["id"]

                    text = client.post("/api/chat", json={
                        "message": "Oi", "mode": "normal", "conversation_id": conversation_id,
                    })
                    self.assertEqual(text.status_code, 200, text.text)
                    self.assertEqual(text.json()["response"], "Oi!")

                    photo = client.post("/api/chat/multimodal", data={
                        "message": "Analise esta foto", "mode": "normal",
                        "conversation_id": conversation_id,
                    }, files={"files": ("foto.png", io.BytesIO(b"example"), "image/png")})
                    self.assertEqual(photo.status_code, 200, photo.text)
                    self.assertEqual(photo.json()["route"], "vision")

                    saved = client.get(f"/api/conversations/{conversation_id}")
                    self.assertEqual(saved.status_code, 200)
                    messages = saved.json()["messages"]
                    self.assertEqual([item["role"] for item in messages],
                                     ["user", "assistant", "user", "assistant"])
                    self.assertEqual(messages[2]["attachments"][0]["filename"], "foto.png")


if __name__ == "__main__":
    unittest.main()
