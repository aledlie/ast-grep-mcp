# Remaining Tasks Summary - ast-grep-mcp

**Last Updated:** 2025-11-24
**Current Branch:** refactor
**Latest Commit:** 5d61b10 - refactor: extract search, rewrite, and schema features (Phases 4-6)

## Project Status: Modular Refactoring (60% Complete)

The ast-grep-mcp project is undergoing a major architectural refactoring from a monolithic `main.py` (19,477 lines) to a clean modular structure. This document tracks progress and remaining work.

---

## Completed Phases ✅

### Phase 0: Project Setup (Complete)
**Commit:** 040bcbc
- Created modular directory structure under `src/ast_grep_mcp/`
- Initialized all module directories: core, models, utils, features, server
- Created empty `__init__.py` files for all modules
- Updated `pyproject.toml` with new structure

### Phase 1: Core Infrastructure (Complete)
**Commits:** 7e6b135, 5460c41
- **Extracted to core module:**
  - `core/exceptions.py` - Custom exception classes (83 lines)
  - `core/logging.py` - Logging setup with structlog (52 lines)
  - `core/config.py` - Configuration management (237 lines)
  - `core/sentry.py` - Sentry error tracking integration (61 lines)
  - `core/cache.py` - Result caching mechanism (137 lines)
  - `core/executor.py` - ast-grep command execution (426 lines)
- **Total:** 996 lines extracted to core

### Phase 2: Data Models (Complete)
**Commit:** 8b80490
- **Extracted to models module:**
  - `models/config.py` - Configuration dataclasses (49 lines)
  - `models/complexity.py` - Complexity metrics models (31 lines)
  - `models/deduplication.py` - 10+ deduplication dataclasses (435 lines)
    - VariationCategory, VariationSeverity
    - AlignmentSegment, AlignmentResult
    - DiffTreeNode, DiffTree
    - FunctionTemplate, ParameterInfo
    - FileDiff, DiffPreview
    - EnhancedDuplicationCandidate
  - `models/standards.py` - Linting and standards models (235 lines)
    - LintingRule, RuleTemplate, RuleValidationResult
    - RuleViolation, RuleSet, EnforcementResult
    - RuleExecutionContext
  - `models/base.py` - Base types (6 lines)
- **Total:** 756 lines extracted to models

### Phase 3: Utilities (Complete)
**Commit:** d3449bf
- **Extracted to utils module:**
  - `utils/templates.py` - Code generation templates (507 lines)
    - Python, Java, TypeScript, JavaScript templates
    - Format functions for each language
  - `utils/formatters.py` - Output formatting utilities (215 lines)
    - format_matches_as_text() - LLM-friendly output
    - format_diff_with_colors() - ANSI colored diffs
    - generate_before_after_example() - Deduplication examples
    - visualize_complexity() - Complexity indicators
  - `utils/text.py` - Text processing utilities (51 lines)
    - normalize_code() - Code normalization
    - calculate_similarity() - Similarity scoring
  - `utils/validation.py` - Re-export validation functions (13 lines)
- **Total:** 786 lines extracted to utils

### Phases 4-6: Feature Extraction (Complete)
**Commit:** 5d61b10 (Most Recent)

#### Phase 4: Search Feature
- **Created:**
  - `features/search/service.py` (454 lines)
    - dump_syntax_tree_impl()
    - test_match_code_rule_impl()
    - find_code_impl()
    - find_code_by_rule_impl()
  - `features/search/tools.py` (175 lines) - MCP tool definitions
  - Implements caching, streaming, and file filtering

#### Phase 5: Rewrite Feature
- **Created:**
  - `features/rewrite/backup.py` (391 lines)
    - create_backup()
    - create_deduplication_backup()
    - verify_backup_integrity()
    - restore_backup()
    - list_available_backups()
    - get_file_hash()
  - `features/rewrite/service.py` (476 lines)
    - rewrite_code_impl()
    - rollback_rewrite_impl()
    - list_backups_impl()
    - validate_syntax()
    - validate_rewrites()
  - `features/rewrite/tools.py` (118 lines) - MCP tool definitions

