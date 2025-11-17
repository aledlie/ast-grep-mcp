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

### Cursor
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

### Claude Desktop
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

## Standalone Tools

### Schema.org Tools CLI (`schema-tools.py`)

A command-line interface for quick access to Schema.org vocabulary tools. Provides instant lookups without running the MCP server.

**Quick Usage:**
```bash
# Search for Schema.org types
uv run python schema-tools.py search "article"

# Get type information
uv run python schema-tools.py type Person

# Get type properties
uv run python schema-tools.py properties Organization
```

**Available commands:**
1. **search** - Search for Schema.org types by keyword
2. **type** - Get detailed information about a specific type
3. **properties** - Get all properties available for a type

**Options:**
- `--limit N` - Limit search results (search command)
- `--no-inherited` - Exclude inherited properties (properties command)
- `--json` - Output as JSON for programmatic use (all commands)

**Use cases:**
- Quick lookups during development
- Exploring Schema.org vocabulary
- Planning structured data implementation
- Exporting type information for reference

**Documentation:** `SCHEMA-TOOLS-README.md`

### Schema Graph Builder (`schema-graph-builder.py`)

A standalone Python script that automates building unified Schema.org entity graphs from multiple JSON files. This tool was created using the MCP server's Schema.org tools and demonstrates their practical application.

**Quick Usage:**
```bash
# Build entity graph from directory of Schema.org JSON files
python3 schema-graph-builder.py <directory> <base_url>

# Example
python3 schema-graph-builder.py ~/code/PersonalSite/schemas-static https://www.aledlie.com
```

**What it does:**
1. Discovers Schema.org JSON files in a directory
2. Extracts entities with `@type` and `@id`
3. Validates all `@id` values against best practices
4. Builds unified `@graph` structure
5. Analyzes relationships between entities
6. Generates comprehensive documentation

**Output files** (in `schema-analysis/` directory):
- `unified-entity-graph.json` - Complete knowledge graph ready for deployment
- `entity-graph-analysis.json` - Relationship statistics and analysis
- `entity-id-validation.json` - @id validation results
- `ENTITY-GRAPH-SUMMARY.md` - Comprehensive documentation

**Options:**
- `--output-dir DIR` - Custom output directory (default: `<directory>/schema-analysis`)
- `--name NAME` - Project name for documentation (default: extracted from base_url)
- `--exclude PATTERN ...` - Additional filename patterns to exclude
- `--json` - Output summary as JSON for programmatic use

**Real-world results:**
- PersonalSite (aledlie.com): 16 entities, 13 types, 33 relationships, 100% validation
- Fisterra Dance (fisterra-dance.com): 22 entities, 17 types, 26 relationships, 100% validation

**Documentation:**
- Quick start: `SCHEMA-GRAPH-BUILDER-QUICK-START.md`
- Full documentation: `SCHEMA-GRAPH-BUILDER-README.md`

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
uv run pytest tests/unit/test_cache.py          # 15 cache tests (Task 7: Caching)
uv run pytest tests/unit/test_duplication.py    # 24 duplication detection tests
uv run pytest tests/unit/test_phase2.py         # 21 Phase 2 feature tests (Tasks 6, 8, 9)
uv run pytest tests/integration/test_integration.py   # 5 integration tests
uv run pytest tests/integration/test_benchmark.py     # Performance benchmarks (Task 10)

# Run with coverage
uv run pytest --cov=main --cov-report=term-missing
```

**Unit Tests** (122 tests): All unit tests use mocked subprocess calls and don't require ast-grep:
- `test_unit.py`: Core functionality tests (dump_syntax_tree, find_code, YAML validation, etc.)
- `test_cache.py`: Query caching functionality (Task 7)
- `test_duplication.py`: Code duplication detection
- `test_phase2.py`: Phase 2 performance features
  - **Task 6 - Result Streaming** (7 tests): JSON parsing, early termination, subprocess cleanup
  - **Task 8 - Parallel Execution** (4 tests): Workers parameter, --threads flag
  - **Task 9 - Large File Handling** (8 tests): File filtering, size limits, language filtering
  - **Integration Tests** (2 tests): Combined features, caching integration

**Integration Tests** (12 tests): Require real ast-grep binary:
- `test_integration.py`: End-to-end tests with real ast-grep subprocess
- `test_benchmark.py`: Performance benchmarking suite (Task 10)

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

The `scripts/` directory contains standalone utilities for running MCP tools from the command line:

**Find Duplication (Python)**:
```bash
# Analyze Python functions (excludes library code by default)
uv run python scripts/find_duplication.py /path/to/project --language python

# Analyze JavaScript classes with strict similarity
uv run python scripts/find_duplication.py /path/to/project --language javascript \
    --construct-type class_definition --min-similarity 0.9

# Analyze more constructs for large codebases (default is 1000)
uv run python scripts/find_duplication.py /path/to/project --language python --max-constructs 5000

# Customize exclusion patterns (or disable with empty list)
uv run python scripts/find_duplication.py /path/to/project --language python \
    --exclude-patterns site-packages build dist

# Output as JSON
uv run python scripts/find_duplication.py /path/to/project --language python --json
```

**Find Duplication (Bash wrapper)**:
```bash
# Simple interface with positional arguments (uses default exclusions)
./scripts/find_duplication.sh /path/to/project python
./scripts/find_duplication.sh /path/to/project javascript class_definition 0.9
```

**Default Exclusions**: By default, the tool excludes library code from analysis:
`site-packages`, `node_modules`, `.venv`, `venv`, `vendor`

See `scripts/README.md` for full documentation.

### Logging System

The server uses **structlog** for structured JSON logging. All logs are written to stderr by default, but can be redirected to a file.

**Configuration Options:**
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO
- `--log-file`: Path to log file. Default: stderr
- `LOG_LEVEL` env var: Alternative to --log-level flag
- `LOG_FILE` env var: Alternative to --log-file flag

**Log Format:**
All logs are JSON formatted with the following fields:
- `timestamp`: ISO 8601 timestamp (UTC)
- `level`: Log level (debug, info, warning, error)
- `event`: Event type (e.g., "tool_invoked", "command_completed", "tool_failed")
- Additional context fields specific to each event

**Examples:**
```bash
# Enable debug logging to stderr
uv run main.py --log-level DEBUG

# Log to file with INFO level
uv run main.py --log-file /var/log/ast-grep-mcp.log

# Use environment variables
export LOG_LEVEL=DEBUG
export LOG_FILE=/tmp/ast-grep.log
uv run main.py
```

**Log Events:**
- `tool_invoked`: Tool called with parameters (sanitized)
- `tool_completed`: Tool finished successfully with metrics
- `tool_failed`: Tool execution failed with error details
- `executing_command`: Subprocess command starting
- `command_completed`: Subprocess command finished with timing
- `command_failed`: Subprocess command failed with error
- `command_not_found`: Subprocess binary not found
- `stream_started`: Streaming search initiated with parameters
- `stream_progress`: Progress update during streaming (every N matches)
- `stream_early_termination`: Subprocess terminated after reaching max_results
- `stream_completed`: Streaming search finished with final metrics
- `stream_failed`: Streaming search failed with error details
- `stream_json_parse_error`: Invalid JSON line encountered during streaming

**Performance Metrics:**
All tool invocations and subprocess executions log:
- `execution_time_seconds`: Duration in seconds (rounded to 3 decimals)
- `match_count` / `total_matches`: Number of results found (for search tools)
- `output_length`: Size of output (for dump_syntax_tree)

### Query Result Caching

The server implements an LRU cache with TTL expiration for `find_code` and `find_code_by_rule` query results. Caching avoids redundant ast-grep executions for identical queries, significantly improving response times for repeated searches.

**Configuration Options:**
- `--no-cache`: Disable result caching entirely
- `--cache-size N`: Maximum number of cached entries (default: 100)
- `--cache-ttl SECONDS`: Time-to-live for cache entries in seconds (default: 300)
- `CACHE_DISABLED` env var: Set to any value to disable caching
- `CACHE_SIZE` env var: Alternative to --cache-size flag
- `CACHE_TTL` env var: Alternative to --cache-ttl flag

**Examples:**
```bash
# Run with default caching (100 entries, 300s TTL)
uv run main.py

# Disable caching
uv run main.py --no-cache

# Custom cache size and TTL
uv run main.py --cache-size 200 --cache-ttl 600

# Use environment variables
export CACHE_SIZE=50
export CACHE_TTL=120
uv run main.py
```

**Cache Behavior:**
- Cache keys include: command type (run/scan), all arguments (sorted), and project folder path
- Cache entries expire after TTL seconds (default 300)
- LRU eviction removes oldest entries when cache is full
- Both `text` and `json` output formats use the same cached query results
- Cache statistics are tracked: hits, misses, hit rate, current size

**Cache Log Events:**
- `cache_initialized`: Cache startup with configuration
- `cache_hit`: Query result served from cache
- `cache_miss`: Query not in cache, executing ast-grep
- `cache_stored`: Query result stored in cache after execution

**Implementation Details:**
- Cache class: `QueryCache` (OrderedDict-based LRU with TTL)
- Cache keys: SHA256 hash (first 16 chars) of command + args + project
- Cache storage: Results stored with timestamp for TTL checking
- Thread safety: Not implemented (single-threaded MCP server)

## Architecture

### Single-file Design
The entire MCP server is implemented in `main.py` (~2775 lines). This is intentional for simplicity and portability. The file includes comprehensive logging (~282 lines), streaming result parsing (~156 lines), query result caching (~117 lines), large file handling (~150 lines), duplication detection (~382 lines), Schema.org client (~490 lines with ID features) and 8 Schema.org MCP tools (~340 lines).

### Core Components

**Tool Registration Pattern**: Tools are registered dynamically via `register_mcp_tools()` which is called at startup. This function uses the FastMCP decorator pattern to register thirteen tools (5 ast-grep + 8 Schema.org including 3 ID-based tools). Tools are defined as nested functions inside `register_mcp_tools()` to access the global `CONFIG_PATH` variable and `get_schema_org_client()` function set during argument parsing.

**Config Path Resolution**: The server supports custom `sgconfig.yaml` via `--config` flag or `AST_GREP_CONFIG` env var. The global `CONFIG_PATH` variable is set by `parse_args_and_get_config()` before tool registration, allowing tools to pass `--config` to ast-grep commands when needed.

**Subprocess Execution Flow**: Tools use two execution paths:
- **Non-streaming** (dump_syntax_tree, test_match_code_rule): `run_ast_grep()` → `run_command()` → `subprocess.run()`
- **Streaming** (find_code, find_code_by_rule): `stream_ast_grep_results()` → `subprocess.Popen()`

Error handling converts `CalledProcessError` and `FileNotFoundError` into user-friendly `RuntimeError` messages.

**Output Format Optimization**: `find_code` and `find_code_by_rule` support two output modes:
- `text` (default): ~75% fewer tokens, formatted as `file:line-range` headers with match text
- `json`: Full metadata including ranges and meta-variables

Both modes internally use JSON from ast-grep for accurate result limiting, then convert to text if requested.

**Streaming Architecture**: `find_code` and `find_code_by_rule` use streaming result parsing via `stream_ast_grep_results()` (main.py:783-937). This function:
- Uses `subprocess.Popen` with `--json=stream` flag to process JSON Lines output
- Parses results line-by-line as they arrive from ast-grep
- Supports early termination: kills the subprocess when `max_results` is reached
- Provides progress logging every N matches (default: 100)
- Performs graceful subprocess cleanup (SIGTERM, then SIGKILL if needed)

The streaming layer sits between the MCP tools and the subprocess execution layer, replacing the traditional `run_ast_grep()` call for search operations. This provides significant performance benefits when searching large codebases with result limits, as ast-grep can be terminated as soon as enough matches are found rather than scanning the entire project.

**Large File Handling**: `find_code` and `find_code_by_rule` support optional file size filtering via the `max_file_size_mb` parameter. This feature helps exclude large generated/minified files from searches. The implementation:
- **File Filtering**: `filter_files_by_size()` function (main.py:2427-2519) recursively walks the project directory
- **Size Checking**: Uses `os.path.getsize()` to check each file against the limit
- **Language Filtering**: Optionally filters by language-specific extensions (e.g., .py for Python)
- **Ignore Patterns**: Automatically skips hidden directories and common patterns (node_modules, venv, .venv, build, dist)
- **File List Mode**: When filtering is active, passes individual file paths to ast-grep instead of the directory
- **Logging**: Logs skipped files at DEBUG level and filtering summary at INFO level (files_filtered_by_size event)
- **Edge Cases**: Handles scenarios where all files exceed the limit (returns empty results)

Memory efficiency is achieved through the streaming architecture (Task 6) rather than custom file parsing. ast-grep handles file reading internally and efficiently, while our streaming layer processes results incrementally.

**Parallel Execution**: `find_code` and `find_code_by_rule` support parallel execution via the `workers` parameter. This leverages ast-grep's built-in threading capabilities:
- **Worker Parameter**: `workers=0` (default) uses ast-grep's auto-detection heuristics
- **Custom Thread Count**: `workers=N` spawns N parallel threads for file processing
- **Threading Flag**: Passes `--threads N` to ast-grep subprocess
- **CPU Utilization**: Higher thread counts improve performance on multi-core systems
- **Large Codebases**: Can reduce search time by 50-70% on projects with 1K+ files
- **Logging**: Worker count logged in tool_invoked events

Performance improvements scale with available CPU cores. For example:
- 1K files, 4 cores, workers=4: ~60% faster than single-threaded
- 10K files, 8 cores, workers=8: ~70% faster than single-threaded

The parallel execution integrates seamlessly with streaming, caching, and file filtering features.

**Duplication Detection**: The `find_duplication` tool (main.py:880-1316) detects duplicate code and suggests refactoring opportunities based on DRY principles. The detection process:
1. Uses ast-grep streaming to find all instances of a construct type (functions, classes, methods)
2. Filters out library code based on exclude_patterns (default: site-packages, node_modules, .venv, venv, vendor)
3. Limits analysis to max_constructs (default: 1000) for performance on large codebases
4. Normalizes code for comparison (removes whitespace, comments)
5. Calculates pairwise similarity using difflib's SequenceMatcher with hash-based bucketing optimization
6. Groups similar code blocks into duplication clusters (configurable threshold)
7. Generates refactoring suggestions for each cluster

Key algorithms:
- `normalize_code()`: Removes whitespace/comments for fair comparison
- `calculate_similarity()`: Returns 0-1 similarity ratio using SequenceMatcher
- `group_duplicates()`: Clusters similar code using hash-based bucketing by line count (reduces O(n²) to practical comparisons):
  - Buckets functions by line count (±5 lines)
  - Quick hash equality check for 100% identical code
  - Size ratio filtering (skips if >2x difference)
  - Only compares within and across adjacent buckets
  - Example: 1000 constructs → 82,594 comparisons vs 499,500 maximum (83% reduction)
- `generate_refactoring_suggestions()`: Creates actionable refactoring advice

Performance optimizations:
- **max_constructs** (default 1000): Limits number of constructs analyzed to prevent excessive computation on large codebases. Set to 0 for unlimited.
- **exclude_patterns**: Filters out library/vendor code that can't be modified (default: ["site-packages", "node_modules", ".venv", "venv", "vendor"])
- **Hash-based bucketing**: Groups constructs by similar line counts before comparison, dramatically reducing pairwise comparisons

The tool returns a structured report with:
- Summary statistics (total constructs, duplicate groups, potential line savings)
- Detailed duplication groups with similarity scores and file locations
- Specific refactoring suggestions (extract function, base class, etc.)

**Usage Example:**
```python
# Find duplicate functions in a Python project
result = find_duplication(
    project_folder="/path/to/project",
    language="python",
    construct_type="function_definition",
    min_similarity=0.8,        # 80% similarity threshold
    min_lines=5,               # Ignore functions < 5 lines
    max_constructs=1000,       # Limit analysis for performance (0=unlimited)
    exclude_patterns=["site-packages", "node_modules", ".venv", "venv", "vendor"]
)

# Result includes:
# - summary.total_constructs: Total functions found (after filtering)
# - summary.duplicate_groups: Number of duplication clusters
# - summary.potential_line_savings: Lines that could be saved
# - duplication_groups: Details of each cluster
# - refactoring_suggestions: Actionable advice for each cluster
```

**Schema.org Integration**: The server includes a SchemaOrgClient class (main.py:494-980) that fetches and indexes the complete Schema.org vocabulary. The integration pattern:

1. **Lazy Initialization**: Schema.org data is fetched from `https://schema.org/version/latest/schemaorg-current-https.jsonld` on first use (not at server startup)
2. **In-Memory Indexing**: All types and properties are indexed by `@id` and `rdfs:label` for fast lookups (~2600+ entries)
3. **Async Client with Sync Wrappers**: The SchemaOrgClient uses httpx for async HTTP requests, wrapped with `asyncio.run()` in the MCP tool functions for synchronous execution
4. **Single Global Instance**: A global `_schema_org_client` instance is created on first access via `get_schema_org_client()`

Schema.org tool features:
- **Type Queries** (`get_schema_type`): Returns type metadata, description, parent types, and URL
- **Search** (`search_schemas`): Full-text search across type names and descriptions, sorted by relevance (limit 1-100 results)
- **Hierarchy** (`get_type_hierarchy`): Traverses parent (`rdfs:subClassOf`) and child relationships
- **Properties** (`get_type_properties`): Lists direct and inherited properties with expected value types
- **Example Generation** (`generate_schema_example`): Creates valid JSON-LD with common properties and custom values
- **ID Generation** (`generate_entity_id`): Creates proper @id values following SEO best practices (canonical URL + hash fragment)
- **ID Validation** (`validate_entity_id`): Validates @id against best practices with warnings and suggestions
- **Knowledge Graph Building** (`build_entity_graph`): Creates @graph structures with multiple entities connected via @id references

