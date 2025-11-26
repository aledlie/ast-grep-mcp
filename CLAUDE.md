# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Quick Start

```bash
uv sync                          # Install dependencies
uv run pytest                    # Run all tests (1,541 tests)
uv run ruff check . && mypy src/  # Lint and type check
uv run main.py                   # Run MCP server locally
doppler run -- uv run main.py    # Run with Doppler secrets (production)
```

## Project Overview

Modular MCP server with 52 modules combining ast-grep structural code search with Schema.org tools, refactoring assistants, enhanced deduplication, and code quality standards.

**Architecture:** Clean modular design with 152-line entry point (`main.py`) and organized features under `src/ast_grep_mcp/` (core, models, utils, features, server).

**27 Tools (100% Registered):** Code search (4), Code rewrite (3), Refactoring Assistants (2), Deduplication (4), Schema.org (8), Complexity (3), Code Quality (3)

**Dependencies:** ast-grep CLI (required), Doppler CLI (optional for secrets), Python 3.13+, uv package manager

**Recent Refactoring:** Successfully migrated from monolithic 19,477-line main.py to clean modular structure (99.2% reduction). All 27 tools refactored with consistent two-layer pattern (2025-11-25). New refactoring assistants feature added (2025-11-26).

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

**1,541 tests total:** Unit tests (mocked) and integration tests (requires ast-grep binary)

**Test directories:**
- `tests/unit/` - Core functionality, caching, rewrite, schema, deduplication phases
- `tests/integration/` - End-to-end workflows, CLI, benchmarks, validation pipelines

**Key test files:**
- `test_unit.py` - Core ast-grep functionality
- `test_cache.py` - Query caching
- `test_rewrite.py` - Code rewrite + backups
- `test_extract_function.py` - Function extraction (11 tests)
- `test_rename_symbol.py` - Symbol renaming (21 tests)
- `test_rename_symbol_integration.py` - Multi-file rename integration tests
- `test_apply_deduplication.py` - Deduplication application (24 tests)
- `test_diff_preview.py` - Unified diff generation (39 tests)
- `test_ranking.py` - Scoring algorithm (23 tests)
- `test_coverage_detection.py` - Test coverage detection (40 tests)
- `test_impact_analysis.py` - Impact analysis (33 tests)
- `test_recommendation_engine.py` - Recommendations (27 tests)
- `test_enhanced_reporting.py` - UI/reporting (39 tests)
- `test_benchmark.py` - Performance regression
- `test_complexity.py` - Complexity analysis (51 tests)
- `test_code_smells.py` - Code smell detection (27 tests)

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

## Code Smell Detection

Detect common code smells and anti-patterns in your codebase.

**Tool:** `detect_code_smells`

```python
detect_code_smells(
    project_folder="/path/to/project",
    language="python",  # python, typescript, javascript, java
    long_function_lines=50,
    parameter_count=5,
    nesting_depth=4,
    class_lines=300,
    class_methods=20,
    detect_magic_numbers=True,
    severity_filter="all"  # all, high, medium, low
)
```

**Smells Detected:**
- **Long Functions**: Functions exceeding line threshold
- **Parameter Bloat**: Functions with too many parameters (>5)
- **Deep Nesting**: Excessive nesting depth (>4)
- **Large Classes**: Classes with too many lines/methods
- **Magic Numbers**: Hard-coded literals (excludes 0, 1, -1, 2, 10, 100)

**Severity Levels:** Each smell is rated high/medium/low based on how far it exceeds thresholds.

## Code Quality & Standards - Phase 1: Rule Definition System

Create and manage custom linting rules using ast-grep patterns.

**Tools:**
- `create_linting_rule` - Create custom linting rules
- `list_rule_templates` - Browse 24+ pre-built rule templates

**Create Custom Rules:**
```python
create_linting_rule(
    rule_name="no-console-log",
    description="Disallow console.log in production code",
    pattern="console.log($$$)",
    severity="warning",  # error, warning, or info
    language="typescript",
    suggested_fix="Use proper logging framework",
    note="console.log should only be used during development",
    save_to_project=True,
    project_folder="/path/to/project"
)
```

