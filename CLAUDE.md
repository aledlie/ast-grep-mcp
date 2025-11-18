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

# Run with Doppler (recommended for production)
doppler run -- uv run main.py

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
- Optional: Doppler CLI for secret management

## Prerequisites

1. **ast-grep**: `brew install ast-grep` or `cargo install ast-grep --locked`
2. **uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. **Python 3.13+**
4. **Doppler CLI** (optional): `brew install dopplerhq/cli/doppler`

## Sentry Error Tracking & Monitoring

The MCP server includes comprehensive Sentry error tracking with Anthropic AI integration for production monitoring.

### Setup with Doppler (Recommended)

This project is configured to use Doppler for secret management:

```bash
# Project is already set up (see .doppler.yaml)
# Secrets are stored in: bottleneck/dev

# Verify secrets are configured
doppler secrets --project bottleneck --config dev | grep SENTRY

# Run MCP server with Doppler
doppler run -- uv run main.py
```

### Manual Setup (Alternative)

```bash
# Add to your environment or MCP client configuration
export SENTRY_DSN="your-sentry-dsn"
export SENTRY_ENVIRONMENT="production"  # or "development"
```

### What Gets Tracked

**Error Tracking (All 18 Tools):**
- ast-grep subprocess failures and execution errors
- Schema.org API fetch failures
- File operation errors (backup/restore)
- Code rewrite validation failures
- YAML parsing errors
- Cache operations and eviction
- Batch operation failures

**Performance Monitoring:**
- Subprocess execution spans (ast-grep commands)
- HTTP request spans (Schema.org API)
- Batch parallel execution spans
- Execution time tracking for all operations

**AI Monitoring (Anthropic Integration):**
- Claude AI interactions if using Anthropic SDK
- Prompts and responses (when `record_inputs=True`, `record_outputs=True`)
- Token usage and cost tracking

**Service Tagging:**
- All events tagged with `service:ast-grep-mcp`
- Additional tags: `language:python`, `component:mcp-server`
- Easy filtering in Sentry dashboard

### Configuration Options

- **No SENTRY_DSN**: Sentry disabled (zero overhead)
- **Development**: 100% trace sampling for full visibility
- **Production**: 10% trace sampling to balance cost vs observability

### Testing Sentry Integration

Use the `test_sentry_integration` tool to verify your setup:

```python
# Test error capture
test_sentry_integration(test_type="error", message="Test error")

# Test warning capture
test_sentry_integration(test_type="warning", message="Test warning")

# Test breadcrumb trail
test_sentry_integration(test_type="breadcrumb", message="Test breadcrumb")

# Test performance span
test_sentry_integration(test_type="span", message="Test span")
```

**Note**: If `SENTRY_DSN` is not configured, the tool returns `status: "skipped"`.

### Privacy Considerations

- `sendDefaultPii: true` enables AI monitoring (captures prompts/responses)
- Ensure compliance with data privacy policies before enabling in production
- Consider using separate Sentry project for AI-heavy workloads
- Review [SENTRY-INTEGRATION.md](SENTRY-INTEGRATION.md) for detailed privacy guidance

### Documentation

- **[SENTRY-INTEGRATION.md](SENTRY-INTEGRATION.md)**: Complete guide (765 lines) covering setup, tracking details, configuration, troubleshooting, and best practices
- **[DOPPLER-MIGRATION.md](DOPPLER-MIGRATION.md)**: Step-by-step migration guide (699 lines) from manual env vars to Doppler

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
- Automatic secret rotation without config changes
- Audit logs for secret access
- Team collaboration without sharing credentials

**See [DOPPLER-MIGRATION.md](DOPPLER-MIGRATION.md) for complete migration guide.**

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

### Option 3: Without Sentry

Minimal configuration without error tracking:
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

## Testing

**Test Organization:**
- `tests/unit/` - 309+ tests, mocked subprocess/HTTP calls, no ast-grep required
- `tests/integration/` - 12 tests, requires real ast-grep binary

**Total: 267 tests** (254 unit + 13 integration) with comprehensive coverage of error paths and edge cases

