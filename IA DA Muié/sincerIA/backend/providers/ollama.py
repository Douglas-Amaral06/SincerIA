import base64
from typing import Optional

import httpx

from backend.core.config import settings
from backend.providers.base import (
    AIProvider,
    ImageInput,
    ProviderError,
    ProviderResponse,
)


class OllamaProvider(AIProvider):
    name = "ollama"
    supports_vision = True

    def __init__(self):
        super().__init__(
            api_key=settings.OLLAMA_API_KEY,
            model=settings.OLLAMA_MODEL,
        )

        self.base_url = settings.OLLAMA_BASE_URL

    async def chat(
        self,
        messages: list[dict],
        images: Optional[list[ImageInput]] = None,
        temperature: float = 0.85,
        max_tokens: int = 1600,
    ) -> ProviderResponse:

        if not self.configured:
            raise ProviderError(
                "OLLAMA_API_KEY não configurada."
            )

        payload_messages = []

        for message in messages:
            payload_messages.append(
                {
                    "role": message.get(
                        "role",
                        "user",
                    ),
                    "content": str(
                        message.get(
                            "content",
                            "",
                        )
                    ),
                }
            )

        # ========================================================
        # IMAGENS
        # ========================================================

        if images:
            encoded_images = [
                base64.b64encode(
                    image.data
                ).decode("utf-8")
                for image in images
            ]

            # Adiciona imagem à mensagem de usuário
            # mais recente.
            for index in range(
                len(payload_messages) - 1,
                -1,
                -1,
            ):
                if (
                    payload_messages[index]["role"]
                    == "user"
                ):
                    payload_messages[index][
                        "images"
                    ] = encoded_images
                    break

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,

            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        headers = {
            "Authorization": (
                f"Bearer {self.api_key}"
            ),
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=120.0
            ) as client:

                response = await client.post(
                    f"{self.base_url}/chat",
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()

                data = response.json()

            message = data.get(
                "message",
                {}
            )

            content = message.get(
                "content",
                "",
            )

            if not content:
                raise ProviderError(
                    "Ollama retornou resposta vazia."
                )

            return ProviderResponse(
                content=content,
                provider=self.name,
                model=self.model,
            )

        except ProviderError:
            raise

        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                "Erro HTTP Ollama "
                f"{exc.response.status_code}: "
                f"{exc.response.text}"
            ) from exc

        except Exception as exc:
            raise ProviderError(
                f"Erro Ollama: {exc}"
            ) from exc