**Use Templates:**
```python
# List available templates
list_rule_templates(language="python", category="security")

# Create rule from template
create_linting_rule(
    rule_name="no-bare-except",
    use_template="no-bare-except",  # Uses template as base
    save_to_project=True,
    project_folder="/path/to/project"
)
```

**24 Pre-built Templates:**
- **JavaScript/TypeScript (13)**: no-var, no-console-log, no-double-equals, no-empty-catch, no-any-type, prefer-const, no-unused-vars, no-magic-numbers, no-todo-comments, no-fixme-comments, no-debugger, no-hardcoded-credentials, no-sql-injection
- **Python (7)**: no-bare-except, no-mutable-defaults, no-eval-exec, no-print-production, require-type-hints, no-string-exception, no-assert-production
- **Java (4)**: no-system-out, proper-exception-handling, no-empty-finally, no-instanceof-object

**Categories:** general, security, performance, style

**Workflow:**
1. Browse templates with `list_rule_templates()`
2. Create custom rule or use template with `create_linting_rule()`
3. Rules saved to `.ast-grep-rules/` directory in project
4. Pattern syntax validated automatically
5. YAML file generated for ast-grep integration

**Rule Validation:**
- Pattern syntax checked against ast-grep
- Severity must be: error, warning, or info
- Language must be supported by ast-grep
- ID must be kebab-case (e.g., 'no-console-log')
- Returns validation results with errors/warnings

**Storage:**
- Rules saved as YAML files in `.ast-grep-rules/{rule-id}.yml`
- Compatible with standard ast-grep tooling
- Can be checked into version control
- Shared across team

## Standards Enforcement - Phase 2 Complete

Enforce coding standards by executing linting rules against your codebase.

**Tool:** `enforce_standards`

```python
enforce_standards(
    project_folder="/path/to/project",
    language="python",  # python, typescript, javascript, java
    rule_set="recommended",  # recommended, security, performance, style, custom, all
    severity_threshold="info",  # error, warning, info
    max_violations=100,  # 0 = unlimited
    max_threads=4,  # parallel execution
    output_format="json"  # json or text
)
```

**Built-in Rule Sets:**
- **recommended** (10 rules): General best practices (no-var, no-console-log, no-bare-except, etc.)
- **security** (9 rules): Security vulnerabilities (no-eval-exec, no-sql-injection, no-hardcoded-credentials, etc.)
- **performance** (1 rule): Performance anti-patterns (no-magic-numbers)
- **style** (9 rules): Code style consistency (prefer-const, require-type-hints, no-todo-comments, etc.)
- **custom**: Load rules from `.ast-grep-rules/` directory
- **all**: All built-in rules for the specified language

**Features:**
- Parallel rule execution with ThreadPoolExecutor
- Early termination at max_violations
- File exclusion patterns (node_modules, .git, dist, etc.)
- Severity threshold filtering
- Dual output formats (JSON structured data, text human-readable)
- Grouping by file, severity, and rule
- Comprehensive error handling with Sentry

**Workflow:**
```python
# 1. Scan with recommended rules
result = enforce_standards(
    project_folder="/path/to/project",
    language="python",
    rule_set="recommended"
)

# 2. Security-focused scan
result = enforce_standards(
    project_folder="/path/to/project",
    language="typescript",
    rule_set="security",
    severity_threshold="error"
)

# 3. Custom rules only
result = enforce_standards(
    project_folder="/path/to/project",
    language="python",
    rule_set="custom",
    custom_rules=["no-console-log", "no-eval"],
    output_format="text"
)
```

**Output Structure (JSON):**
- `summary`: Statistics (total violations, by severity, by file, execution time)
- `violations`: List of all violations with file, line, column, severity, message, fix suggestion
- `violations_by_file`: Grouped by file path
- `rules_executed`: List of rule IDs that ran
- `execution_time_ms`: Total execution time

