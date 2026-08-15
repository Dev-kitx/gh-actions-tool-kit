from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class RepoIdentifier:
    """
    Identifies a GitHub repository by owner and name.

    Attributes:
        owner (str): The GitHub username or organization that owns the repository.
        repo (str): The name of the repository.
    """

    owner: str
    repo: str


@dataclass
class IssueIdentifier:
    """
    Identifies a GitHub issue by repository and issue number.

    Attributes:
        owner (str): The GitHub username or organization that owns the repository.
        repo (str): The name of the repository.
        number (int): The issue number.
    """

    owner: str
    repo: str
    number: int


@dataclass
class PullRequestIdentifier:
    """
    Identifies a GitHub pull request by repository and PR number.

    Attributes:
        owner (str): The GitHub username or organization that owns the repository.
        repo (str): The name of the repository.
        number (int): The pull request number.
    """

    owner: str
    repo: str
    number: int


@dataclass
class Sender:
    """
    Represents the user who triggered the GitHub event.

    Attributes:
        login (str): GitHub username of the sender.
        type (Optional[str]): Type of the sender (e.g., 'User', 'Bot', etc.).
        extra (Dict[str, Any]): Any additional fields not explicitly mapped.
    """

    login: str
    type: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepoOwner:
    """
    Represents the owner of the repository, as part of payload data.

    Attributes:
        login (str): GitHub login of the owner.
        name (Optional[str]): Optional display name of the owner.
        extra (Dict[str, Any]): Additional unmapped fields from the payload.
    """

    login: str
    name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PayloadRepository:
    """
    Represents the repository object from a GitHub webhook payload.

    Attributes:
        name (str): Name of the repository.
        owner (RepoOwner): The owner object of the repository.
        full_name (Optional[str]): Full name of the repository (e.g., "owner/repo").
        html_url (Optional[str]): URL to the GitHub repository.
        extra (Dict[str, Any]): Any extra unmapped fields in the payload.
    """

    name: str
    owner: RepoOwner
    full_name: Optional[str] = None
    html_url: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserInfo:
    """
    A GitHub user embedded in event payloads (issue author, PR author, commenter, etc.).

    Attributes:
        login (str): GitHub username.
        type (Optional[str]): Account type (e.g., 'User', 'Bot').
        extra (Dict[str, Any]): Additional unmapped fields.
    """

    login: str
    type: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Label:
    """
    A GitHub label attached to an issue or pull request.

    Attributes:
        name (str): Label name.
        color (Optional[str]): Hex color string (without '#').
        extra (Dict[str, Any]): Additional unmapped fields.
    """

    name: str
    color: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IssuePayload:
    """
    Typed representation of an issue from a GitHub webhook payload.

    Attributes:
        number (int): Issue number.
        title (Optional[str]): Issue title.
        body (Optional[str]): Issue body.
        state (Optional[str]): 'open' or 'closed'.
        user (Optional[UserInfo]): Issue author.
        labels (List[Label]): Labels attached to the issue.
        extra (Dict[str, Any]): Additional unmapped fields.
    """

    number: int
    title: Optional[str] = None
    body: Optional[str] = None
    state: Optional[str] = None
    user: Optional[UserInfo] = None
    labels: List[Label] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PullRequestPayload:
    """
    Typed representation of a pull_request from a GitHub webhook payload.

    Attributes:
        number (int): PR number.
        title (Optional[str]): PR title.
        body (Optional[str]): PR body.
        state (Optional[str]): 'open', 'closed', or 'merged'.
        user (Optional[UserInfo]): PR author.
        labels (List[Label]): Labels attached to the PR.
        head_ref (Optional[str]): Source branch name.
        head_sha (Optional[str]): Source branch commit SHA.
        base_ref (Optional[str]): Target branch name.
        base_sha (Optional[str]): Target branch commit SHA.
        merged (Optional[bool]): Whether the PR has been merged.
        draft (Optional[bool]): Whether the PR is a draft.
        extra (Dict[str, Any]): Additional unmapped fields.
    """

    number: int
    title: Optional[str] = None
    body: Optional[str] = None
    state: Optional[str] = None
    user: Optional[UserInfo] = None
    labels: List[Label] = field(default_factory=list)
    head_ref: Optional[str] = None
    head_sha: Optional[str] = None
    base_ref: Optional[str] = None
    base_sha: Optional[str] = None
    merged: Optional[bool] = None
    draft: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommentPayload:
    """
    Typed representation of a comment from a GitHub webhook payload.

    Attributes:
        id (Optional[int]): Comment ID.
        body (Optional[str]): Comment body text.
        user (Optional[UserInfo]): Comment author.
        extra (Dict[str, Any]): Additional unmapped fields.
    """

    id: Optional[int] = None
    body: Optional[str] = None
    user: Optional[UserInfo] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommitAuthor:
    """
    Author or committer information embedded in a push-event commit.

    Attributes:
        name (str): Display name.
        email (Optional[str]): Email address.
        username (Optional[str]): GitHub login, if available.
        extra (Dict[str, Any]): Additional unmapped fields.
    """

    name: str
    email: Optional[str] = None
    username: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Commit:
    """
    A single commit entry from a GitHub push-event payload.

    Attributes:
        id (str): Full commit SHA.
        message (str): Commit message.
        author (Optional[CommitAuthor]): Commit author.
        url (Optional[str]): Link to the commit on GitHub.
        added (List[str]): Files added in this commit.
        removed (List[str]): Files removed in this commit.
        modified (List[str]): Files modified in this commit.
        extra (Dict[str, Any]): Additional unmapped fields.
    """

    id: str
    message: str
    author: Optional[CommitAuthor] = None
    url: Optional[str] = None
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookPayload:
    """
    Represents the full GitHub webhook event payload.

    Attributes:
        repository (Optional[PayloadRepository]): Repository information from the payload.
        issue (Optional[IssuePayload]): Typed issue data if the event is related to an issue.
        pull_request (Optional[PullRequestPayload]): Typed PR data if the event is related to a PR.
        sender (Optional[Sender]): User who triggered the event.
        action (Optional[str]): The action type (e.g., "opened", "closed").
        installation (Optional[Dict[str, Any]]): GitHub App installation metadata.
        comment (Optional[CommentPayload]): Typed comment data if the event involves comments.
        extra (Dict[str, Any]): Any additional unmapped fields from the payload.
    """

    repository: Optional[PayloadRepository] = None
    issue: Optional[IssuePayload] = None
    pull_request: Optional[PullRequestPayload] = None
    sender: Optional[Sender] = None
    action: Optional[str] = None
    installation: Optional[Dict[str, Any]] = None
    comment: Optional[CommentPayload] = None
    commits: List[Commit] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
