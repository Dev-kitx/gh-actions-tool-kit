import json
from unittest.mock import MagicMock, call, patch

import pytest

from actions_tool_kit.checks import Annotation, CheckRun, create_check_run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_resp(body: dict):
    m = MagicMock()
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    m.read.return_value = json.dumps(body).encode()
    return m


def _env(monkeypatch, token="gh-tok", repo="my-org/my-repo"):
    monkeypatch.setenv("GITHUB_TOKEN", token)
    monkeypatch.setenv("GITHUB_REPOSITORY", repo)
    monkeypatch.delenv("GITHUB_API_URL", raising=False)


def _create_response(run_id: int = 1) -> dict:
    return {"id": run_id, "status": "queued", "conclusion": None}


# ---------------------------------------------------------------------------
# Annotation._to_dict
# ---------------------------------------------------------------------------

def test_annotation_minimal():
    a = Annotation("src/main.py", 10, 10, "failure", "Bad import")
    d = a._to_dict()
    assert d["path"] == "src/main.py"
    assert d["start_line"] == 10
    assert d["end_line"] == 10
    assert d["annotation_level"] == "failure"
    assert d["message"] == "Bad import"
    assert "title" not in d
    assert "start_column" not in d


def test_annotation_with_all_fields():
    a = Annotation(
        "src/main.py", 5, 5, "warning", "Unused var",
        title="W001",
        start_column=3,
        end_column=12,
        raw_details="extra info",
    )
    d = a._to_dict()
    assert d["title"] == "W001"
    assert d["start_column"] == 3
    assert d["end_column"] == 12
    assert d["raw_details"] == "extra info"


def test_annotation_columns_dropped_on_multiline():
    # GitHub rejects column fields when start_line != end_line
    a = Annotation("f.py", 5, 10, "notice", "msg", start_column=1, end_column=5)
    d = a._to_dict()
    assert "start_column" not in d
    assert "end_column" not in d


def test_annotation_columns_included_on_single_line():
    a = Annotation("f.py", 7, 7, "notice", "msg", start_column=2, end_column=8)
    d = a._to_dict()
    assert d["start_column"] == 2
    assert d["end_column"] == 8


# ---------------------------------------------------------------------------
# CheckRun.create — validation
# ---------------------------------------------------------------------------

def test_create_raises_without_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        CheckRun.create("ci", "abc123")


