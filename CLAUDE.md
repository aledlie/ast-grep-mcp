# CLAUDE.md

## Quick Start

```bash
uv sync                          # Install dependencies
uv run pytest                    # Run all tests (1,261)
uv run ruff check . && mypy src/ # Lint and type check
uv run main.py                   # Run MCP server locally
doppler run -- uv run main.py    # Run with Doppler secrets
```

## Overview

Modular MCP server (109 modules) with ast-grep structural code search, Schema.org tools, refactoring, deduplication, quality, and documentation generation.

**47 Tools:** Search (9), Rewrite (3), Refactoring (2), Deduplication (4), Schema.org (9), Complexity (3), Quality (7), Documentation (5), Cross-Language (5)

**Deps:** ast-grep CLI (required), Doppler CLI (optional), Python 3.13+, uv

## Architecture

```
src/ast_grep_mcp/
├── core/           # Config, cache, executor, logging, sentry, usage tracking
├── models/         # Data models
├── utils/          # Templates, formatters, validation
├── features/       # search, rewrite, refactoring, schema, deduplication, complexity, quality, documentation, cross_language
└── server/         # MCP server registry
```

**Import:** `from ast_grep_mcp.features.search.service import find_code_impl`

## Code Quality

Zero complexity violations: Cyclomatic ≤20, Cognitive ≤30, Nesting ≤6, Function ≤150 lines

```bash
uv run pytest tests/quality/test_complexity_regression.py -v
```

## Config

**Environment:** `AST_GREP_CONFIG`, `LOG_LEVEL`, `SENTRY_DSN`, `CACHE_DISABLED`/`CACHE_SIZE`/`CACHE_TTL`

## Notes

- YAML rules require `kind` field; add `stopBy: end` to relational rules
- Windows: use `shell=True` for npm-installed ast-grep

## Docs

- [CHANGELOG.md](CHANGELOG.md) - Version history
- [docs/PATTERNS.md](docs/PATTERNS.md) - Refactoring patterns
- [docs/DEDUPLICATION-GUIDE.md](docs/DEDUPLICATION-GUIDE.md) - Deduplication workflow
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) - Configuration options
- [docs/SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md) - Error tracking
- [docs/BENCHMARKING.md](docs/BENCHMARKING.md) - Performance benchmarking
