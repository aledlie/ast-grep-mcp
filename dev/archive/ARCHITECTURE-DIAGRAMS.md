# Architecture Diagrams

**Date:** 2025-11-24

## Current State vs. Target State

### Current Architecture (Single File)

```
┌────────────────────────────────────────────────────────────────┐
│                          main.py                               │
│                       (19,477 lines)                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Imports (30 lines)                                           │
│  ├── External: mcp, pydantic, structlog, sentry_sdk          │
│  └── Stdlib: subprocess, threading, pathlib, etc.            │
│                                                                │
│  Global Configuration (8 lines)                               │
│  ├── CONFIG_PATH: Optional[str] = None                       │
│  ├── CACHE_ENABLED: bool = True                              │
│  ├── CACHE_SIZE: int = 100                                   │
│  └── CACHE_TTL: int = 300                                    │
│                                                                │
│  Templates (263 lines)                                        │
│  ├── PYTHON_CLASS_TEMPLATE                                   │
│  ├── JAVA_CLASS_TEMPLATE                                     │
│  └── format_*_class functions                                │
│                                                                │
│  Infrastructure (600 lines)                                   │
│  ├── Logging setup (configure_logging, get_logger)           │
│  ├── Sentry initialization (init_sentry)                     │
│  ├── Exception classes (6 classes)                           │
│  ├── Cache management (QueryCache class)                     │
│  └── Config classes (AstGrepConfig, etc.)                    │
│                                                                │
│  AST-grep Execution (507 lines)                              │
│  ├── run_ast_grep                                            │
│  ├── run_command                                             │
│  └── get_supported_languages                                 │
│                                                                │
│  Schema.org Client (14 lines)                                │
│  └── SchemaOrgClient class                                   │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │   register_mcp_tools() - 4,354 LINES!                   │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │   All 27 MCP tools defined inline:                      │ │
│  │   • dump_syntax_tree                                    │ │
│  │   • test_match_code_rule                                │ │
│  │   • find_code (with caching)                            │ │
│  │   • find_code_by_rule (with caching)                    │ │
│  │   • scan_project (streaming)                            │ │
│  │   • rewrite_code                                        │ │
│  │   • list_backups                                        │ │
│  │   • rollback_rewrite                                    │ │
│  │   • list_schema_org_types                               │ │
│  │   • search_schema_org                                   │ │
│  │   • get_schema_org_type                                 │ │
│  │   • get_schema_org_property                             │ │
│  │   • list_schema_org_children                            │ │
│  │   • get_schema_org_domain_range                         │ │
│  │   • get_schema_org_parent_chain                         │ │
│  │   • get_schema_org_subtree                              │ │
│  │   • find_duplication                                    │ │
│  │   • analyze_deduplication_candidates                    │ │
│  │   • apply_deduplication                                 │ │
│  │   • benchmark_deduplication                             │ │
│  │   • analyze_complexity                                  │ │
│  │   • detect_code_smells                                  │ │
│  │   • validate_linting_rules                             │ │
│  │   • enforce_standards                                   │ │
│  │   • test_sentry_integration                            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │   Deduplication Feature - 11,000 LINES!                 │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │   • Detector (find_duplication_impl)                    │ │
│  │   • Analyzer (classify_variation, build_diff_tree)      │ │
│  │   • Ranker (calculate_deduplication_score)              │ │
│  │   • Generator (generate_refactoring_suggestions)        │ │
│  │   • Applicator (apply_deduplication_impl)               │ │
│  │   • Coverage (has_test_coverage)                        │ │
│  │   • Impact (analyze_deduplication_impact)               │ │
│  │   • Recommendations (generate_recommendation)           │ │
│  │   • Reporting (format_diff_with_colors)                 │ │
│  │   • Benchmark (benchmark_deduplication_impl)            │ │
│  │   + 200+ helper functions                               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
│  Complexity Analysis (900 lines)                             │
│  ├── analyze_complexity_impl                                 │
│  ├── calculate_cyclomatic_complexity                         │
│  ├── calculate_cognitive_complexity                          │
│  └── ComplexityStorage class                                 │
│                                                                │
│  Code Quality & Standards (1,607 lines)                      │
│  ├── Phase 1: detect_code_smells_impl (970 lines)           │
│  ├── Phase 2: validate_linting_rules_impl (637 lines)       │
│  └── enforce_standards_impl                                  │
│                                                                │
│  Server Runner (77 lines)                                    │
│  ├── run_mcp_server                                          │
│  └── if __name__ == "__main__"                               │
│                                                                │
└────────────────────────────────────────────────────────────────┘

Problems:
❌ 19,477 lines - too large for any developer to understand
❌ 4,354 line function - impossible to maintain
❌ No clear boundaries - everything mixed together
❌ Hard to test - difficult to isolate components
❌ Slow IDE - large file bogs down editor
❌ Merge conflicts - high probability with multiple developers
❌ Poor code discovery - takes minutes to find specific code
```

