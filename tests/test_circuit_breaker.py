from app.circuit_breaker import CircuitBreaker, CircuitState


class FakeClock:
    """A manual clock injected as the breaker's `now` callable for tests."""

    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_starts_closed():
    """A new breaker starts closed and allows requests."""
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.state is CircuitState.CLOSED
    assert cb.allow_request() is True


def test_opens_after_threshold_failures():
    """After `failure_threshold` failures the breaker opens and blocks requests."""
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10, now=clock)
    cb.record_failure()
    cb.record_failure()
    assert cb.state is CircuitState.CLOSED
    cb.record_failure()
    assert cb.state is CircuitState.OPEN
    assert cb.allow_request() is False


def test_half_open_after_cooldown():
    """After the cooldown elapses, the breaker lets one probe through in half-open."""
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=10, now=clock)
    cb.record_failure()
    assert cb.state is CircuitState.OPEN
    clock.advance(10)
    assert cb.allow_request() is True
    assert cb.state is CircuitState.HALF_OPEN


def test_closes_after_successful_probes():
    """Enough successful probes in half-open close the circuit again."""
    clock = FakeClock()
    cb = CircuitBreaker(
        failure_threshold=1, cooldown_seconds=10, half_open_max_probes=2, now=clock
    )
    cb.record_failure()
    clock.advance(10)
    cb.allow_request()
    cb.record_success()
    assert cb.state is CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state is CircuitState.CLOSED


def test_reopens_on_failure_during_half_open():
    """A failure during half-open immediately reopens the circuit."""
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=10, now=clock)
    cb.record_failure()
    clock.advance(10)
    cb.allow_request()
    assert cb.state is CircuitState.HALF_OPEN
    cb.record_failure()
    assert cb.state is CircuitState.OPEN


def test_success_resets_failure_count():
    """A success in the closed state resets the failure counter."""
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.failure_count == 2
    cb.record_success()
    assert cb.failure_count == 0
    assert cb.state is CircuitState.CLOSED
