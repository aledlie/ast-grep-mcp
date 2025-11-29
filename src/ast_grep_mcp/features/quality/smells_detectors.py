"""Smell detector implementations using strategy pattern.

This module contains individual detector classes for each type of code smell,
following the strategy pattern for extensibility and maintainability.
"""

import json
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.complexity.analyzer import calculate_nesting_depth, extract_functions_from_file
from ast_grep_mcp.features.quality.smells_helpers import calculate_smell_severity


@dataclass
class SmellInfo:
    """Information about a detected code smell."""
    type: str
    file: str
    name: str
    line: int
    severity: str
    metric: Any
    threshold: Any
    message: str
    suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "file": self.file,
            "name": self.name,
            "line": self.line,
            "severity": self.severity,
            "metric": self.metric,
            "threshold": self.threshold,
            "message": self.message,
            "suggestion": self.suggestion
        }


class SmellDetector(ABC):
    """Base class for smell detectors."""

    @abstractmethod
    def detect(
        self,
        file_path: str,
        content: str,
        language: str,
        project_path: Path
    ) -> List[SmellInfo]:
        """Detect smells in the given file.

        Args:
            file_path: Path to the file being analyzed
            content: File content
            language: Programming language
            project_path: Root project path for relative path calculation

        Returns:
            List of detected smell information
        """
        pass


class LongFunctionDetector(SmellDetector):
    """Detects functions that are too long."""

    def __init__(self, threshold: int) -> None:
        """Initialize with line threshold.

        Args:
            threshold: Maximum number of lines for a function
        """
        self.threshold = threshold
        self.logger = get_logger("smell_detector.long_function")

    def detect(
        self,
        file_path: str,
        content: str,
        language: str,
        project_path: Path
    ) -> List[SmellInfo]:
        """Detect long functions in the file."""
        smells = []
        rel_path = str(Path(file_path).relative_to(project_path))

        try:
            functions = extract_functions_from_file(file_path, language)

            for func in functions:
                func_name = func.get("name", "unknown")
                func_start = func.get("start_line", 1)
                func_end = func.get("end_line", func_start)
                func_lines = func_end - func_start + 1

                if func_lines > self.threshold:
                    severity = calculate_smell_severity(
                        func_lines, self.threshold, "long_function"
                    )
                    smells.append(SmellInfo(
                        type="long_function",
                        file=rel_path,
                        name=func_name,
                        line=func_start,
                        severity=severity,
                        metric=func_lines,
                        threshold=self.threshold,
                        message=f"Function '{func_name}' has {func_lines} lines (threshold: {self.threshold})",
                        suggestion="Consider splitting into smaller, focused functions"
                    ))

        except Exception as e:
            self.logger.warning("detection_failed", file=file_path, error=str(e))

        return smells


class ParameterBloatDetector(SmellDetector):
    """Detects functions with too many parameters."""

    def __init__(self, threshold: int) -> None:
        """Initialize with parameter count threshold.

        Args:
            threshold: Maximum number of parameters for a function
        """
        self.threshold = threshold
        self.logger = get_logger("smell_detector.parameter_bloat")

    def detect(
        self,
        file_path: str,
        content: str,
        language: str,
        project_path: Path
    ) -> List[SmellInfo]:
        """Detect parameter bloat in functions."""
        smells = []
        rel_path = str(Path(file_path).relative_to(project_path))

        try:
            functions = extract_functions_from_file(file_path, language)

            for func in functions:
                func_name = func.get("name", "unknown")
                func_start = func.get("start_line", 1)
                func_code = func.get("code", "")

                param_count = self._count_parameters(func_code, language)

                if param_count > self.threshold:
                    severity = calculate_smell_severity(
                        param_count, self.threshold, "parameter_bloat"
                    )
                    smells.append(SmellInfo(
                        type="parameter_bloat",
                        file=rel_path,
                        name=func_name,
                        line=func_start,
                        severity=severity,
                        metric=param_count,
                        threshold=self.threshold,
                        message=f"Function '{func_name}' has {param_count} parameters (threshold: {self.threshold})",
                        suggestion="Consider using a parameter object or builder pattern"
                    ))

        except Exception as e:
            self.logger.warning("detection_failed", file=file_path, error=str(e))

        return smells

    def _count_parameters(self, code: str, language: str) -> int:
        """Count the number of parameters in a function."""
        # Find the parameter list
        if language.lower() == "python":
            match = re.search(r'def\s+\w+\s*\(([^)]*)\)', code)
        else:
            match = re.search(r'(?:function\s+\w+|\w+)\s*\(([^)]*)\)', code)

        if not match:
            return 0

        params = match.group(1).strip()
        if not params:
            return 0

        # Handle self/this as non-parameter for Python
        if language.lower() == "python":
            params = re.sub(r'\bself\b\s*,?\s*', '', params)
            params = re.sub(r'\bcls\b\s*,?\s*', '', params)

        params = params.strip()
        if not params:
            return 0

        # Count parameters by splitting on commas at the right depth
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


