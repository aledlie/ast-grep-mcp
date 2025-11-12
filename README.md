# ast-grep + Schema.org MCP Server

An experimental [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that combines powerful structural code search capabilities using [ast-grep](https://ast-grep.github.io/) with Schema.org structured data tools.

## Overview

This MCP server provides AI assistants (like Cursor, Claude Desktop, etc.) with two complementary sets of capabilities:

### Code Search (ast-grep)
Search and analyze codebases using Abstract Syntax Tree (AST) pattern matching:
- Find code patterns based on syntax structure, not just text matching
- Search for specific programming constructs (functions, classes, imports, etc.)
- Write and test complex search rules using YAML configuration
- Debug and visualize AST structures for better pattern development
- Detect code duplication and suggest refactoring opportunities

### Structured Data (Schema.org)
Access the complete Schema.org vocabulary for SEO and semantic web:
- Query detailed information about any Schema.org type
- Search for types by keyword
- Explore type inheritance hierarchies
- List all properties available for a type
- Generate example JSON-LD structured data

## Prerequisites

1. **Install ast-grep**: Follow [ast-grep installation guide](https://ast-grep.github.io/guide/quick-start.html#installation)
   ```bash
   # macOS
   brew install ast-grep
   nix-shell -p ast-grep
   cargo install ast-grep --locked
   ```

2. **Install uv**: Python package manager
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **MCP-compatible client**: Such as Cursor, Claude Desktop, or other MCP clients

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/ast-grep/ast-grep-mcp.git
   cd ast-grep-mcp
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Verify ast-grep installation:
   ```bash
   ast-grep --version
   ```

## Running with `uvx`

You can run the server directly from GitHub using `uvx`:

```bash
uvx --from git+https://github.com/ast-grep/ast-grep-mcp ast-grep-server
```

This is useful for quickly trying out the server without cloning the repository.

## Configuration

### For Cursor

Add to your MCP settings (usually in `.cursor-mcp/settings.json`):

```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {}
    }
  }
}
```

### For Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {}
    }
  }
}
```

### Custom ast-grep Configuration

The MCP server supports using a custom `sgconfig.yaml` file to configure ast-grep behavior.
See the [ast-grep configuration documentation](https://ast-grep.github.io/guide/project/project-config.html) for details on the config file format.

You can provide the config file in two ways (in order of precedence):

1. **Command-line argument**: `--config /path/to/sgconfig.yaml`
2. **Environment variable**: `AST_GREP_CONFIG=/path/to/sgconfig.yaml`

## Usage

This repository includes comprehensive ast-grep rule documentation in [ast-grep.mdc](https://github.com/ast-grep/ast-grep-mcp/blob/main/ast-grep.mdc). The documentation covers all aspects of writing effective ast-grep rules, from simple patterns to complex multi-condition searches.

You can add it to your cursor rule or Claude.md, and attach it when you need AI agent to create ast-grep rule for you.

The prompt will ask LLM to use MCP to create, verify and improve the rule it creates.

## Features

The server provides 13 tools across two domains:

### Code Analysis Tools (ast-grep)

### 🔍 `dump_syntax_tree`
Visualize the Abstract Syntax Tree structure of code snippets. Essential for understanding how to write effective search patterns.

**Use cases:**
- Debug why a pattern isn't matching
- Understand the AST structure of target code
- Learn ast-grep pattern syntax

### 🧪 `test_match_code_rule`
Test ast-grep YAML rules against code snippets before applying them to larger codebases.

**Use cases:**
- Validate rules work as expected
- Iterate on rule development
- Debug complex matching logic

### 🎯 `find_code`
Search codebases using simple ast-grep patterns for straightforward structural matches.

**Parameters:**
- `max_results`: Limit number of complete matches returned (default: unlimited)
- `output_format`: Choose between `"text"` (default, ~75% fewer tokens) or `"json"` (full metadata)

**Text Output Format:**
```
Found 2 matches:

path/to/file.py:10-15
def example_function():
    # function body
    return result

path/to/file.py:20-22
def another_function():
    pass
