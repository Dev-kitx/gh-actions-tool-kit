import pytest
from unittest.mock import MagicMock, patch

from actions_tool_kit.retry import retry


def test_retry_succeeds_first_attempt():
    fn = MagicMock(return_value=42)
    assert retry(fn, max_attempts=3) == 42
    fn.assert_called_once()


def test_retry_succeeds_after_failures():
    results = [ValueError("fail"), ValueError("fail"), "ok"]

    def fn():
        val = results.pop(0)
        if isinstance(val, Exception):
            raise val
        return val

    with patch("actions_tool_kit.retry.time.sleep"):
        result = retry(fn, max_attempts=3, delay=0.01)

    assert result == "ok"


def test_retry_raises_after_all_attempts():
    fn = MagicMock(side_effect=RuntimeError("always fails"))
    with patch("actions_tool_kit.retry.time.sleep"):
        with pytest.raises(RuntimeError, match="always fails"):
            retry(fn, max_attempts=3, delay=0.01)
    assert fn.call_count == 3


def test_retry_only_catches_specified_exceptions():
    fn = MagicMock(side_effect=ValueError("wrong type"))
    with pytest.raises(ValueError):
        retry(fn, max_attempts=5, exceptions=(TypeError,))
    fn.assert_called_once()


def test_retry_calls_on_retry_hook():
    hook = MagicMock()
    calls = [ValueError("e1"), ValueError("e2"), "done"]

    def fn():
        val = calls.pop(0)
        if isinstance(val, Exception):
            raise val
        return val

    with patch("actions_tool_kit.retry.time.sleep"):
        retry(fn, max_attempts=3, delay=0.01, on_retry=hook)

    assert hook.call_count == 2
    hook.assert_any_call(1, pytest.approx(hook.call_args_list[0][0][1]))


def test_retry_backoff_increases_delay():
    sleep_calls = []

    def fake_sleep(t):
        sleep_calls.append(t)

    fn = MagicMock(side_effect=[ValueError(), ValueError(), "ok"])
    with patch("actions_tool_kit.retry.time.sleep", side_effect=fake_sleep):
        retry(fn, max_attempts=3, delay=1.0, backoff=3.0)

    assert len(sleep_calls) == 2
    assert sleep_calls[0] == pytest.approx(1.0)
    assert sleep_calls[1] == pytest.approx(3.0)


def test_retry_max_attempts_one_no_sleep():
    fn = MagicMock(side_effect=RuntimeError("fail"))
    with patch("actions_tool_kit.retry.time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError):
            retry(fn, max_attempts=1)
    mock_sleep.assert_not_called()


def test_retry_invalid_max_attempts():
    with pytest.raises(ValueError, match="max_attempts"):
        retry(lambda: None, max_attempts=0)
