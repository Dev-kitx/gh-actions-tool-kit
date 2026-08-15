from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional, TypeVar

try:
    from github import Auth, Github, GithubException, RateLimitExceededException
except ImportError as _e:
    raise ImportError(
        "github_client requires PyGithub. "
        "Install it with: pip install 'gh-actions-tool-kit'"
    ) from _e

T = TypeVar("T")


def get_github_client(token: Optional[str] = None, **options: Any) -> Github:
    """Create an authenticated PyGitHub client.

    Resolves the token in this order:
    1. The ``token`` argument if provided.
    2. The ``GITHUB_TOKEN`` environment variable.

    Args:
        token: Personal access token or GITHUB_TOKEN value.
        **options: Extra keyword arguments forwarded to :class:`github.Github`
                   (e.g. ``base_url``, ``timeout``, ``per_page``).

    Returns:
        An authenticated :class:`github.Github` instance.

    Raises:
        RuntimeError: When no token is available from either source.
    """
    resolved = token or os.getenv("GITHUB_TOKEN")
    if not resolved:
        raise RuntimeError(
            "No GitHub token found. Pass token= or set the GITHUB_TOKEN "
            "environment variable."
        )
    return Github(auth=Auth.Token(resolved), **options)


def call_with_rate_limit_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    on_rate_limit: Optional[Callable[[int, float], None]] = None,
) -> T:
    """Call *fn* and automatically retry on GitHub rate limit errors.

    On a primary rate limit (``RateLimitExceededException``) the function
    sleeps until the ``x-ratelimit-reset`` epoch reported by GitHub, then
    retries.  On a secondary rate limit (HTTP 403 / 429 without a reset
    timestamp) it falls back to exponential backoff (30 s, 60 s, …).

    Args:
        fn: Zero-argument callable that makes one or more PyGitHub API calls.
        max_attempts: Maximum number of total attempts (default 3).
        on_rate_limit: Optional callback ``(attempt: int, wait_seconds: float)``
                       called before each sleep so callers can log progress.

    Returns:
        The return value of *fn*.

    Raises:
        RateLimitExceededException | GithubException: When all attempts are
            exhausted.

    Example::

        client = get_github_client()
        repo = call_with_rate_limit_retry(
            lambda: client.get_repo("owner/repo"),
            on_rate_limit=lambda attempt, wait: warning(f"Rate limited, waiting {wait:.0f}s"),
        )
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_exc: Exception = RuntimeError("No attempts made")
    backoff = 30.0

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except RateLimitExceededException as exc:
            last_exc = exc
            if attempt == max_attempts:
                break
            reset_ts = getattr(exc, "headers", {}) or {}
            reset = reset_ts.get("x-ratelimit-reset")
            if reset:
                wait = max(0.0, float(reset) - time.time()) + 1.0
            else:
                wait = backoff
                backoff *= 2
            if on_rate_limit:
                on_rate_limit(attempt, wait)
            time.sleep(wait)
        except GithubException as exc:
            if exc.status not in (403, 429):
                raise
            last_exc = exc
            if attempt == max_attempts:
                break
            headers = getattr(exc, "headers", {}) or {}
            reset = headers.get("x-ratelimit-reset")
            if reset:
                wait = max(0.0, float(reset) - time.time()) + 1.0
            else:
                wait = backoff
                backoff *= 2
            if on_rate_limit:
                on_rate_limit(attempt, wait)
            time.sleep(wait)

    raise last_exc


__all__ = [
    "get_github_client",
    "call_with_rate_limit_retry",
    "Github",
    "Auth",
    "GithubException",
    "RateLimitExceededException",
]
