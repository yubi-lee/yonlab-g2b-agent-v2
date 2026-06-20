from dataclasses import dataclass, field
from enum import StrEnum


class SignalKind(StrEnum):
    FAVORABLE = "favorable"
    RISK = "risk"
    ELIGIBLE = "eligible"


class FitLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class EligibilitySignal:
    kind: SignalKind
    code: str
    message: str


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    fit: FitLevel
    signals: tuple[EligibilitySignal, ...] = field(default_factory=tuple)

    @property
    def favorable_signals(self) -> tuple[EligibilitySignal, ...]:
        return tuple(signal for signal in self.signals if signal.kind == SignalKind.FAVORABLE)

    @property
    def risk_signals(self) -> tuple[EligibilitySignal, ...]:
        return tuple(signal for signal in self.signals if signal.kind == SignalKind.RISK)

    @property
    def eligible_signals(self) -> tuple[EligibilitySignal, ...]:
        return tuple(signal for signal in self.signals if signal.kind == SignalKind.ELIGIBLE)
