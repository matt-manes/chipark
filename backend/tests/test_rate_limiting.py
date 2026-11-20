import asyncio

import pytest

from backend.tools import rate_limiting
from backend.tools.rate_limiting import (
    IpRateLimitCoordinator,
    IpRateLimitStore,
    RateLimitPolicy,
)


def test_store_rejects_requests_after_policy_is_exhausted() -> None:
    store: IpRateLimitStore = IpRateLimitStore(RateLimitPolicy(1, 60))

    first_decision: rate_limiting.RateLimitDecision = store.acquire_decision(
        "192.0.2.1"
    )
    second_decision: rate_limiting.RateLimitDecision = store.acquire_decision(
        "192.0.2.1"
    )

    assert first_decision.allowed is True
    assert second_decision.allowed is False
    assert second_decision.retry_after_seconds > 0


def test_store_flushes_ip_after_inactivity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_time: list[float] = [100.0]
    monkeypatch.setattr(rate_limiting, "monotonic", lambda: current_time[0])
    store: IpRateLimitStore = IpRateLimitStore(RateLimitPolicy(1, 60))

    store.acquire_decision("192.0.2.1")
    current_time[0] = 161.0
    store.flush_expired()

    decision: rate_limiting.RateLimitDecision = store.acquire_decision("192.0.2.1")
    assert decision.allowed is True


def test_coordinator_applies_authentication_limit_separately() -> None:
    coordinator: IpRateLimitCoordinator = IpRateLimitCoordinator(
        auth_policy="1/minute",
        global_policy="2/minute",
    )

    first_decision: rate_limiting.RateLimitDecision | None = (
        coordinator.acquire_decision("192.0.2.1", True)
    )
    second_decision: rate_limiting.RateLimitDecision | None = (
        coordinator.acquire_decision("192.0.2.1", True)
    )

    assert first_decision is None
    assert second_decision is not None
    assert second_decision.allowed is False


def test_coordinator_resets_state_when_cleanup_starts() -> None:
    coordinator: IpRateLimitCoordinator = IpRateLimitCoordinator(
        auth_policy="1/minute",
        global_policy="1/minute",
    )

    first_decision: rate_limiting.RateLimitDecision | None = (
        coordinator.acquire_decision("192.0.2.1", False)
    )

    async def start_and_stop() -> None:
        await coordinator.start_cleanup_tasks()
        await coordinator.stop_cleanup_tasks()

    asyncio.run(start_and_stop())
    second_decision: rate_limiting.RateLimitDecision | None = (
        coordinator.acquire_decision("192.0.2.1", False)
    )

    assert first_decision is None
    assert second_decision is None


def test_coordinator_starts_one_cleanup_task_per_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator: IpRateLimitCoordinator = IpRateLimitCoordinator(
        auth_policy="1/minute",
        global_policy="1/hour",
    )
    intervals: list[int] = []

    async def record_cleanup_interval(
        store: IpRateLimitStore,
        stop_event: asyncio.Event,
    ) -> None:
        intervals.append(store.cleanup_interval_seconds)
        await stop_event.wait()

    monkeypatch.setattr(coordinator, "_run_store_cleanup", record_cleanup_interval)

    async def start_and_stop() -> None:
        await coordinator.start_cleanup_tasks()
        await asyncio.sleep(0)
        await coordinator.stop_cleanup_tasks()

    asyncio.run(start_and_stop())

    assert sorted(intervals) == [60, 3600]
