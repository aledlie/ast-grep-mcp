# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Quick Start

```bash
uv sync                          # Install dependencies
uv run pytest                    # Run all tests (267 total)
uv run ruff check . && mypy main.py  # Lint and type check
uv run main.py                   # Run MCP server locally
doppler run -- uv run main.py    # Run with Doppler secrets (production)
```

## Project Overview

Single-file MCP server (`main.py`, ~4000 lines) combining ast-grep structural code search with Schema.org tools.

**21 Tools:** Code search (6), Code rewrite (3), Deduplication (3), Schema.org (8), Testing (1)

**Dependencies:** ast-grep CLI (required), Doppler CLI (optional for secrets), Python 3.13+, uv package manager

## Sentry & Doppler Setup

**Optional monitoring** - Zero overhead when not configured.

**Doppler (recommended):**
```bash
doppler secrets --project bottleneck --config dev | grep SENTRY
doppler run -- uv run main.py
```

**Manual:**
```bash
export SENTRY_DSN="your-dsn"
export SENTRY_ENVIRONMENT="production"
```

**What's tracked:** Subprocess failures, API errors, file operations, performance spans, AI interactions (if enabled).

**Docs:** See [SENTRY-INTEGRATION.md](SENTRY-INTEGRATION.md) and [DOPPLER-MIGRATION.md](DOPPLER-MIGRATION.md) for details.

## MCP Client Configuration

**With Doppler:**
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "doppler",
      "args": ["run", "--project", "bottleneck", "--config", "dev", "--command",
               "uv --directory /absolute/path/to/ast-grep-mcp run main.py"]
    }
  }
}
```

**Without Doppler:**
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

**267 tests total:** 254 unit (mocked), 13 integration (requires ast-grep binary)

**Key test files:**
- `test_unit.py` - Core functionality
- `test_cache.py` - Query caching
- `test_rewrite.py` - Code rewrite + backups
- `test_edge_cases.py` - Error paths
- `test_schema.py` - Schema.org client
- `test_benchmark.py` - Performance regression

**Run specific:** `uv run pytest tests/unit/test_cache.py`

## Code Rewrite

Safe transformations with automatic backups and syntax validation.

**Workflow:**
```python
rewrite_code(..., dry_run=true)   # Preview
rewrite_code(..., dry_run=false)  # Apply with backup
rollback_rewrite(..., backup_id)  # Undo if needed
```

**Backups:** `.ast-grep-backups/backup-YYYYMMDD-HHMMSS-mmm/`

## Code Deduplication

Enhanced duplication detection with intelligent analysis and automated refactoring.

**Tools:**
- `find_duplication` - Detect duplicate functions/classes/methods
- `analyze_deduplication_candidates` - Rank duplicates by refactoring value
- `apply_deduplication` - Apply refactoring with validation and backup

**Workflow:**
```python
# 1. Find duplicates
duplicates = find_duplication(project_folder="/path", language="python")

# 2. Get ranked candidates
candidates = analyze_deduplication_candidates(project_path="/path", language="python")

# 3. Preview and apply
preview = apply_deduplication(..., dry_run=True)   # Preview
result = apply_deduplication(..., dry_run=False)   # Apply with backup
```

**CLI:**
```bash
# Basic detection
uv run python scripts/find_duplication.py /path/to/project --language python

# Ranked analysis with recommendations
uv run python scripts/find_duplication.py /path/to/project --language python --analyze --detailed
```

**Docs:** See [DEDUPLICATION-GUIDE.md](DEDUPLICATION-GUIDE.md) for complete documentation.

## Architecture

**Single-file design** (`main.py`, ~4000 lines) with all functionality integrated.

**Key components:**
- **Execution:** Non-streaming (`subprocess.run`) vs streaming (`subprocess.Popen` with line-by-line parsing)
- **Output formats:** `text` (default, 75% fewer tokens) or `json` (full metadata)
- **Caching:** LRU + TTL for `find_code`/`find_code_by_rule` (config: `--cache-size`, `--cache-ttl`)
- **Parallel execution:** `--threads N` for 50-70% speedup on large projects
- **Duplication:** Hash-based bucketing reduces O(n²) comparisons 83%
- **Schema.org:** Client fetches vocabulary on first use, indexes ~2600+ types in memory
- **Logging:** Structured JSON via structlog to stderr

**Testing pattern:**
- MockFastMCP extracts tools
- Mock `Popen` for streaming, `run` for file modifications
- Clear cache in `setup_method()` for isolation

## Development Notes

- **Windows:** Use `shell=True` for npm-installed ast-grep
- **Config precedence:** `--config` flag > `AST_GREP_CONFIG` env var > defaults
- **YAML rules:** Requires `kind` field; add `stopBy: end` to relational rules
- **Streaming:** Early termination on `max_results` (SIGTERM → SIGKILL)

## Standalone Tools

```bash
# Schema.org CLI
uv run python scripts/schema-tools.py search "article"

# Entity graph builder
python3 scripts/schema-graph-builder.py ~/path/to/schemas https://example.com

# Duplication detection
uv run python scripts/find_duplication.py /path/to/project --language python

# Performance benchmarks
python scripts/run_benchmarks.py --check-regression  # CI check
```

## Recent Updates

### 2025-11-18: Repository Organization Refactor
**6-phase cleanup:**
1. Removed `.coverage` from git tracking
2. Moved major docs to root (BENCHMARKING, CONFIGURATION, DOPPLER-MIGRATION, SENTRY-INTEGRATION)
3. Consolidated scripts to `scripts/` directory
4. Deleted 29 redundant repomix snapshots (kept 3 essential)
5. Tracked 12 strategic planning documents
6. Updated documentation

**Impact:** 135 → 120 tracked files (-11%), root docs +133% discoverability, 267 tests passing

### 2025-11-18: Code Quality
- Fixed all ruff/mypy lint errors
- Removed unused imports, organized import blocks
- All tests passing

### 2025-11-17: Sentry & Doppler Integration
- Added error tracking to all 18 tools (optional, zero overhead when disabled)
- Integrated Doppler for secret management
- Created comprehensive docs: SENTRY-INTEGRATION.md, DOPPLER-MIGRATION.md
- Added `test_sentry_integration` tool

**No breaking changes** - all features backward compatible.

## Repository Structure

```
main.py              # Single-file server (~4000 lines, 18 tools)
tests/               # 267 tests (254 unit, 13 integration)
scripts/             # Standalone tools (duplication, benchmarks, schema tools)
docs/                # Main documentation
mcp-docs/            # Reference docs for 30+ MCP servers in ecosystem
dev/active/          # Feature planning docs (12 documents)
```

**Key docs:** README.md, CLAUDE.md, DEDUPLICATION-GUIDE.md, SENTRY-INTEGRATION.md, DOPPLER-MIGRATION.md, CONFIGURATION.md, BENCHMARKING.md

**Repomix snapshots:** Kept in `mcp-docs/` and `tests/` for codebase analysis. Refresh after major changes: `repomix mcp-docs/`

## Troubleshooting

**Sentry:** Run `test_sentry_integration()` tool, verify `SENTRY_DSN` set. See [SENTRY-INTEGRATION.md](SENTRY-INTEGRATION.md).

**Doppler:** Check auth (`doppler login`), verify secrets (`doppler secrets --project bottleneck --config dev`). See [DOPPLER-MIGRATION.md](DOPPLER-MIGRATION.md).

**Tests:** Ensure ast-grep installed (`ast-grep --version`), clear `.coverage` artifacts, check mock configs.
