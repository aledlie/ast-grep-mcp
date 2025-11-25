"""Code formatting utilities for display and output.

This module provides formatting functions for matches, diffs, complexity
visualization, and before/after code examples, plus language-specific code formatters.
"""

import os
import re
import difflib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class FileDiff:
    """Represents a diff for a single file.

    Attributes:
        file_path: Absolute path to the file
        original_content: Original file content
        new_content: New content after changes
        unified_diff: Raw unified diff string
        formatted_diff: Human-readable formatted diff with colors/context
        hunks: List of individual diff hunks
        additions: Number of lines added
        deletions: Number of lines deleted
    """
    file_path: str
    original_content: str
    new_content: str
    unified_diff: str
    formatted_diff: str
    hunks: List[Dict[str, Any]]
    additions: int
    deletions: int


@dataclass
class DiffPreview:
    """Container for multi-file diff preview.

    Attributes:
        file_diffs: List of FileDiff objects for each modified file
        total_files: Number of files with changes
        total_additions: Total lines added across all files
        total_deletions: Total lines deleted across all files
        combined_diff: Single string with all diffs combined
        summary: Human-readable summary of changes
    """
    file_diffs: List[FileDiff]
    total_files: int
    total_additions: int
    total_deletions: int
    combined_diff: str
    summary: str


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


def generate_file_diff(
    file_path: str,
    original_content: str,
    new_content: str,
    context_lines: int = 3
) -> FileDiff:
    """Generate a unified diff for a single file.

    Args:
        file_path: Path to the file (used in diff header)
        original_content: Original file content
        new_content: New content after changes
        context_lines: Number of context lines before/after changes (default 3)

    Returns:
        FileDiff object with raw and formatted diffs
    """
    # Split content into lines
    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    # Ensure lines end with newline for proper diff format
    if original_lines and not original_lines[-1].endswith('\n'):
        original_lines[-1] += '\n'
    if new_lines and not new_lines[-1].endswith('\n'):
        new_lines[-1] += '\n'

    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{os.path.basename(file_path)}",
        tofile=f"b/{os.path.basename(file_path)}",
        lineterm='',
        n=context_lines
    ))

    unified_diff = ''.join(diff_lines)

    # Parse hunks and count additions/deletions
    hunks: List[Dict[str, Any]] = []
    additions = 0
    deletions = 0
    current_hunk: Optional[Dict[str, Any]] = None

    for line in diff_lines:
        if line.startswith('@@'):
            # Parse hunk header: @@ -start,count +start,count @@
            if current_hunk:
                hunks.append(current_hunk)

            # Extract line numbers from hunk header
            match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                current_hunk = {
                    'header': line,
                    'old_start': int(match.group(1)),
                    'old_count': int(match.group(2)) if match.group(2) else 1,
                    'new_start': int(match.group(3)),
                    'new_count': int(match.group(4)) if match.group(4) else 1,
                    'lines': []
                }
            else:
                current_hunk = {
                    'header': line,
                    'lines': []
                }
        elif current_hunk is not None:
            current_hunk['lines'].append(line)
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1

    if current_hunk:
        hunks.append(current_hunk)

    # Generate formatted diff with line numbers
    formatted_diff = _format_diff_with_line_numbers(
        file_path, diff_lines, original_lines, new_lines
    )

    return FileDiff(
        file_path=file_path,
        original_content=original_content,
        new_content=new_content,
        unified_diff=unified_diff,
        formatted_diff=formatted_diff,
        hunks=hunks,
        additions=additions,
        deletions=deletions
    )


