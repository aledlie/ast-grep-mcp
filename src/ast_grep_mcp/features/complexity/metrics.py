"""
Code complexity metrics calculation.

This module provides functions for calculating various code complexity metrics:
- Cyclomatic complexity (McCabe)
- Cognitive complexity (SonarSource)
- Nesting depth
- Pattern-based complexity analysis

All metrics are calculated using ast-grep patterns and text-based analysis.
"""

import json
import re
import subprocess
from typing import Any, Dict

from ast_grep_mcp.core.logging import get_logger

# =============================================================================
# COMPLEXITY PATTERNS
# =============================================================================

COMPLEXITY_PATTERNS: Dict[str, Dict[str, Any]] = {
    "python": {
        "function": "def $NAME($$$)",
        "async_function": "async def $NAME($$$)",
        "branches": [
            "if $COND:",
            "elif $COND:",
            "for $VAR in $ITER:",
            "while $COND:",
            "except $TYPE:",
            "except:",
            "with $CTX:",
            "case $PATTERN:",
        ],
        "logical_operators": [
            "$A and $B",
            "$A or $B",
        ],
        "nesting_constructs": ["if", "for", "while", "with", "try", "match"],
    },
    "typescript": {
        "function": "function $NAME($$$) { $$$ }",
        "arrow_function": "const $NAME = ($$$) => { $$$ }",
        "method": "$NAME($$$) { $$$ }",
        "branches": [
            "if ($COND) { $$$ }",
            "for ($INIT; $COND; $INC) { $$$ }",
            "for ($VAR of $ITER) { $$$ }",
            "for ($VAR in $OBJ) { $$$ }",
            "while ($COND) { $$$ }",
            "switch ($EXPR) { $$$ }",
            "case $VAL:",
            "catch ($ERR) { $$$ }",
            "$COND ? $A : $B",
        ],
        "logical_operators": [
            "$A && $B",
            "$A || $B",
            "$A ?? $B",
        ],
        "nesting_constructs": ["if", "for", "while", "switch", "try"],
    },
    "javascript": {
        "function": "function $NAME($$$) { $$$ }",
        "arrow_function": "const $NAME = ($$$) => { $$$ }",
        "method": "$NAME($$$) { $$$ }",
        "branches": [
            "if ($COND) { $$$ }",
            "for ($INIT; $COND; $INC) { $$$ }",
            "for ($VAR of $ITER) { $$$ }",
            "for ($VAR in $OBJ) { $$$ }",
            "while ($COND) { $$$ }",
            "switch ($EXPR) { $$$ }",
            "case $VAL:",
            "catch ($ERR) { $$$ }",
            "$COND ? $A : $B",
        ],
        "logical_operators": [
            "$A && $B",
            "$A || $B",
            "$A ?? $B",
        ],
        "nesting_constructs": ["if", "for", "while", "switch", "try"],
    },
    "java": {
        "function": "$TYPE $NAME($$$) { $$$ }",
        "branches": [
            "if ($COND) { $$$ }",
            "for ($INIT; $COND; $INC) { $$$ }",
            "for ($TYPE $VAR : $ITER) { $$$ }",
            "while ($COND) { $$$ }",
            "switch ($EXPR) { $$$ }",
            "case $VAL:",
            "catch ($TYPE $VAR) { $$$ }",
            "$COND ? $A : $B",
        ],
        "logical_operators": [
            "$A && $B",
            "$A || $B",
        ],
        "nesting_constructs": ["if", "for", "while", "switch", "try"],
    },
}


def get_complexity_patterns(language: str) -> Dict[str, Any]:
    """Get AST patterns for a specific language.

    Args:
        language: Programming language name

    Returns:
        Dictionary of patterns for the language
    """
    lang_lower = language.lower()
    if lang_lower in COMPLEXITY_PATTERNS:
        return COMPLEXITY_PATTERNS[lang_lower]
    # Default to Python patterns
    return COMPLEXITY_PATTERNS["python"]


