"""Schema.org feature MCP tool definitions."""

import time
from typing import Any, Dict, List, Optional

import sentry_sdk
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.constants import DisplayDefaults, FormattingDefaults
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.schema.client import get_schema_org_client
from ast_grep_mcp.features.schema.enhancement_service import analyze_entity_graph


def _log_tool_error(logger: Any, tool: str, e: Exception, elapsed: float, extras: Dict[str, Any]) -> None:
    logger.error(
        "tool_failed",
        tool=tool,
        execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION),
        error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
        status="failed",
    )
    sentry_sdk.capture_exception(
        e,
        extras={"tool": tool, "execution_time_seconds": round(elapsed, FormattingDefaults.ROUNDING_PRECISION), **extras},
    )


async def get_schema_type_tool(type_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a schema.org type.
    Returns the type's name, description, URL, parent types, and metadata.

    Args:
        type_name: The schema.org type name (e.g., 'Person', 'Organization', 'Article')

    Returns:
        Dictionary with type details including properties and parent types

    Example:
        get_schema_type_tool('Person') returns details about the Person type
    """
    logger = get_logger("tool.get_schema_type")
    start_time = time.time()
    logger.info("tool_invoked", tool="get_schema_type", type_name=type_name)
    try:
        result = await get_schema_org_client().get_schema_type(type_name)
        elapsed = time.time() - start_time
        logger.info(
            "tool_completed", tool="get_schema_type",
            execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION), status="success"
        )
        return result
    except Exception as e:
        _log_tool_error(logger, "get_schema_type", e, time.time() - start_time, {"type_name": type_name})
        raise


async def search_schemas_tool(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for schema.org types by keyword.
    Searches through type names and descriptions, returns matching types sorted by relevance.

    Args:
        query: Search query to find schema types
        limit: Maximum number of results to return (1-100)

    Returns:
        List of matching schema types

    Example:
        search_schemas_tool('blog') finds types like BlogPosting, Blog, etc.
    """
    logger = get_logger("tool.search_schemas")
    start_time = time.time()
    logger.info("tool_invoked", tool="search_schemas", query=query, limit=limit)
    try:
        results = await get_schema_org_client().search_schemas(query, limit)
        elapsed = time.time() - start_time
        logger.info(
            "tool_completed", tool="search_schemas",
            execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION),
            result_count=len(results), status="success"
        )
        return results
    except Exception as e:
        _log_tool_error(logger, "search_schemas", e, time.time() - start_time, {"query": query, "limit": limit})
        raise


async def get_type_hierarchy_tool(type_name: str) -> Dict[str, Any]:
    """
    Get the inheritance hierarchy for a schema.org type.
    Returns the type's parent types (super types) and child types (sub types).

    Args:
        type_name: The schema.org type name

    Returns:
        Dictionary with parent and child type information

    Example:
        get_type_hierarchy_tool('NewsArticle') shows inheritance from Article, CreativeWork, etc.
    """
    logger = get_logger("tool.get_type_hierarchy")
    start_time = time.time()
    logger.info("tool_invoked", tool="get_type_hierarchy", type_name=type_name)
    try:
        result = await get_schema_org_client().get_type_hierarchy(type_name)
        elapsed = time.time() - start_time
        logger.info(
            "tool_completed", tool="get_type_hierarchy",
            execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION), status="success"
        )
        return result
    except Exception as e:
        _log_tool_error(logger, "get_type_hierarchy", e, time.time() - start_time, {"type_name": type_name})
        raise


async def get_type_properties_tool(type_name: str, include_inherited: bool = True) -> List[Dict[str, Any]]:
    """
    Get all properties available for a schema.org type.
    Returns property names, descriptions, and expected value types.

    Args:
        type_name: The schema.org type name
        include_inherited: Include properties inherited from parent types

    Returns:
        List of property definitions

    Example:
        get_type_properties_tool('Organization') returns properties like name, url, address, etc.
    """
    logger = get_logger("tool.get_type_properties")
    start_time = time.time()
    logger.info("tool_invoked", tool="get_type_properties", type_name=type_name, include_inherited=include_inherited)
    try:
        results = await get_schema_org_client().get_type_properties(type_name, include_inherited)
        elapsed = time.time() - start_time
        logger.info(
            "tool_completed", tool="get_type_properties",
            execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION),
            property_count=len(results), status="success"
        )
        return results
    except Exception as e:
        _log_tool_error(
            logger, "get_type_properties", e, time.time() - start_time,
            {"type_name": type_name, "include_inherited": include_inherited}
        )
        raise


