from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


_API_VERSION = "6.0-preview.1"
_CHUNK_SIZE = 32 * 1024 * 1024  # 32 MB


def _cache_url() -> str:
    url = os.getenv("ACTIONS_CACHE_URL", "")
    if not url:
        raise RuntimeError(
            "ACTIONS_CACHE_URL not set — cache service unavailable outside GitHub Actions"
        )
    return url.rstrip("/")


def _runtime_token() -> str:
    token = os.getenv("ACTIONS_RUNTIME_TOKEN", "")
    if not token:
        raise RuntimeError("ACTIONS_RUNTIME_TOKEN not set")
    return token


def _json_headers(**extra: str) -> dict:
    h = {
        "Authorization": f"Bearer {_runtime_token()}",
        "Accept": f"application/json;api-version={_API_VERSION}",
        "Content-Type": "application/json",
    }
    h.update(extra)
    return h


def _cache_version(paths: List[str], salt: str = "") -> str:
    """Deterministic SHA-256 of the sorted path list + optional salt."""
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.encode())
    if salt:
        h.update(salt.encode())
    return h.hexdigest()


@dataclass
class CacheEntry:
    """Metadata returned by the cache service on a cache hit."""

    key: str
    version: str
    archive_location: str


def get_cache(
    keys: List[str],
    paths: List[str],
    *,
    version_salt: str = "",
) -> Optional[CacheEntry]:
    """Query the cache service for a matching entry.

    Keys are tried in order — first match wins (primary key, then restore keys).

    Args:
        keys: Ordered list of cache keys to check.
        paths: Paths that were cached (used to compute the cache version hash).
        version_salt: Extra string mixed into the version hash (e.g. OS name).

    Returns:
        CacheEntry on hit, None on miss.
    """
    base = _cache_url()
    version = _cache_version(paths, version_salt)
    encoded = urllib.parse.quote(",".join(keys))
    url = f"{base}/_apis/artifactcache/cache?keys={encoded}&version={version}"

    req = urllib.request.Request(url, headers=_json_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            return CacheEntry(
                key=data.get("cacheKey", keys[0]),
                version=data.get("cacheVersion", version),
                archive_location=data["archiveLocation"],
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 204:
            return None
        raise


def restore_cache(
    paths: List[str],
    primary_key: str,
    restore_keys: Optional[List[str]] = None,
    *,
    version_salt: str = "",
) -> Optional[str]:
    """Restore cached files and return the matched cache key, or None on miss.

    The archive is extracted into the current working directory preserving
    relative paths. ``restore_keys`` are tried in order if the primary key
    misses (longest-prefix match semantics on the server side).

    Args:
        paths: Paths that were originally cached (used for version hash).
        primary_key: Exact cache key to look up first.
        restore_keys: Fallback keys tried in order on a primary miss.
        version_salt: Extra string mixed into the version hash.

    Returns:
        The cache key that was actually restored, or None on miss.
    """
    all_keys = [primary_key] + (restore_keys or [])
    entry = get_cache(all_keys, paths, version_salt=version_salt)
    if entry is None:
        return None

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        archive_path = tmp.name

    try:
        req = urllib.request.Request(entry.archive_location)
        with urllib.request.urlopen(req) as resp, open(archive_path, "wb") as f:
            while chunk := resp.read(1024 * 1024):
                f.write(chunk)

        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(".")
    finally:
        Path(archive_path).unlink(missing_ok=True)

    return entry.key


def save_cache(
    paths: List[str],
    key: str,
    *,
    version_salt: str = "",
    chunk_size: int = _CHUNK_SIZE,
) -> int:
    """Archive the given paths and push them to the cache service.

    Upload is done in ``chunk_size`` byte chunks via Content-Range.

    Args:
        paths: Local paths to include in the archive (non-existent paths are skipped).
        key: Cache key to store under.
        version_salt: Extra string mixed into the version hash.
        chunk_size: Upload chunk size in bytes (default 32 MB).

    Returns:
        The numeric cache ID assigned by the service.

    Raises:
        RuntimeError: If the key already exists (HTTP 409).
    """
    base = _cache_url()
    version = _cache_version(paths, version_salt)

    reserve_body = json.dumps({"key": key, "version": version}).encode()
    req = urllib.request.Request(
        f"{base}/_apis/artifactcache/caches",
        data=reserve_body,
        headers=_json_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            cache_id: int = json.loads(resp.read())["cacheId"]
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            raise RuntimeError(f"Cache key already exists: {key!r}") from exc
        raise

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        archive_path = tmp.name

    try:
        with tarfile.open(archive_path, "w:gz") as tf:
            for p in paths:
                path = Path(p)
                if path.exists():
                    tf.add(str(path), arcname=str(path))

        total_size = Path(archive_path).stat().st_size
        upload_url = f"{base}/_apis/artifactcache/caches/{cache_id}"

        with open(archive_path, "rb") as f:
            offset = 0
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                end = offset + len(chunk) - 1
                patch_headers = {
                    "Authorization": f"Bearer {_runtime_token()}",
                    "Content-Type": "application/octet-stream",
                    "Content-Range": f"bytes {offset}-{end}/*",
                }
                patch_req = urllib.request.Request(
                    upload_url, data=chunk, headers=patch_headers, method="PATCH"
                )
                with urllib.request.urlopen(patch_req):
                    pass
                offset += len(chunk)

        commit_body = json.dumps({"size": total_size}).encode()
        commit_req = urllib.request.Request(
            upload_url, data=commit_body, headers=_json_headers(), method="POST"
        )
        with urllib.request.urlopen(commit_req):
            pass
    finally:
        Path(archive_path).unlink(missing_ok=True)

    return cache_id


__all__ = ["CacheEntry", "get_cache", "restore_cache", "save_cache"]
