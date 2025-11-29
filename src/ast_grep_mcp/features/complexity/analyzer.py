"""
Code complexity analysis.

This module provides functions for analyzing code complexity at the file level,
extracting functions, and calculating complexity metrics for each function.
"""

import json
import re
import subprocess
from typing import Any, Dict, List, Tuple

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.complexity import (
    ComplexityMetrics,
    ComplexityThresholds,
    FunctionComplexity,
)

from .metrics import (
    calculate_cognitive_complexity,
    calculate_cyclomatic_complexity,
    calculate_nesting_depth,
    get_complexity_patterns,
)

__all__ = [
    "extract_functions_from_file",
    "analyze_file_complexity",
    "calculate_nesting_depth",
]


def extract_functions_from_file(file_path: str, language: str) -> List[Dict[str, Any]]:
    """Extract all functions from a file using ast-grep.

    Args:
        file_path: Path to source file
        language: Programming language

    Returns:
        List of function matches with metadata
    """
    patterns = get_complexity_patterns(language)
    all_functions: List[Dict[str, Any]] = []

    # Get all function patterns for this language
    function_patterns = []
    if "function" in patterns:
        function_patterns.append(patterns["function"])
    if "async_function" in patterns:
        function_patterns.append(patterns["async_function"])
    if "arrow_function" in patterns:
        function_patterns.append(patterns["arrow_function"])
    if "method" in patterns:
        function_patterns.append(patterns["method"])

    for pattern in function_patterns:
        try:
            result = subprocess.run(
                ["ast-grep", "run", "--pattern", pattern, "--lang", language, "--json", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                matches = json.loads(result.stdout)
                if isinstance(matches, list):
                    all_functions.extend(matches)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger = get_logger("complexity.extract")
            logger.warning("extract_functions_failed", file=file_path, error=str(e))

    return all_functions


def _extract_classes_from_file(file_path: str, language: str) -> List[Dict[str, Any]]:
    """Extract all classes from a file using ast-grep.

    Args:
        file_path: Path to source file
        language: Programming language

    Returns:
        List of class info dicts with name, start_line, end_line, method_count
    """
    pattern = _get_class_extraction_pattern(language)

    try:
        matches = _execute_ast_grep_for_classes(file_path, language, pattern)
        return _process_class_match_results(matches, language)
    except Exception as e:
        logger = get_logger("code_smell.extract_classes")
        logger.warning("extract_classes_failed", file=file_path, error=str(e))
        return []


def _get_class_extraction_pattern(language: str) -> str:
    """Get the ast-grep pattern for class detection based on language.

    Args:
        language: Programming language

    Returns:
        Pattern string for ast-grep
    """
    class_patterns = {
        "python": "class $NAME($$$): $$$",
        "typescript": "class $NAME { $$$ }",
        "javascript": "class $NAME { $$$ }",
        "java": "class $NAME { $$$ }"
    }
    return class_patterns.get(language.lower(), class_patterns["python"])


def _execute_ast_grep_for_classes(
    file_path: str,
    language: str,
    pattern: str
) -> List[Dict[str, Any]]:
    """Run ast-grep to find class matches.

    Args:
        file_path: Path to file to analyze
        language: Programming language
        pattern: ast-grep pattern to use

    Returns:
        List of match dictionaries from ast-grep output
    """
    result = subprocess.run(
        ["ast-grep", "run", "--pattern", pattern, "--lang", language, "--json", file_path],
        capture_output=True,
        text=True,
        timeout=30
    )

    # Early return for failed or empty results
    if result.returncode != 0 or not result.stdout.strip():
        return []

    matches = json.loads(result.stdout)
    return matches if isinstance(matches, list) else []


def _process_class_match_results(
    matches: List[Dict[str, Any]],
    language: str
) -> List[Dict[str, Any]]:
    """Process ast-grep matches into class information.

    Args:
        matches: Raw match data from ast-grep
        language: Programming language

    Returns:
        List of class information dictionaries
    """
    classes = []
    for match in matches:
        cls_info = _extract_single_class_info(match, language)
        classes.append(cls_info)
    return classes


def _extract_single_class_info(match: Dict[str, Any], language: str) -> Dict[str, Any]:
    """Extract class information from a single ast-grep match.

    Args:
        match: Single match dictionary from ast-grep
        language: Programming language

    Returns:
        Dictionary with class name, lines, method count, and code
    """
    cls_name = _extract_class_name_from_match(match)
    start_line, end_line = _extract_class_line_range(match)
    code = match.get("text", "")
    method_count = _count_class_methods(code, language)

    return {
        "name": cls_name,
        "start_line": start_line,
        "end_line": end_line,
        "method_count": method_count,
        "code": code
    }


def _extract_class_name_from_match(match: Dict[str, Any]) -> str:
    """Extract class name from ast-grep match metavariables.

    Args:
        match: Match dictionary from ast-grep

    Returns:
        Class name or "unknown" if not found
    """
    meta_vars = match.get("metaVariables", {})
    if "NAME" not in meta_vars:
        return "unknown"

    name_data = meta_vars["NAME"]

    # Handle both dict and string formats
    if isinstance(name_data, dict):
        result = name_data.get("text", "unknown")
        return str(result) if result is not None else "unknown"
    elif isinstance(name_data, str):
        return name_data
    else:
        return "unknown"


def _extract_class_line_range(match: Dict[str, Any]) -> Tuple[int, int]:
    """Extract start and end line numbers from ast-grep match.

    Args:
        match: Match dictionary from ast-grep

    Returns:
        Tuple of (start_line, end_line), 1-indexed
    """
    range_info = match.get("range", {})
    start_line = range_info.get("start", {}).get("line", 0) + 1
    end_line = range_info.get("end", {}).get("line", 0) + 1
    return start_line, end_line


def _count_class_methods(code: str, language: str) -> int:
    """Count the number of methods in a class.

    Args:
        code: Class code as string
        language: Programming language

    Returns:
        Number of methods found
    """
    if language.lower() == "python":
        return len(re.findall(r'^\s+def\s+', code, re.MULTILINE))
    else:
        # Count function/method patterns in class body
        return len(re.findall(r'^\s+\w+\s*\([^)]*\)\s*\{', code, re.MULTILINE))


def _count_function_parameters(code: str, language: str) -> int:
    """Count the number of parameters in a function.

    Args:
        code: Function source code
        language: Programming language

    Returns:
        Number of parameters
    """
    # Find the parameter list
    if language.lower() == "python":
        # Match def name(params): or async def name(params):
        match = re.search(r'def\s+\w+\s*\(([^)]*)\)', code)
    else:
        # Match function name(params) { or (params) =>
        match = re.search(r'(?:function\s+\w+|\w+)\s*\(([^)]*)\)', code)

    if not match:
        return 0

    params = match.group(1).strip()
    if not params:
        return 0

    # Handle self/this as non-parameter
    if language.lower() == "python":
        # Remove 'self' and 'cls' from count
        params = re.sub(r'\bself\b\s*,?\s*', '', params)
        params = re.sub(r'\bcls\b\s*,?\s*', '', params)

    # Count commas + 1 (unless empty)
    params = params.strip()
    if not params:
        return 0

    # Handle default values and type annotations
    # Count actual parameters by splitting on commas at the right depth
    depth = 0
    param_count = 1 if params else 0
    for char in params:
        if char in '([{<':
            depth += 1
        elif char in ')]}>':
            depth -= 1
        elif char == ',' and depth == 0:
            param_count += 1

    return param_count


def _find_magic_numbers(content: str, lines: List[str], language: str) -> List[Dict[str, Any]]:
    """Find magic numbers in code.

    Magic numbers are hard-coded numeric literals that should be named constants.
    Excludes common values: 0, 1, -1, 2, 10, 100, 1000.

    Args:
        content: Full file content
        lines: List of lines in the file
        language: Programming language

    Returns:
        List of magic number findings with line and value
    """
    magic_numbers: List[Dict[str, Any]] = []

    # Common values that aren't magic
    allowed_values = {'0', '1', '-1', '2', '10', '100', '1000', '0.0', '1.0', '0.5'}

    # Patterns for different contexts to exclude
    exclude_patterns = [
        r'^\s*#',        # Python comments
        r'^\s*//',       # JS/Java comments
        r'^\s*\*',       # Multi-line comment continuation
        r'^\s*import',   # Import statements
        r'^\s*from',     # Python from imports
        r'=\s*\d+\s*$',  # Variable assignment (likely a constant definition)
        r'range\(',      # Range calls
        r'sleep\(',      # Sleep calls
        r'timeout',      # Timeout settings
        r'port\s*=',     # Port assignments
        r'version',      # Version numbers
    ]

    for line_num, line in enumerate(lines, 1):
        # Skip comments and certain patterns
        should_skip = False
        for pattern in exclude_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                should_skip = True
                break

        if should_skip:
            continue

        # Find all numeric literals in line
        # Match integers and floats, but not in string literals
        # This is a simplified approach - production would need AST
        numbers = re.findall(r'\b(\d+\.?\d*)\b', line)

        for num in numbers:
            if num not in allowed_values:
                # Check it's not in a string
                # Simple check: not between quotes
                before_num = line[:line.find(num)]
                quote_count = before_num.count('"') + before_num.count("'")
                if quote_count % 2 == 0:  # Even number of quotes = not in string
                    magic_numbers.append({
                        "line": line_num,
                        "value": num
                    })

    # Limit to avoid overwhelming output
    return magic_numbers[:50]


def _extract_function_name(func: Dict[str, Any]) -> str:
    """Extract function name from ast-grep match.

    Args:
        func: Function match from ast-grep

    Returns:
        Function name or "unknown" if not found
    """
    meta_vars = func.get("metaVariables", {})
    if "NAME" not in meta_vars:
        return "unknown"

    name_data = meta_vars["NAME"]
    if isinstance(name_data, dict):
        result = name_data.get("text", "unknown")
        return str(result) if result is not None else "unknown"
    elif isinstance(name_data, str):
        return name_data
    return "unknown"


def _get_line_numbers(func: Dict[str, Any]) -> Tuple[int, int]:
    """Extract line numbers from ast-grep range info.

    Args:
        func: Function match from ast-grep

    Returns:
        Tuple of (start_line, end_line), 1-indexed
    """
    range_info = func.get("range", {})
    start_line = range_info.get("start", {}).get("line", 0) + 1
    end_line = range_info.get("end", {}).get("line", 0) + 1
    return start_line, end_line


def _calculate_all_metrics(code: str, language: str) -> ComplexityMetrics:
    """Calculate all complexity metrics for a function.

    Args:
        code: Function source code
        language: Programming language

    Returns:
        ComplexityMetrics with all calculated values
    """
    cyclomatic = calculate_cyclomatic_complexity(code, language)
    cognitive = calculate_cognitive_complexity(code, language)
    nesting = calculate_nesting_depth(code, language)
    lines = len(code.split('\n'))
    param_count = _count_function_parameters(code, language)

    return ComplexityMetrics(
        cyclomatic=cyclomatic,
        cognitive=cognitive,
        nesting_depth=nesting,
        lines=lines,
        parameter_count=param_count
    )


def _check_threshold_violations(
    metrics: ComplexityMetrics,
    thresholds: ComplexityThresholds
) -> List[str]:
    """Check which thresholds are exceeded.

    Args:
        metrics: Calculated metrics
        thresholds: Threshold values

    Returns:
        List of exceeded threshold names
    """
    exceeds: List[str] = []

    if metrics.cyclomatic > thresholds.cyclomatic:
        exceeds.append("cyclomatic")
    if metrics.cognitive > thresholds.cognitive:
        exceeds.append("cognitive")
    if metrics.nesting_depth > thresholds.nesting_depth:
        exceeds.append("nesting")
    if metrics.lines > thresholds.lines:
        exceeds.append("length")

    return exceeds


def analyze_file_complexity(
    file_path: str,
    language: str,
    thresholds: ComplexityThresholds
) -> List[FunctionComplexity]:
    """Analyze complexity of all functions in a file.

    Args:
        file_path: Path to source file
        language: Programming language
        thresholds: Complexity thresholds

    Returns:
        List of FunctionComplexity objects
    """
    results: List[FunctionComplexity] = []

    try:
        functions = extract_functions_from_file(file_path, language)

        for func in functions:
            code = func.get("text", "")
            if not code:
                continue

            func_name = _extract_function_name(func)
            start_line, end_line = _get_line_numbers(func)
            metrics = _calculate_all_metrics(code, language)
            exceeds = _check_threshold_violations(metrics, thresholds)

            results.append(FunctionComplexity(
                file_path=file_path,
                function_name=func_name,
                start_line=start_line,
                end_line=end_line,
                metrics=metrics,
                language=language,
                exceeds=exceeds
            ))

    except Exception as e:
        logger = get_logger("complexity.analyze")
        logger.error("analyze_file_failed", file=file_path, error=str(e))

    return results
