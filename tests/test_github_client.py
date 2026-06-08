import time
import pytest
from github import Github, GithubException, RateLimitExceededException
from unittest.mock import patch, MagicMock
from actions_tool_kit.github_client import get_github_client, call_with_rate_limit_retry


def test_get_github_client_explicit_token():
    client = get_github_client("ghp_test1234567890")
    assert isinstance(client, Github)


def test_get_github_client_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_token")
    client = get_github_client()
    assert isinstance(client, Github)


def test_get_github_client_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_token")
    client = get_github_client("ghp_explicit")
    assert isinstance(client, Github)


def test_get_github_client_no_token_raises(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        get_github_client()


def test_get_github_client_with_options():
    client = get_github_client(
        "ghp_testtoken",
        base_url="https://api.github.com",
        timeout=20,
        per_page=50,
    )
    assert isinstance(client, Github)
    assert callable(client.get_rate_limit)


# ---------------------------------------------------------------------------
# call_with_rate_limit_retry
# ---------------------------------------------------------------------------

def test_call_with_rate_limit_retry_succeeds_immediately():
    result = call_with_rate_limit_retry(lambda: 42)
    assert result == 42


def test_call_with_rate_limit_retry_retries_on_rate_limit():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise RateLimitExceededException(403, "rate limit", {})
        return "ok"

    with patch("actions_tool_kit.github_client.time.sleep"):
        result = call_with_rate_limit_retry(flaky, max_attempts=3)

    assert result == "ok"
    assert len(calls) == 3


def test_call_with_rate_limit_retry_exhausted_raises():
    def always_rate_limited():
        raise RateLimitExceededException(403, "rate limit", {})

    with patch("actions_tool_kit.github_client.time.sleep"):
        with pytest.raises(RateLimitExceededException):
            call_with_rate_limit_retry(always_rate_limited, max_attempts=2)


def test_call_with_rate_limit_retry_reraises_non_rate_limit():
    def bad_request():
        raise GithubException(422, "Unprocessable", {})

    with pytest.raises(GithubException) as exc_info:
        call_with_rate_limit_retry(bad_request)

    assert exc_info.value.status == 422


def test_call_with_rate_limit_retry_on_rate_limit_callback():
    callback_args = []

    def flaky():
        if len(callback_args) < 1:
            raise RateLimitExceededException(403, "rate limit", {})
        return "done"

    def on_rl(attempt, wait):
        callback_args.append((attempt, wait))

    with patch("actions_tool_kit.github_client.time.sleep"):
        result = call_with_rate_limit_retry(flaky, max_attempts=3, on_rate_limit=on_rl)

    assert result == "done"
    assert len(callback_args) == 1
    assert callback_args[0][0] == 1  # first attempt


def test_call_with_rate_limit_retry_uses_reset_header():
    future_reset = str(int(time.time()) + 60)
    slept = []

    def flaky():
        if not slept:
            raise RateLimitExceededException(403, "rate limit", {"x-ratelimit-reset": future_reset})
        return "ok"

    def fake_sleep(secs):
        slept.append(secs)

    with patch("actions_tool_kit.github_client.time.sleep", side_effect=fake_sleep):
        call_with_rate_limit_retry(flaky, max_attempts=2)

    assert len(slept) == 1
    assert slept[0] > 0  # slept some positive amount


def test_call_with_rate_limit_retry_handles_403_github_exception():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise GithubException(403, "secondary rate limit", {})
        return "recovered"

    with patch("actions_tool_kit.github_client.time.sleep"):
        result = call_with_rate_limit_retry(flaky, max_attempts=3)

    assert result == "recovered"


def test_call_with_rate_limit_retry_invalid_max_attempts():
    with pytest.raises(ValueError):
        call_with_rate_limit_retry(lambda: None, max_attempts=0)
