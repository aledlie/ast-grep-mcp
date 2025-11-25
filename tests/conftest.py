"""Shared pytest fixtures for ast-grep-mcp test suite.

This module provides common fixtures used across unit and integration tests,
reducing duplication and standardizing test setup.
"""

import tempfile
import shutil
from pathlib import Path
from typing import Generator, Any
import pytest

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Cache Management Fixtures
# ============================================================================

@pytest.fixture
def clean_cache():
    """Clear the query cache before each test to avoid interference.

    This fixture is automatically used by tests that need cache isolation.
    """
    import main
    if main._query_cache is not None:
        main._query_cache.cache.clear()
    yield
    # Optionally clear after test too
    if main._query_cache is not None:
        main._query_cache.cache.clear()


@pytest.fixture
def query_cache():
    """Provide a fresh query cache instance.

    Returns:
        QueryCache instance for testing
    """
    from main import QueryCache
    cache = QueryCache()
    yield cache
    cache.cache.clear()


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test isolation.

    Automatically cleaned up after test completion.

    Yields:
        str: Path to temporary directory
    """
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def temp_project_dir(temp_dir) -> str:
    """Create a temporary project directory with standard structure.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        str: Path to project root
    """
    project = Path(temp_dir) / "project"
    project.mkdir()

    # Create common directories
    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / "docs").mkdir()

    return str(project)


# ============================================================================
# Sample Code Fixtures
# ============================================================================

@pytest.fixture
def sample_python_code() -> str:
    """Provide sample Python code for testing.

    Returns:
        str: Sample Python function code
    """
    return """def calculate_sum(a, b):
    \"\"\"Calculate the sum of two numbers.\"\"\"
    result = a + b
    return result
"""


@pytest.fixture
def sample_duplicate_code() -> tuple[str, str]:
    """Provide two similar code blocks for duplication testing.

    Returns:
        tuple: (code1, code2) - Similar code blocks with variations
    """
    code1 = """def process_user_data(user_id):
    user = fetch_user(user_id)
    if user.is_active:
        return user.name
    return None
"""

    code2 = """def process_admin_data(admin_id):
    admin = fetch_user(admin_id)
    if admin.is_active:
        return admin.name
    return None
"""

    return code1, code2


@pytest.fixture
def sample_complex_code() -> str:
    """Provide complex code for complexity analysis testing.

    Returns:
        str: Code with high cyclomatic complexity
    """
    return """def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            if z > 0:
                return x + z
            else:
                return x
    else:
        if y > 0:
            if z > 0:
                return y + z
            else:
                return y
        else:
            return z if z > 0 else 0