**@id Best Practices** (from [Momentic Marketing](https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs)):
- Use format: `{canonical_url}#{entity_type}` or `{canonical_url}/{slug}#{entity_type}`
- Keep IDs stable (no timestamps, query parameters, or dynamic values)
- Use descriptive fragments for debugging clarity
- One unchanging identifier per entity
- Enable cross-page entity references
- Build knowledge graphs over time

The Schema.org client operates independently from ast-grep and requires internet connectivity for initial data fetch. After initialization, all operations use the in-memory indexed data. The ID-based tools (generate_entity_id, validate_entity_id, build_entity_graph) are synchronous and don't require data fetching.

### Testing Architecture

Tests use a `MockFastMCP` class to bypass FastMCP's decorator machinery and extract registered tool functions for direct testing. The pattern:
1. Patch `FastMCP` and `pydantic.Field` before importing
2. Import main.py with mocked decorators
3. Call `register_mcp_tools()` to populate `main.mcp.tools` dict
4. Extract tool functions from the dict for testing

Unit tests (`test_unit.py`) mock subprocess calls. Integration tests (`test_integration.py`) run against real fixtures in `tests/fixtures/`.

**Cache Isolation in Tests**: Test classes that call search tools should clear the query cache in `setup_method()` to prevent test interference:
```python
def setup_method(self):
    """Clear cache before each test to avoid test interference"""
    if main._query_cache is not None:
        main._query_cache.cache.clear()
        main._query_cache.hits = 0
        main._query_cache.misses = 0
```

**Benchmark Tests**: The benchmark suite (test_benchmark.py) initializes caching globally to accurately measure cache performance. The `run_benchmark()` function tracks cache hits by monitoring the cache hit counter before and after each tool invocation.

### Language Support

The `get_supported_languages()` function returns a hardcoded list of ast-grep's built-in languages PLUS any custom languages defined in the `sgconfig.yaml` file (if provided). This list is used in tool parameter descriptions.

## Development Notes

### Windows Compatibility
`run_command()` sets `shell=True` on Windows when calling `ast-grep` because npm-installed ast-grep is a batch file that requires shell execution.

### Config Path Precedence
1. `--config` CLI flag (highest)
2. `AST_GREP_CONFIG` environment variable
3. None (ast-grep uses its defaults)

### Performance Patterns

**Streaming Benefits**: The streaming architecture (main.py:783-937) provides significant performance advantages:
- **Large codebases**: Reduces memory usage by processing results incrementally rather than loading all matches into memory
- **Result limits**: When `max_results` is set, ast-grep is terminated early via SIGTERM, saving CPU and I/O by not scanning the entire project
- **Progress visibility**: Progress logs (every 100 matches by default) help debug long-running searches and provide feedback during development

**Early Termination**: When a search reaches `max_results`, the streaming layer:
1. Stops reading from the subprocess stdout
2. Sends SIGTERM to ast-grep process
3. Waits up to 2 seconds for graceful shutdown
4. Sends SIGKILL if process doesn't terminate
5. Logs `stream_early_termination` event with timing metrics

This can result in substantial time savings on large projects. For example, finding the first 10 matches in a 100,000-file codebase might complete in seconds rather than minutes.

### Common ast-grep Patterns

