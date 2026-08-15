import pytest

from actions_tool_kit import actions_core as core
from actions_tool_kit.testing import ActionCommandCapture, CapturedCommand


def test_captures_notice():
    with ActionCommandCapture() as cap:
        core.notice("hello")
    assert len(cap.notices) == 1
    assert cap.notices[0].message == "hello"


def test_captures_notice_props():
    with ActionCommandCapture() as cap:
        core.notice("msg", title="T", file="f.py", line=10, col=5)
    cmd = cap.notices[0]
    assert cmd.props["title"] == "T"
    assert cmd.props["file"] == "f.py"
    assert cmd.props["line"] == "10"
    assert cmd.props["col"] == "5"


def test_captures_warning():
    with ActionCommandCapture() as cap:
        core.warning("warn msg")
    assert cap.warnings[0].message == "warn msg"


def test_captures_error():
    with ActionCommandCapture() as cap:
        core.error("err msg", title="Oops")
    cmd = cap.errors[0]
    assert cmd.message == "err msg"
    assert cmd.props["title"] == "Oops"


def test_captures_debug():
    with ActionCommandCapture() as cap:
        core.debug("dbg")
    assert cap.debug_messages[0].message == "dbg"


def test_captures_multiple_commands():
    with ActionCommandCapture() as cap:
        core.notice("n1")
        core.notice("n2")
        core.warning("w1")
        core.error("e1")
    assert len(cap.notices) == 2
    assert len(cap.warnings) == 1
    assert len(cap.errors) == 1
    assert cap.notices[0].message == "n1"
    assert cap.notices[1].message == "n2"


def test_of_type():
    with ActionCommandCapture() as cap:
        core.debug("d1")
        core.debug("d2")
    dbgs = cap.of_type("debug")
    assert len(dbgs) == 2


def test_non_command_lines_in_raw():
    with ActionCommandCapture() as cap:
        print("plain output")
        core.notice("annotated")
    assert any("plain output" in l for l in cap.raw_lines)
    assert len(cap.notices) == 1


def test_captured_command_dataclass():
    cmd = CapturedCommand(command="notice", message="hi", props={"title": "T"})
    assert cmd.command == "notice"
    assert cmd.message == "hi"
    assert cmd.props["title"] == "T"


def test_captures_end_line_and_end_column():
    with ActionCommandCapture() as cap:
        core.warning("range warn", file="x.py", line=1, end_line=5, col=1, end_column=10)
    cmd = cap.warnings[0]
    assert cmd.props.get("endLine") == "5"
    assert cmd.props.get("endColumn") == "10"


def test_stdout_restored_after_context():
    import sys
    original = sys.stdout
    with ActionCommandCapture():
        pass
    assert sys.stdout is original
