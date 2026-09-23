from openai import AsyncOpenAI

from backend.core.config import settings


groq_client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url=settings.GROQ_BASE_URL,
)


openrouter_client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
)


async def call_groq(
    model: str,
    messages: list[dict],
    temperature: float = 0.9,
) -> str:

    response = await groq_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=1200,
    )

    return response.choices[0].message.content


async def call_openrouter(
    model: str,
    messages: list[dict],
    temperature: float = 1.0,
) -> str:

    response = await openrouter_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=1200,
    )

    return response.choices[0].message.content