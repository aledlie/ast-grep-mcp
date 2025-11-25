"""Central tool registration for MCP server."""

from mcp.server.fastmcp import FastMCP

from ast_grep_mcp.features.complexity.tools import register_complexity_tools
from ast_grep_mcp.features.deduplication.tools import register_deduplication_tools
from ast_grep_mcp.features.quality.tools import register_quality_tools
from ast_grep_mcp.features.rewrite.tools import register_rewrite_tools
from ast_grep_mcp.features.schema.tools import register_schema_tools
from ast_grep_mcp.features.search.tools import register_search_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register all MCP tools from all features.

    This is the central registration point for all tools in the system.
    Tools are organized by feature and registered in order:
    1. Search (4 tools after consolidation)
    2. Rewrite (3 tools)
    3. Deduplication (4 tools)
    4. Complexity (2 tools)
    5. Quality (4 tools - detect_smells, create_rule, list_templates, enforce_rules)
    6. Schema.org (8 tools)

    Total: 25 tools (after consolidation)
    """
    register_search_tools(mcp)
    register_rewrite_tools(mcp)
    register_deduplication_tools(mcp)
    register_complexity_tools(mcp)
    register_quality_tools(mcp)
    register_schema_tools(mcp)
