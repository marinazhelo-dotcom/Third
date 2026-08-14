import enum
import time
from collections.abc import Callable


class CircuitState(str, enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        half_open_max_probes: int = 3,
        now: Callable[[], float] = time.monotonic,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_probes = half_open_max_probes
        self._now = now
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._half_open_probes = 0

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def allow_request(self) -> bool:
        if self._state is CircuitState.OPEN:
            if self._now() >= self._opened_at + self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_probes = 0
                return True
            return False
        return True

    def record_success(self) -> None:
        if self._state is CircuitState.HALF_OPEN:
            self._half_open_probes += 1
            if self._half_open_probes >= self.half_open_max_probes:
                self._close()
            return
        self._close()

    def record_failure(self) -> None:
        if self._state is CircuitState.HALF_OPEN:
            self._open()
            return
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._open()

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._now()
        self._failure_count = 0

    def _close(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
        self._half_open_probes = 0
