from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


_API_VERSION = "6.0-preview"


@dataclass
class ArtifactInfo:
    """Metadata for a single artifact returned by :meth:`ArtifactClient.list_artifacts`.

    Attributes:
        name: Artifact name.
        size: Total size in bytes.
        container_url: Internal file-container URL used for item listing/download.
    """

    name: str
    size: int
    container_url: str


class ArtifactClient:
    """Thin client for the GitHub Actions artifact service (v3 REST API).

    Requires the ``ACTIONS_RUNTIME_URL`` and ``ACTIONS_RUNTIME_TOKEN``
    environment variables that the runner injects automatically.

    Example::

        client = ArtifactClient()
        client.upload_artifact("my-logs", ["build.log", "test.log"])
        client.download_artifact("my-logs", dest="./downloaded")
    """

    def __init__(self) -> None:
        self._runtime_url = (os.getenv("ACTIONS_RUNTIME_URL") or "").rstrip("/")
        self._token = os.getenv("ACTIONS_RUNTIME_TOKEN") or ""
        self._run_id = os.getenv("GITHUB_RUN_ID", "0")

        if not self._runtime_url or not self._token:
            raise RuntimeError(
                "Artifact service unavailable. "
                "ACTIONS_RUNTIME_URL and ACTIONS_RUNTIME_TOKEN must be set "
                "(they are injected automatically on GitHub-hosted runners)."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self, content_type: str = "application/json") -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": content_type,
            "Accept": f"application/json;api-version={_API_VERSION}",
        }

    def _artifacts_url(self) -> str:
        return (
            f"{self._runtime_url}/_apis/pipelines/workflows/"
            f"{self._run_id}/artifacts?api-version={_API_VERSION}"
        )

    def _request(
        self,
        url: str,
        *,
        method: str = "GET",
        data: Optional[bytes] = None,
        content_type: str = "application/json",
    ) -> dict:
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(content_type),
            method=method,
        )
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            return json.loads(body) if body.strip() else {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload_artifact(
        self,
        name: str,
        files: List[str],
        root_dir: str = ".",
    ) -> None:
        """Upload a list of files as a named artifact.

        Args:
            name: Artifact name (shown in the GitHub UI).
            files: Absolute or relative paths to files to upload.
            root_dir: Directory used to compute relative paths inside the
                      artifact. Files outside *root_dir* use their filename only.
        """
        # 1. Create the artifact container
        payload = json.dumps({"Type": "actions_storage", "Name": name}).encode()
        info = self._request(self._artifacts_url(), method="POST", data=payload)
        container_url: str = info["fileContainerResourceUrl"]
        container_id: int = info["containerId"]

        total_size = 0
        root = Path(root_dir).resolve()

        # 2. Upload each file
        for file_str in files:
            fp = Path(file_str).resolve()
            try:
                rel = fp.relative_to(root)
            except ValueError:
                rel = Path(fp.name)

            raw = fp.read_bytes()
            size = len(raw)
            total_size += size

            item_url = f"{container_url}?itemPath={urllib.parse.quote(str(rel))}"
            req = urllib.request.Request(
                item_url,
                data=raw,
                headers={
                    **self._headers("application/octet-stream"),
                    "Content-Range": f"bytes 0-{size - 1}/{size}",
                },
                method="PUT",
            )
            with urllib.request.urlopen(req):
                pass

        # 3. Finalize / patch size
        finalize_url = (
            f"{self._runtime_url}/_apis/pipelines/workflows/"
            f"{self._run_id}/artifacts/{container_id}?api-version={_API_VERSION}"
        )
        patch_data = json.dumps({"Size": total_size}).encode()
        self._request(finalize_url, method="PATCH", data=patch_data)

    def list_artifacts(self) -> List[ArtifactInfo]:
        """Return metadata for all artifacts associated with the current run."""
        data = self._request(self._artifacts_url())
        return [
            ArtifactInfo(
                name=a["name"],
                size=a.get("size", 0),
                container_url=a.get("fileContainerResourceUrl", ""),
            )
            for a in data.get("value", [])
        ]

    def download_artifact(self, name: str, dest: str = ".") -> Path:
        """Download all files from a named artifact into *dest*.

        Args:
            name: Artifact name to download.
            dest: Local directory to write files into (created if absent).

        Returns:
            The resolved destination directory path.

        Raises:
            FileNotFoundError: When no artifact named *name* exists for this run.
        """
        artifacts = self.list_artifacts()
        match = next((a for a in artifacts if a.name == name), None)
        if match is None:
            raise FileNotFoundError(
                f"Artifact {name!r} not found for run {self._run_id}"
            )

        # List items in the container
        items_url = f"{match.container_url}?itemPath="
        items_data = self._request(items_url)

        dest_path = Path(dest).resolve()
        dest_path.mkdir(parents=True, exist_ok=True)

        for item in items_data.get("value", []):
            if item.get("itemType") != "file":
                continue

            item_rel = item["path"].lstrip("/")
            download_url: str = item["contentLocation"]

            out_file = dest_path / item_rel
            out_file.parent.mkdir(parents=True, exist_ok=True)

            dl_req = urllib.request.Request(
                download_url, headers=self._headers()
            )
            with urllib.request.urlopen(dl_req) as resp:
                out_file.write_bytes(resp.read())

        return dest_path


# ------------------------------------------------------------------
# Module-level convenience wrappers
# ------------------------------------------------------------------


def upload_artifact(name: str, files: List[str], root_dir: str = ".") -> None:
    """Upload files as a named artifact. Convenience wrapper around :class:`ArtifactClient`."""
    ArtifactClient().upload_artifact(name, files, root_dir)


def download_artifact(name: str, dest: str = ".") -> Path:
    """Download a named artifact. Convenience wrapper around :class:`ArtifactClient`."""
    return ArtifactClient().download_artifact(name, dest)


__all__ = [
    "ArtifactInfo",
    "ArtifactClient",
    "upload_artifact",
    "download_artifact",
]
