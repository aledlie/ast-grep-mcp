"""Schema.org feature MCP tool definitions."""

import asyncio
import time
from typing import Any, Dict, List, Optional

import sentry_sdk
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.schema.client import get_schema_org_client
from ast_grep_mcp.features.schema.enhancement_service import analyze_entity_graph


def get_schema_type_tool(type_name: str) -> Dict[str, Any]:
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
        client = get_schema_org_client()
        result = asyncio.run(client.get_schema_type(type_name))

        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="get_schema_type",
            execution_time_seconds=round(execution_time, 3),
            status="success"
        )

        return result
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="get_schema_type",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "get_schema_type",
            "type_name": type_name,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def search_schemas_tool(query: str, limit: int = 10) -> List[Dict[str, Any]]:
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
        client = get_schema_org_client()
        results = asyncio.run(client.search_schemas(query, limit))

        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="search_schemas",
            execution_time_seconds=round(execution_time, 3),
            result_count=len(results),
            status="success"
        )

        return results
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="search_schemas",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "search_schemas",
            "query": query,
            "limit": limit,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def get_type_hierarchy_tool(type_name: str) -> Dict[str, Any]:
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
        client = get_schema_org_client()
        result = asyncio.run(client.get_type_hierarchy(type_name))

        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="get_type_hierarchy",
            execution_time_seconds=round(execution_time, 3),
            status="success"
        )

        return result
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="get_type_hierarchy",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "get_type_hierarchy",
            "type_name": type_name,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def get_type_properties_tool(
    type_name: str,
    include_inherited: bool = True
) -> List[Dict[str, Any]]:
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

    logger.info(
        "tool_invoked",
        tool="get_type_properties",
        type_name=type_name,
        include_inherited=include_inherited
    )

    try:
        client = get_schema_org_client()
        results = asyncio.run(client.get_type_properties(type_name, include_inherited))

        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="get_type_properties",
            execution_time_seconds=round(execution_time, 3),
            property_count=len(results),
            status="success"
        )

        return results
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="get_type_properties",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "get_type_properties",
            "type_name": type_name,
            "include_inherited": include_inherited,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def generate_schema_example_tool(
    type_name: str,
    custom_properties: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
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
        client = get_schema_org_client()
        result = asyncio.run(client.generate_example(type_name, custom_properties))

        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="generate_schema_example",
            execution_time_seconds=round(execution_time, 3),
            status="success"
        )

        return result
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="generate_schema_example",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "generate_schema_example",
            "type_name": type_name,
            "has_custom_properties": custom_properties is not None,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def generate_entity_id_tool(
    base_url: str,
    entity_type: str,
    entity_slug: Optional[str] = None
) -> str:
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

    logger.info(
        "tool_invoked",
        tool="generate_entity_id",
        base_url=base_url,
        entity_type=entity_type
    )

    try:
        client = get_schema_org_client()
        result = client.generate_entity_id(base_url, entity_type, entity_slug)

        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="generate_entity_id",
            execution_time_seconds=round(execution_time, 3),
            generated_id=result,
            status="success"
        )

        return result
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="generate_entity_id",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "generate_entity_id",
            "base_url": base_url,
            "entity_type": entity_type,
            "has_slug": entity_slug is not None,
            "execution_time_seconds": round(execution_time, 3)
        })
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
        client = get_schema_org_client()
        result = client.validate_entity_id(entity_id)

        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="validate_entity_id",
            execution_time_seconds=round(execution_time, 3),
            is_valid=result['valid'],
            warning_count=len(result['warnings']),
            status="success"
        )

        return result
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="validate_entity_id",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "validate_entity_id",
            "entity_id": entity_id,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def build_entity_graph_tool(
    entities: List[Dict[str, Any]],
    base_url: str
) -> Dict[str, Any]:
    """
    Build a knowledge graph of related entities with proper @id references.

    Creates a complete @graph structure where entities can reference each other using @id,
    enabling you to build a relational knowledge base over time.
    Based on best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs

    Args:
        entities: List of entity definitions with type, properties, and relationships
        base_url: Base canonical URL for generating @id values

    Returns:
        Complete JSON-LD @graph with all entities properly connected via @id references

    Entity Definition Format:
        {
            "type": "Organization",           # Required: Schema.org type
            "slug": "about",                  # Optional: URL path segment
            "id_fragment": "org-acme",        # Optional: Custom fragment for referencing
            "properties": {                   # Required: Entity properties
                "name": "Acme Corp",
                "url": "https://example.com"
            },
            "relationships": {                # Optional: References to other entities
                "founder": "person-john"      # References id_fragment of another entity
            }
        }
    """
    logger = get_logger("tool.build_entity_graph")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="build_entity_graph",
        entity_count=len(entities),
        base_url=base_url
    )

    try:
        client = get_schema_org_client()
        result = asyncio.run(client.build_entity_graph(entities, base_url))

        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="build_entity_graph",
            execution_time_seconds=round(execution_time, 3),
            entity_count=len(result.get('@graph', [])),
            status="success"
        )

        return result
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="build_entity_graph",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "tool": "build_entity_graph",
            "entity_count": len(entities),
            "base_url": base_url,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def register_schema_tools(mcp: FastMCP) -> None:
    """Register Schema.org-related MCP tools.

    Args:
        mcp: FastMCP instance to register tools with
    """

    @mcp.tool()
    def get_schema_type(
        type_name: str = Field(
            description="The schema.org type name (e.g., 'Person', 'Organization', 'Article')"
        )
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone get_schema_type_tool function."""
        return get_schema_type_tool(type_name=type_name)

    @mcp.tool()
    def search_schemas(
        query: str = Field(
            description="Search query to find schema types (searches in names and descriptions)"
        ),
        limit: int = Field(
            default=10,
            description="Maximum number of results to return (1-100)"
        )
    ) -> List[Dict[str, Any]]:
        """Wrapper that calls the standalone search_schemas_tool function."""
        return search_schemas_tool(query=query, limit=limit)

    @mcp.tool()
    def get_type_hierarchy(
        type_name: str = Field(description="The schema.org type name")
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone get_type_hierarchy_tool function."""
        return get_type_hierarchy_tool(type_name=type_name)

    @mcp.tool()
    def get_type_properties(
        type_name: str = Field(description="The schema.org type name"),
        include_inherited: bool = Field(
            default=True,
            description="Include properties inherited from parent types"
        )
    ) -> List[Dict[str, Any]]:
        """Wrapper that calls the standalone get_type_properties_tool function."""
        return get_type_properties_tool(type_name=type_name, include_inherited=include_inherited)

    @mcp.tool()
    def generate_schema_example(
        type_name: str = Field(description="The schema.org type name"),
        custom_properties: Optional[Dict[str, Any]] = Field(
            default=None,
            description="Custom property values to include in the example (JSON object)"
        )
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone generate_schema_example_tool function."""
        return generate_schema_example_tool(type_name=type_name, custom_properties=custom_properties)

    @mcp.tool()
    def generate_entity_id(
        base_url: str = Field(
            description="The canonical URL (e.g., 'https://example.com' or 'https://example.com/page')"
        ),
        entity_type: str = Field(
            description="The Schema.org type (e.g., 'Organization', 'Person', 'Product')"
        ),
        entity_slug: Optional[str] = Field(
            default=None,
            description="Optional URL slug for specific entity instances (e.g., 'john-doe', 'products/widget-a')"
        )
    ) -> str:
        """Wrapper that calls the standalone generate_entity_id_tool function."""
        return generate_entity_id_tool(base_url=base_url, entity_type=entity_type, entity_slug=entity_slug)

    @mcp.tool()
    def validate_entity_id(
        entity_id: str = Field(
            description="The @id value to validate (e.g., 'https://example.com/#organization')"
        )
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone validate_entity_id_tool function."""
        return validate_entity_id_tool(entity_id=entity_id)

    @mcp.tool()
    def build_entity_graph(
        entities: List[Dict[str, Any]] = Field(
            description="List of entity definitions with type, properties, and relationships"
        ),
        base_url: str = Field(
            description="Base canonical URL for generating @id values"
        )
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone build_entity_graph_tool function."""
        return build_entity_graph_tool(entities=entities, base_url=base_url)

    @mcp.tool()
    def enhance_entity_graph(
        input_source: str = Field(
            description="File path or directory path containing JSON-LD Schema.org markup"
        ),
        input_type: str = Field(
            default="file",
            description="Input source type: 'file' for single file, 'directory' for scanning all .json files"
        ),
        output_mode: str = Field(
            default="analysis",
            description="Output mode: 'analysis' for enhancement suggestions, 'enhanced' for complete graph with placeholders, 'diff' for additions only"
        )
    ) -> Dict[str, Any]:
        """Analyze existing Schema.org JSON-LD graphs and suggest enhancements.

        Examines JSON-LD structured data and provides recommendations based on:
        - Schema.org vocabulary standards
        - Google Rich Results guidelines
        - SEO best practices

        Returns entity-level analysis with:
        - Missing property suggestions with priorities (critical/high/medium)
        - Missing entity type suggestions (FAQPage, BreadcrumbList, etc.)
        - SEO completeness scores (0-100)
        - Validation issues (broken @id references)
        - Example values for all suggestions

        Output Modes:
        - analysis: Detailed suggestions with priorities and examples
        - enhanced: Complete graph with all suggestions applied (placeholder values)
        - diff: Only the additions needed (for merging with existing markup)
        """
        logger = get_logger("tool.enhance_entity_graph")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="enhance_entity_graph",
            input_source=input_source,
            input_type=input_type,
            output_mode=output_mode
        )

        try:
            result = asyncio.run(analyze_entity_graph(
                input_source=input_source,
                input_type=input_type,
                output_mode=output_mode
            ))

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="enhance_entity_graph",
                execution_time_seconds=round(execution_time, 3),
                entity_count=len(result.get('entity_enhancements', [])),
                seo_score=result.get('overall_seo_score', 0),
                status="success"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="enhance_entity_graph",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "enhance_entity_graph",
                "input_source": input_source,
                "input_type": input_type,
                "output_mode": output_mode,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise
