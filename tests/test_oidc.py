import json
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from actions_tool_kit.oidc import get_id_token


def _mock_response(payload: dict) -> MagicMock:
    """Build a mock urllib response that returns JSON."""
    mock = MagicMock()
    mock.read.return_value = json.dumps(payload).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_get_id_token_success(monkeypatch):
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://token.example.com/token")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "runtime-bearer")

    with patch("actions_tool_kit.oidc.urllib.request.urlopen") as mock_open:
        mock_open.return_value = _mock_response({"value": "eyJhbGciOiJSUzI1NiJ9.payload.sig"})
        token = get_id_token()

    assert token == "eyJhbGciOiJSUzI1NiJ9.payload.sig"


def test_get_id_token_with_audience(monkeypatch):
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://token.example.com/token?foo=bar")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "tok")

    captured_urls = []

    def fake_urlopen(req):
        captured_urls.append(req.full_url)
        return _mock_response({"value": "jwt"})

    with patch("actions_tool_kit.oidc.urllib.request.urlopen", side_effect=fake_urlopen):
        get_id_token(audience="https://example.com")

    assert "audience=https%3A%2F%2Fexample.com" in captured_urls[0]


def test_get_id_token_missing_url_raises(monkeypatch):
    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_URL", raising=False)
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "tok")

    with pytest.raises(RuntimeError, match="OIDC token not available"):
        get_id_token()


def test_get_id_token_missing_token_raises(monkeypatch):
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://token.example.com/token")
    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="OIDC token not available"):
        get_id_token()


def test_get_id_token_sends_auth_header(monkeypatch):
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://token.example.com/token")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "my-runtime-token")

    captured_requests = []

    def fake_urlopen(req):
        captured_requests.append(req)
        return _mock_response({"value": "jwt"})

    with patch("actions_tool_kit.oidc.urllib.request.urlopen", side_effect=fake_urlopen):
        get_id_token()

    assert captured_requests[0].get_header("Authorization") == "Bearer my-runtime-token"
