from dataclasses import dataclass, field
from enum import Enum


class RouteType(str, Enum):
    CONVERSATION = "conversation"
    REASONING = "reasoning"
    VISION = "vision"


class FailureKind(str, Enum):
    AUTH = "auth"
    PAYMENT = "payment"
    RATE_LIMIT = "rate_limit"
    TEMPORARY = "temporary"
    TIMEOUT = "timeout"
    EMPTY = "empty"
    UNKNOWN = "unknown"


class ProviderState(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    COOLDOWN = "cooldown"
    BLOCKED = "blocked"


@dataclass
class AttemptLog:
    provider: str
    model: str | None = None

    success: bool = False
    skipped: bool = False

    failure_kind: FailureKind | None = None

    reason: str | None = None


@dataclass
class OrchestratorResult:
    content: str

    provider: str
    model: str

    route: RouteType

    attempts: list[AttemptLog] = field(
        default_factory=list
    )


class OrchestrationError(RuntimeError):
    def __init__(
        self,
        message: str,
        attempts: list[AttemptLog] | None = None,
    ):
        super().__init__(message)

        self.attempts = attempts or []