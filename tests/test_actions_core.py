from pathlib import Path

import pytest

from actions_tool_kit import actions_core as core


def test_get_input_required_and_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # default when missing
    assert core.get_input("foo", default="bar") == "bar"

    # required raises
    with pytest.raises(RuntimeError):
        core.get_input("missing", required=True)

    # provided via env
    monkeypatch.setenv("INPUT_NAME", " Akash ")
    assert core.get_input("name") == "Akash"
    assert core.get_input("name", trim=False) == " Akash "


@pytest.mark.parametrize(
    "val,expected",
    [
        ("true", True),
        ("TrUe", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("0", False),
        ("no", False),
        ("", False),
    ],
)
def test_get_boolean_input(monkeypatch: pytest.MonkeyPatch, val: str, expected: bool) -> None:
    monkeypatch.setenv("INPUT_FLAG", val)
    assert core.get_boolean_input("flag") is expected


def test_set_output_and_export_variable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"
    envf = tmp_path / "env.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("GITHUB_ENV", str(envf))

    core.set_output("result", "ok")
    core.export_variable("FOO", "bar")

    assert out.read_text().strip() == "result=ok"
    assert envf.read_text().strip() == "FOO=bar"


def test_set_output_multiline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))

    core.set_output("json_blob", '{"a": 1,\n"b": 2}')

    content = out.read_text()
    # Must use heredoc format — simple name=value would break the runner
    assert "<<" in content
    assert '{"a": 1,' in content
    assert '"b": 2}' in content
    # The delimiter line must appear twice (open and close)
    lines = content.splitlines()
    delim_line = lines[0].split("<<")[1]
    assert lines[-1] == delim_line


def test_export_variable_multiline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    envf = tmp_path / "env.txt"
    monkeypatch.setenv("GITHUB_ENV", str(envf))

    core.export_variable("REPORT", "line one\nline two\nline three")

    content = envf.read_text()
    assert "<<" in content
    assert "line one" in content
    assert "line three" in content


def test_set_output_singleline_no_heredoc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))

    core.set_output("tag", "v1.2.3")

    content = out.read_text().strip()
    assert content == "tag=v1.2.3"
    assert "<<" not in content


def test_add_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pathf = tmp_path / "path.txt"
    monkeypatch.setenv("GITHUB_PATH", str(pathf))
    core.add_path("/tool/bin")
    assert pathf.read_text().strip() == "/tool/bin"


def test_state_local_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    # No GITHUB_STATE -> uses local fallback
    monkeypatch.delenv("GITHUB_STATE", raising=False)
    core.save_state("TOKEN", "abc")
    assert core.get_state("TOKEN") == "abc"


def test_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sumf = tmp_path / "sum.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(sumf))
    core.append_summary("# Hello\n")
    assert sumf.read_text() == "# Hello\n"


def test_get_multiline_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INPUT_FILES", "a.py\nb.py\n\nc.py")
    assert core.get_multiline_input("files") == ["a.py", "b.py", "c.py"]

    # trim=False keeps raw lines (still drops empty)
    monkeypatch.setenv("INPUT_FILES", "  x.py  \n  y.py  ")
    assert core.get_multiline_input("files", trim=False) == ["  x.py  ", "  y.py  "]

    # required raises when missing
    with pytest.raises(RuntimeError):
        core.get_multiline_input("not_set", required=True)

    # missing but not required → empty list
    assert core.get_multiline_input("totally_absent") == []


def test_is_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUNNER_DEBUG", "1")
    assert core.is_debug() is True

    monkeypatch.setenv("RUNNER_DEBUG", "0")
    assert core.is_debug() is False

    monkeypatch.delenv("RUNNER_DEBUG", raising=False)
    assert core.is_debug() is False


def test_stop_and_resume_commands(capsys: pytest.CaptureFixture[str]) -> None:
    token = "myUniqueToken42"
    core.stop_commands(token)
    core.resume_commands(token)
    out = capsys.readouterr().out
    assert f"::stop-commands::{token}" in out
    assert f"::{token}::" in out


def test_notice_and_group(capsys: pytest.CaptureFixture[str]) -> None:
    core.notice("hello", title="greet", file="a.py", line=10)
    with core.group("Stuff"):
        print("inside")
    captured = capsys.readouterr().out.splitlines()
    # Notice line present
    assert any(l.startswith("::notice ") and "::hello" in l for l in captured)
    # Group markers present
    assert any(l.startswith("::group::Stuff") for l in captured)
    assert any(l == "::endgroup::" for l in captured)


def test_annotation_range_parameters(capsys: pytest.CaptureFixture[str]) -> None:
    core.notice("n", file="f.py", line=1, end_line=5, col=3, end_column=10)
    core.warning("w", file="f.py", line=2, end_line=6)
    core.error("e", file="f.py", line=3, end_line=7, col=1, end_column=8)
    out = capsys.readouterr().out
    assert "endLine=5" in out
    assert "endColumn=10" in out
    assert "endLine=6" in out
    assert "endLine=7" in out
    assert "endColumn=8" in out


def test_set_command_echo(capsys: pytest.CaptureFixture[str]) -> None:
    core.set_command_echo(True)
    core.set_command_echo(False)
    out = capsys.readouterr().out
    assert "::echo::on" in out
    assert "::echo::off" in out


def test_set_secret_masks_in_logs(capsys: pytest.CaptureFixture[str]) -> None:
    core.set_secret("supersecret")
    out = capsys.readouterr().out
    assert "::add-mask::supersecret" in out

def test_set_failed_no_exit():
    # set_failed(exit=False) logs but does not exit
    core.set_failed("Logged error only", fail=False)

def test_fail_now():
    with pytest.raises(SystemExit) as ex:
        core.fail_action("Immediate fail")
    assert ex.value.code == 1
