from __future__ import annotations

import time
from typing import Callable, Optional, Tuple, Type, TypeVar

T = TypeVar("T")


def retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> T:
    """Retry a zero-argument callable with exponential backoff.

    Args:
        fn: Callable to invoke. Must take no arguments.
        max_attempts: Maximum total invocations (must be >= 1).
        delay: Seconds to wait before the second attempt.
        backoff: Multiplier applied to delay after each failure.
        exceptions: Exception types that trigger a retry.  Any other exception
                    propagates immediately without retrying.
        on_retry: Optional hook called as ``on_retry(attempt, exc)`` just before
                  sleeping, where ``attempt`` is the 1-based attempt number that
                  just failed. Useful for logging.

    Returns:
        The return value of *fn* on success.

    Raises:
        ValueError: When max_attempts < 1.
        Exception: The last exception raised by *fn* after all attempts fail.

    Example::

        result = retry(lambda: requests.get(url), max_attempts=5, delay=0.5)
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    current_delay = delay
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except exceptions as exc:
            last_exc = exc
            if attempt == max_attempts:
                break
            if on_retry is not None:
                on_retry(attempt, exc)
            time.sleep(current_delay)
            current_delay *= backoff

    raise last_exc  # type: ignore[misc]


__all__ = ["retry"]
