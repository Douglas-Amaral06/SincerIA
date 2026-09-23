"""Teste de visão pela cadeia do Orchestrator, sem frontend ou FastAPI."""

import asyncio
import mimetypes
import sys
from pathlib import Path

from backend.personality.engine import personality_engine
from backend.orchestration.router import orchestrator
from backend.providers.base import ImageInput


async def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python test_vision_orchestrator.py caminho/da/imagem.jpg [pergunta]")
    image_path = Path(sys.argv[1])
    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not image_path.is_file() or mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise SystemExit("Forneça uma imagem JPG, PNG ou WEBP existente.")
    question = sys.argv[2] if len(sys.argv) > 2 else "O que achou da minha roupa? Analise visualmente a imagem."
    messages = personality_engine.prepare_messages("nuclear", [], question)
    result = await orchestrator.chat(messages, images=[ImageInput(image_path.read_bytes(), mime_type, image_path.name)])
    print(f"route={result.route.value} provider={result.provider} model={result.model}")
    print(result.content)
    print("attempts:", [(item.provider, item.model, item.success, item.reason) for item in result.attempts])


if __name__ == "__main__":
    asyncio.run(main())