def test_create_raises_without_repo(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_REPOSITORY"):
        CheckRun.create("ci", "abc123")


def test_create_raises_with_invalid_repo(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "no-slash")
    with pytest.raises(RuntimeError, match="GITHUB_REPOSITORY"):
        CheckRun.create("ci", "abc123")


# ---------------------------------------------------------------------------
# CheckRun.create — happy path
# ---------------------------------------------------------------------------

def test_create_posts_to_correct_url(monkeypatch):
    _env(monkeypatch)
    captured = {}

    def fake_urlopen(req):
        captured["url"] = req.full_url
        captured["method"] = req.method
        captured["body"] = json.loads(req.data)
        return _mock_resp(_create_response(42))

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        run = CheckRun.create("mypy", "deadbeef")

    assert captured["url"] == "https://api.github.com/repos/my-org/my-repo/check-runs"
    assert captured["method"] == "POST"
    assert captured["body"]["name"] == "mypy"
    assert captured["body"]["head_sha"] == "deadbeef"
    assert captured["body"]["status"] == "queued"
    assert run.id == 42


def test_create_includes_output_when_title_given(monkeypatch):
    _env(monkeypatch)
    captured = {}

    def fake_urlopen(req):
        captured["body"] = json.loads(req.data)
        return _mock_resp(_create_response())

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        CheckRun.create("lint", "abc", title="Lint Results", summary="## Summary")

    assert captured["body"]["output"]["title"] == "Lint Results"
    assert captured["body"]["output"]["summary"] == "## Summary"


def test_create_uses_explicit_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
    captured = {}

    def fake_urlopen(req):
        captured["auth"] = req.get_header("Authorization")
        return _mock_resp(_create_response())

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        CheckRun.create("ci", "sha", token="explicit-tok")

    assert captured["auth"] == "Bearer explicit-tok"


def test_create_uses_explicit_repo(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    captured = {}

    def fake_urlopen(req):
        captured["url"] = req.full_url
        return _mock_resp(_create_response())

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        CheckRun.create("ci", "sha", repo="other-org/other-repo")

    assert "other-org/other-repo" in captured["url"]


def test_create_uses_custom_api_url(monkeypatch):
    _env(monkeypatch)
    captured = {}

    def fake_urlopen(req):
        captured["url"] = req.full_url
        return _mock_resp(_create_response())

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        CheckRun.create("ci", "sha", api_url="https://github.corp/api/v3")

    assert captured["url"].startswith("https://github.corp/api/v3")


def test_create_uses_github_api_url_env(monkeypatch):
    _env(monkeypatch)
    monkeypatch.setenv("GITHUB_API_URL", "https://ghe.corp/api/v3")
    captured = {}

    def fake_urlopen(req):
        captured["url"] = req.full_url
        return _mock_resp(_create_response())

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        CheckRun.create("ci", "sha")

    assert captured["url"].startswith("https://ghe.corp/api/v3")


# ---------------------------------------------------------------------------
# CheckRun.update
# ---------------------------------------------------------------------------

def _make_run(monkeypatch, run_id: int = 1) -> CheckRun:
    _env(monkeypatch)
    with patch("actions_tool_kit.checks.urllib.request.urlopen", return_value=_mock_resp(_create_response(run_id))):
        return CheckRun.create("ci", "sha123")


def test_update_status(monkeypatch):
    run = _make_run(monkeypatch)
    captured = {}

    def fake_urlopen(req):
        captured["body"] = json.loads(req.data)
        captured["method"] = req.method
        return _mock_resp({})

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        run.update(status="in_progress")

    assert captured["method"] == "PATCH"
    assert captured["body"]["status"] == "in_progress"
    assert run.status == "in_progress"


def test_update_with_summary(monkeypatch):
    run = _make_run(monkeypatch)
    captured = {}

    def fake_urlopen(req):
        captured["body"] = json.loads(req.data)
        return _mock_resp({})

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        run.update(summary="Running…", details="full details")

    assert captured["body"]["output"]["summary"] == "Running…"
    assert captured["body"]["output"]["text"] == "full details"


def test_update_with_annotations(monkeypatch):
    run = _make_run(monkeypatch)
    annotations = [Annotation("a.py", i, i, "failure", f"err {i}") for i in range(3)]
    captured = {}

    def fake_urlopen(req):
        captured["body"] = json.loads(req.data)
        return _mock_resp({})

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        run.update(annotations=annotations)

    assert len(captured["body"]["output"]["annotations"]) == 3


def test_update_no_op_when_nothing_passed(monkeypatch):
    run = _make_run(monkeypatch)
    with patch("actions_tool_kit.checks.urllib.request.urlopen") as mock_open:
        run.update()
    mock_open.assert_not_called()


# ---------------------------------------------------------------------------
# Annotation batching (>50 per request limit)
# ---------------------------------------------------------------------------

def test_update_batches_annotations_over_50(monkeypatch):
    run = _make_run(monkeypatch)
    annotations = [Annotation("f.py", i, i, "notice", f"msg {i}") for i in range(110)]
    request_bodies = []

    def fake_urlopen(req):
        request_bodies.append(json.loads(req.data))
        return _mock_resp({})

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        run.update(annotations=annotations)

    assert len(request_bodies) == 3  # batches of 50, 50, 10
    assert len(request_bodies[0]["output"]["annotations"]) == 50
    assert len(request_bodies[1]["output"]["annotations"]) == 50
    assert len(request_bodies[2]["output"]["annotations"]) == 10


def test_complete_batches_annotations_over_50(monkeypatch):
    run = _make_run(monkeypatch)
    annotations = [Annotation("f.py", i, i, "failure", f"err {i}") for i in range(75)]
    request_bodies = []

    def fake_urlopen(req):
        request_bodies.append(json.loads(req.data))
        return _mock_resp({})

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        run.complete("failure", annotations=annotations)

    # First 25 flushed via update(), last 50 sent with complete()
    assert len(request_bodies) == 2
    # Final request carries the conclusion
    assert request_bodies[-1]["conclusion"] == "failure"
    assert request_bodies[-1]["status"] == "completed"


# ---------------------------------------------------------------------------
# CheckRun.complete
# ---------------------------------------------------------------------------

def test_complete_sets_conclusion(monkeypatch):
    run = _make_run(monkeypatch)
    captured = {}

    def fake_urlopen(req):
        captured["body"] = json.loads(req.data)
        return _mock_resp({})

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        run.complete("success", summary="All good")

    assert captured["body"]["status"] == "completed"
    assert captured["body"]["conclusion"] == "success"
    assert captured["body"]["output"]["summary"] == "All good"
    assert run.status == "completed"
    assert run.conclusion == "success"


def test_complete_with_annotations(monkeypatch):
    run = _make_run(monkeypatch)
    annotations = [Annotation("x.py", 1, 1, "failure", "bad")]
    captured = {}

    def fake_urlopen(req):
        captured["body"] = json.loads(req.data)
        return _mock_resp({})

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        run.complete("failure", annotations=annotations)

    assert len(captured["body"]["output"]["annotations"]) == 1
    assert captured["body"]["output"]["annotations"][0]["path"] == "x.py"


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

def test_context_manager_marks_in_progress_on_enter(monkeypatch):
    bodies = []

    def fake_urlopen(req):
        bodies.append(json.loads(req.data) if req.data else {})
        return _mock_resp(_create_response(1))

    _env(monkeypatch)
    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        with CheckRun.create("ci", "sha") as run:
            pass  # __exit__ will call complete("success")

    statuses = [b.get("status") for b in bodies]
    assert "in_progress" in statuses
    assert "completed" in statuses


def test_context_manager_success(monkeypatch):
    _env(monkeypatch)
    captured = []

    def fake_urlopen(req):
        captured.append(json.loads(req.data) if req.data else {})
        return _mock_resp(_create_response(1))

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        with CheckRun.create("ci", "sha") as run:
            pass

    final = captured[-1]
    assert final["conclusion"] == "success"
    assert final["status"] == "completed"


def test_context_manager_failure_on_exception(monkeypatch):
    _env(monkeypatch)
    captured = []

    def fake_urlopen(req):
        captured.append(json.loads(req.data) if req.data else {})
        return _mock_resp(_create_response(1))

    with pytest.raises(ValueError):
        with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
            with CheckRun.create("ci", "sha"):
                raise ValueError("something broke")

    final = captured[-1]
    assert final["conclusion"] == "failure"


def test_context_manager_does_not_double_complete(monkeypatch):
    _env(monkeypatch)
    patch_calls = []

    def fake_urlopen(req):
        body = json.loads(req.data) if req.data else {}
        patch_calls.append(body)
        return _mock_resp(_create_response(1))

    with patch("actions_tool_kit.checks.urllib.request.urlopen", side_effect=fake_urlopen):
        with CheckRun.create("ci", "sha") as run:
            run.complete("success")  # already completed inside the block

    completed = [b for b in patch_calls if b.get("status") == "completed"]
    assert len(completed) == 1  # __exit__ should not call complete() again


# ---------------------------------------------------------------------------
# create_check_run convenience wrapper
# ---------------------------------------------------------------------------

def test_create_check_run_convenience(monkeypatch):
    _env(monkeypatch)

    with patch("actions_tool_kit.checks.urllib.request.urlopen", return_value=_mock_resp(_create_response(99))):
        run = create_check_run("lint", "abc")

    assert isinstance(run, CheckRun)
    assert run.id == 99
    assert run.name == "lint"
