from app.circuit_breaker import CircuitBreaker, CircuitState


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_starts_closed():
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.state is CircuitState.CLOSED
    assert cb.allow_request() is True


def test_opens_after_threshold_failures():
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10, now=clock)
    cb.record_failure()
    cb.record_failure()
    assert cb.state is CircuitState.CLOSED
    cb.record_failure()
    assert cb.state is CircuitState.OPEN
    assert cb.allow_request() is False


def test_half_open_after_cooldown():
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=10, now=clock)
    cb.record_failure()
    assert cb.state is CircuitState.OPEN
    clock.advance(10)
    assert cb.allow_request() is True
    assert cb.state is CircuitState.HALF_OPEN


def test_closes_after_successful_probes():
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
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=10, now=clock)
    cb.record_failure()
    clock.advance(10)
    cb.allow_request()
    assert cb.state is CircuitState.HALF_OPEN
    cb.record_failure()
    assert cb.state is CircuitState.OPEN


def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.failure_count == 2
    cb.record_success()
    assert cb.failure_count == 0
    assert cb.state is CircuitState.CLOSED