**Example Violation:**
```json
{
  "file": "/path/to/file.py",
  "line": 42,
  "column": 5,
  "severity": "error",
  "rule_id": "no-eval-exec",
  "message": "Use of eval() is dangerous",
  "code_snippet": "eval(user_input)",
  "fix_suggestion": "Use ast.literal_eval() or json.loads()"
}
```

## Code Rewrite

Safe transformations with automatic backups and syntax validation.

**Workflow:**
```python
rewrite_code(..., dry_run=true)   # Preview
rewrite_code(..., dry_run=false)  # Apply with backup
rollback_rewrite(..., backup_id)  # Undo if needed
```

**Backups:** `.ast-grep-backups/backup-YYYYMMDD-HHMMSS-mmm/`

## Refactoring Assistants

Automated code refactoring tools with intelligent analysis and safe transformations.

**Tools:**
- `extract_function` - Extract code into reusable functions
- `rename_symbol` - Rename symbols with scope awareness and conflict detection

### Extract Function

Extract selected code into a new function with parameter detection and return value analysis.

**Features:**
- Automatic parameter detection (variables used but not defined in selection)
- Return value analysis (variables defined in selection and used after)
- Multi-return handling (tuple returns for multiple values)
- Language-specific code generation (Python, TypeScript, JavaScript, Java)
- Automatic import management
- Dry-run mode with diff preview
- Backup and rollback support

**Example:**
```python
# 1. Preview extraction (dry-run)
result = extract_function(
    file_path="/path/to/file.py",
    start_line=10,
    end_line=15,
    function_name="calculate_total",
    language="python",
    dry_run=True  # Default: preview only
)

# Check result
if result["success"]:
    print(f"Parameters: {result['parameters']}")
    print(f"Returns: {result['return_values']}")
    print(result["diff_preview"])

    # 2. Apply extraction
    result = extract_function(..., dry_run=False)
    print(f"Backup ID: {result['backup_id']}")
```

### Rename Symbol

Rename symbols across multiple files with scope awareness and conflict detection.

**Features:**
- Scope-aware renaming (respects function, class, module scopes)
- Multi-file atomic updates
- Import/export statement updates
- Conflict detection (prevents shadowing)
- Dry-run mode with diff preview
- Backup and rollback support
- Word boundary matching (avoids partial replacements)

**Supported Languages:**
- Python (full scope analysis)
- JavaScript/TypeScript (basic scope analysis)
- Java (basic scope analysis)

**Example:**
```python
# 1. Preview rename (dry-run)
result = rename_symbol(
    project_folder="/path/to/project",
    symbol_name="processData",
    new_name="transformData",
    language="typescript",
    scope="project",
    dry_run=True  # Default: preview only
)

# Check for conflicts
if result["success"] and not result.get("conflicts"):
    print(f"Found {result['references_found']} references")
    print(f"Affects {len(result['files_modified'])} files")
    print(result["diff_preview"])

    # 2. Apply rename
    result = rename_symbol(..., dry_run=False)
    print(f"Backup ID: {result['backup_id']}")
    print(f"Updated {result['references_updated']} references")
else:
    print("Conflicts detected:")
    for conflict in result.get("conflicts", []):
        print(f"  - {conflict}")
```

**Workflow:**
1. Find all symbol references using ast-grep
2. Build scope tree for affected files
3. Classify references (definition, import, export, usage)
4. Detect naming conflicts
5. Preview changes (dry-run mode)
6. Apply atomically with backup
7. Rollback if needed

**Docs:** See Phase 1 and Phase 2 completion docs in `dev/active/refactoring-assistants/`

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

**Modular design** with 52 modules organized under `src/ast_grep_mcp/`. Main entry point (`main.py`, 152 lines) provides backward compatibility and server startup.

### Module Structure

```
src/ast_grep_mcp/
├── core/           # Core infrastructure (6 modules, ~1,000 lines)
├── models/         # Data models (6 modules, ~850 lines)
├── utils/          # Utilities (4 modules, ~800 lines)
├── features/       # Feature modules (33 modules, ~11,000 lines)
│   ├── search/         # Code search (2 modules)
│   ├── rewrite/        # Code rewrite (3 modules)
│   ├── refactoring/    # Refactoring assistants (6 modules)
│   ├── schema/         # Schema.org integration (2 modules)
│   ├── deduplication/  # Deduplication (12 modules)
│   ├── complexity/     # Complexity analysis (4 modules)
│   └── quality/        # Code quality (5 modules)
└── server/         # MCP server (3 modules, ~60 lines)
```

