"""Tipos de domínio independentes do SQLite e do FastAPI."""

from dataclasses import dataclass


@dataclass(slots=True)
class StoredAttachment:
    id: str
    filename: str
    mime_type: str
    size: int
    relative_path: str
    created_at: str


@dataclass(slots=True)
class StoredMessage:
    id: str
    conversation_id: str
    role: str
    content: str
    provider: str | None
    model: str | None
    route: str | None
    created_at: str
    attachments: list[StoredAttachment]


@dataclass(slots=True)
class StoredConversation:
    id: str
    title: str
    mode: str
    created_at: str
    updated_at: str
    archived_at: str | None
    message_count: int = 0
