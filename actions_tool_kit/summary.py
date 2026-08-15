from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    pass


class SummaryBuilder:
    """Fluent builder for GitHub Actions step summary markdown.

    Mirrors the JS toolkit's ``@actions/core`` summary API. Each ``add_*``
    method appends content and returns ``self`` for chaining. Call
    :meth:`write` to flush the accumulated markdown to the step summary file.

    Example::

        SummaryBuilder()
            .add_heading("Deploy Report")
            .add_table(
                headers=["Service", "Status"],
                rows=[["api", ":white_check_mark:"], ["worker", ":x:"]],
            )
            .add_code_block("kubectl rollout status deploy/api", lang="sh")
            .write()
    """

    def __init__(self) -> None:
        self._parts: List[str] = []

    # ------------------------------------------------------------------
    # Content methods
    # ------------------------------------------------------------------

    def add_heading(self, text: str, level: int = 1) -> "SummaryBuilder":
        """Append a markdown heading.

        Args:
            text: Heading text.
            level: Heading level 1–6.
        """
        if not 1 <= level <= 6:
            raise ValueError(f"Heading level must be 1–6, got {level}")
        self._parts.append(f"{'#' * level} {text}\n\n")
        return self

    def add_paragraph(self, text: str) -> "SummaryBuilder":
        """Append a paragraph of text."""
        self._parts.append(f"{text}\n\n")
        return self

    def add_code_block(self, code: str, lang: str = "") -> "SummaryBuilder":
        """Append a fenced code block.

        Args:
            code: Code content.
            lang: Optional language hint for syntax highlighting (e.g. ``"python"``).
        """
        self._parts.append(f"```{lang}\n{code}\n```\n\n")
        return self

    def add_table(
        self,
        headers: List[str],
        rows: List[List[str]],
    ) -> "SummaryBuilder":
        """Append a GFM table.

        Args:
            headers: Column header labels.
            rows: Rows of cell strings; each row must have len == len(headers).
        """
        header_row = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join("---" for _ in headers) + " |"
        data_rows = "\n".join(
            "| " + " | ".join(str(cell) for cell in row) + " |" for row in rows
        )
        self._parts.append(f"{header_row}\n{separator}\n{data_rows}\n\n")
        return self

    def add_list(
        self,
        items: List[str],
        *,
        ordered: bool = False,
    ) -> "SummaryBuilder":
        """Append a bullet or numbered list.

        Args:
            items: List items.
            ordered: If True, emit a numbered list; otherwise bullets.
        """
        lines = [
            f"{i}. {item}" if ordered else f"- {item}"
            for i, item in enumerate(items, 1)
        ]
        self._parts.append("\n".join(lines) + "\n\n")
        return self

    def add_separator(self) -> "SummaryBuilder":
        """Append a horizontal rule."""
        self._parts.append("---\n\n")
        return self

    def add_raw(self, text: str) -> "SummaryBuilder":
        """Append raw markdown text without modification."""
        self._parts.append(text)
        return self

    def add_link(self, label: str, url: str) -> "SummaryBuilder":
        """Append a markdown hyperlink paragraph."""
        self._parts.append(f"[{label}]({url})\n\n")
        return self

    def add_image(
        self,
        src: str,
        alt: str = "",
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "SummaryBuilder":
        """Append an HTML image tag (supports optional width/height).

        Args:
            src: Image URL.
            alt: Alt text.
            width: Optional display width in pixels.
            height: Optional display height in pixels.
        """
        attrs = f'src="{src}" alt="{alt}"'
        if width is not None:
            attrs += f' width="{width}"'
        if height is not None:
            attrs += f' height="{height}"'
        self._parts.append(f"<img {attrs}/>\n\n")
        return self

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def build(self) -> str:
        """Return the accumulated markdown as a single string."""
        return "".join(self._parts)

    def write(self) -> "SummaryBuilder":
        """Append the accumulated markdown to the step summary file and return self."""
        from .actions_core import append_summary

        append_summary(self.build())
        return self

    def clear(self) -> "SummaryBuilder":
        """Discard all accumulated content."""
        self._parts.clear()
        return self

    def __len__(self) -> int:
        return len(self.build())

    def __bool__(self) -> bool:
        return bool(self._parts)


__all__ = ["SummaryBuilder"]
