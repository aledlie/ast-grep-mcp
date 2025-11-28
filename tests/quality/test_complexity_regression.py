"""
Complexity Regression Tests

Ensures that refactored functions maintain low complexity and don't regress
back to high complexity levels.

These tests analyze the actual source code complexity metrics to prevent
complexity creep after refactoring.
"""

import ast
from pathlib import Path
from typing import List, Tuple

import pytest

from ast_grep_mcp.features.complexity.analyzer import (
    calculate_cognitive_complexity,
    calculate_cyclomatic_complexity,
    calculate_nesting_depth,
)


# Critical functions that were refactored in Phase 1 (2025-11-28)
CRITICAL_FUNCTIONS = [
    # Deduplication Applicator (refactored from 309 lines, complexity 219)
    # Main orchestrator - lines reduced from 309 to 102 (67% improvement)
    # Cyclomatic reduced from 71 to 21 (70% improvement)
    {
        "file": "src/ast_grep_mcp/features/deduplication/applicator.py",
        "function": "apply_deduplication",
        "max_lines": 150,  # Orchestrators can be slightly larger
        "max_cyclomatic": 25,  # Orchestrators can have higher complexity
        "max_cognitive": 20,
        "max_nesting": 5,
    },
    {
        "file": "src/ast_grep_mcp/features/deduplication/applicator.py",
        "function": "_validate_and_extract_plan",
        "max_lines": 100,
        "max_cyclomatic": 15,
        "max_cognitive": 20,
        "max_nesting": 5,
    },
    {
        "file": "src/ast_grep_mcp/features/deduplication/applicator.py",
        "function": "_perform_pre_validation",
        "max_lines": 100,
        "max_cyclomatic": 15,
        "max_cognitive": 20,
        "max_nesting": 5,
    },
    # Complexity Tools (refactored from 304 lines, complexity 117)
    {
        "file": "src/ast_grep_mcp/features/complexity/tools.py",
        "function": "analyze_complexity_tool",
        "max_lines": 200,  # Main orchestrator can be slightly larger
        "max_cyclomatic": 20,
        "max_cognitive": 20,
        "max_nesting": 5,
    },
    {
        "file": "src/ast_grep_mcp/features/complexity/tools.py",
        "function": "_validate_inputs",
        "max_lines": 50,
        "max_cyclomatic": 10,
        "max_cognitive": 10,
        "max_nesting": 3,
    },
    {
        "file": "src/ast_grep_mcp/features/complexity/tools.py",
        "function": "_find_files_to_analyze",
        "max_lines": 50,
        "max_cyclomatic": 10,
        "max_cognitive": 10,
        "max_nesting": 3,
    },
    # Code Smells (refactored from 250 lines, complexity 88)
    # Main orchestrator - cyclomatic reduced from 61 to 19 (69% improvement)
    {
        "file": "src/ast_grep_mcp/features/quality/smells.py",
        "function": "detect_code_smells_impl",
        "max_lines": 200,  # Main orchestrator
        "max_cyclomatic": 25,  # Orchestrators can have higher complexity
        "max_cognitive": 20,
        "max_nesting": 5,
    },
    {
        "file": "src/ast_grep_mcp/features/quality/smells_helpers.py",
        "function": "validate_smell_detection_inputs",
        "max_lines": 50,
        "max_cyclomatic": 10,
        "max_cognitive": 10,
        "max_nesting": 3,
    },
]


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def find_function_in_ast(tree: ast.Module, function_name: str) -> ast.FunctionDef | None:
    """Find a function definition in the AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    return None


def count_function_lines(func_node: ast.FunctionDef) -> int:
    """Count the number of lines in a function."""
    return func_node.end_lineno - func_node.lineno + 1


def analyze_function_complexity(
    file_path: Path, function_name: str
) -> dict:
    """Analyze complexity metrics for a specific function."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        func_node = find_function_in_ast(tree, function_name)

        if not func_node:
            return {
                "found": False,
                "error": f"Function {function_name} not found in {file_path}",
            }

        # Get function source code
        lines = source_code.splitlines()
        func_lines = lines[func_node.lineno - 1 : func_node.end_lineno]
        func_source = "\n".join(func_lines)

        # Calculate metrics
        cyclomatic = calculate_cyclomatic_complexity(func_source, "python")
        cognitive = calculate_cognitive_complexity(func_source, "python")
        nesting = calculate_nesting_depth(func_source, "python")
        line_count = count_function_lines(func_node)

        return {
            "found": True,
            "cyclomatic": cyclomatic,
            "cognitive": cognitive,
            "nesting": nesting,
            "lines": line_count,
        }

    except Exception as e:
        return {
            "found": False,
            "error": f"Error analyzing {file_path}:{function_name}: {e}",
        }


