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

    # Split into lines
    lines = template.split("\n")

    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in lines]

    # Remove leading/trailing blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    # Collapse multiple consecutive blank lines into single blank line
    result_lines: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank:
            if not prev_blank:
                result_lines.append("")
            prev_blank = True
        else:
            result_lines.append(line)
            prev_blank = False

    return "\n".join(result_lines)


# Alias for backward compatibility
_clean_template_whitespace = clean_template_whitespace
