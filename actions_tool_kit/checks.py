from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

Status = Literal["queued", "in_progress", "completed"]
Conclusion = Literal[
    "action_required", "cancelled", "failure", "neutral",
    "success", "skipped", "timed_out",
]
AnnotationLevel = Literal["notice", "warning", "failure"]

_MAX_ANNOTATIONS = 50


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _api_request(
    url: str,
    *,
    method: str,
    token: str,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        body_bytes = resp.read()
        return json.loads(body_bytes) if body_bytes.strip() else {}


@dataclass
class Annotation:
    """A single inline annotation attached to a file in a check run.

    Attributes:
        path: File path relative to the repository root (e.g. ``"src/main.py"``).
        start_line: Line where the annotation begins.
        end_line: Line where the annotation ends (same as ``start_line`` for a single line).
        annotation_level: Severity — ``"notice"``, ``"warning"``, or ``"failure"``.
        message: Body text shown in the GitHub UI.
        title: Short label displayed above the message.
        start_column: Starting column. Only valid when ``start_line == end_line``.
        end_column: Ending column. Only valid when ``start_line == end_line``.
        raw_details: Extra information shown in a collapsed section.
    """

    path: str
    start_line: int
    end_line: int
    annotation_level: AnnotationLevel
    message: str
    title: Optional[str] = None
    start_column: Optional[int] = None
    end_column: Optional[int] = None
    raw_details: Optional[str] = None

    def _to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "annotation_level": self.annotation_level,
            "message": self.message,
        }
        if self.title is not None:
            d["title"] = self.title
        # GitHub only accepts column fields when start_line == end_line
        if self.start_line == self.end_line:
            if self.start_column is not None:
                d["start_column"] = self.start_column
            if self.end_column is not None:
                d["end_column"] = self.end_column
        if self.raw_details is not None:
            d["raw_details"] = self.raw_details
        return d


