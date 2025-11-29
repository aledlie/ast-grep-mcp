# Architecture Summary - Quick Reference

**Date:** 2025-11-24
**Status:** Design Complete, Ready for Implementation

## TL;DR

Refactor `main.py` (19,477 lines) → **44 modular files** (~450 lines avg)

**Timeline:** 4-6 weeks | **Risk:** Low (full backward compatibility)

## Directory Structure

```
src/ast_grep_mcp/
├── core/          # Infrastructure (6 files)
│   ├── config.py, cache.py, logging.py
│   ├── sentry.py, exceptions.py, executor.py
│
├── models/        # Data classes (4 files)
│   ├── config.py, deduplication.py
│   ├── complexity.py, standards.py
│
├── utils/         # Utilities (4 files)
│   ├── templates.py, formatters.py
│   ├── text.py, validation.py
│
├── features/      # Business logic (30 files)
│   ├── search/         (3 files: service, syntax, tools)
│   ├── rewrite/        (3 files: backup, service, tools)
│   ├── schema/         (2 files: client, tools)
│   ├── deduplication/  (11 files: detector, analyzer, ranker, generator,
│   │                    applicator, coverage, impact, recommendations,
│   │                    reporting, benchmark, tools)
│   ├── complexity/     (4 files: analyzer, metrics, storage, tools)
│   └── quality/        (5 files: smells, rules, validator, enforcer, tools)
│
└── server/        # MCP server (2 files)
    ├── registry.py, runner.py
```

## Layer Dependencies

```
┌─────────────┐
│   Server    │  # Tool registration, runner
└──────┬──────┘
       ↓
┌─────────────┐
│  Features   │  # Business logic (27 tools)
└──────┬──────┘
       ↓
┌─────────────┐
│    Utils    │  # Shared utilities
└──────┬──────┘
       ↓
┌─────────────┐
│   Models    │  # Data structures
└──────┬──────┘
       ↓
┌─────────────┐
│    Core     │  # Infrastructure
└─────────────┘
```

**Rule:** Dependencies flow downward only (no circular dependencies)

## Tool Distribution

| Feature | Tools | Files | Lines |
|---------|-------|-------|-------|
| **Search** | 6 tools | 3 | 1,200 |
| **Rewrite** | 3 tools | 3 | 1,100 |
| **Schema.org** | 8 tools | 2 | 1,100 |
| **Deduplication** | 4 tools | 11 | 11,000 |
| **Complexity** | 2 tools | 4 | 1,300 |
| **Quality** | 3 tools | 5 | 2,000 |
| **Core** | - | 6 | 1,230 |
| **Models** | - | 4 | 800 |
| **Utils** | - | 4 | 1,050 |
| **Server** | - | 2 | 300 |
| **Total** | **27 tools** | **44 files** | **20,080** |

## Migration Phases

### Phase 0: Prep (Day 1)
- Create directory structure
- Set up package installation

### Phase 1-3: Foundation (Days 2-9)
- Extract **core** infrastructure (6 files)
- Extract **models** (4 files)
- Extract **utils** (4 files)
- **Tests:** All unit tests pass

### Phase 4-6: Simple Features (Days 10-14)
- Extract **search** feature (3 files)
- Extract **rewrite** feature (3 files)
- Extract **schema** feature (2 files)
- **Tests:** Feature tests pass

### Phase 7: Deduplication (Days 15-21)
- Extract 11 deduplication modules
- Largest and most complex feature
- **Tests:** 1,000+ deduplication tests pass

### Phase 8-9: Analysis Features (Days 22-25)
- Extract **complexity** feature (4 files)
- Extract **quality** feature (5 files)
- **Tests:** All analysis tests pass

### Phase 10: Integration (Days 26-28)
- Create **server** layer (2 files)
- Refactor **main.py** to entry point
- **Tests:** All 1,561 tests pass

### Phase 11-12: Finalization (Days 29-30)
- Update documentation
- Final validation
- Create PR and merge

## Import Strategy

