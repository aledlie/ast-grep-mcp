"""ast-grep MCP Server - Entry point and backward compatibility layer.

This module serves two purposes:
1. Entry point for the MCP server
2. Backward compatibility layer for existing imports

After test migration, re-exports can be removed.
"""

# Entry point
from ast_grep_mcp.server.runner import run_mcp_server, mcp as _mcp

# Backward compatibility - Re-export all functions
# TODO: Remove after test migration
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

# Re-export mcp for backward compatibility
mcp = _mcp

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