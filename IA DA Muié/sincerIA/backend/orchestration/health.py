from dataclasses import dataclass

from backend.orchestration.cooldown import (
    cooldowns,
)
from backend.orchestration.types import (
    FailureKind,
    ProviderState,
)


@dataclass
class HealthRecord:
    state: ProviderState = (
        ProviderState.UNKNOWN
    )

    consecutive_failures: int = 0

    last_error: str | None = None

    last_failure_kind: (
        FailureKind | None
    ) = None


class HealthManager:
    def __init__(self):

        self._records: dict[
            str,
            HealthRecord,
        ] = {}

    def _get(
        self,
        provider: str,
    ) -> HealthRecord:

        if provider not in self._records:

            self._records[
                provider
            ] = HealthRecord()

        return self._records[
            provider
        ]

    def mark_success(
        self,
        provider: str,
    ):

        record = self._get(
            provider
        )

        record.state = (
            ProviderState.HEALTHY
        )

        record.consecutive_failures = 0

        record.last_error = None
        record.last_failure_kind = None

        cooldowns.clear(
            provider
        )

    def mark_failure(
        self,
        provider: str,
        kind: FailureKind,
        error: str,
    ):

        record = self._get(
            provider
        )

        record.consecutive_failures += 1

        record.last_error = error

        record.last_failure_kind = kind

        if kind in {
            FailureKind.AUTH,
            FailureKind.PAYMENT,
        }:

            record.state = (
                ProviderState.BLOCKED
            )

        else:

            record.state = (
                ProviderState.DEGRADED
            )

    def block(
        self,
        provider: str,
        reason: str,
        kind: FailureKind,
    ):

        record = self._get(
            provider
        )

        record.state = (
            ProviderState.BLOCKED
        )

        record.last_error = reason
        record.last_failure_kind = kind

    def unblock(
        self,
        provider: str,
    ):

        record = self._get(
            provider
        )

        record.state = (
            ProviderState.UNKNOWN
        )

        record.consecutive_failures = 0
        record.last_error = None
        record.last_failure_kind = None

        cooldowns.clear(
            provider
        )

    def can_use(
        self,
        provider: str,
    ) -> bool:

        record = self._get(
            provider
        )

        if (
            record.state
            == ProviderState.BLOCKED
        ):
            return False

        if cooldowns.is_active(
            provider
        ):
            return False

        return True

    def state(
        self,
        provider: str,
    ) -> ProviderState:

        record = self._get(
            provider
        )

        if cooldowns.is_active(
            provider
        ):
            return ProviderState.COOLDOWN

        return record.state

    def snapshot(self) -> dict:

        result = {}

        for provider in self._records:

            record = self._get(
                provider
            )

            state = self.state(
                provider
            )

            result[provider] = {
                "state": state.value,

                "consecutive_failures": (
                    record.consecutive_failures
                ),

                "last_failure_kind": (
                    record.last_failure_kind.value
                    if record.last_failure_kind
                    else None
                ),

                "last_error": (
                    record.last_error
                ),

                "cooldown_remaining": (
                    cooldowns.remaining(
                        provider
                    )
                ),
            }

        return result


health = HealthManager()