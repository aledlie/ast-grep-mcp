"""Code formatting utilities for display and output.

This module provides formatting functions for matches, diffs, complexity
visualization, and before/after code examples.
"""

from typing import List, Dict, Any, Optional, Tuple


def format_matches_as_text(matches: List[Dict[str, Any]]) -> str:
    """Convert JSON matches to LLM-friendly text format.

    Format: file:start-end followed by the complete match text.
    Matches are separated by blank lines for clarity.

    Args:
        matches: List of match dictionaries from ast-grep JSON output

    Returns:
        Formatted text string
    """
    if not matches:
        return ""

    output_blocks: List[str] = []
    for m in matches:
        file_path = m.get('file', '')
        start_line = m.get('range', {}).get('start', {}).get('line', 0) + 1
        end_line = m.get('range', {}).get('end', {}).get('line', 0) + 1
        match_text = m.get('text', '').rstrip()

        # Format: filepath:start-end (or just :line for single-line matches)
        if start_line == end_line:
            header = f"{file_path}:{start_line}"
        else:
            header = f"{file_path}:{start_line}-{end_line}"

        output_blocks.append(f"{header}\n{match_text}")

    return '\n\n'.join(output_blocks)


def format_diff_with_colors(diff: str) -> str:
    """Add ANSI color codes to a unified diff for CLI display.

    Args:
        diff: Unified diff string

    Returns:
        Diff string with ANSI color codes:
        - Green for additions (+)
        - Red for deletions (-)
        - Cyan for hunk headers (@@)
        - Yellow for file headers (--- / +++)
    """
    if not diff:
        return diff

    # ANSI color codes
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    colored_lines = []
    for line in diff.split('\n'):
        if line.startswith('+++') or line.startswith('---'):
            colored_lines.append(f"{YELLOW}{line}{RESET}")
        elif line.startswith('@@'):
            colored_lines.append(f"{CYAN}{line}{RESET}")
        elif line.startswith('+'):
            colored_lines.append(f"{GREEN}{line}{RESET}")
        elif line.startswith('-'):
            colored_lines.append(f"{RED}{line}{RESET}")
        else:
            colored_lines.append(line)

    return '\n'.join(colored_lines)


def generate_before_after_example(
    original_code: str,
    replacement_code: str,
    function_name: str
) -> Dict[str, Any]:
    """Generate before/after code examples for a duplication extraction.

    Creates readable code snippets showing the original duplicate code
    and how it looks after extraction into a reusable function.

    Args:
        original_code: The original duplicate code snippet
        replacement_code: The replacement code (function call)
        function_name: Name of the extracted function

    Returns:
        Dictionary containing:
        - before: Original code snippet with context
        - after: Code with extracted function call
        - function_definition: The extracted function's signature
        - explanation: Human-readable explanation of the change
    """
    # Clean up the code snippets
    original_lines = original_code.strip().split('\n')
    replacement_lines = replacement_code.strip().split('\n')

    # Calculate metrics
    original_line_count = len(original_lines)
    replacement_line_count = len(replacement_lines)
    lines_saved = original_line_count - replacement_line_count

    # Format the before section with line numbers
    before_formatted = []
    for i, line in enumerate(original_lines, 1):
        before_formatted.append(f"{i:3d} | {line}")

    # Format the after section with line numbers
    after_formatted = []
    for i, line in enumerate(replacement_lines, 1):
        after_formatted.append(f"{i:3d} | {line}")

    # Generate a simple function signature based on name
    function_definition = f"def {function_name}(...):"

    # Create explanation
    if lines_saved > 0:
        explanation = (
            f"Extracted {original_line_count} lines of duplicate code into "
            f"'{function_name}', reducing to {replacement_line_count} line(s). "
            f"This saves {lines_saved} line(s) per occurrence."
        )
    else:
        explanation = (
            f"Refactored code into '{function_name}' for better reusability "
            f"and maintainability."
        )

    return {
        "before": '\n'.join(before_formatted),
        "after": '\n'.join(after_formatted),
        "before_raw": original_code.strip(),
        "after_raw": replacement_code.strip(),
        "function_definition": function_definition,
        "function_name": function_name,
        "original_lines": original_line_count,
        "replacement_lines": replacement_line_count,
        "lines_saved": lines_saved,
        "explanation": explanation
    }


def visualize_complexity(score: int) -> Dict[str, Any]:
    """Create a visual complexity indicator with recommendations.

    Args:
        score: Complexity score from 1-10

    Returns:
        Dictionary containing:
        - bar: ASCII bar visualization
        - description: Text description (Low/Medium/High)
        - color_code: ANSI color code for CLI
        - recommendations: List of actionable recommendations
        - score: The input score
    """
    # Clamp score to valid range
    score = max(1, min(10, score))

    # Determine description and color based on score
    if score <= 3:
        description = "Low"
        color_code = "\033[32m"  # Green
        recommendations = [
            "Good candidate for quick refactoring",
            "Consider extracting as a simple helper function",
            "Low risk of introducing bugs during extraction"
        ]
    elif score <= 6:
        description = "Medium"
        color_code = "\033[33m"  # Yellow
        recommendations = [
            "Review the code carefully before extraction",
            "Consider adding unit tests before refactoring",
            "May benefit from breaking into smaller pieces",
            "Check for hidden dependencies or side effects"
        ]
    else:
        description = "High"
        color_code = "\033[31m"  # Red
        recommendations = [
            "High complexity - proceed with caution",
            "Strongly recommend comprehensive test coverage first",
            "Consider incremental refactoring in smaller steps",
            "Review for cyclomatic complexity and reduce branches",
            "May need architectural review before extraction"
        ]

    reset_code = "\033[0m"

    # Create ASCII bar visualization
    filled = score
    empty = 10 - score
    bar_plain = f"[{'=' * filled}{' ' * empty}] {score}/10"
    bar_colored = f"{color_code}[{'=' * filled}{' ' * empty}]{reset_code} {score}/10"

    return {
        "score": score,
        "bar": bar_plain,
        "bar_colored": bar_colored,
        "description": description,
        "color_code": color_code,
        "recommendations": recommendations,
        "formatted": f"{description} Complexity ({score}/10): {bar_plain}"
    }