### Current (Tests)
```python
from main import run_ast_grep, find_code_impl
```

### After Migration (Tests unchanged initially)
```python
from main import run_ast_grep  # Still works (re-exported)
```

### New Package Imports (After test migration)
```python
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.features.search.service import find_code_impl
```

## Tool Registration Pattern

### Before
```python
def register_mcp_tools():  # 4,354 lines
    @mcp.tool()
    def find_code(...):
        # implementation inline
```

### After
```python
# features/search/tools.py
def register_search_tools(mcp: FastMCP):
    @mcp.tool()
    def find_code(...):
        return find_code_impl(...)  # Call service layer

# server/registry.py
def register_all_tools(mcp: FastMCP):
    register_search_tools(mcp)
    register_rewrite_tools(mcp)
    # ... all features
```

## Key Benefits

### Before
- **19,477 lines** in one file
- **4,354 line** function
- **2-5 minutes** to find code
- **High** merge conflicts
- **Slow** IDE performance
- **Overwhelming** for new developers

### After
- **44 files**, ~450 lines avg
- **Clear** module boundaries
- **<30 seconds** to find code
- **Low** merge conflicts
- **Fast** IDE performance
- **Easy** onboarding

## Success Criteria

- [ ] All 1,561 tests pass
- [ ] All 27 tools work
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] No performance regression (<5%)
- [ ] MCP server works
- [ ] Documentation complete
- [ ] Zero breaking changes

## Backward Compatibility

**main.py stays as entry point:**
```python
# Re-export everything for backward compatibility
from ast_grep_mcp.server.runner import run_mcp_server
from ast_grep_mcp.features.search.service import *
from ast_grep_mcp.features.rewrite.service import *
# ... all exports

if __name__ == "__main__":
    run_mcp_server()
```

**Tests keep working:**
```python
# Existing test imports still work
from main import run_ast_grep  # ✓ Works via re-export
```

## Risk Mitigation

### Low Risk Areas
- Core infrastructure (minimal dependencies)
- Models (no business logic)
- Utils (pure functions)
- Schema feature (highly independent)

### Medium Risk Areas
- Deduplication (large, complex, many dependencies)
- Tool registration (ensure all 27 tools work)

### Mitigation Strategies
1. **Incremental extraction** - One module at a time
2. **Test after each phase** - Catch issues early
3. **Backward compatibility** - No breaking changes
4. **Clear rollback plan** - Git branches + backups
5. **Feature freeze** - No parallel changes

## Validation Checklist

After each phase:
```bash
# 1. Imports work
python -c "import ast_grep_mcp; print('✓')"

# 2. Tests pass
uv run pytest tests/unit/ -v

# 3. Type checking
uv run mypy src/ast_grep_mcp/

# 4. Linting
uv run ruff check .

# 5. Commit
git add src/
git commit -m "refactor: extract [phase name]"
```

## Next Steps

### Immediate (Today)
1. **Review** architecture with team
2. **Approve** migration plan
3. **Schedule** 4-6 week timeline
4. **Announce** feature freeze

### Week 1 (Start Migration)
1. Create feature branch
2. Complete Phase 0 (prep)
3. Complete Phase 1-3 (foundation)
4. Daily progress updates

### Week 2-5 (Execute Migration)
- Follow phase-by-phase plan
- Test after each phase
- Commit frequently
- Update documentation

### Week 5-6 (Finalization)
- Final validation
- Create pull request
- Code review
- Merge to main

## Questions?

**See detailed documentation:**
- [MODULAR-ARCHITECTURE.md](MODULAR-ARCHITECTURE.md) - Complete design
- [MODULE-DEPENDENCIES.md](MODULE-DEPENDENCIES.md) - Dependency graph
- [MIGRATION-PLAN.md](MIGRATION-PLAN.md) - Step-by-step guide

**Key contacts:**
- Architecture questions: [Lead Developer]
- Migration timeline: [Project Manager]
- Test strategy: [QA Lead]

---

**Status:** Ready to begin Phase 0
**Last Updated:** 2025-11-24
