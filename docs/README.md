# ast-grep + Schema.org MCP Server

MCP server combining [ast-grep](https://ast-grep.github.io/) structural code search with Schema.org structured data tools for AI assistants (Cursor, Claude Desktop, etc.).

## Overview

**Code Search (ast-grep):** AST-based pattern matching, code construct search, duplication detection, YAML rules, syntax tree debugging

**Structured Data (Schema.org):** Query 2600+ types/properties, search by keyword, explore hierarchies, generate JSON-LD examples, build knowledge graphs

## Quick Start

```bash
# Install prerequisites
brew install ast-grep  # or: cargo install ast-grep --locked
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/ast-grep/ast-grep-mcp.git
cd ast-grep-mcp
uv sync

# Run directly from GitHub (no clone)
uvx --from git+https://github.com/ast-grep/ast-grep-mcp ast-grep-server
```

## Configuration

Add to `.cursor-mcp/settings.json` or `~/Library/Application Support/Claude/claude_desktop_config.json`:

**With Doppler (recommended for production):**
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "doppler",
      "args": ["run", "--project", "bottleneck", "--config", "dev", "--command",
               "uv --directory /path/to/ast-grep-mcp run main.py"]
    }
  }
}
```

**Without Doppler (local development):**
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {
        "SENTRY_DSN": "optional-for-error-tracking",
        "SENTRY_ENVIRONMENT": "production"
      }
    }
  }
}
```

**Custom ast-grep config:** Use `--config /path/to/sgconfig.yaml` or `AST_GREP_CONFIG` env var. See [ast-grep config docs](https://ast-grep.github.io/guide/project/project-config.html).

**Rule writing guide:** See [ast-grep.mdc](https://github.com/ast-grep/ast-grep-mcp/blob/main/ast-grep.mdc) for comprehensive rule patterns.

## Error Tracking (Optional)

**Sentry integration** (optional, zero overhead when disabled) provides:
- Error tracking for all 18 tools
- Performance monitoring (subprocess, API, batch operations)
- AI interaction tracking (with Anthropic SDK)
- Service tagging: `service:ast-grep-mcp`

**Setup:**
```bash
# With Doppler (recommended)
brew install dopplerhq/cli/doppler
doppler login
doppler secrets set SENTRY_DSN="your-dsn" --project bottleneck --config dev

# Manual
export SENTRY_DSN="your-dsn"
export SENTRY_ENVIRONMENT="production"
```

**Docs:** [SENTRY-INTEGRATION.md](SENTRY-INTEGRATION.md), [DOPPLER-MIGRATION.md](DOPPLER-MIGRATION.md)

## Tools (18 Total)

### Code Analysis (ast-grep)

**🔍 `dump_syntax_tree`** - Visualize AST structure for debugging patterns
**🧪 `test_match_code_rule`** - Test YAML rules against code snippets
**🎯 `find_code`** - Simple pattern search (params: `max_results`, `output_format`: text/json)
**🚀 `find_code_by_rule`** - Advanced YAML rule search with relational constraints
**🔁 `find_duplication`** - Detect duplicate code with similarity scoring and refactoring suggestions
**🧪 `test_sentry_integration`** - Verify Sentry error tracking configuration

### Schema.org (8 tools)

**📋 `get_schema_type`** - Get type details (description, properties, parent types)
**🔎 `search_schemas`** - Find types by keyword (params: `query`, `limit`)
**🌳 `get_type_hierarchy`** - Show inheritance chain (e.g., NewsArticle → Article → CreativeWork → Thing)
**🏷️ `get_type_properties`** - List all properties for a type (params: `include_inherited`)
**✨ `generate_schema_example`** - Generate JSON-LD with optional custom properties
**🔗 `generate_entity_id`** - Create stable @id values (`{canonical_url}#{entity_type}`)
**✅ `validate_entity_id`** - Check @id against best practices
**🕸️ `build_entity_graph`** - Build knowledge graphs with proper @id references

**Best practices:** Use canonical URLs + hash fragments, keep IDs stable, avoid timestamps


## Usage Examples

**Pattern search:**
```yaml
# Find console.log statements
pattern: console.log($$$)
```

**Complex rules:**
```yaml
# Find async functions with await
all:
  - kind: function_declaration
  - has: { pattern: async }
  - has: { pattern: await $EXPR, stopBy: end }
```

**Duplication detection:**
```python
find_duplication(project_folder="/path", language="python",
                 construct_type="function_definition", min_similarity=0.8)
# Returns: summary stats, duplicate groups, refactoring suggestions
```

**Schema.org workflow:**
```python
search_schemas('blog')              # Find BlogPosting
get_type_properties('BlogPosting')  # List properties
generate_schema_example('BlogPosting', {'headline': '...', 'author': {...}})
# Returns: Complete JSON-LD markup
```

**Knowledge graph:**
```python
generate_entity_id('https://example.com', 'Organization')  # Generate @id
validate_entity_id('https://example.com/#organization')    # Validate
build_entity_graph([...], 'https://example.com')          # Build @graph
# Returns: Multi-entity JSON-LD with proper @id references
```

## Supported Languages

JavaScript/TypeScript, Python, Rust, Go, Java, C/C++, C#, and [many more](https://ast-grep.github.io/reference/languages.html). Add custom languages via `sgconfig.yaml` ([guide](https://ast-grep.github.io/guide/project/project-config.html#languagecustomlanguage)).

## Troubleshooting

**Common:**
- Command not found: Ensure `ast-grep` in PATH
- No matches: Add `stopBy: end` to relational rules
- Pattern issues: Use `dump_syntax_tree` to debug

**Sentry:** Run `test_sentry_integration()`, check `SENTRY_DSN`. See [SENTRY-INTEGRATION.md](SENTRY-INTEGRATION.md).

**Doppler:** Verify auth (`doppler login`), check secrets (`doppler secrets --project bottleneck --config dev`). See [DOPPLER-MIGRATION.md](DOPPLER-MIGRATION.md).

## Repository

- `main.py` - Single-file server (~4000 lines)
- `tests/` - 267 tests (254 unit, 13 integration)
- `scripts/` - Standalone utilities
- `mcp-docs/` - Reference for 30+ MCP servers
- `dev/` - Development docs

**Repomix snapshots:** Regenerate with `repomix mcp-docs/` after major changes.

## Related

- [ast-grep](https://ast-grep.github.io/) - Core search tool
- [Schema.org](https://schema.org/) - Structured data vocabulary
- [MCP](https://modelcontextprotocol.io/) - Protocol specification
- [FastMCP](https://github.com/pydantic/fastmcp) - Python framework

[![Security Assessment](https://mseep.net/pr/ast-grep-ast-grep-mcp-badge.png)](https://mseep.ai/app/ast-grep-ast-grep-mcp)