### Core (`src/ast_grep_mcp/core/`)

- **`config.py`** (237 lines) - Configuration management, environment variables
- **`cache.py`** (137 lines) - LRU + TTL caching for search results
- **`executor.py`** (426 lines) - ast-grep subprocess execution (streaming & non-streaming)
- **`logging.py`** (52 lines) - Structured logging with structlog
- **`sentry.py`** (61 lines) - Error tracking integration (optional)
- **`exceptions.py`** (83 lines) - Custom exception hierarchy

### Models (`src/ast_grep_mcp/models/`)

Data classes and type definitions (6 modules):
- **`config.py`** (49 lines) - Configuration dataclasses
- **`refactoring.py`** (~50 lines) - Refactoring data structures (SymbolReference, ScopeInfo, etc.)
- **`deduplication.py`** (435 lines) - 10+ deduplication data structures
- **`complexity.py`** (31 lines) - Complexity metrics models
- **`standards.py`** (235 lines) - Linting and quality models
- **`base.py`** (6 lines) - Base types and utilities

### Utils (`src/ast_grep_mcp/utils/`)

Shared utilities:
- **`templates.py`** (507 lines) - Code generation templates for refactoring
- **`formatters.py`** (215 lines) - Output formatting, diff generation
- **`text.py`** (51 lines) - Text processing utilities
- **`validation.py`** (13 lines) - Validation helpers

### Features (`src/ast_grep_mcp/features/`)

#### Search Feature (`features/search/`)
- **`service.py`** (454 lines) - Search implementations (find_code, find_by_rule, dump_syntax_tree)
- **`tools.py`** (175 lines) - 4 MCP tool definitions

#### Rewrite Feature (`features/rewrite/`)
- **`backup.py`** (391 lines) - Backup management with rollback
- **`service.py`** (476 lines) - Code rewrite logic with syntax validation
- **`tools.py`** (118 lines) - 3 MCP tool definitions

#### Refactoring Feature (`features/refactoring/`)

Automated refactoring assistants with intelligent analysis:
- **`analyzer.py`** (519 lines) - Variable analyzer, scope detection, dependency tracking
- **`extractor.py`** (475 lines) - Function extraction with parameter/return analysis
- **`renamer.py`** (452 lines) - Symbol renaming with scope awareness
- **`rename_coordinator.py`** (288 lines) - Multi-file rename coordination
- **`tools.py`** (314 lines) - 2 MCP tool definitions (extract_function, rename_symbol)
- **`__init__.py`** (21 lines) - Module exports

**Total:** ~2,069 lines across 6 modules

#### Schema Feature (`features/schema/`)
- **`client.py`** (524 lines) - Schema.org API client (fetches vocabulary, indexes ~2600+ types)
- **`tools.py`** (498 lines) - 8 MCP tool definitions

#### Deduplication Feature (`features/deduplication/`)

Complete duplication detection and refactoring system:
- **`detector.py`** (547 lines) - DuplicationDetector class (hash-based bucketing, reduces O(n²) by 83%)
- **`analyzer.py`** (582 lines) - PatternAnalyzer, variation classification, AST-based diff
- **`generator.py`** (351 lines) - CodeGenerator for refactoring (language-specific templates)
- **`ranker.py`** (201 lines) - DuplicationRanker scoring (weighted algorithm)
- **`applicator.py`** (632 lines) - Multi-file orchestration, backup integration
- **`coverage.py`** (392 lines) - Test coverage detection (9+ languages)
- **`impact.py`** (507 lines) - Impact analysis, breaking change risk assessment
- **`recommendations.py`** (186 lines) - Recommendation engine (extract_function, extract_class, inline)
- **`reporting.py`** (400 lines) - Enhanced reporting with color-coded diffs
- **`benchmark.py`** (290 lines) - Performance benchmarking, regression detection
- **`tools.py`** (274 lines) - 4 MCP tool definitions

