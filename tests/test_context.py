import json
import os
import pytest
from pathlib import Path

from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from actions_tool_kit.context import Context


@pytest.fixture
def fake_payload():
    return MagicMock(
        repository=SimpleNamespace(
            name="repo-name",
            owner=SimpleNamespace(login="repo-owner"),
        ),
        issue=SimpleNamespace(number=123),
        pull_request=SimpleNamespace(number=456, head_ref="feature-branch", base_ref="main"),
        sender=SimpleNamespace(login="contributor", type="User"),
        extra={"number": 789},
    )


@pytest.fixture
def event_file(tmp_path):
    payload = {
        "repository": {
            "name": "repo-name",
            "owner": {
                "login": "repo-owner"
            }
        },
        "issue": {"number": 123},
        "pull_request": {"number": 456, "head": {"ref": "feature-branch"}, "base": {"ref": "main"}},
        "sender": {"login": "contributor", "type": "User"},
        "extra": {"number": 789}
    }
    file_path = tmp_path / "event.json"
    file_path.write_text(json.dumps(payload))
    return file_path


@patch("actions_tool_kit.context.parse_payload")
def test_context_initialization(mock_parse, event_file, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_WORKFLOW", "CI")
    monkeypatch.setenv("GITHUB_ACTION", "run")
    monkeypatch.setenv("GITHUB_ACTOR", "octocat")
    monkeypatch.setenv("GITHUB_JOB", "build")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "45")
    monkeypatch.setenv("GITHUB_RUN_ID", "1001")

    mock_parse.return_value = MagicMock()

    ctx = Context()
    assert ctx.event_name == "push"
    assert ctx.sha == "abc123"
    assert ctx.ref == "refs/heads/main"
    assert ctx.workflow == "CI"
    assert ctx.action == "run"
    assert ctx.actor == "octocat"
    assert ctx.run_attempt == 2
    assert ctx.run_number == 45
    assert ctx.run_id == 1001


