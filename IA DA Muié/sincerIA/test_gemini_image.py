"""Teste Gemini isolado: não depende de FastAPI, Streamlit ou Orchestrator."""

import asyncio
import mimetypes
import sys
from pathlib import Path

from backend.providers.base import ImageInput
from backend.providers.registry import gemini


async def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python test_gemini_image.py caminho/da/imagem.jpg [pergunta]")
    image_path = Path(sys.argv[1])
    if not image_path.is_file():
        raise SystemExit(f"Imagem não encontrada: {image_path}")
    mime_type, _ = mimetypes.guess_type(image_path.name)
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise SystemExit("Use JPG, PNG ou WEBP.")
    question = sys.argv[2] if len(sys.argv) > 2 else "O que você vê nesta imagem? Descreva apenas o que for visível."
    result = await gemini.chat(
        messages=[{"role": "user", "content": question}],
        images=[ImageInput(data=image_path.read_bytes(), mime_type=mime_type, filename=image_path.name)],
    )
    print(f"provider={result.provider} model={result.model}")
    print(result.content)


if __name__ == "__main__":
    asyncio.run(main())
