# Modular Architecture Design for ast-grep-mcp

**Date:** 2025-11-24
**Status:** Design Phase
**Current State:** Single file (19,477 lines)
**Target State:** Modular package structure (30+ files)

## Executive Summary

This document outlines a comprehensive plan to refactor `main.py` from a single 19,477-line file into a maintainable, modular architecture following software engineering best practices. The design prioritizes **backward compatibility**, **testability**, and **developer experience** while maintaining all existing functionality.

**Key Goals:**
- Zero breaking changes to MCP tool interfaces
- All 1,561 tests pass without modification (initially)
- Improved code discovery (<30 seconds to find any function)
- Reduced merge conflicts between developers
- Clear separation of concerns
- Easy addition of new features

## Current State Analysis

### File Structure
```
main.py (19,477 lines)
├── Imports (1-29)                           30 lines
├── Global configuration (30-37)              8 lines
├── Templates (38-300)                      263 lines
├── Logging setup (301-400)                 100 lines
├── Sentry initialization (401-500)         100 lines
├── Cache management (501-800)              300 lines
├── AST-grep execution (801-1307)           507 lines
├── Schema.org client (1307-1320)            14 lines
├── MCP tool registration (1320-5673)     4,354 lines ← MASSIVE
├── Deduplication (5674-16700)           11,027 lines ← HUGE
├── Complexity analysis (16701-17600)       900 lines
├── Code quality Phase 1 (17601-18570)      970 lines
├── Code quality Phase 2 (18571-19207)      637 lines
├── Complexity storage (19208-19400)        193 lines
└── Server runner (19401-19477)              77 lines
```

### Tool Distribution (27 total tools)

**AST-grep Search (6 tools):**
- `dump_syntax_tree` - Syntax tree inspection
- `test_match_code_rule` - Rule testing
- `find_code` - Pattern search (cached)
- `find_code_by_rule` - YAML rule search (cached)
- `scan_project` - Streaming project scan
- `rewrite_code` - Code transformation with backup

**Code Rewrite (3 tools):**
- `rewrite_code` - Safe code rewrite with backup
- `list_backups` - List available backups
- `rollback_rewrite` - Restore from backup

**Deduplication (4 tools):**
- `find_duplication` - Detect duplicate code
- `analyze_deduplication_candidates` - Rank duplicates
- `apply_deduplication` - Apply refactoring
- `benchmark_deduplication` - Performance testing

**Schema.org (8 tools):**
- `list_schema_org_types` - List all types
- `search_schema_org` - Search vocabulary
- `get_schema_org_type` - Get type details
- `get_schema_org_property` - Get property details
- `list_schema_org_children` - List subtypes
- `get_schema_org_domain_range` - Get domains/ranges
- `get_schema_org_parent_chain` - Get inheritance chain
- `get_schema_org_subtree` - Get type subtree

**Complexity Analysis (2 tools):**
- `analyze_complexity` - Function complexity metrics
- `test_sentry_integration` - Sentry error tracking test

**Code Quality & Standards (3 tools):**
- `detect_code_smells` - Detect anti-patterns
- `validate_linting_rules` - Validate rule definitions
- `enforce_standards` - Apply rules to codebase

### Key Classes (33 total)

**Exceptions (6):**
- `AstGrepError`, `AstGrepNotFoundError`, `InvalidYAMLError`
- `ConfigurationError`, `AstGrepExecutionError`, `NoMatchesError`

**Core Infrastructure (4):**
- `QueryCache` - LRU cache with TTL
- `CustomLanguageConfig` - Language configuration
- `AstGrepConfig` - Main configuration
- `SchemaOrgClient` - Schema.org API client

**Deduplication (8):**
- `VariationCategory`, `VariationSeverity` - Enums
- `AlignmentSegment`, `AlignmentResult` - Code alignment
- `DiffTreeNode`, `DiffTree` - Diff tree structure
- `FunctionTemplate`, `ParameterType`, `ParameterInfo` - Code generation

**Complexity & Quality (6):**
- `ComplexityMetrics`, `FunctionComplexity`, `ComplexityThresholds`
- `ComplexityStorage` - SQLite storage

**Standards Enforcement (9):**
- `RuleValidationError`, `RuleStorageError` - Exceptions
- `LintingRule`, `RuleTemplate`, `RuleValidationResult`
- `RuleViolation`, `RuleSet`, `EnforcementResult`, `RuleExecutionContext`

### Dependencies

**External:**
- `mcp.server.fastmcp` - FastMCP server
- `pydantic` - Data validation
- `structlog` - Structured logging
- `sentry_sdk` - Error tracking
- `httpx` - HTTP client for Schema.org
- `yaml` - YAML parsing

**Internal Cross-Dependencies:**
- Deduplication uses complexity analysis functions
- Code quality uses AST-grep execution
- All tools use logging and Sentry
- All search tools use caching
- All write tools use backup management

## Proposed Architecture

### Design Principles

1. **Feature-Based Organization** - Group by domain (search, rewrite, deduplication)
2. **Layered Architecture** - Separate tools, services, infrastructure
3. **Dependency Inversion** - Tools depend on abstractions, not implementations
4. **Single Responsibility** - Each module has one clear purpose
5. **Plugin Architecture** - Easy to add new tool categories
6. **Backward Compatibility** - Re-export everything from main.py initially

