from backend.core.config import settings
from backend.core.prompts import MODES
from backend.services.providers import (
    call_groq,
    call_openrouter,
)


def classify_nuclear_route(message: str) -> str:
    """
    Roteamento inicial simples.

    Depois vamos substituir isso por uma classificação
    mais inteligente baseada em contexto, tamanho,
    visão, histórico e disponibilidade das APIs.
    """

    text = message.lower()

    complex_keywords = [
        "analisa",
        "analise",
        "explica",
        "explique",
        "por que",
        "porque",
        "o que você faria",
        "conselho",
        "decisão",
        "decisao",
        "relacionamento",
        "trabalho",
    ]

    roast_keywords = [
        "roast",
        "me julga",
        "me julgue",
        "fala na lata",
        "sem dó",
        "sem do",
        "seja sincera",
        "sinceridade",
        "humilha",
    ]

    if any(word in text for word in roast_keywords):
        return "venice"

    if (
        len(message) > 800
        or any(word in text for word in complex_keywords)
    ):
        return "gpt_oss_120b"

    return "gpt_oss_20b"


async def generate_response(
    message: str,
    mode: str,
    history: list[dict],
):
    system_prompt = MODES.get(
        mode,
        MODES["normal"],
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        *history[-12:],
        {
            "role": "user",
            "content": message,
        },
    ]

    # =============================
    # ☢️ NUCLEAR ROUTER
    # =============================

    if mode == "nuclear":

        route = classify_nuclear_route(message)

        if route == "venice":
            try:
                response = await call_openrouter(
                    model=settings.VENICE_MODEL,
                    messages=messages,
                    temperature=1.05,
                )

                return {
                    "response": response,
                    "provider": "openrouter",
                    "model": settings.VENICE_MODEL,
                }

            except Exception:
                # Venice estourou limite?
                # Cai automaticamente para Qwen.
                pass

        if route == "gpt_oss_120b":
            try:
                response = await call_groq(
                    model=settings.GPT_OSS_POWER_MODEL,
                    messages=messages,
                    temperature=0.95,
                )

                return {
                    "response": response,
                    "provider": "groq",
                    "model": settings.GPT_OSS_POWER_MODEL,
                }

            except Exception:
                pass

        if route == "gpt_oss_20b":
            try:
                response = await call_groq(
                    model=settings.GPT_OSS_FAST_MODEL,
                    messages=messages,
                    temperature=1.0,
                )

                return {
                    "response": response,
                    "provider": "groq",
                    "model": settings.GPT_OSS_FAST_MODEL,
                }

            except Exception:
                pass

        # FALLBACK UNIVERSAL
        response = await call_groq(
            model=settings.QWEN_MODEL,
            messages=messages,
            temperature=0.9,
        )

        return {
            "response": response,
            "provider": "groq",
            "model": settings.QWEN_MODEL,
        }

    # =============================
    # OUTROS MODOS
    # =============================

    response = await call_groq(
        model=settings.QWEN_MODEL,
        messages=messages,
        temperature=0.8,
    )

    return {
        "response": response,
        "provider": "groq",
        "model": settings.QWEN_MODEL,
    }