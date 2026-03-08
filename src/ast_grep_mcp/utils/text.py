"""Text processing and string manipulation utilities.

This module provides utilities for normalizing code, calculating similarity,
and other text processing operations.
"""

import difflib

__all__ = [
    "normalize_code",
    "calculate_similarity",
    "clean_template_whitespace",
    "_clean_template_whitespace",
    "indent_lines",
    "read_file_lines",
    "write_file_lines",
]


def normalize_code(code: str, language: str | None = None) -> str:
    """Normalize code for comparison by removing whitespace and comments.

    Args:
        code: Code string to normalize
        language: Optional language hint (for future language-specific normalization)

    Returns:
        Normalized code string
    """
    lines = []
    for line in code.split("\n"):
        # Remove leading/trailing whitespace
        stripped = line.strip()
        # Skip empty lines and simple comments
        if stripped and not stripped.startswith("#") and not stripped.startswith("//"):
            lines.append(stripped)
    return "\n".join(lines)


def calculate_similarity(code1: str, code2: str, language: str | None = None) -> float:
    """Calculate similarity ratio between two code snippets.

    Uses SequenceMatcher for structural similarity comparison.

    Args:
        code1: First code snippet
        code2: Second code snippet
        language: Optional language hint (for future language-specific comparison)

    Returns:
        Similarity ratio between 0 and 1
    """
    if not code1 or not code2:
        return 0.0

    # Normalize code for comparison
    norm1 = normalize_code(code1, language)
    norm2 = normalize_code(code2, language)

    # Use difflib SequenceMatcher for similarity
    matcher = difflib.SequenceMatcher(None, norm1, norm2)
    return matcher.ratio()


def _trim_surrounding_blanks(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def clean_template_whitespace(template: str) -> str:
    """Clean and normalize whitespace in code templates.

    Removes excessive blank lines, normalizes indentation, and trims
    trailing whitespace while preserving code structure.

    Args:
        template: Code template string to clean

    Returns:
        Cleaned template with normalized whitespace
    """
    if not template:
        return ""
    lines = [line.rstrip() for line in template.split("\n")]
    lines = _trim_surrounding_blanks(lines)
    return "\n".join(_collapse_blank_lines(lines))


def _collapse_blank_lines(lines: list[str]) -> list[str]:
    result: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and not prev_blank:
            result.append("")
        elif not is_blank:
            result.append(line)
        prev_blank = is_blank
    return result


def indent_lines(text: str, prefix: str = "    ") -> list[str]:
    """Indent non-empty lines with the given prefix, leave blank lines empty.

    Args:
        text: Text to indent
        prefix: Indentation prefix (default 4 spaces)

    Returns:
        List of indented lines
    """
    return [f"{prefix}{line}" if line.strip() else "" for line in text.split("\n")]


def read_file_lines(file_path: str) -> list[str]:
    """Read a file and return its lines (including newlines).

    Args:
        file_path: Path to the file

    Returns:
        List of lines with trailing newlines preserved
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.readlines()


def write_file_lines(file_path: str, lines: list[str]) -> None:
    """Write lines to a file.

    Args:
        file_path: Path to the file
        lines: Lines to write (should include trailing newlines)
    """
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


# Alias for backward compatibility
_clean_template_whitespace = clean_template_whitespace
