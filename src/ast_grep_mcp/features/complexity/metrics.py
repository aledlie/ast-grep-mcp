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
from typing import Any, Dict, List, Optional, Tuple

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


# =============================================================================
# COGNITIVE COMPLEXITY HELPER FUNCTIONS
# =============================================================================


def _get_control_flow_keywords(language: str, patterns: Dict[str, Any]) -> List[str]:
    """Get control flow keywords for a specific language.

    Args:
        language: Programming language name
        patterns: Language complexity patterns

    Returns:
        List of control flow keywords that add complexity
    """
    if language.lower() == "python":
        # Python: elif is separate, else doesn't count
        return ["if", "elif", "for", "while", "except", "with"]
    elif language.lower() in ("typescript", "javascript"):
        # JS/TS: catch, switch add; else if handled specially
        return ["if", "for", "while", "catch", "switch", "do"]
    elif language.lower() == "java":
        return ["if", "for", "while", "catch", "switch", "do"]
    else:
        # Default to nesting constructs from patterns (may be empty list)
        structural_keywords: List[str] = patterns.get("nesting_constructs", [])
        return structural_keywords


def _calculate_line_indentation(line: str, base_indent: Optional[int]) -> Tuple[int, Optional[int]]:
    """Calculate the nesting level from line indentation.

    Args:
        line: Source code line
        base_indent: Base indentation level (None if not yet determined)

    Returns:
        Tuple of (current_nesting_level, updated_base_indent)
    """
    stripped = line.lstrip()
    if not stripped:
        return 0, base_indent

    indent = len(line) - len(stripped)

    # Set base indent on first non-empty line
    if base_indent is None:
        return 0, indent

    # Calculate nesting level (assume 4 spaces per level)
    indent_diff = indent - base_indent
    current_nesting = max(0, indent_diff // 4)

    return current_nesting, base_indent


def _is_comment_line(stripped: str) -> bool:
    """Check if a line is a comment.

    Args:
        stripped: Left-stripped line content

    Returns:
        True if line is a comment
    """
    return stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*')


def _match_control_flow_keyword(stripped: str, control_flow: List[str]) -> Optional[str]:
    """Check if line starts with a control flow keyword.

    Args:
        stripped: Left-stripped line content
        control_flow: List of control flow keywords

    Returns:
        Matched keyword or None
    """
    for keyword in control_flow:
        # Match keyword at start of line (after stripping)
        # Use word boundary to avoid matching 'format' when looking for 'for'
        pattern = rf'^{keyword}(?:\s|\(|:)'
        if re.match(pattern, stripped):
            return keyword
    return None


def _calculate_keyword_complexity(keyword: str, stripped: str, current_nesting: int) -> int:
    """Calculate complexity increment for a control flow keyword.

    Args:
        keyword: Matched control flow keyword
        stripped: Left-stripped line content
        current_nesting: Current nesting level

    Returns:
        Complexity increment (1 + nesting penalty for most keywords)
    """
    # Handle else if / elif specially - they add +1 but no nesting penalty
    if keyword == "elif" or stripped.startswith("else if"):
        return 1

    # Base increment + nesting penalty for all other keywords
    return 1 + current_nesting


def _count_logical_operator_sequences(stripped: str, language: str) -> int:
    """Count logical operator sequences in a line.

    Based on SonarSource spec: Each sequence of logical operators adds complexity.
    Changes from AND to OR (or vice versa) increment the count.
    Examples: "a && b && c" = +1, "a && b || c" = +2

    Args:
        stripped: Left-stripped line content
        language: Programming language

    Returns:
        Complexity increment from logical operators
    """
    # Get language-specific patterns
    if language.lower() == "python":
        and_pattern = r'\band\b'
        or_pattern = r'\bor\b'
    else:
        # C-style uses && and ||
        and_pattern = r'&&'
        or_pattern = r'\|\|'

    # Find all operator matches with positions
    and_matches = list(re.finditer(and_pattern, stripped))
    or_matches = list(re.finditer(or_pattern, stripped))

    if not and_matches and not or_matches:
        return 0

    # Combine and sort by position
    all_ops: List[Tuple[int, str]] = (
        [(m.start(), 'and') for m in and_matches] +
        [(m.start(), 'or') for m in or_matches]
    )
    all_ops.sort(key=lambda x: x[0])

    # Count sequences (changes in operator type)
    sequences = 1  # First sequence
    for i in range(1, len(all_ops)):
        if all_ops[i][1] != all_ops[i-1][1]:
            sequences += 1

    return sequences


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
    base_indent: Optional[int] = None

    # Get language-specific control flow keywords
    control_flow = _get_control_flow_keywords(language, patterns)

    # Process each line
    for line in code.split('\n'):
        stripped = line.lstrip()

        # Skip empty lines and comments
        if not stripped or _is_comment_line(stripped):
            continue

        # Calculate nesting level from indentation
        current_nesting, base_indent = _calculate_line_indentation(line, base_indent)

        # Check for control flow keywords
        keyword = _match_control_flow_keyword(stripped, control_flow)
        if keyword:
            complexity += _calculate_keyword_complexity(keyword, stripped, current_nesting)
        # Handle 'else if' in C-style languages (not caught by keyword match)
        elif stripped.startswith("else if"):
            complexity += 1  # No nesting penalty for else if

        # Count logical operator sequences
        complexity += _count_logical_operator_sequences(stripped, language)

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
