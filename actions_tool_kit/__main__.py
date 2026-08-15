from __future__ import annotations

import sys
import argparse
from pathlib import Path

from actions_tool_kit.actions_core import (
    notice,
    warning,
    error,
    debug,
    get_input,
    get_boolean_input,
    get_multiline_input,
    set_output,
    export_variable,
    set_secret,
    append_summary,
    group,
    is_debug,
    stop_commands,
    resume_commands,
    set_command_echo,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="actions-core",
        description="Tiny @actions/core-style CLI (Python)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # --- notice ---
    p_notice = sub.add_parser("notice", help="Emit a notice annotation")
    p_notice.add_argument("message")
    p_notice.add_argument("--title")
    p_notice.add_argument("--file")
    p_notice.add_argument("--line", type=int)
    p_notice.add_argument("--end-line", type=int, dest="end_line")
    p_notice.add_argument("--col", type=int)
    p_notice.add_argument("--end-column", type=int, dest="end_column")

    # --- warning ---
    p_warn = sub.add_parser("warning", help="Emit a warning annotation")
    p_warn.add_argument("message")
    p_warn.add_argument("--title")
    p_warn.add_argument("--file")
    p_warn.add_argument("--line", type=int)
    p_warn.add_argument("--end-line", type=int, dest="end_line")
    p_warn.add_argument("--col", type=int)
    p_warn.add_argument("--end-column", type=int, dest="end_column")

    # --- error ---
    p_err = sub.add_parser("error", help="Emit an error annotation")
    p_err.add_argument("message")
    p_err.add_argument("--title")
    p_err.add_argument("--file")
    p_err.add_argument("--line", type=int)
    p_err.add_argument("--end-line", type=int, dest="end_line")
    p_err.add_argument("--col", type=int)
    p_err.add_argument("--end-column", type=int, dest="end_column")

    # --- debug ---
    p_dbg = sub.add_parser("debug", help="Emit a debug message")
    p_dbg.add_argument("message")

    # --- get-input ---
    p_get = sub.add_parser("get-input", help="Read an INPUT_<NAME> env var")
    p_get.add_argument("name")
    p_get.add_argument("--required", action="store_true")
    p_get.add_argument("--default")

    # --- get-multiline-input ---
    p_ml = sub.add_parser(
        "get-multiline-input",
        help="Read a multiline input; prints each line on its own stdout line",
    )
    p_ml.add_argument("name")
    p_ml.add_argument("--required", action="store_true")

    # --- get-boolean-input ---
    p_bool = sub.add_parser("get-boolean-input", help="Read a boolean INPUT_<NAME>")
    p_bool.add_argument("name")
    p_bool.add_argument("--required", action="store_true")

    # --- set-output ---
    p_out = sub.add_parser("set-output", help="Write key=value to $GITHUB_OUTPUT")
    p_out.add_argument("pair", help="Format: key=value")

    # --- export ---
    p_env = sub.add_parser("export", help="Export env var (key=value)")
    p_env.add_argument("pair", help="Format: key=value")

    # --- mask ---
    p_mask = sub.add_parser("mask", help="Mask a secret in logs")
    p_mask.add_argument("secret")

    # --- summary ---
    p_sum = sub.add_parser("summary", help="Append a markdown file to the step summary")
    p_sum.add_argument("path", type=Path)

    # --- group ---
    p_group = sub.add_parser(
        "group", help="Wrap stdin lines in a collapsible log group"
    )
    p_group.add_argument("name")

    # --- is-debug ---
    sub.add_parser("is-debug", help="Exit 0 if RUNNER_DEBUG=1, else exit 1")

    # --- stop-commands ---
    p_stop = sub.add_parser(
        "stop-commands", help="Emit ::stop-commands:: to pause command processing"
    )
    p_stop.add_argument("token", help="Unique token used to resume later")

    # --- resume-commands ---
    p_resume = sub.add_parser(
        "resume-commands", help="Emit ::<token>:: to resume command processing"
    )
    p_resume.add_argument("token", help="Token that was passed to stop-commands")

    # --- echo ---
    p_echo = sub.add_parser("echo", help="Toggle workflow command echoing")
    p_echo.add_argument("state", choices=["on", "off"])

    # ------------------------------------------------------------------
    args = parser.parse_args()

    if args.cmd == "notice":
        notice(
            args.message,
            title=args.title,
            file=args.file,
            line=args.line,
            end_line=args.end_line,
            col=args.col,
            end_column=args.end_column,
        )
    elif args.cmd == "warning":
        warning(
            args.message,
            title=args.title,
            file=args.file,
            line=args.line,
            end_line=args.end_line,
            col=args.col,
            end_column=args.end_column,
        )
    elif args.cmd == "error":
        error(
            args.message,
            title=args.title,
            file=args.file,
            line=args.line,
            end_line=args.end_line,
            col=args.col,
            end_column=args.end_column,
        )
    elif args.cmd == "debug":
        debug(args.message)
    elif args.cmd == "get-input":
        print(get_input(args.name, required=bool(args.required), default=args.default))
    elif args.cmd == "get-multiline-input":
        for line in get_multiline_input(args.name, required=bool(args.required)):
            print(line)
    elif args.cmd == "get-boolean-input":
        print(get_boolean_input(args.name, required=bool(args.required)))
    elif args.cmd == "set-output":
        key, sep, val = args.pair.partition("=")
        if not sep:
            print("set-output requires key=value", file=sys.stderr)
            return 2
        set_output(key, val)
    elif args.cmd == "export":
        key, sep, val = args.pair.partition("=")
        if not sep:
            print("export requires key=value", file=sys.stderr)
            return 2
        export_variable(key, val)
    elif args.cmd == "mask":
        set_secret(args.secret)
    elif args.cmd == "summary":
        append_summary(Path(args.path).read_text(encoding="utf-8"))
    elif args.cmd == "group":
        with group(args.name):
            for line in sys.stdin:
                sys.stdout.write(line)
            sys.stdout.flush()
    elif args.cmd == "is-debug":
        return 0 if is_debug() else 1
    elif args.cmd == "stop-commands":
        stop_commands(args.token)
    elif args.cmd == "resume-commands":
        resume_commands(args.token)
    elif args.cmd == "echo":
        set_command_echo(args.state == "on")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
