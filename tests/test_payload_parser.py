import pytest
from actions_tool_kit.models import (
    WebhookPayload,
    PayloadRepository,
    RepoOwner,
    Sender,
    IssuePayload,
    PullRequestPayload,
    CommentPayload,
    UserInfo,
    Label,
    Commit,
    CommitAuthor,
)
from actions_tool_kit.payload_parser import parse_payload


def test_parse_payload_full():
    payload_dict = {
        "repository": {
            "name": "my-repo",
            "full_name": "owner/my-repo",
            "html_url": "https://github.com/owner/my-repo",
            "owner": {
                "login": "owner",
                "name": "Repo Owner",
                "avatar_url": "https://avatars.githubusercontent.com/u/1",
            },
            "private": True,
        },
        "issue": {"number": 123, "title": "Bug report", "state": "open"},
        "pull_request": {
            "number": 456,
            "title": "Fix the bug",
            "state": "open",
            "head": {"ref": "fix-branch", "sha": "abc123"},
            "base": {"ref": "main", "sha": "def456"},
            "draft": False,
            "merged": False,
        },
        "sender": {"login": "octocat", "type": "User", "id": 999},
        "action": "opened",
        "installation": {"id": 42},
        "comment": {"id": 1, "body": "Looks good", "user": {"login": "reviewer", "type": "User"}},
        "custom_field": "value",
    }

    result: WebhookPayload = parse_payload(payload_dict)

    # repository
    assert isinstance(result.repository, PayloadRepository)
    assert result.repository.name == "my-repo"
    assert result.repository.full_name == "owner/my-repo"
    assert result.repository.owner.login == "owner"
    assert result.repository.owner.name == "Repo Owner"
    assert result.repository.owner.extra["avatar_url"] == "https://avatars.githubusercontent.com/u/1"
    assert result.repository.extra["private"] is True

    # sender
    assert isinstance(result.sender, Sender)
    assert result.sender.login == "octocat"
    assert result.sender.type == "User"
    assert result.sender.extra["id"] == 999

    # typed issue
    assert isinstance(result.issue, IssuePayload)
    assert result.issue.number == 123
    assert result.issue.title == "Bug report"
    assert result.issue.state == "open"

    # typed pull_request
    assert isinstance(result.pull_request, PullRequestPayload)
    assert result.pull_request.number == 456
    assert result.pull_request.title == "Fix the bug"
    assert result.pull_request.head_ref == "fix-branch"
    assert result.pull_request.head_sha == "abc123"
    assert result.pull_request.base_ref == "main"
    assert result.pull_request.base_sha == "def456"
    assert result.pull_request.draft is False
    assert result.pull_request.merged is False

    # typed comment
    assert isinstance(result.comment, CommentPayload)
    assert result.comment.id == 1
    assert result.comment.body == "Looks good"
    assert result.comment.user.login == "reviewer"

    assert result.action == "opened"
    assert result.installation["id"] == 42
    assert result.extra["custom_field"] == "value"


def test_parse_payload_issue_with_labels():
    data = {
        "issue": {
            "number": 10,
            "title": "Crash on startup",
            "state": "open",
            "user": {"login": "reporter", "type": "User"},
            "labels": [
                {"name": "bug", "color": "d73a4a"},
                {"name": "critical", "color": "e11d48"},
            ],
        }
    }
    result = parse_payload(data)
    assert result.issue.number == 10
    assert result.issue.user.login == "reporter"
    assert len(result.issue.labels) == 2
    assert result.issue.labels[0].name == "bug"
    assert result.issue.labels[0].color == "d73a4a"
    assert result.issue.labels[1].name == "critical"


def test_parse_payload_pr_with_labels():
    data = {
        "pull_request": {
            "number": 7,
            "title": "Add tests",
            "labels": [{"name": "tests"}],
            "head": {"ref": "add-tests", "sha": "aaa"},
            "base": {"ref": "main", "sha": "bbb"},
        }
    }
    result = parse_payload(data)
    assert result.pull_request.number == 7
    assert result.pull_request.labels[0].name == "tests"
    assert result.pull_request.head_ref == "add-tests"
    assert result.pull_request.base_ref == "main"


def test_parse_payload_missing_repository_and_sender():
    data = {
        "issue": {"number": 789},
        "pull_request": {"number": 555},
        "action": "closed",
        "comment": {"body": "done"},
        "custom_thing": 123,
    }

    result = parse_payload(data)

    assert result.repository is None
    assert result.sender is None
    assert result.issue.number == 789
    assert result.pull_request.number == 555
    assert result.action == "closed"
    assert result.comment.body == "done"
    assert result.extra == {"custom_thing": 123}


def test_parse_payload_minimal():
    result = parse_payload({})
    assert isinstance(result, WebhookPayload)
    assert result.repository is None
    assert result.sender is None
    assert result.issue is None
    assert result.pull_request is None
    assert result.comment is None
    assert result.extra == {}


def test_parse_payload_commits():
    data = {
        "commits": [
            {
                "id": "abc123",
                "message": "fix: crash on startup",
                "author": {"name": "Akash", "email": "a@b.com", "username": "akash"},
                "url": "https://github.com/o/r/commit/abc123",
                "added": ["new_file.py"],
                "removed": [],
                "modified": ["main.py"],
            },
            {
                "id": "def456",
                "message": "chore: bump deps",
                "author": {"name": "Bot", "email": "bot@b.com"},
                "url": "https://github.com/o/r/commit/def456",
                "added": [],
                "removed": ["old.py"],
                "modified": [],
            },
        ]
    }
    result = parse_payload(data)

    assert len(result.commits) == 2
    c0 = result.commits[0]
    assert isinstance(c0, Commit)
    assert c0.id == "abc123"
    assert c0.message == "fix: crash on startup"
    assert isinstance(c0.author, CommitAuthor)
    assert c0.author.name == "Akash"
    assert c0.author.email == "a@b.com"
    assert c0.author.username == "akash"
    assert c0.added == ["new_file.py"]
    assert c0.modified == ["main.py"]

    c1 = result.commits[1]
    assert c1.id == "def456"
    assert c1.author.username is None
    assert c1.removed == ["old.py"]


def test_parse_payload_commits_empty_for_non_push():
    result = parse_payload({"action": "opened", "issue": {"number": 1}})
    assert result.commits == []


def test_parse_payload_partial_owner_data():
    data = {
        "repository": {
            "name": "demo",
            "owner": {"login": "demo-user"},
        }
    }

    result = parse_payload(data)

    assert result.repository.name == "demo"
    assert result.repository.owner.login == "demo-user"
    assert result.repository.owner.name is None
    assert result.repository.owner.extra == {}
