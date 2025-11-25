"""Schema.org feature - structured data and knowledge graph functionality."""

from ast_grep_mcp.features.schema.client import (
    SchemaOrgClient,
    get_schema_org_client,
)
from ast_grep_mcp.features.schema.tools import register_schema_tools

__all__ = [
    # Client
    "SchemaOrgClient",
    "get_schema_org_client",
    # Registration
    "register_schema_tools",
]