def _format_diff_with_line_numbers(
    file_path: str,
    diff_lines: List[str],
    original_lines: List[str],
    new_lines: List[str]
) -> str:
    """Format diff with line numbers for readability.

    Args:
        file_path: Path to the file
        diff_lines: Raw diff lines from unified_diff
        original_lines: Original file lines
        new_lines: New file lines

    Returns:
        Formatted diff string with line numbers and visual indicators
    """
    if not diff_lines:
        return f"No changes in {file_path}"

    output = []
    output.append(f"{'=' * 70}")
    output.append(f"File: {file_path}")
    output.append(f"{'=' * 70}")

    old_line_num = 0
    new_line_num = 0

    for line in diff_lines:
        if line.startswith('---'):
            output.append(f"--- {file_path} (original)")
        elif line.startswith('+++'):
            output.append(f"+++ {file_path} (modified)")
        elif line.startswith('@@'):
            # Parse hunk header for line numbers
            match = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)', line)
            if match:
                old_line_num = int(match.group(1)) - 1
                new_line_num = int(match.group(2)) - 1
                context = match.group(3).strip()
                output.append(f"\n{line.strip()}")
                if context:
                    output.append(f"  Context: {context}")
            else:
                output.append(f"\n{line.strip()}")
        elif line.startswith('-'):
            old_line_num += 1
            output.append(f"{old_line_num:4d}      - {line[1:].rstrip()}")
        elif line.startswith('+'):
            new_line_num += 1
            output.append(f"     {new_line_num:4d} + {line[1:].rstrip()}")
        else:
            # Context line
            old_line_num += 1
            new_line_num += 1
            output.append(f"{old_line_num:4d} {new_line_num:4d}   {line.rstrip()}")

    output.append(f"\n{'=' * 70}\n")

    return '\n'.join(output)


def generate_multi_file_diff(
    file_changes: List[Dict[str, str]],
    context_lines: int = 3
) -> DiffPreview:
    """Generate combined diff preview for multiple file changes.

    Args:
        file_changes: List of dicts with keys:
            - 'file_path': Absolute path to file
            - 'original_content': Original file content
            - 'new_content': New content after changes
        context_lines: Number of context lines (default 3)

    Returns:
        DiffPreview with all file diffs combined
    """
    file_diffs = []
    total_additions = 0
    total_deletions = 0

    for change in file_changes:
        file_diff = generate_file_diff(
            file_path=change['file_path'],
            original_content=change['original_content'],
            new_content=change['new_content'],
            context_lines=context_lines
        )
        file_diffs.append(file_diff)
        total_additions += file_diff.additions
        total_deletions += file_diff.deletions

    # Combine all formatted diffs
    combined_parts = []
    for fd in file_diffs:
        combined_parts.append(fd.formatted_diff)

    combined_diff = '\n'.join(combined_parts)

    # Generate summary
    files_with_changes = [fd for fd in file_diffs if fd.additions > 0 or fd.deletions > 0]
    summary_lines = [
        "Diff Preview Summary",
        "-" * 40,
        f"Files modified: {len(files_with_changes)}",
        f"Total additions: +{total_additions}",
        f"Total deletions: -{total_deletions}",
        "-" * 40,
    ]

    for fd in files_with_changes:
        summary_lines.append(
            f"  {os.path.basename(fd.file_path)}: +{fd.additions}/-{fd.deletions}"
        )

    summary = '\n'.join(summary_lines)

    return DiffPreview(
        file_diffs=file_diffs,
        total_files=len(files_with_changes),
        total_additions=total_additions,
        total_deletions=total_deletions,
        combined_diff=combined_diff,
        summary=summary
    )


# ============================================================================
# Code Formatting Functions
# ============================================================================

def format_python_code(code: str, line_length: int = 88) -> str:
    """Format Python code using Black-style formatting.

    Attempts to use the 'black' library if available, otherwise falls back
    to basic Python formatting.

    Args:
        code: Python code to format
        line_length: Maximum line length (default: 88, Black's default)

    Returns:
        Formatted Python code
    """
    try:
        import black

        # Use Black's formatting
        mode = black.Mode(
            target_versions=set(),
            line_length=line_length,
            string_normalization=True,
            is_pyi=False,
        )

        try:
            formatted = black.format_str(code, mode=mode)
            return formatted
        except Exception:
            # Black formatting failed, fall back to basic formatting
            return _basic_python_format(code, line_length)

    except ImportError:
        # Black not available, use basic formatting
        return _basic_python_format(code, line_length)


