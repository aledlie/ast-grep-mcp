"""Code smell detection implementation.

This module provides functionality to detect common code smells and anti-patterns:
- Long functions
- Parameter bloat
- Deep nesting
- Large classes
- Magic numbers

Each smell includes severity ratings and actionable suggestions.
"""

import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.complexity.analyzer import calculate_nesting_depth, extract_functions_from_file


def detect_code_smells_impl(
    project_folder: str,
    language: str,
    include_patterns: List[str],
    exclude_patterns: List[str],
    long_function_lines: int,
    parameter_count: int,
    nesting_depth: int,
    class_lines: int,
    class_methods: int,
    detect_magic_numbers: bool,
    severity_filter: str,
    max_threads: int
) -> Dict[str, Any]:
    """Detect common code smells in a project.

    Args:
        project_folder: Absolute path to project
        language: Programming language (python, typescript, javascript, java)
        include_patterns: Glob patterns for files to include
        exclude_patterns: Glob patterns for files to exclude
        long_function_lines: Line count threshold for long function smell
        parameter_count: Parameter count threshold for parameter bloat
        nesting_depth: Nesting depth threshold for deep nesting smell
        class_lines: Line count threshold for large class smell
        class_methods: Method count threshold for large class smell
        detect_magic_numbers: Whether to detect magic number smells
        severity_filter: Filter by severity: 'all', 'high', 'medium', 'low'
        max_threads: Number of parallel threads for analysis

    Returns:
        Dictionary containing smell detection results with summary and details
    """
    logger = get_logger("detect_code_smells")

    # Validate project folder
    project_path = Path(project_folder)
    if not project_path.exists():
        return {"error": f"Project folder not found: {project_folder}"}
    if not project_path.is_dir():
        return {"error": f"Path is not a directory: {project_folder}"}

    # Get file extension for language
    ext_map = {
        "python": ".py",
        "typescript": ".ts",
        "javascript": ".js",
        "java": ".java"
    }
    file_ext = ext_map.get(language.lower(), ".py")

    # Find all matching files
    all_files = []
    for pattern in include_patterns:
        if not pattern.endswith(file_ext) and not pattern.endswith("*"):
            pattern = pattern.rstrip("/") + f"/**/*{file_ext}"
        elif pattern.endswith("*") and not pattern.endswith(file_ext):
            pattern = pattern + file_ext if pattern.endswith("*/") else pattern.rstrip("*") + f"*{file_ext}"

        matches = list(project_path.glob(pattern.lstrip("/")))
        all_files.extend([str(f) for f in matches if f.is_file()])

    # Remove duplicates
    all_files = list(set(all_files))

    # Filter by exclude patterns
    filtered_files = []
    for file_path in all_files:
        excluded = False
        rel_path = str(Path(file_path).relative_to(project_path))
        for exc_pattern in exclude_patterns:
            if fnmatch(rel_path, exc_pattern.lstrip("/")):
                excluded = True
                break
        if not excluded:
            filtered_files.append(file_path)

    if not filtered_files:
        return {
            "error": f"No {language} files found matching patterns",
            "project_folder": project_folder,
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns
        }

    # Collect all smells
    all_smells: List[Dict[str, Any]] = []

    def analyze_file_for_smells(file_path: str) -> List[Dict[str, Any]]:
        """Analyze a single file for code smells."""
        smells = []
        try:
            content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            rel_path = str(Path(file_path).relative_to(project_path))

            # Extract functions and classes from file
            functions = extract_functions_from_file(file_path, language)
            classes = _extract_classes_from_file(file_path, language)

            # Check each function for smells
            for func in functions:
                func_name = func.get("name", "unknown")
                func_start = func.get("start_line", 1)
                func_end = func.get("end_line", func_start)
                func_code = func.get("code", "")
                func_lines = func_end - func_start + 1

                # 1. Long Function Detection
                if func_lines > long_function_lines:
                    severity = "high" if func_lines > long_function_lines * 2 else "medium" if func_lines > long_function_lines * 1.5 else "low"
                    smells.append({
                        "type": "long_function",
                        "file": rel_path,
                        "name": func_name,
                        "line": func_start,
                        "severity": severity,
                        "metric": func_lines,
                        "threshold": long_function_lines,
                        "message": f"Function '{func_name}' has {func_lines} lines (threshold: {long_function_lines})",
                        "suggestion": "Consider splitting into smaller, focused functions"
                    })

                # 2. Parameter Bloat Detection
                param_count = _count_function_parameters(func_code, language)
                if param_count > parameter_count:
                    severity = "high" if param_count > parameter_count * 2 else "medium" if param_count > parameter_count + 2 else "low"
                    smells.append({
                        "type": "parameter_bloat",
                        "file": rel_path,
                        "name": func_name,
                        "line": func_start,
                        "severity": severity,
                        "metric": param_count,
                        "threshold": parameter_count,
                        "message": f"Function '{func_name}' has {param_count} parameters (threshold: {parameter_count})",
                        "suggestion": "Consider using a parameter object or builder pattern"
                    })

                # 3. Deep Nesting Detection
                max_nesting = calculate_nesting_depth(func_code, language)
                if max_nesting > nesting_depth:
                    severity = "high" if max_nesting > nesting_depth + 2 else "medium" if max_nesting > nesting_depth + 1 else "low"
                    smells.append({
                        "type": "deep_nesting",
                        "file": rel_path,
                        "name": func_name,
                        "line": func_start,
                        "severity": severity,
                        "metric": max_nesting,
                        "threshold": nesting_depth,
                        "message": f"Function '{func_name}' has nesting depth {max_nesting} (threshold: {nesting_depth})",
                        "suggestion": "Use early returns, extract nested logic, or apply guard clauses"
                    })

            # Check each class for smells
            for cls in classes:
                cls_name = cls.get("name", "unknown")
                cls_start = cls.get("start_line", 1)
                cls_end = cls.get("end_line", cls_start)
                cls_method_count = cls.get("method_count", 0)
                cls_lines_count = cls_end - cls_start + 1

                # 4. Large Class Detection
                is_large = False
                reason = ""
                if cls_lines_count > class_lines:
                    is_large = True
                    reason = f"{cls_lines_count} lines (threshold: {class_lines})"
                if cls_method_count > class_methods:
                    is_large = True
                    reason = f"{cls_method_count} methods (threshold: {class_methods})"

                if is_large:
                    severity = "high" if cls_lines_count > class_lines * 1.5 or cls_method_count > class_methods * 1.5 else "medium"
                    smells.append({
                        "type": "large_class",
                        "file": rel_path,
                        "name": cls_name,
                        "line": cls_start,
                        "severity": severity,
                        "metric": {"lines": cls_lines_count, "methods": cls_method_count},
                        "threshold": {"lines": class_lines, "methods": class_methods},
                        "message": f"Class '{cls_name}' is too large: {reason}",
                        "suggestion": "Consider splitting into smaller classes following Single Responsibility Principle"
                    })

            # 5. Magic Number Detection
            if detect_magic_numbers:
                magic_numbers = _find_magic_numbers(content, lines, language)
                for magic in magic_numbers:
                    smells.append({
                        "type": "magic_number",
                        "file": rel_path,
                        "name": magic.get("value"),
                        "line": magic.get("line"),
                        "severity": "low",
                        "metric": magic.get("value"),
                        "threshold": "N/A",
                        "message": f"Magic number '{magic.get('value')}' on line {magic.get('line')}",
                        "suggestion": "Extract to a named constant with meaningful name"
                    })

        except Exception as e:
            logger.error("file_analysis_failed", file=file_path, error=str(e))

        return smells

    # Analyze files in parallel
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        results = list(executor.map(analyze_file_for_smells, filtered_files))

    # Flatten results
    for file_smells in results:
        all_smells.extend(file_smells)

    # Filter by severity if requested
    if severity_filter != "all":
        all_smells = [s for s in all_smells if s.get("severity") == severity_filter]

    # Sort by severity (high > medium > low) then by type
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_smells.sort(key=lambda s: (severity_order.get(s.get("severity", "low"), 3), s.get("type", "")))

    # Generate summary
    smell_counts: Dict[str, int] = {}
    severity_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for smell in all_smells:
        smell_type = smell.get("type", "unknown")
        smell_counts[smell_type] = smell_counts.get(smell_type, 0) + 1
        severity_counts[smell.get("severity", "low")] += 1

    return {
        "project_folder": project_folder,
        "language": language,
        "files_analyzed": len(filtered_files),
        "total_smells": len(all_smells),
        "summary": {
            "by_type": smell_counts,
            "by_severity": severity_counts
        },
        "smells": all_smells,
        "thresholds": {
            "long_function_lines": long_function_lines,
            "parameter_count": parameter_count,
            "nesting_depth": nesting_depth,
            "class_lines": class_lines,
            "class_methods": class_methods
        }
    }


def _extract_classes_from_file(file_path: str, language: str) -> List[Dict[str, Any]]:
    """Extract all classes from a file using ast-grep.

    Args:
        file_path: Path to source file
        language: Programming language

    Returns:
        List of class info dicts with name, start_line, end_line, method_count
    """
    logger = get_logger("code_smell.extract_classes")
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
