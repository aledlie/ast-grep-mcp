"""Schema.org feature MCP tool definitions."""

import asyncio
import time
from typing import Any, Dict, List, Optional

import sentry_sdk
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.schema.client import get_schema_org_client


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
        """
        Get detailed information about a schema.org type.
        Returns the type's name, description, URL, parent types, and metadata.

        Example: get_schema_type('Person') returns details about the Person type including its properties and parent types.
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
        """
        Search for schema.org types by keyword.
        Searches through type names and descriptions, returns matching types sorted by relevance.

        Example: search_schemas('blog') finds types like BlogPosting, Blog, etc.
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

    @mcp.tool()
    def get_type_hierarchy(
        type_name: str = Field(description="The schema.org type name")
    ) -> Dict[str, Any]:
        """
        Get the inheritance hierarchy for a schema.org type.
        Returns the type's parent types (super types) and child types (sub types).

        Example: get_type_hierarchy('NewsArticle') shows it inherits from Article, which inherits from CreativeWork, etc.
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

    @mcp.tool()
    def get_type_properties(
        type_name: str = Field(description="The schema.org type name"),
        include_inherited: bool = Field(
            default=True,
            description="Include properties inherited from parent types"
        )
    ) -> List[Dict[str, Any]]:
        """
        Get all properties available for a schema.org type.
        Returns property names, descriptions, and expected value types.

        Example: get_type_properties('Organization') returns properties like name, url, address, founder, etc.
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

    @mcp.tool()
    def generate_schema_example(
        type_name: str = Field(description="The schema.org type name"),
        custom_properties: Optional[Dict[str, Any]] = Field(
            default=None,
            description="Custom property values to include in the example (JSON object)"
        )
    ) -> Dict[str, Any]:
        """
        Generate an example JSON-LD structured data for a schema.org type.
        Creates a valid schema.org JSON-LD object with common properties and any custom values provided.

        Example: generate_schema_example('Recipe', {'name': 'Chocolate Cake', 'prepTime': 'PT30M'})
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
        """
        Generate a proper @id value following Schema.org and SEO best practices.

        Creates stable, unique identifiers for entities that can be referenced across your knowledge graph.
        Based on best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs

        Examples:
        - Homepage organization: generate_entity_id('https://example.com', 'Organization')
          → 'https://example.com/#organization'

        - Specific product: generate_entity_id('https://example.com', 'Product', 'products/widget-a')
          → 'https://example.com/products/widget-a#product'

        - Team member: generate_entity_id('https://example.com', 'Person', 'team/john-doe')
          → 'https://example.com/team/john-doe#person'

        Best Practices:
        - Use canonical URLs only
        - Keep IDs stable (no timestamps or dynamic values)
        - Use descriptive entity types
        - One unchanging identifier per entity
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

    @mcp.tool()
    def validate_entity_id(
        entity_id: str = Field(
            description="The @id value to validate (e.g., 'https://example.com/#organization')"
        )
    ) -> Dict[str, Any]:
        """
        Validate an @id value against Schema.org and SEO best practices.

        Checks for common issues and provides actionable suggestions for improvement.
        Based on best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs

        Returns:
        - valid: Whether the @id follows all best practices
        - warnings: List of issues found
        - suggestions: Specific improvements to make
        - best_practices: Key principles to follow

        Example:
        validate_entity_id('https://example.com/#organization')
        → { "valid": true, "warnings": [], "suggestions": [] }

        validate_entity_id('example.com/page')
        → { "valid": false, "warnings": ["Missing protocol", "Missing hash fragment"], ... }
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

    @mcp.tool()
    def build_entity_graph(
        entities: List[Dict[str, Any]] = Field(
            description="List of entity definitions with type, properties, and relationships"
        ),
        base_url: str = Field(
            description="Base canonical URL for generating @id values"
        )
    ) -> Dict[str, Any]:
        """
        Build a knowledge graph of related entities with proper @id references.

        Creates a complete @graph structure where entities can reference each other using @id,
        enabling you to build a relational knowledge base over time.
        Based on best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs

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

        Example:
        build_entity_graph([
            {
                "type": "Organization",
                "properties": {"name": "Acme Corp"},
                "relationships": {"founder": "person-john", "employee": "person-jane"}
            },
            {
                "type": "Person",
                "id_fragment": "person-john",
                "slug": "team/john-doe",
                "properties": {"name": "John Doe", "jobTitle": "CEO"}
            },
            {
                "type": "Person",
                "id_fragment": "person-jane",
                "slug": "team/jane-smith",
                "properties": {"name": "Jane Smith", "jobTitle": "CTO"}
            }
        ], "https://example.com")

        Returns complete JSON-LD @graph with all entities properly connected via @id references.
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