```

**Use cases:**
- Find function calls with specific patterns
- Locate variable declarations
- Search for simple code constructs

### 🚀 `find_code_by_rule`
Advanced codebase search using complex YAML rules that can express sophisticated matching criteria.

**Parameters:**
- `max_results`: Limit number of complete matches returned (default: unlimited)
- `output_format`: Choose between `"text"` (default, ~75% fewer tokens) or `"json"` (full metadata)

**Use cases:**
- Find nested code structures
- Search with relational constraints (inside, has, precedes, follows)
- Complex multi-condition searches

### 🔁 `find_duplication`
Detect duplicate code and suggest modularization based on DRY (Don't Repeat Yourself) principles.

**Parameters:**
- `construct_type`: Type of code construct to analyze (`function_definition`, `class_definition`, `method_definition`)
- `min_similarity`: Similarity threshold (0.0-1.0) to consider code as duplicate (default: 0.8)
- `min_lines`: Minimum lines to consider for duplication (default: 5)

**Returns:**
- Summary statistics (total constructs analyzed, duplicate groups found, potential line savings)
- Detailed duplication groups with similarity scores and locations
- Specific refactoring suggestions for each duplication group

**Use cases:**
- Identify duplicate functions, classes, or methods across a codebase
- Get quantified metrics on code duplication (lines duplicated, potential savings)
- Receive actionable refactoring suggestions to eliminate duplication
- Enforce DRY principles during code review

### Schema.org Tools

### 📋 `get_schema_type`
Get detailed information about a specific Schema.org type.

**Use cases:**
- Learn about Schema.org types before implementing them
- Understand type properties and relationships
- Validate that a type exists and fits your use case

**Example:**
```
get_schema_type('Person')
→ Returns name, description, URL, parent types, and full metadata
```

### 🔎 `search_schemas`
Search for Schema.org types by keyword.

**Parameters:**
- `query`: Search term (searches in type names and descriptions)
- `limit`: Maximum results to return (default: 10, max: 100)

**Use cases:**
- Discover relevant Schema.org types for your content
- Find specialized types for specific domains
- Explore the Schema.org vocabulary

**Example:**
```
search_schemas('article')
→ Finds Article, NewsArticle, ScholarlyArticle, TechArticle, etc.
```

### 🌳 `get_type_hierarchy`
Get the inheritance hierarchy for a Schema.org type.

**Use cases:**
- Understand type relationships and inheritance
- Find parent types to understand inherited properties
- Discover child types for more specific markup

**Example:**
```
get_type_hierarchy('NewsArticle')
→ Shows: NewsArticle → Article → CreativeWork → Thing
```

### 🏷️ `get_type_properties`
Get all properties available for a Schema.org type.

**Parameters:**
- `type_name`: The Schema.org type name
- `include_inherited`: Include properties from parent types (default: true)

**Use cases:**
- Discover all available properties for a type
- Understand property constraints and expected types
- Plan your structured data implementation

**Example:**
```
get_type_properties('Organization')
→ Returns properties like name, url, address, founder, employee, etc.
```

### ✨ `generate_schema_example`
Generate example JSON-LD structured data for a Schema.org type.

**Parameters:**
- `type_name`: The Schema.org type name
- `custom_properties`: Optional custom property values (JSON object)

**Use cases:**
- Get a starting point for implementing structured data
- See valid JSON-LD format for a type
- Quickly generate markup with custom values

**Example:**
```
generate_schema_example('Recipe', {
  'name': 'Chocolate Chip Cookies',
  'prepTime': 'PT20M',
  'cookTime': 'PT10M'
})
→ Returns complete JSON-LD with @context and common properties
```

### 🔗 `generate_entity_id`
Generate proper @id values for Schema.org entities following SEO and knowledge graph best practices.

**Parameters:**
- `base_url`: Canonical URL (e.g., 'https://example.com')
- `entity_type`: Schema.org type (e.g., 'Organization', 'Person')
- `entity_slug`: Optional URL path segment for specific instances

**Use cases:**
- Create stable identifiers for entities across your site
- Enable cross-page entity references
- Build a knowledge graph with consistent IDs

**Example:**
```
generate_entity_id('https://example.com', 'Organization')
→ 'https://example.com/#organization'

