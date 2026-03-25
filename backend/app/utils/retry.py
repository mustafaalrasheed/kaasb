"""
Kaasb Platform - Async Retry Decorator
Exponential backoff with jitter for all external service calls.
"""

import asyncio
import functools
import logging
import random
from collections.abc import Callable

logger = logging.getLogger(__name__)


def async_retry(
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Retry an async function with exponential backoff + ±20% jitter.

    Args:
        max_attempts: Total attempts including the first try.
        base_delay:   Initial wait in seconds.
        max_delay:    Upper bound on wait time.
        backoff_factor: Multiplier applied each retry: delay *= backoff_factor.
        exceptions:   Exception types to catch and retry on.

    Usage::

        @async_retry(max_attempts=3, exceptions=(httpx.RequestError,))
        async def call_payment_api(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                    # ±20% jitter prevents thundering herd on shared external services
                    jitter = delay * 0.2 * (2 * random.random() - 1)
                    wait = max(0.0, delay + jitter)
                    logger.warning(
                        "Attempt %d/%d for %s failed: %s — retrying in %.1fs",
                        attempt, max_attempts, func.__qualname__, exc, wait,
                    )
                    await asyncio.sleep(wait)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator
