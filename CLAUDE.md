# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest                    # All tests
uv run pytest tests/unit/        # Unit tests (fast, mocked)
uv run pytest tests/integration/ # Integration tests (requires ast-grep)
uv run pytest --cov=main --cov-report=term-missing  # With coverage

# Lint and type check
uv run ruff check .
uv run mypy main.py

# Run MCP server
uv run main.py

# Standalone tools
uv run python scripts/find_duplication.py /path/to/project --language python
uv run python schema-tools.py search "article"
python3 schema-graph-builder.py ~/path/to/schemas https://example.com
```

## Project Overview

MCP server combining ast-grep's structural code search/rewrite with Schema.org tools. Single-file design (`main.py`, ~4000 lines).

**18 MCP Tools:**
- **Code Search** (6): dump_syntax_tree, test_match_code_rule, find_code, find_code_by_rule, find_duplication, batch_search
- **Code Rewrite** (3): rewrite_code, rollback_rewrite, list_backups
- **Schema.org** (8): get_schema_type, search_schemas, get_type_hierarchy, get_type_properties, generate_schema_example, generate_entity_id, validate_entity_id, build_entity_graph
- **Testing** (1): test_sentry_integration

**External Dependencies:**
- `ast-grep` CLI - must be installed and in PATH
- Internet connection for Schema.org tools (fetches vocabulary on first use)

## Prerequisites

1. **ast-grep**: `brew install ast-grep` or `cargo install ast-grep --locked`
2. **uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. **Python 3.13+**

## Sentry Error Tracking (Optional)

The MCP server includes Sentry error tracking with Anthropic AI integration for monitoring production errors and AI agent interactions.

**Setup with Doppler (Recommended):**

This project is configured to use Doppler for secret management:

```bash
# Project is already set up (see .doppler.yaml)
# Secrets are stored in: bottleneck/dev

# Verify secrets are configured
doppler secrets --project bottleneck --config dev | grep SENTRY

# Run MCP server with Doppler
doppler run -- uv run main.py
```

**Manual Setup (Alternative):**

```bash
# Add to your environment or MCP client configuration
export SENTRY_DSN="your-sentry-dsn"
export SENTRY_ENVIRONMENT="production"  # or "development"
```

**Features:**
- **Error Tracking**: Captures all subprocess errors, API failures, and file operation errors
- **AI Monitoring**: Tracks Claude AI interactions (prompts, responses, token usage) if using Anthropic SDK
- **Performance Monitoring**: Traces slow operations and subprocess execution times
- **Service Tagging**: All events tagged with `service:ast-grep-mcp` for easy filtering

**What Gets Tracked:**
- ast-grep subprocess failures and execution errors
- Schema.org API fetch failures
- File operation errors (backup/restore)
- Code rewrite validation failures
- YAML parsing errors

**Configuration:**
- If `SENTRY_DSN` is not set, Sentry is disabled (no overhead)
- Development: 100% trace sampling for full visibility
- Production: 10% trace sampling to balance cost vs observability

**Privacy:**
- `sendDefaultPii: true` enables AI monitoring (captures prompts/responses)
- Ensure compliance with data privacy policies before enabling in production
- Consider using separate Sentry project for AI-heavy workloads

## MCP Client Configuration

### Option 1: With Doppler (Recommended)

Add to `.cursor-mcp/settings.json` or Claude Desktop:
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "doppler",
      "args": [
        "run",
        "--project", "bottleneck",
        "--config", "dev",
        "--command",
        "uv --directory /absolute/path/to/ast-grep-mcp run main.py"
      ]
    }
  }
}
```

**Benefits:**
- Secrets managed centrally in Doppler (no hardcoded credentials)
- Easy environment switching (dev/stg/prd configs)
- Automatic secret rotation
- Audit logs for secret access

### Option 2: Manual Configuration

Add to `.cursor-mcp/settings.json` or Claude Desktop:
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {
        "SENTRY_DSN": "your-sentry-dsn-here (optional)",
        "SENTRY_ENVIRONMENT": "production (optional)"
      }
    }
  }
}
```

**Note**: Sentry environment variables are optional. If not provided, error tracking is disabled.

## Testing

**Test Organization:**
- `tests/unit/` - 236 tests, mocked subprocess/HTTP calls, no ast-grep required
- `tests/integration/` - 12 tests, requires real ast-grep binary

**Total: 248 tests** (90% coverage: 736/818 statements)

**Key Test Files:**
- `test_unit.py` (57) - Core ast-grep functionality
- `test_cache.py` (26) - Query caching with TTL/LRU eviction
- `test_duplication.py` (24) - Code duplication detection
- `test_phase2.py` (21) - Streaming, parallel execution, large file handling
- `test_schema.py` (52) - Schema.org client and tools
- `test_rewrite.py` (33) - Code rewrite with backups and syntax validation
- `test_batch.py` (18) - Batch operations with parallel execution
- `test_integration.py` (5) - End-to-end with real ast-grep
- `test_benchmark.py` - Performance benchmarks (CI regression detection)

**Running Specific Tests:**
```bash
uv run pytest tests/unit/test_cache.py         # Test caching
uv run pytest tests/unit/test_rewrite.py       # Test code rewrite
uv run pytest tests/unit/test_batch.py         # Test batch operations
uv run pytest tests/integration/test_benchmark.py  # Performance benchmarks
```

## Code Rewrite Functionality

Safe automated code transformations with ast-grep fix rules.

**Safety Features:**
- Dry-run by default (`dry_run=true`)
- Automatic timestamped backups before changes
- Syntax validation (Python, JavaScript/TypeScript, C-like languages)
- Rollback capability via `rollback_rewrite`

**Workflow:**
```python
# 1. Preview (dry-run mode)
rewrite_code(project_folder="/path", yaml_rule=rule, dry_run=true)