**Key Test Files:**
- `test_unit.py` (57) - Core ast-grep functionality
- `test_cache.py` (26) - Query caching with TTL/LRU eviction
- `test_duplication.py` (24) - Code duplication detection
- `test_phase2.py` (21) - Streaming, parallel execution, large file handling
- `test_schema.py` (52) - Schema.org client and tools
- `test_rewrite.py` (33) - Code rewrite with backups and syntax validation
- `test_batch.py` (18) - Batch operations with parallel execution
- `test_edge_cases.py` (78) - **NEW**: Edge cases and error handling paths
- `test_integration.py` (5) - End-to-end with real ast-grep
- `test_benchmark.py` - Performance benchmarks (CI regression detection)

**New Edge Case Tests (Added 2025-11-17):**
- Config validation error paths with `sys.exit`
- Cache configuration via environment variables
- Duplication detection size ratio filtering
- JavaScript/TypeScript validation error handling
- Schema.org client HTTP error fallback
- Rewrite backup handling for nonexistent files
- Command not found error logging
- Streaming subprocess cleanup and early termination

**Running Specific Tests:**
```bash
uv run pytest tests/unit/test_cache.py         # Test caching
uv run pytest tests/unit/test_rewrite.py       # Test code rewrite
uv run pytest tests/unit/test_batch.py         # Test batch operations
uv run pytest tests/unit/test_edge_cases.py    # Test error paths
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
Entire server in `main.py` (~4000 lines). Includes logging, streaming, caching, file handling, duplication detection, batch operations, code rewrite with backups, Schema.org client, and Sentry error tracking.

### Core Components

**Sentry Initialization:** `init_sentry()` called early in server startup, configures:
- Anthropic AI integration with input/output recording
- Service tagging for unified dashboard filtering
- Environment-based sampling rates
- before_send hook for global tags

**Tool Registration:** 18 tools registered via `register_mcp_tools()` using FastMCP decorators.

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

**Logging:** Structured JSON via structlog to stderr. Config: `--log-level`, `--log-file`. Key events: tool_invoked, tool_completed, cache_hit/miss, sentry_error_captured.

### Testing Architecture

**MockFastMCP pattern:** Extracts tools for testing. Unit tests mock subprocess; integration tests use real ast-grep.

**Subprocess Mocking Strategy (Updated 2025-11-17):**
- **Streaming operations** (scan, find): Mock `subprocess.Popen` with iterable stdout
- **File modifications** (rewrite): Mock `subprocess.run` for actual file changes
- Mock processes include proper stderr and wait attributes

**Cache isolation:** Clear `main._query_cache` in `setup_method()` to prevent test interference.

**Edge case coverage:** Dedicated test suite for error paths, environment variables, and graceful degradation.

## Development Notes

**Windows:** `shell=True` required for npm-installed ast-grep

**Config precedence:** `--config` flag > `AST_GREP_CONFIG` env var > ast-grep defaults

**Streaming benefits:** Early termination on `max_results` saves CPU/I/O. SIGTERM then SIGKILL if needed.

**YAML rules:** Modern ast-grep requires `kind` field. Add `stopBy: end` to relational rules if no matches found.

**Text format:** Minimizes tokens: `filepath:startline-endline` headers + match text.

**Sentry overhead:** Zero overhead when SENTRY_DSN not set. Minimal overhead when enabled due to async event sending.

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

## Recent Updates (Updated: 2025-11-18)

### Final Lint Cleanup
**Commit:** 93d4d81 (2025-11-18)

- Fixed remaining auto-fixable ruff import ordering errors in 14 files
- Organized import blocks (I001 violations)
- Removed unused typing imports (F401 violations)
- All 267 tests continue to pass

**Quality Assurance:**
- ✅ ruff validation passes (zero errors)
- ✅ mypy type checking passes
- ✅ Full test suite passing (266 passed, 1 skipped)

### Code Quality Improvements
**Commit:** 77e06e7 (2025-11-18)

- Fixed all ruff and mypy lint errors across 14 files
- Removed unused imports (defaultdict, Tuple, get_supported_languages)
- Fixed f-strings without placeholders in schema-graph-builder.py
- Added explicit type annotations for better type safety
- Renamed exception variables to avoid type conflicts
- Auto-fixed import statement ordering
- All 254 unit tests continue to pass

**Quality Assurance:**
- ✅ ruff validation passes
- ✅ mypy type checking passes
- ✅ 100% test coverage maintained

### Documentation Cleanup
**Commits:** e7753cd, aa411c7, 2fa9225, 583a3a8 (2025-11-18)

- Archived completed strategic plan (Phase 1 & 2: 100% complete) to `~/dev/archive/`
- Removed outdated repomix snapshots from git (now git-ignored, documented)
- Removed experimental README_ENHANCED.md files with Schema.org metadata
- Documented mcp-docs/ directory purpose and maintenance in CLAUDE.md
- Added repository structure section to both CLAUDE.md and README.md
- Documented repomix refresh best practices

**Repository Organization:**
- Clean dev/active/ workspace (only current work)
- mcp-docs/ kept as valuable ecosystem reference (30+ MCP servers)
- Repomix snapshots kept locally for development (regenerable)
- All decisions documented in repository-analysis.md

### Sentry Error Tracking Integration
**Commits:** 826529c, 49cbbb6 (2025-11-17)

- Added comprehensive error tracking to all 18 MCP tools
- Integrated Anthropic AI monitoring for Claude interactions
- Added performance spans for subprocess, HTTP, and batch operations
- Created `test_sentry_integration` tool for setup verification
- Service tagging: All events tagged with `service:ast-grep-mcp`
- Environment-based sampling: 100% dev, 10% production

**Dependencies:**
- Added `sentry-sdk[anthropic]>=2.0.0`

**Configuration:**
- Graceful degradation: Zero overhead when SENTRY_DSN not set
- Privacy controls: `sendDefaultPii: true` for AI monitoring
- Performance: Async event sending, minimal runtime impact

### Doppler Secret Management Integration
**Commit:** d0251da (2025-11-17)

- Migrated from manual environment variables to Doppler
- Project: `bottleneck`, Config: `dev`
- Secrets: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`
- Updated MCP client configuration examples
- Added `.doppler.yaml` to `.gitignore`

