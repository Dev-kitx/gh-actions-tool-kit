import os
import json
from pathlib import Path
from typing import List, Optional

from .models import (
    WebhookPayload,
    RepoIdentifier,
    IssueIdentifier,
    PullRequestIdentifier,
    Sender,
    Commit,
)
from .payload_parser import parse_payload


class Context:
    """
    Context class to access GitHub Actions environment and event payload data.

    Initializes values from environment variables and event JSON payload for ease of access
    to repository, issue, PR, and workflow information inside a GitHub Actions workflow.
    """

    def __init__(self) -> None:
        """
        Initialize context by loading event payload and environment variables.
        """
        event_path = os.getenv("GITHUB_EVENT_PATH")
        payload_data = {}

        if event_path:
            path = Path(event_path)
            if path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    payload_data = json.load(f)
            else:
                print(f"GITHUB_EVENT_PATH {event_path} does not exist\n")

        self.payload: WebhookPayload = parse_payload(payload_data)

        self.event_name = os.getenv("GITHUB_EVENT_NAME")
        self.sha = os.getenv("GITHUB_SHA")
        self.ref = os.getenv("GITHUB_REF")
        self.workflow = os.getenv("GITHUB_WORKFLOW")
        self.action = os.getenv("GITHUB_ACTION")
        self.actor = os.getenv("GITHUB_ACTOR")
        self.job = os.getenv("GITHUB_JOB")
        self.run_attempt = int(os.getenv("GITHUB_RUN_ATTEMPT", "0"))
        self.run_number = int(os.getenv("GITHUB_RUN_NUMBER", "0"))
        self.run_id = int(os.getenv("GITHUB_RUN_ID", "0"))
        self.api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
        self.server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
        self.graphql_url = os.getenv(
            "GITHUB_GRAPHQL_URL", "https://api.github.com/graphql"
        )

    @property
    def repo(self) -> RepoIdentifier:
        """
        Get repository identifier from environment or payload.

        Returns:
            RepoIdentifier: Object containing `owner` and `repo` name.

        Raises:
            RuntimeError: If repository information is unavailable.
        """
        repo_str = os.getenv("GITHUB_REPOSITORY")

        if repo_str:
            owner, repo = repo_str.split("/")
            return RepoIdentifier(owner=owner, repo=repo)

        if self.payload.repository:
            return RepoIdentifier(
                owner=self.payload.repository.owner.login,
                repo=self.payload.repository.name,
            )

        raise RuntimeError(
            "context.repo requires a GITHUB_REPOSITORY environment variable like 'owner/repo'"
        )

    @property
    def issue(self) -> IssueIdentifier:
        """
        Get issue identifier from payload. Falls back to pull request number if no issue is present.

        Returns:
            IssueIdentifier: Object containing `owner`, `repo`, and `number`.

        Raises:
            RuntimeError: If issue number is unavailable.
        """
        number: Optional[int] = None
        if self.payload.issue is not None:
            number = self.payload.issue.number
        elif self.payload.pull_request is not None:
            number = self.payload.pull_request.number
        else:
            number = self.payload.extra.get("number")

        if number is None:
            raise RuntimeError("context.issue is not available for this event type")

        return IssueIdentifier(
            owner=self.repo.owner,
            repo=self.repo.repo,
            number=number,
        )

    @property
    def pr(self) -> Optional[PullRequestIdentifier]:
        """
        Get pull request identifier from payload.

        Returns:
            PullRequestIdentifier | None: PR identifier if present, else None.
        """
        if self.payload.pull_request is not None:
            return PullRequestIdentifier(
                owner=self.repo.owner,
                repo=self.repo.repo,
                number=self.payload.pull_request.number,
            )
        return None

    @property
    def sender(self) -> Sender:
        """
        Get sender information from payload or fallback to actor environment variable.

        Returns:
            Sender: Sender object from payload, or a minimal one built from GITHUB_ACTOR.
        """
        if self.payload.sender:
            return self.payload.sender
        return Sender(login=self.actor or "", type=None)

    @property
    def head_branch(self) -> Optional[str]:
        """
        Get the source branch of a pull request.

        Returns:
            str | None: Head branch name or None if not a PR.
        """
        if self.payload.pull_request is not None:
            return self.payload.pull_request.head_ref
        return None

    @property
    def base_branch(self) -> Optional[str]:
        """
        Get the target branch of a pull request.

        Returns:
            str | None: Base branch name or None if not a PR.
        """
        if self.payload.pull_request is not None:
            return self.payload.pull_request.base_ref
        return None

    @property
    def ref_name(self) -> Optional[str]:
        """
        Short branch or tag name (GITHUB_REF_NAME), e.g. ``main`` instead of
        ``refs/heads/main``.

        Returns:
            str | None: Short ref name, or None outside a runner.
        """
        return os.getenv("GITHUB_REF_NAME")

    @property
    def ref_type(self) -> Optional[str]:
        """
        Type of the ref that triggered the workflow (GITHUB_REF_TYPE).

        Returns:
            str | None: ``"branch"`` or ``"tag"``, or None outside a runner.
        """
        return os.getenv("GITHUB_REF_TYPE")

    @property
    def trigger_actor(self) -> Optional[str]:
        """
        The actor that triggered the initial workflow run (GITHUB_TRIGGERING_ACTOR).

        Differs from ``actor`` when a workflow is re-run by a different user.

        Returns:
            str | None: GitHub login of the triggering actor, or None outside a runner.
        """
        return os.getenv("GITHUB_TRIGGERING_ACTOR")

    @property
    def is_pr(self) -> bool:
        """
        True when the current event includes a pull request payload.

        Returns:
            bool: Whether payload.pull_request is present.
        """
        return self.payload.pull_request is not None

    @property
    def is_push(self) -> bool:
        """True when the triggering event is a ``push``."""
        return self.event_name == "push"

    @property
    def is_issue(self) -> bool:
        """True when the triggering event is ``issues`` (open, close, label, etc.)."""
        return self.event_name == "issues"

    @property
    def is_release(self) -> bool:
        """True when the triggering event is ``release``."""
        return self.event_name == "release"

    @property
    def is_schedule(self) -> bool:
        """True when the triggering event is ``schedule`` (cron)."""
        return self.event_name == "schedule"

    @property
    def is_workflow_dispatch(self) -> bool:
        """True when the triggering event is ``workflow_dispatch`` (manual run)."""
        return self.event_name == "workflow_dispatch"

    @property
    def commits(self) -> List[Commit]:
        """
        Typed list of commits from a push-event payload.

        For non-push events this returns an empty list.

        Returns:
            List[Commit]: Commits included in the push, or [].
        """
        return self.payload.commits


# Instance of context for easy reuse
context = Context()
