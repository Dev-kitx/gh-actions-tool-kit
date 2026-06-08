import pytest
from actions_tool_kit.models import (
    RepoIdentifier,
    IssueIdentifier,
    PullRequestIdentifier,
    Sender,
    RepoOwner,
    PayloadRepository,
    WebhookPayload,
    UserInfo,
    Label,
    IssuePayload,
    PullRequestPayload,
    CommentPayload,
    CommitAuthor,
    Commit,
)


def test_repo_identifier():
    repo = RepoIdentifier(owner="octocat", repo="hello-world")
    assert repo.owner == "octocat"
    assert repo.repo == "hello-world"


def test_issue_identifier():
    issue = IssueIdentifier(owner="octocat", repo="hello-world", number=42)
    assert issue.owner == "octocat"
    assert issue.repo == "hello-world"
    assert issue.number == 42


def test_pull_request_identifier():
    pr = PullRequestIdentifier(owner="octocat", repo="hello-world", number=99)
    assert pr.owner == "octocat"
    assert pr.repo == "hello-world"
    assert pr.number == 99


def test_sender_with_extra():
    sender = Sender(login="octocat", type="User", extra={"id": 1, "site_admin": False})
    assert sender.login == "octocat"
    assert sender.type == "User"
    assert sender.extra["id"] == 1
    assert sender.extra["site_admin"] is False


def test_sender_without_extra():
    sender = Sender(login="bot-account")
    assert sender.login == "bot-account"
    assert sender.type is None
    assert sender.extra == {}


def test_repo_owner_with_extra():
    owner = RepoOwner(login="octocat", name="The Octocat", extra={"id": 123})
    assert owner.login == "octocat"
    assert owner.name == "The Octocat"
    assert owner.extra == {"id": 123}


def test_repo_owner_without_extra():
    owner = RepoOwner(login="octocat")
    assert owner.name is None
    assert owner.extra == {}


def test_payload_repository_minimal():
    owner = RepoOwner(login="octocat")
    repo = PayloadRepository(name="hello-world", owner=owner)
    assert repo.name == "hello-world"
    assert repo.owner.login == "octocat"
    assert repo.full_name is None
    assert repo.html_url is None
    assert repo.extra == {}


def test_payload_repository_with_extra():
    owner = RepoOwner(login="octocat", name="The Octocat")
    repo = PayloadRepository(
        name="hello-world",
        owner=owner,
        full_name="octocat/hello-world",
        html_url="https://github.com/octocat/hello-world",
        extra={"private": False}
    )
    assert repo.full_name == "octocat/hello-world"
    assert repo.html_url == "https://github.com/octocat/hello-world"
    assert repo.extra["private"] is False


def test_user_info():
    user = UserInfo(login="octocat", type="User", extra={"id": 1})
    assert user.login == "octocat"
    assert user.type == "User"
    assert user.extra["id"] == 1


def test_user_info_defaults():
    user = UserInfo(login="bot")
    assert user.type is None
    assert user.extra == {}


def test_label():
    lbl = Label(name="bug", color="d73a4a", extra={"description": "Something isn't working"})
    assert lbl.name == "bug"
    assert lbl.color == "d73a4a"
    assert lbl.extra["description"] == "Something isn't working"


def test_label_defaults():
    lbl = Label(name="enhancement")
    assert lbl.color is None
    assert lbl.extra == {}


def test_issue_payload():
    user = UserInfo(login="octocat")
    labels = [Label(name="bug"), Label(name="help wanted")]
    issue = IssuePayload(
        number=42,
        title="Something broke",
        body="Steps to reproduce...",
        state="open",
        user=user,
        labels=labels,
        extra={"html_url": "https://github.com/o/r/issues/42"},
    )
    assert issue.number == 42
    assert issue.title == "Something broke"
    assert issue.state == "open"
    assert issue.user.login == "octocat"
    assert len(issue.labels) == 2
    assert issue.labels[0].name == "bug"
    assert issue.extra["html_url"] == "https://github.com/o/r/issues/42"


def test_issue_payload_defaults():
    issue = IssuePayload(number=1)
    assert issue.title is None
    assert issue.body is None
    assert issue.state is None
    assert issue.user is None
    assert issue.labels == []
    assert issue.extra == {}


