from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ImageInput:
    data: bytes
    mime_type: str
    filename: str | None = None


@dataclass(slots=True)
class ProviderResponse:
    content: str
    provider: str
    model: str


class ProviderError(Exception):
    """
    Erro genérico lançado por qualquer provider.

    O orquestrador futuramente vai capturar esse erro
    e automaticamente tentar o próximo modelo.
    """

    pass


class AIProvider(ABC):
    name: str = "unknown"
    supports_vision: bool = False

    def __init__(
        self,
        api_key: str,
        model: str,
    ):
        self.api_key = api_key
        self.model = model

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def timeout_budget(self) -> float:
        """Tempo mínimo necessário para o provider concluir seus próprios fallbacks."""
        return 0.0

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        images: Optional[list[ImageInput]] = None,
        temperature: float = 0.9,
        max_tokens: int = 1200,
    ) -> ProviderResponse:
        raise NotImplementedError
