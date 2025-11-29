# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Quick Start

```bash
uv sync                          # Install dependencies
uv run pytest                    # Run all tests (1,600+ tests)
uv run ruff check . && mypy src/ # Lint and type check
uv run main.py                   # Run MCP server locally
doppler run -- uv run main.py    # Run with Doppler secrets (production)
```

## Project Overview

Modular MCP server with 57 modules combining ast-grep structural code search with Schema.org tools, refactoring assistants, enhanced deduplication, and code quality standards.

**Architecture:** Clean modular design with entry point (`main.py`) and organized features under `src/ast_grep_mcp/` (core, models, utils, features, server).

**30 MCP Tools:** Code search (4), Code rewrite (3), Refactoring (2), Deduplication (4), Schema.org (8), Complexity (3), Code Quality (6)

**Dependencies:** ast-grep CLI (required), Doppler CLI (optional), Python 3.13+, uv package manager

## Recent Work: Phase 1 Complexity Refactoring (2025-11-28)

**Status:** 33% complete (48 → 32 violations)
**Next Session:** See [PHASE1_NEXT_SESSION_GUIDE.md](PHASE1_NEXT_SESSION_GUIDE.md)
**Full Summary:** See [PHASE1_REFACTORING_SUMMARY.md](PHASE1_REFACTORING_SUMMARY.md)

### Completed Refactorings

**Critical Functions (3):**
1. ✅ `format_java_code` - 95% complexity reduction (cyclomatic 39→7, cognitive 60→3)
2. ✅ `detect_security_issues_impl` - 90% reduction (cyclomatic 31→3, cognitive 57→8)
3. ✅ `parse_args_and_get_config` - 90% cyclomatic, 97% cognitive reduction

**Additional Functions (13):**
- Complexity calculators: `calculate_cyclomatic_complexity`, `calculate_cognitive_complexity`
- Quality tools: MCP wrappers refactored with service layer separation
- Search, schema, deduplication modules: Various helper extraction

### Refactoring Patterns Used

1. **Extract Method** - Breaking down large functions into focused helpers
2. **Configuration-Driven Design** - Replacing repetitive if-blocks with data structures
3. **Early Returns** - Reducing nesting with guard clauses
4. **Service Layer Separation** - Extracting business logic from MCP wrappers

### Testing

**Complexity Regression Tests:**
```bash
# Check current violations
uv run pytest tests/quality/test_complexity_regression.py::TestComplexityTrends::test_no_functions_exceed_critical_thresholds -v

# Run all regression tests
uv run pytest tests/quality/test_complexity_regression.py -v
```

**Current Results:**
- ✅ 14/15 tests passing
- ⚠️ 1 expected failure tracking 32 remaining violations
- Target: 15/15 passing (0 violations)

**Critical Thresholds:**
- Cyclomatic complexity: ≤20
- Cognitive complexity: ≤30
- Nesting depth: ≤6
- Function length: ≤150 lines

### Next Priority Functions (Top 5)

1. `_merge_overlapping_groups` - cognitive=58 (93% over limit) ⚠️ HIGHEST
2. `execute_rules_batch` - cognitive=45, nesting=8
3. `analyze_file_complexity` - cognitive=45
4. `_check_test_file_references_source` - cyclomatic=30, cognitive=44
5. `get_test_coverage_for_files_batch` - cognitive=40

## Architecture

**57 Modules organized under `src/ast_grep_mcp/`:**

```
src/ast_grep_mcp/
├── core/           # Config, cache, executor, logging, sentry
├── models/         # Data models for refactoring, deduplication, complexity
├── utils/          # Templates, formatters, text, validation
├── features/       # Feature modules (38 modules)
│   ├── search/         # Code search (2 modules)
│   ├── rewrite/        # Code rewrite (3 modules)
│   ├── refactoring/    # Refactoring assistants (5 modules)
│   ├── schema/         # Schema.org integration (2 modules)
│   ├── deduplication/  # Deduplication (12 modules)
│   ├── complexity/     # Complexity analysis (4 modules)
│   └── quality/        # Code quality (5 modules)
└── server/         # MCP server registry and runner
```

### Import Patterns

**Recommended:**
```python
# Import from service modules
from ast_grep_mcp.features.search.service import find_code_impl
from ast_grep_mcp.features.rewrite.service import rewrite_code_impl

# Import core components
from ast_grep_mcp.core.config import get_config
from ast_grep_mcp.core.cache import get_cache
from ast_grep_mcp.core.executor import execute_ast_grep
```

## Key Features

### Code Complexity Analysis
- Cyclomatic, cognitive complexity, nesting depth, function length
- SQLite storage at `~/.local/share/ast-grep-mcp/complexity.db`
- Regression tests prevent complexity creep

### Code Quality & Standards
- Custom linting rules (24+ templates)
- Security vulnerability scanner (SQL injection, XSS, command injection, secrets, crypto)
- Auto-fix with safety classification
- Parallel rule execution

