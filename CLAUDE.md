# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Quick Start

```bash
uv sync                          # Install dependencies
uv run pytest                    # Run all tests (1,150+)
uv run ruff check . && mypy main.py  # Lint and type check
uv run main.py                   # Run MCP server locally
doppler run -- uv run main.py    # Run with Doppler secrets (production)
```

## Project Overview

Single-file MCP server (`main.py`, ~20,000 lines) combining ast-grep structural code search with Schema.org tools and enhanced deduplication.

**23 Tools:** Code search (6), Code rewrite (3), Deduplication (4), Schema.org (8), Complexity (1), Testing (1)

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

**Docs:** See [SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md) and [DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md) for details.

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

**1,150+ tests total:** Unit tests (mocked) and integration tests (requires ast-grep binary)

**Test directories:**
- `tests/unit/` - Core functionality, caching, rewrite, schema, deduplication phases
- `tests/integration/` - End-to-end workflows, CLI, benchmarks, validation pipelines

**Key test files:**
- `test_unit.py` - Core ast-grep functionality
- `test_cache.py` - Query caching
- `test_rewrite.py` - Code rewrite + backups
- `test_apply_deduplication.py` - Deduplication application (24 tests)
- `test_diff_preview.py` - Unified diff generation (39 tests)
- `test_ranking.py` - Scoring algorithm (23 tests)
- `test_coverage_detection.py` - Test coverage detection (40 tests)
- `test_impact_analysis.py` - Impact analysis (33 tests)
- `test_recommendation_engine.py` - Recommendations (27 tests)
- `test_enhanced_reporting.py` - UI/reporting (39 tests)
- `test_benchmark.py` - Performance regression
- `test_complexity.py` - Complexity analysis (46 tests)

**Run specific:** `uv run pytest tests/unit/test_ranking.py -v`

## Code Complexity Analysis

Analyze cyclomatic complexity, cognitive complexity, nesting depth, and function length.

**Tool:** `analyze_complexity`

```python
analyze_complexity(
    project_folder="/path/to/project",
    language="python",  # python, typescript, javascript, java
    cyclomatic_threshold=10,
    cognitive_threshold=15,
    nesting_threshold=4,
    length_threshold=50,
    store_results=True,  # SQLite storage for trends
    include_trends=False
)
```

**Metrics:**
- **Cyclomatic**: McCabe's cyclomatic complexity (decision points + 1)
- **Cognitive**: SonarSource-style with nesting penalties
- **Nesting**: Maximum indentation depth
- **Length**: Lines per function

**Storage:** Results stored in SQLite at `~/.local/share/ast-grep-mcp/complexity.db` (Linux) or equivalent platform location for trend tracking.

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
- `benchmark_deduplication` - Performance benchmarking with regression detection

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

**Scoring Algorithm:**
- Savings: 40% weight (normalized to 500 lines max)
- Complexity: 20% weight (inverse, 1-10 scale)
- Risk: 25% weight (inverse, based on test coverage + call sites)
- Effort: 15% weight (inverse, based on affected files)

**Refactoring Strategies:**
- `extract_function` - Best for simple, stateless duplicates
- `extract_class` - Best for complex/stateful duplicates
- `inline` - Best when duplication is intentional

**CLI:**
```bash
# Basic detection
uv run python scripts/find_duplication.py /path/to/project --language python

# Ranked analysis with recommendations
uv run python scripts/find_duplication.py /path/to/project --language python --analyze --detailed

# Without colors (for CI/CD)
uv run python scripts/find_duplication.py /path/to/project --language python --no-color --json
```

**Docs:** See [DEDUPLICATION-GUIDE.md](DEDUPLICATION-GUIDE.md) for complete documentation.

## Architecture

**Single-file design** (`main.py`, ~20,000 lines) with all functionality integrated.

**Key components:**
- **Execution:** Non-streaming (`subprocess.run`) vs streaming (`subprocess.Popen` with line-by-line parsing)
- **Output formats:** `text` (default, 75% fewer tokens) or `json` (full metadata)
- **Caching:** LRU + TTL for `find_code`/`find_code_by_rule` (config: `--cache-size`, `--cache-ttl`)
- **Parallel execution:** `--threads N` for 50-70% speedup on large projects
- **Duplication:** Hash-based bucketing reduces O(n²) comparisons 83%
- **Schema.org:** Client fetches vocabulary on first use, indexes ~2600+ types in memory
- **Logging:** Structured JSON via structlog to stderr

**Deduplication architecture (Phases 1-6):**
- **Pattern Analysis:** AST-based diff, parameter extraction, variation classification, complexity scoring
- **Code Generation:** Language-specific templates, function generation, import management, formatters
- **Application:** Multi-file orchestration, backup integration, syntax validation, rollback
- **Ranking:** Weighted scoring, test coverage detection, impact analysis, recommendations
- **Reporting:** Color-coded diffs, before/after examples, complexity visualization, CLI enhancement

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

# Duplication detection with analysis
uv run python scripts/find_duplication.py /path/to/project --language python --analyze --detailed