### Target Architecture (Modular Package)

```
┌─────────────────────────────────────────────────────────────────┐
│                       Application Layer                         │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ main.py (100 lines)                                       │ │
│  │ • Entry point: run_mcp_server()                           │ │
│  │ • Backward compatibility: re-exports from package         │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Server Layer                             │
│  ┌─────────────────────┬─────────────────────────────────────┐ │
│  │ server/registry.py  │ server/runner.py                    │ │
│  │ (200 lines)         │ (100 lines)                         │ │
│  │                     │                                     │ │
│  │ register_all_tools  │ run_mcp_server()                    │ │
│  │ ├── search (6)      │ ├── parse_args_and_get_config()    │ │
│  │ ├── rewrite (3)     │ ├── init_sentry()                  │ │
│  │ ├── dedup (4)       │ ├── register_all_tools()           │ │
│  │ ├── complex (2)     │ └── mcp.run()                      │ │
│  │ ├── quality (3)     │                                     │ │
│  │ └── schema (8)      │                                     │ │
│  └─────────────────────┴─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Features Layer                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ features/search/ (3 files, 1,200 lines)                  │  │
│  │ ├── service.py: Business logic                           │  │
│  │ ├── syntax.py: Syntax tree operations                    │  │
│  │ └── tools.py: MCP tool registration                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ features/rewrite/ (3 files, 1,100 lines)                 │  │
│  │ ├── backup.py: Backup management                         │  │
│  │ ├── service.py: Rewrite business logic                   │  │
│  │ └── tools.py: MCP tool registration                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ features/schema/ (2 files, 1,100 lines)                  │  │
│  │ ├── client.py: SchemaOrgClient class                     │  │
│  │ └── tools.py: MCP tool registration (8 tools)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ features/deduplication/ (11 files, 11,000 lines)         │  │
│  │ ├── detector.py: Find duplicates (1,500 lines)           │  │
│  │ ├── analyzer.py: Pattern analysis (1,200 lines)          │  │
│  │ ├── ranker.py: Score candidates (800 lines)              │  │
│  │ ├── generator.py: Code generation (1,800 lines)          │  │
│  │ ├── applicator.py: Apply refactoring (1,200 lines)       │  │
│  │ ├── coverage.py: Test coverage (1,000 lines)             │  │
│  │ ├── impact.py: Impact analysis (600 lines)               │  │
│  │ ├── recommendations.py: Suggestions (800 lines)          │  │
│  │ ├── reporting.py: Enhanced reports (1,000 lines)         │  │
│  │ ├── benchmark.py: Performance tests (400 lines)          │  │
│  │ └── tools.py: MCP tool registration (4 tools)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ features/complexity/ (4 files, 1,300 lines)              │  │
│  │ ├── analyzer.py: Complexity analysis                     │  │
│  │ ├── metrics.py: Metric calculation                       │  │
│  │ ├── storage.py: SQLite storage                           │  │
│  │ └── tools.py: MCP tool registration (2 tools)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ features/quality/ (5 files, 2,000 lines)                 │  │
│  │ ├── smells.py: Code smell detection                      │  │
│  │ ├── rules.py: Linting rules                              │  │
│  │ ├── validator.py: Rule validation                        │  │
│  │ ├── enforcer.py: Standards enforcement                   │  │
│  │ └── tools.py: MCP tool registration (3 tools)            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Utils Layer                             │
│  ┌───────────────┬───────────────┬──────────────┬────────────┐ │
│  │ templates.py  │ formatters.py │   text.py    │validation  │ │
│  │ (400 lines)   │ (300 lines)   │ (200 lines)  │(150 lines) │ │
│  │               │               │              │            │ │
│  │ Code gen      │ Output format │ Text utils   │ YAML/config│ │
│  │ templates     │ Match format  │ Normalize    │ validation │ │
│  └───────────────┴───────────────┴──────────────┴────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Models Layer                             │
│  ┌───────────────┬───────────────┬──────────────┬────────────┐ │
│  │  config.py    │deduplication  │ complexity   │ standards  │ │
│  │ (100 lines)   │  (400 lines)  │ (100 lines)  │(200 lines) │ │
│  │               │               │              │            │ │
│  │ AstGrepConfig │ 13 dataclasses│ Metrics      │ Rules      │ │
│  │ LanguageConfig│ AlignmentRes  │ Thresholds   │ Violations │ │
│  └───────────────┴───────────────┴──────────────┴────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Core Layer                              │
│  ┌──────────┬────────┬─────────┬─────────┬────────┬─────────┐ │
│  │ config   │ cache  │ logging │ sentry  │ except │executor │ │
│  │ (150 ln) │(300 ln)│ (100 ln)│ (100 ln)│ (80 ln)│(500 ln) │ │
│  │          │        │         │         │        │         │ │
│  │ Parse    │ Query  │Structlog│ Init    │ 6      │ run_    │ │
│  │ args     │ cache  │ setup   │ SDK     │ classes│ ast_grep│ │
│  └──────────┴────────┴─────────┴─────────┴────────┴─────────┘ │
└─────────────────────────────────────────────────────────────────┘

Benefits:
✅ 44 files, ~450 lines average - manageable size
✅ Clear module boundaries - easy to understand
✅ Layered architecture - proper separation of concerns
✅ Easy to test - isolated components
✅ Fast IDE - small files load quickly
✅ Low merge conflicts - different features in different files
✅ Excellent code discovery - navigate to feature in seconds
✅ Easy onboarding - start with one feature at a time
```

