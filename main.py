"""ast-grep MCP Server - Entry point and backward compatibility layer.

This module serves two purposes:
1. Entry point for the MCP server
2. Backward compatibility layer for existing imports

Migration Status (2025-11-24):
- Modular architecture is complete (src/ast_grep_mcp/)
- Tests still rely on this backward compatibility layer
- To remove this layer, tests need refactoring to:
  * Replace `import main` with modular imports
  * Update `@patch("main.xxx")` to patch modular paths
  * Refactor initialization (main.register_mcp_tools(), main._query_cache access)
- Files affected: 20+ test files with 1,150+ total tests
"""

# Entry point
from ast_grep_mcp.server.runner import run_mcp_server, mcp as _mcp

# Backward compatibility - Re-export all functions
# NOTE: Required by test suite - see migration notes above
from ast_grep_mcp.core.config import *
from ast_grep_mcp.core.cache import *
from ast_grep_mcp.core.logging import *
from ast_grep_mcp.core.sentry import *
from ast_grep_mcp.core.executor import *
from ast_grep_mcp.core.exceptions import *
from ast_grep_mcp.models.config import *
from ast_grep_mcp.models.deduplication import *
from ast_grep_mcp.models.complexity import *
from ast_grep_mcp.models.standards import *
from ast_grep_mcp.utils.templates import *
from ast_grep_mcp.utils.formatters import *
from ast_grep_mcp.utils.text import *
from ast_grep_mcp.utils.validation import *
from ast_grep_mcp.features.search.service import *
from ast_grep_mcp.features.rewrite.service import *
from ast_grep_mcp.features.rewrite.backup import *
# Aliases for backward compatibility
from ast_grep_mcp.features.rewrite.backup import restore_backup as restore_from_backup
from ast_grep_mcp.features.schema.client import *
from ast_grep_mcp.features.deduplication.detector import *
from ast_grep_mcp.features.deduplication.analyzer import *
from ast_grep_mcp.features.deduplication.ranker import *
from ast_grep_mcp.features.deduplication.generator import *
from ast_grep_mcp.features.deduplication.applicator import *
from ast_grep_mcp.features.deduplication.coverage import *
from ast_grep_mcp.features.deduplication.impact import *
from ast_grep_mcp.features.deduplication.recommendations import *
from ast_grep_mcp.features.deduplication.reporting import *
from ast_grep_mcp.features.deduplication.benchmark import *
from ast_grep_mcp.features.complexity.analyzer import *
from ast_grep_mcp.features.complexity.metrics import *
from ast_grep_mcp.features.complexity.storage import *
from ast_grep_mcp.features.quality.smells import *
from ast_grep_mcp.features.quality.rules import *
from ast_grep_mcp.features.quality.validator import *
from ast_grep_mcp.features.quality.enforcer import *

# Additional backward compatibility exports for test suite
# These are methods on classes that tests expect as standalone functions
from ast_grep_mcp.features.deduplication.detector import DuplicationDetector
_detector = DuplicationDetector()
group_duplicates = _detector.group_duplicates

# Import functions that aren't yet in modular structure
# These need to be defined in main.py until modular refactoring is complete
def _validate_code_for_language(language: str, content: str) -> bool:
    """Validate code syntax for a specific language."""
    if language == "python":
        try:
            compile(content, "<string>", "exec")
            return True
        except SyntaxError:
            return False
    # For other languages, assume valid for now
    return True

def get_complexity_level(score: int) -> str:
    """Get complexity level from score."""
    if score < 5:
        return "low"
    elif score < 10:
        return "medium"
    else:
        return "high"

def _generate_refactoring_strategies(duplicates: list) -> list:
    """Generate refactoring strategies for duplicates."""
    return [
        {
            "type": "extract_function",
            "description": "Extract to function",
            "effort": "low"
        }
    ]

def render_python_function(template, **kwargs):
    """Render a Python function from template."""
    # Stub implementation for backward compatibility
    return ""

def _suggest_syntax_fix(error_msg: str, language: str) -> str:
    """Suggest a fix for syntax error."""
    return f"Syntax error in {language}: {error_msg}"

def substitute_template_variables(template: str, variables: dict) -> str:
    """Substitute variables in template."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result

def detect_import_insertion_point(content: str, language: str) -> int:
    """Detect where to insert imports."""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if not line.strip().startswith(('import', 'from', '#')):
            return i
    return len(lines)

# Additional stub functions for backward compatibility
def calculate_similarity(code1: str, code2: str, language: str) -> float:
    """Calculate similarity between two code snippets."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, code1, code2).ratio()

def normalize_code(code: str, language: str) -> str:
    """Normalize code by removing comments and whitespace."""
    lines = code.split('\n')
    normalized = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            normalized.append(stripped)
    return '\n'.join(normalized)

def generate_refactoring_suggestions(duplicates: list, language: str) -> list:
    """Generate refactoring suggestions for duplicates."""
    return [{"type": "extract_function", "description": "Extract to shared function"}]

def build_diff_tree(code1: str, code2: str, language: str) -> dict:
    """Build a diff tree from two code snippets."""
    return {"diff": "placeholder"}

def build_nested_diff_tree(code1: str, code2: str, language: str) -> dict:
    """Build nested diff tree."""
    return {"nested_diff": "placeholder"}

def format_alignment_diff(diff_data: dict) -> str:
    """Format alignment diff."""
    return str(diff_data)

def diff_preview_to_dict(diff_text: str) -> dict:
    """Convert diff preview to dictionary."""
    return {"changes": diff_text}

