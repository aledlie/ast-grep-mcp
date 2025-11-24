"""Text processing and string manipulation utilities.

This module provides utilities for normalizing code, calculating similarity,
and other text processing operations.
"""

import difflib
from typing import Optional


def normalize_code(code: str) -> str:
    """Normalize code for comparison by removing whitespace and comments.

    Args:
        code: Code string to normalize

    Returns:
        Normalized code string
    """
    lines = []
    for line in code.split('\n'):
        # Remove leading/trailing whitespace
        stripped = line.strip()
        # Skip empty lines and simple comments
        if stripped and not stripped.startswith('#') and not stripped.startswith('//'):
            lines.append(stripped)
    return '\n'.join(lines)


def calculate_similarity(code1: str, code2: str) -> float:
    """Calculate similarity ratio between two code snippets.

    Uses SequenceMatcher for structural similarity comparison.

    Args:
        code1: First code snippet
        code2: Second code snippet

    Returns:
        Similarity ratio between 0 and 1
    """
    if not code1 or not code2:
        return 0.0

    # Normalize code for comparison
    norm1 = normalize_code(code1)
    norm2 = normalize_code(code2)

    # Use difflib SequenceMatcher for similarity
    matcher = difflib.SequenceMatcher(None, norm1, norm2)
    return matcher.ratio()