"""
Kaasb Platform - Async Circuit Breaker
Prevents cascading failures when external services (Qi Card, etc.) are down.

States:
  CLOSED    — normal operation, requests pass through
  OPEN      — service is down, requests fail fast without calling the service
  HALF_OPEN — testing recovery: one probe request allowed through

Usage::

    cb = CircuitBreaker(name="qi_card", failure_threshold=5, recovery_timeout=30)

    try:
        result = await cb.call(client.create_payment, amount_iqd=131000, ...)
    except CircuitOpenError:
        # fail fast — no network call was made
        raise ExternalServiceError("Payment service temporarily unavailable")
"""

import asyncio
import logging
import time
from collections.abc import Callable
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when the circuit is OPEN and a call is attempted."""

    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit '{name}' is OPEN — retry after {retry_after:.0f}s"
        )


class CircuitBreaker:
    """
    Async circuit breaker for protecting external service calls.

    Args:
        name:               Identifier used in log messages.
        failure_threshold:  Number of consecutive failures before opening the circuit.
        recovery_timeout:   Seconds to wait in OPEN state before probing (HALF_OPEN).
        success_threshold:  Consecutive successes in HALF_OPEN needed to re-close.
        exceptions:         Exception types that count as failures.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
        exceptions: tuple = (Exception,),
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.exceptions = exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable, *args, **kwargs):
        """
        Execute *func* through the circuit breaker.

        Raises:
            CircuitOpenError: if the circuit is OPEN (fail fast).
            Exception: any exception from *func* (also recorded as a failure).
        """
        async with self._lock:
            await self._maybe_attempt_reset()

            if self._state == CircuitState.OPEN:
                retry_after = (self._opened_at or 0) + self.recovery_timeout - time.monotonic()
                raise CircuitOpenError(self.name, max(0.0, retry_after))

        # Call happens outside the lock so we don't block other coroutines
        try:
            result = await func(*args, **kwargs)
        except self.exceptions:
            async with self._lock:
                await self._on_failure()
            raise

        async with self._lock:
            await self._on_success()

        return result

    def reset(self) -> None:
        """Manually close the circuit (useful in tests or after maintenance)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None
        logger.info("Circuit '%s' manually reset to CLOSED", self.name)

    # ------------------------------------------------------------------
    # Internal state machine
    # ------------------------------------------------------------------

    async def _maybe_attempt_reset(self) -> None:
        """Transition OPEN → HALF_OPEN when the recovery timeout has elapsed."""
        if (
            self._state == CircuitState.OPEN
            and self._opened_at is not None
            and time.monotonic() - self._opened_at >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
            logger.info(
                "Circuit '%s' → HALF_OPEN (probing after %ds)",
                self.name, self.recovery_timeout,
            )

    async def _on_failure(self) -> None:
        self._failure_count += 1
        self._success_count = 0

        if self._state == CircuitState.HALF_OPEN:
            # Probe failed — re-open immediately
            self._trip()
        elif self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
            self._trip()

    async def _on_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._opened_at = None
                logger.info("Circuit '%s' → CLOSED (service recovered)", self.name)
        elif self._state == CircuitState.CLOSED:
            # Reset failure streak on any success
            self._failure_count = 0

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        logger.error(
            "Circuit '%s' → OPEN after %d failures (recovery in %ds)",
            self.name, self._failure_count, self.recovery_timeout,
        )
