# Test Suite Analysis & Consolidation Plan

**Date:** 2025-11-24
**Status:** Phase 11 - Testing & Validation

## Executive Summary

The test suite contains **24,814 lines** across **38 test files** with **1,536 test functions** organized into **245 test classes**. Analysis reveals **21 files have import errors** due to the Phase 10 refactoring that converted standalone functions to class-based APIs.

---

## Current State

### Test Suite Metrics
- **Total test files:** 38
- **Total lines:** 24,814
- **Test classes:** 245
- **Test functions:** 1,536
- **Average tests per file:** 40.4
- **Average tests per class:** 6.3
- **Files with `setup_method`:** 14

### Test Collection Status
- ✅ **532 tests collected** successfully
- ❌ **21 test files** with import errors
- 🔧 **Import errors blocking:** ~1,000+ tests

---

## Top 10 Largest Test Files

| Lines | File | Notes |
|-------|------|-------|
| 2,186 | `unit/test_standards_enforcement.py` | Code quality/standards tests |
| 1,421 | `unit/test_linting_rules.py` | Linting rule tests |
| 1,244 | `unit/test_dependencies.py` | Dependency analysis tests |
| 991 | `unit/test_unit.py` | **28 imports from main** ⚠️ |
| 989 | `integration/test_benchmark.py` | **9 imports from main** ⚠️ |
| 930 | `unit/test_schema.py` | Schema.org tests |
| 846 | `unit/test_rewrite.py` | Code rewrite tests |
| 821 | `unit/test_function_generation.py` | Function generation tests |
| 802 | `unit/test_complexity.py` | Complexity analysis tests |
| 740 | `unit/test_templates.py` | Template tests |

**Key Insight:** Top 2 files contain **3,607 lines (14.5%)** of test code and are likely targets for consolidation.

---

## Files with Import Errors (21 files, sorted by severity)

### High Priority (Multiple Imports)
1. **test_unit.py** - 28 imports ⚠️⚠️⚠️
2. **test_benchmark.py** - 9 imports ⚠️⚠️
3. **test_phase2.py** - 2 imports ⚠️

### Medium Priority (Single Import)
4-21. Files with 1 import each:
   - test_duplication.py
   - test_coverage_detection.py
   - test_import_management.py
   - test_parameter_extraction.py
   - test_enhanced_suggestions.py
   - test_complexity_scoring.py
   - test_function_generation.py
   - test_templates.py
   - test_standards_enforcement.py
   - test_dependency_analysis.py
   - test_linting_rules.py
   - test_schema.py
   - test_analyze_deduplication.py
   - test_validation_pipeline.py
   - test_ast_diff.py
   - test_call_site.py
   - test_code_formatting.py
   - test_code_smells.py
   - test_diff_preview.py
   - test_impact_analysis.py
   - test_recommendation_engine.py
   - test_variation_classification.py

---

## Consolidation Opportunities

### 1. **Merge Small Test Files** 🎯
**Candidates:** Files testing similar functionality in the same feature area

**Deduplication Targets:**
- **test_ast_diff.py** + **test_diff_preview.py** → `test_deduplication_diff.py`
- **test_call_site.py** + **test_impact_analysis.py** → `test_deduplication_impact.py`
- **test_parameter_extraction.py** + **test_function_generation.py** → `test_deduplication_generation.py`
- **test_complexity_scoring.py** + complexity tests → integrate into `test_complexity.py`
- **test_linting_rules.py** (1,421 lines) → Split into focused files or consolidate tests

**Estimated reduction:** 3,000-5,000 lines

### 2. **Standardize Import Patterns** 🔧
Currently 29 files import from `main.py` directly. After fixing imports:

**Before:**
```python
from main import align_code_blocks, classify_variation
```

**After (new modular approach):**
```python
from ast_grep_mcp.features.deduplication.analyzer import PatternAnalyzer
from ast_grep_mcp.models.deduplication import AlignmentResult, DiffTree
```

