from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union


@dataclass
class ExecResult:
    """
    Result of a subprocess invocation.

    Attributes:
        returncode (int): Process exit code.
        stdout (str): Captured stdout (empty string when capture_output=False).
        stderr (str): Captured stderr (empty string when capture_output=False).
    """

    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        """True when the process exited with code 0."""
        return self.returncode == 0


def run(
    cmd: Union[str, Sequence[str]],
    args: Sequence[str] = (),
    *,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    capture_output: bool = False,
    check: bool = False,
    silent: bool = False,
) -> ExecResult:
    """Run a subprocess and return an ExecResult.

    Args:
        cmd: Command to run. Pass a string (e.g. "git") or a full argv list
             (e.g. ["git", "status"]). When a list is given, ``args`` is ignored.
        args: Extra arguments appended after ``cmd`` when ``cmd`` is a string.
        cwd: Working directory for the subprocess.
        env: Extra environment variables merged on top of the current process env.
        capture_output: Capture stdout/stderr into ExecResult instead of streaming
                        them to the terminal.
        check: Raise RuntimeError when the command exits non-zero.
        silent: Discard stdout/stderr (sends to /dev/null). Ignored when
                capture_output=True.

    Returns:
        ExecResult with returncode, stdout, and stderr.

    Raises:
        RuntimeError: When check=True and the command exits non-zero.
        FileNotFoundError: When the command binary is not found.
    """
    if isinstance(cmd, str):
        full_cmd: List[str] = [cmd, *args]
    else:
        full_cmd = list(cmd)

    merged_env: Optional[Dict[str, str]] = None
    if env is not None:
        merged_env = {**os.environ, **env}

    proc: subprocess.CompletedProcess[Any]
    if capture_output:
        proc = subprocess.run(
            full_cmd,
            cwd=cwd,
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out = proc.stdout or ""
        err = proc.stderr or ""
    else:
        stdout_target = subprocess.DEVNULL if silent else None
        stderr_target = subprocess.DEVNULL if silent else None
        proc = subprocess.run(
            full_cmd,
            cwd=cwd,
            env=merged_env,
            stdout=stdout_target,
            stderr=stderr_target,
        )
        out = ""
        err = ""

    result = ExecResult(returncode=proc.returncode, stdout=out, stderr=err)

    if check and not result.success:
        raise RuntimeError(
            f"Command {full_cmd!r} exited with code {proc.returncode}.\n"
            f"stderr: {err.strip()}"
        )

    return result


__all__ = ["ExecResult", "run"]