### Code Deduplication
- Intelligent duplication detection with scoring algorithm
- Automated refactoring with validation
- Test coverage integration (9+ languages)
- Performance benchmarking

### Refactoring Assistants
- Extract function with parameter/return detection
- Rename symbol with scope awareness
- Dry-run mode, backups, rollback support
- Multi-file atomic updates

## Testing

**1,600+ tests:** Unit (mocked) and integration (requires ast-grep)

**Key Test Suites:**
- `test_complexity_regression.py` - Complexity tracking (15 tests)
- `test_extract_function.py` - Function extraction (11 tests)
- `test_rename_symbol.py` - Symbol renaming (21 tests)
- `test_apply_deduplication.py` - Deduplication (24 tests)
- `test_complexity.py` - Complexity analysis (51 tests)

**Run Tests:**
```bash
uv run pytest tests/ -q --tb=no                     # All tests
uv run pytest tests/unit/test_ranking.py -v         # Specific suite
uv run pytest tests/quality/ -v                     # Quality tests only
```

## Configuration

**MCP Client Setup:**

With Doppler:
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

Without Doppler:
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {}
    }
  }
}
```

**Environment Variables:**
- `AST_GREP_CONFIG` - Path to sgconfig.yaml
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR (default: INFO)
- `LOG_FILE` - Path to log file (default: stderr)
- `SENTRY_DSN` - Sentry error tracking (optional)
- `CACHE_DISABLED` - Set to 1 to disable caching
- `CACHE_SIZE` - Max cached queries (default: 100)
- `CACHE_TTL` - Cache TTL in seconds (default: 300)

## Development Notes

- **Windows:** Use `shell=True` for npm-installed ast-grep
- **Config precedence:** `--config` flag > `AST_GREP_CONFIG` env > defaults
- **YAML rules:** Requires `kind` field; add `stopBy: end` to relational rules
- **Streaming:** Early termination on `max_results` (SIGTERM → SIGKILL)
- **Sentry:** Optional monitoring with zero overhead when disabled

## Standalone Tools

```bash
# Schema.org CLI
uv run python scripts/schema-tools.py search "article"

# Duplication detection with analysis
uv run python scripts/find_duplication.py /path/to/project --language python --analyze --detailed

# Performance benchmarks
python scripts/run_benchmarks.py --check-regression
```

## Key Documentation

**Project:**
- README.md - Full project overview
- CLAUDE.md - This file (development guide)

**Features:**
- [DEDUPLICATION-GUIDE.md](DEDUPLICATION-GUIDE.md) - Complete deduplication workflow

**Infrastructure:**
- [SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md) - Error tracking setup
- [DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md) - Secret management
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
- [BENCHMARKING.md](BENCHMARKING.md) - Performance testing

**Refactoring:**
- [PHASE1_REFACTORING_SUMMARY.md](PHASE1_REFACTORING_SUMMARY.md) - Session summary
- [PHASE1_NEXT_SESSION_GUIDE.md](PHASE1_NEXT_SESSION_GUIDE.md) - Quick reference
- [COMPLEXITY_REFACTORING_REPORT.md](COMPLEXITY_REFACTORING_REPORT.md) - Detailed analysis

## Recent Updates

### 2025-11-28: Phase 1 Complexity Refactoring
- Reduced violations from 48 → 32 functions (33% progress)
- Refactored 16 critical functions
- Established refactoring patterns for continued work
- Created comprehensive documentation and next session guide

### 2025-11-27: Security Scanner & Auto-Fix
- Added `detect_security_issues` tool (SQL injection, XSS, command injection, secrets, crypto)
- Added `apply_standards_fixes` tool with safety classification
- Added `generate_quality_report` tool (Markdown/JSON formats)

### 2025-11-26: Refactoring Assistants
- Added `extract_function` tool with parameter/return detection
- Added `rename_symbol` tool with scope-aware renaming
- 32 tests passing for both tools

### 2025-11-25: Tool Registration Complete
- 100% tool registration (30 tools)
- Consistent two-layer pattern (standalone + MCP wrapper)
- Full backward compatibility maintained

### 2025-11-24: Modular Architecture & Code Quality
- Migrated to 57-module architecture
- Added code complexity analysis tools
- Added code smell detection
- Created linting rule system (24+ templates)

### 2025-11-23: Enhanced Deduplication
- Complete rewrite with intelligent analysis
- Automated refactoring with validation
- 1,000+ new tests
- 9+ language test coverage support

## Troubleshooting

**Sentry:** Run `test_sentry_integration()` tool, verify `SENTRY_DSN` set. See [SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md).

**Doppler:** Check auth (`doppler login`), verify secrets. See [DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md).

**Tests:** Ensure ast-grep installed (`ast-grep --version`), clear `.coverage` artifacts.

**Deduplication:** See [DEDUPLICATION-GUIDE.md](DEDUPLICATION-GUIDE.md) for troubleshooting.

**Complexity Issues:** See [PHASE1_NEXT_SESSION_GUIDE.md](PHASE1_NEXT_SESSION_GUIDE.md) for refactoring guidance.