# Performance benchmarks
python scripts/run_benchmarks.py --check-regression  # CI check
```

## Recent Updates

### 2025-11-24: Code Complexity Analysis (Phase 1)

**New feature** - Code analysis and metrics tool for measuring function complexity.

**New MCP tool:** `analyze_complexity`
- Calculates cyclomatic complexity, cognitive complexity, nesting depth, function length
- Supports Python, TypeScript, JavaScript, Java
- Parallel processing via ThreadPoolExecutor for performance
- SQLite storage for trend tracking
- Configurable thresholds (default: cyclomatic=10, cognitive=15, nesting=4, lines=50)

**Components added:**
- Data classes: `ComplexityMetrics`, `FunctionComplexity`, `ComplexityThresholds`
- Language patterns: `COMPLEXITY_PATTERNS` for 4 languages
- Storage: `ComplexityStorage` class with SQLite schema
- Functions: `calculate_cyclomatic_complexity`, `calculate_cognitive_complexity`, `calculate_nesting_depth`, `analyze_file_complexity`

**Testing:** 46 new unit tests in `tests/unit/test_complexity.py`

**Lines added:** ~926 lines to main.py (15,797 → 16,707)

### 2025-11-23: Enhanced Deduplication System (Phases 1-6)

**Major feature release** - Complete rewrite of duplication detection with intelligent analysis and automated refactoring.

**Type Safety:** All 73 mypy type errors fixed - full type annotations for generic types (`Set[str]`, `Dict[str, Any]`, `Match[str]`), logger definitions, and return types.

**6 phases implemented:**
1. **Pattern Analysis Engine** - AST-based diff, parameter extraction, variation classification, complexity scoring (258 tests)
2. **Code Generation Engine** - Templates, function generator, call replacement, import management, formatters (432 tests)
3. **Automated Application Tool** - Multi-file orchestration, backup, diff preview, syntax validation, rollback (90 tests)
4. **Analysis & Ranking Tool** - Scoring algorithm, test coverage detection, impact analysis, recommendations (137 tests)
5. **Enhanced Reporting & UI** - Color-coded diffs, before/after examples, complexity visualization, CLI flags (65 tests)
6. **Testing & Documentation** - DEDUPLICATION-GUIDE.md, benchmark tool, performance regression detection

**Impact:**
- **4 new MCP tools:** `find_duplication`, `analyze_deduplication_candidates`, `apply_deduplication`, `benchmark_deduplication`
- **1,000+ new tests** across all phases
- **~20,500 lines added** to main.py
- **Supports 9+ languages** for test coverage detection (Python, TypeScript, JavaScript, Java, Go, Ruby, Rust, C#)
- **Complete CLI enhancement** with `--analyze`, `--detailed`, `--no-color`, `--max-candidates` flags

**Key functions added:**
- Scoring: `calculate_deduplication_score`, `rank_deduplication_candidates`
- Coverage: `has_test_coverage`, `get_test_coverage_for_files`, `find_test_file_patterns`
- Impact: `analyze_deduplication_impact`, `_assess_breaking_change_risk`
- Generation: `generate_deduplication_recommendation`, `_generate_dedup_refactoring_strategies`
- Reporting: `format_diff_with_colors`, `generate_before_after_example`, `visualize_complexity`, `create_enhanced_duplication_response`
- Orchestration: `create_deduplication_backup`, `_plan_file_modification_order`, `_add_import_to_content`

### 2025-11-18: Repository Organization Refactor
**6-phase cleanup:**
1. Removed `.coverage` from git tracking
2. Moved major docs to root (BENCHMARKING, CONFIGURATION, DOPPLER-MIGRATION, SENTRY-INTEGRATION)
3. Consolidated scripts to `scripts/` directory
4. Deleted 29 redundant repomix snapshots (kept 3 essential)
5. Tracked 12 strategic planning documents
6. Updated documentation

### 2025-11-17: Sentry & Doppler Integration
- Added error tracking to all tools (optional, zero overhead when disabled)
- Integrated Doppler for secret management
- Created comprehensive docs: SENTRY-INTEGRATION.md, DOPPLER-MIGRATION.md
- Added `test_sentry_integration` tool

**No breaking changes** - all features backward compatible.

## Repository Structure

```
main.py              # Single-file server (~20,000 lines, 22 tools)
tests/               # 1,150+ tests
  unit/              # Unit tests (mocked)
  integration/       # Integration tests (requires ast-grep)
scripts/             # Standalone tools (duplication, benchmarks, schema tools)
docs/                # Main documentation
mcp-docs/            # Reference docs for 30+ MCP servers in ecosystem
dev/active/          # Feature planning docs (12 documents)
todos/               # Phase tracking (6 completed phases)
```

**Key docs:** README.md, CLAUDE.md, DEDUPLICATION-GUIDE.md, SENTRY-INTEGRATION.md, DOPPLER-MIGRATION.md, CONFIGURATION.md, BENCHMARKING.md

**Repomix snapshots:** Kept in `mcp-docs/` and `tests/` for codebase analysis. Refresh after major changes: `repomix mcp-docs/`

## Troubleshooting

**Sentry:** Run `test_sentry_integration()` tool, verify `SENTRY_DSN` set. See [SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md).

**Doppler:** Check auth (`doppler login`), verify secrets (`doppler secrets --project bottleneck --config dev`). See [DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md).

**Tests:** Ensure ast-grep installed (`ast-grep --version`), clear `.coverage` artifacts, check mock configs.

**Deduplication:** Check DEDUPLICATION-GUIDE.md for troubleshooting common issues with:
- Pattern matching failures
- Backup/rollback issues
- Import generation errors
- Validation failures