@patch("actions_tool_kit.context.parse_payload")
def test_context_repo_env(mock_parse, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    mock_parse.return_value = MagicMock(repository=None)

    ctx = Context()
    repo = ctx.repo
    assert repo.owner == "octocat"
    assert repo.repo == "my-repo"


@patch("actions_tool_kit.context.parse_payload")
def test_context_repo_from_payload(mock_parse, monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    payload = MagicMock(
        repository=SimpleNamespace(name="repo-name", owner=SimpleNamespace(login="repo-owner")),
        issue=None,
        pull_request=None,
        sender=None,
        extra={}
    )
    mock_parse.return_value = payload

    ctx = Context()
    repo = ctx.repo
    assert repo.owner == "repo-owner"
    assert repo.repo == "repo-name"


@patch("actions_tool_kit.context.parse_payload")
def test_context_repo_missing(mock_parse, monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    mock_parse.return_value = MagicMock(repository=None)

    ctx = Context()
    with pytest.raises(RuntimeError):
        _ = ctx.repo


@patch("actions_tool_kit.context.parse_payload")
def test_context_issue_and_pr(mock_parse, fake_payload, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    mock_parse.return_value = fake_payload
    ctx = Context()

    assert ctx.issue.number == 123
    assert ctx.pr.number == 456


@patch("actions_tool_kit.context.parse_payload")
def test_context_issue_fallback_to_extra(mock_parse, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    payload = MagicMock(
        repository=None,
        issue=None,
        pull_request=None,
        sender=None,
        extra={"number": 999}
    )
    mock_parse.return_value = payload
    ctx = Context()

    issue = ctx.issue
    assert issue.number == 999


@patch("actions_tool_kit.context.parse_payload")
def test_context_issue_missing_all(mock_parse, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    payload = MagicMock(issue=None, pull_request=None, extra={})
    payload.repository = None
    payload.sender = None
    mock_parse.return_value = payload
    ctx = Context()

    with pytest.raises(RuntimeError):
        _ = ctx.issue


@patch("actions_tool_kit.context.parse_payload")
def test_context_sender_from_payload(mock_parse, fake_payload, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    mock_parse.return_value = fake_payload
    ctx = Context()
    assert ctx.sender.login == "contributor"


@patch("actions_tool_kit.context.parse_payload")
def test_context_sender_fallback_to_actor(mock_parse, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTOR", "fallback-user")
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    payload = MagicMock(sender=None, repository=None, issue=None, pull_request=None, extra={})
    mock_parse.return_value = payload

    ctx = Context()
    assert ctx.sender.login == "fallback-user"


@patch("actions_tool_kit.context.parse_payload")
def test_context_branches(mock_parse, fake_payload, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    mock_parse.return_value = fake_payload
    ctx = Context()
    assert ctx.head_branch == "feature-branch"
    assert ctx.base_branch == "main"


@patch("actions_tool_kit.context.parse_payload")
def test_context_ref_name(mock_parse, monkeypatch):
    mock_parse.return_value = MagicMock(repository=None)
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    ctx = Context()
    assert ctx.ref_name == "main"


@patch("actions_tool_kit.context.parse_payload")
def test_context_ref_name_missing(mock_parse, monkeypatch):
    mock_parse.return_value = MagicMock(repository=None)
    monkeypatch.delenv("GITHUB_REF_NAME", raising=False)
    ctx = Context()
    assert ctx.ref_name is None


@patch("actions_tool_kit.context.parse_payload")
def test_context_ref_type(mock_parse, monkeypatch):
    mock_parse.return_value = MagicMock(repository=None)
    monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
    ctx = Context()
    assert ctx.ref_type == "branch"

    monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
    ctx2 = Context()
    assert ctx2.ref_type == "tag"


@patch("actions_tool_kit.context.parse_payload")
def test_context_trigger_actor(mock_parse, monkeypatch):
    mock_parse.return_value = MagicMock(repository=None)
    monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", "rerun-user")
    ctx = Context()
    assert ctx.trigger_actor == "rerun-user"


@patch("actions_tool_kit.context.parse_payload")
def test_context_trigger_actor_missing(mock_parse, monkeypatch):
    mock_parse.return_value = MagicMock(repository=None)
    monkeypatch.delenv("GITHUB_TRIGGERING_ACTOR", raising=False)
    ctx = Context()
    assert ctx.trigger_actor is None


@patch("actions_tool_kit.context.parse_payload")
def test_context_is_pr_true(mock_parse, fake_payload, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    mock_parse.return_value = fake_payload
    ctx = Context()
    assert ctx.is_pr is True


@patch("actions_tool_kit.context.parse_payload")
def test_context_is_pr_false(mock_parse, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    payload = MagicMock(pull_request=None, repository=None, issue=None, sender=None, extra={})
    mock_parse.return_value = payload
    ctx = Context()
    assert ctx.is_pr is False


@pytest.mark.parametrize("event,prop,expected", [
    ("push", "is_push", True),
    ("pull_request", "is_push", False),
    ("issues", "is_issue", True),
    ("push", "is_issue", False),
    ("release", "is_release", True),
    ("push", "is_release", False),
    ("schedule", "is_schedule", True),
    ("push", "is_schedule", False),
])
@patch("actions_tool_kit.context.parse_payload")
def test_context_event_guards(mock_parse, monkeypatch, event, prop, expected):
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    mock_parse.return_value = MagicMock(repository=None)
    ctx = Context()
    assert getattr(ctx, prop) is expected


@patch("actions_tool_kit.context.parse_payload")
def test_context_commits_push_event(mock_parse, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setenv("GITHUB_REPOSITORY", "octocat/my-repo")
    commits = [
        SimpleNamespace(id="abc", message="fix: bug", author=None, url=None,
                        added=[], removed=[], modified=["a.py"]),
    ]
    mock_parse.return_value = MagicMock(
        repository=None, commits=commits
    )
    ctx = Context()
    assert len(ctx.commits) == 1
    assert ctx.commits[0].id == "abc"
    assert ctx.commits[0].message == "fix: bug"


@patch("actions_tool_kit.context.parse_payload")
def test_context_commits_non_push_is_empty(mock_parse, monkeypatch):
    mock_parse.return_value = MagicMock(repository=None, commits=[])
    ctx = Context()
    assert ctx.commits == []


@patch("actions_tool_kit.context.parse_payload")
def test_context_server_url_default(mock_parse, monkeypatch):
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    mock_parse.return_value = MagicMock(repository=None)
    ctx = Context()
    assert ctx.server_url == "https://github.com"


@patch("actions_tool_kit.context.parse_payload")
def test_context_server_url_from_env(mock_parse, monkeypatch):
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.example.com")
    mock_parse.return_value = MagicMock(repository=None)
    ctx = Context()
    assert ctx.server_url == "https://github.example.com"


@patch("actions_tool_kit.context.parse_payload")
def test_context_api_url_default(mock_parse, monkeypatch):
    monkeypatch.delenv("GITHUB_API_URL", raising=False)
    mock_parse.return_value = MagicMock(repository=None)
    ctx = Context()
    assert ctx.api_url == "https://api.github.com"


@patch("actions_tool_kit.context.parse_payload")
def test_context_graphql_url_default(mock_parse, monkeypatch):
    monkeypatch.delenv("GITHUB_GRAPHQL_URL", raising=False)
    mock_parse.return_value = MagicMock(repository=None)
    ctx = Context()
    assert ctx.graphql_url == "https://api.github.com/graphql"


@patch("actions_tool_kit.context.parse_payload")
def test_context_job(mock_parse, monkeypatch):
    monkeypatch.setenv("GITHUB_JOB", "lint")
    mock_parse.return_value = MagicMock(repository=None)
    ctx = Context()
    assert ctx.job == "lint"


@patch("actions_tool_kit.context.parse_payload")
def test_context_is_workflow_dispatch_true(mock_parse, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    mock_parse.return_value = MagicMock(repository=None)
    ctx = Context()
    assert ctx.is_workflow_dispatch is True


@patch("actions_tool_kit.context.parse_payload")
def test_context_is_workflow_dispatch_false(mock_parse, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    mock_parse.return_value = MagicMock(repository=None)
    ctx = Context()
    assert ctx.is_workflow_dispatch is False


@pytest.mark.parametrize("event,prop,expected", [
    ("workflow_dispatch", "is_workflow_dispatch", True),
    ("push", "is_workflow_dispatch", False),
])
@patch("actions_tool_kit.context.parse_payload")
def test_context_workflow_dispatch_guard(mock_parse, monkeypatch, event, prop, expected):
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    mock_parse.return_value = MagicMock(repository=None)
    ctx = Context()
    assert getattr(ctx, prop) is expected
