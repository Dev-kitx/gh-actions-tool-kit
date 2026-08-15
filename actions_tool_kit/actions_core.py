# actions_core.py
# Minimal Python equivalent of @actions/core for GitHub Actions (typed + docstrings)

from __future__ import annotations

import os
import sys
import uuid
from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Optional, Union


def _file_from_env(var: str) -> Optional[str]:
    """Return the path from an env var if set and non-empty, else None.

    Args:
        var: Environment variable name.

    Returns:
        The string path if present, otherwise None.
    """
    p: Optional[str] = os.getenv(var)
    return p if p and p.strip() else None


def _append_line(filepath: str, line: str) -> None:
    """Append a single line to a file, ensuring a trailing newline."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def _append_env_file_command(filepath: str, name: str, value: str) -> None:
    """Write a name=value pair to a GitHub env file, using heredoc syntax for multiline values.

    Single-line values use ``name=value`` format.
    Multiline values use the heredoc format required by newer runners::

        name<<_delimiter_
        value line 1
        value line 2
        _delimiter_
    """
    with open(filepath, "a", encoding="utf-8") as f:
        if "\n" in value or "\r" in value:
            delim = f"ghadelimiter_{uuid.uuid4().hex}"
            f.write(f"{name}<<{delim}\n{value}\n{delim}\n")
        else:
            f.write(f"{name}={value}\n")


def _serialize_props(**props: Any) -> str:
    """Serialize command properties per workflow command format with escaping.

    Note:
        See GH Actions 'workflow commands' docs for escaping rules.

    Returns:
        A string like " key=val,key2=val2" or empty string if no props.
    """

    def esc(val: Any) -> str:
        s = str(val)
        return (
            s.replace("%", "%25")
            .replace("\r", "%0D")
            .replace("\n", "%0A")
            .replace(":", "%3A")
            .replace(",", "%2C")
        )

    items: list[str] = [
        f"{k}={esc(v)}" for k, v in props.items() if v not in (None, "", False)
    ]
    return " " + ",".join(items) if items else ""


def _escape_msg(msg: Union[str, Any]) -> str:
    """Escape a command message payload per GH runner rules.

    Args:
        msg: Message to escape.

    Returns:
        Escaped message.
    """
    s = str(msg)
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _cmd(command: str, message: str = "", **props: Any) -> None:
    """Emit a raw workflow command to stdout.

    Args:
        command: Command verb (e.g., 'notice', 'warning').
        message: Optional message body.
        **props: Optional command properties such as title=, file=, line=.
    """
    sys.stdout.write(
        f"::{command}{_serialize_props(**props)}::{_escape_msg(message)}\n"
    )
    sys.stdout.flush()


# ---------- inputs ----------
def get_input(
    name: str,
    *,
    required: bool = False,
    trim: bool = True,
    default: Optional[str] = None,
) -> str:
    """Read an action input from environment (INPUT_<NAME>).

    Args:
        name: Input name as defined in workflow 'with:' (case-insensitive).
        required: If True, raise if missing and also emit a failed error.
        trim: If True, strip surrounding whitespace.
        default: Optional default if not provided.

    Returns:
        The input value (possibly empty string if not required and missing).

    Raises:
        RuntimeError: If required is True and the input is missing.
    """
    key = f"INPUT_{name.replace(' ', '_').upper()}"
    val: Optional[str] = os.getenv(key)
    if val is None or val == "":
        if default is not None:
            return default
        if required:
            set_failed(f"Input required and not supplied: {name}")
            raise RuntimeError(f"Missing required input: {name}")
        return ""
    return val.strip() if trim else val


def get_multiline_input(
    name: str,
    *,
    required: bool = False,
    trim: bool = True,
) -> list[str]:
    """Read a multiline action input as a list of non-empty lines.

    Each newline-separated segment becomes one list element. Empty lines are
    dropped after trimming so callers get a clean list without filtering.

    Args:
        name: Input name as defined in workflow 'with:'.
        required: If True, raise when the input is missing or blank.
        trim: If True, strip whitespace from each line before filtering.

    Returns:
        List of non-empty line strings.
    """
    raw = get_input(name, required=required, trim=False)
    lines = raw.splitlines()
    if trim:
        lines = [ln.strip() for ln in lines]
    return [ln for ln in lines if ln]


def get_boolean_input(
    name: str,
    *,
    required: bool = False,
    trim: bool = True,
    default: Optional[str] = None,
) -> bool:
    """Read a boolean action input.

    Accepts truthy values: 1, true, t, yes, y, on (case-insensitive).

    Args:
        name: Input name.
        required: If True, raise when missing.
        trim: If True, strip whitespace.
        default: Default string passed through truthy check if provided.

    Returns:
        Parsed boolean value.
    """
    val: str = get_input(name, required=required, trim=trim, default=default)
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


# ---------- outputs / env / path / state / summary ----------
def set_output(name: str, value: Union[str, int, float, bool]) -> None:
    """Set a step output using $GITHUB_OUTPUT, with legacy fallback.

    Multiline values are written using the heredoc delimiter format required
    by GitHub Actions runners so that newlines are preserved correctly.

    Args:
        name: Output variable name.
        value: Output value; will be stringified.
    """
    v = str(value)
    path: Optional[str] = _file_from_env("GITHUB_OUTPUT")
    if not path:
        _cmd("set-output", f"{name}={v}")  # legacy/local fallback
        return
    _append_env_file_command(path, name, v)


def export_variable(name: str, value: Union[str, int, float, bool]) -> None:
    """Export an environment variable for subsequent steps.

    Multiline values are written using the heredoc delimiter format required
    by GitHub Actions runners so that newlines are preserved correctly.

    Args:
        name: Variable name.
        value: Value; will be stringified.
    """
    v = str(value)
    path: Optional[str] = _file_from_env("GITHUB_ENV")
    if not path:
        os.environ[name] = v  # local fallback
        return
    _append_env_file_command(path, name, v)


def add_path(input_path: str) -> None:
    """Prepend a path to the runner PATH for subsequent steps.

    Args:
        input_path: Directory to add to PATH.
    """
    path: Optional[str] = _file_from_env("GITHUB_PATH")
    if not path:
        os.environ["PATH"] = f"{input_path}{os.pathsep}{os.environ.get('PATH','')}"
        return
    _append_line(path, input_path)


def save_state(name: str, value: Union[str, int, float, bool]) -> None:
    """Persist state for the post-step using $GITHUB_STATE (runner-managed).

    Note:
        When not running on the runner (local tests), this function stores
        the value in process env under STATE_<name> as a convenience.

    Args:
        name: State key.
        value: State value; will be stringified.
    """
    v = str(value)
    path: Optional[str] = _file_from_env("GITHUB_STATE")
    if not path:
        os.environ[f"STATE_{name}"] = v  # local fallback
        return
    _append_line(path, f"{name}={v}")


def get_state(name: str) -> str:
    """Return locally saved state (testing fallback only).

    Note:
        On the real runner, post-steps read $GITHUB_STATE file directly.
        This helper only returns the local fallback (STATE_<name>).

    Args:
        name: State key.

    Returns:
        The value if set via local fallback; empty string otherwise.
    """
    return os.getenv(f"STATE_{name}", "")


def is_debug() -> bool:
    """Return True when step debug logging is enabled (RUNNER_DEBUG=1)."""
    return os.getenv("RUNNER_DEBUG") == "1"


def stop_commands(end_token: str) -> None:
    """Stop workflow command processing until resume_commands() is called.

    Use this before emitting untrusted content so the runner does not
    interpret it as workflow commands.

    Args:
        end_token: A unique token used to resume commands later.
    """
    _cmd("stop-commands", end_token)


def resume_commands(end_token: str) -> None:
    """Resume workflow command processing after stop_commands().

    Args:
        end_token: The same token passed to stop_commands().
    """
    sys.stdout.write(f"::{end_token}::\n")
    sys.stdout.flush()


def set_command_echo(enabled: bool) -> None:
    """Toggle workflow command echoing in the runner log.

    When enabled, every workflow command (e.g. ``::set-output::``) is echoed
    to the log alongside its effect. Useful for debugging action internals.

    Args:
        enabled: True to turn echoing on, False to turn it off.
    """
    _cmd("echo", "on" if enabled else "off")


def set_secret(secret: str) -> None:
    """Mask a secret in the logs using 'add-mask' command.

    Args:
        secret: The sensitive string to mask.
    """
    _cmd("add-mask", secret)


def append_summary(markdown: Union[str, Iterable[str]]) -> None:
    """Append markdown to the step summary panel.

    Args:
        markdown: Markdown string or iterable of chunks.

    Note:
        When $GITHUB_STEP_SUMMARY is not set (local runs), content is printed
        between markers to stdout for easy preview.
    """
    body: str = "".join(markdown) if not isinstance(markdown, str) else markdown
    path: Optional[str] = _file_from_env("GITHUB_STEP_SUMMARY")
    if not path:
        sys.stdout.write(
            "\n--- STEP SUMMARY (local) ---\n"
            + body
            + "\n----------------------------\n"
        )
        sys.stdout.flush()
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(body)


# ---------- logging / annotations ----------
def debug(message: Union[str, Any]) -> None:
    """Emit a debug annotation (visible when step debug is enabled)."""
    _cmd("debug", str(message))


def notice(
    message: Union[str, Any],
    *,
    title: Optional[str] = None,
    file: Optional[str] = None,
    line: Optional[int] = None,
    end_line: Optional[int] = None,
    col: Optional[int] = None,
    end_column: Optional[int] = None,
) -> None:
    """Emit a non-fatal informational annotation (blue box in UI).

    Args:
        message: The content to display.
        title: Optional short title shown in UI.
        file: Optional file path to attach to annotation.
        line: Optional start line number.
        end_line: Optional end line number for range annotations.
        col: Optional start column number.
        end_column: Optional end column number for range annotations.
    """
    _cmd(
        "notice", str(message),
        title=title, file=file, line=line, endLine=end_line, col=col, endColumn=end_column,
    )


def warning(
    message: Union[str, Any],
    *,
    title: Optional[str] = None,
    file: Optional[str] = None,
    line: Optional[int] = None,
    end_line: Optional[int] = None,
    col: Optional[int] = None,
    end_column: Optional[int] = None,
) -> None:
    """Emit a warning annotation (yellow).

    Args:
        message: The content to display.
        title: Optional short title.
        file: Optional file path.
        line: Optional start line number.
        end_line: Optional end line number for range annotations.
        col: Optional start column number.
        end_column: Optional end column number for range annotations.
    """
    _cmd(
        "warning", str(message),
        title=title, file=file, line=line, endLine=end_line, col=col, endColumn=end_column,
    )


def error(
    message: Union[str, Any],
    *,
    title: Optional[str] = None,
    file: Optional[str] = None,
    line: Optional[int] = None,
    end_line: Optional[int] = None,
    col: Optional[int] = None,
    end_column: Optional[int] = None,
) -> None:
    """Emit an error annotation (red).

    Args:
        message: The content to display.
        title: Optional short title.
        file: Optional file path.
        line: Optional start line number.
        end_line: Optional end line number for range annotations.
        col: Optional start column number.
        end_column: Optional end column number for range annotations.
    """
    _cmd(
        "error", str(message),
        title=title, file=file, line=line, endLine=end_line, col=col, endColumn=end_column,
    )


def set_failed(message: Union[str, Any], fail: bool = False) -> None:
    """Mark the step as failed by emitting an error annotation.

     Note:
        This function does NOT exit the process. Callers may raise or sys.exit(1).
        GitHub Annotations (`::error::`) DO NOT fail the step by themselves.
        Exiting with a non-zero status is required to fail the job.

    Args:
        message: The failure message.
        fail: If True (default), raise SystemExit(1) to fail the step.
    """
    error(str(message))
    if fail:
        raise SystemExit(1)


def fail_action(message: Union[str, Any]) -> None:
    """
    Emit an error annotation and immediately exit the process with status 1.
    Args:
        message:
    Returns:
        The failure message.
    """
    error(str(message))
    raise SystemExit(1)

# ---------- groups ----------
def start_group(name: str) -> None:
    """Start a collapsible log group with the given name."""
    _cmd("group", name)


def end_group() -> None:
    """End the current collapsible log group."""
    _cmd("endgroup")


@contextmanager
def group(name: str) -> Iterator[None]:
    """Context manager that wraps logs in a collapsible group.

    Example:
        with group("Install deps"):
            print("pip install ...")
    """
    start_group(name)
    try:
        yield
    finally:
        end_group()


__all__ = [
    "get_input",
    "get_boolean_input",
    "get_multiline_input",
    "set_output",
    "export_variable",
    "add_path",
    "save_state",
    "get_state",
    "set_secret",
    "append_summary",
    "is_debug",
    "stop_commands",
    "resume_commands",
    "set_command_echo",
    "debug",
    "notice",
    "warning",
    "error",
    "set_failed",
    "fail_action",
    "start_group",
    "end_group",
    "group",
]