def _basic_python_format(code: str, line_length: int = 88) -> str:
    """Basic Python formatting when Black is not available.

    Provides simple formatting improvements:
    - Sorts and separates imports
    - Adds spaces around operators
    - Normalizes whitespace
    - Ensures trailing newline

    Args:
        code: Python code to format
        line_length: Maximum line length hint (not strictly enforced)

    Returns:
        Formatted Python code
    """
    if not code.strip():
        return "\n"

    lines = code.split('\n')
    formatted_lines = []
    import_lines = []
    from_import_lines = []
    in_imports = True

    for line in lines:
        stripped = line.strip()

        # Handle imports
        if stripped.startswith('import ') and in_imports:
            # Split multi-imports like "import os, sys"
            if ',' in stripped:
                parts = stripped.replace('import ', '').split(',')
                for part in parts:
                    import_lines.append(f'import {part.strip()}')
            else:
                import_lines.append(stripped)
            continue

        elif stripped.startswith('from ') and in_imports:
            from_import_lines.append(stripped)
            continue

        elif stripped and in_imports:
            # End of import section
            in_imports = False

            # Add sorted imports
            if import_lines or from_import_lines:
                formatted_lines.extend(sorted(import_lines))
                if import_lines and from_import_lines:
                    formatted_lines.append('')  # Blank line between import types
                formatted_lines.extend(sorted(from_import_lines))
                formatted_lines.append('')  # Blank line after imports

        # Format the line
        if not in_imports:
            formatted_lines.append(_format_python_line(line))

    # Handle case where file is only imports
    if in_imports and (import_lines or from_import_lines):
        formatted_lines.extend(sorted(import_lines))
        if import_lines and from_import_lines:
            formatted_lines.append('')
        formatted_lines.extend(sorted(from_import_lines))

    result = '\n'.join(formatted_lines)

    # Ensure trailing newline
    if not result.endswith('\n'):
        result += '\n'

    return result


def _format_python_line(line: str) -> str:
    """Format a single Python line with basic improvements.

    Args:
        line: Single line of Python code

    Returns:
        Formatted line
    """
    if not line.strip():
        return ''

    # Preserve indentation
    stripped = line.lstrip()
    indent = line[:len(line) - len(stripped)]

    # Add spaces around operators (simple approach)
    # This is a very basic implementation - Black does this much better
    formatted = stripped

    # Handle common operators
    operators = ['=', '+', '-', '*', '/', '<', '>', '==', '!=', '<=', '>=']
    for op in operators:
        # Skip if operator is in a string
        if f'"{op}"' in formatted or f"'{op}'" in formatted:
            continue

        # Add spaces around operator if not already present
        pattern = rf'(\S){re.escape(op)}(\S)'
        formatted = re.sub(pattern, rf'\1 {op} \2', formatted)

    # Normalize multiple spaces to single space (except at start of line)
    formatted = re.sub(r'  +', ' ', formatted)

    return indent + formatted


