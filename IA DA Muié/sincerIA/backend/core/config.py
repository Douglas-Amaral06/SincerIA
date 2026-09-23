import os

from dotenv import load_dotenv


load_dotenv()


class Settings:

    # ============================================================
    # API KEYS
    # ============================================================

    GROQ_API_KEY = os.getenv(
        "GROQ_API_KEY",
        "",
    )

    OPENROUTER_API_KEY = os.getenv(
        "OPENROUTER_API_KEY",
        "",
    )

    VENICE_API_KEY = os.getenv(
        "VENICE_API_KEY",
        "",
    )

    NVIDIA_API_KEY = os.getenv(
        "NVIDIA_API_KEY",
        "",
    )

    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY",
        "",
    )

    OLLAMA_API_KEY = os.getenv(
        "OLLAMA_API_KEY",
        "",
    )

    # ============================================================
    # BASE URLS
    # ============================================================

    GROQ_BASE_URL = (
        "https://api.groq.com/openai/v1"
    )

    OPENROUTER_BASE_URL = (
        "https://openrouter.ai/api/v1"
    )

    VENICE_BASE_URL = (
        "https://api.venice.ai/api/v1"
    )

    NVIDIA_BASE_URL = (
        "https://integrate.api.nvidia.com/v1"
    )

    OLLAMA_BASE_URL = (
        "https://ollama.com/api"
    )

    # ============================================================
    # GROQ
    # ============================================================

    QWEN_MODEL = os.getenv(
        "QWEN_MODEL",
        "qwen/qwen3.8-27b",
    )

    GPT_OSS_FAST_MODEL = os.getenv(
        "GPT_OSS_FAST_MODEL",
        "openai/gpt-oss-20b",
    )

    GPT_OSS_POWER_MODEL = os.getenv(
        "GPT_OSS_POWER_MODEL",
        "openai/gpt-oss-120b",
    )

    # ============================================================
    # OPENROUTER
    # ============================================================

    OPENROUTER_MODEL = os.getenv(
        "OPENROUTER_MODEL",
        "openrouter/free",
    )

    # ============================================================
    # VENICE
    # ============================================================

    VENICE_MODEL = os.getenv(
        "VENICE_MODEL",
        "venice-uncensored-1-2",
    )

    # ============================================================
    # NVIDIA
    # ============================================================

    NVIDIA_MODEL = os.getenv(
        "NVIDIA_MODEL",
        "nvidia/nemotron-3-super-120b-a12b",
    )

    # ============================================================
    # GEMINI
    # ============================================================

    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.8-flash",
    )

    GEMINI_FALLBACK_MODEL = os.getenv(
        "GEMINI_FALLBACK_MODEL",
        "gemini-3.5-flash-lite",
    )

    GEMINI_PRIMARY_TIMEOUT_SECONDS = float(
        os.getenv("GEMINI_PRIMARY_TIMEOUT_SECONDS", "15")
    )

    GEMINI_FALLBACK_TIMEOUT_SECONDS = float(
        os.getenv("GEMINI_FALLBACK_TIMEOUT_SECONDS", "25")
    )

    ORCHESTRATOR_TIMEOUT_SECONDS = float(
        os.getenv("ORCHESTRATOR_TIMEOUT_SECONDS", "45")
    )

    ORCHESTRATOR_VISION_TIMEOUT_SECONDS = float(
        os.getenv("ORCHESTRATOR_VISION_TIMEOUT_SECONDS", "45")
    )

    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/sincerIA.db")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/uploads")

    # ============================================================
    # OLLAMA
    # ============================================================

    OLLAMA_MODEL = os.getenv(
        "OLLAMA_MODEL",
        "glm-5.3-flash",
    )


settings = Settings()
