"""Diff utilities for code comparison and visualization.

This module provides utilities for building diff trees, formatting diffs,
and generating various diff representations for duplicate code analysis.
"""

import difflib
import re
from pathlib import Path
from typing import Any


def build_nested_diff_tree(code1: str, code2: str, language: str | None = None) -> dict[str, Any]:
    """Build a nested diff tree from two code snippets.

    Creates a hierarchical representation of differences between two code blocks,
    organizing changes by type (additions, deletions, modifications).

    Args:
        code1: First code snippet (original)
        code2: Second code snippet (modified)
        language: Optional language hint for language-specific parsing

    Returns:
        Nested dictionary containing:
        - nested_diff: The hierarchical diff structure
        - summary: Statistics about the changes
        - changes: List of individual changes with context
    """
    if not code1 and not code2:
        return {"nested_diff": {}, "summary": {"additions": 0, "deletions": 0, "modifications": 0}, "changes": []}

    lines1 = code1.splitlines(keepends=True) if code1 else []
    lines2 = code2.splitlines(keepends=True) if code2 else []

    differ = difflib.unified_diff(lines1, lines2, lineterm="")
    diff_lines = list(differ)

    # Parse unified diff into structured format
    additions = 0
    deletions = 0
    modifications = 0
    changes: list[dict[str, Any]] = []

    i = 0
    while i < len(diff_lines):
        line = diff_lines[i]

        if line.startswith("---") or line.startswith("+++"):
            i += 1
            continue

        if line.startswith("@@"):
            # Parse hunk header
            i += 1
            continue

        if line.startswith("-") and not line.startswith("---"):
            deletions += 1
            # Check if next line is an addition (modification)
            if i + 1 < len(diff_lines) and diff_lines[i + 1].startswith("+"):
                modifications += 1
                deletions -= 1
                changes.append({
                    "type": "modification",
                    "old": line[1:].rstrip("\n"),
                    "new": diff_lines[i + 1][1:].rstrip("\n"),
                })
                i += 2
                continue
            changes.append({"type": "deletion", "content": line[1:].rstrip("\n")})

        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
            changes.append({"type": "addition", "content": line[1:].rstrip("\n")})

        i += 1

    # Build nested structure
    nested_diff = {
        "root": {
            "type": "diff_root",
            "language": language,
            "children": [],
        }
    }

    # Group changes by type
    for change in changes:
        change_node = {
            "type": change["type"],
            "data": change,
        }
        nested_diff["root"]["children"].append(change_node)

    return {
        "nested_diff": nested_diff,
        "summary": {
            "additions": additions,
            "deletions": deletions,
            "modifications": modifications,
            "total_changes": additions + deletions + modifications,
        },
        "changes": changes,
    }