class CheckRun:
    """A GitHub Check Run that can be created, updated, and completed via the Checks API.

    Requires a token with ``checks:write`` permission (``GITHUB_TOKEN`` works on
    GitHub-hosted runners when the workflow declares ``permissions: checks: write``).

    Use :meth:`create` to open a new check run, :meth:`update` for intermediate
    progress, and :meth:`complete` to set the final conclusion. Can also be used as
    a context manager — automatically marks the run ``success`` on clean exit or
    ``failure`` if an exception propagates.

    Example::

        from actions_tool_kit.checks import CheckRun, Annotation

        with CheckRun.create("mypy", head_sha=context.sha) as check:
            check.update(status="in_progress", summary="Running type checks…")
            violations = run_mypy()
            check.complete(
                conclusion="failure" if violations else "success",
                summary=f"{len(violations)} error(s)",
                annotations=[
                    Annotation(v.file, v.line, v.line, "failure", v.message)
                    for v in violations
                ],
            )
    """

    def __init__(
        self,
        run_id: int,
        name: str,
        head_sha: str,
        *,
        token: str,
        owner: str,
        repo: str,
        api_url: str,
    ) -> None:
        self.id = run_id
        self.name = name
        self.head_sha = head_sha
        self.status: Status = "queued"
        self.conclusion: Optional[Conclusion] = None
        self._token = token
        self._owner = owner
        self._repo = repo
        self._api_url = api_url

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name: str,
        head_sha: str,
        *,
        token: Optional[str] = None,
        repo: Optional[str] = None,
        status: Status = "queued",
        title: Optional[str] = None,
        summary: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "CheckRun":
        """Create a new check run on GitHub and return a :class:`CheckRun` handle.

        Args:
            name: Display name for the check run (e.g. ``"mypy"``).
            head_sha: The commit SHA to attach this check run to.
            token: GitHub token with ``checks:write`` scope. Falls back to
                   ``GITHUB_TOKEN``.
            repo: ``"owner/repo"`` slug. Falls back to ``GITHUB_REPOSITORY``.
            status: Initial status — ``"queued"`` (default), ``"in_progress"``,
                    or ``"completed"``.
            title: Short output title shown in the check panel.
            summary: Markdown summary shown in the check panel.
            api_url: Override the GitHub API base URL. Falls back to
                     ``GITHUB_API_URL`` or ``https://api.github.com``.

        Returns:
            A :class:`CheckRun` instance bound to the newly created run.

        Raises:
            RuntimeError: When no token or repository can be resolved.
            urllib.error.HTTPError: On API errors (e.g. missing permission).
        """
        resolved_token = token or os.getenv("GITHUB_TOKEN")
        if not resolved_token:
            raise RuntimeError(
                "No GitHub token found. Pass token= or set GITHUB_TOKEN."
            )

        repo_slug = repo or os.getenv("GITHUB_REPOSITORY", "")
        if not repo_slug or "/" not in repo_slug:
            raise RuntimeError(
                "No repository found. Pass repo='owner/name' or set GITHUB_REPOSITORY."
            )
        owner, repo_name = repo_slug.split("/", 1)

        resolved_api = (
            api_url or os.getenv("GITHUB_API_URL") or "https://api.github.com"
        ).rstrip("/")

        body: Dict[str, Any] = {
            "name": name,
            "head_sha": head_sha,
            "status": status,
            "started_at": _now_iso(),
        }
        if title or summary:
            body["output"] = {
                "title": title or name,
                "summary": summary or "",
            }

        data = _api_request(
            f"{resolved_api}/repos/{owner}/{repo_name}/check-runs",
            method="POST",
            token=resolved_token,
            body=body,
        )

        instance = cls(
            run_id=data["id"],
            name=name,
            head_sha=head_sha,
            token=resolved_token,
            owner=owner,
            repo=repo_name,
            api_url=resolved_api,
        )
        instance.status = status
        return instance

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def update(
        self,
        *,
        status: Optional[Status] = None,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        details: Optional[str] = None,
        annotations: Optional[List[Annotation]] = None,
    ) -> None:
        """Update the check run's status or output without completing it.

        Useful for mid-run progress messages. Annotations are sent in batches of
        50 (the GitHub API limit per request).

        Args:
            status: New status to set (``"in_progress"`` or ``"completed"``).
            title: Output title shown in the check panel.
            summary: Markdown summary shown in the check panel.
            details: Extended Markdown shown in the "Details" tab.
            annotations: File-level annotations to attach.
        """
        body: Dict[str, Any] = {}
        if status is not None:
            body["status"] = status
            self.status = status

        output: Dict[str, Any] = {}
        if title is not None:
            output["title"] = title
        if summary is not None:
            output["summary"] = summary
        if details is not None:
            output["text"] = details

        all_annotations = annotations or []

        if output or all_annotations:
            output.setdefault("title", self.name)
            output.setdefault("summary", "")
            # Send first batch alongside the other fields, remainder separately
            first_batch = all_annotations[:_MAX_ANNOTATIONS]
            output["annotations"] = [a._to_dict() for a in first_batch]
            body["output"] = output
            self._patch(body)
            # Send any remaining annotation batches
            for i in range(_MAX_ANNOTATIONS, len(all_annotations), _MAX_ANNOTATIONS):
                batch = all_annotations[i: i + _MAX_ANNOTATIONS]
                self._patch({"output": {"title": self.name, "summary": "", "annotations": [a._to_dict() for a in batch]}})
        elif body:
            self._patch(body)

    def complete(
        self,
        conclusion: Conclusion,
        *,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        details: Optional[str] = None,
        annotations: Optional[List[Annotation]] = None,
    ) -> None:
        """Mark the check run as completed with a final conclusion.

        Args:
            conclusion: Final result — ``"success"``, ``"failure"``,
                        ``"neutral"``, ``"cancelled"``, ``"skipped"``,
                        ``"timed_out"``, or ``"action_required"``.
            title: Output title shown in the check panel.
            summary: Markdown summary shown in the check panel.
            details: Extended Markdown shown in the "Details" tab.
            annotations: File-level annotations to attach.
        """
        all_annotations = annotations or []

        # If there are >50 annotations, flush the overflow first via update()
        # so the final PATCH only carries the last batch alongside the conclusion.
        if len(all_annotations) > _MAX_ANNOTATIONS:
            self.update(annotations=all_annotations[:-_MAX_ANNOTATIONS])
            all_annotations = all_annotations[-_MAX_ANNOTATIONS:]

        body: Dict[str, Any] = {
            "status": "completed",
            "conclusion": conclusion,
            "completed_at": _now_iso(),
        }
        output: Dict[str, Any] = {}
        if title is not None:
            output["title"] = title
        if summary is not None:
            output["summary"] = summary
        if details is not None:
            output["text"] = details
        if all_annotations:
            output["annotations"] = [a._to_dict() for a in all_annotations]
        if output:
            output.setdefault("title", self.name)
            output.setdefault("summary", "")
            body["output"] = output

        self._patch(body)
        self.status = "completed"
        self.conclusion = conclusion

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "CheckRun":
        if self.status == "queued":
            self.update(status="in_progress")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        if self.status != "completed":
            self.complete(conclusion="failure" if exc_type else "success")
        return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _patch(self, body: Dict[str, Any]) -> None:
        _api_request(
            f"{self._api_url}/repos/{self._owner}/{self._repo}/check-runs/{self.id}",
            method="PATCH",
            token=self._token,
            body=body,
        )


# ------------------------------------------------------------------
# Module-level convenience wrapper
# ------------------------------------------------------------------


def create_check_run(
    name: str,
    head_sha: str,
    *,
    token: Optional[str] = None,
    repo: Optional[str] = None,
    status: Status = "queued",
    title: Optional[str] = None,
    summary: Optional[str] = None,
    api_url: Optional[str] = None,
) -> CheckRun:
    """Create a new check run. Convenience wrapper around :meth:`CheckRun.create`."""
    return CheckRun.create(
        name,
        head_sha,
        token=token,
        repo=repo,
        status=status,
        title=title,
        summary=summary,
        api_url=api_url,
    )


__all__ = [
    "Annotation",
    "AnnotationLevel",
    "CheckRun",
    "Conclusion",
    "Status",
    "create_check_run",
]