class DeepNestingDetector(SmellDetector):
    """Detects excessive nesting depth in functions."""

    def __init__(self, threshold: int) -> None:
        """Initialize with nesting depth threshold.

        Args:
            threshold: Maximum nesting depth for a function
        """
        self.threshold = threshold
        self.logger = get_logger("smell_detector.deep_nesting")

    def detect(
        self,
        file_path: str,
        content: str,
        language: str,
        project_path: Path
    ) -> List[SmellInfo]:
        """Detect deep nesting in functions."""
        smells = []
        rel_path = str(Path(file_path).relative_to(project_path))

        try:
            functions = extract_functions_from_file(file_path, language)

            for func in functions:
                func_name = func.get("name", "unknown")
                func_start = func.get("start_line", 1)
                func_code = func.get("code", "")

                max_nesting = calculate_nesting_depth(func_code, language)

                if max_nesting > self.threshold:
                    severity = calculate_smell_severity(
                        max_nesting, self.threshold, "deep_nesting"
                    )
                    smells.append(SmellInfo(
                        type="deep_nesting",
                        file=rel_path,
                        name=func_name,
                        line=func_start,
                        severity=severity,
                        metric=max_nesting,
                        threshold=self.threshold,
                        message=f"Function '{func_name}' has nesting depth {max_nesting} (threshold: {self.threshold})",
                        suggestion="Use early returns, extract nested logic, or apply guard clauses"
                    ))

        except Exception as e:
            self.logger.warning("detection_failed", file=file_path, error=str(e))

        return smells