def build_diff_tree(code1: str, code2: str, language: str | None = None) -> dict[str, Any]:
    """Build a diff tree from two code snippets.

    Creates a simplified diff representation showing changes between two code blocks.

    Args:
        code1: First code snippet (original)
        code2: Second code snippet (modified)
        language: Optional language hint for language-specific parsing

    Returns:
        Dictionary containing diff information with keys:
        - diff: List of diff operations
        - language: The language hint if provided
        - summary: Statistics about changes
    """
    if not code1 and not code2:
        return {"diff": [], "language": language, "summary": {"changes": 0}}

    lines1 = code1.splitlines() if code1 else []
    lines2 = code2.splitlines() if code2 else []

    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    diff_ops: list[dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in lines1[i1:i2]:
                diff_ops.append({"type": "equal", "content": line})
        elif tag == "delete":
            for line in lines1[i1:i2]:
                diff_ops.append({"type": "delete", "content": line})
        elif tag == "insert":
            for line in lines2[j1:j2]:
                diff_ops.append({"type": "insert", "content": line})
        elif tag == "replace":
            for line in lines1[i1:i2]:
                diff_ops.append({"type": "delete", "content": line})
            for line in lines2[j1:j2]:
                diff_ops.append({"type": "insert", "content": line})

    change_count = sum(1 for op in diff_ops if op["type"] != "equal")

    return {
        "diff": diff_ops,
        "language": language,
        "summary": {"changes": change_count},
    }


def format_alignment_diff(diff_data: dict[str, Any]) -> str | dict[str, Any]:
    """Format alignment diff for display.

    Converts alignment diff data into a human-readable format.

    Args:
        diff_data: Dictionary containing alignment information with optional keys:
            - alignments: List of alignment entries (type, value, old, new)
            - diff: List of diff operations
            - changes: List of change entries

    Returns:
        Formatted string representation of the diff, or the original dict if
        no recognized format is found.
    """
    if not diff_data:
        return ""

    # Handle alignments format
    if "alignments" in diff_data:
        lines: list[str] = []
        for alignment in diff_data["alignments"]:
            align_type = alignment.get("type", "unknown")
            if align_type == "match":
                lines.append(f"  {alignment.get('value', '')}")
            elif align_type == "diff":
                old_val = alignment.get("old", "")
                new_val = alignment.get("new", "")
                if old_val:
                    lines.append(f"- {old_val}")
                if new_val:
                    lines.append(f"+ {new_val}")
            elif align_type == "delete":
                lines.append(f"- {alignment.get('value', alignment.get('content', ''))}")
            elif align_type == "insert":
                lines.append(f"+ {alignment.get('value', alignment.get('content', ''))}")
        return "\n".join(lines)

    # Handle diff operations format
    if "diff" in diff_data and isinstance(diff_data["diff"], list):
        lines = []
        for op in diff_data["diff"]:
            op_type = op.get("type", "equal")
            content = op.get("content", "")
            if op_type == "equal":
                lines.append(f"  {content}")
            elif op_type == "delete":
                lines.append(f"- {content}")
            elif op_type == "insert":
                lines.append(f"+ {content}")
        return "\n".join(lines)

    # Handle changes format
    if "changes" in diff_data and isinstance(diff_data["changes"], list):
        lines = []
        for change in diff_data["changes"]:
            change_type = change.get("type", "")
            if change_type == "modification":
                lines.append(f"- {change.get('old', '')}")
                lines.append(f"+ {change.get('new', '')}")
            elif change_type == "deletion":
                lines.append(f"- {change.get('content', '')}")
            elif change_type == "addition":
                lines.append(f"+ {change.get('content', '')}")
        return "\n".join(lines)

    # Return original if no recognized format
    return diff_data


def diff_preview_to_dict(diff_text: str) -> dict[str, Any]:
    """Convert unified diff text to a dictionary representation.

    Parses unified diff format and extracts structured information.

    Args:
        diff_text: Unified diff text string

    Returns:
        Dictionary containing:
        - hunks: List of parsed hunk dictionaries with line changes
        - files: Tuple of (old_file, new_file) names if present
        - raw: Original diff text
    """
    if not diff_text or not diff_text.strip():
        return {"hunks": [], "files": (None, None), "raw": diff_text}

    lines = diff_text.strip().split("\n")
    hunks: list[dict[str, Any]] = []
    current_hunk: dict[str, Any] | None = None
    old_file = None
    new_file = None

    hunk_header_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")

    for line in lines:
        # Parse file headers
        if line.startswith("--- "):
            old_file = line[4:].split("\t")[0]  # Remove timestamp if present
            if old_file.startswith("a/"):
                old_file = old_file[2:]
        elif line.startswith("+++ "):
            new_file = line[4:].split("\t")[0]
            if new_file.startswith("b/"):
                new_file = new_file[2:]
        # Parse hunk header
        elif line.startswith("@@"):
            match = hunk_header_pattern.match(line)
            if match:
                if current_hunk:
                    hunks.append(current_hunk)
                current_hunk = {
                    "old_start": int(match.group(1)),
                    "old_count": int(match.group(2)) if match.group(2) else 1,
                    "new_start": int(match.group(3)),
                    "new_count": int(match.group(4)) if match.group(4) else 1,
                    "context": match.group(5).strip(),
                    "changes": [],
                }
        # Parse diff lines
        elif current_hunk is not None:
            if line.startswith("-"):
                current_hunk["changes"].append({"type": "deletion", "content": line[1:]})
            elif line.startswith("+"):
                current_hunk["changes"].append({"type": "addition", "content": line[1:]})
            elif line.startswith(" "):
                current_hunk["changes"].append({"type": "context", "content": line[1:]})
            else:
                # No-newline marker or other
                current_hunk["changes"].append({"type": "other", "content": line})

    # Add final hunk
    if current_hunk:
        hunks.append(current_hunk)

    return {
        "hunks": hunks,
        "files": (old_file, new_file),
        "raw": diff_text,
    }


def generate_file_diff(old_content: str, new_content: str, filename: str) -> str:
    """Generate unified diff for a single file.

    Args:
        old_content: Original file content
        new_content: Modified file content
        filename: Name of the file for diff headers

    Returns:
        Unified diff string
    """
    old_lines = old_content.splitlines(keepends=True) if old_content else []
    new_lines = new_content.splitlines(keepends=True) if new_content else []

    # Ensure lines end with newlines for proper diff output
    if old_lines and not old_lines[-1].endswith("\n"):
        old_lines[-1] += "\n"
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


def generate_multi_file_diff(changes: list[dict[str, Any]]) -> str:
    """Generate unified diff for multiple files.

    Args:
        changes: List of change dictionaries, each containing:
            - file: Filename
            - old_content: Original content
            - new_content: Modified content

    Returns:
        Combined unified diff string for all files
    """
    diffs: list[str] = []
    for change in changes:
        filename = change.get("file", "unknown")
        old_content = change.get("old_content", "")
        new_content = change.get("new_content", "")
        diff = generate_file_diff(old_content, new_content, filename)
        if diff:
            diffs.append(diff)
    return "\n".join(diffs)


def generate_diff_from_file_paths(old_path: str, new_path: str) -> str:
    """Generate unified diff between two files by their paths.

    Args:
        old_path: Path to the original file
        new_path: Path to the modified file

    Returns:
        Unified diff string, or error message if files cannot be read
    """
    try:
        old_file = Path(old_path)
        new_file = Path(new_path)

        if not old_file.exists():
            return f"Error: File not found: {old_path}"
        if not new_file.exists():
            return f"Error: File not found: {new_path}"

        old_content = old_file.read_text(encoding="utf-8")
        new_content = new_file.read_text(encoding="utf-8")

        # Use the new file's name for the diff header
        filename = new_file.name
        return generate_file_diff(old_content, new_content, filename)

    except (OSError, UnicodeDecodeError) as e:
        return f"Error reading files: {e}"
