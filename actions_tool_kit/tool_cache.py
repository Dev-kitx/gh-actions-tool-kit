from __future__ import annotations

import fnmatch
import os
import platform
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple, Union

TarMode = Literal[
    "r", "r:*", "r:", "r:gz", "r:bz2", "r:xz",
    "r|*", "r|", "r|gz", "r|bz2", "r|xz",
]


def _runner_tool_cache() -> Path:
    tc = os.getenv("RUNNER_TOOL_CACHE", "")
    if not tc:
        raise RuntimeError(
            "RUNNER_TOOL_CACHE not set — tool cache unavailable outside GitHub Actions"
        )
    return Path(tc)


def _current_arch() -> str:
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x64"
    if machine in ("aarch64", "arm64"):
        return "arm64"
    return machine


def download_tool(url: str, dest: Optional[Union[str, Path]] = None) -> Path:
    """Download a file from *url* to *dest* and return its local path.

    If *dest* is omitted a temporary file with a matching suffix is created.
    The directory is created automatically when a dest path is supplied.

    Args:
        url: Remote URL to fetch.
        dest: Optional local destination path.

    Returns:
        Path to the downloaded file.
    """
    if dest is None:
        suffix = Path(url.split("?")[0]).suffix or ".tmp"
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        dest_path = Path(tmp)
    else:
        dest_path = Path(dest)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(url) as resp, open(dest_path, "wb") as f:
        while chunk := resp.read(1024 * 1024):
            f.write(chunk)

    return dest_path


def extract_tar(
    file: Union[str, Path],
    dest: Optional[Union[str, Path]] = None,
    *,
    flags: TarMode = "r:gz",
) -> Path:
    """Extract a tar archive and return the extraction directory.

    Args:
        file: Path to the archive.
        dest: Directory to extract into (created if absent; uses a temp dir when omitted).
        flags: tarfile open mode (default ``"r:gz"`` for .tar.gz; use ``"r:*"`` for auto-detect).

    Returns:
        Path to the extraction directory.
    """
    if dest is None:
        dest_path = Path(tempfile.mkdtemp())
    else:
        dest_path = Path(dest)
        dest_path.mkdir(parents=True, exist_ok=True)

    with tarfile.open(str(file), flags) as tf:
        tf.extractall(str(dest_path))

    return dest_path


def extract_zip(
    file: Union[str, Path],
    dest: Optional[Union[str, Path]] = None,
) -> Path:
    """Extract a zip archive and return the extraction directory.

    Args:
        file: Path to the zip file.
        dest: Directory to extract into (created if absent; uses a temp dir when omitted).

    Returns:
        Path to the extraction directory.
    """
    if dest is None:
        dest_path = Path(tempfile.mkdtemp())
    else:
        dest_path = Path(dest)
        dest_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(str(file)) as zf:
        zf.extractall(str(dest_path))

    return dest_path


def cache_dir(
    src: Union[str, Path],
    tool: str,
    version: str,
    arch: Optional[str] = None,
) -> Path:
    """Copy *src* into the runner tool cache and return the cached path.

    Layout inside ``RUNNER_TOOL_CACHE``:
    ``{tool}/{version}/{arch}/``

    An existing cached entry for the same tool/version/arch is replaced.

    Args:
        src: Directory to cache (must exist).
        tool: Tool name (e.g. ``"ruff"``).
        version: Exact version string (e.g. ``"0.4.1"``).
        arch: CPU architecture (e.g. ``"x64"``); defaults to current machine arch.

    Returns:
        Path to the newly created cache directory.

    Raises:
        RuntimeError: If RUNNER_TOOL_CACHE is not set.
    """
    resolved_arch = arch or _current_arch()
    dest = _runner_tool_cache() / tool / version / resolved_arch
    if dest.exists():
        shutil.rmtree(str(dest))
    shutil.copytree(str(src), str(dest))
    return dest


def find_cached_tool(
    tool: str,
    version_spec: str,
    arch: Optional[str] = None,
) -> Optional[Path]:
    """Look for a previously cached tool directory.

    *version_spec* can be an exact version (``"1.2.3"``) or an fnmatch wildcard
    (``"1.2.*"``, ``"1.*"``).  When multiple versions match, the highest
    version is returned (sorted lexicographically per dot-segment, with numeric
    segments compared as integers).

    Args:
        tool: Tool name as passed to :func:`cache_dir`.
        version_spec: Exact version or wildcard pattern.
        arch: Architecture to look for; defaults to current machine arch.

    Returns:
        Path to the arch-specific cached directory, or None when not found.
    """
    try:
        tool_root = _runner_tool_cache() / tool
    except RuntimeError:
        return None

    if not tool_root.exists():
        return None

    resolved_arch = arch or _current_arch()

    if "*" not in version_spec and "?" not in version_spec:
        candidate = tool_root / version_spec / resolved_arch
        return candidate if candidate.exists() else None

    matches: List[Tuple[List[Any], Path]] = []
    for version_dir in tool_root.iterdir():
        if not version_dir.is_dir():
            continue
        if fnmatch.fnmatch(version_dir.name, version_spec):
            arch_dir = version_dir / resolved_arch
            if arch_dir.exists():
                sort_key = [
                    int(p) if p.isdigit() else p
                    for p in version_dir.name.split(".")
                ]
                matches.append((sort_key, arch_dir))

    if not matches:
        return None

    matches.sort(key=lambda x: x[0])
    return matches[-1][1]


__all__ = [
    "download_tool",
    "extract_tar",
    "extract_zip",
    "cache_dir",
    "find_cached_tool",
]