def format_typescript_code(code: str, line_length: int = 80) -> str:
    """Format TypeScript code using Prettier if available.

    Args:
        code: TypeScript code to format
        line_length: Maximum line length (default: 80)

    Returns:
        Formatted TypeScript code
    """
    prettier_path = shutil.which('prettier')

    if prettier_path:
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run prettier
                result = subprocess.run(
                    [
                        prettier_path,
                        '--parser', 'typescript',
                        '--print-width', str(line_length),
                        '--single-quote',
                        '--trailing-comma', 'es5',
                        '--arrow-parens', 'always',
                        temp_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    return result.stdout
                else:
                    # Prettier failed, use fallback
                    return _basic_typescript_format(code)

            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except (subprocess.TimeoutExpired, Exception):
            # Prettier execution failed
            return _basic_typescript_format(code)

    else:
        # Prettier not available
        return _basic_typescript_format(code)


def format_javascript_code(code: str, line_length: int = 80) -> str:
    """Format JavaScript code using Prettier if available.

    Args:
        code: JavaScript code to format
        line_length: Maximum line length (default: 80)

    Returns:
        Formatted JavaScript code
    """
    prettier_path = shutil.which('prettier')

    if prettier_path:
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run prettier with babel parser for JavaScript
                result = subprocess.run(
                    [
                        prettier_path,
                        '--parser', 'babel',
                        '--print-width', str(line_length),
                        '--single-quote',
                        '--trailing-comma', 'es5',
                        '--arrow-parens', 'always',
                        temp_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    return result.stdout
                else:
                    return _basic_javascript_format(code)

            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except (subprocess.TimeoutExpired, Exception):
            return _basic_javascript_format(code)

    else:
        return _basic_javascript_format(code)


def _basic_typescript_format(code: str) -> str:
    """Basic TypeScript formatting fallback.

    Args:
        code: TypeScript code to format

    Returns:
        Formatted code with basic improvements
    """
    if not code.strip():
        return code

    lines = code.split('\n')
    formatted_lines = []

    for line in lines:
        # Preserve indentation
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]

        # Basic formatting
        formatted = stripped

        # Add semicolons if missing (simple heuristic)
        if formatted and not formatted.endswith((';', '{', '}', ',')):
            if any(keyword in formatted for keyword in ['const ', 'let ', 'var ', 'return ']):
                formatted += ';'

        formatted_lines.append(indent + formatted if formatted else '')

    result = '\n'.join(formatted_lines)

    if not result.endswith('\n'):
        result += '\n'

    return result


def _basic_javascript_format(code: str) -> str:
    """Basic JavaScript formatting fallback.

    Args:
        code: JavaScript code to format

    Returns:
        Formatted code with basic improvements
    """
    # JavaScript and TypeScript basic formatting is the same
    return _basic_typescript_format(code)


def format_java_code(code: str) -> str:
    """Format Java code using google-java-format if available.

    Args:
        code: Java code to format

    Returns:
        Formatted Java code
    """
    # Check for google-java-format
    formatter_path = shutil.which('google-java-format')

    if formatter_path:
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run google-java-format
                result = subprocess.run(
                    [formatter_path, '--replace', temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                # Read formatted code
                with open(temp_path, 'r') as f:
                    formatted = f.read()

                return formatted

            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except (subprocess.TimeoutExpired, Exception):
            return _basic_java_format(code)

    else:
        return _basic_java_format(code)


def _basic_java_format(code: str) -> str:
    """Basic Java formatting fallback.

    Args:
        code: Java code to format

    Returns:
        Formatted code with basic improvements
    """
    if not code.strip():
        return code

    lines = code.split('\n')
    formatted_lines = []

    for line in lines:
        # Preserve indentation
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]

        # Basic formatting
        formatted = stripped

        # Ensure proper spacing around braces
        formatted = formatted.replace('){', ') {')
        formatted = formatted.replace('}{', '} {')

        formatted_lines.append(indent + formatted if formatted else '')

    result = '\n'.join(formatted_lines)

    if not result.endswith('\n'):
        result += '\n'

    return result


def format_generated_code(code: str, language: str, line_length: int = 88) -> str:
    """Format generated code based on language.

    Dispatcher function that routes to language-specific formatters.

    Args:
        code: Code to format
        language: Programming language (python, typescript, javascript, java)
        line_length: Maximum line length

    Returns:
        Formatted code

    Raises:
        ValueError: If language is not supported
    """
    language = language.lower()

    if language == 'python':
        return format_python_code(code, line_length)
    elif language == 'typescript':
        return format_typescript_code(code, line_length)
    elif language == 'javascript':
        return format_javascript_code(code, line_length)
    elif language == 'java':
        return format_java_code(code)
    else:
        # Unknown language, return as-is
        return code