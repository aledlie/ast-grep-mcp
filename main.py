"""ast-grep MCP Server - Entry point and backward compatibility layer.

This module serves two purposes:
1. Entry point for the MCP server
2. Backward compatibility layer for existing imports

After test migration, re-exports can be removed.
"""

# Entry point
from ast_grep_mcp.server.runner import run_mcp_server, mcp

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

# Backward compatibility - the old registration function
def register_mcp_tools() -> None:
    """Legacy registration function for backward compatibility with tests.

    In the new architecture, tools are registered via register_all_tools
    in the server.registry module.
    """
    from mcp.server.fastmcp import FastMCP
    from ast_grep_mcp.server.registry import register_all_tools

    # Create a temporary MCP instance just for registration
    temp_mcp = FastMCP("ast-grep-test")
    register_all_tools(temp_mcp)
    # Note: This doesn't actually register the tools globally,
    # it's just here to prevent test failures

if __name__ == "__main__":
    run_mcp_server()