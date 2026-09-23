import time
from dataclasses import dataclass


@dataclass
class CooldownEntry:
    provider: str

    until: float
    reason: str


class CooldownManager:
    def __init__(self):
        self._entries: dict[
            str,
            CooldownEntry,
        ] = {}

    def set(
        self,
        provider: str,
        seconds: int,
        reason: str,
    ):
        self._entries[provider] = CooldownEntry(
            provider=provider,
            until=time.time() + seconds,
            reason=reason,
        )

    def clear(
        self,
        provider: str,
    ):
        self._entries.pop(
            provider,
            None,
        )

    def is_active(
        self,
        provider: str,
    ) -> bool:

        entry = self._entries.get(
            provider
        )

        if not entry:
            return False

        if time.time() >= entry.until:

            self.clear(
                provider
            )

            return False

        return True

    def remaining(
        self,
        provider: str,
    ) -> int:

        entry = self._entries.get(
            provider
        )

        if not entry:
            return 0

        remaining = int(
            entry.until - time.time()
        )

        if remaining <= 0:

            self.clear(
                provider
            )

            return 0

        return remaining

    def get_reason(
        self,
        provider: str,
    ) -> str | None:

        entry = self._entries.get(
            provider
        )

        if not entry:
            return None

        return entry.reason

    def snapshot(self) -> dict:

        result = {}

        for provider in list(
            self._entries.keys()
        ):

            if not self.is_active(
                provider
            ):
                continue

            result[provider] = {
                "remaining_seconds": (
                    self.remaining(
                        provider
                    )
                ),
                "reason": (
                    self.get_reason(
                        provider
                    )
                ),
            }

        return result


cooldowns = CooldownManager()