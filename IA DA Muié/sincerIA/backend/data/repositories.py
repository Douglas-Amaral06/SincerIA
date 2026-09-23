"""Repositórios síncronos; a API os chama em thread para não bloquear o loop."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from backend.data.database import Database
from backend.data.models import StoredAttachment, StoredConversation, StoredMessage
from backend.providers.base import ImageInput


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _title_from(content: str) -> str:
    compact = " ".join(content.split())
    if len(compact) <= 60:
        return compact or "Nova conversa"
    return f"{compact[:57].rstrip()}..."


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)
    return cleaned or "anexo"


class ConversationRepository:
    def __init__(self, database: Database, upload_dir: Path) -> None:
        self.database = database
        self.upload_dir = upload_dir

    def create_conversation(self, mode: str = "nuclear", title: str = "Nova conversa") -> StoredConversation:
        conversation_id = str(uuid.uuid4())
        now = _now()
        with self.database.session() as connection:
            connection.execute(
                "INSERT INTO conversations (id, title, mode, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, title, mode, now, now),
            )
        return StoredConversation(conversation_id, title, mode, now, now, None)

    def list_conversations(self) -> list[StoredConversation]:
        with self.database.session() as connection:
            rows = connection.execute(
                """
                SELECT c.*, COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE c.deleted_at IS NULL AND c.archived_at IS NULL
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                """
            ).fetchall()
        return [self._conversation(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> StoredConversation | None:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ? AND deleted_at IS NULL",
                (conversation_id,),
            ).fetchone()
        return self._conversation(row) if row else None

    def get_messages(self, conversation_id: str, limit: int | None = None) -> list[StoredMessage]:
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC"
        parameters: tuple[object, ...] = (conversation_id,)
        if limit:
            query = """
                SELECT * FROM (
                    SELECT * FROM messages WHERE conversation_id = ?
                    ORDER BY created_at DESC LIMIT ?
                ) ORDER BY created_at ASC
            """
            parameters = (conversation_id, limit)
        with self.database.session() as connection:
            messages = connection.execute(query, parameters).fetchall()
            attachment_rows = connection.execute(
                "SELECT * FROM attachments WHERE message_id IN (SELECT id FROM messages WHERE conversation_id = ?)",
                (conversation_id,),
            ).fetchall()
        by_message: dict[str, list[StoredAttachment]] = {}
        for attachment in attachment_rows:
            by_message.setdefault(attachment["message_id"], []).append(self._attachment(attachment))
        return [self._message(row, by_message.get(row["id"], [])) for row in messages]

    def add_exchange(
        self,
        conversation_id: str,
        mode: str,
        user_content: str,
        attachments: list[ImageInput],
        assistant_content: str,
        provider: str,
        model: str,
        route: str,
    ) -> tuple[StoredMessage, StoredMessage]:
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            raise KeyError("Conversa não encontrada.")
        now = _now()
        user_id, assistant_id = str(uuid.uuid4()), str(uuid.uuid4())
        stored_attachments: list[StoredAttachment] = []
        saved_files: list[Path] = []
        try:
            for attachment in attachments:
                attachment_id = str(uuid.uuid4())
                filename = _safe_filename(attachment.filename or "anexo")
                relative_path = Path(conversation_id) / f"{attachment_id}_{filename}"
                destination = self.upload_dir / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(attachment.data)
                saved_files.append(destination)
                stored_attachments.append(
                    StoredAttachment(attachment_id, filename, attachment.mime_type, len(attachment.data), str(relative_path), now)
                )

            title = conversation.title
            if title == "Nova conversa":
                title = _title_from(user_content)
            with self.database.session() as connection:
                connection.execute(
                    "UPDATE conversations SET title = ?, mode = ?, updated_at = ? WHERE id = ?",
                    (title, mode, now, conversation_id),
                )
                connection.execute(
                    "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
                    (user_id, conversation_id, user_content, now),
                )
                connection.execute(
                    """INSERT INTO messages (id, conversation_id, role, content, provider, model, route, created_at)
                       VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?)""",
                    (assistant_id, conversation_id, assistant_content, provider, model, route, now),
                )
                for attachment in stored_attachments:
                    connection.execute(
                        """INSERT INTO attachments (id, message_id, filename, mime_type, size, relative_path, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (attachment.id, user_id, attachment.filename, attachment.mime_type, attachment.size, attachment.relative_path, attachment.created_at),
                    )
        except Exception:
            for saved_file in saved_files:
                saved_file.unlink(missing_ok=True)
            raise
        return (
            StoredMessage(user_id, conversation_id, "user", user_content, None, None, None, now, stored_attachments),
            StoredMessage(assistant_id, conversation_id, "assistant", assistant_content, provider, model, route, now, []),
        )

    def archive(self, conversation_id: str) -> bool:
        with self.database.session() as connection:
            result = connection.execute(
                "UPDATE conversations SET archived_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
                (_now(), _now(), conversation_id),
            )
        return result.rowcount > 0

    def get_attachment_path(self, attachment_id: str) -> tuple[Path, str] | None:
        with self.database.session() as connection:
            row = connection.execute("SELECT relative_path, mime_type FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
        if not row:
            return None
        path = (self.upload_dir / row["relative_path"]).resolve()
        if self.upload_dir.resolve() not in path.parents or not path.is_file():
            return None
        return path, row["mime_type"]

    def _conversation(self, row) -> StoredConversation:
        return StoredConversation(row["id"], row["title"], row["mode"], row["created_at"], row["updated_at"], row["archived_at"], row["message_count"] if "message_count" in row.keys() else 0)

    @staticmethod
    def _attachment(row) -> StoredAttachment:
        return StoredAttachment(row["id"], row["filename"], row["mime_type"], row["size"], row["relative_path"], row["created_at"])

    @staticmethod
    def _message(row, attachments: list[StoredAttachment]) -> StoredMessage:
        return StoredMessage(row["id"], row["conversation_id"], row["role"], row["content"], row["provider"], row["model"], row["route"], row["created_at"], attachments)


class MemoryRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add(self, content: str, category: str, importance: int, conversation_id: str) -> None:
        now = _now()
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO memories (id, content, category, importance, source_conversation_id, created_at, updated_at, active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (str(uuid.uuid4()), content, category, importance, conversation_id, now, now),
            )

    def relevant(self, query: str, limit: int = 4) -> list[str]:
        tokens = {word.lower() for word in re.findall(r"[\wÀ-ÿ]{4,}", query)}
        with self.database.session() as connection:
            rows = connection.execute(
                "SELECT content FROM memories WHERE active = 1 ORDER BY importance DESC, updated_at DESC LIMIT 30"
            ).fetchall()
        ranked = sorted(
            ((sum(token in row["content"].lower() for token in tokens), row["content"]) for row in rows),
            reverse=True,
        )
        return [content for score, content in ranked if score > 0][:limit]
