"""Schema.org client for fetching and querying vocabulary."""

from typing import Any, Callable, Dict, List, Optional, Set, cast

import httpx
import sentry_sdk

from ast_grep_mcp.core.logging import get_logger

# Global instance for singleton pattern
_client_instance: Optional['SchemaOrgClient'] = None


def get_schema_org_client() -> 'SchemaOrgClient':
    """Get or create the global Schema.org client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = SchemaOrgClient()
    return _client_instance


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
            data = await self._fetch_schema_data()
            self._validate_and_index_data(data)
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

    async def _fetch_schema_data(self) -> Dict[str, Any]:
        """Fetch schema.org data from remote endpoint."""
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

        return cast(Dict[str, Any], data)

    def _validate_and_index_data(self, data: Dict[str, Any]) -> None:
        """Validate data format and index all types and properties."""
        graph = data.get('@graph')
        if not graph or not isinstance(graph, list):
            raise RuntimeError("Invalid schema.org data format: missing @graph array")

        for item in graph:
            if not item or not isinstance(item, dict):
                continue

            item_id = item.get('@id')
            if not item_id:
                continue

            self.schema_data[item_id] = item

            # Also index by label for easier lookup
            label = item.get('rdfs:label')
            if isinstance(label, str):
                self.schema_data[f"schema:{label}"] = item

        if not self.schema_data:
            raise RuntimeError("No schema data was loaded")

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

        # Ensure name is always a string
        raw_label = prop.get('rdfs:label', '')
        name = raw_label if isinstance(raw_label, str) else str(raw_label) if raw_label else ''

        # Ensure description is always a string
        raw_comment = prop.get('rdfs:comment', 'No description available')
        description = raw_comment if isinstance(raw_comment, str) else str(raw_comment) if raw_comment else 'No description available'

        return {
            'name': name,
            'description': description,
            'id': prop.get('@id', ''),
            'expectedTypes': expected_types
        }

    def _generate_example_value(self, property_data: Dict[str, Any]) -> Any:
        """Generate an example value for a property."""
        expected_types = property_data.get('expectedTypes', [])
        if not expected_types:
            return f"Example {property_data.get('name', 'value')}"

        type_name = expected_types[0]

        # Use a mapping to reduce nesting
        type_examples: Dict[str, Callable[[], Any]] = {
            'Text': lambda: f"Example {property_data.get('name', 'text')}",
            'URL': lambda: 'https://example.com',
            'Date': lambda: '2024-01-01',
            'DateTime': lambda: '2024-01-01T12:00:00Z',
            'Number': lambda: 42,
            'Integer': lambda: 42,
            'Boolean': lambda: True,
            'ImageObject': lambda: {
                '@type': 'ImageObject',
                'url': 'https://example.com/image.jpg',
                'contentUrl': 'https://example.com/image.jpg'
            }
        }

        generator = type_examples.get(type_name)
        if generator:
            return generator()

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

    def _collect_properties_for_type(
        self,
        type_id: str,
        processed_props: Set[str],
        inherit_from: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Collect properties for a specific type."""
        properties = []

        for item in self.schema_data.values():
            # Skip if not a property
            item_types = item.get('@type')
            if not item_types:
                continue

            types_list = self._normalize_to_array(item_types)
            if 'rdf:Property' not in types_list:
                continue

            # Check if this property belongs to the type
            domains = self._normalize_to_array(item.get('schema:domainIncludes'))
            for domain in domains:
                if not isinstance(domain, dict):
                    continue

                if domain.get('@id') != type_id:
                    continue

                prop_id = item.get('@id', '')
                if not prop_id or prop_id in processed_props:
                    break

                processed_props.add(prop_id)
                prop = self._format_property(item)

                if inherit_from:
                    prop['inheritedFrom'] = inherit_from

                properties.append(prop)
                break

        return properties

    async def get_type_properties(self, type_name: str, include_inherited: bool = True) -> List[Dict[str, Any]]:
        """Get all properties available for a type."""
        await self.initialize()

        type_id = type_name if type_name.startswith('schema:') else f"schema:{type_name}"
        processed_props: Set[str] = set()
        properties: List[Dict[str, Any]] = []

        # Get direct properties
        direct_props = self._collect_properties_for_type(type_id, processed_props)
        properties.extend(direct_props)

        # Get inherited properties if requested
        if include_inherited:
            type_data = self.schema_data.get(type_id)
            if type_data:
                super_types = self._extract_super_types(type_data)
                for super_type in super_types:
                    inherited_props = self._collect_properties_for_type(
                        super_type['id'],
                        processed_props,
                        inherit_from=super_type['name']
                    )
                    properties.extend(inherited_props)

        # Sort by name, handling cases where name might not be a string
        properties.sort(key=lambda x: str(x.get('name', '')) if x.get('name') else '')
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
            Properly formatted @id like 'https://example.com#organization' or
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
        entity_type = entity_type.lower()

        # Generate the @id based on whether we have an entity_slug
        if entity_slug:
            # Remove leading slash from slug if present
            slug = entity_slug.lstrip('/')
            # For specific entities, include the slug in the path
            return f"{base_url}/{slug}#{entity_type}"
        else:
            # For generic entities, use base URL with hash fragment (no slash before #)
            return f"{base_url}#{entity_type}"

    def _check_url_protocol(self, entity_id: str) -> Optional[tuple[str, str]]:
        """Check if entity_id has a valid URL protocol."""
        if not entity_id.startswith(('http://', 'https://')):
            return (
                "@id must be a full URL starting with http:// or https://",
                f"Change to: https://example.com/{entity_id}"
            )
        return None

    def _check_hash_fragment(self, entity_id: str) -> Optional[tuple[str, str]]:
        """Check if entity_id has a hash fragment."""
        if '#' not in entity_id:
            return (
                "@id should include a hash fragment (#) for referenceability",
                "Add a descriptive fragment like #organization or #product"
            )
        return None

    def _check_query_params(self, entity_id: str) -> Optional[tuple[str, str]]:
        """Check if entity_id has query parameters."""
        if '?' in entity_id:
            return (
                "@id contains query parameters which may change over time",
                "Remove query parameters and use path + fragment instead"
            )
        return None

    def _check_fragment_quality(self, entity_id: str) -> Optional[tuple[str, str]]:
        """Check if the hash fragment is descriptive."""
        if '#' not in entity_id:
            return None
        fragment = entity_id.split('#')[1]
        if fragment.isdigit():
            return (
                "@id fragment is numeric-only which is not descriptive",
                "Use descriptive fragment like #organization or #product"
            )
        if 'timestamp' in entity_id.lower() or 'session' in entity_id.lower():
            return (
                "@id appears to contain unstable components (timestamp/session)",
                "Use stable identifiers without timestamps or session IDs"
            )
        return None

    def _check_https(self, entity_id: str) -> Optional[tuple[str, str]]:
        """Check if entity_id uses https."""
        if entity_id.startswith('http://'):
            return (
                "Using http:// instead of https://",
                "Use https:// for security and consistency"
            )
        return None

    def validate_entity_id(self, entity_id: str) -> Dict[str, Any]:
        """Validate an @id value against Schema.org and SEO best practices.

        Args:
            entity_id: The @id value to validate

        Returns:
            Dictionary with validation results:
            - entity_id: The validated @id
            - valid: Whether the @id follows all best practices
            - warnings: List of issues found
            - suggestions: Specific improvements to make
            - best_practices: Key principles to follow
        """
        warnings = []
        suggestions = []

        # Run all validation checks
        validators = [
            self._check_url_protocol,
            self._check_hash_fragment,
            self._check_query_params,
            self._check_fragment_quality,
            self._check_https,
        ]

        for validator in validators:
            result = validator(entity_id)
            if result:
                warnings.append(result[0])
                suggestions.append(result[1])

        return {
            'entity_id': entity_id,
            'valid': len(warnings) == 0,
            'warnings': warnings,
            'suggestions': suggestions,
            'best_practices': [
                "Use canonical URLs with hash fragments",
                "Keep IDs stable (no timestamps or session IDs)",
                "Use descriptive entity types in fragments",
                "One unchanging identifier per entity",
                "Avoid query parameters in @id values"
            ]
        }

    def _generate_entity_id_for_graph(
        self,
        entity: Dict[str, Any],
        base_url: str
    ) -> str:
        """Generate @id for an entity in the graph.

        Args:
            entity: Entity definition
            base_url: Base URL for @id generation

        Returns:
            Generated @id string
        """
        id_fragment = entity.get('id_fragment')
        slug = entity.get('slug')
        entity_type = entity.get('type', '')

        if id_fragment and not slug:
            return f"{base_url}#{id_fragment}"
        return self.generate_entity_id(base_url, entity_type, slug)

    def _build_entity_id_map(
        self,
        entities: List[Dict[str, Any]],
        base_url: str
    ) -> Dict[str, str]:
        """Build mapping from id_fragment to full @id for all entities.

        Args:
            entities: List of entity definitions
            base_url: Base URL for @id generation

        Returns:
            Dictionary mapping id_fragment to @id
        """
        entity_id_map = {}
        for entity in entities:
            if not entity.get('type'):
                raise ValueError("Each entity must have a 'type' field")

            entity_id = self._generate_entity_id_for_graph(entity, base_url)
            id_fragment = entity.get('id_fragment')
            if id_fragment:
                entity_id_map[id_fragment] = entity_id

        return entity_id_map

    def _resolve_relationship(
        self,
        rel_target: Any,
        entity_id_map: Dict[str, str]
    ) -> Any:
        """Resolve a relationship target to @id references.

        Args:
            rel_target: Target value (string or list)
            entity_id_map: Mapping of id_fragments to @ids

        Returns:
            Resolved relationship value
        """
        if isinstance(rel_target, list):
            return [
                {'@id': entity_id_map[t]} if t in entity_id_map else t
                for t in rel_target
            ]
        if rel_target in entity_id_map:
            return {'@id': entity_id_map[rel_target]}
        return rel_target

    def _build_entity_object(
        self,
        entity: Dict[str, Any],
        base_url: str,
        entity_id_map: Dict[str, str]
    ) -> Dict[str, Any]:
        """Build a single entity object for the graph.

        Args:
            entity: Entity definition
            base_url: Base URL for @id generation
            entity_id_map: Mapping of id_fragments to @ids

        Returns:
            Entity object with @type, @id, properties, and resolved relationships
        """
        entity_type = entity.get('type')
        entity_id = self._generate_entity_id_for_graph(entity, base_url)
        slug = entity.get('slug')

        entity_obj: Dict[str, Any] = {'@type': entity_type, '@id': entity_id}
        entity_obj.update(entity.get('properties', {}))

        # Add url from slug if not already specified
        if slug and 'url' not in entity_obj:
            entity_obj['url'] = entity_id.split('#')[0]

        # Resolve relationships
        for rel_property, rel_target in entity.get('relationships', {}).items():
            entity_obj[rel_property] = self._resolve_relationship(rel_target, entity_id_map)

        return entity_obj

    async def build_entity_graph(
        self,
        entities: List[Dict[str, Any]],
        base_url: str
    ) -> Dict[str, Any]:
        """Build a knowledge graph of related entities with proper @id references.

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
        await self.initialize()

        # First pass: Create @id values for all entities
        entity_id_map = self._build_entity_id_map(entities, base_url)

        # Second pass: Build graph entities with resolved relationships
        graph = [
            self._build_entity_object(entity, base_url, entity_id_map)
            for entity in entities
        ]

        return {'@context': 'https://schema.org', '@graph': graph}