## Tool Flow Diagram

### Before: Monolithic Tool Registration

```
User Request
     ↓
MCP Protocol
     ↓
┌─────────────────────────────────────────────┐
│     register_mcp_tools() - 4,354 lines      │
│                                             │
│  @mcp.tool()                                │
│  def find_code(...):                        │
│      # 173 lines of logic inline           │
│      logger = get_logger()                  │
│      cache = get_query_cache()              │
│      result = run_ast_grep(...)             │
│      format_output(...)                     │
│      return result                          │
│                                             │
│  @mcp.tool()                                │
│  def apply_deduplication(...):              │
│      # 211 lines of logic inline           │
│      validate(...)                          │
│      backup(...)                            │
│      generate(...)                          │
│      apply(...)                             │
│      return result                          │
│                                             │
│  ... 25 more tools with logic inline       │
│                                             │
└─────────────────────────────────────────────┘
     ↓
Response
```

### After: Modular Tool Registration

```
User Request
     ↓
MCP Protocol
     ↓
┌─────────────────────────────────────────────┐
│     server/registry.py                      │
│     register_all_tools() - 200 lines        │
│                                             │
│  register_search_tools(mcp)                 │
│  register_rewrite_tools(mcp)                │
│  register_deduplication_tools(mcp)          │
│  register_complexity_tools(mcp)             │
│  register_quality_tools(mcp)                │
│  register_schema_tools(mcp)                 │
│                                             │
└─────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────┐
│     features/search/tools.py                │
│                                             │
│  @mcp.tool()                                │
│  def find_code(...):                        │
│      return find_code_impl(...)  ← 5 lines  │
│                                             │
└─────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────┐
│     features/search/service.py              │
│                                             │
│  def find_code_impl(...):                   │
│      logger = get_logger()                  │
│      cache = get_query_cache()              │
│      result = run_ast_grep(...)             │
│      format_output(...)                     │
│      return result                          │
│                                             │
└─────────────────────────────────────────────┘
     ↓
Response
```

**Benefits:**
- Tool definition: 5 lines (vs 173 inline)
- Business logic: Separate, testable
- Easy to add new tools: Just add to tools.py
- Clear separation: MCP vs business logic

## Data Flow Diagram

### Search Feature Data Flow

```
┌──────────────┐
│ User Request │
│ "Find code"  │
└──────┬───────┘
       ↓
┌──────────────────────────────────┐
│ features/search/tools.py         │
│ @mcp.tool()                      │
│ def find_code(pattern, path...)  │
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│ features/search/service.py       │
│ def find_code_impl(...)          │
│   ├─→ Check cache                │
│   ├─→ Run AST-grep               │
│   ├─→ Format results             │
│   └─→ Update cache               │
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│ core/cache.py                    │
│ QueryCache.get(key)              │
│ QueryCache.set(key, value)       │
└──────────────────────────────────┘
       ↓
┌──────────────────────────────────┐
│ core/executor.py                 │
│ run_ast_grep(pattern, path)      │
│   ├─→ Build command              │
│   ├─→ Execute subprocess         │
│   └─→ Parse output               │
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│ utils/formatters.py              │
│ format_matches_as_text(matches)  │
│   ├─→ Group by file              │
│   └─→ Format for LLM             │
└──────┬───────────────────────────┘
       ↓
┌──────────────┐
│   Response   │
│ (formatted)  │
└──────────────┘
```