### Directory Structure

```
ast-grep-mcp/
├── main.py                          # Entry point + re-exports (50-100 lines)
├── pyproject.toml
├── README.md
├── CLAUDE.md
│
├── src/
│   └── ast_grep_mcp/               # Main package
│       ├── __init__.py             # Package exports
│       │
│       ├── core/                   # Core infrastructure (shared)
│       │   ├── __init__.py
│       │   ├── config.py           # Configuration classes
│       │   ├── cache.py            # Query cache implementation
│       │   ├── logging.py          # Logging setup
│       │   ├── sentry.py           # Sentry initialization
│       │   ├── exceptions.py       # Custom exceptions
│       │   └── executor.py         # AST-grep command execution
│       │
│       ├── models/                 # Data models (Pydantic/dataclasses)
│       │   ├── __init__.py
│       │   ├── config.py           # AstGrepConfig, CustomLanguageConfig
│       │   ├── deduplication.py    # Deduplication models
│       │   ├── complexity.py       # Complexity models
│       │   └── standards.py        # Standards enforcement models
│       │
│       ├── utils/                  # Shared utilities
│       │   ├── __init__.py
│       │   ├── templates.py        # Code generation templates
│       │   ├── formatters.py       # Code formatters (Python, Java, TS)
│       │   ├── text.py             # Text processing utilities
│       │   └── validation.py       # Validation utilities
│       │
│       ├── features/               # Feature modules (business logic)
│       │   ├── __init__.py
│       │   │
│       │   ├── search/             # AST-grep search features
│       │   │   ├── __init__.py
│       │   │   ├── service.py      # Search business logic
│       │   │   ├── syntax.py       # Syntax tree operations
│       │   │   └── tools.py        # MCP tool definitions
│       │   │
│       │   ├── rewrite/            # Code rewrite features
│       │   │   ├── __init__.py
│       │   │   ├── service.py      # Rewrite business logic
│       │   │   ├── backup.py       # Backup management
│       │   │   └── tools.py        # MCP tool definitions
│       │   │
│       │   ├── deduplication/      # Deduplication features
│       │   │   ├── __init__.py
│       │   │   ├── detector.py     # Duplicate detection
│       │   │   ├── analyzer.py     # Pattern analysis
│       │   │   ├── ranker.py       # Candidate ranking
│       │   │   ├── generator.py    # Code generation
│       │   │   ├── applicator.py   # Apply refactoring
│       │   │   ├── coverage.py     # Test coverage detection
│       │   │   ├── impact.py       # Impact analysis
│       │   │   ├── recommendations.py  # Recommendation engine
│       │   │   ├── reporting.py    # Enhanced reporting
│       │   │   ├── benchmark.py    # Performance benchmarking
│       │   │   └── tools.py        # MCP tool definitions
│       │   │
│       │   ├── complexity/         # Complexity analysis
│       │   │   ├── __init__.py
│       │   │   ├── analyzer.py     # Complexity analysis
│       │   │   ├── metrics.py      # Metric calculation
│       │   │   ├── storage.py      # SQLite storage
│       │   │   └── tools.py        # MCP tool definitions
│       │   │
│       │   ├── quality/            # Code quality & standards
│       │   │   ├── __init__.py
│       │   │   ├── smells.py       # Code smell detection
│       │   │   ├── rules.py        # Linting rules
│       │   │   ├── validator.py    # Rule validation
│       │   │   ├── enforcer.py     # Standards enforcement
│       │   │   └── tools.py        # MCP tool definitions
│       │   │
│       │   └── schema/             # Schema.org integration
│       │       ├── __init__.py
│       │       ├── client.py       # Schema.org API client
│       │       └── tools.py        # MCP tool definitions
│       │
│       └── server/                 # MCP server setup
│           ├── __init__.py
│           ├── registry.py         # Tool registration
│           └── runner.py           # Server entry point
│
├── scripts/                        # Standalone tools (unchanged)
│   ├── find_duplication.py
│   ├── schema-tools.py
│   └── run_benchmarks.py
│
├── tests/                          # Tests (unchanged initially)
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
└── docs/                           # Documentation
    ├── MODULAR-ARCHITECTURE.md     # This document
    ├── MIGRATION-PLAN.md           # Step-by-step migration
    └── MODULE-DEPENDENCIES.md      # Dependency graph
```

### Module Responsibilities

#### Core Layer (`core/`)

**Purpose:** Shared infrastructure used by all features

**`core/config.py`** (150 lines)
```python
# Classes: CustomLanguageConfig, AstGrepConfig
# Functions: validate_config_file, parse_args_and_get_config
# Globals: CONFIG_PATH, CACHE_ENABLED, CACHE_SIZE, CACHE_TTL
```

**`core/cache.py`** (300 lines)
```python
# Classes: QueryCache
# Functions: get_query_cache
# Features: LRU cache with TTL, thread-safe
```

**`core/logging.py`** (100 lines)
```python
# Functions: configure_logging, get_logger
# Features: Structlog setup, JSON output
```

**`core/sentry.py`** (100 lines)
```python
# Functions: init_sentry
# Features: Sentry SDK initialization, error tracking
```

**`core/exceptions.py`** (80 lines)
```python
# Classes: AstGrepError, AstGrepNotFoundError, InvalidYAMLError,
#          ConfigurationError, AstGrepExecutionError, NoMatchesError
```

**`core/executor.py`** (500 lines)
```python
# Functions: run_ast_grep, run_command, get_supported_languages
# Features: Subprocess execution, streaming support, error handling
```

#### Models Layer (`models/`)

**Purpose:** Data structures with no business logic

**`models/config.py`** (100 lines)
```python
# Classes: CustomLanguageConfig, AstGrepConfig
# Pure Pydantic models, no logic
```

**`models/deduplication.py`** (400 lines)
```python
# Classes: VariationCategory, VariationSeverity, AlignmentSegment,
#          AlignmentResult, DiffTreeNode, DiffTree, FunctionTemplate,
#          ParameterType, ParameterInfo, FileDiff, DiffPreview,
#          EnhancedDuplicationCandidate
```

**`models/complexity.py`** (100 lines)
```python
# Classes: ComplexityMetrics, FunctionComplexity, ComplexityThresholds
```

**`models/standards.py`** (200 lines)
```python
# Classes: RuleValidationError, RuleStorageError, LintingRule,
#          RuleTemplate, RuleValidationResult, RuleViolation,
#          RuleSet, EnforcementResult, RuleExecutionContext
```

#### Utils Layer (`utils/`)

**Purpose:** Reusable utilities with no state

**`utils/templates.py`** (400 lines)
```python
# Constants: PYTHON_CLASS_TEMPLATE, JAVA_CLASS_TEMPLATE, etc.
# Functions: format_python_class, format_java_code, format_typescript_class
```

**`utils/formatters.py`** (300 lines)
```python
# Functions: format_java_code, format_typescript_code, format_matches_as_text
```

**`utils/text.py`** (200 lines)
```python
# Functions: normalize_code, calculate_similarity
```

**`utils/validation.py`** (150 lines)
```python
# Functions: validate_config_file, validate_yaml_rule
```

#### Features Layer (`features/`)

**Purpose:** Feature-specific business logic and MCP tools

**`features/search/service.py`** (600 lines)
```python
# Functions: dump_syntax_tree_impl, test_match_code_rule_impl,
#            find_code_impl, find_code_by_rule_impl, scan_project_impl
# Business logic only, no MCP decorators
```

**`features/search/tools.py`** (400 lines)
```python
# All @mcp.tool() decorators for search tools
# Thin wrappers calling service functions
```

**`features/rewrite/service.py`** (500 lines)
```python
# Functions: rewrite_code_impl, list_backups_impl, rollback_rewrite_impl
```

**`features/rewrite/backup.py`** (300 lines)
```python
# Functions: create_backup, restore_backup, list_available_backups
```

**`features/rewrite/tools.py`** (300 lines)
```python
# All @mcp.tool() decorators for rewrite tools
```

**`features/deduplication/detector.py`** (1,500 lines)
```python
# Functions: find_duplication_impl, detect_variations_between_blocks,
#            detect_conditional_variations, group_duplicates
```

**`features/deduplication/analyzer.py`** (1,200 lines)
```python
# Functions: classify_variation, classify_variations,
#            analyze_duplicate_variations, build_diff_tree, align_code_blocks
```

**`features/deduplication/ranker.py`** (800 lines)
```python
# Functions: calculate_deduplication_score, rank_deduplication_candidates,
#            calculate_refactoring_complexity, get_complexity_level
```

**`features/deduplication/generator.py`** (1,800 lines)
```python
# Functions: generate_refactoring_suggestions, generate_parameter_names,
#            identify_varying_identifiers, generate_function_code
```

**`features/deduplication/applicator.py`** (1,200 lines)
```python
# Functions: apply_deduplication_impl, create_deduplication_backup,
#            validate_refactoring, rollback_deduplication
```

**`features/deduplication/coverage.py`** (1,000 lines)
```python
# Functions: has_test_coverage, get_test_coverage_for_files,
#            find_test_file_patterns, detect_test_framework
```

**`features/deduplication/impact.py`** (600 lines)
```python
# Functions: analyze_deduplication_impact, assess_breaking_change_risk,
#            estimate_migration_effort
```

**`features/deduplication/recommendations.py`** (800 lines)
```python
# Functions: generate_deduplication_recommendation,
#            generate_refactoring_strategies, suggest_best_approach
```

**`features/deduplication/reporting.py`** (1,000 lines)
```python
# Functions: format_diff_with_colors, generate_before_after_example,
#            visualize_complexity, create_enhanced_duplication_response
```

**`features/deduplication/benchmark.py`** (400 lines)
```python
# Functions: benchmark_deduplication_impl, check_performance_regression
```

**`features/deduplication/tools.py`** (600 lines)
```python
# All @mcp.tool() decorators for deduplication (4 tools)
```

**`features/complexity/analyzer.py`** (600 lines)
```python
# Functions: analyze_complexity_impl, analyze_file_complexity,
#            calculate_cyclomatic_complexity, calculate_cognitive_complexity
```

**`features/complexity/metrics.py`** (300 lines)
```python
# Functions: calculate_nesting_depth, calculate_function_length,
#            get_complexity_trends
```

**`features/complexity/storage.py`** (200 lines)
```python
# Classes: ComplexityStorage
# Functions: store_complexity_results, get_historical_trends
```

**`features/complexity/tools.py`** (200 lines)
```python
# All @mcp.tool() decorators for complexity (2 tools)
```

**`features/quality/smells.py`** (500 lines)
```python
# Functions: detect_code_smells_impl, detect_long_functions,
#            detect_parameter_bloat, detect_magic_numbers
```

**`features/quality/rules.py`** (400 lines)
```python
# Functions: load_rules, create_rule_from_template, store_rule
```

**`features/quality/validator.py`** (300 lines)
```python
# Functions: validate_linting_rules_impl, validate_rule_syntax,
#            check_rule_conflicts
```

**`features/quality/enforcer.py`** (500 lines)
```python
# Functions: enforce_standards_impl, execute_rules, collect_violations
```

**`features/quality/tools.py`** (300 lines)
```python
# All @mcp.tool() decorators for quality (3 tools)
```

**`features/schema/client.py`** (600 lines)
```python
# Classes: SchemaOrgClient
# Functions: get_schema_org_client
```

**`features/schema/tools.py`** (500 lines)
```python
# All @mcp.tool() decorators for Schema.org (8 tools)
```

#### Server Layer (`server/`)

**Purpose:** MCP server setup and tool registration

**`server/registry.py`** (200 lines)
```python
# Functions: register_all_tools
# Imports all tool modules and registers them
```

**`server/runner.py`** (100 lines)
```python
# Functions: run_mcp_server
# Main server entry point
```

### Import Strategy

**Three-tier import pattern:**

1. **External imports** - Only from `ast_grep_mcp` package
2. **Internal imports** - Absolute imports within package
3. **Main.py re-exports** - Backward compatibility layer

#### Example Import Patterns

**In feature modules:**
```python
# features/search/service.py
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.core.cache import get_query_cache
from ast_grep_mcp.models.config import AstGrepConfig
```

**In tool modules:**
```python
# features/search/tools.py
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from ast_grep_mcp.features.search.service import find_code_impl

mcp = FastMCP("ast-grep")

@mcp.tool()
def find_code(...):
    return find_code_impl(...)
```

**In main.py (backward compatibility):**
```python
# main.py - Entry point with re-exports
from ast_grep_mcp.server.runner import run_mcp_server
from ast_grep_mcp.core.config import parse_args_and_get_config
from ast_grep_mcp.core.sentry import init_sentry

# Re-export everything for backward compatibility
from ast_grep_mcp.features.search.service import *
from ast_grep_mcp.features.rewrite.service import *
from ast_grep_mcp.features.deduplication.detector import *
# ... all other exports

if __name__ == "__main__":
    run_mcp_server()
```

**In tests (initially unchanged):**
```python
# tests/unit/test_unit.py
# Keep existing imports
from main import (
    format_matches_as_text,
    run_ast_grep,
    # ...
)
```

### Tool Registration Architecture

**Current problem:** 4,354 lines in one `register_mcp_tools()` function

**Solution:** Distributed registration with central coordinator

#### Pattern 1: Per-Feature Tool Modules

```python
# features/search/tools.py
from mcp.server.fastmcp import FastMCP

def register_search_tools(mcp: FastMCP) -> None:
    """Register all search-related tools"""

    @mcp.tool()
    def dump_syntax_tree(...):
        from .service import dump_syntax_tree_impl
        return dump_syntax_tree_impl(...)

    @mcp.tool()
    def find_code(...):
        from .service import find_code_impl
        return find_code_impl(...)

    # ... more tools
```

#### Pattern 2: Central Registry

```python
# server/registry.py
from mcp.server.fastmcp import FastMCP
from ast_grep_mcp.features.search.tools import register_search_tools
from ast_grep_mcp.features.rewrite.tools import register_rewrite_tools
from ast_grep_mcp.features.deduplication.tools import register_deduplication_tools
from ast_grep_mcp.features.complexity.tools import register_complexity_tools
from ast_grep_mcp.features.quality.tools import register_quality_tools
from ast_grep_mcp.features.schema.tools import register_schema_tools

def register_all_tools(mcp: FastMCP) -> None:
    """Register all MCP tools from all features"""
    register_search_tools(mcp)
    register_rewrite_tools(mcp)
    register_deduplication_tools(mcp)
    register_complexity_tools(mcp)
    register_quality_tools(mcp)
    register_schema_tools(mcp)
```

#### Pattern 3: Server Runner

```python
# server/runner.py
from mcp.server.fastmcp import FastMCP
from ast_grep_mcp.core.config import parse_args_and_get_config
from ast_grep_mcp.core.sentry import init_sentry
from ast_grep_mcp.server.registry import register_all_tools

mcp = FastMCP("ast-grep")

def run_mcp_server() -> None:
    """Run the MCP server"""
    parse_args_and_get_config()  # sets CONFIG_PATH
    init_sentry()  # Initialize error tracking
    register_all_tools(mcp)  # Register all tools
    mcp.run(transport="stdio")
```

