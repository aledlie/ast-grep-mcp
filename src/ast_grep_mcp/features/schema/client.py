"""Schema.org client for fetching and querying vocabulary."""

from typing import Any, Dict, List, Optional

import httpx
import sentry_sdk

from ast_grep_mcp.core.logging import get_logger


class SchemaOrgClient:
    """Client for fetching and querying Schema.org vocabulary."""

    def __init__(self) -> None:
        self.schema_data: Dict[str, Any] = {}
        self.initialized = False
        self.SCHEMA_URL = "https://schema.org/version/latest/schemaorg-current-https.jsonld"
        self.logger = get_logger("schema_org")

    async def initialize(self) -> None:
        """Fetch and index Schema.org data."""
        if self.initialized:
            return

        try:
            self.logger.info("fetching_schema_org_data", url=self.SCHEMA_URL)
            with sentry_sdk.start_span(op="http.client", name="Fetch Schema.org vocabulary") as span:
                span.set_data("url", self.SCHEMA_URL)
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self.SCHEMA_URL)
                    response.raise_for_status()
                    data = response.json()
                span.set_data("status_code", response.status_code)
                span.set_data("content_length", len(str(data)))

            if not data:
                raise RuntimeError("No data received from schema.org")

            # Index all types and properties by their @id
            if data.get('@graph') and isinstance(data['@graph'], list):
                for item in data['@graph']:
                    if item and isinstance(item, dict) and item.get('@id'):
                        self.schema_data[item['@id']] = item
                        # Also index by label for easier lookup
                        label = item.get('rdfs:label')
                        if isinstance(label, str):
                            self.schema_data[f"schema:{label}"] = item
            else:
                raise RuntimeError("Invalid schema.org data format: missing @graph array")

            if not self.schema_data:
                raise RuntimeError("No schema data was loaded")

            self.initialized = True
            self.logger.info("schema_org_loaded", entry_count=len(self.schema_data))
        except Exception as e:
            self.logger.error("schema_org_load_failed", error=str(e))
            self.initialized = False
            sentry_sdk.capture_exception(e, extras={
                "url": self.SCHEMA_URL,
                "operation": "schema_org_initialize"
            })
            raise RuntimeError(f"Failed to initialize schema.org client: {e}") from e

    def _normalize_to_array(self, value: Any) -> List[Any]:
        """Normalize a value or array to a list."""
        if not value:
            return []
        return value if isinstance(value, list) else [value]

    def _extract_super_types(self, type_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract parent types from a type definition."""
        super_classes = self._normalize_to_array(type_data.get('rdfs:subClassOf'))
        result = []
        for sc in super_classes:
            if isinstance(sc, dict) and sc.get('@id'):
                super_type = self.schema_data.get(sc['@id'], {})
                label = super_type.get('rdfs:label')
                result.append({
                    'name': label if isinstance(label, str) else sc['@id'].replace('schema:', ''),
                    'id': sc['@id']
                })
        return result

    def _find_sub_types(self, type_id: str) -> List[Dict[str, str]]:
        """Find all subtypes of a given type."""
        sub_types = []
        for item in self.schema_data.values():
            if not item.get('@type'):
                continue

            types = self._normalize_to_array(item['@type'])
            if 'rdfs:Class' not in types:
                continue

            super_classes = self._normalize_to_array(item.get('rdfs:subClassOf'))
            for sc in super_classes:
                if isinstance(sc, dict) and sc.get('@id') == type_id:
                    label = item.get('rdfs:label')
                    if label:
                        sub_types.append({
                            'name': label,
                            'id': item['@id']
                        })
                    break

        return sub_types

    def _format_property(self, prop: Dict[str, Any]) -> Dict[str, Any]:
        """Format a property for output."""
        ranges = self._normalize_to_array(prop.get('schema:rangeIncludes'))
        expected_types = []
        for r in ranges:
            if isinstance(r, dict) and r.get('@id'):
                range_type = self.schema_data.get(r['@id'], {})
                label = range_type.get('rdfs:label')
                expected_types.append(label if isinstance(label, str) else r['@id'].replace('schema:', ''))

        return {
            'name': prop.get('rdfs:label', ''),
            'description': prop.get('rdfs:comment', 'No description available'),
            'id': prop.get('@id', ''),
            'expectedTypes': expected_types
        }

    def _generate_example_value(self, property_data: Dict[str, Any]) -> Any:
        """Generate an example value for a property."""
        expected_types = property_data.get('expectedTypes', [])
        if not expected_types:
            return f"Example {property_data.get('name', 'value')}"

        type_name = expected_types[0]

        if type_name == 'Text':
            return f"Example {property_data.get('name', 'text')}"
        elif type_name == 'URL':
            return 'https://example.com'
        elif type_name == 'Date':
            return '2024-01-01'
        elif type_name == 'DateTime':
            return '2024-01-01T12:00:00Z'
        elif type_name in ('Number', 'Integer'):
            return 42
        elif type_name == 'Boolean':
            return True
        elif type_name == 'ImageObject':
            return {
                '@type': 'ImageObject',
                'url': 'https://example.com/image.jpg',
                'contentUrl': 'https://example.com/image.jpg'
            }
        else:
            return f"Example {property_data.get('name', 'value')}"

    async def get_schema_type(self, type_name: str) -> Dict[str, Any]:
        """Get detailed information about a schema.org type."""
        await self.initialize()

        if not type_name or not isinstance(type_name, str):
            raise ValueError("Type name must be a non-empty string")

        type_id = type_name if type_name.startswith('schema:') else f"schema:{type_name}"
        type_data = self.schema_data.get(type_id)

        if not type_data:
            raise ValueError(f"Type '{type_name}' not found in schema.org")

        label = type_data.get('rdfs:label')
        clean_name = label if isinstance(label, str) else type_name

        return {
            'name': clean_name,
            'description': type_data.get('rdfs:comment', 'No description available'),
            'id': type_data.get('@id', ''),
            'type': type_data.get('@type'),
            'superTypes': self._extract_super_types(type_data),
            'url': f"https://schema.org/{clean_name}"
        }

    async def search_schemas(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for schema types by keyword."""
        await self.initialize()

        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        normalized_limit = max(1, min(limit or 10, 100))
        results = []
        query_lower = query.lower().strip()

        if not query_lower:
            raise ValueError("Query cannot be empty")

        for item in self.schema_data.values():
            if not item.get('@type'):
                continue

            types = self._normalize_to_array(item['@type'])
            if 'rdfs:Class' not in types:
                continue

            label = item.get('rdfs:label', '')
            comment = item.get('rdfs:comment', '')

            if not isinstance(label, str):
                continue

            label_lower = label.lower()
            comment_lower = comment.lower() if isinstance(comment, str) else ''

            if query_lower in label_lower or query_lower in comment_lower:
                results.append({
                    'name': label,
                    'description': comment or 'No description available',
                    'id': item.get('@id', ''),
                    'url': f"https://schema.org/{label}",
                    'relevance': 2 if query_lower in label_lower else 1
                })

            if len(results) >= normalized_limit * 2:
                break

        # Sort by relevance and limit
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return [{'name': r['name'], 'description': r['description'], 'id': r['id'], 'url': r['url']}
                for r in results[:normalized_limit]]

    async def get_type_hierarchy(self, type_name: str) -> Dict[str, Any]:
        """Get the inheritance hierarchy for a type."""
        await self.initialize()

        type_id = type_name if type_name.startswith('schema:') else f"schema:{type_name}"
        type_data = self.schema_data.get(type_id)

        if not type_data:
            raise ValueError(f"Type '{type_name}' not found in schema.org")

        label = type_data.get('rdfs:label')
        return {
            'name': label if isinstance(label, str) else type_name,
            'id': type_data.get('@id', ''),
            'parents': self._extract_super_types(type_data),
            'children': self._find_sub_types(type_id)
        }

    async def get_type_properties(self, type_name: str, include_inherited: bool = True) -> List[Dict[str, Any]]:
        """Get all properties available for a type."""
        await self.initialize()

        type_id = type_name if type_name.startswith('schema:') else f"schema:{type_name}"
        properties: List[Dict[str, Any]] = []
        processed_props: set[str] = set()

        # Get direct properties
        for item in self.schema_data.values():
            item_types = item.get('@type')
            if not item_types:
                continue

            types_list = self._normalize_to_array(item_types)
            if 'rdf:Property' not in types_list:
                continue

            domains = self._normalize_to_array(item.get('schema:domainIncludes'))
            for domain in domains:
                if isinstance(domain, dict) and domain.get('@id') == type_id:
                    prop_id = item.get('@id', '')
                    if prop_id and prop_id not in processed_props:
                        processed_props.add(prop_id)
                        properties.append(self._format_property(item))
                    break

        # Get inherited properties if requested
        if include_inherited:
            type_data = self.schema_data.get(type_id)
            if type_data:
                super_types = self._extract_super_types(type_data)
                for super_type in super_types:
                    super_type_id = super_type['id']
                    for item in self.schema_data.values():
                        item_types = item.get('@type')
                        if not item_types:
                            continue

                        types_list = self._normalize_to_array(item_types)
                        if 'rdf:Property' not in types_list:
                            continue

                        domains = self._normalize_to_array(item.get('schema:domainIncludes'))
                        for domain in domains:
                            if isinstance(domain, dict) and domain.get('@id') == super_type_id:
                                prop_id = item.get('@id', '')
                                if prop_id and prop_id not in processed_props:
                                    processed_props.add(prop_id)
                                    prop = self._format_property(item)
                                    prop['inheritedFrom'] = super_type['name']
                                    properties.append(prop)
                                break

        properties.sort(key=lambda x: x['name'])
        return properties

    async def generate_example(self, type_name: str, custom_properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate an example JSON-LD for a type."""
        await self.initialize()

        type_info = await self.get_schema_type(type_name)
        properties = await self.get_type_properties(type_name, include_inherited=False)

        example: Dict[str, Any] = {
            '@context': 'https://schema.org',
            '@type': type_info['name']
        }

        # Add common properties
        common_props = ['name', 'description', 'url', 'identifier', 'image']

        for prop in properties:
            if prop['name'] in common_props:
                example[prop['name']] = self._generate_example_value(prop)

        # Add custom properties
        if custom_properties:
            example.update(custom_properties)

        return example

    def generate_entity_id(self, base_url: str, entity_type: str, entity_slug: Optional[str] = None) -> str:
        """Generate a proper @id value following best practices.

        Args:
            base_url: The canonical URL (e.g., 'https://example.com' or 'https://example.com/page')
            entity_type: The schema type in lowercase (e.g., 'organization', 'person', 'product')
            entity_slug: Optional specific identifier (e.g., 'john-doe', 'widget-a')

        Returns:
            Properly formatted @id like 'https://example.com/#organization' or
            'https://example.com/products/widget-a#product'

        Best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs:
        - Use canonical URL + hash fragment
        - Keep IDs stable (no timestamps or dynamic values)
        - Use descriptive entity types for debugging clarity
        - One unchanging identifier per entity
        """
        # Remove trailing slash from base_url
        base_url = base_url.rstrip('/')

        # Normalize entity_type to lowercase
        entity_type_lower = entity_type.lower()

        # If entity_slug provided, append it to the path
        if entity_slug:
            # Remove leading slash from slug if present
            entity_slug = entity_slug.lstrip('/')
            return f"{base_url}/{entity_slug}#{entity_type_lower}"
        else:
            return f"{base_url}#{entity_type_lower}"

    def validate_entity_id(self, entity_id: str) -> Dict[str, Any]:
        """Validate an @id value against best practices.

        Args:
            entity_id: The @id value to validate

        Returns:
            Dictionary with validation results:
            - valid: bool - Overall validity
            - warnings: List[str] - Best practice warnings
            - suggestions: List[str] - Improvement suggestions
        """
        warnings = []
        suggestions = []

        # Check if it's a valid URL
        if not entity_id.startswith(('http://', 'https://')):
            warnings.append("@id should be a full URL (http:// or https://)")

        # Check for hash fragment
        if '#' not in entity_id:
            warnings.append("@id should include a hash fragment (e.g., #organization)")
            suggestions.append("Add a descriptive fragment like #organization, #person, or #product")

        # Check for problematic patterns
        if any(pattern in entity_id.lower() for pattern in ['timestamp', 'date', 'time', 'random', 'temp']):
            warnings.append("@id contains potentially unstable components (timestamp, date, random)")
            suggestions.append("Use stable, permanent identifiers")

        # Check for numeric-only fragment
        if '#' in entity_id:
            fragment = entity_id.split('#')[1]
            if fragment.isdigit():
                warnings.append("Fragment is numeric-only, consider using descriptive names")
                suggestions.append("Use descriptive fragments like #organization instead of #1")

        # Check for query parameters
        if '?' in entity_id:
            warnings.append("@id contains query parameters which may be unstable")
            suggestions.append("Use clean URLs without query strings")

        valid = len(warnings) == 0

        return {
            'valid': valid,
            'entity_id': entity_id,
            'warnings': warnings,
            'suggestions': suggestions,
            'best_practices': [
                'Use canonical URL + hash fragment',
                'Keep IDs stable (no timestamps or dynamic values)',
                'Use descriptive fragments for debugging',
                'One unchanging identifier per entity'
            ] if warnings else []
        }

    async def build_entity_graph(
        self,
        entities: List[Dict[str, Any]],
        base_url: str
    ) -> Dict[str, Any]:
        """Build a knowledge graph of related entities with proper @id references.

        Args:
            entities: List of entity definitions, each with:
                - type: Schema.org type name
                - slug: Optional URL slug
                - properties: Dict of property values
                - relationships: Optional dict of relationships to other entities
            base_url: Base canonical URL for generating @id values

        Returns:
            Complete @graph structure with all entities properly connected

        Example:
            entities = [
                {
                    'type': 'Organization',
                    'slug': None,  # Homepage entity
                    'properties': {'name': 'Acme Corp'},
                    'relationships': {'founder': 'person-john'}
                },
                {
                    'type': 'Person',
                    'slug': 'team/john',
                    'id_fragment': 'person-john',  # Custom fragment for referencing
                    'properties': {'name': 'John Doe'}
                }
            ]
        """
        await self.initialize()

        graph_entities = []
        entity_id_map = {}  # Map fragments to full @id values

        # First pass: Generate all @id values
        for entity in entities:
            entity_type = entity['type']
            slug = entity.get('slug')
            id_fragment = entity.get('id_fragment', entity_type.lower())

            # Generate @id
            entity_id = self.generate_entity_id(base_url, entity_type, slug)
            entity_id_map[id_fragment] = entity_id

        # Second pass: Build complete entity objects with relationships
        for entity in entities:
            entity_type = entity['type']
            slug = entity.get('slug')
            id_fragment = entity.get('id_fragment', entity_type.lower())
            properties = entity.get('properties', {})
            relationships = entity.get('relationships', {})

            # Get type info
            type_info = await self.get_schema_type(entity_type)

            # Build entity
            entity_obj: Dict[str, Any] = {
                '@type': type_info['name'],
                '@id': entity_id_map[id_fragment]
            }

            # Add properties
            entity_obj.update(properties)

            # Add URL if slug provided
            if slug:
                entity_obj['url'] = f"{base_url.rstrip('/')}/{slug.lstrip('/')}"

            # Add relationships using @id references
            for rel_property, target_fragments in relationships.items():
                # Handle both single values and lists
                if isinstance(target_fragments, list):
                    # Multiple relationships
                    entity_obj[rel_property] = []
                    for target_fragment in target_fragments:
                        if target_fragment in entity_id_map:
                            entity_obj[rel_property].append({'@id': entity_id_map[target_fragment]})
                        else:
                            entity_obj[rel_property].append(target_fragment)
                else:
                    # Single relationship
                    if target_fragments in entity_id_map:
                        entity_obj[rel_property] = {'@id': entity_id_map[target_fragments]}
                    else:
                        entity_obj[rel_property] = target_fragments

            graph_entities.append(entity_obj)

        return {
            '@context': 'https://schema.org',
            '@graph': graph_entities
        }


# Global schema.org client instance
_schema_org_client: Optional[SchemaOrgClient] = None


def get_schema_org_client() -> SchemaOrgClient:
    """Get or create the global schema.org client."""
    global _schema_org_client
    if _schema_org_client is None:
        _schema_org_client = SchemaOrgClient()
    return _schema_org_client