from typing import Optional

from .models import (
    WebhookPayload,
    PayloadRepository,
    RepoOwner,
    Sender,
    UserInfo,
    Label,
    IssuePayload,
    PullRequestPayload,
    CommentPayload,
    CommitAuthor,
    Commit,
)

_KNOWN_TOP_LEVEL = {
    "repository", "issue", "pull_request", "sender",
    "action", "installation", "comment", "commits",
}


def _parse_user(data: dict) -> UserInfo:
    return UserInfo(
        login=data.get("login", ""),
        type=data.get("type"),
        extra={k: v for k, v in data.items() if k not in {"login", "type"}},
    )


def _parse_label(data: dict) -> Label:
    return Label(
        name=data.get("name", ""),
        color=data.get("color"),
        extra={k: v for k, v in data.items() if k not in {"name", "color"}},
    )


def _parse_issue(data: dict) -> IssuePayload:
    _known = {"number", "title", "body", "state", "user", "labels"}
    return IssuePayload(
        number=data.get("number", 0),
        title=data.get("title"),
        body=data.get("body"),
        state=data.get("state"),
        user=_parse_user(data["user"]) if data.get("user") else None,
        labels=[_parse_label(lbl) for lbl in data.get("labels", [])],
        extra={k: v for k, v in data.items() if k not in _known},
    )


def _parse_pull_request(data: dict) -> PullRequestPayload:
    _known = {
        "number", "title", "body", "state", "user", "labels",
        "head", "base", "merged", "draft",
    }
    head = data.get("head") or {}
    base = data.get("base") or {}
    return PullRequestPayload(
        number=data.get("number", 0),
        title=data.get("title"),
        body=data.get("body"),
        state=data.get("state"),
        user=_parse_user(data["user"]) if data.get("user") else None,
        labels=[_parse_label(lbl) for lbl in data.get("labels", [])],
        head_ref=head.get("ref"),
        head_sha=head.get("sha"),
        base_ref=base.get("ref"),
        base_sha=base.get("sha"),
        merged=data.get("merged"),
        draft=data.get("draft"),
        extra={k: v for k, v in data.items() if k not in _known},
    )


def _parse_commit_author(data: dict) -> CommitAuthor:
    _known = {"name", "email", "username"}
    return CommitAuthor(
        name=data.get("name", ""),
        email=data.get("email"),
        username=data.get("username"),
        extra={k: v for k, v in data.items() if k not in _known},
    )


def _parse_commit(data: dict) -> Commit:
    _known = {"id", "message", "author", "url", "added", "removed", "modified"}
    return Commit(
        id=data.get("id", ""),
        message=data.get("message", ""),
        author=_parse_commit_author(data["author"]) if data.get("author") else None,
        url=data.get("url"),
        added=data.get("added", []),
        removed=data.get("removed", []),
        modified=data.get("modified", []),
        extra={k: v for k, v in data.items() if k not in _known},
    )


def _parse_comment(data: dict) -> CommentPayload:
    _known = {"id", "body", "user"}
    return CommentPayload(
        id=data.get("id"),
        body=data.get("body"),
        user=_parse_user(data["user"]) if data.get("user") else None,
        extra={k: v for k, v in data.items() if k not in _known},
    )


def parse_payload(data: dict) -> WebhookPayload:
    """
    Parse a raw GitHub webhook payload dictionary into a strongly typed WebhookPayload object.

    Extracts and types: repository (with nested owner), issue, pull_request, comment, sender.
    Unknown top-level keys are collected in WebhookPayload.extra.

    Args:
        data (dict): The raw webhook event payload (typically loaded from GITHUB_EVENT_PATH).

    Returns:
        WebhookPayload: A fully typed representation of the GitHub webhook event.
    """
    # --- Parse repository ---
    repository_data = data.get("repository")
    repo = None
    if repository_data:
        owner_data = repository_data.get("owner", {})
        owner = RepoOwner(
            login=owner_data.get("login", ""),
            name=owner_data.get("name"),
            extra={k: v for k, v in owner_data.items() if k not in {"login", "name"}},
        )
        repo = PayloadRepository(
            name=repository_data.get("name", ""),
            owner=owner,
            full_name=repository_data.get("full_name"),
            html_url=repository_data.get("html_url"),
            extra={
                k: v
                for k, v in repository_data.items()
                if k not in {"name", "owner", "full_name", "html_url"}
            },
        )

    # --- Parse sender ---
    sender_data = data.get("sender")
    sender: Optional[Sender] = None
    if sender_data:
        sender = Sender(
            login=sender_data.get("login", ""),
            type=sender_data.get("type"),
            extra={k: v for k, v in sender_data.items() if k not in {"login", "type"}},
        )

    # --- Parse typed sub-objects ---
    issue_data = data.get("issue")
    pr_data = data.get("pull_request")
    comment_data = data.get("comment")
    commits_data = data.get("commits") or []

    return WebhookPayload(
        repository=repo,
        issue=_parse_issue(issue_data) if issue_data else None,
        pull_request=_parse_pull_request(pr_data) if pr_data else None,
        sender=sender,
        action=data.get("action"),
        installation=data.get("installation"),
        comment=_parse_comment(comment_data) if comment_data else None,
        commits=[_parse_commit(c) for c in commits_data],
        extra={k: v for k, v in data.items() if k not in _KNOWN_TOP_LEVEL},
    )
