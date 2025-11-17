# Schema.org Tools CLI

**Quick command-line access to Schema.org vocabulary tools**

---

## Overview

The `schema-tools.py` script provides a simple command-line interface to three essential Schema.org MCP tools:

1. **`search`** - Search for Schema.org types by keyword
2. **`type`** - Get detailed information about a specific type
3. **`properties`** - Get all properties available for a type

This is a standalone executable that uses the SchemaOrgClient from the main MCP server.

---

## Installation

No installation required beyond the main project dependencies:

```bash
# Install project dependencies
uv sync

# Make executable (already done)
chmod +x schema-tools.py
```

---

## Quick Start

### Search for Schema Types

```bash
# Basic search
uv run python schema-tools.py search "article"

# Limit results
uv run python schema-tools.py search "organization" --limit 5

# JSON output
uv run python schema-tools.py search "person" --json
```

### Get Type Information

```bash
# Get type details
uv run python schema-tools.py type Person

# Get type with JSON output
uv run python schema-tools.py type BlogPosting --json
```

### Get Type Properties

```bash
# Get all properties (including inherited)
uv run python schema-tools.py properties Person

# Get only direct properties
uv run python schema-tools.py properties Organization --no-inherited

# JSON output
uv run python schema-tools.py properties Article --json
```

---

## Command Reference

### `search` - Search for Schema Types

**Usage:**
```bash
uv run python schema-tools.py search <query> [--limit N] [--json]
```

**Arguments:**
- `query` - Search term (searches in type names and descriptions)

**Options:**
- `--limit N` - Maximum results to return (1-100, default: 10)
- `--json` - Output as JSON instead of formatted text

**Examples:**
```bash
# Find article types
uv run python schema-tools.py search "article"

# Search for event-related types
uv run python schema-tools.py search "event" --limit 5

# Get results as JSON
uv run python schema-tools.py search "organization" --json
```

**Output Format (text):**
```
Found 3 result(s):

1. TechArticle
   URL: https://schema.org/TechArticle
   Description: A technical article - Example: How-to (task) topics...
   Relevance: 0.00

2. NewsArticle
   URL: https://schema.org/NewsArticle
   Description: A NewsArticle is an article whose content reports news...
   Relevance: 0.00
```

---

### `type` - Get Type Information

**Usage:**
```bash
uv run python schema-tools.py type <type_name> [--json]
```

**Arguments:**
- `type_name` - Schema.org type name (e.g., Person, Organization, Article)

**Options:**
- `--json` - Output as JSON instead of formatted text

**Examples:**
```bash
# Get Person type info
uv run python schema-tools.py type Person

# Get BlogPosting info
uv run python schema-tools.py type BlogPosting

# JSON output
uv run python schema-tools.py type Organization --json
```

**Output Format (text):**
```
Person
======

URL: https://schema.org/Person

Description:
A person (alive, dead, undead, or fictional).
```

---

### `properties` - Get Type Properties

**Usage:**
```bash
uv run python schema-tools.py properties <type_name> [--no-inherited] [--json]
```

**Arguments:**
- `type_name` - Schema.org type name

**Options:**
- `--no-inherited` - Exclude properties inherited from parent types
- `--json` - Output as JSON instead of formatted text

**Examples:**
```bash
# Get all Person properties (including inherited)
uv run python schema-tools.py properties Person

# Get only direct Organization properties
uv run python schema-tools.py properties Organization --no-inherited

# JSON output
uv run python schema-tools.py properties Article --json
```

**Output Format (text):**
```
Properties for Person

=====================

Total Properties: 67
----------------------------------------

• additionalName
  Description: An additional name for a Person, can be used for a middle name.

• address
  Description: Physical address of the item.

• affiliation
  Inherited from: Thing
  Description: An organization that this person is affiliated with...

Total: 67 properties
```

---

## Common Use Cases

### Exploring Schema Types

**Find relevant types for your content:**
```bash
# What types are available for blog posts?
uv run python schema-tools.py search "blog"

# What types exist for organizations?
uv run python schema-tools.py search "organization"

# Find event-related types
uv run python schema-tools.py search "event"
```