class LargeClassDetector(SmellDetector):
    """Detects classes that are too large."""

    def __init__(self, lines_threshold: int, methods_threshold: int) -> None:
        """Initialize with size thresholds.

        Args:
            lines_threshold: Maximum number of lines for a class
            methods_threshold: Maximum number of methods for a class
        """
        self.lines_threshold = lines_threshold
        self.methods_threshold = methods_threshold
        self.logger = get_logger("smell_detector.large_class")

    def detect(
        self,
        file_path: str,
        content: str,
        language: str,
        project_path: Path
    ) -> List[SmellInfo]:
        """Detect large classes in the file."""
        smells = []
        rel_path = str(Path(file_path).relative_to(project_path))

        try:
            classes = self._extract_classes(file_path, language)

            for cls in classes:
                cls_name = cls.get("name", "unknown")
                cls_start = cls.get("start_line", 1)
                cls_end = cls.get("end_line", cls_start)
                cls_method_count = cls.get("method_count", 0)
                cls_lines_count = cls_end - cls_start + 1

                # Check if class is too large
                is_large = False
                reason = ""
                metric_value = {}

                if cls_lines_count > self.lines_threshold:
                    is_large = True
                    reason = f"{cls_lines_count} lines (threshold: {self.lines_threshold})"
                    metric_value = {"lines": cls_lines_count, "methods": cls_method_count}

                if cls_method_count > self.methods_threshold:
                    is_large = True
                    if reason:
                        reason += f" and {cls_method_count} methods (threshold: {self.methods_threshold})"
                    else:
                        reason = f"{cls_method_count} methods (threshold: {self.methods_threshold})"
                    metric_value = {"lines": cls_lines_count, "methods": cls_method_count}

                if is_large:
                    # Use lines for severity calculation as primary metric
                    severity = calculate_smell_severity(
                        cls_lines_count, self.lines_threshold, "large_class"
                    )
                    smells.append(SmellInfo(
                        type="large_class",
                        file=rel_path,
                        name=cls_name,
                        line=cls_start,
                        severity=severity,
                        metric=metric_value,
                        threshold={"lines": self.lines_threshold, "methods": self.methods_threshold},
                        message=f"Class '{cls_name}' is too large: {reason}",
                        suggestion="Consider splitting into smaller classes following Single Responsibility Principle"
                    ))

        except Exception as e:
            self.logger.warning("detection_failed", file=file_path, error=str(e))

        return smells

    def _extract_classes(self, file_path: str, language: str) -> List[Dict[str, Any]]:
        """Extract all classes from a file using ast-grep."""
        pattern = self._get_class_pattern(language)

        try:
            matches = self._run_ast_grep_for_classes(file_path, language, pattern)
            return self._process_class_matches(matches, language)
        except Exception as e:
            self.logger.warning("extract_classes_failed", file=file_path, error=str(e))
            return []

    def _get_class_pattern(self, language: str) -> str:
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

    def _run_ast_grep_for_classes(
        self,
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

    def _process_class_matches(
        self,
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
            cls_info = self._extract_class_info(match, language)
            classes.append(cls_info)
        return classes

    def _extract_class_info(self, match: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Extract class information from a single ast-grep match.

        Args:
            match: Single match dictionary from ast-grep
            language: Programming language

        Returns:
            Dictionary with class name, lines, and method count
        """
        cls_name = self._extract_class_name(match)
        start_line, end_line = self._extract_line_range(match)
        method_count = self._count_methods_in_class(match.get("text", ""), language)

        return {
            "name": cls_name,
            "start_line": start_line,
            "end_line": end_line,
            "method_count": method_count
        }

    def _extract_class_name(self, match: Dict[str, Any]) -> str:
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

    def _extract_line_range(self, match: Dict[str, Any]) -> tuple[int, int]:
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

    def _count_methods_in_class(self, code: str, language: str) -> int:
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
            return len(re.findall(r'^\s+\w+\s*\([^)]*\)\s*\{', code, re.MULTILINE))


class MagicNumberDetector(SmellDetector):
    """Detects magic numbers in code."""

    def __init__(self, enabled: bool = True) -> None:
        """Initialize magic number detector.

        Args:
            enabled: Whether detection is enabled
        """
        self.enabled = enabled
        self.logger = get_logger("smell_detector.magic_number")

    def detect(
        self,
        file_path: str,
        content: str,
        language: str,
        project_path: Path
    ) -> List[SmellInfo]:
        """Detect magic numbers in the code."""
        if not self.enabled:
            return []

        smells = []
        rel_path = str(Path(file_path).relative_to(project_path))

        try:
            lines = content.split('\n')
            magic_numbers = self._find_magic_numbers(content, lines, language)

            for magic in magic_numbers:
                smells.append(SmellInfo(
                    type="magic_number",
                    file=rel_path,
                    name=str(magic.get("value")),
                    line=magic.get("line", 0),
                    severity="low",
                    metric=magic.get("value"),
                    threshold="N/A",
                    message=f"Magic number '{magic.get('value')}' on line {magic.get('line')}",
                    suggestion="Extract to a named constant with meaningful name"
                ))

        except Exception as e:
            self.logger.warning("detection_failed", file=file_path, error=str(e))

        return smells

    def _find_magic_numbers(
        self,
        content: str,
        lines: List[str],
        language: str
    ) -> List[Dict[str, Any]]:
        """Find magic numbers in code."""
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
            numbers = re.findall(r'\b(\d+\.?\d*)\b', line)

            for num in numbers:
                if num not in allowed_values:
                    # Check it's not in a string (simple check)
                    before_num = line[:line.find(num)]
                    quote_count = before_num.count('"') + before_num.count("'")
                    if quote_count % 2 == 0:  # Even number of quotes = not in string
                        magic_numbers.append({
                            "line": line_num,
                            "value": num
                        })

        # Limit to avoid overwhelming output
        return magic_numbers[:50]


class SmellAnalyzer:
    """Orchestrates smell detection across files."""

    def __init__(self, detectors: List[SmellDetector]) -> None:
        """Initialize with a list of detectors.

        Args:
            detectors: List of smell detector instances
        """
        self.detectors = detectors
        self.logger = get_logger("smell_analyzer")

    def analyze_file(
        self,
        file_path: str,
        language: str,
        project_path: Path
    ) -> List[Dict[str, Any]]:
        """Analyze a single file for all configured smells.

        Args:
            file_path: Path to file to analyze
            language: Programming language
            project_path: Root project path

        Returns:
            List of detected smells as dictionaries
        """
        smells = []

        try:
            content = Path(file_path).read_text(encoding='utf-8', errors='ignore')

            for detector in self.detectors:
                detected = detector.detect(file_path, content, language, project_path)
                smells.extend([smell.to_dict() for smell in detected])

        except Exception as e:
            self.logger.error("file_analysis_failed", file=file_path, error=str(e))

        return smells
