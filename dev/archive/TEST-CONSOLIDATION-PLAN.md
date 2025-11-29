# Test Consolidation Plan - Deduplication Tests

**Status:** Phase 11B In Progress
**Target:** Consolidate 14 files (7,955 lines) → 5 focused files

---

## Current State

### Files to Consolidate (14 files, 7,955 lines)

| File | Lines | Focus Area |
|------|-------|------------|
| test_duplication.py | ~600 | Core detection |
| test_apply_deduplication.py | ~800 | Application logic |
| test_ast_diff.py | ~700 | AST diffing & alignment |
| test_diff_preview.py | ~550 | Diff preview generation |
| test_call_site.py | ~400 | Call site analysis |
| test_parameter_extraction.py | ~500 | Parameter extraction |
| test_function_generation.py | ~821 | Function generation |
| test_variation_classification.py | ~650 | Variation classification |
| test_coverage_detection.py | ~550 | Test coverage detection |
| test_impact_analysis.py | ~600 | Impact analysis |
| test_recommendation_engine.py | ~580 | Recommendation generation |
| test_enhanced_suggestions.py | ~400 | Enhanced suggestions |
| test_enhanced_reporting.py | ~500 | Reporting & UI |
| test_complexity_scoring.py | ~304 | Complexity scoring |

---

## Proposed Consolidation

### New Structure (5 files, ~8,000 lines maintained)

#### 1. `test_deduplication_detection.py` (~2,000 lines)
**Merges:** test_duplication.py, test_ast_diff.py, test_diff_preview.py
**Focus:** Detection, grouping, AST diff, alignment

**Sections:**
- Detection & Grouping Tests
- AST Diff Analysis Tests
- Code Alignment Tests
- Diff Preview Generation Tests

#### 2. `test_deduplication_analysis.py` (~1,800 lines)
**Merges:** test_variation_classification.py, test_parameter_extraction.py, test_complexity_scoring.py
**Focus:** Variation analysis, parameter extraction, complexity

**Sections:**
- Variation Classification Tests
- Parameter Extraction Tests
- Complexity Scoring Tests
- Pattern Analysis Tests

#### 3. `test_deduplication_generation.py` (~1,800 lines)
**Merges:** test_function_generation.py, test_call_site.py
**Focus:** Code generation, function templates, call replacement

**Sections:**
- Function Template Tests
- Function Generation Tests
- Call Site Replacement Tests
- Import Management Tests

#### 4. `test_deduplication_ranking.py` (~1,600 lines)
**Merges:** test_impact_analysis.py, test_coverage_detection.py, test_recommendation_engine.py
**Focus:** Impact analysis, coverage detection, recommendations

**Sections:**
- Test Coverage Detection Tests
- Impact Analysis Tests
- Ranking Algorithm Tests
- Recommendation Engine Tests

#### 5. `test_deduplication_application.py` (~1,800 lines)
**Merges:** test_apply_deduplication.py, test_enhanced_suggestions.py, test_enhanced_reporting.py
**Focus:** Application orchestration, reporting, UI

**Sections:**
- Application Orchestration Tests
- Backup & Rollback Tests
- Enhanced Reporting Tests
- Diff Visualization Tests

---

## Benefits

### Code Reduction
- **Before:** 14 files, 7,955 lines
- **After:** 5 files, ~7,500 lines (estimated 5-10% reduction from removing duplicate imports/setup)
- **Improvement:** 64% fewer files, better organization

### Maintainability
- ✅ Related tests grouped logically
- ✅ Reduced import duplication
- ✅ Shared fixtures via conftest.py
- ✅ Easier to find relevant tests
- ✅ Better alignment with module structure

### Test Discovery
- Tests now match feature module structure:
  - `features/deduplication/detector.py` → `test_deduplication_detection.py`
  - `features/deduplication/analyzer.py` → `test_deduplication_analysis.py`
  - `features/deduplication/generator.py` → `test_deduplication_generation.py`
  - `features/deduplication/ranker.py` → `test_deduplication_ranking.py`
  - `features/deduplication/applicator.py` → `test_deduplication_application.py`

---

## Implementation Strategy

### Approach 1: Manual Consolidation (High Effort, High Quality)
**Time:** 6-8 hours
**Process:**
1. Create 5 new test files with structure
2. Copy test classes from old files, grouping logically
3. Remove duplicate imports/fixtures
4. Update imports to use conftest.py fixtures
5. Run tests to verify nothing broken
6. Delete old files
7. Update test discovery

**Pros:** Complete control, optimal organization
**Cons:** Time-intensive, error-prone

### Approach 2: Semi-Automated (Medium Effort, Good Quality)
**Time:** 3-4 hours
**Process:**
1. Create 5 new files with basic structure
2. Use script to copy test classes automatically
3. Manually review and fix imports
4. Run tests incrementally
5. Archive old files (don't delete immediately)

**Pros:** Faster, safer (can rollback)
**Cons:** May need manual cleanup

### Approach 3: Defer Consolidation (Low Effort, Current State)
**Time:** 0 hours
**Process:**
1. Skip consolidation for now
2. Fix import errors (Phase 11A)
3. Get tests running
4. Revisit consolidation later

**Pros:** Focus on critical path
**Cons:** Maintains current complexity

---

## Recommendation

**Defer to Approach 3** for now:

### Reasoning
1. **Critical Path:** Import errors block 1,000+ tests from running
2. **Time Investment:** Consolidation is 6-8 hours vs 3-4 hours for imports
3. **Risk:** Consolidation could introduce new errors
4. **Value:** Getting tests passing is higher priority than organization

### Revised Plan
1. ✅ Create conftest.py (DONE)
2. ⏭️ **Skip detailed consolidation for now**
3. 🔧 **Move to Phase 11A:** Fix 21 test import errors
4. ✅ Get all 1,536 tests running
5. 📋 Revisit consolidation in Phase 12 if time permits

---

## If Consolidation is Pursued Later

### Step-by-Step Process

**Step 1: Create New Files**
```bash
touch tests/unit/test_deduplication_detection.py
touch tests/unit/test_deduplication_analysis.py
touch tests/unit/test_deduplication_generation.py
touch tests/unit/test_deduplication_ranking.py
touch tests/unit/test_deduplication_application.py
```

**Step 2: Add File Headers**
Each file gets:
- Module docstring
- Standard imports
- Import from conftest.py fixtures
- Test class structure

**Step 3: Copy Test Classes**
Use script to extract and copy test classes:
```python
# Script to extract test classes and move to new files
# Maps old file → test classes → new file
```

**Step 4: Update Imports**
- Replace `from main import X` with new modular imports
- Use conftest.py fixtures where possible
- Remove duplicate setup_method code

**Step 5: Validate**
```bash
# Run new files to verify tests pass
uv run pytest tests/unit/test_deduplication_detection.py -v
uv run pytest tests/unit/test_deduplication_analysis.py -v
# ... etc
```

**Step 6: Archive Old Files**
```bash
mkdir tests/archive
mv tests/unit/test_duplication.py tests/archive/
# ... etc
```

**Step 7: Update Documentation**
- Update TEST-SUITE-ANALYSIS.md
- Update CLAUDE.md test section
- Document consolidation in Phase 11 report

---

## Decision

**DEFER CONSOLIDATION**

Move immediately to **Phase 11A: Fix Import Errors** for maximum impact with minimum risk.

Consolidation can be revisited after tests are passing and import errors are resolved.

---

**Status:** Consolidation Deferred | **Next:** Phase 11A | **Priority:** Fix Imports