### Dependency Management

**Dependency Rules:**

1. **Layers can only depend downward:**
   - `features/` → `utils/`, `models/`, `core/`
   - `utils/` → `models/`
   - `models/` → (no dependencies except stdlib/pydantic)
   - `core/` → `models/`, `utils/` (minimal)

2. **No circular dependencies:**
   - Use dependency injection for complex cases
   - Use lazy imports if necessary (rare)

3. **Feature isolation:**
   - Features cannot import from other features
   - Shared logic goes in `utils/` or `core/`

4. **Explicit over implicit:**
   - No star imports between internal modules
   - Explicit imports in `__init__.py` for public APIs

**Dependency Graph:**

```
┌─────────────────────────────────────────────────────────┐
│                       Features Layer                     │
│  ┌────────┐ ┌─────────┐ ┌──────────────┐ ┌──────────┐ │
│  │ search │ │ rewrite │ │ deduplication│ │ quality  │ │
│  └────────┘ └─────────┘ └──────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                        Utils Layer                       │
│     ┌───────────┐ ┌────────────┐ ┌──────────────┐     │
│     │ templates │ │ formatters │ │  validation  │     │
│     └───────────┘ └────────────┘ └──────────────┘     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                       Models Layer                       │
│     ┌────────┐ ┌──────────────┐ ┌──────────────┐      │
│     │ config │ │ deduplication│ │  complexity  │      │
│     └────────┘ └──────────────┘ └──────────────┘      │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                        Core Layer                        │
│  ┌────────┐ ┌───────┐ ┌─────────┐ ┌──────────┐        │
│  │ config │ │ cache │ │ logging │ │ executor │        │
│  └────────┘ └───────┘ └─────────┘ └──────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Cross-Cutting Concerns

**Logging:**
- All modules use `get_logger(__name__)`
- Configured once in `core/logging.py`
- Structured logging via structlog

**Caching:**
- Only search tools use cache
- Cache instance from `core/cache.py`
- Thread-safe singleton pattern

**Sentry:**
- Initialized once in `core/sentry.py`
- All features use `sentry_sdk.capture_exception()`
- Optional (no-op if not configured)

**Configuration:**
- Global `CONFIG_PATH` set by `parse_args_and_get_config()`
- All features access via `from ast_grep_mcp.core.config import CONFIG_PATH`
- Thread-safe read-only access

## File-by-File Breakdown

### Phase 1: Core Infrastructure (Week 1)

**Priority: HIGH - Foundation for everything else**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `core/exceptions.py` | 80 | All exception classes | None |
| `core/logging.py` | 100 | Logging setup | structlog |
| `core/sentry.py` | 100 | Sentry initialization | sentry_sdk, logging |
| `core/config.py` | 150 | Config classes, globals | pydantic, exceptions |
| `core/cache.py` | 300 | QueryCache class | threading, logging |
| `core/executor.py` | 500 | AST-grep execution | subprocess, cache, logging |

**Testing:** Run unit tests for each module as extracted

### Phase 2: Models (Week 1)

**Priority: HIGH - No business logic, easy to extract**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `models/config.py` | 100 | AstGrepConfig, CustomLanguageConfig | pydantic |
| `models/deduplication.py` | 400 | All deduplication data classes | dataclasses, pydantic |
| `models/complexity.py` | 100 | Complexity metrics classes | dataclasses |
| `models/standards.py` | 200 | Standards enforcement classes | pydantic, exceptions |

**Testing:** Type checking only (no logic to test)

### Phase 3: Utilities (Week 2)

**Priority: MEDIUM - Shared utilities**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `utils/templates.py` | 400 | Code generation templates | None |
| `utils/formatters.py` | 300 | Code formatters | subprocess |
| `utils/text.py` | 200 | Text processing | difflib |
| `utils/validation.py` | 150 | Validation utilities | yaml, exceptions |

**Testing:** Run unit tests for formatters, text utilities

### Phase 4: Search Feature (Week 2)

**Priority: HIGH - Core functionality**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `features/search/service.py` | 600 | Search business logic | core, models, utils |
| `features/search/syntax.py` | 200 | Syntax tree operations | core, models |
| `features/search/tools.py` | 400 | MCP tool definitions | FastMCP, service |

**Testing:** Run all search-related tests

### Phase 5: Rewrite Feature (Week 2)

**Priority: HIGH - Important functionality**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `features/rewrite/backup.py` | 300 | Backup management | shutil, pathlib |
| `features/rewrite/service.py` | 500 | Rewrite business logic | core, backup |
| `features/rewrite/tools.py` | 300 | MCP tool definitions | FastMCP, service |

**Testing:** Run all rewrite-related tests

### Phase 6: Schema.org Feature (Week 2)

**Priority: MEDIUM - Independent feature**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `features/schema/client.py` | 600 | SchemaOrgClient class | httpx, logging |
| `features/schema/tools.py` | 500 | MCP tool definitions (8 tools) | FastMCP, client |

**Testing:** Run all Schema.org tests

### Phase 7: Deduplication Feature (Week 3-4)

**Priority: MEDIUM - Largest feature, most complex**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `features/deduplication/detector.py` | 1,500 | Duplicate detection | core, models, utils |
| `features/deduplication/analyzer.py` | 1,200 | Pattern analysis | models, utils |
| `features/deduplication/ranker.py` | 800 | Candidate ranking | models, coverage |
| `features/deduplication/generator.py` | 1,800 | Code generation | models, utils |
| `features/deduplication/applicator.py` | 1,200 | Apply refactoring | core, generator |
| `features/deduplication/coverage.py` | 1,000 | Test coverage | core, models |
| `features/deduplication/impact.py` | 600 | Impact analysis | models, coverage |
| `features/deduplication/recommendations.py` | 800 | Recommendation engine | models, ranker |
| `features/deduplication/reporting.py` | 1,000 | Enhanced reporting | models, utils |
| `features/deduplication/benchmark.py` | 400 | Performance benchmarking | core, detector |
| `features/deduplication/tools.py` | 600 | MCP tool definitions (4 tools) | FastMCP, services |

**Testing:** Run all 1,000+ deduplication tests

### Phase 8: Complexity Feature (Week 4)

**Priority: MEDIUM - Independent feature**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `features/complexity/metrics.py` | 300 | Metric calculation | models |
| `features/complexity/storage.py` | 200 | SQLite storage | sqlite3, models |
| `features/complexity/analyzer.py` | 600 | Complexity analysis | core, metrics, storage |
| `features/complexity/tools.py` | 200 | MCP tool definitions (2 tools) | FastMCP, analyzer |

**Testing:** Run all complexity tests

### Phase 9: Quality Feature (Week 4)

**Priority: MEDIUM - Independent feature**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `features/quality/smells.py` | 500 | Code smell detection | core, models |
| `features/quality/rules.py` | 400 | Linting rules | models, storage |
| `features/quality/validator.py` | 300 | Rule validation | models, utils |
| `features/quality/enforcer.py` | 500 | Standards enforcement | core, rules |
| `features/quality/tools.py` | 300 | MCP tool definitions (3 tools) | FastMCP, services |

**Testing:** Run all quality tests

### Phase 10: Server Layer (Week 5)

**Priority: HIGH - Integration**

| File | Lines | Content | Dependencies |
|------|-------|---------|--------------|
| `server/registry.py` | 200 | Tool registration | all feature tools |
| `server/runner.py` | 100 | Server entry point | FastMCP, core, registry |
| `main.py` (refactored) | 100 | Entry point + re-exports | server, all features |

**Testing:** Run full integration test suite

## Migration Plan

### Phase 0: Preparation (Day 1)

1. **Create feature branch:** `git checkout -b refactor/modular-architecture`
2. **Backup current state:** Copy `main.py` to `main.py.backup`
3. **Create directory structure:** Create all folders
4. **Add `__init__.py` files:** Empty files for now
5. **Update `.gitignore`:** Add `*.pyc`, `__pycache__/`, `.mypy_cache/`

### Phase 1-9: Feature Extraction (Weeks 1-4)

**For each phase:**

1. **Create files:** Create module files for that phase
2. **Extract code:** Copy relevant code from `main.py`
3. **Update imports:** Change imports to absolute package imports
4. **Add exports:** Update `__init__.py` files with exports
5. **Run tests:** Verify tests still pass
6. **Commit:** Commit changes with descriptive message

**Example for Phase 1 (Core Infrastructure):**

```bash
# Day 1: Exceptions
git checkout -b refactor/phase1-core
mkdir -p src/ast_grep_mcp/core
touch src/ast_grep_mcp/core/__init__.py