#### Complexity Feature (`features/complexity/`)
- **`analyzer.py`** - Complexity calculations (cyclomatic, cognitive, nesting)
- **`metrics.py`** - Complexity metrics classes
- **`storage.py`** - SQLite storage for trend tracking
- **`tools.py`** - 2 MCP tool definitions

#### Quality Feature (`features/quality/`)
- **`smells.py`** - Code smell detection (long functions, parameter bloat, etc.)
- **`rules.py`** - 24+ linting rule templates
- **`validator.py`** - Rule validation against ast-grep
- **`enforcer.py`** - Standards enforcement
- **`tools.py`** - 3 MCP tool definitions

### Server (`src/ast_grep_mcp/server/`)
- **`registry.py`** (32 lines) - Central tool registration
- **`runner.py`** (25 lines) - MCP server entry point

### Key Technical Details

- **Execution:** Non-streaming (`subprocess.run`) vs streaming (`subprocess.Popen` with line-by-line parsing)
- **Output formats:** `text` (default, 75% fewer tokens) or `json` (full metadata)
- **Caching:** LRU + TTL for `find_code`/`find_code_by_rule` (config: `--cache-size`, `--cache-ttl`)
- **Parallel execution:** `--threads N` for 50-70% speedup on large projects
- **Logging:** Structured JSON via structlog to stderr

### Import Patterns

**Backward compatibility (temporary):**
```python
# Old pattern (still works via main.py re-exports)
from main import find_code, rewrite_code
```

**New modular pattern (recommended):**
```python
# Import from service modules
from ast_grep_mcp.features.search.service import find_code_impl
from ast_grep_mcp.features.rewrite.service import rewrite_code_impl

# Or import tool wrappers
from ast_grep_mcp.features.search.tools import find_code
from ast_grep_mcp.features.rewrite.tools import rewrite_code

# Import core components
from ast_grep_mcp.core.config import get_config
from ast_grep_mcp.core.cache import get_cache
from ast_grep_mcp.core.executor import execute_ast_grep
```

**Testing pattern:**
- MockFastMCP extracts tools
- Mock `Popen` for streaming, `run` for file modifications
- Clear cache in `setup_method()` for isolation
- Tests currently use backward compatibility layer in `main.py`

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

### 2025-11-25: Tool Registration Complete - WebSocket Compatibility Fixes

**Achievement:** 100% tool registration complete (25/25 tools) with full WebSocket/MCP compatibility.

**What changed:**
- **All 18 remaining tools refactored** to use consistent two-layer pattern
- **WebSocket communication fixes** - Proper parameter passing via Field() annotations
- **Tool count consolidated** from 27 to 25 tools (detect_code_smells moved to complexity module)

**Tools refactored (2025-11-25):**
- **Complexity tools (3):** `analyze_complexity`, `test_sentry_integration`, `detect_code_smells`
- **Quality tools (3):** `create_linting_rule`, `list_rule_templates`, `enforce_standards`
- **Schema.org tools (8):** All 8 schema tools refactored with proper Pydantic validation
- **Deduplication tools (4):** All 4 deduplication tools refactored with wrapper pattern

**Technical improvements:**
- Standalone `*_tool` functions for testability
- MCP wrapper functions with Pydantic Field() annotations for parameter validation
- Consistent naming pattern across all 25 tools
- Full backward compatibility maintained

**Impact:**
- Zero test failures related to tool registration
- All tools properly communicate via WebSocket protocol
- 100% testable and importable tool functions
- Documentation updated: [TOOL-REGISTRATION-STATUS.md](docs/TOOL-REGISTRATION-STATUS.md)

**Files modified:**
- `src/ast_grep_mcp/features/complexity/tools.py` (+159 lines)
- `src/ast_grep_mcp/features/quality/tools.py` (848 lines refactored)
- `src/ast_grep_mcp/features/schema/tools.py` (886 lines refactored)
- `src/ast_grep_mcp/features/deduplication/tools.py` (+91 lines)
- `docs/TOOL-REGISTRATION-STATUS.md` (updated to reflect 100% completion)

