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

Modular MCP server (64 modules) combining ast-grep structural code search with Schema.org tools, refactoring assistants, deduplication, code quality, and documentation generation.

**47 MCP Tools:** Code search (9), Rewrite (3), Refactoring (2), Deduplication (4), Schema.org (9), Complexity (3), Quality (7), Documentation (5), Cross-Language (5)

**Dependencies:** ast-grep CLI (required), Doppler CLI (optional), Python 3.13+, uv

## Code Quality

✅ **ZERO COMPLEXITY VIOLATIONS** - All thresholds met:
- Cyclomatic: ≤20, Cognitive: ≤30, Nesting: ≤6, Function length: ≤150 lines

```bash
uv run pytest tests/quality/test_complexity_regression.py -v  # Verify before commit
```

## Architecture

```
src/ast_grep_mcp/
├── core/           # Config, cache, executor, logging, sentry
├── models/         # Data models
├── utils/          # Templates, formatters, validation
├── features/       # Feature modules
│   ├── search/         # Code search + documentation tools
│   ├── rewrite/        # Code rewrite
│   ├── refactoring/    # Extract function, rename symbol
│   ├── schema/         # Schema.org integration
│   ├── deduplication/  # Duplication detection
│   ├── complexity/     # Complexity analysis
│   ├── quality/        # Linting, security scanning
│   └── documentation/  # Docstring/API doc generation
└── server/         # MCP server registry
```

**Import Pattern:**
```python
from ast_grep_mcp.features.search.service import find_code_impl
from ast_grep_mcp.core.config import get_config
```

## Key Features

- **Code Search:** Pattern matching, YAML rules, AST debugging, pattern development
- **Documentation:** `get_ast_grep_docs` for pattern/rules/metavariables/workflow docs
- **Refactoring:** Extract function, rename symbol with scope awareness
- **Quality:** Security scanner, complexity analysis, auto-fix
- **Schema.org:** Entity generation, graph enhancement, SEO scoring

## Testing

```bash
uv run pytest tests/ -q --tb=no      # All tests
uv run pytest tests/unit/ -v          # Unit tests only
uv run pytest tests/quality/ -v       # Quality regression tests
```

## Configuration

**MCP Client (with Doppler):**
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

**Environment Variables:**
- `AST_GREP_CONFIG` - Path to sgconfig.yaml
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR (default: INFO)
- `SENTRY_DSN` - Sentry error tracking (optional)
- `CACHE_DISABLED` / `CACHE_SIZE` / `CACHE_TTL` - Caching options

## Development Notes

- **YAML rules:** Requires `kind` field; add `stopBy: end` to relational rules
- **Windows:** Use `shell=True` for npm-installed ast-grep
- **Refactoring patterns:** See [PATTERNS.md](PATTERNS.md)

## Key Documentation

- [PATTERNS.md](PATTERNS.md) - Refactoring patterns (80-100% complexity reduction)
- [DEDUPLICATION-GUIDE.md](DEDUPLICATION-GUIDE.md) - Deduplication workflow
- [docs/SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md) - Error tracking
- [docs/DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md) - Secret management

## Troubleshooting

- **Sentry:** Verify `SENTRY_DSN` set, run `test_sentry_integration()` tool
- **Doppler:** Run `doppler login`, verify secrets
- **Tests:** Ensure ast-grep installed (`ast-grep --version`)
- **Quality:** See [PATTERNS.md](PATTERNS.md) for complexity patterns

---

**Last Updated:** 2026-01-10 | **Code Quality:** ✅ ZERO violations | **Tools:** 47
