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

This is an MCP (Model Context Protocol) server that combines ast-grep's structural code search and rewrite capabilities with Schema.org structured data tools. The server provides 16 MCP tools across three domains:

### Code Search Tools (ast-grep)
1. **`dump_syntax_tree`**: Visualize AST structure of code snippets for pattern development
2. **`test_match_code_rule`**: Test YAML rules against code before applying to larger codebases
3. **`find_code`**: Search using simple patterns for straightforward structural matches
4. **`find_code_by_rule`**: Advanced search using complex YAML rules with relational constraints
5. **`find_duplication`**: Detect duplicate code and suggest modularization based on DRY principles

### Code Rewrite Tools (ast-grep fix mode)
6. **`rewrite_code`**: Apply code transformations using ast-grep fix rules with dry-run preview and automatic backups
7. **`rollback_rewrite`**: Restore files from a previous backup after a rewrite
8. **`list_backups`**: List all available backups for a project

### Schema.org Tools
9. **`get_schema_type`**: Get detailed information about a Schema.org type
10. **`search_schemas`**: Search for Schema.org types by keyword
11. **`get_type_hierarchy`**: Get the inheritance hierarchy for a type
12. **`get_type_properties`**: Get all properties available for a type
13. **`generate_schema_example`**: Generate example JSON-LD structured data
14. **`generate_entity_id`**: Generate proper @id values following SEO best practices
15. **`validate_entity_id`**: Validate @id values against best practices
16. **`build_entity_graph`**: Build knowledge graphs with related entities using @id references

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
uv run pytest tests/unit/test_rewrite.py        # 33 code rewrite tests (Task 11 + validation)
uv run pytest tests/integration/test_integration.py   # 5 integration tests
uv run pytest tests/integration/test_benchmark.py     # Performance benchmarks (Task 10)

# Run with coverage
uv run pytest --cov=main --cov-report=term-missing
```

**Unit Tests** (218 tests): All unit tests use mocked HTTP/subprocess calls:
- `test_unit.py`: Core AST-grep functionality (dump_syntax_tree, find_code, YAML validation, etc.)
- `test_cache.py`: **Query caching functionality (26 tests)** - Task 7
  - Core caching (10 tests): put/get, TTL expiration, LRU eviction, cache keys
  - Tool integration (5 tests): find_code/find_code_by_rule caching, format handling
  - **Helper methods (11 tests):** clear(), get_stats(), cache key consistency, LRU behavior
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
- `test_rewrite.py`: **Code rewrite functionality (33 tests)** - Task 11 + validation ⭐
  - rewrite_code tool tests (8 tests): dry-run mode, actual mode with backups, YAML validation, file size limits, parallel execution
  - Backup management tests (8 tests): backup creation, file copying, metadata, restoration, backup listing
  - rollback_rewrite tool tests (3 tests): tool registration, successful rollback, error handling
  - list_backups tool tests (3 tests): empty list, multiple backups, sorting
  - Integration tests (2 tests): full workflow, data loss prevention
  - **Syntax validation tests (7 tests):** valid/invalid Python, mismatched braces, unsupported languages, validation aggregation
  - **Validation integration tests (2 tests):** rewrite with validation, validation warnings

**Integration Tests** (13 tests): Require real ast-grep binary:
- `test_integration.py`: End-to-end tests with real ast-grep subprocess
- `test_benchmark.py`: Performance benchmarking suite (Task 10)

**Total Tests: 230** (218 unit + 12 integration, excluding 1 skipped)

**Test Coverage: 90%** (736 statements covered out of 818, 82 uncovered)

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

### Code Rewrite Functionality

The rewrite tools enable safe, automated code transformations using ast-grep's fix rules. All rewrites include safety guardrails to prevent data loss.

**Safety Features:**
- **Dry-run by default**: `dry_run=true` previews changes without modifying files
- **Automatic backups**: Creates timestamped backups before applying changes (unless `backup=false`)
- **Syntax validation**: Automatically validates rewritten code for syntax errors after changes
- **Rollback capability**: Restore previous state from any backup
- **Backup metadata**: JSON metadata tracks all modified files with timestamps
- **Validation warnings**: Alerts when rewritten code fails syntax validation

**Workflow:**
1. **Preview** - Run with `dry_run=true` (default) to see what will change
2. **Apply** - Set `dry_run=false` to apply changes (creates backup automatically)
3. **Validate** - Automatic syntax validation runs on rewritten files
4. **Verify** - Check the modified code and validation results
5. **Rollback** (if needed) - Use `rollback_rewrite` with backup_id to restore

**Backup Storage:**
- Location: `.ast-grep-backups/` directory in project root
- Format: `backup-YYYYMMDD-HHMMSS-mmm/` (timestamped directories)
- Metadata: `backup-metadata.json` contains file list and timestamps
- Sorted: `list_backups` returns newest first

**Example: Refactor quote style in Python**

```yaml
# Convert single quotes to double quotes
id: quote-style
language: python
rule:
  pattern: print('$MSG')
