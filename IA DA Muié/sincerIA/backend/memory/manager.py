"""Memórias opt-in por regra: poucas, explícitas e recuperadas por relevância."""

from __future__ import annotations

import re

from backend.data.repositories import MemoryRepository


class MemoryManager:
    _RULES = (
        ("preference", re.compile(r"\b(?:eu gosto de|eu adoro|eu prefiro)\s+(.+)", re.IGNORECASE)),
        ("dislike", re.compile(r"\b(?:eu odeio|eu não gosto de)\s+(.+)", re.IGNORECASE)),
        ("person", re.compile(r"\b(?:meu nome é|eu me chamo)\s+(.+)", re.IGNORECASE)),
        ("relationship", re.compile(r"\b(?:meu namorado|minha namorada|meu marido|minha esposa)\s+(.+)", re.IGNORECASE)),
    )

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def remember_if_relevant(self, message: str, conversation_id: str) -> None:
        """Persiste somente declarações claras da própria pessoa, não suposições."""
        cleaned = " ".join(message.split())
        if len(cleaned) < 8 or len(cleaned) > 350:
            return
        for category, pattern in self._RULES:
            if pattern.search(cleaned):
                self.repository.add(cleaned, category, importance=2, conversation_id=conversation_id)
                return

    def context_for(self, message: str) -> list[str]:
        return self.repository.relevant(message, limit=4)