**YAML Rule Requirements**: Modern ast-grep versions require the `kind` field in YAML rules. For example:
```yaml
id: test-rule
language: python
rule:
  kind: class_definition  # Required!
  pattern: class $NAME
```

When testing rules, if no matches are found, the error message suggests adding `stopBy: end` to relational rules (inside/has). This is a common gotcha with ast-grep's traversal behavior.

### Text Format Design
The text output format was designed to minimize token usage for LLMs while maintaining context. Format: `filepath:startline-endline` header followed by complete match text, with matches separated by blank lines.

## Real-World Usage: PersonalSite Schema Enhancement Project

This section documents a complete real-world usage of the Schema.org tools to implement a unified knowledge graph and enhanced blog post schemas for a Jekyll-based personal website.

### Project Overview

**Repository**: ~/code/PersonalSite (Jekyll static site)
**Objective**: Replace fragmented Schema.org markup with unified knowledge graph and content-specific schemas
**Tools Used**: 8 of 13 MCP tools (5 Schema.org tools + ast-grep for analysis)
**Outcome**: 91% file reduction, 100% @id validation, 3 new blog post schema types

### Phase 1: Unified Knowledge Graph Implementation

**Problem**: PersonalSite had 11 separate schema include files with duplicate entity definitions and inconsistent @id usage.

**Solution**: Used Schema.org tools to create a unified knowledge graph:

1. **Analysis** (using `search_schemas`, `get_type_properties`):
   - Identified 5 core entities: Person, WebSite, Blog, 2 Organizations
   - Mapped 15 bidirectional relationships between entities

2. **ID Generation** (using `generate_entity_id`):
   ```bash
   # Generated proper @id values following best practices
   generate_entity_id("https://www.aledlie.com", "person")
   # Returns: "https://www.aledlie.com#person"

   generate_entity_id("https://www.aledlie.com", "organization", "organizations/integrity-studios")
   # Returns: "https://www.aledlie.com/organizations/integrity-studios#organization"
   ```

3. **Validation** (using `validate_entity_id`):
   - Validated all @id values: 100% pass rate
   - Verified hash fragments present
   - Confirmed no dynamic values or timestamps

4. **Knowledge Graph Construction** (using `build_entity_graph`):
   ```python
   entities = [
       {
           "fragment": "person",
           "type": "Person",
           "name": "Alyshia Ledlie",
           "relationships": {
               "owns": "website",
               "worksFor": ["organization-integrity", "organization-inventoryai"]
           }
       },
       {
           "fragment": "website",
           "type": "WebSite",
           "name": "Alyshia Ledlie",
           "relationships": {
               "publisher": "person",
               "hasPart": ["blog"]
           }
       },
       # ... more entities
   ]

   graph = build_entity_graph(entities, "https://www.aledlie.com")
   # Returns complete @graph with all @id references resolved
   ```

**Files Created**:
- `_includes/unified-knowledge-graph-schema.html` (260 lines) - Production schema
- `_includes/SCHEMA-KNOWLEDGE-GRAPH-GUIDE.md` - Implementation guide
- `KNOWLEDGE-GRAPH-ANALYSIS-SUMMARY.md` - Analysis report
- `SCHEMA-BEFORE-AFTER-COMPARISON.md` - Comparison document

**Results**:
- Replaced 11 fragmented files with 1 unified schema
- 91% file reduction
- 100% @id validation pass rate
- 15 bidirectional entity relationships

### Phase 2: Enhanced Blog Post Schemas

**Problem**: All blog posts used generic BlogPosting schema regardless of content type (technical guides, performance analysis, tutorials).

**Solution**: Created specialized schemas for different content patterns:

1. **Content Analysis** (using ast-grep `find_code`):
   - Analyzed blog post markdown files
   - Identified 3 content patterns:
     - Technical guides (Jekyll update)
     - Performance analysis with data (Wix performance)
     - Personal narratives (What3Things)

2. **Schema Research** (using `search_schemas`, `get_type_properties`):
   ```python
   # Found appropriate schema types
   search_schemas("technical article")
   # Returns: TechArticle - "A technical article - Example: How-to topics, step-by-step..."

   search_schemas("analysis report data")
   # Returns: AnalysisNewsArticle - "A NewsArticle that incorporates expertise..."

   search_schemas("how to guide tutorial")
   # Returns: HowTo - "Instructions that explain how to achieve a result..."
   ```