def count_pattern_matches(code: str, pattern: str, language: str) -> int:
    """Count occurrences of an AST pattern in code using ast-grep.

    Args:
        code: Source code to analyze
        pattern: ast-grep pattern to search for
        language: Programming language

    Returns:
        Number of matches found
    """
    try:
        result = subprocess.run(
            ["ast-grep", "run", "--pattern", pattern, "--lang", language, "--json"],
            input=code,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            matches = json.loads(result.stdout)
            return len(matches) if isinstance(matches, list) else 0
        return 0
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return 0


def calculate_cyclomatic_complexity(code: str, language: str) -> int:
    """Calculate McCabe cyclomatic complexity.

    Cyclomatic complexity = E - N + 2P
    Simplified: 1 + number of decision points

    Args:
        code: Function source code
        language: Programming language

    Returns:
        Cyclomatic complexity score (minimum 1)
    """
    complexity = 1  # Base complexity

    # Language-specific keywords that represent decision points
    if language.lower() == "python":
        # Count decision keywords
        keywords = ['if ', 'elif ', 'for ', 'while ', 'except ', 'except:', 'with ', 'case ']
        operators = [' and ', ' or ']
    elif language.lower() in ["typescript", "javascript"]:
        keywords = ['if ', 'if(', 'for ', 'for(', 'while ', 'while(', 'switch ', 'switch(', 'case ', 'catch ', 'catch(', '? ']
        operators = [' && ', ' || ', ' ?? ']
    elif language.lower() == "java":
        keywords = ['if ', 'if(', 'for ', 'for(', 'while ', 'while(', 'switch ', 'switch(', 'case ', 'catch ', 'catch(']
        operators = [' && ', ' || ']
    else:
        # Default to Python-style
        keywords = ['if ', 'elif ', 'for ', 'while ', 'except ', 'case ']
        operators = [' and ', ' or ']

    # Count keywords
    for keyword in keywords:
        complexity += code.count(keyword)

    # Count logical operators
    for op in operators:
        complexity += code.count(op)

    return complexity


def calculate_cognitive_complexity(code: str, language: str) -> int:
    """Calculate cognitive complexity with nesting penalties.

    Based on SonarSource cognitive complexity specification:
    - +1 for each control flow break (if, for, while, catch, switch, etc.)
    - +N nesting penalty when nested (N = current nesting level)
    - +1 for each sequence of logical operators (not each operator)
    - else doesn't increment, but else if does

    Args:
        code: Function source code
        language: Programming language

    Returns:
        Cognitive complexity score
    """
    patterns = get_complexity_patterns(language)
    complexity = 0

    lines = code.split('\n')
    base_indent = None

    # Keywords that add +1 AND increase nesting level
    structural_keywords = patterns.get("nesting_constructs", [])

    # Language-specific adjustments
    if language.lower() in ("python",):
        # Python: elif is separate, else doesn't count
        control_flow = ["if", "elif", "for", "while", "except", "with"]
        # else doesn't add complexity in Python
    elif language.lower() in ("typescript", "javascript"):
        # JS/TS: catch, switch add; else if handled specially
        control_flow = ["if", "for", "while", "catch", "switch", "do"]
    elif language.lower() == "java":
        control_flow = ["if", "for", "while", "catch", "switch", "do"]
    else:
        control_flow = structural_keywords

    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            continue

        # Skip comments
        if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Calculate current indentation for nesting level
        indent = len(line) - len(stripped)
        if base_indent is None and stripped:
            base_indent = indent

        # Estimate nesting level from indentation
        if base_indent is not None:
            indent_diff = indent - base_indent
            # Assume 4 spaces or 1 tab per level
            current_nesting = max(0, indent_diff // 4)
        else:
            current_nesting = 0

        # Check for control flow keywords
        keyword_found = False
        for keyword in control_flow:
            # Match keyword at start of line (after stripping)
            # Use word boundary to avoid matching 'format' when looking for 'for'
            pattern = rf'^{keyword}(?:\s|\(|:)'
            if re.match(pattern, stripped):
                # Handle else if / elif specially
                if keyword in ("elif",) or stripped.startswith("else if"):
                    # else if adds +1 but no nesting penalty (continues same branch)
                    complexity += 1
                else:
                    # Base increment + nesting penalty
                    complexity += 1
                    complexity += current_nesting
                keyword_found = True
                break

        # Handle 'else if' in C-style languages
        if not keyword_found and stripped.startswith("else if"):
            complexity += 1  # No nesting penalty for else if

        # Count logical operator sequences (not individual operators)
        # Each change from AND to OR or vice versa adds +1
        # "a && b && c" = +1, "a && b || c" = +2
        if language.lower() in ("python",):
            # Python uses 'and' and 'or'
            and_pattern = r'\band\b'
            or_pattern = r'\bor\b'
        else:
            # C-style uses && and ||
            and_pattern = r'&&'
            or_pattern = r'\|\|'

        and_matches = list(re.finditer(and_pattern, stripped))
        or_matches = list(re.finditer(or_pattern, stripped))

        if and_matches or or_matches:
            # Combine and sort by position
            all_ops = [(m.start(), 'and') for m in and_matches] + \
                      [(m.start(), 'or') for m in or_matches]
            all_ops.sort(key=lambda x: x[0])

            if all_ops:
                # Count sequences (changes in operator type)
                sequences = 1  # First sequence
                for i in range(1, len(all_ops)):
                    if all_ops[i][1] != all_ops[i-1][1]:
                        sequences += 1
                complexity += sequences

    return complexity


def calculate_nesting_depth(code: str, language: str) -> int:
    """Calculate maximum nesting depth.

    Args:
        code: Function source code
        language: Programming language

    Returns:
        Maximum nesting depth
    """
    lines = code.split('\n')
    max_depth = 0
    base_indent = None

    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            continue

        indent = len(line) - len(stripped)
        if base_indent is None:
            base_indent = indent
            continue

        # Calculate depth from indentation difference
        indent_diff = indent - base_indent
        depth = max(0, indent_diff // 4)  # Assume 4 spaces per level
        max_depth = max(max_depth, depth)

    return max_depth