**Benefits:**
- Centralized secret management
- Audit logs for access tracking
- Team collaboration without sharing credentials
- Easy environment switching

### Comprehensive Documentation
**Commit:** fb55eba (2025-11-17)

Created extensive documentation (2,190+ lines):
- **SENTRY-INTEGRATION.md** (765 lines): Complete Sentry guide
- **DOPPLER-MIGRATION.md** (699 lines): Step-by-step migration guide
- **README.md** (+167 lines): Quick start and overview updates
- **dev/CONFIGURATION.md** (+567 lines): Configuration examples and validation

### Test Suite Improvements
**Commits:** 112b28d, 47303ce, d21ad5c (2025-11-17)

- Added `.coverage` to `.gitignore` for clean git status
- Created `tests/unit/test_edge_cases.py` (309 lines) covering:
  - Config validation error paths
  - Cache environment variable handling
  - JavaScript validation error handling
  - Schema.org client HTTP errors
  - Streaming subprocess cleanup
- Updated `test_rewrite.py` to properly mock `Popen` for streaming
- Total test count: 267 tests (254 unit + 13 integration)

### Breaking Changes
None. All changes are backward compatible:
- Sentry integration is opt-in via environment variables
- Doppler is recommended but not required
- Existing manual configurations continue to work

### Migration Path
1. **Optional**: Install Doppler CLI
2. **Optional**: Configure Doppler secrets
3. **Optional**: Update MCP client config to use Doppler
4. **Optional**: Restart MCP client to enable Sentry tracking

All features work without migration - this provides enhanced observability for production deployments.

## Repository Structure

### Directory Organization

**Core Files:**
- `main.py` (151KB, ~4000 lines) - Single-file MCP server with all 18 tools
- `pyproject.toml` - uv dependency management
- `uv.lock` - Locked dependencies

**Documentation:**
- `README.md` - Main project documentation
- `CLAUDE.md` - This file, Claude Code instructions
- `SENTRY-INTEGRATION.md` - Sentry setup guide (765 lines)
- `DOPPLER-MIGRATION.md` - Doppler migration guide (699 lines)
- `BENCHMARKING.md` - Performance benchmarking guide
- `ast-grep.mdc` - ast-grep rule writing instructions

**Testing:**
- `tests/unit/` - 8 test files with mocked subprocess/HTTP calls
- `tests/integration/` - 2 test files requiring real ast-grep binary
- Total: 267 tests (254 unit + 13 integration) with comprehensive edge case coverage

