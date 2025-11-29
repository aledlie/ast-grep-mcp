# Module-by-Module Complexity Breakdown
**Generated:** 2025-11-28
**Total Functions Exceeding Thresholds:** 42

## Summary by Module

### 🔴 features/deduplication (21 functions - 50% of all issues)
**Risk Level:** CRITICAL
- **Count:** 21 functions (50% of all critical functions)
- **Average Cyclomatic:** 20.5
- **Average Cognitive:** 37.3
- **Max Cognitive:** 89 (worst in codebase)

**Top 3 Most Complex:**
1. `analysis_orchestrator.py:505-621` - Cyclomatic: 30, Cognitive: 89, Nesting: 8
2. `applicator.py:600-678` - Cyclomatic: 32, Cognitive: 73, Nesting: 6
3. `impact.py:386-494` - Cyclomatic: 38, Cognitive: 58, Nesting: 6

**Recommendation:** PRIORITY 1 - This module needs immediate refactoring attention

---

### ⚠️ features/schema (6 functions - 14% of issues)
**Risk Level:** HIGH
- **Count:** 6 functions (14% of all critical functions)
- **Average Cyclomatic:** 15.2
- **Average Cognitive:** 37.5
- **Max Cognitive:** 43

**Top 3 Most Complex:**
1. `client.py:31-74` - Cyclomatic: 17, Cognitive: 43, Nesting: 7 (duplicate)
2. `client.py:31-74` - Cyclomatic: 17, Cognitive: 43, Nesting: 7 (duplicate)
3. `client.py:192-238` - Cyclomatic: 18, Cognitive: 38, Nesting: 5

**Note:** Duplicate entries suggest complexity analyzer may be detecting same function twice

**Recommendation:** PRIORITY 2 - Address after deduplication module

---

### 🟡 features/refactoring (4 functions - 10% of issues)
**Risk Level:** MEDIUM
- **Count:** 4 functions (10% of all critical functions)
- **Average Cyclomatic:** 19.0
- **Average Cognitive:** 33.2
- **Max Cognitive:** 42

**Top 3 Most Complex:**
1. `renamer.py:165-202` - Cyclomatic: 18, Cognitive: 42, Nesting: 6
2. `analyzer.py:456-509` - Cyclomatic: 24, Cognitive: 33, Nesting: 5
3. `extractor.py:207-259` - Cyclomatic: 13, Cognitive: 31, Nesting: 5

**Recommendation:** PRIORITY 3 - Address in Phase 2

---

### 🟡 features/quality (4 functions - 10% of issues)
**Risk Level:** MEDIUM
- **Count:** 4 functions (10% of all critical functions)
- **Average Cyclomatic:** 15.0
- **Average Cognitive:** 31.5
- **Max Cognitive:** 42

**Top 3 Most Complex:**
1. `smells_detectors.py:352-409` - Cyclomatic: 11, Cognitive: 42, Nesting: 8
2. `enforcer.py:116-199` - Cyclomatic: 17, Cognitive: 32, Nesting: 5
3. `smells_detectors.py:460-513` - Cyclomatic: 10, Cognitive: 31, Nesting: 7

**Recommendation:** PRIORITY 3 - Address in Phase 2

---

### 🟢 features/complexity (3 functions - 7% of issues)
**Risk Level:** LOW-MEDIUM
- **Count:** 3 functions (7% of all critical functions)
- **Average Cyclomatic:** 17.3
- **Average Cognitive:** 19.7
- **Max Cognitive:** 35

**Top 3 Most Complex:**
1. `analyzer.py:77-145` - Cyclomatic: 12, Cognitive: 35, Nesting: 7
2. `tools.py:211-384` - Cyclomatic: 18, Cognitive: 13, Nesting: 5
3. `tools.py:514-627` - Cyclomatic: 22, Cognitive: 11, Nesting: 3

**Recommendation:** PRIORITY 4 - Address in Phase 3

---

### 🟢 features/search (2 functions - 5% of issues)
**Risk Level:** LOW
- **Count:** 2 functions (5% of all critical functions)
- **Average Cyclomatic:** 20.0
- **Average Cognitive:** 12.5
- **Max Cognitive:** 16

**Top 2 Most Complex:**
1. `service.py:308-409` - Cyclomatic: 22, Cognitive: 16, Nesting: 3
2. `tools.py:18-175` - Cyclomatic: 18, Cognitive: 9, Nesting: 4

**Recommendation:** PRIORITY 4 - Primarily cyclomatic violations, low cognitive load

---

### 🟢 utils (2 functions - 5% of issues)
**Risk Level:** LOW
- **Count:** 2 functions (5% of all critical functions)
- **Average Cyclomatic:** 12.5
- **Average Cognitive:** 11.5
- **Max Cognitive:** 13

**Top 2 Most Complex:**
1. `templates.py:422-489` - Cyclomatic: 16, Cognitive: 13, Nesting: 7
2. `templates.py:526-579` - Cyclomatic: 9, Cognitive: 10, Nesting: 7

**Recommendation:** PRIORITY 4 - Nesting violations only, low overall complexity

---

## Analysis Summary

### Module Priority Ranking

1. **features/deduplication** (21 functions)
   - 50% of all critical complexity issues
   - Contains worst function in entire codebase (cognitive 89)
   - Average cognitive 37.3 (23% over critical threshold)
   - **Action:** Immediate refactoring required

2. **features/schema** (6 functions)
   - 14% of issues
   - High average cognitive (37.5)
   - Duplicate detection issue needs investigation
   - **Action:** High priority, after deduplication

3. **features/refactoring** (4 functions)
   - 10% of issues
   - Moderate complexity
   - **Action:** Medium priority

4. **features/quality** (4 functions)
   - 10% of issues
   - Deep nesting in smell detectors (ironic!)
   - **Action:** Medium priority

5. **features/complexity** (3 functions)
   - 7% of issues
   - Moderate complexity
   - **Action:** Lower priority

6. **features/search** (2 functions)
   - 5% of issues
   - Primarily cyclomatic violations
   - **Action:** Lower priority

7. **utils** (2 functions)
   - 5% of issues
   - Nesting violations only
   - **Action:** Lowest priority

### Recommended Refactoring Order

**Phase 1 (Weeks 1-2): Critical Refactoring**
- Target: features/deduplication (21 functions)
- Focus: Top 5 worst functions
- Goal: Reduce by 70-80%

**Phase 2 (Weeks 3-4): High Priority**
- Target: features/schema (6 functions)
- Target: features/refactoring (4 functions)
- Target: features/quality (4 functions)
- Goal: All functions <30 cognitive

**Phase 3 (Weeks 5-6): Remaining Functions**
- Target: features/complexity (3 functions)
- Target: features/search (2 functions)
- Target: utils (2 functions)
- Goal: <5% functions exceeding thresholds

### Success Metrics by Module

**Deduplication Module:**
- Current: 21 functions exceeding thresholds
- Target: <3 functions (85% reduction)
- Timeline: 2 weeks

**Schema Module:**
- Current: 6 functions exceeding thresholds
- Target: 0 functions (100% elimination)
- Timeline: 1 week

**All Other Modules:**
- Current: 15 functions exceeding thresholds
- Target: <2 functions (87% reduction)
- Timeline: 2 weeks

---

**Generated:** 2025-11-28
**Next Review:** After Phase 1 refactoring (Week 3)