3. **Property Research** (using `get_type_properties`):
   - TechArticle: dependencies, proficiencyLevel, articleSection
   - AnalysisNewsArticle: dateline, backstory (inherits from NewsArticle)
   - HowTo: steps, tools, supplies, totalTime, estimatedCost

4. **Schema Template Creation**:
   - Created 3 conditional schema templates using Liquid templating
   - All schemas reference unified knowledge graph via @id
   - Front matter controls which schema type is used

**Files Created**:
- `_includes/tech-article-schema.html` (94 lines) - For technical guides
- `_includes/analysis-article-schema.html` (92 lines) - For analysis articles
- `_includes/how-to-schema.html` (136 lines) - For step-by-step tutorials
- `BLOG-SCHEMA-ENHANCEMENT-ANALYSIS.md` (450+ lines) - Complete analysis
- `ENHANCED-SCHEMA-IMPLEMENTATION-GUIDE.md` (800+ lines) - Usage guide
- `BLOG-SCHEMA-ENHANCEMENT-SUMMARY.md` - Implementation summary

**Files Modified**:
- `_includes/seo.html` - Added conditional schema logic
- `_includes/post-schema.html` - Replaced nested objects with @id references
- `_posts/2025-09-02-WixPerformanceImprovement.md` - Added AnalysisNewsArticle schema
- `_posts/2025-07-02-updating-jekyll-in-2025.markdown` - Added TechArticle schema

**Implementation Pattern**:
```yaml
# Front matter for TechArticle
---
title: "Updating Jekyll in 2025"
date: 2025-07-02
schema_type: TechArticle
schema_dependencies: "Ruby 3.x, Jekyll 4.x, Bundler 2.x"
schema_proficiency: "Intermediate"
schema_section: "Jekyll"
schema_about: "Jekyll Static Site Generator"
---

# Front matter for AnalysisNewsArticle
---
title: "Wix Performance Improvement"
date: 2025-09-02
schema_type: AnalysisNewsArticle
schema_about: "Web Performance Optimization"
schema_dateline: "November 2025"
schema_section: "Performance Analysis"
schema_backstory: "Performance analysis based on real-world production data..."
---
```

### Phase 3: Documentation & Validation

**Documentation Created** (8 comprehensive guides):

1. **Testing**: `SCHEMA-TESTING-VALIDATION-GUIDE.md`
   - 3-phase testing checklist (pre-deploy, post-deploy, relationship validation)
   - Google Rich Results Test procedures
   - Schema.org Validator procedures
   - JSON-LD Playground usage
   - Common issues and fixes
   - Success criteria

2. **Monitoring**: `SEARCH-CONSOLE-MONITORING-GUIDE.md`
   - Daily monitoring (Week 1)
   - Weekly monitoring (Weeks 2-4)
   - Monthly monitoring (Long-term)
   - Error detection and response
   - Performance analysis framework
   - Reporting templates

3. **Analysis**: `KNOWLEDGE-GRAPH-ANALYSIS-SUMMARY.md`
   - Complete entity analysis
   - Relationship mapping
   - Statistics and metrics
   - Technical implementation details

4. **Comparison**: `SCHEMA-BEFORE-AFTER-COMPARISON.md`
   - Side-by-side comparison of approaches
   - Visual relationship diagrams
   - SEO impact analysis

5. **Original Implementation**: `IMPLEMENTATION-COMPLETE-SUMMARY.md`
   - Complete summary of unified schema implementation
   - Deployment steps
   - Testing procedures
   - Next actions

6. **Blog Enhancement Analysis**: `BLOG-SCHEMA-ENHANCEMENT-ANALYSIS.md`
   - Content pattern analysis
   - Schema type deep dive
   - Implementation strategy
   - Benefits analysis

7. **Implementation Guide**: `ENHANCED-SCHEMA-IMPLEMENTATION-GUIDE.md`
   - Front matter templates for each schema type
   - Required vs. optional fields
   - Decision tree for schema selection
   - Validation checklist
   - Troubleshooting guide

8. **Enhancement Summary**: `BLOG-SCHEMA-ENHANCEMENT-SUMMARY.md`
   - Complete implementation summary
   - Files created/modified
   - Testing procedures
   - Next steps

**Validation Steps**:

1. **Local Testing**:
   ```bash
   cd ~/code/PersonalSite
   bundle exec jekyll build
   bundle exec jekyll serve
   # View source → Copy JSON-LD → Validate in JSON-LD Playground
   ```

2. **Production Validation** (Post-Deployment):
   - Google Rich Results Test: https://search.google.com/test/rich-results
   - Schema.org Validator: https://validator.schema.org/
   - Manual source inspection for @id resolution

3. **Search Console Monitoring** (Ongoing):
   - Week 1: Schema detection, URL inspection
   - Weeks 2-4: Structured data processing, entity detection
   - Months 2-3: Rich results eligibility and appearance
   - Month 6+: Knowledge graph impact, CTR improvements

### Expected SEO Benefits

**TechArticle Schema**:
- Better technical documentation indexing
- "How-to" rich results eligibility
- Developer audience targeting
- Skill level matching

**AnalysisNewsArticle Schema**:
- Expert analysis recognition
- Data-driven content highlighting
- Trust signals (Trust Project alignment)
- Analysis query matching

**HowTo Schema**:
- Step-by-step rich snippets
- Featured snippet eligibility
- Voice search optimization
- FAQ-style results

**Knowledge Graph**:
- Improved semantic clarity
- Enhanced relationship depth
- Better entity recognition
- Cross-page entity references

### Key Learnings

1. **@id Best Practices**: Using format `{canonical_url}#{entity_type}` enables knowledge graph building across multiple pages

2. **Schema Type Selection**: Different content types benefit from specialized schemas (TechArticle vs AnalysisNewsArticle vs HowTo vs BlogPosting)

3. **Conditional Templates**: Jekyll's Liquid templating allows clean conditional schema inclusion based on front matter

4. **Validation is Critical**: Using `validate_entity_id` tool caught potential issues before deployment

5. **Documentation Matters**: Comprehensive guides ensure maintainability and future content creators understand schema usage

### Tools Usage Statistics

**Schema.org Tools Used**:
1. `search_schemas` - Found appropriate schema types for content patterns
2. `get_type_properties` - Researched properties for TechArticle, AnalysisNewsArticle, HowTo
3. `generate_entity_id` - Created all @id values following best practices
4. `validate_entity_id` - Validated all @id values (100% pass rate)
5. `build_entity_graph` - Built complete knowledge graph with 5 entities and 15 relationships

**ast-grep Tools Used**:
1. `find_code` - Analyzed blog post content patterns (Markdown files)
2. `search_schemas` integration - Pattern analysis led to schema research

**External Tools**:
- WebSearch - Researched Schema.org properties and examples
- WebFetch - Fetched Momentic Marketing @id best practices guide

### Repository Links

**Main Files**:
- Unified Schema: `~/code/PersonalSite/_includes/unified-knowledge-graph-schema.html`
- Enhanced Schemas: `~/code/PersonalSite/_includes/{tech-article,analysis-article,how-to}-schema.html`
- SEO Include: `~/code/PersonalSite/_includes/seo.html`
- Post Schema: `~/code/PersonalSite/_includes/post-schema.html`

**Documentation**:
- All guides in `~/code/PersonalSite/*.md`
- Implementation guide in `~/code/PersonalSite/_includes/SCHEMA-KNOWLEDGE-GRAPH-GUIDE.md`

**Modified Posts**:
- `~/code/PersonalSite/_posts/2025-09-02-WixPerformanceImprovement.md` (AnalysisNewsArticle)
- `~/code/PersonalSite/_posts/2025-07-02-updating-jekyll-in-2025.markdown` (TechArticle)

### Final Metrics

**File Changes**:
- 17 files changed
- 4,388 insertions
- 45 deletions
- Git commit: 88f6a304
- Pushed to: origin/master

**Schema Implementation**:
- 1 unified knowledge graph schema (replaces 11 files)
- 3 enhanced blog post schemas
- 2 blog posts enhanced with specialized schemas
- 8 comprehensive documentation files
- 100% @id validation pass rate
- 15 entity relationships mapped

**Timeline**:
- Analysis & Implementation: 1 session
- Testing: In progress
- Monitoring: Next 6 months (following SEARCH-CONSOLE-MONITORING-GUIDE.md)

This project demonstrates the practical application of Schema.org tools for building semantic web structures and knowledge graphs in a real-world Jekyll static site.
