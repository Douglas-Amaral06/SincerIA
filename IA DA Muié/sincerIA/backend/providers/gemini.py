import asyncio
import logging
from typing import Optional

from google import genai
from google.genai import errors, types

from backend.core.config import settings
from backend.providers.base import (
    AIProvider,
    ImageInput,
    ProviderError,
    ProviderResponse,
)


class GeminiProvider(AIProvider):
    name = "gemini"
    supports_vision = True

    def __init__(self):
        super().__init__(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )

        self.primary_model = (
            settings.GEMINI_MODEL
        )

        self.fallback_model = (
            settings.GEMINI_FALLBACK_MODEL
        )

        self.models = list(dict.fromkeys([self.primary_model, self.fallback_model]))

        self.client = genai.Client(
            api_key=self.api_key,
        )

        # ========================================================
        # TIMEOUT POR MODELO
        # ========================================================
        #
        # O ponto importante:
        #
        # o Gemini 3.8 NÃO pode consumir sozinho
        # os 45s do Orchestrator.
        #
        # Se ele enrolar, pulamos rapidamente
        # para o Flash-Lite.
        # ========================================================

        self.model_timeouts = {
            self.primary_model: settings.GEMINI_PRIMARY_TIMEOUT_SECONDS,
            self.fallback_model: settings.GEMINI_FALLBACK_TIMEOUT_SECONDS,
        }

        self.logger = logging.getLogger("GEMINI")

    def timeout_budget(self) -> float:
        return sum(self.model_timeouts.get(model, 20.0) for model in self.models) + 3.0

    # ============================================================
    # CONVERSÃO DE MENSAGENS
    # ============================================================

    def _convert_messages(
        self,
        messages: list[dict],
        images: Optional[list[ImageInput]] = None,
    ):
        system_parts = []
        contents = []

        last_user_index = -1

        for index, message in enumerate(messages):
            if message.get("role") == "user":
                last_user_index = index

        for index, message in enumerate(messages):

            role = message.get(
                "role",
                "user",
            )

            content = message.get(
                "content",
                "",
            )

            if not isinstance(content, str):
                content = str(content)

            # ====================================================
            # SYSTEM
            # ====================================================

            if role == "system":

                if content:
                    system_parts.append(
                        content
                    )

                continue

            # ====================================================
            # ROLE
            # ====================================================

            gemini_role = (
                "model"
                if role == "assistant"
                else "user"
            )

            parts = []

            # ====================================================
            # TEXTO
            # ====================================================

            if content:

                parts.append(
                    types.Part.from_text(
                        text=content,
                    )
                )

            # ====================================================
            # IMAGENS / ARQUIVOS
            # ====================================================

            if (
                images
                and role == "user"
                and index == last_user_index
            ):

                for image in images:

                    parts.append(
                        types.Part.from_bytes(
                            data=image.data,
                            mime_type=image.mime_type,
                        )
                    )

            if parts:

                contents.append(
                    types.Content(
                        role=gemini_role,
                        parts=parts,
                    )
                )

        system_instruction = "\n\n".join(
            system_parts
        )

        if not contents:
            raise ProviderError("Gemini não recebeu conteúdo utilizável.")
        return system_instruction, contents

    # ============================================================
    # CONFIG
    # ============================================================

    def _build_config(
        self,
        model: str,
        system_instruction: str,
        temperature: float,
        max_tokens: int,
    ):
        config_data = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if system_instruction:

            config_data[
                "system_instruction"
            ] = system_instruction

        # O modelo principal pode usar pensamento baixo.
        # Não queremos 40 segundos de reflexão sobre
        # uma camiseta.
        if model == self.primary_model:

            config_data[
                "thinking_config"
            ] = types.ThinkingConfig(
                thinking_level="low",
            )

        return types.GenerateContentConfig(
            **config_data
        )

    # ============================================================
    # EXTRAI SOMENTE TEXTO
    # ============================================================

    def _extract_text(
        self,
        response,
    ) -> str:

        try:

            if not response.candidates:
                return ""

            candidate = response.candidates[0]

            if not candidate.content:
                return ""

            if not candidate.content.parts:
                return ""

            text_parts = []

            for part in candidate.content.parts:

                text = getattr(
                    part,
                    "text",
                    None,
                )

                if text:
                    text_parts.append(
                        text
                    )

            return "".join(
                text_parts
            ).strip()

        except Exception:
            return ""

    # ============================================================
    # CHAMA UM MODELO
    # ============================================================

    async def _call_model(
        self,
        model: str,
        contents,
        system_instruction: str,
        temperature: float,
        max_tokens: int,
    ) -> ProviderResponse:

        config = self._build_config(
            model=model,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response = (
            await self.client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        )

        content = self._extract_text(
            response
        )

        if not content:

            raise ProviderError(
                f"Gemini ({model}) "
                "retornou resposta vazia."
            )

        return ProviderResponse(
            content=content,
            provider=self.name,
            model=model,
        )

    # ============================================================
    # CHAT
    # ============================================================

    async def chat(
        self,
        messages: list[dict],
        images: Optional[list[ImageInput]] = None,
        temperature: float = 0.9,
        max_tokens: int = 1600,
    ) -> ProviderResponse:

        if not self.configured:

            raise ProviderError(
                "GEMINI_API_KEY não configurada."
            )

        (
            system_instruction,
            contents,
        ) = self._convert_messages(
            messages=messages,
            images=images,
        )

        errors_received = []

        # ========================================================
        # FALLBACK INTERNO GEMINI
        # ========================================================

        for model in self.models:

            timeout = self.model_timeouts.get(
                model,
                20.0,
            )

            try:
                self.logger.info("tentando modelo=%s timeout=%.1fs imagens=%s", model, timeout, bool(images))

                # =================================================
                # TIMEOUT INDIVIDUAL
                # =================================================
                #
                # Se o 3.8 travar por 15s:
                #
                # 3.8 ❌
                # ↓
                # 3.5 Flash-Lite
                #
                # SEM esperar o Orchestrator matar tudo.
                # =================================================

                result = await asyncio.wait_for(
                    self._call_model(
                        model=model,
                        contents=contents,
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout,
                )

                self.logger.info("sucesso modelo=%s", model)
                return result

            # ====================================================
            # TIMEOUT DO MODELO
            # ====================================================

            except asyncio.TimeoutError:

                errors_received.append(
                    f"{model}: timeout "
                    f"após {timeout:.0f}s"
                )

                self.logger.warning("timeout modelo=%s; tentando fallback", model)

                continue

            # ====================================================
            # GOOGLE API ERROR
            # ====================================================

            except errors.APIError as exc:

                code = getattr(
                    exc,
                    "code",
                    None,
                )

                message = getattr(
                    exc,
                    "message",
                    str(exc),
                )

                errors_received.append(
                    f"{model}: "
                    f"HTTP {code} - {message}"
                )

                # -----------------------------------------------
                # RECUPERÁVEIS
                # -----------------------------------------------

                if code in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    self.logger.warning("falha recuperável modelo=%s status=%s; tentando fallback", model, code)
                    continue

                # -----------------------------------------------
                # NÃO RECUPERÁVEIS
                # -----------------------------------------------

                raise ProviderError(
                    "Erro Gemini "
                    "não recuperável: "
                    f"HTTP {code} - {message}"
                ) from exc

            except ProviderError as exc:

                errors_received.append(
                    f"{model}: {exc}"
                )
                self.logger.warning("resposta inválida modelo=%s; tentando fallback: %s", model, exc)

                continue

            except Exception as exc:

                errors_received.append(
                    f"{model}: {exc}"
                )
                self.logger.warning("falha inesperada modelo=%s; tentando fallback: %s", model, type(exc).__name__)

                continue

        # ========================================================
        # TODOS MORRERAM
        # ========================================================

        details = " | ".join(
            errors_received
        )

        raise ProviderError(
            "Todos os modelos Gemini falharam. "
            f"{details}"
        )