generate_entity_id('https://example.com', 'Person', 'team/john-doe')
→ 'https://example.com/team/john-doe#person'
```

**Best Practices** (from [Momentic Marketing](https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs)):
- Use canonical URLs + hash fragments
- Keep IDs stable (no timestamps or dynamic values)
- Use descriptive fragments for debugging
- One unchanging identifier per entity

### ✅ `validate_entity_id`
Validate @id values against Schema.org and SEO best practices.

**Use cases:**
- Check existing @id implementations
- Identify issues before deploying structured data
- Learn best practices for entity identifiers

**Example:**
```
validate_entity_id('https://example.com/#organization')
→ { "valid": true, "warnings": [], "suggestions": [] }

validate_entity_id('example.com/page')
→ {
  "valid": false,
  "warnings": ["Missing protocol", "Missing hash fragment"],
  "suggestions": ["Add https://", "Add descriptive fragment like #organization"]
}
```

### 🕸️ `build_entity_graph`
Build a knowledge graph of related entities with proper @id references.

**Parameters:**
- `entities`: List of entity definitions with types, properties, and relationships
- `base_url`: Base URL for generating @id values

**Use cases:**
- Create complex multi-entity structured data
- Build relationships between entities (founder, employee, author, etc.)
- Maintain consistent entity references across your site
- Build a knowledge base over time

**Entity Format:**
```json
{
  "type": "Organization",
  "slug": "about",
  "id_fragment": "org-acme",
  "properties": {
    "name": "Acme Corp",
    "url": "https://example.com"
  },
  "relationships": {
    "founder": "person-john"
  }
}
```

**Example:**
```
build_entity_graph([
  {
    "type": "Organization",
    "properties": {"name": "Acme Corp"},
    "relationships": {"founder": "person-john"}
  },
  {
    "type": "Person",
    "id_fragment": "person-john",
    "slug": "team/john-doe",
    "properties": {"name": "John Doe", "jobTitle": "CEO"}
  }
], "https://example.com")
```

**Returns:**
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://example.com/#organization",
      "name": "Acme Corp",
      "founder": {
        "@id": "https://example.com/team/john-doe#person"
      }
    },
    {
      "@type": "Person",
      "@id": "https://example.com/team/john-doe#person",
      "name": "John Doe",
      "jobTitle": "CEO",
      "url": "https://example.com/team/john-doe"
    }
  ]
}
```


## Usage Examples

### Basic Pattern Search

Use Query:

> Find all console.log statements

AI will generate rules like:

```yaml
id: find-console-logs
language: javascript
rule:
  pattern: console.log($$$)
```

### Complex Rule Example

User Query:
> Find async functions that use await

AI will generate rules like:

```yaml
id: async-with-await
language: javascript
rule:
  all:
    - kind: function_declaration
    - has:
        pattern: async
    - has:
        pattern: await $EXPR
        stopBy: end
```

### Duplication Detection Example

User Query:
> Find duplicate functions in my Python codebase

AI will use the `find_duplication` tool:

```
find_duplication(
  project_folder="/path/to/project",
  language="python",
  construct_type="function_definition",
  min_similarity=0.8,
  min_lines=5
)
```

Result might show:
```json
{
  "summary": {
    "total_constructs": 45,
    "duplicate_groups": 3,
    "total_duplicated_lines": 120,
    "potential_line_savings": 80
  },
  "refactoring_suggestions": [
    {
      "type": "Extract Shared Function",
      "description": "Extract 3 similar functions into a shared utility function",
      "duplicate_count": 3,
      "locations": [
        "utils.py:15-25",
        "helpers.py:30-40",
        "services.py:50-60"
      ]
    }
  ]
}
```

### Schema.org Implementation Example

User Query:
> I need to add Schema.org markup for a blog post

AI workflow using schema.org tools:

1. Search for relevant types:
```
search_schemas('blog')
→ Finds BlogPosting, Blog, etc.
```