# 2. Apply with backup
result = rewrite_code(project_folder="/path", yaml_rule=rule, dry_run=false)
# Returns: {"backup_id": "backup-20250117-...", "validation": {...}}

# 3. Rollback if needed
rollback_rewrite(project_folder="/path", backup_id="backup-20250117-...")
```

**Backups:** Stored in `.ast-grep-backups/backup-YYYYMMDD-HHMMSS-mmm/` with metadata JSON.

**Best Practices:**
1. Always preview with `dry_run=true` first
2. Test on small subset (use `--paths` in YAML rule)
3. Keep backups until verified and committed
4. Use git as additional safety layer
5. Run tests after rewriting

## Architecture

### Single-file Design
Entire server in `main.py` (~3588 lines). Includes logging, streaming, caching, file handling, duplication detection, batch operations, code rewrite with backups, Schema.org client.

### Core Components

**Tool Registration:** 17 tools registered via `register_mcp_tools()` using FastMCP decorators.

**Execution Paths:**
- Non-streaming: `run_ast_grep()` → `subprocess.run()`
- Streaming: `stream_ast_grep_results()` → `subprocess.Popen()` with `--json=stream`

**Output Formats:** `text` (75% fewer tokens, default) or `json` (full metadata). Both use JSON internally.

**Streaming:** Line-by-line parsing with early termination when `max_results` reached. Graceful cleanup via SIGTERM/SIGKILL.

**Large File Handling:** `max_file_size_mb` filters files via `filter_files_by_size()`. Skips large generated/minified files.

**Parallel Execution:** `workers` parameter uses ast-grep's `--threads N`. Can reduce search time 50-70% on large projects.

**Duplication Detection:** Uses ast-grep + difflib similarity. Hash-based bucketing by line count reduces O(n²) comparisons 83%. Filters library code via `exclude_patterns`.

**Batch Operations:** Executes multiple queries in parallel (ThreadPoolExecutor, max 4 workers). Features: deduplication, conditional execution (if_matches/if_no_matches), per-query stats, auto query IDs.

**Schema.org Integration:** SchemaOrgClient fetches vocabulary on first use, indexes ~2600+ types/properties in memory. @id format: `{canonical_url}#{entity_type}`.

**Caching:** LRU cache with TTL for `find_code` and `find_code_by_rule`. Config: `--cache-size N` (default 100), `--cache-ttl SECONDS` (default 300).

**Logging:** Structured JSON via structlog to stderr. Config: `--log-level`, `--log-file`. Key events: tool_invoked, tool_completed, cache_hit/miss.

### Testing Architecture

**MockFastMCP pattern:** Extracts tools for testing. Unit tests mock subprocess; integration tests use real ast-grep.

**Cache isolation:** Clear `main._query_cache` in `setup_method()` to prevent test interference.

## Development Notes

**Windows:** `shell=True` required for npm-installed ast-grep

**Config precedence:** `--config` flag > `AST_GREP_CONFIG` env var > ast-grep defaults

**Streaming benefits:** Early termination on `max_results` saves CPU/I/O. SIGTERM then SIGKILL if needed.

**YAML rules:** Modern ast-grep requires `kind` field. Add `stopBy: end` to relational rules if no matches found.

**Text format:** Minimizes tokens: `filepath:startline-endline` headers + match text.

## Standalone Tools

**schema-tools.py** - Quick Schema.org lookups without MCP server:
```bash
uv run python schema-tools.py search "article"
uv run python schema-tools.py type Person
uv run python schema-tools.py properties Organization --json
```
See `SCHEMA-TOOLS-README.md` for details.

**schema-graph-builder.py** - Build unified entity graphs from JSON files:
```bash
python3 schema-graph-builder.py ~/path/to/schemas https://example.com
```
Outputs: `unified-entity-graph.json`, analysis files, validation reports. See `SCHEMA-GRAPH-BUILDER-README.md`.

**find_duplication.py** - Detect code duplication:
```bash
uv run python scripts/find_duplication.py /path/to/project --language python
./scripts/find_duplication.sh /path/to/project javascript class_definition 0.9
```
Options: `--construct-type`, `--min-similarity`, `--max-constructs`, `--exclude-patterns`, `--json`. See `scripts/README.md`.

## Performance Benchmarking

```bash
python scripts/run_benchmarks.py              # Run benchmarks
python scripts/run_benchmarks.py --save-baseline  # Update baseline
python scripts/run_benchmarks.py --check-regression  # CI regression check
```

Tracks: execution time, memory usage, cache hit performance (>10x speedup), early termination, file filtering. Fails CI if >10% performance degradation. See `BENCHMARKING.md`.
