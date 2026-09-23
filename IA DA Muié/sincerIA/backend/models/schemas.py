from typing import Literal

from pydantic import BaseModel, Field


ChatMode = Literal[
    "normal",
    "sincera",
    "acida",
    "nuclear",
]


class ChatMessage(BaseModel):
    role: Literal[
        "user",
        "assistant",
    ]

    content: str


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=20_000,
    )

    mode: ChatMode = "normal"

    history: list[ChatMessage] = Field(
        default_factory=list
    )

    conversation_id: str | None = None


class AttemptResponse(BaseModel):
    provider: str

    model: str | None = None

    success: bool = False
    skipped: bool = False

    failure: str | None = None
    reason: str | None = None


class ChatResponse(BaseModel):
    response: str

    mode: str
    route: str

    provider: str
    model: str

    attempts: list[AttemptResponse]
    conversation_id: str | None = None


class ModeInfo(BaseModel):
    id: str
    name: str

    description: str

    honesty: int
    sarcasm: int
    arrogance: int
    roast: int
    profanity: int
    affection: int


class ConversationCreate(BaseModel):
    mode: ChatMode = "nuclear"


class AttachmentResponse(BaseModel):
    id: str
    filename: str
    mime_type: str
    size: int
    created_at: str
    url: str


class MessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    provider: str | None = None
    model: str | None = None
    route: str | None = None
    created_at: str
    attachments: list[AttachmentResponse] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    id: str
    title: str
    mode: str
    created_at: str
    updated_at: str
    message_count: int = 0
    messages: list[MessageResponse] | None = None
