# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Quick Start

```bash
uv sync                          # Install dependencies
uv run pytest                    # Run all tests (1,586 tests)
uv run ruff check . && mypy src/  # Lint and type check
uv run main.py                   # Run MCP server locally
doppler run -- uv run main.py    # Run with Doppler secrets (production)
```

## Project Overview

Modular MCP server with 57 modules combining ast-grep structural code search with Schema.org tools, refactoring assistants, enhanced deduplication, and code quality standards.

**Architecture:** Clean modular design with entry point (`main.py`) providing backward compatibility and organized features under `src/ast_grep_mcp/` (core, models, utils, features, server).

**30 Tools (100% Registered):** Code search (4), Code rewrite (3), Refactoring Assistants (2), Deduplication (4), Schema.org (8), Complexity (3), Code Quality (6)

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

**Docs:** See [SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md) and [DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md).

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

**1,586 tests total:** Unit tests (mocked) and integration tests (requires ast-grep binary)

**Key test files:**
- `test_extract_function.py` - Function extraction (11 tests)
- `test_rename_symbol.py` - Symbol renaming (21 tests)
- `test_complexity.py` - Complexity analysis (51 tests)
- `test_code_smells.py` - Code smell detection (27 tests)
- `test_apply_deduplication.py` - Deduplication (24 tests)

**Run specific:** `uv run pytest tests/unit/test_ranking.py -v`

## Features

### Code Complexity Analysis

Analyze cyclomatic complexity, cognitive complexity, nesting depth, and function length.

**Tool:** `analyze_complexity`

**Metrics:**
- **Cyclomatic**: McCabe's cyclomatic complexity (decision points + 1)
- **Cognitive**: SonarSource-style with nesting penalties
- **Nesting**: Maximum indentation depth
- **Length**: Lines per function

**Storage:** SQLite at `~/.local/share/ast-grep-mcp/complexity.db`

### Code Smell Detection

**Tool:** `detect_code_smells`

**Detects:**
- Long functions, parameter bloat, deep nesting, large classes, magic numbers
- Severity ratings: high/medium/low

### Code Quality & Standards

**Tools:**
- `create_linting_rule` - Create custom linting rules (24+ templates)
- `list_rule_templates` - Browse rule templates
- `enforce_standards` - Execute linting rules with parallel processing
- `apply_standards_fixes` - Auto-fix violations with safety classification
- `generate_quality_report` - Generate Markdown/JSON quality reports
- `detect_security_issues` - Scan for security vulnerabilities

**Built-in Rule Sets:**
- **recommended** (10): General best practices
- **security** (9): Security vulnerabilities
- **performance** (1): Performance anti-patterns
- **style** (9): Code style consistency

**Security Scanner:**
- SQL injection (f-strings, .format(), concatenation)
- XSS (innerHTML, document.write)
- Command injection (os.system, subprocess with shell=True, eval/exec)
- Hardcoded secrets (API keys, tokens, passwords)
- Insecure cryptography (MD5, SHA-1)
- CWE IDs and confidence scoring

**Storage:** `.ast-grep-rules/{rule-id}.yml`

### Code Rewrite

Safe transformations with automatic backups and syntax validation.

**Workflow:**
```python
rewrite_code(..., dry_run=true)   # Preview
rewrite_code(..., dry_run=false)  # Apply with backup
rollback_rewrite(..., backup_id)  # Undo if needed
```

**Backups:** `.ast-grep-backups/backup-YYYYMMDD-HHMMSS-mmm/`

### Refactoring Assistants

**Tools:**
- `extract_function` - Extract code into reusable functions with parameter/return detection
- `rename_symbol` - Rename symbols with scope awareness and conflict detection

**Features:**
- Dry-run mode with diff preview
- Backup and rollback support
- Multi-file atomic updates (rename_symbol)
- Language support: Python (full), TypeScript/JavaScript/Java (basic)

**Workflow:**
1. Preview with dry_run=True
2. Check for conflicts
3. Apply with dry_run=False
4. Rollback if needed

### Code Deduplication

Enhanced duplication detection with intelligent analysis and automated refactoring.

