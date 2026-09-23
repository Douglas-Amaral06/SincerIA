from backend.orchestration.fallback import (
    execute_fallback_chain,
)
from backend.orchestration.types import (
    OrchestratorResult,
    RouteType,
)
from backend.providers.base import ImageInput
import logging


logger = logging.getLogger("ORCHESTRATOR")


class Orchestrator:
    # ============================================================
    # FALLBACK CHAINS
    # ============================================================

    CONVERSATION_CHAIN = [
        "groq_qwen",
        "openrouter",
        "groq_fast",
        "groq_power",
        "nvidia",
    ]

    REASONING_CHAIN = [
        "nvidia",
        "groq_power",
        "groq_qwen",
        "openrouter",
        "groq_fast",
    ]

    VISION_CHAIN = [
        "gemini",
        "groq_vision",
    ]

    # ============================================================
    # CLASSIFICAÇÃO
    # ============================================================

    def classify_route(
        self,
        message: str,
        images: list[ImageInput] | None = None,
    ) -> RouteType:

        # ========================================================
        # IMAGEM SEMPRE TEM PRIORIDADE
        # ========================================================

        if images:
            return RouteType.VISION

        text = message.lower().strip()

        # ========================================================
        # REASONING
        # ========================================================

        reasoning_keywords = [
            "analisa tudo",
            "analise tudo",
            "analisa essa situação",
            "analise essa situação",
            "analisa essa historia",
            "analise essa historia",
            "analisa essa história",
            "analise essa história",

            "me ajuda a decidir",
            "o que você faria",
            "qual decisão",
            "qual decisao",

            "compare",
            "comparação",
            "comparacao",

            "prós e contras",
            "pros e contras",

            "encontre padrões",
            "identifique padrões",

            "explica detalhadamente",
            "explique detalhadamente",

            "relacionamento inteiro",
            "história inteira",
            "historia inteira",
        ]

        if any(
            keyword in text
            for keyword
            in reasoning_keywords
        ):
            return RouteType.REASONING

        # Texto muito grande provavelmente
        # merece um modelo de análise.
        if len(message) >= 1200:
            return RouteType.REASONING

        # ========================================================
        # CONVERSA NORMAL
        # ========================================================

        return RouteType.CONVERSATION

    # ============================================================
    # ESCOLHE CHAIN
    # ============================================================

    def get_chain(
        self,
        route: RouteType,
    ) -> list[str]:

        if route == RouteType.VISION:

            return self.VISION_CHAIN.copy()

        if route == RouteType.REASONING:

            return self.REASONING_CHAIN.copy()

        return self.CONVERSATION_CHAIN.copy()

    # ============================================================
    # CHAT
    # ============================================================

    async def chat(
        self,
        messages: list[dict],
        images: list[ImageInput] | None = None,
        temperature: float = 0.9,
        max_tokens: int = 1600,
    ) -> OrchestratorResult:

        # ========================================================
        # PEGA ÚLTIMA MENSAGEM DO USER
        # ========================================================

        user_message = ""

        for message in reversed(
            messages
        ):

            if (
                message.get("role")
                == "user"
            ):

                user_message = str(
                    message.get(
                        "content",
                        "",
                    )
                )

                break

        # ========================================================
        # CLASSIFICA
        # ========================================================

        route = self.classify_route(
            message=user_message,
            images=images,
        )

        chain = self.get_chain(
            route
        )
        if images and (len(images) > 3 or any(not image.mime_type.startswith("image/") for image in images)):
            chain = [provider for provider in chain if provider != "groq_vision"]
        logger.info("rota selecionada=%s cadeia=%s", route.value, ",".join(chain))

        # ========================================================
        # EXECUTA
        # ========================================================

        return await execute_fallback_chain(
            chain=chain,
            route=route,
            messages=messages,
            images=images,
            temperature=temperature,
            max_tokens=max_tokens,
        )


orchestrator = Orchestrator()