### Understanding Type Structure

**Learn about a specific type before implementing:**
```bash
# What is a TechArticle?
uv run python schema-tools.py type TechArticle

# What properties does it have?
uv run python schema-tools.py properties TechArticle
```

### Planning Structured Data

**Discover available properties for your implementation:**
```bash
# What can I add to a Person schema?
uv run python schema-tools.py properties Person

# What properties are specific to Organization?
uv run python schema-tools.py properties Organization --no-inherited
```

### Programmatic Integration

**Use JSON output for scripts and automation:**
```bash
# Get search results as JSON
uv run python schema-tools.py search "article" --json > article-types.json

# Get all properties as JSON for processing
uv run python schema-tools.py properties Person --json | jq '.[] | .name'
```

---

## Output Formats

### Text Format (Default)

Human-readable formatted output with:
- Clear section headers
- Descriptive labels
- Organized information hierarchy
- Easy to read in terminal

### JSON Format (--json flag)

Machine-readable JSON output for:
- Programmatic processing
- Integration with other tools
- Piping to jq or other JSON processors
- Automation scripts

---

## Examples

### Example 1: Find and Explore Article Types

```bash
# Step 1: Search for article types
uv run python schema-tools.py search "article" --limit 5

# Output shows: Article, NewsArticle, TechArticle, ScholarlyArticle, etc.

# Step 2: Get details on TechArticle
uv run python schema-tools.py type TechArticle

# Step 3: See what properties are available
uv run python schema-tools.py properties TechArticle
```

### Example 2: Plan Organization Schema

```bash
# Step 1: Confirm Organization type exists
uv run python schema-tools.py type Organization

# Step 2: Get all available properties
uv run python schema-tools.py properties Organization

# Step 3: Export properties for reference
uv run python schema-tools.py properties Organization --json > org-props.json
```

### Example 3: Compare Direct vs Inherited Properties

```bash
# Get only direct properties
uv run python schema-tools.py properties BlogPosting --no-inherited

# Get all properties (including inherited)
uv run python schema-tools.py properties BlogPosting
```

---

## Integration with MCP Server

This CLI tool uses the same `SchemaOrgClient` class as the MCP server, ensuring:

- **Consistency**: Same data source and behavior
- **Reliability**: Tested Schema.org vocabulary access
- **Performance**: Shared caching and optimization

The tool is particularly useful for:
- Quick lookups during development
- Exploring Schema.org vocabulary offline (after first fetch)
- Testing before implementing in production
- Documentation and reference

---

## Troubleshooting

### Import Error

**Problem:**
```
Error: Could not import SchemaOrgClient from main.py
```

**Solution:**
Always run with `uv run` from the project directory:
```bash
uv run python schema-tools.py search "article"
```

### Type Not Found

**Problem:**
```
Error: Type 'Xyz' not found in Schema.org vocabulary
```

**Solution:**
- Check spelling and capitalization (e.g., `Person` not `person`)
- Use search first to find the correct type name:
  ```bash
  uv run python schema-tools.py search "xyz"
  ```

### Network Error on First Run

**Problem:**
```
Error connecting to schema.org
```

**Solution:**
- Check internet connection
- The tool needs to fetch the Schema.org vocabulary on first run
- Subsequent runs use cached data

---

## Related Tools

- **MCP Server**: Full 13-tool MCP server (includes these tools plus ast-grep tools)
- **schema-graph-builder.py**: Build unified entity graphs from JSON files
- **Schema.org Validator**: https://validator.schema.org/

---

## Quick Reference

```bash
# Search
uv run python schema-tools.py search "query" [--limit N] [--json]

# Type info
uv run python schema-tools.py type <TypeName> [--json]

# Properties
uv run python schema-tools.py properties <TypeName> [--no-inherited] [--json]

# Help
uv run python schema-tools.py --help
uv run python schema-tools.py search --help
uv run python schema-tools.py type --help
uv run python schema-tools.py properties --help
```

---

**Created**: 2025-11-16
**Version**: 1.0.0
**Part of**: ast-grep-mcp project