### 3. **Extract Common Test Fixtures** 🏗️
14 files have `setup_method` - potential for shared fixtures:

**Create:** `tests/conftest.py` with common fixtures:
```python
@pytest.fixture
def mock_executor():
    """Mock ast-grep executor for tests."""
    ...

@pytest.fixture
def sample_code_blocks():
    """Common test code samples."""
    ...

@pytest.fixture
def mock_mcp_instance():
    """Mock MCP server instance."""
    ...
```

**Estimated reduction:** 500-1,000 lines of duplicated setup code

### 4. **Consolidate Deduplication Tests** 📦
Multiple small deduplication test files can be merged:

**Current:**
- test_ast_diff.py
- test_diff_preview.py
- test_call_site.py
- test_parameter_extraction.py
- test_function_generation.py
- test_variation_classification.py
- test_coverage_detection.py
- test_impact_analysis.py
- test_recommendation_engine.py
- test_enhanced_suggestions.py
- test_complexity_scoring.py

**Proposed:**
- `test_deduplication_detection.py` - Detection & grouping
- `test_deduplication_analysis.py` - Variation analysis & diff trees
- `test_deduplication_generation.py` - Code generation & templates
- `test_deduplication_ranking.py` - Scoring & recommendations
- `test_deduplication_application.py` - Application & impact

**Estimated reduction:** 11 files → 5 files (~2,000 line reduction)

---

## Recommended Approach

### Phase 11A: Fix Import Errors (Priority 1)
**Goal:** Get all 1,536 tests running

**Strategy:** Update imports to use new modular API
- Update `test_unit.py` (28 imports) - highest impact
- Update `test_benchmark.py` (9 imports)
- Batch update remaining 19 files (1-2 imports each)

**Time:** 3-4 hours

### Phase 11B: Consolidate Tests (Priority 2)
**Goal:** Reduce test suite size by 20-30%

**Strategy:**
1. Create `tests/conftest.py` with common fixtures
2. Merge 11 deduplication test files → 5 consolidated files
3. Extract shared test utilities to `tests/helpers.py`
4. Remove duplicate setup/teardown code

**Time:** 4-6 hours

### Phase 11C: Validate & Document (Priority 3)
**Goal:** Ensure all tests pass and document changes

**Strategy:**
1. Run full test suite: `uv run pytest -v`
2. Fix any broken tests from consolidation
3. Update test documentation
4. Create test coverage report

**Time:** 2-3 hours

---

## Expected Outcomes

### Before Consolidation
- 38 test files
- 24,814 lines
- 245 test classes
- 1,536 tests
- 21 files with import errors

### After Consolidation (Estimated)
- ~30 test files (-21%)
- ~18,000 lines (-27%)
- ~180 test classes (-27%)
- 1,536 tests (same, better organized)
- 0 import errors ✅
- Shared fixtures in conftest.py
- Better test organization by feature

---

## Risks & Mitigations

### Risk 1: Breaking Tests During Consolidation
**Mitigation:**
- Fix imports first, verify all tests pass
- Consolidate incrementally, one feature at a time
- Keep git commits small and atomic

### Risk 2: Lost Test Coverage
**Mitigation:**
- Run coverage analysis before/after: `pytest --cov`
- Verify same test count maintained
- Review merged tests carefully

### Risk 3: Time Overrun
**Mitigation:**
- Phase 11A is critical, do first
- Phase 11B is optimization, can defer
- Set 2-hour time box per phase

---

## Next Actions

1. ✅ **Complete this analysis**
2. 🔧 **Start Phase 11A:** Fix import errors in test_unit.py
3. 🔧 **Continue Phase 11A:** Fix remaining 20 files
4. ✅ **Run tests:** Verify 1,536 tests pass
5. 📋 **Evaluate Phase 11B:** Decide if consolidation is worth the time
6. 📝 **Document results:** Update REMAINING-TASKS-SUMMARY.md

---

**Status:** Analysis Complete | **Priority:** Fix Imports (Phase 11A) | **Estimated Time:** 3-4 hours
