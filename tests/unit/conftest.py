"""Shared pytest fixtures for unit tests.

This module provides reusable fixtures for all unit test modules, including:
- Tool access fixtures (apply_deduplication_tool, rewrite_code_tool, etc.)
- File setup fixtures (simple_test_files, backup_test_files, orchestration_test_files)
- Factory fixtures (refactoring_plan_factory)
"""

import os
from typing import Any, Dict
from unittest.mock import patch

import pytest

# Mock FastMCP before importing main
class MockFastMCP:
    """Mock FastMCP class for testing."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: Dict[str, Any] = {}
        self._registered = False

    def tool(self, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs: Any) -> None:
        pass

    def get(self, name: str) -> Any:
        """Get a tool by name (for backward compatibility)."""
        return self.tools.get(name)


def mock_field(**kwargs: Any) -> Any:
    """Mock pydantic Field function."""
    return kwargs.get("default")


# Tool Access Fixtures

@pytest.fixture(scope="module")
def mcp_main():
    """Import main module with mocked decorators.

    This fixture must be module-scoped to ensure main is imported once
    and tools are registered once for all tests in the module.
    """
    with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
        with patch("pydantic.Field", mock_field):
            import main
            main.register_mcp_tools()
            return main


@pytest.fixture(scope="module")
def apply_deduplication_tool(mcp_main):
    """Get apply_deduplication tool function."""
    tool = mcp_main.mcp.tools.get("apply_deduplication")
    assert tool is not None, "apply_deduplication tool not registered"
    return tool


@pytest.fixture(scope="module")
def find_duplication_tool(mcp_main):
    """Get find_duplication tool function."""
    tool = mcp_main.mcp.tools.get("find_duplication")
    assert tool is not None, "find_duplication tool not registered"
    return tool


@pytest.fixture(scope="module")
def analyze_deduplication_candidates_tool(mcp_main):
    """Get analyze_deduplication_candidates tool function."""
    tool = mcp_main.mcp.tools.get("analyze_deduplication_candidates")
    assert tool is not None, "analyze_deduplication_candidates tool not registered"
    return tool


@pytest.fixture(scope="module")
def benchmark_deduplication_tool(mcp_main):
    """Get benchmark_deduplication tool function."""
    tool = mcp_main.mcp.tools.get("benchmark_deduplication")
    assert tool is not None, "benchmark_deduplication tool not registered"
    return tool


@pytest.fixture(scope="module")
def rewrite_code_tool(mcp_main):
    """Get rewrite_code tool function."""
    tool = mcp_main.mcp.tools.get("rewrite_code")
    assert tool is not None, "rewrite_code tool not registered"
    return tool


@pytest.fixture(scope="module")
def list_backups_tool(mcp_main):
    """Get list_backups tool function."""
    tool = mcp_main.mcp.tools.get("list_backups")
    assert tool is not None, "list_backups tool not registered"
    return tool


@pytest.fixture(scope="module")
def rollback_rewrite_tool(mcp_main):
    """Get rollback_rewrite tool function."""
    tool = mcp_main.mcp.tools.get("rollback_rewrite")
    assert tool is not None, "rollback_rewrite tool not registered"
    return tool


# File Setup Fixtures

@pytest.fixture
def project_folder(tmp_path):
    """Temporary project folder for testing.

    Uses pytest's tmp_path fixture which automatically creates a unique
    temporary directory for each test and cleans it up afterward.

    Returns:
        pathlib.Path: Path to temporary project folder
    """
    return tmp_path


@pytest.fixture
def simple_test_files(project_folder):
    """Create simple test files for basic testing.

    Creates two simple Python files with minimal content, suitable for
    tests that don't need complex file structures.

    Args:
        project_folder: Temporary project folder fixture

    Returns:
        dict: Dictionary with file paths:
            - file1: Path to sample.py
            - file2: Path to sample2.py
    """
    file1 = project_folder / "sample.py"
    file2 = project_folder / "sample2.py"
    file1.write_text("def hello():\n    print('hello')\n")
    file2.write_text("def world():\n    print('world')\n")
    return {
        "file1": str(file1),
        "file2": str(file2),
    }


@pytest.fixture
def backup_test_files(project_folder):
    """Create test files with original content tracking for backup tests.

    Creates two Python files and tracks their original content, suitable for
    tests that need to verify backup and rollback functionality.

    Args:
        project_folder: Temporary project folder fixture

    Returns:
        dict: Dictionary with file paths and original content:
            - file1: Path to file1.py
            - file2: Path to file2.py
            - original_content1: Original content of file1
            - original_content2: Original content of file2
    """
    original_content1 = "def func1():\n    pass\n"
    original_content2 = "def func2():\n    pass\n"

    file1 = project_folder / "file1.py"
    file2 = project_folder / "file2.py"
    file1.write_text(original_content1)
    file2.write_text(original_content2)

    return {
        "file1": str(file1),
        "file2": str(file2),
        "original_content1": original_content1,
        "original_content2": original_content2,
    }


@pytest.fixture
def orchestration_test_files(project_folder):
    """Create test files in subdirectory with complex content.

    Creates a subdirectory structure with Python files containing imports
    and function definitions, suitable for testing multi-file orchestration.

    Args:
        project_folder: Temporary project folder fixture

    Returns:
        dict: Dictionary with directory and file information:
            - src_dir: Path to src subdirectory
            - file1: Path to src/file1.py
            - file2: Path to src/file2.py
            - original_content1: Original content of file1
            - original_content2: Original content of file2
    """
    src_dir = project_folder / "src"
    src_dir.mkdir()

    original_content1 = "import os\n\ndef func1():\n    return os.getcwd()\n"
    original_content2 = "import os\n\ndef func2():\n    return os.getcwd()\n"

    file1 = src_dir / "file1.py"
    file2 = src_dir / "file2.py"
    file1.write_text(original_content1)
    file2.write_text(original_content2)

    return {
        "src_dir": str(src_dir),
        "file1": str(file1),
        "file2": str(file2),
        "original_content1": original_content1,
        "original_content2": original_content2,
    }


# Factory Fixtures

@pytest.fixture
def refactoring_plan_factory():
    """Factory for creating refactoring plans with various configurations.

    This factory fixture creates refactoring plans with flexible options,
    reducing duplication of plan creation logic across test modules.

    Returns:
        function: Factory function that creates refactoring plans

    Example:
        >>> plan = refactoring_plan_factory(
        ...     files=["file1.py", "file2.py"],
        ...     new_contents=["# new content 1", "# new content 2"],
        ...     strategy="extract_function"
        ... )
    """
    def _create_plan(
        files: list[str],
        new_contents: list[str] = None,
        strategy: str = "extract_function",
        extracted_function: str = "",
        extract_to_file: str = "",
        function_name: str = "extracted_func",
        language: str = "python"
    ) -> Dict[str, Any]:
        """Create a refactoring plan.

        Args:
            files: List of file paths to refactor
            new_contents: List of new file contents (one per file)
            strategy: Refactoring strategy (default: "extract_function")
            extracted_function: Code for extracted function
            extract_to_file: File to extract function to
            function_name: Name of extracted function
            language: Programming language (default: "python")

        Returns:
            dict: Refactoring plan dictionary
        """
        if new_contents is None:
            new_contents = [f"# Modified: {f}\n" for f in files]

        replacements = {}
        for f, content in zip(files, new_contents):
            replacements[f] = {
                "new_content": content,
                "changes": [{"line": 1, "old": "original", "new": "modified"}]
            }

        plan = {
            "strategy": strategy,
            "files_affected": files,
            "generated_code": {
                "extracted_function": extracted_function,
                "replacements": replacements
            },
            "language": language
        }

        if extract_to_file:
            plan["generated_code"]["extract_to_file"] = extract_to_file
            plan["generated_code"]["function_name"] = function_name

        return plan

    return _create_plan
