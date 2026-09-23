from typing import Optional

from openai import AsyncOpenAI

from backend.core.config import settings
from backend.providers.base import (
    AIProvider,
    ImageInput,
    ProviderError,
    ProviderResponse,
)


class OpenRouterProvider(AIProvider):
    name = "openrouter"
    supports_vision = False

    def __init__(
        self,
        model: str | None = None,
    ):
        super().__init__(
            api_key=settings.OPENROUTER_API_KEY,
            model=model or settings.OPENROUTER_MODEL,
        )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=settings.OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://sinceria.app",
                "X-Title": "SincerIA",
            },
        ) if self.configured else None

    async def chat(
        self,
        messages: list[dict],
        images: Optional[list[ImageInput]] = None,
        temperature: float = 0.9,
        max_tokens: int = 1200,
    ) -> ProviderResponse:

        if not self.configured:
            raise ProviderError(
                "OPENROUTER_API_KEY não configurada."
            )

        if images:
            raise ProviderError(
                "OpenRouter vision ainda não habilitado."
            )

        try:
            response = (
                await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,

                    # openrouter/free pode selecionar
                    # modelos de reasoning.
                    #
                    # Mantemos reasoning baixo para sobrar
                    # orçamento para a resposta final.
                    extra_body={
                        "reasoning": {
                            "effort": "low",
                        },
                    },
                )
            )

            if not response.choices:
                raise ProviderError(
                    "OpenRouter não retornou nenhuma choice."
                )

            message = response.choices[0].message

            content = message.content

            if content:
                content = content.strip()

            if not content:
                finish_reason = (
                    response.choices[0].finish_reason
                )

                raise ProviderError(
                    "OpenRouter retornou resposta vazia. "
                    f"finish_reason={finish_reason}"
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
                f"Erro OpenRouter: {exc}"
            ) from exc