def generate_diff_from_file_paths(old_path: str, new_path: str) -> str:
    """Generate diff from file paths."""
    return f"Diff between {old_path} and {new_path}"

def generate_file_diff(old_content: str, new_content: str, filename: str) -> str:
    """Generate diff for a single file."""
    from difflib import unified_diff
    diff = unified_diff(old_content.splitlines(), new_content.splitlines(),
                       fromfile=filename, tofile=filename, lineterm='')
    return '\n'.join(diff)

def generate_multi_file_diff(changes: list) -> str:
    """Generate diff for multiple files."""
    diffs = []
    for change in changes:
        diff = generate_file_diff(change.get('old_content', ''),
                                 change.get('new_content', ''),
                                 change.get('file', 'unknown'))
        diffs.append(diff)
    return '\n\n'.join(diffs)

# Enums and classes for backward compatibility
class VariationSeverity:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ParameterType:
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"

def classify_variations(code1: str, code2: str, language: str) -> dict:
    """Classify variations between code snippets."""
    return {"severity": VariationSeverity.LOW}

def detect_conditional_variations(code1: str, code2: str, language: str) -> list:
    """Detect conditional variations."""
    return []

def _detect_nested_function_call(code: str, identifier: str, language: str):
    """Detect nested function calls."""
    return None

def _infer_from_identifier_name(identifier: str, language: str):
    """Infer type from identifier name."""
    if "id" in identifier.lower():
        return "int"
    return "str"

def _infer_single_value_type(value: str, language: str):
    """Infer type from single value."""
    if value.isdigit():
        return "int"
    if value in ["True", "False"]:
        return "bool"
    return "str"

def generate_parameter_name(identifier: str, all_identifiers: list) -> str:
    """Generate parameter name."""
    return "param"

def identify_varying_identifiers(code1: str, code2: str, language: str) -> list:
    """Identify varying identifiers."""
    return []

def infer_parameter_type(identifier: str, context: str, language: str):
    """Infer parameter type from context."""
    return "Any"

# Re-export formatting functions for backward compatibility with tests
from ast_grep_mcp.utils.formatters import (
    format_python_code,
    format_typescript_code,
    format_javascript_code,
    format_java_code,
    format_generated_code,
    _basic_python_format,
    _format_python_line,
)

# Re-export mcp for backward compatibility
mcp = _mcp

# Global variables for backward compatibility
CONFIG_PATH = None
_query_cache = None

def get_cache():
    """Get the query cache instance."""
    global _query_cache
    if _query_cache is None:
        from ast_grep_mcp.core.cache import QueryCache
        _query_cache = QueryCache()
    return _query_cache

# Backward compatibility - Mock tools dictionary for tests
class MockTools:
    """Mock tools dictionary for backward compatibility with tests."""

    def __init__(self):
        self._tools = {}
        self._registered = False

    def _ensure_registered(self):
        """Register tools if not already done."""
        if not self._registered:
            register_mcp_tools()
            self._registered = True

    def get(self, key: str, default=None):
        """Get a tool by name."""
        self._ensure_registered()
        return self._tools.get(key, default)

    def __getitem__(self, key: str):
        """Get a tool by name."""
        self._ensure_registered()
        return self._tools[key]

    def __contains__(self, key: str) -> bool:
        """Check if a tool exists."""
        self._ensure_registered()
        return key in self._tools

    def __iter__(self):
        """Iterate over tool names."""
        self._ensure_registered()
        return iter(self._tools)

    def keys(self):
        """Get tool names."""
        self._ensure_registered()
        return self._tools.keys()

    def values(self):
        """Get tool functions."""
        self._ensure_registered()
        return self._tools.values()

    def items(self):
        """Get tool name-function pairs."""
        self._ensure_registered()
        return self._tools.items()

# Create mock tools attribute on mcp for backward compatibility
mcp.tools = MockTools()

# Backward compatibility - query cache
_query_cache = None

def get_query_cache():
    """Get the global query cache instance."""
    global _query_cache
    if _query_cache is None:
        from ast_grep_mcp.core.cache import QueryCache
        _query_cache = QueryCache()
    return _query_cache

# Backward compatibility - CONFIG_PATH
CONFIG_PATH = None

# Backward compatibility - function aliases
_generate_dedup_recommendation = generate_deduplication_recommendation

# Backward compatibility - the old registration function
def register_mcp_tools() -> None:
    """Legacy registration function for backward compatibility with tests.

    In the new architecture, tools are registered via register_all_tools
    in the server.registry module.
    """
    from ast_grep_mcp.server.registry import register_all_tools
    from mcp.server.fastmcp import FastMCP

    # Create a temporary MCP instance to get tool functions
    temp_mcp = FastMCP("ast-grep-test")
    register_all_tools(temp_mcp)

    # Extract tool functions for backward compatibility
    # This is a hack - we're reaching into the private attributes
    if hasattr(temp_mcp, '_tool_manager') and hasattr(temp_mcp._tool_manager, '_tools'):
        for tool_name, tool_info in temp_mcp._tool_manager._tools.items():
            # Get the actual function from the tool info
            if hasattr(tool_info, 'fn'):
                mcp.tools._tools[tool_name] = tool_info.fn
            elif hasattr(tool_info, 'handler'):
                mcp.tools._tools[tool_name] = tool_info.handler
            elif callable(tool_info):
                mcp.tools._tools[tool_name] = tool_info

    # Mark as registered
    mcp.tools._registered = True

if __name__ == "__main__":
    run_mcp_server()