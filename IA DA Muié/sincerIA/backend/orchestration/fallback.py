import asyncio
import os
import re
import logging

from dotenv import load_dotenv

from backend.orchestration.cooldown import (
    cooldowns,
)
from backend.orchestration.health import (
    health,
)
from backend.orchestration.types import (
    AttemptLog,
    FailureKind,
    OrchestrationError,
    OrchestratorResult,
    RouteType,
)
from backend.providers.base import ImageInput
from backend.providers.registry import PROVIDERS


logger = logging.getLogger("ORCHESTRATOR")


load_dotenv()


def _env_bool(
    name: str,
    default: bool = True,
) -> bool:

    value = os.getenv(
        name
    )

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "sim",
    }


def _timeout_seconds(
    route: RouteType | None = None,
) -> float:

    if route == RouteType.VISION:

        try:
            return float(os.getenv("ORCHESTRATOR_VISION_TIMEOUT_SECONDS", "45"))

        except ValueError:
            return 45.0

    try:
        return float(os.getenv("ORCHESTRATOR_TIMEOUT_SECONDS", "45"))

    except ValueError:
        return 45.0


def provider_enabled(
    provider_name: str,
) -> bool:

    if provider_name.startswith(
        "groq_"
    ):
        return _env_bool(
            "GROQ_ENABLED",
            True,
        )

    mapping = {
        "openrouter": (
            "OPENROUTER_ENABLED"
        ),
        "nvidia": (
            "NVIDIA_ENABLED"
        ),
        "gemini": (
            "GEMINI_ENABLED"
        ),
        "venice": (
            "VENICE_ENABLED"
        ),
        "ollama": (
            "OLLAMA_ENABLED"
        ),
    }

    env_name = mapping.get(
        provider_name
    )

    if env_name is None:
        return True

    default = (
        False
        if provider_name
        in {"venice", "ollama"}
        else True
    )

    return _env_bool(
        env_name,
        default,
    )


def classify_failure(
    exception: Exception,
) -> FailureKind:

    if isinstance(
        exception,
        asyncio.TimeoutError,
    ):
        return FailureKind.TIMEOUT

    text = str(
        exception
    ).lower()

    # ============================================================
    # AUTH
    # ============================================================

    if (
        re.search(
            r"\b401\b",
            text,
        )
        or "invalid api key" in text
        or "unauthorized" in text
        or "authentication" in text
    ):
        return FailureKind.AUTH

    if (
        re.search(
            r"\b403\b",
            text,
        )
        or "forbidden" in text
        or "permission denied" in text
    ):
        return FailureKind.AUTH

    # ============================================================
    # PAYMENT
    # ============================================================

    if (
        re.search(
            r"\b402\b",
            text,
        )
        or "insufficient balance" in text
        or "add credits" in text
        or "payment required" in text
    ):
        return FailureKind.PAYMENT

    # ============================================================
    # RATE LIMIT
    # ============================================================

    if (
        re.search(
            r"\b429\b",
            text,
        )
        or "rate limit" in text
        or "too many requests" in text
    ):
        return FailureKind.RATE_LIMIT

    # ============================================================
    # TEMPORARY SERVER ERRORS
    # ============================================================

    if re.search(
        r"\b(500|502|503|504)\b",
        text,
    ):
        return FailureKind.TEMPORARY

    if (
        "unavailable" in text
        or "high demand" in text
        or "bad gateway" in text
        or "service unavailable" in text
    ):
        return FailureKind.TEMPORARY

    # ============================================================
    # EMPTY
    # ============================================================

    if (
        "resposta vazia" in text
        or "empty response" in text
        or "nenhuma choice" in text
    ):
        return FailureKind.EMPTY

    # ============================================================
    # TIMEOUT textual
    # ============================================================

    if (
        "timeout" in text
        or "timed out" in text
    ):
        return FailureKind.TIMEOUT

    return FailureKind.UNKNOWN


def apply_failure_policy(
    provider_name: str,
    kind: FailureKind,
    error: str,
):

    health.mark_failure(
        provider=provider_name,
        kind=kind,
        error=error,
    )

    # ============================================================
    # ERROS PERMANENTES
    # ============================================================

    if kind in {
        FailureKind.AUTH,
        FailureKind.PAYMENT,
    }:

        health.block(
            provider=provider_name,
            reason=error,
            kind=kind,
        )

        return

    # ============================================================
    # RATE LIMIT
    # ============================================================

    if kind == FailureKind.RATE_LIMIT:

        cooldowns.set(
            provider=provider_name,
            seconds=60,
            reason=error,
        )

        return

    # ============================================================
    # TEMPORARY
    # ============================================================

    if kind == FailureKind.TEMPORARY:

        cooldowns.set(
            provider=provider_name,
            seconds=30,
            reason=error,
        )

        return

    # ============================================================
    # TIMEOUT
    # ============================================================

    if kind == FailureKind.TIMEOUT:

        cooldowns.set(
            provider=provider_name,
            seconds=20,
            reason=error,
        )

        return

    # ============================================================
    # EMPTY RESPONSE
    # ============================================================

    if kind == FailureKind.EMPTY:

        cooldowns.set(
            provider=provider_name,
            seconds=10,
            reason=error,
        )

        return

    # ============================================================
    # UNKNOWN
    # ============================================================

    cooldowns.set(
        provider=provider_name,
        seconds=15,
        reason=error,
    )


