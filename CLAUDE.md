# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run specific test suite
uv run pytest tests/test_unit.py          # Unit tests (fast, no ast-grep needed)
uv run pytest tests/test_integration.py   # Integration tests (requires ast-grep)

# Run with coverage
uv run pytest --cov=main --cov-report=term-missing

# Lint code
uv run ruff check .

# Type check
uv run mypy main.py

# Run the MCP server
uv run main.py

# Standalone tools (see "Standalone Tools" section below)
uv run python scripts/find_duplication.py /path/to/project --language python
uv run python schema-tools.py search "article"
python3 schema-graph-builder.py ~/path/to/schemas https://example.com
```

## Project Overview

This is an MCP (Model Context Protocol) server that combines ast-grep's structural code search capabilities with Schema.org structured data tools. The server provides 13 MCP tools across two domains:

### Code Search Tools (ast-grep)
1. **`dump_syntax_tree`**: Visualize AST structure of code snippets for pattern development
2. **`test_match_code_rule`**: Test YAML rules against code before applying to larger codebases
3. **`find_code`**: Search using simple patterns for straightforward structural matches
4. **`find_code_by_rule`**: Advanced search using complex YAML rules with relational constraints
5. **`find_duplication`**: Detect duplicate code and suggest modularization based on DRY principles

### Schema.org Tools
6. **`get_schema_type`**: Get detailed information about a Schema.org type
7. **`search_schemas`**: Search for Schema.org types by keyword
8. **`get_type_hierarchy`**: Get the inheritance hierarchy for a type
9. **`get_type_properties`**: Get all properties available for a type
10. **`generate_schema_example`**: Generate example JSON-LD structured data
11. **`generate_entity_id`**: Generate proper @id values following SEO best practices
12. **`validate_entity_id`**: Validate @id values against best practices
13. **`build_entity_graph`**: Build knowledge graphs with related entities using @id references

**External dependencies**:
- `ast-grep` CLI (for code search tools) - must be installed and available in PATH
- Internet connection (for Schema.org tools) - fetches vocabulary from schema.org on first use

## Prerequisites

1. **ast-grep**: Install via [ast-grep installation guide](https://ast-grep.github.io/guide/quick-start.html#installation)
   ```bash
   # macOS
   brew install ast-grep
   # or via cargo
   cargo install ast-grep --locked
   ```
   Verify installation: `ast-grep --version`

2. **uv**: Python package manager
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Python 3.13+**: Required by the project

## MCP Client Configuration

Add to Cursor (`.cursor-mcp/settings.json`) or Claude Desktop MCP configuration:
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

## Standalone Tools

### Schema.org Tools CLI (`schema-tools.py`)
Quick Schema.org lookups without running the MCP server.

```bash
uv run python schema-tools.py search "article"
uv run python schema-tools.py type Person
uv run python schema-tools.py properties Organization --json
```

Options: `--limit N`, `--no-inherited`, `--json`. See `SCHEMA-TOOLS-README.md`.

### Schema Graph Builder (`schema-graph-builder.py`)
Builds unified Schema.org entity graphs from JSON files. Validates @id values, analyzes relationships, generates documentation.

```bash
python3 schema-graph-builder.py ~/path/to/schemas https://example.com
```

Outputs: `unified-entity-graph.json`, analysis files, validation reports. See `SCHEMA-GRAPH-BUILDER-README.md`.

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev
```

### Testing

Tests are organized into two categories:
- **Unit tests** (`tests/unit/`): Fast, mocked dependencies, no ast-grep required
- **Integration tests** (`tests/integration/`): Require ast-grep binary installed

```bash
# Run all tests
uv run pytest

# Run only unit tests (fast, mocked)
uv run pytest tests/unit/

# Run only integration tests (requires ast-grep)
uv run pytest tests/integration/

# Run specific test file
uv run pytest tests/unit/test_unit.py           # 57 unit tests
uv run pytest tests/unit/test_cache.py          # 26 cache tests (Task 7: Caching + helpers)
uv run pytest tests/unit/test_duplication.py    # 24 duplication detection tests
uv run pytest tests/unit/test_phase2.py         # 21 Phase 2 feature tests (Tasks 6, 8, 9)
uv run pytest tests/unit/test_schema.py         # 52 Schema.org tests
uv run pytest tests/integration/test_integration.py   # 5 integration tests
uv run pytest tests/integration/test_benchmark.py     # Performance benchmarks (Task 10)

# Run with coverage
uv run pytest --cov=main --cov-report=term-missing
```