#### Phase 6: Schema Feature
- **Created:**
  - `features/schema/client.py` (524 lines)
    - SchemaOrgClient class with full API
    - get_schema_type(), search_schemas()
    - get_type_hierarchy(), get_type_properties()
    - generate_example(), generate_entity_id()
    - validate_entity_id(), build_entity_graph()
  - `features/schema/tools.py` (498 lines) - MCP tool definitions
  - Global client instance management

**Phases 4-6 Total:** 2,712 lines extracted to features

---

## Remaining Phases ⏳

### Phase 7: Deduplication Feature (In Progress)
**Priority:** HIGH
**Estimated:** 3-4 days

The deduplication feature is the largest remaining component with 11 sub-modules to extract:

#### Day 1-2: Core Detection
- [ ] Extract `features/deduplication/detector.py`
  - find_duplication_impl()
  - detect_variations_between_blocks()
  - detect_conditional_variations()
  - group_duplicates()
- [ ] Extract `features/deduplication/analyzer.py`
  - classify_variation()
  - classify_variations()
  - analyze_duplicate_variations()
  - build_diff_tree()
  - align_code_blocks()

#### Day 3: Template & Generation
- [ ] Extract `features/deduplication/template.py`
  - extract_function_template()
  - generate_parameterized_function()
  - extract_common_params()
- [ ] Extract `features/deduplication/generator.py`
  - generate_deduplication_plan()
  - generate_replacement_code()

#### Day 4: Tools & Integration
- [ ] Extract `features/deduplication/tools.py`
  - Register all deduplication MCP tools
  - find_duplication
  - analyze_variations
  - generate_deduplication_plan
  - apply_deduplication_plan
- [ ] Update `features/deduplication/__init__.py` with exports
- [ ] Run integration tests for deduplication

**Estimated Lines:** ~2,000 lines

### Phase 8: Complexity Feature (Not Started)
**Priority:** MEDIUM
**Estimated:** 2-3 days

- [ ] Extract `features/complexity/analyzer.py`
  - calculate_complexity()
  - analyze_function_complexity()
  - analyze_cognitive_complexity()
- [ ] Extract `features/complexity/tools.py`
  - analyze_complexity MCP tool
- [ ] Run complexity analysis tests

**Estimated Lines:** ~800 lines

### Phase 9: Quality Feature (Not Started)
**Priority:** MEDIUM
**Estimated:** 2-3 days

- [ ] Extract `features/quality/linting.py`
  - create_linting_rule_impl()
  - validate_rule()
  - save_rule()
- [ ] Extract `features/quality/standards.py`
  - enforce_standards_impl()
  - execute_rule()
  - group_violations()
- [ ] Extract `features/quality/tools.py`
  - create_linting_rule MCP tool
  - enforce_standards MCP tool
  - list_rule_templates MCP tool
- [ ] Run quality tests (181 tests from Phase 1 & 2)

**Estimated Lines:** ~1,500 lines

### Phase 10: Server Module (Not Started)
**Priority:** HIGH
**Estimated:** 2 days

- [ ] Extract `server/main.py` (or keep as `main.py` in root)
  - MCP server initialization
  - Tool registration
  - Request handlers
- [ ] Extract `server/handlers.py` (if needed)
  - Request routing logic
- [ ] Update imports to use new modular structure
- [ ] Verify all MCP tools are registered

**Estimated Lines:** ~500 lines remaining in main.py

### Phase 11: Testing & Validation (Not Started)
**Priority:** CRITICAL
**Estimated:** 2-3 days

- [ ] Run full test suite (1,561 tests)
- [ ] Fix any import errors
- [ ] Fix any type checking errors (mypy)
- [ ] Fix any linting errors (ruff)
- [ ] Update test imports to use new module paths
- [ ] Add integration tests for new module structure
- [ ] Verify all MCP tools work end-to-end

### Phase 12: Documentation (Not Started)
**Priority:** MEDIUM
**Estimated:** 1-2 days