### 2025-11-24: Modular Architecture Refactoring (Phases 0-10)

**Major achievement** - Successfully refactored from monolithic architecture to clean modular design.

**Migration results:**
- **99.2% code reduction** in main.py (19,477 → 152 lines)
- **46 new modules** created under `src/ast_grep_mcp/`
- **10 phases completed** over 13 days
- **Zero breaking changes** - backward compatibility maintained via main.py re-exports

**Phases completed:**
1. **Phase 0:** Project setup - Created directory structure, initialized modules
2. **Phase 1:** Core infrastructure - 6 modules (~1,000 lines): config, cache, executor, logging, sentry, exceptions
3. **Phase 2:** Data models - 5 modules (~800 lines): config, deduplication, complexity, standards models
4. **Phase 3:** Utilities - 4 modules (~800 lines): templates, formatters, text, validation
5. **Phase 4:** Search feature - 2 modules (~600 lines): search service + tools
6. **Phase 5:** Rewrite feature - 3 modules (~1,000 lines): backup, service, tools
7. **Phase 6:** Schema feature - 2 modules (~1,000 lines): client, tools
8. **Phase 7:** Deduplication feature - 12 modules (~4,400 lines): detector, analyzer, ranker, generator, applicator, coverage, impact, recommendations, reporting, benchmark, tools
9. **Phase 8:** Complexity feature - 4 modules (~800 lines): analyzer, metrics, storage, tools
10. **Phase 9:** Quality feature - 5 modules (~1,000 lines): smells, rules, validator, enforcer, tools
11. **Phase 10:** Server integration - 3 modules (~60 lines): registry, runner

**What changed:**
- All code moved to `src/ast_grep_mcp/` directory structure
- Clean separation of concerns (core, models, utils, features, server)
- Entry point (`main.py`) now 152 lines (down from 19,477)
- Backward compatibility layer preserves existing test suite
- All 27 MCP tools registered via central registry

**Benefits:**
- Easier navigation and code discovery
- Clear module boundaries and responsibilities
- Better testability and maintainability
- Foundation for future features
- No performance impact

**Migration guide:** See [docs/MIGRATION-FROM-MONOLITH.md](docs/MIGRATION-FROM-MONOLITH.md) (coming soon)

**Module guide:** See [docs/MODULE-GUIDE.md](docs/MODULE-GUIDE.md) (coming soon)

### 2025-11-26: Code Quality & Standards - Phase 2: Standards Enforcement Engine

**Feature complete** - Execute linting rules against codebases with parallel processing and comprehensive reporting.

**New MCP tool:**

**`enforce_standards`** - Enforce coding standards by executing rule sets
- Execute built-in or custom linting rules against projects
- 5 built-in rule sets: recommended (10), security (9), performance (1), style (9), all
- Parallel execution with ThreadPoolExecutor (configurable threads)
- Early termination at max_violations for performance
- File exclusion patterns (node_modules, .git, dist, etc.)
- Severity threshold filtering (error, warning, info)
- Dual output formats: JSON (structured) or text (human-readable)
- Violation grouping by file, severity, and rule
- Comprehensive error handling with Sentry integration

**Implementation details:**
- **Location:** `src/ast_grep_mcp/features/quality/enforcer.py` (698 lines)
- **Core functions:**
  - `execute_rule()` - Single rule execution with ast-grep streaming
  - `execute_rules_batch()` - Parallel batch execution
  - `parse_match_to_violation()` - Convert matches to violations
  - `should_exclude_file()` - Pattern-based file exclusion
  - `group_violations_by_file/severity/rule()` - Result grouping
  - `filter_violations_by_severity()` - Threshold filtering
  - `format_violation_report()` - Text report generation
  - `enforce_standards_impl()` - Main orchestration function

**Registration:** Added to `main.py` register_mcp_tools() for test compatibility

**Bug fixes:**
- Removed `--lang` argument (language specified in YAML rule)
- Added underscore-prefixed aliases for backward compatibility
- Exported `enforce_standards_tool` from main.py
- Fixed 13 test fixture parameter ordering issues

