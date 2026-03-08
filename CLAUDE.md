# CLAUDE.md

## Quick Start

```bash
uv sync                          # Install dependencies
uv run pytest                    # Run all tests (1,598 collected)
uv run ruff check . && uv run mypy src/ # Lint and type check
uv run main.py                   # Run MCP server locally
doppler run -- uv run main.py    # Run with Doppler secrets
```

## Overview

Modular MCP server (120 modules) with ast-grep structural code search, Schema.org tools, refactoring, deduplication, quality, documentation generation, and semantic code condensation.

**53 Tools:** Search (9), Rewrite (3), Refactoring (2), Deduplication (4), Schema.org (9), Complexity (3), Quality (7), Documentation (5), Cross-Language (5), Condense (6)

**Deps:** ast-grep CLI (required), Doppler CLI (optional), Python 3.13+, uv

## Architecture

### Efficiency
- **file tree** load docs/repomix/token-tree.txt into memory before multi-file read/explore or
refactoring tasks for context.
- **compression** use token-tree to identify the correct section in the lossless
  compression file at docs/repomix/repomix.xml during complex debugging or read/explore operations


### Structure
```
src/ast_grep_mcp/
├── core/           # Config, cache, executor, logging, sentry, usage tracking
├── models/         # Data models
├── utils/          # Templates, formatters, validation
├── features/       # search, rewrite, refactoring, schema, deduplication, complexity, quality, documentation, cross_language, condense
└── server/         # MCP server registry
```

**Import:** `from ast_grep_mcp.features.search.service import find_code_impl`

## Code Quality

Quality gates: Ruff + mypy + pytest + analyze_codebase.py

```bash
uv run pytest tests/quality/test_complexity_regression.py -v
```

## Config

**Environment:** `AST_GREP_CONFIG`, `LOG_LEVEL`, `SENTRY_DSN`, `CACHE_DISABLED`/`CACHE_SIZE`/`CACHE_TTL`

## Tool Response Field Names

When calling tools programmatically, use these field names (NOT `line`/`file_path`):

- **analyze_complexity** `functions[]`: `name`, `file`, `lines`, `cyclomatic`, `cognitive`, `nesting_depth`, `length`, `exceeds`
- **find_duplication** top-level: `summary`, `duplication_groups[]`, `refactoring_suggestions[]`; group keys: `group_id`, `similarity_score`, `instances[]` (with `file`, `lines`, `code_preview`)
- **enforce_standards**: `summary`, `violations[]` (with `file`, `line`, `column`, `severity`, `rule_id`, `message`, `code_snippet`)
- **detect_security_issues**: `summary`, `issues[]` (with `file`, `line`, `severity`, `issue_type`, `title`, `cwe_id`)
- **detect_orphans**: `summary`, `orphan_files[]` (with `file_path`, `lines`, `status`), `orphan_functions[]` (with `file`, `line`, `name`)
- **detect_code_smells**: `smells[]` (with `file`, `line`, `severity`, `smell_type`, `message`)
- **benchmark_deduplication**: `results[]` (with `name`, `mean_ms`, `median_ms`, `p95_ms`)

## Analysis Scripts

- Full analysis suite: `uv run python scripts/run_all_analysis.py [src_path]`

## Notes

- YAML rules support `kind`-based matching (e.g., `kind: catch_clause` with `has`); add `stopBy: end` to relational rules
- Windows: use `shell=True` for npm-installed ast-grep
- **All tool functions are synchronous** — call directly, do NOT wrap in `asyncio.run()`
- CLI invocation: `uv run python -c "from ast_grep_mcp.features.X.tools import Y; print(Y(...))"`
- Codebase analyzer: `uv run python analyze_codebase.py <path> -l <language> [--fix]`
- ast-grep supported languages: python, javascript, typescript, tsx, html, css, json, yaml, rust, go, java, kotlin, c, cpp, csharp, swift, ruby, lua, scala — **not** dart

## Docs

- [docs/CHANGELOG.md](docs/CHANGELOG.md) - Version history (index to `docs/changelog/` entries)
- [docs/PATTERNS.md](docs/PATTERNS.md) - Refactoring patterns
- [docs/DEDUPLICATION-GUIDE.md](docs/DEDUPLICATION-GUIDE.md) - Deduplication workflow
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) - Configuration options
- [docs/SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md) - Error tracking
- [docs/BENCHMARKING.md](docs/BENCHMARKING.md) - Performance benchmarking
- [docs/CODE-CONDENSE-PREP.md](docs/CODE-CONDENSE-PREP.md) - Condense feature design
- [docs/CODE-CONDENSE-PHASE-2.md](docs/CODE-CONDENSE-PHASE-2.md) - Condense phase 2 design
- [docs/BACKLOG.md](docs/BACKLOG.md) - Open backlog items
