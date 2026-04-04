"""Shared plain-text rendering for chat channels."""

from __future__ import annotations

import re

_TABLE_RE = re.compile(
    r"((?:^[ \t]*\|.+\|[ \t]*\n)(?:^[ \t]*\|[-:\s|]+\|[ \t]*\n)(?:^[ \t]*\|.+\|[ \t]*\n?)+)",
    re.MULTILINE,
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_BOLD2_RE = re.compile(r"__(.+?)__")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_STRIKE_RE = re.compile(r"~~(.+?)~~")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_INLINE_LATEX_RE = re.compile(r"\$(.+?)\$")

_LATEX_REPLACEMENTS = (
    (r"\sqrt", "sqrt"),
    (r"\times", " x "),
    (r"\cdot", " * "),
    (r"\leq", "<="),
    (r"\geq", ">="),
    (r"\neq", "!="),
    (r"\approx", "~"),
    (r"\pm", "+/-"),
)


def _strip_markdown(text: str) -> str:
    text = _BOLD_RE.sub(r"\1", text)
    text = _BOLD2_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    text = _STRIKE_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _INLINE_LATEX_RE.sub(r"\1", text)
    for source, target in _LATEX_REPLACEMENTS:
        text = text.replace(source, target)
    return text


def _render_table(table_text: str) -> str:
    lines = [line.strip() for line in table_text.strip().splitlines() if line.strip()]
    if len(lines) < 3:
        return _strip_markdown(table_text.strip())

    def split_row(line: str) -> list[str]:
        return [_strip_markdown(cell.strip()) for cell in line.strip("|").split("|")]

    rows = [split_row(line) for line in lines if not re.fullmatch(r"\|?[-:\s|]+\|?", line)]
    if not rows:
        return _strip_markdown(table_text.strip())

    column_count = max(len(row) for row in rows)
    widths = [0] * column_count
    for row in rows:
        for index in range(column_count):
            cell = row[index] if index < len(row) else ""
            widths[index] = max(widths[index], len(cell))

    formatted: list[str] = []
    for row_index, row in enumerate(rows):
        padded = [
            (row[index] if index < len(row) else "").ljust(widths[index])
            for index in range(column_count)
        ]
        formatted.append(" | ".join(padded).rstrip())
        if row_index == 0:
            formatted.append("-+-".join("-" * width for width in widths))
    return "\n".join(formatted)


def render_plain_reply(content: str) -> str:
    """Convert markdown-heavy model output into cleaner plain text."""
    rendered: list[str] = []
    last_end = 0
    for match in _TABLE_RE.finditer(content or ""):
        before = (content or "")[last_end:match.start()]
        if before:
            rendered.append(_strip_markdown(before))
        rendered.append(_render_table(match.group(1)))
        last_end = match.end()
    rendered.append(_strip_markdown((content or "")[last_end:]))
    merged = "".join(rendered).strip()
    merged = _HEADING_RE.sub(lambda m: f"[{_strip_markdown(m.group(2).strip())}]", merged)
    return re.sub(r"\n{3,}", "\n\n", merged)
