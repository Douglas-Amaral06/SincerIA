"""API da SincerIA: contratos de chat legados e persistência incremental."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.core.config import settings
from backend.core.logging import configure_logging
from backend.data.database import Database
from backend.data.models import StoredAttachment, StoredConversation, StoredMessage
from backend.data.repositories import ConversationRepository, MemoryRepository
from backend.memory.manager import MemoryManager
from backend.models.schemas import AttachmentResponse, AttemptResponse, ChatMessage, ChatRequest, ChatResponse, ConversationCreate, ConversationResponse, MessageResponse, ModeInfo
from backend.orchestration.cooldown import cooldowns
from backend.orchestration.health import health
from backend.orchestration.router import orchestrator
from backend.orchestration.types import OrchestrationError
from backend.personality.engine import personality_engine
from backend.personality.profiles import PROFILES
from backend.providers.base import ImageInput


logger = logging.getLogger("API")
configure_logging()
MAX_FILE_SIZE = 15 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
ALLOWED_MODES = {"normal", "sincera", "acida", "nuclear"}

database = Database(Path(settings.DATABASE_PATH))
conversations = ConversationRepository(database, Path(settings.UPLOAD_DIR))
memory_manager = MemoryManager(MemoryRepository(database))


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(database.initialize)
    logger.info("banco SQLite inicializado em %s", database.path)
    yield


app = FastAPI(title="SincerIA API", description="Backend multi-modelo da SincerIA.", version="1.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


def serialize_attempts(attempts) -> list[AttemptResponse]:
    return [
        AttemptResponse(
            provider=attempt.provider,
            model=attempt.model,
            success=attempt.success,
            skipped=attempt.skipped,
            failure=attempt.failure_kind.value if attempt.failure_kind else None,
            reason=attempt.reason,
        )
        for attempt in attempts
    ]


def attachment_response(attachment: StoredAttachment) -> AttachmentResponse:
    return AttachmentResponse(id=attachment.id, filename=attachment.filename, mime_type=attachment.mime_type, size=attachment.size, created_at=attachment.created_at, url=f"/api/attachments/{attachment.id}")


def message_response(message: StoredMessage) -> MessageResponse:
    return MessageResponse(id=message.id, role=message.role, content=message.content, provider=message.provider, model=message.model, route=message.route, created_at=message.created_at, attachments=[attachment_response(item) for item in message.attachments])


def conversation_response(conversation: StoredConversation, include_messages: bool = False) -> ConversationResponse:
    messages = conversations.get_messages(conversation.id) if include_messages else None
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        mode=conversation.mode,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=conversation.message_count,
        messages=[message_response(item) for item in messages] if messages is not None else None,
    )


async def conversation_history(conversation_id: str | None, fallback_history: list[dict]) -> list[dict]:
    if not conversation_id:
        return fallback_history
    conversation = await asyncio.to_thread(conversations.get_conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    messages = await asyncio.to_thread(conversations.get_messages, conversation_id, 40)
    return [{"role": item.role, "content": item.content} for item in messages]


async def execute_chat(
    message: str,
    mode: str,
    history: list[dict],
    attachments: list[ImageInput] | None = None,
    conversation_id: str | None = None,
) -> ChatResponse:
    relevant_memories = await asyncio.to_thread(memory_manager.context_for, message) if conversation_id else []
    messages = personality_engine.prepare_messages(mode=mode, history=history, user_message=message, memory_context=relevant_memories)
    try:
        result = await orchestrator.chat(messages=messages, images=attachments, temperature=0.9, max_tokens=1800)
    except OrchestrationError as exc:
        logger.warning("nenhum provider respondeu rota=%s", "vision" if attachments else "text")
        raise HTTPException(
            status_code=503,
            detail={"message": "Nenhuma IA conseguiu responder agora.", "attempts": [item.model_dump() for item in serialize_attempts(exc.attempts)]},
        ) from exc
    except Exception as exc:
        logger.exception("erro interno durante chat")
        raise HTTPException(status_code=500, detail={"message": "Erro interno da SincerIA."}) from exc

    if conversation_id:
        try:
            await asyncio.to_thread(conversations.add_exchange, conversation_id, mode, message, attachments or [], result.content, result.provider, result.model, result.route.value)
            await asyncio.to_thread(memory_manager.remember_if_relevant, message, conversation_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Conversa não encontrada.") from exc
        except Exception:
            logger.exception("falha ao persistir conversa=%s", conversation_id)
            # A resposta já existe: uma falha no armazenamento não deve escondê-la.

    return ChatResponse(response=result.content, mode=mode, route=result.route.value, provider=result.provider, model=result.model, attempts=serialize_attempts(result.attempts), conversation_id=conversation_id)


@app.get("/")
async def root():
    return {"service": "SincerIA", "version": "1.2.0", "status": "online", "message": "A sinceridade está operacional."}


@app.get("/health")
async def health_check():
    return {"status": "ok", "providers": health.snapshot(), "cooldowns": cooldowns.snapshot()}


@app.get("/api/modes", response_model=list[ModeInfo])
async def get_modes():
    return [ModeInfo(id=mode.value, name=profile.name, description=profile.description, honesty=profile.honesty, sarcasm=profile.sarcasm, arrogance=profile.arrogance, roast=profile.roast, profanity=profile.profanity, affection=profile.affection) for mode, profile in PROFILES.items()]


@app.post("/api/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(payload: ConversationCreate):
    conversation = await asyncio.to_thread(conversations.create_conversation, payload.mode)
    logger.info("conversa criada id=%s", conversation.id)
    return conversation_response(conversation)


@app.get("/api/conversations", response_model=list[ConversationResponse])
async def list_conversations():
    items = await asyncio.to_thread(conversations.list_conversations)
    return [conversation_response(item) for item in items]


@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    conversation = await asyncio.to_thread(conversations.get_conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return await asyncio.to_thread(conversation_response, conversation, True)


@app.get("/api/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(conversation_id: str):
    conversation = await asyncio.to_thread(conversations.get_conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    items = await asyncio.to_thread(conversations.get_messages, conversation_id)
    return [message_response(item) for item in items]


@app.delete("/api/conversations/{conversation_id}", status_code=204)
async def archive_conversation(conversation_id: str):
    archived = await asyncio.to_thread(conversations.archive, conversation_id)
    if not archived:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")


@app.get("/api/attachments/{attachment_id}")
async def get_attachment(attachment_id: str):
    found = await asyncio.to_thread(conversations.get_attachment_path, attachment_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
    path, mime_type = found
    return FileResponse(path, media_type=mime_type, filename=path.name)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    history = await conversation_history(payload.conversation_id, [message.model_dump() for message in payload.history])
    return await execute_chat(payload.message, payload.mode, history, conversation_id=payload.conversation_id)


@app.post("/api/chat/multimodal", response_model=ChatResponse)
async def chat_multimodal(
    message: str = Form(...),
    mode: str = Form("normal"),
    history: str = Form("[]"),
    conversation_id: str | None = Form(default=None),
    files: list[UploadFile] | None = File(default=None),
):
    if mode not in ALLOWED_MODES:
        raise HTTPException(status_code=400, detail=f"Modo inválido: {mode}")
    try:
        parsed_history = [ChatMessage.model_validate(item).model_dump() for item in json.loads(history)]
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Histórico inválido.") from exc

    attachments: list[ImageInput] = []
    for uploaded in files or []:
        mime_type = uploaded.content_type or "application/octet-stream"
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=415, detail=f"Tipo não suportado: {mime_type}")
        content = await uploaded.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"O arquivo {uploaded.filename} está vazio.")
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"O arquivo {uploaded.filename} ultrapassa 15 MB.")
        logger.info("arquivo recebido nome=%s mime=%s tamanho=%d", uploaded.filename, mime_type, len(content))
        attachments.append(ImageInput(data=content, mime_type=mime_type, filename=uploaded.filename))

    clean_message = message.strip() or ("Analise o arquivo enviado e fale comigo de acordo com sua personalidade atual." if attachments else "")
    if not clean_message:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")
    stored_history = await conversation_history(conversation_id, parsed_history)
    return await execute_chat(clean_message, mode, stored_history, attachments, conversation_id)