**Testing:** 80/94 tests passing (85% pass rate, 14 test mocking issues remain)

**Example usage:**
```python
# Scan with recommended rules
result = enforce_standards(
    project_folder="/path/to/project",
    language="python",
    rule_set="recommended",
    max_violations=100,
    output_format="json"
)

# Security-focused scan
result = enforce_standards(
    project_folder="/path/to/project",
    language="typescript",
    rule_set="security",
    severity_threshold="error"
)
```

**Lines added:** ~698 lines in enforcer.py, ~275 lines in tools.py

### 2025-11-26: Refactoring Assistants - Phases 1-2 Complete

**New feature** - Automated code refactoring with intelligent analysis.

**New MCP tools:**

1. **`extract_function`** (Phase 1) - Extract code into reusable functions
   - Automatic parameter detection (variables used but not defined)
   - Return value analysis (variables defined and used after)
   - Multi-return handling (tuple returns for multiple values)
   - Language-specific code generation (Python, TypeScript, JavaScript, Java)
   - Dry-run mode with diff preview
   - Backup and rollback support
   - **Testing:** 11/11 tests passing (100%)
   - **Lines added:** ~1,650 lines (implementation + tests)

2. **`rename_symbol`** (Phase 2) - Rename symbols with scope awareness
   - Scope-aware renaming (function, class, module scopes)
   - Multi-file atomic updates
   - Import/export statement updates
   - Conflict detection (prevents shadowing)
   - Word boundary matching (avoids partial replacements)
   - Dry-run mode with diff preview
   - Backup and rollback support
   - **Testing:** 21/21 tests passing (100%)
   - **Lines added:** ~1,542 lines (implementation: ~915, tests: 627)

**Components added:**
- **6 new modules** in `src/ast_grep_mcp/features/refactoring/`:
  - `analyzer.py` (519 lines) - Variable analyzer, scope detection
  - `extractor.py` (475 lines) - Function extraction logic
  - `renamer.py` (452 lines) - Symbol renaming with scope awareness
  - `rename_coordinator.py` (288 lines) - Multi-file coordination
  - `tools.py` (314 lines) - 2 MCP tool definitions
  - `__init__.py` (21 lines) - Module exports

- **Data models** in `src/ast_grep_mcp/models/refactoring.py`:
  - `SymbolReference` - Symbol metadata with scope info
  - `ScopeInfo` - Scope tree structure
  - Extended models for import/export tracking

**Features:**
- ast-grep integration for accurate symbol finding
- Scope tree building (Python, JavaScript/TypeScript, Java)
- Reference classification (definition, import, export, usage)
- Conflict detection before applying changes
- Multi-file atomic updates with rollback
- Comprehensive error handling with Sentry

**Development time:**
- Phase 1: ~3 hours (implementation) + ~1 hour (refinement)
- Phase 2: ~1.5 hours (implementation) + ~1 hour (tests)

**Total lines:** ~3,192 lines (implementation + tests)

**Docs:** See `dev/active/refactoring-assistants/` for phase completion reports

### 2025-11-24: Code Quality & Standards - Phase 1: Rule Definition System

**New feature** - Create and manage custom linting rules using ast-grep patterns.

**New MCP tools:**

1. **`create_linting_rule`** - Create custom linting rules
   - Define custom code quality rules with ast-grep patterns
   - Template support (24 pre-built templates)
   - Pattern validation against ast-grep
   - Save rules to project's `.ast-grep-rules/` directory
   - YAML generation for ast-grep integration
   - Comprehensive validation (severity, language, ID format, pattern syntax)

2. **`list_rule_templates`** - Browse pre-built rule templates
   - 24 templates across JavaScript/TypeScript, Python, Java
   - Filter by language or category
   - Categories: general, security, performance, style
   - Each template includes pattern, message, fix suggestion, and note