# Extract exceptions (lines 330-390)
# Copy to core/exceptions.py
# Test: pytest tests/unit/ -k "exception"

git add src/ast_grep_mcp/core/exceptions.py
git commit -m "refactor: extract exception classes to core/exceptions.py"

# Day 2: Logging
# Extract logging (lines 226-262)
# Copy to core/logging.py
# Test: pytest tests/unit/ -k "logging"

git add src/ast_grep_mcp/core/logging.py
git commit -m "refactor: extract logging setup to core/logging.py"

# Continue for each module...
```

### Phase 10: Integration (Week 5)

**Day 1-2: Server Layer**
```bash
# Create server registry
mkdir -p src/ast_grep_mcp/server
# Create server/registry.py
# Create server/runner.py
# Test: pytest tests/integration/
```

**Day 3-4: Main.py Refactor**
```bash
# Refactor main.py to import from package
# Keep re-exports for backward compatibility
# Test: pytest tests/ (all tests)
# Test: Run MCP server manually
```

**Day 5: Documentation Update**
```bash
# Update CLAUDE.md with new structure
# Update README.md with import examples
# Create MODULE-DEPENDENCIES.md diagram
# Update CONFIGURATION.md with new paths
```

### Phase 11: Test Migration (Week 6)

**Optional but recommended:** Update tests to import from package

```bash
# Update test imports from:
from main import function_name

# To:
from ast_grep_mcp.features.search.service import function_name