def test_pull_request_payload():
    user = UserInfo(login="contributor")
    pr = PullRequestPayload(
        number=99,
        title="Add feature",
        body="Description",
        state="open",
        user=user,
        labels=[Label(name="feature")],
        head_ref="my-branch",
        head_sha="abc123",
        base_ref="main",
        base_sha="def456",
        merged=False,
        draft=False,
    )
    assert pr.number == 99
    assert pr.head_ref == "my-branch"
    assert pr.base_ref == "main"
    assert pr.head_sha == "abc123"
    assert pr.merged is False
    assert pr.draft is False
    assert pr.labels[0].name == "feature"


def test_pull_request_payload_defaults():
    pr = PullRequestPayload(number=1)
    assert pr.title is None
    assert pr.head_ref is None
    assert pr.head_sha is None
    assert pr.base_ref is None
    assert pr.base_sha is None
    assert pr.merged is None
    assert pr.draft is None
    assert pr.labels == []
    assert pr.extra == {}


def test_comment_payload():
    user = UserInfo(login="reviewer")
    comment = CommentPayload(id=555, body="LGTM!", user=user, extra={"url": "https://..."})
    assert comment.id == 555
    assert comment.body == "LGTM!"
    assert comment.user.login == "reviewer"
    assert comment.extra["url"] == "https://..."


def test_comment_payload_defaults():
    comment = CommentPayload()
    assert comment.id is None
    assert comment.body is None
    assert comment.user is None
    assert comment.extra == {}


def test_commit_author():
    author = CommitAuthor(name="Akash", email="a@b.com", username="akash")
    assert author.name == "Akash"
    assert author.email == "a@b.com"
    assert author.username == "akash"
    assert author.extra == {}


def test_commit_author_defaults():
    author = CommitAuthor(name="Bot")
    assert author.email is None
    assert author.username is None
    assert author.extra == {}


def test_commit():
    author = CommitAuthor(name="Akash")
    commit = Commit(
        id="abc123",
        message="fix: bug",
        author=author,
        url="https://github.com/o/r/commit/abc123",
        added=["new.py"],
        removed=[],
        modified=["old.py"],
        extra={"timestamp": "2024-01-01T00:00:00Z"},
    )
    assert commit.id == "abc123"
    assert commit.message == "fix: bug"
    assert commit.author.name == "Akash"
    assert commit.added == ["new.py"]
    assert commit.modified == ["old.py"]
    assert commit.extra["timestamp"] == "2024-01-01T00:00:00Z"


def test_commit_defaults():
    commit = Commit(id="sha", message="msg")
    assert commit.author is None
    assert commit.url is None
    assert commit.added == []
    assert commit.removed == []
    assert commit.modified == []
    assert commit.extra == {}


def test_webhook_payload_defaults():
    payload = WebhookPayload()
    assert payload.repository is None
    assert payload.issue is None
    assert payload.pull_request is None
    assert payload.sender is None
    assert payload.action is None
    assert payload.installation is None
    assert payload.comment is None
    assert payload.extra == {}


def test_webhook_payload_with_typed_fields():
    repo_owner = RepoOwner(login="octocat", name="The Octocat")
    payload_repo = PayloadRepository(name="repo", owner=repo_owner)
    issue = IssuePayload(number=1, title="Bug")
    pr = PullRequestPayload(number=2, title="Fix")
    sender = Sender(login="octocat")
    comment = CommentPayload(body="Looks good")

    payload = WebhookPayload(
        repository=payload_repo,
        issue=issue,
        pull_request=pr,
        sender=sender,
        action="opened",
        installation={"id": 123},
        comment=comment,
        extra={"custom": "value"},
    )

    assert payload.repository.name == "repo"
    assert payload.issue.number == 1
    assert payload.issue.title == "Bug"
    assert payload.pull_request.number == 2
    assert payload.sender.login == "octocat"
    assert payload.action == "opened"
    assert payload.installation["id"] == 123
    assert payload.comment.body == "Looks good"
    assert payload.extra["custom"] == "value"