class TestComplexityRegression:
    """Test suite to prevent complexity regression in refactored functions."""

    @pytest.fixture(scope="class")
    def project_root(self) -> Path:
        """Get project root path."""
        return get_project_root()

    @pytest.mark.parametrize("func_spec", CRITICAL_FUNCTIONS)
    def test_function_complexity_thresholds(
        self, project_root: Path, func_spec: dict
    ):
        """Ensure refactored functions stay below complexity thresholds."""
        file_path = project_root / func_spec["file"]
        function_name = func_spec["function"]

        # Analyze the function
        metrics = analyze_function_complexity(file_path, function_name)

        # Check if function was found
        assert metrics["found"], metrics.get(
            "error", f"Function {function_name} not found"
        )

        # Check cyclomatic complexity
        assert (
            metrics["cyclomatic"] <= func_spec["max_cyclomatic"]
        ), f"{function_name} has cyclomatic complexity {metrics['cyclomatic']}, max allowed: {func_spec['max_cyclomatic']}"

        # Check cognitive complexity
        assert (
            metrics["cognitive"] <= func_spec["max_cognitive"]
        ), f"{function_name} has cognitive complexity {metrics['cognitive']}, max allowed: {func_spec['max_cognitive']}"

        # Check nesting depth
        assert (
            metrics["nesting"] <= func_spec["max_nesting"]
        ), f"{function_name} has nesting depth {metrics['nesting']}, max allowed: {func_spec['max_nesting']}"

        # Check line count
        assert (
            metrics["lines"] <= func_spec["max_lines"]
        ), f"{function_name} has {metrics['lines']} lines, max allowed: {func_spec['max_lines']}"

    def test_all_refactored_functions_exist(self, project_root: Path):
        """Verify that all critical functions still exist after refactoring."""
        missing_functions = []

        for func_spec in CRITICAL_FUNCTIONS:
            file_path = project_root / func_spec["file"]
            function_name = func_spec["function"]

            if not file_path.exists():
                missing_functions.append(f"{func_spec['file']} (file not found)")
                continue

            metrics = analyze_function_complexity(file_path, function_name)
            if not metrics["found"]:
                missing_functions.append(
                    f"{func_spec['file']}:{function_name} (function not found)"
                )

        assert not missing_functions, (
            f"Missing refactored functions:\n"
            + "\n".join(f"  - {f}" for f in missing_functions)
        )

    def test_phase1_refactoring_impact(self, project_root: Path):
        """Verify the overall impact of Phase 1 refactoring."""
        total_cyclomatic = 0
        total_cognitive = 0
        total_nesting = 0
        total_lines = 0
        function_count = 0

        for func_spec in CRITICAL_FUNCTIONS:
            file_path = project_root / func_spec["file"]
            function_name = func_spec["function"]

            metrics = analyze_function_complexity(file_path, function_name)
            if metrics["found"]:
                total_cyclomatic += metrics["cyclomatic"]
                total_cognitive += metrics["cognitive"]
                total_nesting += metrics["nesting"]
                total_lines += metrics["lines"]
                function_count += 1

        # Calculate averages
        avg_cyclomatic = total_cyclomatic / function_count if function_count > 0 else 0
        avg_cognitive = total_cognitive / function_count if function_count > 0 else 0
        avg_nesting = total_nesting / function_count if function_count > 0 else 0
        avg_lines = total_lines / function_count if function_count > 0 else 0

        # Phase 1 success criteria (from CODEBASE_ANALYSIS_REPORT.md)
        assert (
            avg_cyclomatic < 12
        ), f"Average cyclomatic complexity {avg_cyclomatic:.1f} exceeds target of 12"
        assert (
            avg_cognitive < 15
        ), f"Average cognitive complexity {avg_cognitive:.1f} exceeds target of 15"
        assert (
            avg_nesting < 4
        ), f"Average nesting depth {avg_nesting:.1f} exceeds target of 4"
        assert avg_lines < 100, f"Average lines {avg_lines:.1f} exceeds target of 100"


class TestComplexityTrends:
    """Monitor complexity trends across the codebase."""

    @pytest.fixture(scope="class")
    def project_root(self) -> Path:
        """Get project root path."""
        return get_project_root()

    def test_no_extremely_complex_functions(self, project_root: Path):
        """Ensure no function has extreme complexity after Phase 1."""
        # Scan the three refactored files
        refactored_files = [
            "src/ast_grep_mcp/features/deduplication/applicator.py",
            "src/ast_grep_mcp/features/complexity/tools.py",
            "src/ast_grep_mcp/features/quality/smells.py",
        ]

        extreme_functions = []

        for file_rel_path in refactored_files:
            file_path = project_root / file_rel_path
            if not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source_code = f.read()

                tree = ast.parse(source_code)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        metrics = analyze_function_complexity(file_path, func_name)

                        if metrics["found"]:
                            # Flag functions with extreme complexity
                            if (
                                metrics["cyclomatic"] > 30
                                or metrics["cognitive"] > 50
                                or metrics["nesting"] > 6
                            ):
                                extreme_functions.append(
                                    f"{file_rel_path}:{func_name} "
                                    f"(cyclomatic={metrics['cyclomatic']}, "
                                    f"cognitive={metrics['cognitive']}, "
                                    f"nesting={metrics['nesting']})"
                                )

            except Exception:
                # Skip files that can't be parsed
                pass

        assert not extreme_functions, (
            f"Found functions with extreme complexity after Phase 1 refactoring:\n"
            + "\n".join(f"  - {f}" for f in extreme_functions)
        )


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