### Deduplication Feature Data Flow

```
┌──────────────────────┐
│ User Request         │
│ "Apply dedup"        │
└──────┬───────────────┘
       ↓
┌────────────────────────────────────────┐
│ features/deduplication/tools.py        │
│ @mcp.tool()                            │
│ def apply_deduplication(...)           │
└──────┬─────────────────────────────────┘
       ↓
┌────────────────────────────────────────┐
│ features/deduplication/applicator.py   │
│ def apply_deduplication_impl(...)      │
│   ├─→ Validate input                   │
│   ├─→ Create backup                    │
│   ├─→ Generate code                    │
│   ├─→ Apply changes                    │
│   └─→ Validate syntax                  │
└──────┬─────────────────────────────────┘
       │
       ├─→ features/rewrite/backup.py
       │   create_backup(files)
       │
       ├─→ features/deduplication/generator.py
       │   generate_function_code(...)
       │   ├─→ utils/templates.py
       │   └─→ utils/formatters.py
       │
       ├─→ core/executor.py
       │   run_ast_grep(rewrite_rule)
       │
       └─→ features/deduplication/reporting.py
           create_enhanced_response(...)
           └─→ models/deduplication.py
```

## Dependency Graph

### Core Dependencies (Foundation)

```
┌───────────────┐
│  exceptions   │ ← No dependencies
└───────────────┘
        ↑
        │
┌───────────────┐
│    logging    │ ← exceptions only
└───────────────┘
        ↑
        │
┌───────────────┐
│    sentry     │ ← logging
└───────────────┘
        ↑
        │
┌───────────────┐     ┌───────────────┐
│    config     │ ←── │     cache     │
└───────────────┘     └───────────────┘
        ↑                     ↑
        └─────────┬───────────┘
                  │
           ┌──────────────┐
           │   executor   │ ← config, cache, logging, exceptions
           └──────────────┘
```

### Feature Dependencies

```
┌─────────────────────────────────────────────────────┐
│                  Features Layer                     │
│                                                     │
│  ┌─────────┐  ┌─────────┐  ┌──────────────┐      │
│  │ search  │  │ rewrite │  │ schema       │      │
│  │         │  │         │  │              │      │
│  │ No cross-feature dependencies                 │
│  │ Each uses: core, models, utils                │
│  └─────────┘  └─────────┘  └──────────────┘      │
│                                                     │
│  ┌──────────────────────────────────────────┐      │
│  │        deduplication (complex)           │      │
│  │                                          │      │
│  │  detector → analyzer → ranker            │      │
│  │     ↓          ↓          ↓              │      │
│  │  generator ← coverage ← impact           │      │
│  │     ↓                      ↓              │      │
│  │  applicator ← recommendations             │      │
│  │     ↓                      ↓              │      │
│  │  reporting ← benchmark                    │      │
│  │                                          │      │
│  │  Uses: rewrite/backup (shared)           │      │
│  └──────────────────────────────────────────┘      │
│                                                     │
│  ┌──────────┐  ┌──────────┐                       │
│  │complexity│  │ quality  │                       │
│  │          │  │          │                       │
│  │ analyzer │  │ smells   │                       │
│  │ metrics  │  │ rules    │                       │
│  │ storage  │  │ validator│                       │
│  │          │  │ enforcer │                       │
│  └──────────┘  └──────────┘                       │
│                                                     │
│  All use: core, models, utils                     │
└─────────────────────────────────────────────────────┘
```

### Circular Dependency Prevention

**Rule:** Dependencies only flow downward

```
❌ BAD: Feature → Feature
   features/deduplication/ranker.py
   ↓
   from ast_grep_mcp.features.complexity.analyzer import calculate_complexity

❌ BAD: Utils → Features
   utils/formatters.py
   ↓
   from ast_grep_mcp.features.search.service import find_code_impl

✅ GOOD: Feature → Utils
   features/deduplication/ranker.py
   ↓
   from ast_grep_mcp.utils.code_analysis import analyze_structure

✅ GOOD: Feature (internal)
   features/deduplication/ranker.py
   ↓
   from ast_grep_mcp.features.deduplication.coverage import get_coverage
```

## Migration Flow

### Phase-by-Phase Migration

