from typing import Optional

from openai import AsyncOpenAI

from backend.core.config import settings
from backend.providers.base import (
    AIProvider,
    ImageInput,
    ProviderError,
    ProviderResponse,
)


class NvidiaProvider(AIProvider):
    name = "nvidia"
    supports_vision = False

    def __init__(self):
        super().__init__(
            api_key=settings.NVIDIA_API_KEY,
            model=settings.NVIDIA_MODEL,
        )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=settings.NVIDIA_BASE_URL,
        ) if self.configured else None

    async def chat(
        self,
        messages: list[dict],
        images: Optional[list[ImageInput]] = None,
        temperature: float = 1.0,
        max_tokens: int = 1800,
    ) -> ProviderResponse:

        if not self.configured:
            raise ProviderError(
                "NVIDIA_API_KEY não configurada."
            )

        if images:
            raise ProviderError(
                "O NvidiaProvider atual está configurado apenas para texto."
            )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,

                # Configuração recomendada para Nemotron 3 Super
                temperature=temperature,
                top_p=0.95,
                max_tokens=max_tokens,

                # MUITO IMPORTANTE:
                # impede o Nemotron de vomitar
                # todo o raciocínio interno na resposta.
                extra_body={
                    "chat_template_kwargs": {
                        "enable_thinking": False,
                    }
                },

                stream=False,
            )

            if not response.choices:
                raise ProviderError(
                    "NVIDIA não retornou nenhuma choice."
                )

            message = response.choices[0].message

            content = message.content

            if content:
                content = content.strip()

            if not content:
                raise ProviderError(
                    "NVIDIA retornou resposta vazia."
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
                f"Erro NVIDIA: {exc}"
            ) from exc