**Tools:**
- `find_duplication` - Detect duplicate functions/classes/methods
- `analyze_deduplication_candidates` - Rank duplicates by refactoring value
- `apply_deduplication` - Apply refactoring with validation and backup
- `benchmark_deduplication` - Performance benchmarking

**Scoring Algorithm:**
- Savings: 40% weight
- Complexity: 20% weight (inverse)
- Risk: 25% weight (inverse, based on test coverage + call sites)
- Effort: 15% weight (inverse, based on affected files)

**Docs:** See [DEDUPLICATION-GUIDE.md](DEDUPLICATION-GUIDE.md)

## Architecture

**Modular design** with 57 modules organized under `src/ast_grep_mcp/`:

```
src/ast_grep_mcp/
├── core/           # Core infrastructure (6 modules)
│   ├── config.py, cache.py, executor.py
│   └── logging.py, sentry.py, exceptions.py
├── models/         # Data models (6 modules)
│   └── refactoring.py, deduplication.py, complexity.py, standards.py
├── utils/          # Utilities (4 modules)
│   └── templates.py, formatters.py, text.py, validation.py
├── features/       # Feature modules (38 modules)
│   ├── search/         # Code search (2 modules)
│   ├── rewrite/        # Code rewrite (3 modules)
│   ├── refactoring/    # Refactoring assistants (5 modules)
│   ├── schema/         # Schema.org integration (2 modules)
│   ├── deduplication/  # Deduplication (12 modules)
│   ├── complexity/     # Complexity analysis (4 modules)
│   └── quality/        # Code quality (5 modules)
└── server/         # MCP server (3 modules)
    └── registry.py, runner.py
```

### Import Patterns

**New modular pattern (recommended):**
```python
# Import from service modules
from ast_grep_mcp.features.search.service import find_code_impl
from ast_grep_mcp.features.rewrite.service import rewrite_code_impl

# Import core components
from ast_grep_mcp.core.config import get_config
from ast_grep_mcp.core.cache import get_cache
from ast_grep_mcp.core.executor import execute_ast_grep
```

**Backward compatibility (temporary):**
```python
# Old pattern (still works via main.py re-exports)
from main import find_code, rewrite_code
```

## Development Notes

- **Windows:** Use `shell=True` for npm-installed ast-grep
- **Config precedence:** `--config` flag > `AST_GREP_CONFIG` env var > defaults
- **YAML rules:** Requires `kind` field; add `stopBy: end` to relational rules
- **Streaming:** Early termination on `max_results` (SIGTERM → SIGKILL)

## Standalone Tools

```bash
# Schema.org CLI
uv run python scripts/schema-tools.py search "article"

# Duplication detection with analysis
uv run python scripts/find_duplication.py /path/to/project --language python --analyze --detailed

# Performance benchmarks
python scripts/run_benchmarks.py --check-regression
```

## Recent Updates

### 2025-11-27: Security Vulnerability Scanner (Phase 3)

**New MCP tool:**
- **`detect_security_issues`** - Comprehensive security vulnerability scanning

**Vulnerability Detection:**
- **SQL Injection**: f-strings, .format(), string concatenation in SQL queries
- **XSS**: innerHTML assignment, document.write with user input
- **Command Injection**: os.system, subprocess with shell=True, eval/exec
- **Hardcoded Secrets**: API keys, tokens, passwords (regex-based detection)
- **Insecure Cryptography**: MD5, SHA-1 usage

**Features:**
- CWE (Common Weakness Enumeration) IDs for each issue type
- Confidence scoring (0.0-1.0) for vulnerability detection
- Severity levels: critical, high, medium, low
- ast-grep pattern-based detection for code structure
- Regex-based detection for secrets
- Language support: Python, JavaScript, TypeScript, Java

**Components:** 1 new module (~650 lines) in `src/ast_grep_mcp/features/quality/`
- `security_scanner.py` - Vulnerability detection engine

**Usage:**
```python
# Scan for all security issues
result = detect_security_issues(
    project_folder="/path/to/project",
    language="python",
    issue_types=["all"],
    severity_threshold="medium"
)

# Scan for specific vulnerability types
result = detect_security_issues(
    project_folder="/path/to/project",
    language="javascript",
    issue_types=["sql_injection", "xss", "hardcoded_secrets"],
    severity_threshold="critical",
    max_issues=50
)
```

