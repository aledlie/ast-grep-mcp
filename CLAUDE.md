# CLAUDE.md

## Quick Start

```bash
uv sync                          # Install dependencies
uv run pytest                    # Run all tests (1,668 collected)
uv run ruff check . && uv run mypy src/ # Lint and type check
uv run main.py                   # Run MCP server locally
doppler run -- uv run main.py    # Run with Doppler secrets
```

## Overview

Modular MCP server (121 modules) with ast-grep structural code search, Schema.org tools, refactoring, deduplication, quality, documentation generation, and semantic code condensation.

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

- **analyze_complexity** (`complexity.tools`): top-level keys: `summary`, `thresholds`, `functions`, `message`, `storage`. `summary` keys: `total_functions`, `total_files`, `exceeding_threshold` (no trailing `s`), `avg_cyclomatic`, `avg_cognitive`, `max_cyclomatic`, `max_cognitive`, `max_nesting`, `analysis_time_seconds`. `functions[]` with `name`, `file`, `lines`, `cyclomatic`, `cognitive`, `nesting_depth`, `length`, `exceeds`
- **detect_code_smells** (`complexity.tools`): top-level keys: `project_folder`, `language`, `files_analyzed`, `total_smells`, `summary`, `smells`, `thresholds`, `execution_time_ms`. `summary` has `by_type` and `by_severity` (`high`/`medium`/`low`). `smells[]` with `file`, `line`, `severity`, `smell_type`, `message`
- **find_duplication** (`deduplication.tools`): `summary`, `duplication_groups[]`, `refactoring_suggestions[]`; group keys: `group_id`, `similarity_score`, `instances[]` (with `file`, `lines`, `code_preview`)
- **benchmark_deduplication** (`deduplication.tools`): `results[]` with `name`, `mean_ms`, `median_ms`, `p95_ms`
- **enforce_standards** (`quality.tools`): `summary`, `violations[]` with `file`, `line`, `column`, `severity`, `rule_id`, `message`, `code_snippet`
- **detect_security_issues** (`quality.tools`): `summary`, `issues[]` with `file`, `line`, `severity`, `issue_type`, `title`, `cwe_id`
- **detect_orphans** (`quality.tools`): `summary`, `orphan_files[]` (with `file_path`, `lines`, `status`), `orphan_functions[]` (with `file`, `line`, `name`)

Import pattern: `from ast_grep_mcp.features.<module>.tools import <tool_name>_tool`

## Public API vs Internals

- **extract_function** — always call via `extract_function_tool(project_folder, file_path, start_line, end_line, language)` from `refactoring.tools`. Do NOT instantiate `FunctionExtractor` directly; it is an internal class that requires `language` and does not accept `project_folder`.
- **refactor_polyglot** — `refactoring_type` accepts `rename_api`, `extract_constant`, `update_contract`. `rename` is also accepted as an alias for `rename_api`.

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
- [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) - Known issues and workarounds
- [docs/BACKFILLING.md](docs/BACKFILLING.md) - OTEL telemetry backfilling for skills
