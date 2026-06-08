import hashlib
import json
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from actions_tool_kit.cache import (
    _cache_version,
    CacheEntry,
    get_cache,
    restore_cache,
    save_cache,
)


# ---------------------------------------------------------------------------
# _cache_version
# ---------------------------------------------------------------------------

def test_cache_version_deterministic():
    v1 = _cache_version(["requirements.txt", ".venv"])
    v2 = _cache_version(["requirements.txt", ".venv"])
    assert v1 == v2


def test_cache_version_order_independent():
    v1 = _cache_version(["a", "b", "c"])
    v2 = _cache_version(["c", "a", "b"])
    assert v1 == v2


def test_cache_version_salt_changes_hash():
    v1 = _cache_version(["requirements.txt"])
    v2 = _cache_version(["requirements.txt"], salt="linux")
    assert v1 != v2


def test_cache_version_is_hex():
    v = _cache_version(["path"])
    assert len(v) == 64
    int(v, 16)  # raises if not valid hex


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(monkeypatch):
    monkeypatch.setenv("ACTIONS_CACHE_URL", "http://cache.local/")
    monkeypatch.setenv("ACTIONS_RUNTIME_TOKEN", "tok123")


# ---------------------------------------------------------------------------
# get_cache
# ---------------------------------------------------------------------------

def test_get_cache_hit(monkeypatch):
    _env(monkeypatch)
    hit = {
        "cacheKey": "pip-abc",
        "cacheVersion": "v1",
        "archiveLocation": "http://blob/archive.tar.gz",
    }

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = json.dumps(hit).encode()

    with patch("urllib.request.urlopen", return_value=mock_resp):
        entry = get_cache(["pip-abc"], ["requirements.txt"])

    assert isinstance(entry, CacheEntry)
    assert entry.key == "pip-abc"
    assert entry.archive_location == "http://blob/archive.tar.gz"


def test_get_cache_miss_204(monkeypatch):
    _env(monkeypatch)

    import urllib.error
    exc = urllib.error.HTTPError(url="", code=204, msg="No Content", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=exc):
        result = get_cache(["pip-abc"], ["requirements.txt"])

    assert result is None


def test_get_cache_missing_env_raises(monkeypatch):
    monkeypatch.delenv("ACTIONS_CACHE_URL", raising=False)
    monkeypatch.delenv("ACTIONS_RUNTIME_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="ACTIONS_CACHE_URL"):
        get_cache(["key"], ["path"])


# ---------------------------------------------------------------------------
# restore_cache
# ---------------------------------------------------------------------------

def test_restore_cache_miss_returns_none(monkeypatch):
    _env(monkeypatch)
    with patch("actions_tool_kit.cache.get_cache", return_value=None):
        result = restore_cache(["requirements.txt"], "pip-abc")
    assert result is None


def test_restore_cache_hit_extracts_and_returns_key(monkeypatch, tmp_path):
    _env(monkeypatch)

    # Build a real tar.gz in memory to serve as the "archive"
    archive = tmp_path / "cache.tar.gz"
    with tarfile.open(str(archive), "w:gz"):
        pass  # empty archive is fine for this test

    entry = CacheEntry(
        key="pip-abc",
        version="v1",
        archive_location="http://blob/archive.tar.gz",
    )

    download_data = archive.read_bytes()
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.side_effect = [download_data, b""]

    with (
        patch("actions_tool_kit.cache.get_cache", return_value=entry),
        patch("urllib.request.urlopen", return_value=mock_resp),
    ):
        key = restore_cache(["requirements.txt"], "pip-abc")

    assert key == "pip-abc"


# ---------------------------------------------------------------------------
# save_cache
# ---------------------------------------------------------------------------

def test_save_cache_key_conflict_raises(monkeypatch):
    _env(monkeypatch)
    import urllib.error
    exc = urllib.error.HTTPError(url="", code=409, msg="Conflict", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=exc):
        with pytest.raises(RuntimeError, match="already exists"):
            save_cache(["requirements.txt"], "pip-abc")


def test_save_cache_archives_existing_paths(monkeypatch, tmp_path):
    _env(monkeypatch)

    source = tmp_path / "pkg"
    source.mkdir()
    (source / "lib.py").write_text("x = 1")

    call_log = []

    class FakeResp:
        def __init__(self, body=b""):
            self._body = body
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return self._body

    def fake_urlopen(req):
        method = getattr(req, "method", "GET") or "GET"
        call_log.append(method)
        if method == "POST" and "caches" in req.full_url and "caches/" not in req.full_url:
            return FakeResp(json.dumps({"cacheId": 42}).encode())
        return FakeResp(b"")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        cache_id = save_cache([str(source)], "my-key")

    assert cache_id == 42
    assert "POST" in call_log
    assert "PATCH" in call_log


def test_save_cache_skips_nonexistent_paths(monkeypatch, tmp_path):
    _env(monkeypatch)

    class FakeResp:
        def __init__(self, body=b""):
            self._body = body
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return self._body

    def fake_urlopen(req):
        method = getattr(req, "method", "GET") or "GET"
        if method == "POST" and "caches/" not in req.full_url:
            return FakeResp(json.dumps({"cacheId": 1}).encode())
        return FakeResp(b"")

    # path does not exist — should not raise, just produce an empty archive
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        cache_id = save_cache([str(tmp_path / "nonexistent")], "empty-key")

    assert cache_id == 1
