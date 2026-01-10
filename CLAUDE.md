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

Modular MCP server with 64 modules combining ast-grep structural code search with Schema.org tools, refactoring assistants, enhanced deduplication, code quality standards, and documentation generation.

**Architecture:** Clean modular design with entry point (`main.py`) and organized features under `src/ast_grep_mcp/` (core, models, utils, features, server).

**43 MCP Tools:** Code search (5), Code rewrite (3), Refactoring (2), Deduplication (4), Schema.org (9), Complexity (3), Code Quality (7), Documentation (5), Cross-Language (5)

**Dependencies:** ast-grep CLI (required), Doppler CLI (optional), Python 3.13+, uv package manager

## Code Quality Status 🏆

> **✅ ZERO COMPLEXITY VIOLATIONS** (as of 2025-11-29)
>
> Phase 1 + Phase 2 refactoring **100% COMPLETE**: All 48 complexity violations resolved
> - **Quality Gate:** ✅ PASSING (15/15 regression tests)
> - **Test Coverage:** ✅ 518/533 tests passing (15 pre-existing schema failures)
> - **Patterns Documented:** See [PATTERNS.md](PATTERNS.md) for proven refactoring techniques
> - **Completion Report:** See [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) for full details

**Critical Thresholds (All Met):**
- Cyclomatic complexity: ≤20 ✅
- Cognitive complexity: ≤30 ✅
- Nesting depth: ≤6 ✅
- Function length: ≤150 lines ✅

**Maintaining Quality:**
```bash
# Run before committing to ensure no regressions
uv run pytest tests/quality/test_complexity_regression.py -v
```

## Architecture

**64 Modules organized under `src/ast_grep_mcp/`:**

```
src/ast_grep_mcp/
├── core/           # Config, cache, executor, logging, sentry
├── models/         # Data models for refactoring, deduplication, complexity, documentation, schema_enhancement
├── utils/          # Templates, formatters, text, validation, syntax_validation
├── features/       # Feature modules (45 modules)
│   ├── search/         # Code search (2 modules)
│   ├── rewrite/        # Code rewrite (3 modules)
│   ├── refactoring/    # Refactoring assistants (5 modules)
│   ├── schema/         # Schema.org integration (4 modules: client, tools, enhancement_rules, enhancement_service)
│   ├── deduplication/  # Deduplication (12 modules)
│   ├── complexity/     # Complexity analysis (4 modules)
│   ├── quality/        # Code quality (5 modules)
│   └── documentation/  # Documentation generation (6 modules)
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

# Import shared utilities
from ast_grep_mcp.utils.syntax_validation import suggest_syntax_fix
```

## Key Features

### Code Complexity Analysis
- Cyclomatic, cognitive complexity, nesting depth, function length
- SQLite storage at `~/.local/share/ast-grep-mcp/complexity.db`
- Regression tests prevent complexity creep (15 tests enforcing thresholds)

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

### Documentation Generation
- **generate_docstrings**: Auto-generate docstrings/JSDoc from function signatures (Google, NumPy, Sphinx, JSDoc, Javadoc styles)
- **generate_readme_sections**: Create README sections from code structure analysis
- **generate_api_docs**: Build API documentation from route definitions (Express, FastAPI, Flask) with OpenAPI 3.0 spec
- **generate_changelog**: Generate changelogs from git commits (Keep a Changelog, Conventional formats)
- **sync_documentation**: Keep documentation synchronized with code, detect stale params and broken links

## Testing

**1,600+ tests:** Unit (mocked) and integration (requires ast-grep)

**Key Test Suites:**
- `test_complexity_regression.py` - Complexity tracking (15 tests, **all passing**)
- `test_documentation.py` - Documentation generation (32 tests)
- `test_extract_function.py` - Function extraction (11 tests)
- `test_rename_symbol.py` - Symbol renaming (21 tests)
- `test_apply_deduplication.py` - Deduplication (24 tests)
- `test_complexity.py` - Complexity analysis (51 tests)

**Run Tests:**
```bash
uv run pytest tests/ -q --tb=no                     # All tests
uv run pytest tests/unit/test_ranking.py -v         # Specific suite
uv run pytest tests/quality/ -v                     # Quality tests (15 passing)
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
- **Refactoring:** See [PATTERNS.md](PATTERNS.md) for proven complexity reduction techniques

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

### Project
- [README.md](README.md) - Full project overview
- [CLAUDE.md](CLAUDE.md) - This file (development guide)
- [PATTERNS.md](PATTERNS.md) - **Proven refactoring patterns** (80-100% complexity reduction)

### Features
- [DEDUPLICATION-GUIDE.md](DEDUPLICATION-GUIDE.md) - Complete deduplication workflow

### Infrastructure
- [SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md) - Error tracking setup
- [DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md) - Secret management
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
- [BENCHMARKING.md](BENCHMARKING.md) - Performance testing

### Code Quality & Refactoring
- [PATTERNS.md](PATTERNS.md) - **Proven refactoring patterns and techniques**
- [PHASE2_SESSION2_COMPLETE.md](PHASE2_SESSION2_COMPLETE.md) - Phase 2 completion summary
- [SESSION_REPORT_2025-11-28_Phase2_Complete.md](SESSION_REPORT_2025-11-28_Phase2_Complete.md) - Session report
- [PHASE2_ACTION_PLAN.md](PHASE2_ACTION_PLAN.md) - Complete action plan (archived)

## Refactoring Best Practices

**For new code or refactoring work, follow these proven patterns:**

1. **High Cognitive Complexity (>40)** → Use Extract Method pattern
   - Break into 4-6 focused helpers (20-30 lines each)
   - Expected: 80-97% reduction
   - See [PATTERNS.md](PATTERNS.md#pattern-1-extract-method)

2. **High Cyclomatic Complexity (>30)** → Use Configuration-Driven Design
   - Replace if-elif chains with lookup dictionaries
   - Expected: 90-95% reduction
   - See [PATTERNS.md](PATTERNS.md#pattern-2-configuration-driven-design)

3. **Deep Nesting (>6)** → Use Early Returns / Guard Clauses
   - Fail fast with guard clauses at function start
   - Expected: 50-75% nesting reduction
   - See [PATTERNS.md](PATTERNS.md#pattern-4-early-returns--guard-clauses)

4. **Duplicate Code** → Apply DRY Principle
   - Extract to shared utility modules
   - See [PATTERNS.md](PATTERNS.md#pattern-5-dry-principle-dont-repeat-yourself)

**Quick Pattern Reference:**
```bash
# See full pattern documentation
cat PATTERNS.md