**Unit Tests** (185 tests): All unit tests use mocked HTTP/subprocess calls:
- `test_unit.py`: Core AST-grep functionality (dump_syntax_tree, find_code, YAML validation, etc.)
- `test_cache.py`: **Query caching functionality (26 tests)** - Task 7
  - Core caching (10 tests): put/get, TTL expiration, LRU eviction, cache keys
  - Tool integration (5 tests): find_code/find_code_by_rule caching, format handling
  - **Helper methods (11 tests):** clear(), get_stats(), cache key consistency, LRU behavior ⭐ NEW!
- `test_duplication.py`: Code duplication detection
- `test_phase2.py`: Phase 2 performance features
  - **Task 6 - Result Streaming** (7 tests): JSON parsing, early termination, subprocess cleanup
  - **Task 8 - Parallel Execution** (4 tests): Workers parameter, --threads flag
  - **Task 9 - Large File Handling** (8 tests): File filtering, size limits, language filtering
  - **Integration Tests** (2 tests): Combined features, caching integration
- `test_schema.py`: Schema.org client and tools (52 tests)
  - SchemaOrgClient class tests (38 tests): initialization, type queries, search, hierarchy, properties, example generation
  - Entity @id generation/validation tests (7 tests): proper formatting, best practices validation
  - Entity graph building tests (7 tests): relationships, cross-references

**Integration Tests** (13 tests): Require real ast-grep binary:
- `test_integration.py`: End-to-end tests with real ast-grep subprocess
- `test_benchmark.py`: Performance benchmarking suite (Task 10)

**Test Coverage: 90%** (651 statements covered out of 720, 69 uncovered)

### Performance Benchmarking
```bash
# Run performance benchmarks
python scripts/run_benchmarks.py

# Update baseline metrics (after performance improvements)
python scripts/run_benchmarks.py --save-baseline

# Check for regressions (for CI)
python scripts/run_benchmarks.py --check-regression
```

The benchmark suite tracks:
- **Execution time** for standard query patterns
- **Memory usage** during searches
- **Cache hit performance** (>10x speedup expected)
- **Early termination** efficiency with max_results
- **File size filtering** overhead

**Regression Detection:** Fails CI if performance degrades >10% compared to baseline

See `BENCHMARKING.md` for detailed documentation on:
- Expected performance ranges by codebase size
- How to add custom benchmarks
- CI integration for automated regression detection
- Interpreting benchmark reports

### Linting and Type Checking
```bash
# Run ruff linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Run mypy type checker
uv run mypy main.py
```

### Running the Server
```bash
# Run directly
uv run main.py

# Run with config file
uv run main.py --config /path/to/sgconfig.yaml

# Run with logging options
uv run main.py --log-level DEBUG --log-file /tmp/ast-grep-mcp.log

# Run with caching options
uv run main.py --cache-size 200 --cache-ttl 600

# Run via installed script name
uv run ast-grep-server

# Run directly from GitHub using uvx (no clone required)
uvx --from git+https://github.com/ast-grep/ast-grep-mcp ast-grep-server
```

### Command-Line Scripts

```bash
# Find code duplication (Python or Bash wrapper)
uv run python scripts/find_duplication.py /path/to/project --language python
./scripts/find_duplication.sh /path/to/project javascript class_definition 0.9

# Options: --construct-type, --min-similarity, --max-constructs, --exclude-patterns, --json
# Default exclusions: site-packages, node_modules, .venv, venv, vendor
```

See `scripts/README.md` for full documentation.

### Logging System

Structured JSON logging via **structlog** to stderr (or file).

**Config:** `--log-level DEBUG`, `--log-file /path/to/file`, or env vars `LOG_LEVEL`, `LOG_FILE`

**Key events:** tool_invoked, tool_completed, stream_progress, cache_hit/miss, command_completed. All logs include execution_time_seconds and result counts.

### Query Result Caching

LRU cache with TTL for `find_code` and `find_code_by_rule` queries.

**Config:** `--no-cache`, `--cache-size N` (default: 100), `--cache-ttl SECONDS` (default: 300), or env vars

Cache keys include command, args, and project path. Both text/json formats share cached results.

