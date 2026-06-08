from __future__ import annotations

import io
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List

# Matches the wire format emitted by _cmd():  ::command[ props]::message
_CMD_RE = re.compile(r"^::([^:\s]+)(?:\s([^:]*))?::(.*)$")


@dataclass
class CapturedCommand:
    """A single parsed workflow command captured from stdout.

    Attributes:
        command: The command verb (e.g. ``"notice"``, ``"error"``).
        message: The message payload after the trailing ``::`` separator.
        props: Key-value pairs from the command properties section
               (e.g. ``{"file": "a.py", "line": "10"}``).
    """

    command: str
    message: str
    props: Dict[str, str] = field(default_factory=dict)


class ActionCommandCapture:
    """Context manager that captures GitHub Actions workflow commands during tests.

    Intercepts stdout while active, parses every ``::command::message`` line
    into :class:`CapturedCommand` objects, and restores stdout on exit.

    Example::

        with ActionCommandCapture() as cap:
            notice("hello", title="Hi", file="a.py", line=1)
            error("boom")

        assert cap.notices[0].message == "hello"
        assert cap.notices[0].props["title"] == "Hi"
        assert cap.errors[0].message == "boom"
    """

    def __init__(self) -> None:
        self.commands: List[CapturedCommand] = []
        self.raw_lines: List[str] = []
        self._old_stdout: object = None
        self._buf: io.StringIO | None = None

    def __enter__(self) -> "ActionCommandCapture":
        self._old_stdout = sys.stdout
        self._buf = io.StringIO()
        sys.stdout = self._buf
        return self

    def __exit__(self, *_: object) -> None:
        sys.stdout = self._old_stdout
        assert self._buf is not None
        self._parse(self._buf.getvalue())

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse(self, text: str) -> None:
        for line in text.splitlines():
            self.raw_lines.append(line)
            m = _CMD_RE.match(line)
            if not m:
                continue
            command = m.group(1)
            props_str = m.group(2) or ""
            message = m.group(3)
            props: Dict[str, str] = {}
            for pair in props_str.split(","):
                if "=" in pair:
                    k, _, v = pair.partition("=")
                    props[k.strip()] = v.strip()
            self.commands.append(
                CapturedCommand(command=command, message=message, props=props)
            )

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def of_type(self, command: str) -> List[CapturedCommand]:
        """Return all captured commands matching *command*."""
        return [c for c in self.commands if c.command == command]

    @property
    def notices(self) -> List[CapturedCommand]:
        """All ``::notice::`` commands."""
        return self.of_type("notice")

    @property
    def warnings(self) -> List[CapturedCommand]:
        """All ``::warning::`` commands."""
        return self.of_type("warning")

    @property
    def errors(self) -> List[CapturedCommand]:
        """All ``::error::`` commands."""
        return self.of_type("error")

    @property
    def debug_messages(self) -> List[CapturedCommand]:
        """All ``::debug::`` commands."""
        return self.of_type("debug")

    @property
    def outputs(self) -> List[CapturedCommand]:
        """All ``::set-output::`` commands (legacy output method)."""
        return self.of_type("set-output")


__all__ = ["CapturedCommand", "ActionCommandCapture"]