fix: print("$MSG")
```

**Usage with rewrite_code tool:**
```python
# Step 1: Preview changes (dry-run mode)
result = rewrite_code(
    project_folder="/path/to/project",
    yaml_rule=yaml_rule_above,
    dry_run=true  # Default - preview only
)
# Returns: {"dry_run": true, "changes": [...previews...]}

# Step 2: Apply changes with automatic backup
result = rewrite_code(
    project_folder="/path/to/project",
    yaml_rule=yaml_rule_above,
    dry_run=false,  # Apply changes
    backup=true     # Default - create backup
)
# Returns: {
#   "dry_run": false,
#   "modified_files": [...],
#   "backup_id": "backup-20250117-120000-123",
#   "validation": {
#     "validated": 3,
#     "passed": 3,
#     "failed": 0,
#     "skipped": 0,
#     "results": [...]
#   }
# }

# Step 3: List available backups
backups = list_backups(project_folder="/path/to/project")
# Returns: [{"backup_id": "...", "timestamp": "...", "file_count": 3, "files": [...]}]

# Step 4: Rollback if needed
result = rollback_rewrite(
    project_folder="/path/to/project",
    backup_id="backup-20250117-120000-123"
)
# Returns: {"restored_files": [...], "backup_id": "..."}
```

**Advanced Options:**
- `max_file_size_mb`: Skip files larger than N MB (prevents processing minified/generated files)
- `workers`: Parallel execution (e.g., `workers=4` for faster rewrites on large codebases)

**Syntax Validation:**

After applying changes, the rewrite tool automatically validates the syntax of all modified files:
- **Python**: Uses built-in `compile()` to detect syntax errors
- **JavaScript/TypeScript**: Uses Node.js if available (falls back to basic validation)
- **C/C++/Java/Rust/Go**: Checks for mismatched braces and basic syntax patterns
- **Other languages**: Reports "validation not supported" but doesn't fail

Validation results are included in the response:
- `validated`: Total files checked
- `passed`: Files with valid syntax
- `failed`: Files with syntax errors (includes warning message)
- `skipped`: Files where validation wasn't possible
- `results`: Per-file validation details

If validation fails, a warning message suggests using `rollback_rewrite()` to restore the original code.

**Best Practices:**
1. Always preview with `dry_run=true` before applying changes
2. Test on a small subset first (use `--paths` in YAML rule to limit scope)
3. Keep backups until changes are verified and committed
4. Use version control (git) as an additional safety layer
5. Run tests after rewriting to ensure functionality preserved

## Architecture

### Single-file Design
Entire server in `main.py` (~3190 lines) for simplicity. Includes logging, streaming, caching, file handling, duplication detection, code rewrite with backups, and Schema.org client.

### Core Components

**Tool Registration:** 16 tools (5 ast-grep search + 3 ast-grep rewrite + 8 Schema.org) registered via `register_mcp_tools()` using FastMCP decorators.

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
