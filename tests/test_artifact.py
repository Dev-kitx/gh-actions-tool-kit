import json
import pytest
from unittest.mock import patch, MagicMock

from actions_tool_kit.artifact import ArtifactClient, ArtifactInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(monkeypatch, url="https://runtime.example.com/", token="runtime-tok", run_id="42"):
    monkeypatch.setenv("ACTIONS_RUNTIME_URL", url)
    monkeypatch.setenv("ACTIONS_RUNTIME_TOKEN", token)
    monkeypatch.setenv("GITHUB_RUN_ID", run_id)


def _mock_urlopen(responses: list):
    """Return a context-manager mock that yields json payloads in order."""
    mocks = []
    for payload in responses:
        m = MagicMock()
        m.read.return_value = json.dumps(payload).encode() if payload is not None else b""
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        mocks.append(m)
    return iter(mocks)


# ---------------------------------------------------------------------------
# ArtifactClient construction
# ---------------------------------------------------------------------------

def test_client_raises_without_runtime_url(monkeypatch):
    monkeypatch.delenv("ACTIONS_RUNTIME_URL", raising=False)
    monkeypatch.setenv("ACTIONS_RUNTIME_TOKEN", "tok")
    with pytest.raises(RuntimeError, match="ACTIONS_RUNTIME_URL"):
        ArtifactClient()


def test_client_raises_without_token(monkeypatch):
    monkeypatch.setenv("ACTIONS_RUNTIME_URL", "https://runtime.example.com/")
    monkeypatch.delenv("ACTIONS_RUNTIME_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="ACTIONS_RUNTIME_TOKEN"):
        ArtifactClient()


# ---------------------------------------------------------------------------
# list_artifacts
# ---------------------------------------------------------------------------

def test_list_artifacts(monkeypatch):
    _env(monkeypatch)
    payload = {
        "value": [
            {"name": "logs", "size": 1024, "fileContainerResourceUrl": "https://cont/1"},
            {"name": "reports", "size": 512, "fileContainerResourceUrl": "https://cont/2"},
        ]
    }
    responses = iter([_mock_urlopen([payload]).__next__()])

    with patch("actions_tool_kit.artifact.urllib.request.urlopen", side_effect=lambda r: next(responses)):
        client = ArtifactClient()
        results = client.list_artifacts()

    assert len(results) == 2
    assert results[0].name == "logs"
    assert results[0].size == 1024
    assert results[1].name == "reports"


def test_list_artifacts_empty(monkeypatch):
    _env(monkeypatch)
    m = MagicMock()
    m.read.return_value = json.dumps({"value": []}).encode()
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)

    with patch("actions_tool_kit.artifact.urllib.request.urlopen", return_value=m):
        assert ArtifactClient().list_artifacts() == []


# ---------------------------------------------------------------------------
# upload_artifact
# ---------------------------------------------------------------------------

def test_upload_artifact(monkeypatch, tmp_path):
    _env(monkeypatch)

    f1 = tmp_path / "a.txt"
    f1.write_bytes(b"hello")
    f2 = tmp_path / "b.txt"
    f2.write_bytes(b"world")

    create_resp = {"containerId": 99, "fileContainerResourceUrl": "https://cont/99"}
    upload_resp = {}  # PUT returns empty
    patch_resp = {}   # PATCH returns empty

    call_count = 0
    responses = [create_resp, upload_resp, upload_resp, patch_resp]

    def fake_urlopen(req):
        nonlocal call_count
        m = MagicMock()
        m.read.return_value = json.dumps(responses[call_count]).encode()
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        call_count += 1
        return m

    with patch("actions_tool_kit.artifact.urllib.request.urlopen", side_effect=fake_urlopen):
        ArtifactClient().upload_artifact("my-artifact", [str(f1), str(f2)], root_dir=str(tmp_path))

    assert call_count == 4  # create + 2 uploads + finalize


# ---------------------------------------------------------------------------
# download_artifact
# ---------------------------------------------------------------------------

def test_download_artifact(monkeypatch, tmp_path):
    _env(monkeypatch)
    dest = tmp_path / "dl"

    list_resp = {
        "value": [
            {"name": "logs", "size": 5, "fileContainerResourceUrl": "https://cont/1"},
        ]
    }
    items_resp = {
        "value": [
            {"itemType": "file", "path": "/logs/app.log", "contentLocation": "https://dl/app.log"},
        ]
    }
    file_content = b"log data"

    call_count = 0
    responses_data = [list_resp, items_resp, file_content]

    def fake_urlopen(req):
        nonlocal call_count
        m = MagicMock()
        data = responses_data[call_count]
        m.read.return_value = json.dumps(data).encode() if isinstance(data, dict) else data
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        call_count += 1
        return m

    with patch("actions_tool_kit.artifact.urllib.request.urlopen", side_effect=fake_urlopen):
        result = ArtifactClient().download_artifact("logs", dest=str(dest))

    assert (dest / "logs" / "app.log").read_bytes() == b"log data"
    assert result == dest.resolve()


def test_download_artifact_not_found(monkeypatch):
    _env(monkeypatch)
    list_resp = {"value": [{"name": "other", "size": 0, "fileContainerResourceUrl": ""}]}

    m = MagicMock()
    m.read.return_value = json.dumps(list_resp).encode()
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)

    with patch("actions_tool_kit.artifact.urllib.request.urlopen", return_value=m):
        with pytest.raises(FileNotFoundError, match="missing-artifact"):
            ArtifactClient().download_artifact("missing-artifact")
