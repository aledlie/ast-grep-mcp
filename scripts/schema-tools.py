#!/usr/bin/env python3
"""
Schema.org Tools CLI
====================

Command-line interface for Schema.org vocabulary tools.
Provides quick access to search, type information, and property queries.

Usage:
    schema-tools.py search <query> [--limit N]
    schema-tools.py type <type_name>
    schema-tools.py properties <type_name> [--no-inherited]

Examples:
    # Search for schema types
    schema-tools.py search "article"
    schema-tools.py search "organization" --limit 5

    # Get type information
    schema-tools.py type Person
    schema-tools.py type BlogPosting

    # Get type properties
    schema-tools.py properties Person
    schema-tools.py properties Article --no-inherited
"""

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List

# Import the SchemaOrgClient from main.py
try:
    from main import SchemaOrgClient
except ImportError:
    print("Error: Could not import SchemaOrgClient from main.py", file=sys.stderr)
    print("Make sure you're running this script from the ast-grep-mcp directory", file=sys.stderr)
    sys.exit(1)


class SchemaToolsCLI:
    """Command-line interface for Schema.org tools."""

    def __init__(self) -> None:
        self.client: SchemaOrgClient | None = None

    async def initialize(self) -> None:
        """Initialize the Schema.org client."""
        if self.client is None:
            self.client = SchemaOrgClient()
            await self.client.initialize()

    async def search_schemas(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for Schema.org types by keyword.

        Args:
            query: Search term
            limit: Maximum results (1-100)

        Returns:
            List of matching types with relevance scores
        """
        await self.initialize()
        assert self.client is not None

        # Validate limit
        limit = max(1, min(100, limit))

        results = await self.client.search_schemas(query, limit)
        return results

    async def get_schema_type(self, type_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a Schema.org type.

        Args:
            type_name: The Schema.org type name

        Returns:
            Type information including description, URL, and parent types
        """
        await self.initialize()
        assert self.client is not None

        type_info = await self.client.get_schema_type(type_name)

        if not type_info:
            raise ValueError(f"Type '{type_name}' not found in Schema.org vocabulary")

        return type_info

    async def get_type_properties(
        self,
        type_name: str,
        include_inherited: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all properties available for a Schema.org type.

        Args:
            type_name: The Schema.org type name
            include_inherited: Include properties from parent types

        Returns:
            List of properties with metadata
        """
        await self.initialize()
        assert self.client is not None

        properties = await self.client.get_type_properties(type_name, include_inherited)

        if properties is None:
            raise ValueError(f"Type '{type_name}' not found in Schema.org vocabulary")

        return properties


def format_search_results(results: List[Dict[str, Any]]) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."

    lines = [f"\nFound {len(results)} result(s):\n"]

    for i, result in enumerate(results, 1):
        name = result.get('name', 'Unknown')
        description = result.get('description', 'No description available')
        url = result.get('url', '')
        score = result.get('relevance_score', 0)

        lines.append(f"{i}. {name}")
        lines.append(f"   URL: {url}")
        lines.append(f"   Description: {description}")
        lines.append(f"   Relevance: {score:.2f}")
        lines.append("")

    return '\n'.join(lines)


def format_type_info(type_info: Dict[str, Any]) -> str:
    """Format type information for display."""
    lines = []

    name = type_info.get('name', 'Unknown')
    description = type_info.get('description', 'No description available')
    url = type_info.get('url', '')
    parent_types = type_info.get('parent_types', [])

    lines.append(f"\n{name}")
    lines.append("=" * len(name))
    lines.append(f"\nURL: {url}")
    lines.append(f"\nDescription:\n{description}")

    if parent_types:
        lines.append("\nParent Type(s):")
        for parent in parent_types:
            lines.append(f"  - {parent}")

    return '\n'.join(lines)


def format_properties(properties: List[Dict[str, Any]], type_name: str) -> str:
    """Format properties for display."""
    lines = [f"\nProperties for {type_name}\n"]
    lines.append("=" * (len(type_name) + 15))

    if not properties:
        lines.append("\nNo properties found.")
        return '\n'.join(lines)

    lines.append(f"\nTotal Properties: {len(properties)}")
    lines.append("-" * 40)

    for prop in properties:
        prop_name = prop.get('name', 'Unknown')
        prop_desc = prop.get('description', 'No description')
        expected_types = prop.get('expected_types', [])
        inherited_from = prop.get('inherited_from', None)

        lines.append(f"\n• {prop_name}")
        if inherited_from:
            lines.append(f"  Inherited from: {inherited_from}")
        lines.append(f"  Description: {prop_desc}")
        if expected_types:
            lines.append(f"  Expected Type(s): {', '.join(expected_types)}")

    lines.append(f"\n\nTotal: {len(properties)} properties")

    return '\n'.join(lines)


async def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Schema.org vocabulary tools for searching types and querying properties',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for schema types
  %(prog)s search "article"
  %(prog)s search "organization" --limit 5

  # Get type information
  %(prog)s type Person
  %(prog)s type BlogPosting

  # Get type properties
  %(prog)s properties Person
  %(prog)s properties Article --no-inherited

  # JSON output mode
  %(prog)s search "article" --json
  %(prog)s type Person --json
  %(prog)s properties Person --json
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for Schema.org types')
    search_parser.add_argument('query', help='Search term')
    search_parser.add_argument('--limit', type=int, default=10,
                              help='Maximum results (1-100, default: 10)')
    search_parser.add_argument('--json', action='store_true',
                              help='Output as JSON')

    # Type command
    type_parser = subparsers.add_parser('type', help='Get Schema.org type information')
    type_parser.add_argument('type_name', help='Schema.org type name')
    type_parser.add_argument('--json', action='store_true',
                            help='Output as JSON')

    # Properties command
    props_parser = subparsers.add_parser('properties', help='Get type properties')
    props_parser.add_argument('type_name', help='Schema.org type name')
    props_parser.add_argument('--no-inherited', action='store_true',
                             help='Exclude inherited properties')
    props_parser.add_argument('--json', action='store_true',
                             help='Output as JSON')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = SchemaToolsCLI()

    try:
        if args.command == 'search':
            results = await cli.search_schemas(args.query, args.limit)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(format_search_results(results))

        elif args.command == 'type':
            type_info = await cli.get_schema_type(args.type_name)
            if args.json:
                print(json.dumps(type_info, indent=2))
            else:
                print(format_type_info(type_info))

        elif args.command == 'properties':
            properties = await cli.get_type_properties(
                args.type_name,
                include_inherited=not args.no_inherited
            )
            if args.json:
                print(json.dumps(properties, indent=2))
            else:
                print(format_properties(properties, args.type_name))

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
