"""Central tool registration for MCP server."""

from mcp.server.fastmcp import FastMCP

from ast_grep_mcp.features.complexity.tools import register_complexity_tools
from ast_grep_mcp.features.deduplication.tools import register_deduplication_tools
from ast_grep_mcp.features.documentation.tools import register_documentation_tools
from ast_grep_mcp.features.quality.tools import register_quality_tools
from ast_grep_mcp.features.refactoring.tools import extract_function, rename_symbol
from ast_grep_mcp.features.rewrite.tools import register_rewrite_tools
from ast_grep_mcp.features.schema.tools import register_schema_tools
from ast_grep_mcp.features.search.tools import register_search_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register all MCP tools from all features.

    This is the central registration point for all tools in the system.
    Tools are organized by feature and registered in order:
    1. Search (4 tools after consolidation)
    2. Rewrite (3 tools)
    3. Refactoring (2 tools: extract_function, rename_symbol)
    4. Deduplication (4 tools)
    5. Complexity (2 tools)
    6. Quality (4 tools - detect_smells, create_rule, list_templates, enforce_rules)
    7. Schema.org (8 tools)
    8. Documentation (5 tools - generate_docstrings, generate_readme_sections,
       generate_api_docs, generate_changelog, sync_documentation)

    Total: 32 tools
    """
    register_search_tools(mcp)
    register_rewrite_tools(mcp)
    mcp.tool()(extract_function)
    mcp.tool()(rename_symbol)
    register_deduplication_tools(mcp)
    register_complexity_tools(mcp)
    register_quality_tools(mcp)
    register_schema_tools(mcp)
    register_documentation_tools(mcp)
