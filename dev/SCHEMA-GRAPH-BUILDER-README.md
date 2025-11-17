# Schema.org Entity Graph Builder

**Comprehensive automation tool for building unified Schema.org knowledge graphs**

---

## Overview

The `schema-graph-builder.py` script automates the entire process of analyzing, enhancing, and building unified entity graphs from Schema.org JSON files. It combines discovery, validation, graph building, relationship analysis, and documentation generation into a single command.

### What It Does

1. **Discovers** Schema.org JSON files in any directory
2. **Extracts** all entities with @type and @id properties
3. **Validates** @id values against SEO best practices
4. **Builds** unified entity graphs with @graph structure
5. **Analyzes** relationships between entities
6. **Generates** comprehensive documentation

### Based On

This script consolidates the workflow we used for two real-world projects:
- **Fisterra Dance Organization** (https://fisterra-dance.com) - 22 entities, 17 types, 26 relationships
- **PersonalSite** (https://www.aledlie.com) - 16 entities, 13 types, 33 relationships

---

## Installation

No installation required beyond Python 3.7+. The script is standalone.

```bash
# Make executable
chmod +x schema-graph-builder.py

# Or run with python3
python3 schema-graph-builder.py --help
```

---

## Usage

### Basic Usage

```bash
python3 schema-graph-builder.py <directory> <base_url>
```

**Arguments**:
- `directory`: Root directory containing Schema.org JSON files
- `base_url`: Base URL for the site (used for @id generation/validation)

### Examples

**PersonalSite** (Jekyll static site):
```bash
python3 schema-graph-builder.py \
  ~/code/PersonalSite/schemas-static \
  https://www.aledlie.com
```

**Fisterra** (Wix site with test samples):
```bash
python3 schema-graph-builder.py \
  ~/code/IntegrityStudioClients/fisterra/test-samples \
  https://fisterra-dance.com \
  --name "Fisterra Dance"
```

**Custom Output Directory**:
```bash
python3 schema-graph-builder.py \
  ~/code/mysite/schemas \
  https://example.com \
  --output-dir ~/code/mysite/graph-analysis
```

**Exclude Additional Files**:
```bash
python3 schema-graph-builder.py \
  ~/code/mysite \
  https://example.com \
  --exclude test.json sample.json
```

**JSON Output Mode** (for programmatic use):
```bash
python3 schema-graph-builder.py \
  ~/code/mysite \
  https://example.com \
  --json
```

---

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output-dir DIR` | Output directory for generated files | `<directory>/schema-analysis` |
| `--name NAME` | Project name for documentation | Extracted from base_url |
| `--exclude PATTERN ...` | Additional filename patterns to exclude | None |
| `--json` | Output summary as JSON | False |

---

## Output Files

The script generates 4 files in the output directory:

### 1. `unified-entity-graph.json`

Complete entity graph with @context and @graph structure, ready for deployment.

**Format**:
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@id": "https://example.com#person",
      "@type": "Person",
      "name": "...",
      "worksFor": {
        "@id": "https://example.com/organizations/company#organization"
      }
    }
  ]
}
```

### 2. `entity-graph-analysis.json`

Detailed relationship analysis with statistics.

**Contents**:
- `total_entities`: Total unique entities
- `entities_by_type`: Count of each Schema.org type
- `total_relationships`: Total relationships found
- `relationships`: Array of all relationships with source, property, target
- `relationships_by_property`: Count of each relationship type

### 3. `entity-id-validation.json`

Validation results for all @id values.

**Format**:
```json
[
  {
    "valid": true,
    "entity_id": "https://example.com#person",
    "entity_type": "Person",
    "warnings": []
  }
]
```

### 4. `ENTITY-GRAPH-SUMMARY.md`

Comprehensive markdown documentation including:
- Executive summary
- Graph statistics
- Entity breakdown by type
- Source file listing
- Relationship analysis
- Entity relationship map
- Validation results
- Build statistics

---

## How It Works

### 1. Schema Discovery

Recursively scans the directory for JSON files containing `@context` or `@type` properties.

**Automatically Excludes**:
- `unified-entity-graph.json` (output file)
- `entity-graph-analysis.json` (output file)
- `package.json`, `package-lock.json`, `tsconfig.json` (configuration files)
- Files in `node_modules`, `.git`, `dist`, `build` directories

### 2. Entity Extraction

Recursively extracts all objects with both `@type` and `@id` properties.

**Features**:
- Handles nested entities (extracts and references)
- Processes arrays of entities
- Preserves @id references for relationships
- Tracks parent paths for debugging

### 3. Deduplication

Merges entities with the same `@id` value, combining properties.

**Strategy**:
- Uses @id as unique key
- Keeps entity with more properties as base
- Adds missing properties from other instances

### 4. @id Validation

Validates all @id values against best practices:

**Checks**:
- ✅ HTTPS protocol usage
- ✅ Hash fragment presence (`#entity_type`)
- ✅ No query parameters (unstable)
- ✅ No timestamps (unstable)

**Best Practices** (from [Momentic Marketing](https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs)):
- Format: `{canonical_url}#{entity_type}`
- Or: `{canonical_url}/{slug}#{entity_type}`
- Stable, unchanging identifiers
- Descriptive fragments for clarity

### 5. Relationship Analysis

Identifies all relationships between entities by finding properties with @id references.

**Analyzes**:
- Direct relationships (single @id reference)
- Array relationships (multiple @id references)
- Relationship frequency (by property type)
- Entity connections (source → property → target)

### 6. Documentation Generation

Creates comprehensive markdown documentation with:
- Statistics tables
- Entity breakdowns
- Source file details
- Relationship maps
- Validation summaries

---

## Real-World Results

### PersonalSite (aledlie.com)

**Input**: 5 JSON schema files
**Output**:
- 16 unique entities
- 13 Schema.org types
- 33 relationships
- 100% @id validation pass

**Entity Types**: Person, WebSite, Blog, BlogPosting, TechArticle, Organization (2), Occupation (3), ContactPoint, Place, SearchAction, ReadAction, ViewAction, EntryPoint

**Hub Entities**:
- Person (9 relationships)
- WebSite (10 relationships)

### Fisterra Dance (fisterra-dance.com)

**Input**: 3 JSON schema files
**Output**:
- 22 unique entities
- 17 Schema.org types
- 26 relationships
- 100% @id validation pass

**Entity Types**: Organization, PerformingGroup, Person (3), Place, DanceEvent, Course, CourseInstance, Offer (2), RegisterAction (2), ContactPoint, PostalAddress (2), GeoCoordinates, EntryPoint (2), Schedule, Audience, City, State

**Hub Entities**:
- Organization/PerformingGroup (referenced by events, courses, people)
- Place (shared by multiple events/courses)

---

## SEO Benefits

### Knowledge Graph Building

- **Entity Recognition**: Search engines can identify distinct entities
- **Relationship Mapping**: Clear connections between entities
- **Cross-Page References**: Entities can reference each other across pages
- **Semantic Clarity**: Explicit entity types and relationships

### Rich Results Eligibility

**Person Entities**:
- Person cards with knowledge panels
- Social profile links
- Organization affiliations

**Organization Entities**:
- Organization snippets
- Contact information
- Founder/employee connections

**Event/Course Entities**:
- Event rich results
- Course listings
- Registration actions

**Blog/Article Entities**:
- Article rich results
- Author attribution
- Publication information

---

## Integration Patterns

### Static JSON Deployment

Directly deploy the unified-entity-graph.json:

```html
<script type="application/ld+json" src="/unified-entity-graph.json"></script>
```

### Liquid Template Conversion (Jekyll)

Use the JSON structure as a template for Liquid:

```liquid
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@id": "{{ site.url }}#person",
      "@type": "Person",
      "name": "{{ site.author.name }}",
      ...
    }
  ]
}
```

### Dynamic Template Conversion (Other platforms)

Adapt the structure to your templating language (Jinja2, Handlebars, etc.)

---

## Validation

The script performs automatic validation, but you should also test with external validators:

### JSON-LD Validation

```bash
python3 -m json.tool unified-entity-graph.json > /dev/null
echo $?  # Should output 0
```

### Google Rich Results Test

1. Deploy your schema to a public URL
2. Visit: https://search.google.com/test/rich-results
3. Enter your URL
4. Check for entity recognition and rich result eligibility

### Schema.org Validator

1. Visit: https://validator.schema.org/
2. Paste your JSON-LD or enter URL
3. Verify structure and relationships

---

## Troubleshooting

### No JSON files found

**Problem**: Script reports "No Schema.org JSON files found"

**Solutions**:
- Verify directory path is correct
- Check files have `@context` or `@type` properties
- Ensure files have `.json` extension
- Files aren't in excluded directories (`node_modules`, `.git`, etc.)

### @id validation warnings

**Problem**: Some @id values have warnings

**Common Issues**:
- Missing hash fragment: Add `#{entity_type}` to end of @id
- Not using HTTPS: Update to `https://` protocol
- Contains query parameters: Remove `?key=value` portions
- Contains timestamps: Use stable identifiers without dates

### Entities not merging

**Problem**: Duplicate entities not merging as expected

**Cause**: @id values don't match exactly (case-sensitive)

**Solution**: Ensure consistent @id formatting across all files

### Missing relationships

**Problem**: Expected relationships not showing in analysis

**Cause**: Properties don't contain @id references

**Solution**: Convert inline objects to @id references:

```json
// Before
"author": {
  "@type": "Person",
  "name": "John"
}

// After
"author": {
  "@id": "https://example.com#person"
}
```

---

## Advanced Usage

### Processing Entire Site Hierarchies

To process all JSON files in a complex directory structure:

```bash
# Find all JSON files first
find ~/code/mysite -name "*.json" -type f

# Run builder on root directory
python3 schema-graph-builder.py \
  ~/code/mysite \
  https://example.com
```

### Batch Processing Multiple Sites

Create a wrapper script:

```bash
#!/bin/bash

sites=(
  "~/code/site1|https://site1.com"
  "~/code/site2|https://site2.com"
)

for site_config in "${sites[@]}"; do
  IFS='|' read -r dir url <<< "$site_config"
  python3 schema-graph-builder.py "$dir" "$url"
done
```

### Custom Post-Processing

Use the `--json` flag to get machine-readable output for further processing:

```bash
python3 schema-graph-builder.py \
  ~/code/mysite \
  https://example.com \
  --json > stats.json

# Process with jq
cat stats.json | jq '.analysis.entities_by_type'
```

---

## Script Architecture

### Class: `SchemaGraphBuilder`

Main class containing all functionality.

**Key Methods**:

| Method | Purpose |
|--------|---------|
| `discover_json_schemas()` | Find Schema.org JSON files |
| `generate_entity_id()` | Create @id values |
| `validate_entity_id()` | Validate @id against best practices |
| `extract_entities_from_schema()` | Recursively extract entities |
| `merge_duplicate_entities()` | Deduplicate by @id |
| `build_entity_graph()` | Build unified @graph |
| `analyze_relationships()` | Find all entity connections |
| `generate_documentation()` | Create markdown docs |
| `validate_all_entity_ids()` | Batch validate all @ids |

### Statistics Tracking

The builder tracks comprehensive statistics:

```python
{
  'files_found': 5,
  'entities_extracted': 16,
  'entities_unique': 16,
  'relationships': 33,
  'ids_validated': 16,
  'validation_warnings': []
}
```

---

## Related Resources

### Schema.org Documentation
- **Official Site**: https://schema.org/
- **Vocabulary**: https://schema.org/docs/schemas.html
- **JSON-LD Guide**: https://json-ld.org/

### @id Best Practices
- **Momentic Marketing Guide**: [Schema.org @id for SEO, LLMs, and Knowledge Graphs](https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs)
- Key takeaways: Stable identifiers, hash fragments, cross-page references

### Validation Tools
- **Google Rich Results**: https://search.google.com/test/rich-results
- **Schema.org Validator**: https://validator.schema.org/
- **JSON-LD Playground**: https://json-ld.org/playground/

### ast-grep MCP Server
This script was created using the ast-grep-mcp Schema.org tools:
- **Repository**: https://github.com/ast-grep/ast-grep-mcp
- **Tools Used**: `generate_entity_id`, `validate_entity_id`, `build_entity_graph`

---

## License

This script is part of the ast-grep-mcp project and follows the same license.

---

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review the examples
3. Open an issue on the ast-grep-mcp GitHub repository

---

**Created**: 2025-11-16
**Version**: 1.0.0
**Tested On**: PersonalSite (aledlie.com), Fisterra Dance (fisterra-dance.com)
