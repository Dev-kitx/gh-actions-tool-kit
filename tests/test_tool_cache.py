import os
import platform
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from actions_tool_kit.tool_cache import (
    _current_arch,
    download_tool,
    extract_tar,
    extract_zip,
    cache_dir,
    find_cached_tool,
)


# ---------------------------------------------------------------------------
# _current_arch
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("machine,expected", [
    ("x86_64", "x64"),
    ("amd64", "x64"),
    ("aarch64", "arm64"),
    ("arm64", "arm64"),
    ("ppc64le", "ppc64le"),
])
def test_current_arch(machine, expected):
    with patch("platform.machine", return_value=machine):
        assert _current_arch() == expected


# ---------------------------------------------------------------------------
# download_tool
# ---------------------------------------------------------------------------

def test_download_tool_to_temp(tmp_path):
    content = b"binary data"

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.side_effect = [content, b""]

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = download_tool("http://example.com/tool.tar.gz")

    assert result.exists()
    assert result.read_bytes() == content
    result.unlink()


def test_download_tool_to_explicit_dest(tmp_path):
    content = b"tool binary"
    dest = tmp_path / "subdir" / "mytool"

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.side_effect = [content, b""]

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = download_tool("http://example.com/mytool", dest)

    assert result == dest
    assert dest.read_bytes() == content


def test_download_tool_suffix_preserved(tmp_path):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.side_effect = [b"data", b""]

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = download_tool("http://example.com/archive.zip")

    assert result.suffix == ".zip"
    result.unlink()


# ---------------------------------------------------------------------------
# extract_tar
# ---------------------------------------------------------------------------

def test_extract_tar_to_temp(tmp_path):
    archive = tmp_path / "pkg.tar.gz"
    with tarfile.open(str(archive), "w:gz") as tf:
        (tmp_path / "hello.txt").write_text("hi")
        tf.add(str(tmp_path / "hello.txt"), arcname="hello.txt")

    dest = extract_tar(archive)
    assert (dest / "hello.txt").read_text() == "hi"


def test_extract_tar_to_explicit_dest(tmp_path):
    archive = tmp_path / "pkg.tar.gz"
    with tarfile.open(str(archive), "w:gz") as tf:
        (tmp_path / "file.txt").write_text("content")
        tf.add(str(tmp_path / "file.txt"), arcname="file.txt")

    dest = tmp_path / "extracted"
    result = extract_tar(archive, dest)
    assert result == dest
    assert (dest / "file.txt").read_text() == "content"


# ---------------------------------------------------------------------------
# extract_zip
# ---------------------------------------------------------------------------

def test_extract_zip_to_temp(tmp_path):
    archive = tmp_path / "pkg.zip"
    with zipfile.ZipFile(str(archive), "w") as zf:
        zf.writestr("readme.txt", "hello zip")

    dest = extract_zip(archive)
    assert (dest / "readme.txt").read_text() == "hello zip"


def test_extract_zip_to_explicit_dest(tmp_path):
    archive = tmp_path / "pkg.zip"
    with zipfile.ZipFile(str(archive), "w") as zf:
        zf.writestr("main.py", "print('hi')")

    dest = tmp_path / "out"
    result = extract_zip(archive, dest)
    assert result == dest
    assert (dest / "main.py").read_text() == "print('hi')"


# ---------------------------------------------------------------------------
# cache_dir
# ---------------------------------------------------------------------------

def test_cache_dir_copies_into_tool_cache(tmp_path, monkeypatch):
    tc = tmp_path / "tool_cache"
    tc.mkdir()
    monkeypatch.setenv("RUNNER_TOOL_CACHE", str(tc))

    src = tmp_path / "ruff-bin"
    src.mkdir()
    (src / "ruff").write_text("binary")

    result = cache_dir(src, "ruff", "0.4.1", arch="x64")

    assert result == tc / "ruff" / "0.4.1" / "x64"
    assert (result / "ruff").read_text() == "binary"


def test_cache_dir_replaces_existing(tmp_path, monkeypatch):
    tc = tmp_path / "tool_cache"
    tc.mkdir()
    monkeypatch.setenv("RUNNER_TOOL_CACHE", str(tc))

    # Pre-populate
    old = tc / "mytool" / "1.0.0" / "x64"
    old.mkdir(parents=True)
    (old / "old_file").write_text("old")

    src = tmp_path / "new-bin"
    src.mkdir()
    (src / "new_file").write_text("new")

    cache_dir(src, "mytool", "1.0.0", arch="x64")

    assert not (old / "old_file").exists()
    assert (old / "new_file").read_text() == "new"


def test_cache_dir_missing_env_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("RUNNER_TOOL_CACHE", raising=False)
    src = tmp_path / "src"
    src.mkdir()
    with pytest.raises(RuntimeError, match="RUNNER_TOOL_CACHE"):
        cache_dir(src, "tool", "1.0.0")


# ---------------------------------------------------------------------------
# find_cached_tool
# ---------------------------------------------------------------------------

def _make_cached(tc: Path, tool: str, version: str, arch: str) -> Path:
    d = tc / tool / version / arch
    d.mkdir(parents=True)
    return d


def test_find_cached_tool_exact(tmp_path, monkeypatch):
    tc = tmp_path / "tc"
    monkeypatch.setenv("RUNNER_TOOL_CACHE", str(tc))
    expected = _make_cached(tc, "ruff", "0.4.1", "x64")

    result = find_cached_tool("ruff", "0.4.1", arch="x64")
    assert result == expected


def test_find_cached_tool_exact_missing(tmp_path, monkeypatch):
    tc = tmp_path / "tc"
    tc.mkdir()
    monkeypatch.setenv("RUNNER_TOOL_CACHE", str(tc))

    assert find_cached_tool("ruff", "0.4.1", arch="x64") is None


def test_find_cached_tool_wildcard(tmp_path, monkeypatch):
    tc = tmp_path / "tc"
    monkeypatch.setenv("RUNNER_TOOL_CACHE", str(tc))
    _make_cached(tc, "node", "18.0.0", "x64")
    _make_cached(tc, "node", "18.1.0", "x64")
    _make_cached(tc, "node", "18.2.0", "x64")

    result = find_cached_tool("node", "18.*", arch="x64")
    assert result == tc / "node" / "18.2.0" / "x64"


def test_find_cached_tool_wildcard_no_match(tmp_path, monkeypatch):
    tc = tmp_path / "tc"
    monkeypatch.setenv("RUNNER_TOOL_CACHE", str(tc))
    _make_cached(tc, "node", "20.0.0", "x64")

    assert find_cached_tool("node", "18.*", arch="x64") is None


def test_find_cached_tool_missing_env_returns_none(monkeypatch):
    monkeypatch.delenv("RUNNER_TOOL_CACHE", raising=False)
    assert find_cached_tool("ruff", "0.4.1") is None


def test_find_cached_tool_unknown_tool_returns_none(tmp_path, monkeypatch):
    tc = tmp_path / "tc"
    tc.mkdir()
    monkeypatch.setenv("RUNNER_TOOL_CACHE", str(tc))
    assert find_cached_tool("unknowntool", "1.0.0") is None
