import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from math import ceil
from threading import Lock
from time import monotonic
from typing import ClassVar

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


@dataclass(frozen=True)
class RateLimitPolicy:
    """Describe the request count allowed during a time window."""

    _WINDOW_SECONDS_BY_UNIT: ClassVar[dict[str, int]] = {
        "second": 1,
        "minute": 60,
        "hour": 60 * 60,
        "day": 24 * 60 * 60,
    }

    max_requests: int
    window_seconds: int

    @classmethod
    def from_value(cls, value: str) -> "RateLimitPolicy":
        """
        Parse a policy in ``count/unit`` format.

        Parameters
        ----------
        value : str
            Policy such as ``"5/minute"`` or ``"60/hour"``.

        Returns
        -------
        RateLimitPolicy
            Parsed request count and window.

        Raises
        ------
        ValueError
            If the policy format or values are invalid.
        """
        try:
            count_text, unit = value.casefold().split("/", maxsplit=1)
            max_requests: int = int(count_text)
        except ValueError as error:
            raise ValueError(
                "Rate limits must use the format '<positive integer>/<unit>'."
            ) from error

        window_seconds: int | None = cls._WINDOW_SECONDS_BY_UNIT.get(unit.strip())
        if max_requests <= 0 or window_seconds is None:
            raise ValueError(
                "Rate limits must use a positive count and second, minute, "
                "hour, or day as the unit."
            )
        return cls(max_requests, window_seconds)


@dataclass(frozen=True)
class RateLimitDecision:
    """Represent the result of attempting to consume one request allowance."""

    allowed: bool
    remaining: int
    retry_after_seconds: int


class IpRateLimitStore:
    """Track request timestamps for each client IP address."""

    def __init__(self, policy: RateLimitPolicy) -> None:
        """Initialize an empty store using ``policy``."""
        self._policy: RateLimitPolicy = policy
        self._requests_by_ip: defaultdict[str, deque[float]] = defaultdict(deque)

    def flush_expired(self) -> None:
        """
        Remove IP addresses inactive for longer than the policy window.

        This method assumes the caller serializes access to the store.
        """
        cutoff: float = monotonic() - self._policy.window_seconds
        expired_ips: list[str] = [
            client_ip
            for client_ip, timestamps in self._requests_by_ip.items()
            if not timestamps or timestamps[-1] <= cutoff
        ]
        for client_ip in expired_ips:
            del self._requests_by_ip[client_ip]

    def clear(self) -> None:
        """Remove all tracked IP addresses from the store."""
        self._requests_by_ip.clear()

    def acquire_decision(self, client_ip: str) -> RateLimitDecision:
        """
        Consume one request allowance for ``client_ip``.

        Parameters
        ----------
        client_ip : str
            Address identifying the caller.

        Returns
        -------
        RateLimitDecision
            Whether the request is allowed and, when blocked, when to retry.
        """
        now: float = monotonic()
        timestamps: deque[float] = self._requests_by_ip[client_ip]
        cutoff: float = now - self._policy.window_seconds
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) >= self._policy.max_requests:
            retry_after: int = max(
                1,
                ceil(timestamps[0] + self._policy.window_seconds - now),
            )
            return RateLimitDecision(False, 0, retry_after)

        timestamps.append(now)
        remaining: int = self._policy.max_requests - len(timestamps)
        return RateLimitDecision(True, remaining, 0)

    @property
    def cleanup_interval_seconds(self) -> int:
        """Return the store's cleanup interval."""
        return self._policy.window_seconds