### 2025-11-27: Code Quality Auto-Fix & Reporting (Phases 4-5)

**New MCP tools:**
1. **`apply_standards_fixes`** - Automatically fix code quality violations with safety checks
   - Safe fix classification (confidence 0.6-1.0)
   - Pattern-based fixes with metavariable substitution
   - Batch operations with automatic backup/rollback
   - Dry-run preview mode
   - Syntax validation (Python/JS/TS/Java)

2. **`generate_quality_report`** - Generate comprehensive quality reports
   - Markdown format (human-readable with tables)
   - JSON format (machine-readable structured data)
   - Top issues and problematic files
   - Auto-fix suggestions and recommendations

**Components:** 2 new modules (~945 lines) in `src/ast_grep_mcp/features/quality/`
- `fixer.py` - Auto-fix engine with safety classification
- `reporter.py` - Report generation (Markdown/JSON)

**Complete Workflow:**
```python
# 1. Find violations
result = enforce_standards(project_folder="/path", language="python")

# 2. Auto-fix safe violations
fixed = apply_standards_fixes(
    violations=result["violations"],
    language="python",
    fix_types=["safe"],
    dry_run=False
)

# 3. Generate report
report = generate_quality_report(
    enforcement_result=result,
    output_format="markdown",
    save_to_file="quality-report.md"
)
```

### 2025-11-26: Refactoring Assistants (Phases 1-2)

**New MCP tools:**
1. **`extract_function`** - Extract code with parameter/return detection (11/11 tests passing)
2. **`rename_symbol`** - Scope-aware symbol renaming (21/21 tests passing)

**Components:** 5 modules (~2,144 lines) in `src/ast_grep_mcp/features/refactoring/`

### 2025-11-25: Tool Registration Complete

**Achievement:** 100% tool registration (27 tools) with WebSocket/MCP compatibility

**Improvements:**
- Consistent two-layer pattern (standalone `*_tool` + MCP wrapper)
- Pydantic Field() annotations for parameter validation
- Full backward compatibility

### 2025-11-24: Modular Architecture Refactoring

**Major achievement:** Modular architecture migration with 57 modules created

**Results:**
- 57 modules created under `src/ast_grep_mcp/`
- 10 phases completed over 13 days
- Zero breaking changes

### 2025-11-24: Code Quality & Standards

**New features:**
- `create_linting_rule`, `list_rule_templates` - Rule definition system (24+ templates)
- `enforce_standards` - Standards enforcement with parallel processing

### 2025-11-24: Code Analysis & Metrics

**New tools:**
- `analyze_complexity` - Cyclomatic, cognitive, nesting, length metrics
- `detect_code_smells` - Long functions, parameter bloat, deep nesting, etc.

### 2025-11-23: Enhanced Deduplication System

**Complete rewrite** with intelligent analysis and automated refactoring (6 phases)

**Impact:**
- 4 new MCP tools
- 1,000+ new tests
- Supports 9+ languages for test coverage detection

### 2025-11-17: Sentry & Doppler Integration

- Error tracking (optional, zero overhead when disabled)
- Doppler secret management
- Comprehensive documentation

## Repository Structure

```
main.py              # Entry point with backward compatibility exports
src/ast_grep_mcp/    # Modular codebase (57 modules)
tests/               # 1,586 tests
scripts/             # Standalone tools
docs/                # Main documentation
dev/active/          # Feature planning docs
```

**Key docs:**
- **Project:** README.md, CLAUDE.md
- **Features:** DEDUPLICATION-GUIDE.md
- **Infrastructure:** SENTRY-INTEGRATION.md, DOPPLER-MIGRATION.md, CONFIGURATION.md, BENCHMARKING.md

## Troubleshooting

**Sentry:** Run `test_sentry_integration()` tool, verify `SENTRY_DSN` set. See [SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md).

**Doppler:** Check auth (`doppler login`), verify secrets. See [DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md).

**Tests:** Ensure ast-grep installed (`ast-grep --version`), clear `.coverage` artifacts.

**Deduplication:** See DEDUPLICATION-GUIDE.md for troubleshooting.
- remember to check mcp tool registrations