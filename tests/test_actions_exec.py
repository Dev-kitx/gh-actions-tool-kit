import sys
import pytest

from actions_tool_kit.actions_exec import ExecResult, run


def test_exec_result_success():
    result = ExecResult(returncode=0, stdout="ok", stderr="")
    assert result.success is True


def test_exec_result_failure():
    result = ExecResult(returncode=1, stdout="", stderr="oops")
    assert result.success is False


def test_run_simple_command():
    result = run(sys.executable, ["-c", "print('hello')"], capture_output=True)
    assert result.success
    assert result.stdout.strip() == "hello"
    assert result.stderr == ""


def test_run_argv_list():
    result = run([sys.executable, "-c", "import sys; sys.exit(0)"], capture_output=True)
    assert result.returncode == 0


def test_run_captures_stderr():
    result = run(
        sys.executable,
        ["-c", "import sys; sys.stderr.write('err\\n')"],
        capture_output=True,
    )
    assert "err" in result.stderr


def test_run_non_zero_exit():
    result = run(sys.executable, ["-c", "import sys; sys.exit(2)"], capture_output=True)
    assert result.returncode == 2
    assert not result.success


def test_run_check_raises_on_failure():
    with pytest.raises(RuntimeError, match="exited with code"):
        run(sys.executable, ["-c", "import sys; sys.exit(1)"], check=True)


def test_run_check_does_not_raise_on_success():
    result = run(sys.executable, ["-c", "pass"], check=True)
    assert result.success


def test_run_with_env(monkeypatch):
    result = run(
        sys.executable,
        ["-c", "import os; print(os.environ['MY_VAR'])"],
        env={"MY_VAR": "hello_env"},
        capture_output=True,
    )
    assert result.stdout.strip() == "hello_env"


def test_run_with_cwd(tmp_path):
    result = run(
        sys.executable,
        ["-c", "import os; print(os.getcwd())"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    assert str(tmp_path) in result.stdout


def test_run_silent_does_not_capture():
    result = run(
        sys.executable,
        ["-c", "print('should be discarded')"],
        silent=True,
    )
    assert result.stdout == ""
    assert result.returncode == 0


def test_run_unknown_command_raises():
    with pytest.raises(FileNotFoundError):
        run("__nonexistent_binary_xyz__")