## Architecture

### Single-file Design
Entire server in `main.py` (~2775 lines) for simplicity. Includes logging, streaming, caching, file handling, duplication detection, and Schema.org client.

### Core Components

**Tool Registration:** 13 tools (5 ast-grep + 8 Schema.org) registered via `register_mcp_tools()` using FastMCP decorators.

**Execution Paths:**
- Non-streaming: `run_ast_grep()` → `subprocess.run()`
- Streaming: `stream_ast_grep_results()` → `subprocess.Popen()` with `--json=stream`

**Output Formats:** `text` (75% fewer tokens, default) or `json` (full metadata). Both use JSON internally for accurate limiting.

**Streaming:** Parses results line-by-line with early termination when `max_results` reached. Graceful subprocess cleanup via SIGTERM/SIGKILL. Significant performance benefit on large codebases.

**Large File Handling:** `max_file_size_mb` parameter filters files via `filter_files_by_size()`. Skips large generated/minified files, respects language extensions and ignore patterns.

**Parallel Execution:** `workers` parameter leverages ast-grep's threading (`--threads N`). Can reduce search time by 50-70% on large projects.

**Duplication Detection:** `find_duplication` tool finds duplicate code using ast-grep streaming + difflib similarity. Hash-based bucketing by line count reduces O(n²) comparisons (83% reduction). Filters library code via `exclude_patterns`, limits analysis via `max_constructs` (default 1000). Returns structured report with duplicate groups, similarity scores, and refactoring suggestions.

**Schema.org Integration:** SchemaOrgClient class fetches vocabulary on first use, indexes ~2600+ types/properties in memory. 8 tools: type queries, search, hierarchy, properties, example generation, @id generation/validation, knowledge graph building. @id format: `{canonical_url}#{entity_type}` for stable, cross-page entity references.

### Testing Architecture

`MockFastMCP` pattern extracts tools for testing. Unit tests mock subprocess calls; integration tests use real ast-grep.

**Cache isolation:** Clear `main._query_cache` in `setup_method()` to prevent test interference.

## Development Notes

**Windows:** `shell=True` required for npm-installed ast-grep

**Config precedence:** `--config` flag > `AST_GREP_CONFIG` env var > ast-grep defaults

**Streaming benefits:** Early termination on `max_results` saves CPU/I/O on large projects. SIGTERM then SIGKILL if needed.

**YAML rules:** Modern ast-grep requires `kind` field in rules. Add `stopBy: end` to relational rules if no matches found.

**Text format:** Designed to minimize tokens: `filepath:startline-endline` headers + match text.

## Real-World Example: PersonalSite Schema Enhancement

**Project:** Jekyll static site (`~/code/PersonalSite`)
**Objective:** Replace fragmented Schema.org markup with unified knowledge graph + specialized blog schemas
**Tools:** `search_schemas`, `get_type_properties`, `generate_entity_id`, `validate_entity_id`, `build_entity_graph`, ast-grep `find_code`

### Phase 1: Unified Knowledge Graph
**Problem:** 11 separate schema files with duplicate entities and inconsistent @id usage
**Solution:**
- Used `generate_entity_id` to create stable @id values (`{url}#{entity_type}`)
- Built unified graph with 5 entities (Person, WebSite, Blog, 2 Organizations) and 15 relationships
- 100% @id validation pass rate via `validate_entity_id`
**Result:** 91% file reduction (11 files → 1 unified schema)

### Phase 2: Enhanced Blog Schemas
**Problem:** All posts used generic BlogPosting schema
**Solution:**
- Used ast-grep to analyze post content patterns
- Used `search_schemas` to find specialized types: TechArticle, AnalysisNewsArticle, HowTo
- Created 3 conditional templates with Liquid, controlled by front matter
**Result:** Content-specific schemas with improved SEO (rich results, featured snippets)

### Key Learnings
1. Stable @id format enables cross-page entity references and knowledge graph building
2. Specialized schemas (TechArticle vs AnalysisNewsArticle vs HowTo) improve semantic clarity
3. `validate_entity_id` catches issues before deployment
4. Jekyll/Liquid supports clean conditional schema inclusion

**Metrics:** 17 files changed, 4,388 insertions, 100% validation, 8 documentation files created

See `~/code/PersonalSite/` for implementation details and comprehensive documentation.
