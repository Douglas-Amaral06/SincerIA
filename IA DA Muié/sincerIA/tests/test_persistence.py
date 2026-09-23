import tempfile
import unittest
from pathlib import Path

from backend.data.database import Database
from backend.data.repositories import ConversationRepository
from backend.providers.base import ImageInput


class PersistenceTests(unittest.TestCase):
    def test_creates_and_recovers_exchange_with_attachment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = Database(root / "sinceria.db")
            database.initialize()
            repository = ConversationRepository(database, root / "uploads")
            conversation = repository.create_conversation("nuclear")
            repository.add_exchange(
                conversation.id,
                "nuclear",
                "Minha roupa está boa?",
                [ImageInput(b"fake-image", "image/png", "look.png")],
                "A análise veio daqui.",
                "gemini",
                "gemini-test",
                "vision",
            )
            messages = repository.get_messages(conversation.id)
            self.assertEqual([message.role for message in messages], ["user", "assistant"])
            self.assertEqual(messages[0].attachments[0].filename, "look.png")
            self.assertEqual(repository.get_conversation(conversation.id).title, "Minha roupa está boa?")


if __name__ == "__main__":
    unittest.main()