async def generate_schema_example_tool(type_name: str, custom_properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate an example JSON-LD structured data for a schema.org type.
    Creates a valid schema.org JSON-LD object with common properties and any custom values provided.

    Args:
        type_name: The schema.org type name
        custom_properties: Custom property values to include in the example

    Returns:
        Dictionary containing JSON-LD example

    Example:
        generate_schema_example_tool('Recipe', {'name': 'Chocolate Cake', 'prepTime': 'PT30M'})
    """
    logger = get_logger("tool.generate_schema_example")
    start_time = time.time()
    logger.info("tool_invoked", tool="generate_schema_example", type_name=type_name)
    try:
        result = await get_schema_org_client().generate_example(type_name, custom_properties)
        elapsed = time.time() - start_time
        logger.info(
            "tool_completed", tool="generate_schema_example",
            execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION), status="success"
        )
        return result
    except Exception as e:
        _log_tool_error(
            logger, "generate_schema_example", e, time.time() - start_time,
            {"type_name": type_name, "has_custom_properties": custom_properties is not None}
        )
        raise


def generate_entity_id_tool(base_url: str, entity_type: str, entity_slug: Optional[str] = None) -> str:
    """
    Generate a proper @id value following Schema.org and SEO best practices.

    Creates stable, unique identifiers for entities that can be referenced across your knowledge graph.
    Based on best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs

    Args:
        base_url: The canonical URL (e.g., 'https://example.com')
        entity_type: The Schema.org type (e.g., 'Organization', 'Person')
        entity_slug: Optional URL slug for specific entity instances

    Returns:
        Generated @id string

    Examples:
        - generate_entity_id_tool('https://example.com', 'Organization')
          → 'https://example.com/#organization'
        - generate_entity_id_tool('https://example.com', 'Product', 'products/widget-a')
          → 'https://example.com/products/widget-a#product'
    """
    logger = get_logger("tool.generate_entity_id")
    start_time = time.time()
    logger.info("tool_invoked", tool="generate_entity_id", base_url=base_url, entity_type=entity_type)
    try:
        result = get_schema_org_client().generate_entity_id(base_url, entity_type, entity_slug)
        elapsed = time.time() - start_time
        logger.info(
            "tool_completed", tool="generate_entity_id",
            execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION),
            generated_id=result, status="success"
        )
        return result
    except Exception as e:
        _log_tool_error(
            logger, "generate_entity_id", e, time.time() - start_time,
            {"base_url": base_url, "entity_type": entity_type, "has_slug": entity_slug is not None}
        )
        raise


def validate_entity_id_tool(entity_id: str) -> Dict[str, Any]:
    """
    Validate an @id value against Schema.org and SEO best practices.

    Checks for common issues and provides actionable suggestions for improvement.
    Based on best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs

    Args:
        entity_id: The @id value to validate

    Returns:
        Dictionary with validation results:
        - valid: Whether the @id follows all best practices
        - warnings: List of issues found
        - suggestions: Specific improvements to make
        - best_practices: Key principles to follow

    Example:
        validate_entity_id_tool('https://example.com/#organization')
        → { "valid": true, "warnings": [], "suggestions": [] }
    """
    logger = get_logger("tool.validate_entity_id")
    start_time = time.time()
    logger.info("tool_invoked", tool="validate_entity_id", entity_id=entity_id)
    try:
        result = get_schema_org_client().validate_entity_id(entity_id)
        elapsed = time.time() - start_time
        logger.info(
            "tool_completed", tool="validate_entity_id",
            execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION),
            is_valid=result["valid"], warning_count=len(result["warnings"]), status="success"
        )
        return result
    except Exception as e:
        _log_tool_error(logger, "validate_entity_id", e, time.time() - start_time, {"entity_id": entity_id})
        raise


async def build_entity_graph_tool(entities: List[Dict[str, Any]], base_url: str) -> Dict[str, Any]:
    """
    Build a knowledge graph of related entities with proper @id references.

    Args:
        entities: List of entity definitions (type, slug, id_fragment, properties, relationships)
        base_url: Base canonical URL for generating @id values

    Returns:
        Complete JSON-LD @graph with all entities properly connected via @id references
    """
    logger = get_logger("tool.build_entity_graph")
    start_time = time.time()
    logger.info("tool_invoked", tool="build_entity_graph", entity_count=len(entities), base_url=base_url)
    try:
        result = await get_schema_org_client().build_entity_graph(entities, base_url)
        elapsed = time.time() - start_time
        logger.info(
            "tool_completed", tool="build_entity_graph",
            execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION),
            entity_count=len(result.get("@graph", [])), status="success"
        )
        return result
    except Exception as e:
        _log_tool_error(logger, "build_entity_graph", e, time.time() - start_time, {"entity_count": len(entities), "base_url": base_url})
        raise


async def enhance_entity_graph_tool(input_source: str, input_type: str = "file", output_mode: str = "analysis") -> Dict[str, Any]:
    """
    Analyze existing Schema.org JSON-LD graphs and suggest enhancements.

    Args:
        input_source: File path or directory path containing JSON-LD Schema.org markup
        input_type: 'file' (single file) or 'directory' (scan all .json files)
        output_mode: 'analysis' (suggestions), 'enhanced' (complete graph), 'diff' (additions only)

    Returns:
        Entity-level analysis: missing properties, missing types, SEO scores, validation issues
    """
    logger = get_logger("tool.enhance_entity_graph")
    start_time = time.time()
    logger.info("tool_invoked", tool="enhance_entity_graph", input_source=input_source, input_type=input_type, output_mode=output_mode)
    try:
        result = await analyze_entity_graph(input_source=input_source, input_type=input_type, output_mode=output_mode)
        elapsed = time.time() - start_time
        logger.info(
            "tool_completed", tool="enhance_entity_graph",
            execution_time_seconds=round(elapsed, FormattingDefaults.ROUNDING_PRECISION),
            entity_count=len(result.get("entity_enhancements", [])),
            seo_score=result.get("overall_seo_score", 0), status="success"
        )
        return result
    except Exception as e:
        _log_tool_error(
            logger, "enhance_entity_graph", e, time.time() - start_time,
            {"input_source": input_source, "input_type": input_type, "output_mode": output_mode}
        )
        raise


def _reg_get_search(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_schema_type(
        type_name: str = Field(description="The schema.org type name (e.g., 'Person', 'Organization', 'Article')"),
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone get_schema_type_tool function."""
        return await get_schema_type_tool(type_name=type_name)

    @mcp.tool()
    async def search_schemas(
        query: str = Field(description="Search query to find schema types (searches in names and descriptions)"),
        limit: int = Field(default=10, description="Maximum number of results to return (1-100)"),
    ) -> List[Dict[str, Any]]:
        """Wrapper that calls the standalone search_schemas_tool function."""
        return await search_schemas_tool(query=query, limit=limit)


def _reg_hierarchy_properties(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_type_hierarchy(type_name: str = Field(description="The schema.org type name")) -> Dict[str, Any]:
        """Wrapper that calls the standalone get_type_hierarchy_tool function."""
        return await get_type_hierarchy_tool(type_name=type_name)

    @mcp.tool()
    async def get_type_properties(
        type_name: str = Field(description="The schema.org type name"),
        include_inherited: bool = Field(default=True, description="Include properties inherited from parent types"),
    ) -> List[Dict[str, Any]]:
        """Wrapper that calls the standalone get_type_properties_tool function."""
        return await get_type_properties_tool(type_name=type_name, include_inherited=include_inherited)


def _reg_example_entity_id(mcp: FastMCP) -> None:
    @mcp.tool()
    async def generate_schema_example(
        type_name: str = Field(description="The schema.org type name"),
        custom_properties: Optional[Dict[str, Any]] = Field(
            default=None, description="Custom property values to include in the example (JSON object)"
        ),
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone generate_schema_example_tool function."""
        return await generate_schema_example_tool(type_name=type_name, custom_properties=custom_properties)

    @mcp.tool()
    def generate_entity_id(
        base_url: str = Field(description="The canonical URL (e.g., 'https://example.com' or 'https://example.com/page')"),
        entity_type: str = Field(description="The Schema.org type (e.g., 'Organization', 'Person', 'Product')"),
        entity_slug: Optional[str] = Field(
            default=None, description="Optional URL slug for specific entity instances (e.g., 'john-doe', 'products/widget-a')"
        ),
    ) -> str:
        """Wrapper that calls the standalone generate_entity_id_tool function."""
        return generate_entity_id_tool(base_url=base_url, entity_type=entity_type, entity_slug=entity_slug)


def _reg_validate_build(mcp: FastMCP) -> None:
    @mcp.tool()
    def validate_entity_id(
        entity_id: str = Field(description="The @id value to validate (e.g., 'https://example.com/#organization')"),
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone validate_entity_id_tool function."""
        return validate_entity_id_tool(entity_id=entity_id)

    @mcp.tool()
    async def build_entity_graph(
        entities: List[Dict[str, Any]] = Field(description="List of entity definitions with type, properties, and relationships"),
        base_url: str = Field(description="Base canonical URL for generating @id values"),
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone build_entity_graph_tool function."""
        return await build_entity_graph_tool(entities=entities, base_url=base_url)


def _reg_enhance(mcp: FastMCP) -> None:
    @mcp.tool()
    async def enhance_entity_graph(
        input_source: str = Field(description="File path or directory path containing JSON-LD Schema.org markup"),
        input_type: str = Field(
            default="file", description="Input source type: 'file' for single file, 'directory' for scanning all .json files"
        ),
        output_mode: str = Field(
            default="analysis",
            description=("Output: 'analysis' for suggestions, 'enhanced' for complete graph, 'diff' for additions only"),
        ),
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone enhance_entity_graph_tool function."""
        return await enhance_entity_graph_tool(input_source=input_source, input_type=input_type, output_mode=output_mode)


def register_schema_tools(mcp: FastMCP) -> None:
    """Register Schema.org-related MCP tools.

    Args:
        mcp: FastMCP instance to register tools with
    """
    _reg_get_search(mcp)
    _reg_hierarchy_properties(mcp)
    _reg_example_entity_id(mcp)
    _reg_validate_build(mcp)
    _reg_enhance(mcp)