# Benefits:
# - Explicit dependencies
# - Better IDE support
# - Clearer test organization
```

### Phase 12: Cleanup (Week 6)

1. **Remove main.py re-exports:** After tests updated
2. **Remove main.py.backup:** Keep in git history only
3. **Update CI/CD:** Ensure all pipelines pass
4. **Update documentation:** Final documentation review
5. **Merge to main:** Create PR, review, merge

## Testing Strategy

### During Migration

**Unit Tests:**
- Run after each module extraction
- Mock dependencies using existing patterns
- Should pass without changes

**Integration Tests:**
- Run after feature completion
- Test end-to-end workflows
- Should pass without changes

**Manual Testing:**
- Test MCP server startup
- Test tool invocations
- Verify tool responses match

### Test Migration Options

**Option 1: Keep current imports (recommended for migration)**
```python
# tests/unit/test_unit.py
from main import format_matches_as_text, run_ast_grep
```
**Pros:** Zero test changes during migration
**Cons:** Obscures dependencies

**Option 2: Update to package imports (recommended after migration)**
```python
# tests/unit/test_search.py
from ast_grep_mcp.features.search.service import find_code_impl
from ast_grep_mcp.core.executor import run_ast_grep
```
**Pros:** Explicit dependencies, better organization
**Cons:** Requires updating all test files

**Option 3: Hybrid approach**
- Keep integration tests with `from main import`
- Update unit tests to package imports
- Gradual migration

### Test Structure After Migration

```
tests/
├── unit/
│   ├── core/
│   │   ├── test_cache.py
│   │   ├── test_config.py
│   │   └── test_executor.py
│   ├── features/
│   │   ├── test_search_service.py
│   │   ├── test_rewrite_service.py
│   │   ├── test_deduplication_detector.py
│   │   └── test_complexity_analyzer.py
│   └── utils/
│       ├── test_formatters.py
│       └── test_templates.py
├── integration/
│   ├── test_end_to_end.py
│   ├── test_search_integration.py
│   └── test_deduplication_integration.py
└── conftest.py
```

## Risk Mitigation

### Risk 1: Breaking Changes to MCP Tools

**Mitigation:**
- Tool signatures unchanged
- All tools re-exported from `main.py` initially
- Integration tests verify tool behavior
- Manual testing before merge

**Rollback:** Revert feature branch, restore from backup

### Risk 2: Import Errors

**Mitigation:**
- Absolute imports only
- Update `__init__.py` files with exports
- Run type checking after each phase (`mypy`)
- Run tests after each module extraction

**Rollback:** Fix imports, don't move to next phase until passing

### Risk 3: Circular Dependencies

**Mitigation:**
- Strict layer dependency rules
- No feature-to-feature imports
- Shared logic in `utils/` or `core/`
- Dependency graph validation

**Detection:** `pytest --collect-only` will fail on circular imports

### Risk 4: Test Failures

**Mitigation:**
- Run tests after each extraction
- Keep test imports unchanged initially
- Mock fixtures still work (MockFastMCP pattern)
- Clear cache in `setup_method()`

**Rollback:** Fix broken module before proceeding

### Risk 5: Performance Regression

**Mitigation:**
- No algorithmic changes, only refactoring
- Import overhead negligible (<1ms per import)
- Cache still works exactly the same
- Run benchmarks before and after

**Verification:** `pytest tests/integration/test_benchmark.py`

### Risk 6: IDE Performance

**Mitigation:**
- Smaller files improve IDE responsiveness
- Better indexing with modular structure
- Faster go-to-definition
- Better autocomplete

**Expected:** Improved IDE experience

### Risk 7: Merge Conflicts

**Mitigation:**
- Coordinate with team during migration
- Feature freeze during migration (1-2 weeks)
- Communicate refactor plan
- Quick merge after testing

**Resolution:** Migrate changes into new structure

## Benefits Analysis

### Before Refactor

**Metrics:**
- **File size:** 19,477 lines
- **Find time:** 2-5 minutes to find specific function
- **IDE performance:** Slow on 20K line file
- **Merge conflicts:** High probability with multiple developers
- **Test time:** Hard to test specific components
- **Onboarding:** Overwhelming for new developers

### After Refactor

**Metrics:**
- **Max file size:** ~1,800 lines (generator.py)
- **Average file size:** ~400 lines
- **Total files:** ~35 files vs 1 file
- **Find time:** <30 seconds (navigate to feature folder)
- **IDE performance:** Fast, responsive
- **Merge conflicts:** Low (developers work in different features)
- **Test time:** Run specific test modules
- **Onboarding:** Clear structure, easy to understand

### Quantifiable Benefits

**Developer Productivity:**
- **Code navigation:** 5-10x faster (minutes → seconds)
- **Feature addition:** 2-3x faster (clear where to add code)
- **Bug fixes:** 2x faster (isolated features)
- **Code review:** 2x faster (smaller, focused files)

**Code Quality:**
- **Test coverage:** Easier to test isolated components
- **Type safety:** Better type inference with smaller files
- **Documentation:** Clear module responsibilities
- **Maintainability:** High cohesion, low coupling

**Team Collaboration:**
- **Parallel development:** Multiple features without conflicts
- **Onboarding:** New developers productive faster
- **Code ownership:** Clear feature ownership
- **Refactoring:** Safe, isolated changes

## Success Criteria

### Phase Completion Criteria

**Each phase must meet:**
1. All unit tests pass
2. All integration tests pass
3. Type checking passes (`mypy`)
4. Linting passes (`ruff check`)
5. Manual MCP server test passes
6. Performance benchmarks pass

### Final Success Criteria

**Migration complete when:**
1. **All 1,561 tests pass:** No test failures
2. **All 27 tools work:** Manual testing verified
3. **No performance regression:** Benchmarks within 5%
4. **Type checking passes:** Full mypy compliance
5. **Documentation updated:** All docs reflect new structure
6. **CI/CD passes:** All pipelines green
7. **Team approval:** Code review approved
8. **Production deployment:** Successfully deployed

## Timeline Estimate

### Aggressive Timeline (1 developer, full-time)

**Week 1:** Core + Models + Start Utilities (Phase 0-2)
**Week 2:** Finish Utilities + Search + Rewrite + Schema (Phase 3-6)
**Week 3:** Deduplication Part 1 (Phase 7, first half)
**Week 4:** Deduplication Part 2 + Complexity + Quality (Phase 7-9)
**Week 5:** Server Integration + Testing (Phase 10)
**Week 6:** Test Migration + Cleanup + Documentation (Phase 11-12)

**Total: 6 weeks**

### Conservative Timeline (1 developer, 50% time)

**Week 1-2:** Core + Models (Phase 0-2)
**Week 3-4:** Utilities + Search + Rewrite (Phase 3-5)
**Week 5-6:** Schema + Deduplication Part 1 (Phase 6-7)
**Week 7-8:** Deduplication Part 2 (Phase 7 continued)
**Week 9-10:** Complexity + Quality (Phase 8-9)
**Week 11-12:** Server + Integration + Testing (Phase 10-11)
**Week 13-14:** Cleanup + Documentation (Phase 12)

**Total: 14 weeks (3.5 months)**

### Team Timeline (2 developers, full-time, parallel)

**Week 1:** Core + Models (both developers)
**Week 2:** Dev 1: Search + Rewrite | Dev 2: Schema + Utilities
**Week 3-4:** Dev 1: Deduplication Part 1 | Dev 2: Complexity + Quality
**Week 5:** Dev 1: Deduplication Part 2 | Dev 2: Server Integration
**Week 6:** Both: Testing + Cleanup + Documentation

**Total: 6 weeks**

## Next Steps

### Immediate Actions

1. **Review architecture design:** Team review, get feedback
2. **Approve migration plan:** Management approval for timeline
3. **Create feature branch:** `git checkout -b refactor/modular-architecture`
4. **Create directory structure:** Set up folders
5. **Start Phase 1:** Extract core infrastructure

### Week 1 Deliverables

- [ ] Core layer complete (`core/`)
- [ ] Models layer complete (`models/`)
- [ ] All tests passing
- [ ] Documentation updated

### Questions for Review

1. **Is the layered architecture appropriate?** (features → utils → models → core)
2. **Should we use different tool registration pattern?** (centralized vs distributed)
3. **What's the priority for feature extraction?** (search first vs schema first)
4. **Should we update tests during or after migration?** (hybrid approach?)
5. **What's the merge strategy?** (single PR vs incremental merges)
6. **Who will review the changes?** (code review process)
7. **When can we schedule the migration?** (feature freeze coordination)

## Appendix

### A. Module Size Breakdown

| Module | Files | Total Lines | Avg Lines/File |
|--------|-------|-------------|----------------|
| core | 6 | 1,230 | 205 |
| models | 4 | 800 | 200 |
| utils | 4 | 1,050 | 262 |
| features/search | 3 | 1,200 | 400 |
| features/rewrite | 3 | 1,100 | 367 |
| features/schema | 2 | 1,100 | 550 |
| features/deduplication | 11 | 11,000 | 1,000 |
| features/complexity | 4 | 1,300 | 325 |
| features/quality | 5 | 2,000 | 400 |
| server | 2 | 300 | 150 |
| **Total** | **44** | **20,080** | **456** |

### B. Import Dependency Matrix

```
              core  models  utils  features  server
core            -      ✓      ✓       -        -
models          -      -      -       -        -
utils           ✓      ✓      -       -        -
features        ✓      ✓      ✓       -        -
server          ✓      ✓      ✓       ✓        -
```

### C. Tool Distribution by Feature

| Feature | Tool Count | Percentage |
|---------|------------|------------|
| Schema.org | 8 | 30% |
| Search | 6 | 22% |
| Deduplication | 4 | 15% |
| Rewrite | 3 | 11% |
| Quality | 3 | 11% |
| Complexity | 2 | 7% |
| Sentry Test | 1 | 4% |
| **Total** | **27** | **100%** |

### D. Function Count by Module

**Current:** 200+ functions in one file

**After refactor:**
- Average 10-15 functions per file
- Max 50 functions in largest file (deduplication/generator.py)
- Clear function organization by responsibility

### E. Class Distribution

| Feature | Class Count |
|---------|-------------|
| Standards | 9 classes |
| Deduplication | 8 classes |
| Core | 4 classes |
| Exceptions | 6 classes |
| Complexity | 3 classes |
| Schema | 1 class |
| **Total** | **31 classes** |

---

**Document Version:** 1.0
**Last Updated:** 2025-11-24
**Status:** Ready for Review
**Next Review:** After team feedback
