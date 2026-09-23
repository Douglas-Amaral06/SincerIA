from backend.core.config import settings

from backend.providers.gemini import GeminiProvider
from backend.providers.groq import GroqProvider
from backend.providers.nvidia import NvidiaProvider
from backend.providers.ollama import OllamaProvider
from backend.providers.openrouter import OpenRouterProvider
from backend.providers.venice import VeniceProvider


# ================================================================
# GROQ
# ================================================================

groq_qwen = GroqProvider(
    model=settings.QWEN_MODEL,
)

# Estado de falhas separado: uma imagem inválida não suspende o chat de texto.
groq_vision = GroqProvider(
    model=settings.QWEN_MODEL,
)

groq_fast = GroqProvider(
    model=settings.GPT_OSS_FAST_MODEL,
)

groq_power = GroqProvider(
    model=settings.GPT_OSS_POWER_MODEL,
)


# ================================================================
# OPENROUTER
# ================================================================

openrouter = OpenRouterProvider()


# ================================================================
# VENICE
# ================================================================

venice = VeniceProvider()


# ================================================================
# NVIDIA
# ================================================================

nvidia = NvidiaProvider()


# ================================================================
# GEMINI
# ================================================================

gemini = GeminiProvider()


# ================================================================
# OLLAMA
# ================================================================

ollama = OllamaProvider()


# ================================================================
# REGISTRY
# ================================================================

PROVIDERS = {
    "venice": venice,

    "groq_qwen": groq_qwen,
    "groq_vision": groq_vision,
    "groq_fast": groq_fast,
    "groq_power": groq_power,

    "openrouter": openrouter,

    "nvidia": nvidia,

    "gemini": gemini,

    "ollama": ollama,
}


def get_provider(
    name: str,
):
    provider = PROVIDERS.get(name)

    if provider is None:
        raise ValueError(
            f"Provider desconhecido: {name}"
        )

    return provider
