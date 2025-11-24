"""
Code complexity analysis.

This module provides functions for analyzing code complexity at the file level,
extracting functions, and calculating complexity metrics for each function.
"""

import json
import re
import subprocess
from typing import Any, Dict, List

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
    classes: List[Dict[str, Any]] = []

    # Define class patterns per language
    class_patterns = {
        "python": "class $NAME($$$): $$$",
        "typescript": "class $NAME { $$$ }",
        "javascript": "class $NAME { $$$ }",
        "java": "class $NAME { $$$ }"
    }

    pattern = class_patterns.get(language.lower(), class_patterns["python"])

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
                for match in matches:
                    # Extract class name
                    cls_name = "unknown"
                    meta_vars = match.get("metaVariables", {})
                    if "NAME" in meta_vars:
                        name_data = meta_vars["NAME"]
                        if isinstance(name_data, dict):
                            cls_name = name_data.get("text", "unknown")
                        elif isinstance(name_data, str):
                            cls_name = name_data

                    # Get line numbers
                    range_info = match.get("range", {})
                    start_line = range_info.get("start", {}).get("line", 0) + 1
                    end_line = range_info.get("end", {}).get("line", 0) + 1

                    # Count methods in class
                    code = match.get("text", "")
                    method_count = 0
                    if language.lower() == "python":
                        method_count = len(re.findall(r'^\s+def\s+', code, re.MULTILINE))
                    else:
                        # Count function/method patterns in class body
                        method_count = len(re.findall(r'^\s+\w+\s*\([^)]*\)\s*\{', code, re.MULTILINE))

                    classes.append({
                        "name": cls_name,
                        "start_line": start_line,
                        "end_line": end_line,
                        "method_count": method_count,
                        "code": code
                    })
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        logger = get_logger("code_smell.extract_classes")
        logger.warning("extract_classes_failed", file=file_path, error=str(e))

    return classes


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

            # Extract function name from match
            # Try to get from metaVariables or parse from code
            func_name = "unknown"
            meta_vars = func.get("metaVariables", {})
            if "NAME" in meta_vars:
                name_data = meta_vars["NAME"]
                if isinstance(name_data, dict):
                    func_name = name_data.get("text", "unknown")
                elif isinstance(name_data, str):
                    func_name = name_data

            # Get line numbers
            range_info = func.get("range", {})
            start_line = range_info.get("start", {}).get("line", 0) + 1
            end_line = range_info.get("end", {}).get("line", 0) + 1

            # Calculate metrics
            cyclomatic = calculate_cyclomatic_complexity(code, language)
            cognitive = calculate_cognitive_complexity(code, language)
            nesting = calculate_nesting_depth(code, language)
            lines = len(code.split('\n'))

            # Count parameters (simple heuristic)
            param_count = 0
            if '(' in code and ')' in code:
                param_section = code[code.index('('):code.index(')')]
                if param_section.strip('()'):
                    param_count = param_section.count(',') + 1

            metrics = ComplexityMetrics(
                cyclomatic=cyclomatic,
                cognitive=cognitive,
                nesting_depth=nesting,
                lines=lines,
                parameter_count=param_count
            )

            # Check which thresholds are exceeded
            exceeds: List[str] = []
            if cyclomatic > thresholds.cyclomatic:
                exceeds.append("cyclomatic")
            if cognitive > thresholds.cognitive:
                exceeds.append("cognitive")
            if nesting > thresholds.nesting_depth:
                exceeds.append("nesting")
            if lines > thresholds.lines:
                exceeds.append("length")

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