**Components added:**
- Data classes: `LintingRule`, `RuleTemplate`, `RuleValidationResult`
- Exception classes: `RuleValidationError`, `RuleStorageError`
- Rule templates: `RULE_TEMPLATES` dictionary with 24 templates
- Helper functions: `_validate_rule_pattern`, `_validate_rule_definition`, `_save_rule_to_project`, `_load_rule_from_file`, `_get_available_templates`

**Template breakdown:**
- JavaScript/TypeScript: 13 templates (no-var, no-console-log, no-double-equals, etc.)
- Python: 7 templates (no-bare-except, no-mutable-defaults, no-eval-exec, etc.)
- Java: 4 templates (no-system-out, proper-exception-handling, etc.)

**Features:**
- Pattern syntax validation using ast-grep dry-run
- Kebab-case ID validation
- Severity validation (error, warning, info)
- Language validation against supported languages
- Optional fix suggestions
- Save to project with automatic directory creation
- Load from YAML files
- Template filtering by language/category

**Lines added:** ~969 lines to main.py

### 2025-11-24: Code Analysis & Metrics (Phases 1-2)

**New features** - Code complexity analysis and code smell detection tools.

**New MCP tools:**

1. **`analyze_complexity`** - Measures function complexity metrics
   - Cyclomatic complexity, cognitive complexity, nesting depth, function length
   - Supports Python, TypeScript, JavaScript, Java
   - Parallel processing via ThreadPoolExecutor
   - SQLite storage for trend tracking
   - Configurable thresholds (default: cyclomatic=10, cognitive=15, nesting=4, lines=50)

2. **`detect_code_smells`** - Identifies code quality issues
   - Long functions, parameter bloat, deep nesting, large classes, magic numbers
   - Severity ratings (high/medium/low)
   - Actionable suggestions for each smell
   - Parallel file processing

**Key improvements:**
- **Cognitive complexity algorithm** - Improved to follow SonarSource specification:
  - Proper logical operator sequence counting (a && b || c = +2)
  - else if doesn't add nesting penalty
  - Comment skipping for accuracy
- **Benchmark tests** - 5 new tests verifying <10s for 1000 functions

**Components added:**
- Data classes: `ComplexityMetrics`, `FunctionComplexity`, `ComplexityThresholds`
- Language patterns: `COMPLEXITY_PATTERNS` for 4 languages
- Storage: `ComplexityStorage` class with SQLite schema
- Helper functions: `_extract_classes_from_file`, `_count_function_parameters`, `_find_magic_numbers`
- Functions: `calculate_cyclomatic_complexity`, `calculate_cognitive_complexity`, `calculate_nesting_depth`, `analyze_file_complexity`

**Testing:** 78 new unit tests
- `test_complexity.py` - 51 tests (complexity analysis + benchmarks)
- `test_code_smells.py` - 27 tests (smell detection)

**Lines added:** ~1,200 lines to main.py

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
main.py              # Entry point + backward compatibility (152 lines)
src/ast_grep_mcp/    # Modular codebase (46 modules, ~11,500 lines)
  ├── core/          # Core infrastructure (6 modules)
  ├── models/        # Data models (5 modules)
  ├── utils/         # Utilities (4 modules)
  ├── features/      # Feature modules (27 modules)
  │   ├── search/
  │   ├── rewrite/
  │   ├── schema/
  │   ├── deduplication/
  │   ├── complexity/
  │   └── quality/
  └── server/        # MCP server (3 modules)
tests/               # 1,150+ tests
  unit/              # Unit tests (mocked)
  integration/       # Integration tests (requires ast-grep)
scripts/             # Standalone tools (duplication, benchmarks, schema tools)
docs/                # Main documentation
mcp-docs/            # Reference docs for 30+ MCP servers in ecosystem
dev/active/          # Feature planning docs
todos/               # Phase tracking docs
```

**Key docs:**
- **Project:** README.md, CLAUDE.md
- **Features:** DEDUPLICATION-GUIDE.md
- **Infrastructure:** SENTRY-INTEGRATION.md, DOPPLER-MIGRATION.md, CONFIGURATION.md, BENCHMARKING.md
- **Architecture:** MODULE-GUIDE.md (coming soon), MIGRATION-FROM-MONOLITH.md (coming soon)

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