class IpRateLimitCoordinator:
    """Coordinate rate-limit stores and their lifecycle cleanup tasks."""

    def __init__(self, auth_policy: str, global_policy: str) -> None:
        """
        Initialize rate-limit stores and their shared synchronization lock.

        Parameters
        ----------
        auth_policy : str
            Authentication endpoint limit in ``count/unit`` format.
        global_policy : str
            Global API endpoint limit in ``count/unit`` format.

        Raises
        ------
        ValueError
            If either policy is invalid.
        """
        self._auth_store: IpRateLimitStore = IpRateLimitStore(
            RateLimitPolicy.from_value(auth_policy)
        )
        self._global_store: IpRateLimitStore = IpRateLimitStore(
            RateLimitPolicy.from_value(global_policy)
        )
        self._lock: Lock = Lock()
        self._stop_event: asyncio.Event | None = None
        self._cleanup_tasks: list[asyncio.Task[None]] = []

    def acquire_decision(
        self,
        client_ip: str,
        is_authentication_request: bool,
    ) -> RateLimitDecision | None:
        """
        Acquire request allowances and return a rejection decision if limited.

        Parameters
        ----------
        client_ip : str
            Address identifying the caller.
        is_authentication_request : bool
            Whether the request should also use the authentication limit.

        Returns
        -------
        RateLimitDecision or None
            Rejection decision when a limit is exceeded, otherwise ``None``.
        """
        with self._lock:
            global_decision: RateLimitDecision = self._global_store.acquire_decision(
                client_ip
            )
            if not global_decision.allowed:
                return global_decision

            if is_authentication_request:
                auth_decision: RateLimitDecision = self._auth_store.acquire_decision(
                    client_ip
                )
                if not auth_decision.allowed:
                    return auth_decision
        return None

    async def start_cleanup_tasks(self) -> None:
        """Start one periodic cleanup task for each rate-limit store."""
        if self._cleanup_tasks:
            return
        self.reset()
        self._stop_event = asyncio.Event()
        self._cleanup_tasks = [
            asyncio.create_task(
                self._run_store_cleanup(self._global_store, self._stop_event),
                name="chipark-global-rate-limit-cleanup",
            ),
            asyncio.create_task(
                self._run_store_cleanup(self._auth_store, self._stop_event),
                name="chipark-auth-rate-limit-cleanup",
            ),
        ]

    async def stop_cleanup_tasks(self) -> None:
        """Stop and await all periodic rate-limit cleanup tasks."""
        if self._stop_event is None:
            return
        self._stop_event.set()
        await asyncio.gather(*self._cleanup_tasks)
        self._cleanup_tasks = []
        self._stop_event = None

    def reset(self) -> None:
        """Clear all process-local rate-limit state."""
        with self._lock:
            self._global_store.clear()
            self._auth_store.clear()

    async def _run_store_cleanup(
        self,
        store: IpRateLimitStore,
        stop_event: asyncio.Event,
    ) -> None:
        """
        Periodically flush one store until the application shuts down.

        Parameters
        ----------
        store : IpRateLimitStore
            Store to flush.
        stop_event : asyncio.Event
            Event indicating application shutdown.
        """
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=store.cleanup_interval_seconds,
                )
            except TimeoutError:
                with self._lock:
                    store.flush_expired()


class IpRateLimitMiddleware(BaseHTTPMiddleware):
    """Apply configurable per-IP request limits to the backend."""

    _AUTHENTICATION_PATHS: frozenset[str] = frozenset(
        {"/auth/login", "/auth/register", "/auth/google"}
    )

    def __init__(
        self,
        app: ASGIApp,
        rate_limit_coordinator: IpRateLimitCoordinator,
    ) -> None:
        """
        Initialize middleware with its rate-limit coordinator.

        Parameters
        ----------
        app : ASGIApp
            ASGI application wrapped by the middleware.
        rate_limit_coordinator : IpRateLimitCoordinator
            Coordinator managing request allowances and cleanup tasks.
        """
        super().__init__(app)
        self._rate_limit_coordinator: IpRateLimitCoordinator = rate_limit_coordinator

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Reject requests that exceed the configured per-IP allowance.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        call_next : RequestResponseEndpoint
            Next middleware or application handler.

        Returns
        -------
        Response
            Either a 429 response or the downstream response.
        """
        if request.method == "OPTIONS":
            return await call_next(request)

        client_ip: str = request.client.host if request.client else "unknown"
        decision: RateLimitDecision | None = (
            self._rate_limit_coordinator.acquire_decision(
                client_ip,
                request.url.path in self._AUTHENTICATION_PATHS,
            )
        )
        if decision is not None:
            return self._build_limit_response(decision)

        return await call_next(request)

    @staticmethod
    def _build_limit_response(decision: RateLimitDecision) -> JSONResponse:
        """Build a standard response for an exhausted rate-limit window."""
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Try again later."},
            headers={
                "Retry-After": str(decision.retry_after_seconds),
                "X-RateLimit-Remaining": str(decision.remaining),
            },
        )