2. Get type details:
```
get_schema_type('BlogPosting')
→ Returns description, properties, and parent types
```

3. Check available properties:
```
get_type_properties('BlogPosting')
→ Lists: headline, author, datePublished, articleBody, etc.
```

4. Generate example markup:
```
generate_schema_example('BlogPosting', {
  'headline': 'My Amazing Blog Post',
  'author': {'@type': 'Person', 'name': 'John Doe'},
  'datePublished': '2024-01-15'
})
```

Result:
```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "My Amazing Blog Post",
  "author": {
    "@type": "Person",
    "name": "John Doe"
  },
  "datePublished": "2024-01-15",
  "description": "Example description",
  "url": "https://example.com"
}
```

### Building a Knowledge Graph with @id

User Query:
> Create a knowledge graph for my organization with team members and products

AI workflow using ID-based tools:

1. **Generate entity IDs:**
```
generate_entity_id('https://example.com', 'Organization')
→ 'https://example.com/#organization'

generate_entity_id('https://example.com', 'Person', 'team/ceo')
→ 'https://example.com/team/ceo#person'

generate_entity_id('https://example.com', 'Product', 'products/widget')
→ 'https://example.com/products/widget#product'
```

2. **Validate IDs before using:**
```
validate_entity_id('https://example.com/#organization')
→ { "valid": true, "warnings": [], "suggestions": [] }
```

3. **Build the complete knowledge graph:**
```
build_entity_graph([
  {
    "type": "Organization",
    "properties": {
      "name": "Acme Corp",
      "description": "Leading widget manufacturer",
      "url": "https://example.com"
    },
    "relationships": {
      "founder": "person-ceo",
      "makesOffer": "product-widget"
    }
  },
  {
    "type": "Person",
    "id_fragment": "person-ceo",
    "slug": "team/ceo",
    "properties": {
      "name": "Jane Doe",
      "jobTitle": "CEO"
    }
  },
  {
    "type": "Product",
    "id_fragment": "product-widget",
    "slug": "products/widget",
    "properties": {
      "name": "Super Widget",
      "price": "$99.99"
    },
    "relationships": {
      "manufacturer": "organization"
    }
  }
], "https://example.com")
```

**Result:** A complete @graph with bidirectional entity relationships that can be:
- Embedded across multiple pages
- Referenced consistently using @id
- Built up over time as you add new entities
- Used by search engines and LLMs to understand your content structure

**Key Benefits:**
- **Consistency**: Same @id used everywhere for each entity
- **Relationships**: Entities reference each other via @id, not duplication
- **Scalability**: Add new entities without modifying existing ones
- **SEO**: Search engines understand entity relationships
- **Knowledge Graphs**: Build a queryable knowledge base over time

## Supported Languages

ast-grep supports many programming languages including:
- JavaScript/TypeScript
- Python
- Rust
- Go
- Java
- C/C++
- C#
- And many more...

For a complete list of built-in supported languages, see the [ast-grep language support documentation](https://ast-grep.github.io/reference/languages.html).

You can also add support for custom languages through the `sgconfig.yaml` configuration file. See the [custom language guide](https://ast-grep.github.io/guide/project/project-config.html#languagecustomlanguage) for details.

## Troubleshooting

### Common Issues

1. **"Command not found" errors**: Ensure ast-grep is installed and in your PATH
2. **No matches found**: Try adding `stopBy: end` to relational rules
3. **Pattern not matching**: Use `dump_syntax_tree` to understand the AST structure
4. **Permission errors**: Ensure the server has read access to target directories

## Contributing

This is an experimental project. Issues and pull requests are welcome!

## Related Projects

- [ast-grep](https://ast-grep.github.io/) - The core structural search tool
- [Schema.org](https://schema.org/) - Structured data vocabulary for the web
- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol this server implements
- [FastMCP](https://github.com/pydantic/fastmcp) - The Python MCP framework used

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/ast-grep-ast-grep-mcp-badge.png)](https://mseep.ai/app/ast-grep-ast-grep-mcp)
