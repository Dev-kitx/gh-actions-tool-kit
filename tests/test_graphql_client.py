import json
from unittest.mock import MagicMock, patch

import pytest

from actions_tool_kit.graphql_client import GraphQLError, graphql


# ---------------------------------------------------------------------------
# GraphQLError
# ---------------------------------------------------------------------------

def test_graphql_error_message():
    err = GraphQLError([{"message": "Field not found"}, {"message": "Unauthorized"}])
    assert "Field not found" in str(err)
    assert "Unauthorized" in str(err)
    assert err.errors[0]["message"] == "Field not found"


# ---------------------------------------------------------------------------
# graphql()
# ---------------------------------------------------------------------------

def _mock_resp(body: dict):
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = json.dumps(body).encode()
    return mock


def test_graphql_returns_data(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok123")
    response = {"data": {"repository": {"stargazerCount": 42}}}

    with patch("urllib.request.urlopen", return_value=_mock_resp(response)):
        data = graphql("query { repository { stargazerCount } }")

    assert data["repository"]["stargazerCount"] == 42


def test_graphql_raises_on_errors(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok123")
    response = {"errors": [{"message": "Could not resolve to a Repository"}]}

    with patch("urllib.request.urlopen", return_value=_mock_resp(response)):
        with pytest.raises(GraphQLError, match="Could not resolve"):
            graphql("query { repository(owner: \"\", name: \"\") { id } }")


def test_graphql_sends_variables(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok123")
    captured = {}

    def fake_urlopen(req):
        captured["body"] = json.loads(req.data)
        return _mock_resp({"data": {}})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        graphql("query($owner: String!) { viewer { login } }", variables={"owner": "octocat"})

    assert captured["body"]["variables"] == {"owner": "octocat"}


def test_graphql_uses_explicit_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    captured = {}

    def fake_urlopen(req):
        captured["auth"] = req.get_header("Authorization")
        return _mock_resp({"data": {}})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        graphql("{ viewer { login } }", token="explicit-tok")

    assert captured["auth"] == "Bearer explicit-tok"


def test_graphql_uses_custom_url(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    captured = {}

    def fake_urlopen(req):
        captured["url"] = req.full_url
        return _mock_resp({"data": {}})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        graphql("{ viewer { login } }", url="https://github.example.com/api/graphql")

    assert captured["url"] == "https://github.example.com/api/graphql"


def test_graphql_uses_env_graphql_url(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_GRAPHQL_URL", "https://ghe.corp/api/graphql")
    captured = {}

    def fake_urlopen(req):
        captured["url"] = req.full_url
        return _mock_resp({"data": {}})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        graphql("{ viewer { login } }")

    assert captured["url"] == "https://ghe.corp/api/graphql"


def test_graphql_no_token_raises(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        graphql("{ viewer { login } }")


def test_graphql_empty_data(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    with patch("urllib.request.urlopen", return_value=_mock_resp({"data": {}})):
        result = graphql("{ viewer { login } }")
    assert result == {}