**Scripts:**
- `scripts/find_duplication.py` - Standalone duplication detection
- `scripts/run_benchmarks.py` - Performance regression testing
- `schema-tools.py` - Standalone Schema.org CLI
- `schema-graph-builder.py` - Entity graph builder

**Development Documentation:**
- `dev/README.md` - Development workflow guide
- `dev/CONFIGURATION.md` - Configuration examples (567 lines)
- `dev/active/` - Active task documentation and planning
  - `repository-organization-analyzer/` - Current repository analysis and cleanup decisions

**Archived Documentation:**
- `~/dev/archive/ast-grep-mcp-strategic-plan-2025-11/` - Completed Phase 1 & 2 strategic plan (archived 2025-11-18)

### mcp-docs/ Directory

The `mcp-docs/` directory contains reference documentation for 30+ MCP servers available in the ecosystem:

**Purpose:**
- Catalogs available MCP servers by category (AI/ML, Database, Development Tools, etc.)
- Each subdirectory contains README.md and schema.json for one MCP server
- Helps developers understand available MCP integrations
- Reference for configuring Claude Code with different MCP capabilities

**Categories:**
- AI/ML: cloudflare-ai-gateway, memory
- Analytics: cloudflare-radar
- Authentication: auth0
- Automation: mcp-cron, scheduler-mcp
- Database: postgres, redis, supabase
- Development Tools: ast-grep, git-visualization, github, openapi
- And 20+ more across various domains

**Maintenance:**
- Documentation is manually curated
- Updated when new MCP servers are configured or discovered
- Not auto-generated - represents ecosystem snapshot

**Decision:** Kept as-is (Phase 2 analysis, 2025-11-18)
- Provides valuable MCP ecosystem reference
- Well-organized by category
- Size (412KB) justified by comprehensive coverage
- See `dev/active/repository-organization-analyzer/repository-analysis.md` for full analysis

### Repomix Snapshots

The repository includes periodic `repomix-output.xml` files that capture codebase snapshots:

**Locations:**
- `mcp-docs/repomix-output.xml` - MCP documentation snapshot
- `tests/repomix-output.xml` - Test suite snapshot

**Purpose:**
- Provides point-in-time codebase overview
- Useful for analysis, documentation, and understanding project structure
- Can be used with code analysis tools and AI assistants

**Refresh Frequency:**
- **Recommended:** Regenerate after major changes (new features, refactoring)
- **Minimum:** Monthly for active development
- **Triggers:** Before releases, after significant architectural changes

**How to Regenerate:**
```bash
# Install repomix if not already installed
npm install -g repomix

# Generate full repository snapshot
repomix

# Generate specific directory snapshot
repomix mcp-docs/
repomix tests/
```

**Decision:** Kept in repository (Phase 2 analysis, 2025-11-18)
- Provides valuable context for code analysis
- Small size relative to benefit (~100KB total)
- Easily regenerable when outdated
- Git-trackable for change history

## Troubleshooting

### Sentry Not Capturing Events
1. Verify `SENTRY_DSN` is set: `echo $SENTRY_DSN`
2. Use `test_sentry_integration` tool to verify setup
3. Check Sentry dashboard for `service:ast-grep-mcp` tag
4. Review [SENTRY-INTEGRATION.md](SENTRY-INTEGRATION.md) troubleshooting section

### Doppler Secrets Not Loading
1. Verify Doppler authentication: `doppler login`
2. Check project access: `doppler projects`
3. Verify secrets: `doppler secrets --project bottleneck --config dev`
4. Review [DOPPLER-MIGRATION.md](DOPPLER-MIGRATION.md) troubleshooting section

### Test Failures
1. Clear coverage artifacts: `rm .coverage`
2. Ensure ast-grep installed: `ast-grep --version`
3. Run specific test file to isolate issue
4. Check mock configurations for streaming vs run operations

### For More Help
- **Sentry Issues**: See [SENTRY-INTEGRATION.md](SENTRY-INTEGRATION.md)
- **Doppler Issues**: See [DOPPLER-MIGRATION.md](DOPPLER-MIGRATION.md)
- **Configuration**: See [dev/CONFIGURATION.md](dev/CONFIGURATION.md)
- **General Setup**: See [README.md](README.md)