```
Week 1: Foundation
┌────────────────────────────────────────────────┐
│ Day 1: Prep                                    │
│ └─→ Create directory structure                 │
│                                                │
│ Days 2-4: Core Layer                           │
│ ├─→ exceptions.py                              │
│ ├─→ logging.py                                 │
│ ├─→ sentry.py                                  │
│ ├─→ config.py                                  │
│ ├─→ cache.py                                   │
│ └─→ executor.py                                │
│     ✓ Tests pass                               │
│                                                │
│ Days 5-6: Models Layer                         │
│ ├─→ config.py                                  │
│ ├─→ deduplication.py                           │
│ ├─→ complexity.py                              │
│ └─→ standards.py                               │
│     ✓ Type checking passes                     │
│                                                │
│ Days 7-9: Utils Layer                          │
│ ├─→ templates.py                               │
│ ├─→ formatters.py                              │
│ ├─→ text.py                                    │
│ └─→ validation.py                              │
│     ✓ Tests pass                               │
└────────────────────────────────────────────────┘

Week 2: Simple Features
┌────────────────────────────────────────────────┐
│ Days 10-11: Search                             │
│ └─→ service.py, syntax.py, tools.py            │
│     ✓ 6 tools work                             │
│                                                │
│ Days 12-13: Rewrite                            │
│ └─→ backup.py, service.py, tools.py            │
│     ✓ 3 tools work                             │
│                                                │
│ Day 14: Schema                                 │
│ └─→ client.py, tools.py                        │
│     ✓ 8 tools work                             │
└────────────────────────────────────────────────┘

Weeks 3-4: Complex Features
┌────────────────────────────────────────────────┐
│ Days 15-21: Deduplication (7 days)            │
│ ├─→ detector.py, analyzer.py                  │
│ ├─→ ranker.py, generator.py                   │
│ ├─→ applicator.py, coverage.py                │
│ ├─→ impact.py, recommendations.py             │
│ ├─→ reporting.py, benchmark.py                │
│ └─→ tools.py                                   │
│     ✓ 4 tools work, 1000+ tests pass          │
│                                                │
│ Days 22-23: Complexity                         │
│ └─→ analyzer.py, metrics.py, storage.py       │
│     ✓ 2 tools work                             │
│                                                │
│ Days 24-25: Quality                            │
│ └─→ smells.py, rules.py, validator.py         │
│     enforcer.py, tools.py                      │
│     ✓ 3 tools work                             │
└────────────────────────────────────────────────┘

Week 5: Integration
┌────────────────────────────────────────────────┐
│ Days 26-28: Server Integration                │
│ ├─→ server/registry.py                        │
│ ├─→ server/runner.py                          │
│ └─→ main.py (refactored)                      │
│     ✓ All 27 tools work                       │
│     ✓ All 1,561 tests pass                    │
│                                                │
│ Days 29-30: Finalization                      │
│ ├─→ Update documentation                      │
│ ├─→ Final validation                          │
│ └─→ Create PR & merge                         │
└────────────────────────────────────────────────┘
```

## Test Strategy Diagram

### Test Organization

```
tests/
├── unit/                    # Unit tests (mocked)
│   ├── core/
│   │   ├── test_cache.py           ← core/cache.py
│   │   ├── test_config.py          ← core/config.py
│   │   ├── test_executor.py        ← core/executor.py
│   │   └── test_exceptions.py      ← core/exceptions.py
│   │
│   ├── features/
│   │   ├── test_search_service.py  ← features/search/service.py
│   │   ├── test_rewrite_service.py ← features/rewrite/service.py
│   │   ├── test_dedup_detector.py  ← features/dedup/detector.py
│   │   ├── test_dedup_analyzer.py  ← features/dedup/analyzer.py
│   │   ├── test_dedup_ranker.py    ← features/dedup/ranker.py
│   │   └── ... (30+ test files)
│   │
│   └── utils/
│       ├── test_formatters.py      ← utils/formatters.py
│       ├── test_templates.py       ← utils/templates.py
│       └── test_text.py            ← utils/text.py
│
└── integration/             # Integration tests (real ast-grep)
    ├── test_search_integration.py
    ├── test_dedup_integration.py
    ├── test_benchmark.py
    └── test_end_to_end.py
```

### Test Import Pattern

```python
# Before migration (keeps working)
from main import run_ast_grep, find_code_impl

# After migration (tests use new imports)
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.features.search.service import find_code_impl
```

---

**Summary:**
- Current: 1 file, 19,477 lines, unmaintainable
- Target: 44 files, ~450 lines avg, highly maintainable
- Migration: 12 phases, 4-6 weeks, low risk
- Result: 5-10x improvement in developer productivity
