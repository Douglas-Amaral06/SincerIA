from typing import Optional

from openai import AsyncOpenAI

from backend.core.config import settings
from backend.providers.base import (
    AIProvider,
    ImageInput,
    ProviderError,
    ProviderResponse,
)


class VeniceProvider(AIProvider):
    name = "venice"
    supports_vision = False

    def __init__(self):
        super().__init__(
            api_key=settings.VENICE_API_KEY,
            model=settings.VENICE_MODEL,
        )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=settings.VENICE_BASE_URL,
        )

    async def chat(
        self,
        messages: list[dict],
        images: Optional[list[ImageInput]] = None,
        temperature: float = 1.0,
        max_tokens: int = 1500,
    ) -> ProviderResponse:

        if not self.configured:
            raise ProviderError(
                "VENICE_API_KEY não configurada."
            )

        # Por enquanto deixamos visão sendo tratada
        # pelo Gemini/Ollama.
        if images:
            raise ProviderError(
                "Visão Venice ainda não habilitada neste provider."
            )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            content = (
                response
                .choices[0]
                .message
                .content
            )

            if not content:
                raise ProviderError(
                    "Venice retornou resposta vazia."
                )

            return ProviderResponse(
                content=content,
                provider=self.name,
                model=self.model,
            )

        except ProviderError:
            raise

        except Exception as exc:
            raise ProviderError(
                f"Erro Venice: {exc}"
            ) from exc