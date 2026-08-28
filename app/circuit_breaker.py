import enum
import time
from collections.abc import Callable

import structlog

logger = structlog.get_logger()

# Prometheus gauge for circuit breaker state (imported lazily to avoid circular deps)
_CB_STATE_GAUGE = None


def _get_cb_gauge():
    """Lazy-import the circuit breaker state gauge from shared.metrics."""
    global _CB_STATE_GAUGE
    if _CB_STATE_GAUGE is None:
        from shared.metrics import CIRCUIT_BREAKER_STATE
        _CB_STATE_GAUGE = CIRCUIT_BREAKER_STATE
    return _CB_STATE_GAUGE


class CircuitState(str, enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    ''' The Circuit Breaker pattern helps to prevent a cascading failure of a system.
    The idea: a remote service can fail, and hammering it while it's down just makes things worse
    so you wrap calls to it in a state machine that stops sending requests once enough failures happen,
    gives the service time to recover, then cautiously re-allows traffic.
    '''
    def __init__(
        self,
        source_name: str = "unknown",
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        half_open_max_probes: int = 3,
        now: Callable[[], float] = time.monotonic,
        # Callable[[], float] -> [] types of arguments, float -> return type
    ):
        self.source_name = source_name
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

    def _update_gauge(self) -> None:
        """Push the current state to the Prometheus gauge."""
        try:
            gauge = _get_cb_gauge()
            gauge.labels(source=self.source_name).set(
                list(CircuitState).index(self._state)
            )
        except Exception:
            pass

    def allow_request(self) -> bool:
        '''
        Checks if the circuit breaker allows a request to be made.
        If the circuit is open - dont
        If the circuit is closed - go
        If the circuit is half open and it's time to try again - go
        '''
        if self._state is CircuitState.OPEN:
            if self._now() >= self._opened_at + self.cooldown_seconds:
                old = self._state
                self._state = CircuitState.HALF_OPEN
                self._half_open_probes = 0
                logger.info("circuit_breaker_state_changed",
                    source=self.source_name, old_state=old.value,
                    new_state=self._state.value, failure_count=self._failure_count)
                self._update_gauge()
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
        '''
        Records a failed request.
        If the circuit was half open, it will open the circuit again.
        If the circuit was closed, it will increment the failure count.
        and when failure count is greater than the failure threshold, it will open the circuit.
        '''
        if self._state is CircuitState.HALF_OPEN:
            self._open()
            return
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._open()

    def _open(self) -> None:
        old = self._state
        self._state = CircuitState.OPEN
        self._opened_at = self._now()
        self._failure_count = 0
        logger.warning("circuit_breaker_state_changed",
            source=self.source_name, old_state=old.value,
            new_state=self._state.value)
        self._update_gauge()

    def _close(self) -> None:
        old = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
        self._half_open_probes = 0
        if old != CircuitState.CLOSED:
            logger.info("circuit_breaker_state_changed",
                source=self.source_name, old_state=old.value,
                new_state=self._state.value)
        self._update_gauge()