"""


# ============================================================================
# Mock MCP Server Fixtures
# ============================================================================

@pytest.fixture
def mock_mcp_instance():
    """Provide a mock MCP server instance for testing tools.

    Returns:
        MockFastMCP: Mock MCP instance
    """
    from mcp.server.fastmcp import FastMCP

    class MockFastMCP:
        """Mock FastMCP instance for testing."""
        def __init__(self):
            self.tools = {}
            self._resources = []
            self._prompts = []

        def tool(self):
            """Decorator for registering tools."""
            def decorator(func):
                self.tools[func.__name__] = func
                return func
            return decorator

        def resource(self, uri: str):
            """Decorator for registering resources."""
            def decorator(func):
                self._resources.append((uri, func))
                return func
            return decorator

        def prompt(self):
            """Decorator for registering prompts."""
            def decorator(func):
                self._prompts.append(func)
                return func
            return decorator

    return MockFastMCP()


# ============================================================================
# File Creation Helpers
# ============================================================================

@pytest.fixture
def create_test_file(temp_dir):
    """Factory fixture for creating test files.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Callable: Function to create files with content
    """
    def _create_file(filename: str, content: str, subdir: str = "") -> Path:
        """Create a file with given content in temp directory.

        Args:
            filename: Name of file to create
            content: Content to write
            subdir: Optional subdirectory path

        Returns:
            Path: Path to created file
        """
        if subdir:
            dir_path = Path(temp_dir) / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            file_path = dir_path / filename
        else:
            file_path = Path(temp_dir) / filename

        file_path.write_text(content)
        return file_path

    return _create_file


# ============================================================================
# Deduplication Fixtures
# ============================================================================

@pytest.fixture
def sample_duplication_matches() -> list[dict]:
    """Provide sample code matches for deduplication testing.

    Returns:
        list: Sample match dictionaries
    """
    return [
        {
            "text": "def foo():\n    return 1",
            "file": "file1.py",
            "start_line": 1,
            "end_line": 2
        },
        {
            "text": "def bar():\n    return 1",
            "file": "file2.py",
            "start_line": 1,
            "end_line": 2
        },
        {
            "text": "def baz():\n    return 2",
            "file": "file3.py",
            "start_line": 1,
            "end_line": 2
        }
    ]


# ============================================================================
# Schema.org Fixtures
# ============================================================================

@pytest.fixture
def mock_schema_client():
    """Provide a mock Schema.org client for testing.

    Returns:
        Mock client with basic schema data
    """
    class MockSchemaClient:
        """Mock SchemaOrgClient for testing."""
        def __init__(self):
            self.types = {
                "Thing": {
                    "label": "Thing",
                    "comment": "The most generic type of item."
                },
                "Person": {
                    "label": "Person",
                    "comment": "A person (alive, dead, undead, or fictional).",
                    "subClassOf": "Thing"
                }
            }

        def get_schema_type(self, type_name: str) -> dict:
            return self.types.get(type_name, {})

        def search_schemas(self, query: str) -> list:
            return [t for t in self.types.keys() if query.lower() in t.lower()]

    return MockSchemaClient()


# ============================================================================
# Auto-use Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_module_state():
    """Reset module-level state between tests (auto-used).

    This fixture runs automatically before each test to ensure clean state.
    """
    # Clear any global caches or state
    yield
    # Cleanup after test


# ============================================================================
# Parametrize Helpers
# ============================================================================

# Common language parameter sets
SUPPORTED_LANGUAGES = ["python", "javascript", "typescript", "java", "go", "rust"]

@pytest.fixture(params=SUPPORTED_LANGUAGES)
def language(request):
    """Parametrize tests across all supported languages.

    Usage:
        def test_something(language):
            # Test runs once per language
            assert language in SUPPORTED_LANGUAGES
    """
    return request.param


# Common similarity thresholds
SIMILARITY_THRESHOLDS = [0.7, 0.8, 0.85, 0.9, 0.95]

@pytest.fixture(params=SIMILARITY_THRESHOLDS)
def similarity_threshold(request):
    """Parametrize tests across common similarity thresholds."""
    return request.param


# Fixtures for class-based deduplication components
@pytest.fixture
def duplication_detector():
    """Provide DuplicationDetector instance."""
    from ast_grep_mcp.features.deduplication.detector import DuplicationDetector
    from ast_grep_mcp.core.executor import run_ast_grep
    return DuplicationDetector(run_ast_grep)


@pytest.fixture
def pattern_analyzer():
    """Provide PatternAnalyzer instance."""
    from ast_grep_mcp.features.deduplication.analyzer import PatternAnalyzer
    from ast_grep_mcp.core.executor import run_ast_grep
    return PatternAnalyzer(run_ast_grep)


@pytest.fixture
def code_generator():
    """Provide CodeGenerator instance."""
    from ast_grep_mcp.features.deduplication.generator import CodeGenerator
    return CodeGenerator()


@pytest.fixture
def duplication_ranker():
    """Provide DuplicationRanker instance."""
    from ast_grep_mcp.features.deduplication.ranker import DuplicationRanker
    return DuplicationRanker()


@pytest.fixture
def recommendation_engine():
    """Provide RecommendationEngine instance."""
    from ast_grep_mcp.features.deduplication.recommendations import RecommendationEngine
    return RecommendationEngine()