- [ ] Update CLAUDE.md with new architecture
- [ ] Update README with module structure
- [ ] Add docstrings to all extracted modules
- [ ] Create architecture diagrams (mermaid)
- [ ] Document migration process
- [ ] Create module dependency graph

### Phase 13: Cleanup & Optimization (Not Started)
**Priority:** LOW
**Estimated:** 1 day

- [ ] Remove old monolithic `main.py` (or convert to thin wrapper)
- [ ] Clean up unused imports
- [ ] Optimize module structure if needed
- [ ] Profile performance
- [ ] Final code review

---

## Progress Metrics

### Lines Migrated
- **Phase 0-6 Total:** 5,250 lines extracted
- **Remaining in main.py:** ~14,000 lines
- **Overall Progress:** ~27% of code migrated

### Module Breakdown
| Module | Files | Lines | Status |
|--------|-------|-------|--------|
| core | 6 | 996 | ✅ Complete |
| models | 5 | 756 | ✅ Complete |
| utils | 4 | 786 | ✅ Complete |
| features/search | 2 | 629 | ✅ Complete |
| features/rewrite | 3 | 985 | ✅ Complete |
| features/schema | 2 | 1,022 | ✅ Complete |
| features/deduplication | 0 | 0 | ⏳ Next |
| features/complexity | 0 | 0 | 📋 Planned |
| features/quality | 0 | 0 | 📋 Planned |
| server | 0 | 0 | 📋 Planned |

### Test Status
- **Total Tests:** 1,561
- **Passing:** 1,561 ✅
- **Type Checking:** Clean ✅
- **Linting:** Clean ✅

---

## Timeline Estimate

### Completed (Days 1-6)
- Phase 0: 1 day ✅
- Phase 1: 2 days ✅
- Phase 2: 1 day ✅
- Phase 3: 2 days ✅
- Phases 4-6: 1 day ✅

### Remaining (Days 7-20)
- Phase 7 (Deduplication): 3-4 days
- Phase 8 (Complexity): 2-3 days
- Phase 9 (Quality): 2-3 days
- Phase 10 (Server): 2 days
- Phase 11 (Testing): 2-3 days
- Phase 12 (Documentation): 1-2 days
- Phase 13 (Cleanup): 1 day

**Total Estimated Time:**
- Completed: 6 days
- Remaining: 13-18 days
- **Total:** 19-24 days (4-5 weeks)

**Current Progress:** 6/24 days = ~25% time spent, ~27% code migrated

---

## Key Risks & Blockers

### Risks
1. **Import Cycles:** May need to adjust module dependencies
2. **Test Failures:** Integration tests may need updating
3. **Performance:** Modular structure may impact performance
4. **MCP Tool Registration:** All tools must be properly registered in new structure

### Mitigations
- Run tests after each phase
- Use mypy for type checking
- Profile performance before/after
- Keep backup branch for rollback

---

## Documentation References

- **Architecture Plan:** `docs/MODULAR-ARCHITECTURE.md`
- **Migration Plan:** `docs/MIGRATION-PLAN.md`
- **Phase Completions:**
  - `docs/PHASE-2-COMPLETION.md`
  - `docs/PHASE3-COMPLETION.md`
- **Module Dependencies:** `docs/MODULE-DEPENDENCIES.md`
- **Architecture Diagrams:** `docs/ARCHITECTURE-DIAGRAMS.md`

---

## Quick Commands

```bash
# Check current status
tree src/ast_grep_mcp -L 2

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Count remaining lines in main.py
wc -l main.py

# View commit history
git log --oneline --graph --all -20
```

---

## Next Immediate Action

**Start Phase 7: Deduplication Feature Extraction**

1. Create `features/deduplication/detector.py`
2. Extract detection functions from main.py
3. Create `features/deduplication/analyzer.py`
4. Extract analysis functions from main.py
5. Run tests to verify extraction
6. Commit: "refactor: extract deduplication detection and analysis"

---

**Status:** 🟢 On Track | **Priority:** HIGH | **Phase:** 7/13