async def execute_fallback_chain(
    chain: list[str],
    route: RouteType,
    messages: list[dict],
    images: list[ImageInput] | None = None,
    temperature: float = 0.9,
    max_tokens: int = 1600,
) -> OrchestratorResult:

    attempts: list[
        AttemptLog
    ] = []

    for provider_name in chain:

        provider = PROVIDERS.get(
            provider_name
        )

        # ========================================================
        # PROVIDER NÃO EXISTE
        # ========================================================

        if provider is None:

            attempts.append(
                AttemptLog(
                    provider=provider_name,
                    skipped=True,
                    reason=(
                        "Provider não encontrado "
                        "no registry."
                    ),
                )
            )

            continue

        # ========================================================
        # DESABILITADO PELO .ENV
        # ========================================================

        if not provider_enabled(
            provider_name
        ):

            attempts.append(
                AttemptLog(
                    provider=provider_name,
                    model=provider.model,
                    skipped=True,
                    reason=(
                        "Provider desabilitado."
                    ),
                )
            )

            continue

        # ========================================================
        # SEM API KEY
        # ========================================================

        if not provider.configured:

            attempts.append(
                AttemptLog(
                    provider=provider_name,
                    model=provider.model,
                    skipped=True,
                    reason=(
                        "API key não configurada."
                    ),
                )
            )

            continue

        if images and not provider.supports_vision:
            attempts.append(
                AttemptLog(
                    provider=provider_name,
                    model=provider.model,
                    skipped=True,
                    reason="Provider não suporta visão.",
                )
            )
            continue

        # ========================================================
        # BLOCK / COOLDOWN
        # ========================================================

        if not health.can_use(
            provider_name
        ):

            state = health.state(
                provider_name
            )

            attempts.append(
                AttemptLog(
                    provider=provider_name,
                    model=provider.model,
                    skipped=True,
                    reason=(
                        f"Provider indisponível: "
                        f"{state.value}"
                    ),
                )
            )

            continue

        # ========================================================
        # CHAMADA REAL
        # ========================================================

        try:

            configured_timeout = _timeout_seconds(route)
            provider_timeout = provider.timeout_budget()
            timeout = max(configured_timeout, provider_timeout)
            logger.info(
                "rota=%s provider=%s timeout=%.1fs imagens=%s",
                route.value,
                provider_name,
                timeout,
                bool(images),
            )

            response = await asyncio.wait_for(
                provider.chat(
                    messages=messages,
                    images=images,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout=timeout,
            )

            # ====================================================
            # SUCESSO
            # ====================================================

            health.mark_success(
                provider_name
            )
            logger.info("sucesso rota=%s provider=%s modelo=%s", route.value, provider_name, response.model)

            attempts.append(
                AttemptLog(
                    provider=provider_name,
                    model=response.model,
                    success=True,
                )
            )

            return OrchestratorResult(
                content=response.content,
                provider=response.provider,
                model=response.model,
                route=route,
                attempts=attempts,
            )

        # ========================================================
        # TIMEOUT
        # ========================================================

        except asyncio.TimeoutError:

            error = (
                "Provider excedeu o timeout "
                f"de {timeout:.0f} segundos."
            )
            kind = FailureKind.TIMEOUT

            apply_failure_policy(
                provider_name=provider_name,
                kind=kind,
                error=error,
            )

            attempts.append(
                AttemptLog(
                    provider=provider_name,
                    model=provider.model,
                    failure_kind=kind,
                    reason=error,
                )
            )

            continue

        # ========================================================
        # QUALQUER OUTRO ERRO
        # ========================================================

        except Exception as exc:

            error = str(
                exc
            )

            kind = classify_failure(
                exc
            )

            apply_failure_policy(
                provider_name=provider_name,
                kind=kind,
                error=error,
            )
            logger.warning("falha rota=%s provider=%s tipo=%s", route.value, provider_name, kind.value)

            attempts.append(
                AttemptLog(
                    provider=provider_name,
                    model=provider.model,
                    failure_kind=kind,
                    reason=error,
                )
            )

            continue

    # ============================================================
    # TODO MUNDO MORREU
    # ============================================================

    raise OrchestrationError(
        message=(
            "Nenhum provider conseguiu "
            "responder à solicitação."
        ),
        attempts=attempts,
    )
