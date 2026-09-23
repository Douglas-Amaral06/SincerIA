import base64
from typing import Optional

from openai import AsyncOpenAI

from backend.core.config import settings
from backend.providers.base import (
    AIProvider,
    ImageInput,
    ProviderError,
    ProviderResponse,
)


class GroqProvider(AIProvider):
    name = "groq"
    supports_vision = False

    def __init__(
        self,
        model: str | None = None,
    ):
        super().__init__(
            api_key=settings.GROQ_API_KEY,
            model=model or settings.QWEN_MODEL,
        )
        self.supports_vision = self.model == settings.QWEN_MODEL

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=settings.GROQ_BASE_URL,
        )

    def _is_gpt_oss(self) -> bool:
        return self.model in {
            settings.GPT_OSS_FAST_MODEL,
            settings.GPT_OSS_POWER_MODEL,
        }

    async def chat(
        self,
        messages: list[dict],
        images: Optional[list[ImageInput]] = None,
        temperature: float = 0.9,
        max_tokens: int = 1200,
    ) -> ProviderResponse:

        if not self.configured:
            raise ProviderError(
                "GROQ_API_KEY não configurada."
            )

        if images and self.model != settings.QWEN_MODEL:
            raise ProviderError("Este modelo Groq não aceita imagens.")
        if images and (len(images) > 3 or any(not image.mime_type.startswith("image/") for image in images)):
            raise ProviderError("Groq aceita até três imagens PNG, JPG ou WEBP por mensagem.")

        try:
            request_messages = messages
            if images:
                request_messages = [message.copy() for message in messages]
                last_user = next((index for index in range(len(request_messages) - 1, -1, -1)
                                  if request_messages[index].get("role") == "user"), None)
                if last_user is None:
                    raise ProviderError("Nenhuma mensagem de usuário para anexar a imagem.")
                original = request_messages[last_user]
                request_messages[last_user] = {
                    **original,
                    "content": [
                        {"type": "text", "text": str(original.get("content", ""))},
                        *[
                            {"type": "image_url", "image_url": {"url":
                                f"data:{image.mime_type};base64,{base64.b64encode(image.data).decode('ascii')}"}}
                            for image in images
                        ],
                    ],
                }
            request_data = {
                "model": self.model,
                "messages": request_messages,
                "temperature": temperature,
                "max_completion_tokens": max_tokens,
                "stream": False,
            }

            # GPT-OSS pode gastar boa parte do limite
            # fazendo reasoning antes da resposta final.
            #
            # Para nosso chat, queremos a resposta pronta,
            # não pagar tokens de filosofia interna do robô.
            if self._is_gpt_oss():
                request_data["reasoning_effort"] = "low"

                request_data["extra_body"] = {
                    "include_reasoning": False,
                }

            response = (
                await self.client.chat.completions.create(
                    **request_data
                )
            )

            message = response.choices[0].message

            content = message.content

            if content:
                content = content.strip()

            if not content:
                raise ProviderError(
                    "Groq retornou resposta vazia."
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
                f"Erro Groq: {exc}"
            ) from exc