# Check if refactoring needed
uv run pytest tests/quality/test_complexity_regression.py -v
```

## Recent Updates

### 2026-01-09: Pattern Debugging Tool
- Added `debug_pattern` tool for diagnosing why patterns don't match code
- Validates metavariable syntax (detects $name vs $NAME, $123, $KEBAB-CASE errors)
- Compares pattern AST with code AST to find structural mismatches
- Attempts actual matching and reports results
- Provides prioritized suggestions for fixing pattern issues
- Warns about common mistakes like using $ARG instead of $$$ARGS for function arguments
- New models: `pattern_debug.py` with 8 dataclasses/enums
- 31 new tests for pattern debugging
- Total MCP tools: 43 (added 1 search tool)

### 2025-11-29: Entity Graph Enhancement Tool
- Added `enhance_entity_graph` tool for analyzing existing Schema.org JSON-LD graphs
- Suggests missing properties based on Schema.org vocabulary and Google Rich Results guidelines
- Suggests missing entity types (FAQPage, WebSite, BreadcrumbList, Review)
- Calculates SEO completeness scores (0-100) for entities and overall graph
- Validates @id references across the graph
- Three output modes: analysis, enhanced (with placeholders), diff (additions only)
- 51 new tests covering all enhancement functionality
- New models: `schema_enhancement.py` with 6 dataclasses/enums
- New modules: `enhancement_rules.py`, `enhancement_service.py`
- Total MCP tools: 38 (added 1 Schema.org tool)

### 2025-11-29: Documentation Generation Feature
- Added `generate_docstrings` tool with 5 docstring styles (Google, NumPy, Sphinx, JSDoc, Javadoc)
- Added `generate_readme_sections` tool with project analysis
- Added `generate_api_docs` tool with OpenAPI 3.0 spec generation
- Added `generate_changelog` tool with Keep a Changelog and Conventional formats
- Added `sync_documentation` tool for detecting stale docs and broken links
- 32 new tests for documentation generation
- Total MCP tools: 37 (added 5 documentation tools)

### 2025-11-28: Phase 2 Complexity Refactoring COMPLETE 🎉
- ✅ **ZERO violations achieved** (48 → 0 functions, 100% complete)
- ✅ Refactored all 25 remaining complex functions
- ✅ Created [PATTERNS.md](PATTERNS.md) with proven refactoring techniques
- ✅ Quality gate now **PASSING** (15/15 regression tests)
- ✅ 278 module tests passing (all refactored code verified)
- **Key Achievements:**
  - 100% cognitive reduction in _assess_breaking_change_risk (44→0)
  - 97% cognitive reduction in _parallel_enrich (74→2, highest violation)
  - 94% reduction in both _extract_classes functions (35→2 each)
  - Eliminated 118 lines of duplicate code via DRY principle
  - Created shared utils/syntax_validation.py module

### 2025-11-27: Security Scanner & Auto-Fix
- Added `detect_security_issues` tool (SQL injection, XSS, command injection, secrets, crypto)
- Added `apply_standards_fixes` tool with safety classification
- Added `generate_quality_report` tool (Markdown/JSON formats)

### 2025-11-26: Refactoring Assistants
- Added `extract_function` tool with parameter/return detection
- Added `rename_symbol` tool with scope-aware renaming
- 32 tests passing for both tools

### 2025-11-25: Tool Registration Complete
- 100% tool registration (38 tools)
- Consistent two-layer pattern (standalone + MCP wrapper)

### 2025-11-24: Modular Architecture & Code Quality
- Migrated to 64-module architecture
- Added code complexity analysis tools
- Added code smell detection
- Created linting rule system (24+ templates)
- `main.py` reduced to entry point only (10 lines)

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

**Code Quality:** All complexity violations resolved. See [PATTERNS.md](PATTERNS.md) for maintaining quality standards.

---

**Last Updated:** 2026-01-09
**Code Quality:** ✅ ZERO violations (15/15 tests passing)
**Refactoring Patterns:** See [PATTERNS.md](PATTERNS.md)
**Documentation Generation:** 5 new tools, 32 tests passing
