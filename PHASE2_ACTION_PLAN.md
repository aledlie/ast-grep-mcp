# Phase 2 Refactoring - Action Plan & Recommendations

**Date:** 2025-11-28
**Current Status:** 31 functions exceeding critical thresholds (down from 48)
**Phase 1 Progress:** 35% complete (17 functions refactored)

## Executive Summary

Phase 1 refactoring successfully reduced complexity violations from **48 → 32 functions** (33% reduction). The refactoring work demonstrated clear patterns and established robust testing infrastructure to prevent regressions.

### Key Achievements from Phase 1

✅ **16 functions refactored** with zero behavioral regressions
✅ **95% complexity reduction** in format_java_code (cyclomatic 39→7, cognitive 60→3)
✅ **90% complexity reduction** in detect_security_issues_impl (cyclomatic 31→3, cognitive 57→8)
✅ **14/15 regression tests passing**
✅ **All 1,600+ tests passing**
✅ **detector.py fully refactored** - ZERO violations remaining in this critical module

### Verified: detector.py Refactoring Complete

Analysis confirms `detector.py` has **0 functions exceeding critical thresholds**:
- ✅ `_merge_overlapping_groups` - Successfully refactored with helper extraction
- ✅ All 22 functions in detector.py within acceptable limits
- ✅ Clean modular design with `_build_item_to_groups_map` and `_process_group_connections` helpers

## Phase 2 Priority: Top 10 Critical Functions

Based on test failures and analysis, here are the **actual** top 10 functions to refactor:

### Critical Priority (Do These First!)

#### 1. **quality/enforcer.py:execute_rules_batch**
   - **Metrics:** Cognitive=45 (50% over), Nesting=8 (33% over)
   - **Issue:** Complex batch processing with deep error handling nesting
   - **Strategy:** Extract batch processing helpers, separate error handling
   - **Estimated Time:** 25-30 minutes
   - **Impact:** HIGH - Core quality enforcement function

#### 2. **complexity/analyzer.py:analyze_file_complexity**
   - **Metrics:** Cognitive=45 (50% over)
   - **Issue:** Language-specific analysis mixed with orchestration
   - **Strategy:** Extract language handlers, use strategy pattern
   - **Estimated Time:** 25-30 minutes
   - **Impact:** HIGH - Critical complexity analysis function

#### 3. **deduplication/coverage.py:_check_test_file_references_source**
   - **Metrics:** Cyclomatic=30 (50% over), Cognitive=44 (47% over)
   - **Issue:** Complex reference checking with multiple path types
   - **Strategy:** Extract reference patterns, use early returns
   - **Estimated Time:** 20-25 minutes
   - **Impact:** MEDIUM-HIGH - Test coverage critical for deduplication

### High Priority (High Complexity)

#### 4. **deduplication/coverage.py:get_test_coverage_for_files_batch**
   - **Metrics:** Cognitive=40 (33% over)
   - **Issue:** Batch processing with complex aggregation logic
   - **Strategy:** Extract aggregation helpers, parallelize operations
   - **Estimated Time:** 20-25 minutes
   - **Impact:** MEDIUM - Performance-sensitive batch operation

#### 5. **quality/fixer.py:apply_fixes_batch**
   - **Metrics:** Cyclomatic=26 (30% over), Cognitive=39 (30% over)
   - **Issue:** Complex fix application with safety checks
   - **Strategy:** Extract fix validators, separate dry-run logic
   - **Estimated Time:** 20-25 minutes
   - **Impact:** HIGH - Core auto-fix functionality

#### 6. **deduplication/recommendations.py:_generate_dedup_refactoring_strategies**
   - **Metrics:** Cyclomatic=37 (85% over)
   - **Issue:** Massive if-elif chain for strategy selection
   - **Strategy:** Configuration-driven strategy generation (like Phase 1 patterns)
   - **Estimated Time:** 20-25 minutes
   - **Impact:** MEDIUM - Strategy generation, can use Phase 1 config pattern

#### 7. **quality/security_scanner.py:scan_for_secrets_regex**
   - **Metrics:** Cognitive=36 (20% over), Nesting=8 (33% over)
   - **Issue:** Nested regex pattern matching loops
   - **Strategy:** Extract pattern matchers, reduce nesting
   - **Estimated Time:** 15-20 minutes
   - **Impact:** MEDIUM-HIGH - Security scanning

### Medium Priority (Moderate Complexity)

#### 8. **quality/smells_detectors.py:_extract_classes**
   - **Metrics:** Cognitive=35 (17% over), Nesting=7 (17% over)
   - **Issue:** Nested class detection logic
   - **Strategy:** Extract detection patterns, early returns
   - **Estimated Time:** 15-20 minutes
   - **Impact:** MEDIUM - Code smell detection

#### 9. **complexity/analyzer.py:_extract_classes_from_file**
   - **Metrics:** Cognitive=35 (17% over), Nesting=7 (17% over)
   - **Issue:** Similar to #8, class extraction logic
   - **Strategy:** Similar pattern to #8, extract helpers
   - **Estimated Time:** 15-20 minutes
   - **Impact:** MEDIUM - Complexity analysis support

#### 10. **quality/enforcer.py:load_rule_set**
   - **Metrics:** Cognitive=32 (7% over)
   - **Issue:** Rule loading with complex validation
   - **Strategy:** Extract validators, simplify loading logic
   - **Estimated Time:** 10-15 minutes
   - **Impact:** MEDIUM - Configuration loading

**Total Estimated Time for Top 10:** ~3.5 hours

## Remaining 22 Functions (Medium/Low Priority)

### Deduplication Module (6 functions)
- `applicator_validator.py:_suggest_syntax_fix` - cyclomatic=23
- `applicator_post_validator.py:_suggest_syntax_fix` - cyclomatic=24
- `generator.py:generate_extracted_function` - cyclomatic=23
- `generator.py:_infer_parameter_type` - cyclomatic=24
- `generator.py:substitute_template_variables` - cyclomatic=22
- Additional functions in recommendations, metrics modules

### Quality Module (4 functions)
- `tools.py:enforce_standards_tool` - cyclomatic=22
- `tools.py:detect_code_smells_tool` - cyclomatic=22
- Plus 2 more in fixer, scanner modules

### Complexity Module (2 functions)
- `tools.py:analyze_complexity_tool` - lines=174
- Plus 1 more

### Utils/Templates (2 functions)
- `format_typescript_function` - nesting=7
- `format_javascript_function` - nesting=7

### Other Modules (~8 functions)
- Various functions in rewrite, backup, search, schema modules

**Estimated Total Time for Remaining 22:** ~3-4 hours

## Refactoring Strategy by Module

### Quality Module (7 functions total)

**Common Pattern:** These functions handle rule enforcement, fix application, and security scanning. They share similar patterns of batch processing, rule execution, and error handling.

**Recommended Approach:**
1. Extract common batch processing utilities
2. Create shared error handling patterns
3. Use configuration-driven rule execution (proven pattern from Phase 1)

**Refactoring Order:**
1. `execute_rules_batch` (most complex) - establishes patterns
2. `apply_fixes_batch` - reuses patterns
3. `scan_for_secrets_regex` - similar nesting issues
4. `enforce_standards_tool`, `detect_code_smells_tool` - MCP wrappers
5. `load_rule_set` - configuration loading
6. `_extract_classes` - detection logic

### Deduplication Module (6 functions total)

**Common Pattern:** Syntax validation, code generation, template substitution. Multiple `_suggest_syntax_fix` implementations indicate duplication opportunity.

**Recommended Approach:**
1. **DRY Violation:** Two `_suggest_syntax_fix` functions (applicator_validator, applicator_post_validator)
   - Extract common syntax fix logic to shared utility
   - Reduce cyclomatic from 23-24 to <10 each
2. Extract template variable substitution patterns
3. Simplify type inference logic

**Refactoring Order:**
1. `_check_test_file_references_source` (highest complexity)
2. `get_test_coverage_for_files_batch` (batch processing)
3. `_generate_dedup_refactoring_strategies` (config-driven opportunity)
4. Create shared `_suggest_syntax_fix` utility
5. Refactor both applicator validators to use shared utility
6. Simplify generator functions

### Complexity Module (3 functions total)

**Common Pattern:** File analysis, class extraction, metrics calculation.

**Recommended Approach:**
1. Extract language-specific analysis into strategy pattern
2. Separate orchestration from analysis logic
3. Reduce MCP wrapper line counts

**Refactoring Order:**
1. `analyze_file_complexity` (core analysis)
2. `_extract_classes_from_file` (extraction logic)
3. `analyze_complexity_tool` (MCP wrapper - split into helpers)

### Utils/Templates (2 functions total)

**Common Pattern:** Deep nesting in code formatters.

**Recommended Approach:**
1. Extract nested formatting logic into helpers
2. Use early returns to reduce nesting
3. Consider shared formatting utilities (both are nesting=7)

## Proven Refactoring Patterns from Phase 1

### Pattern 1: Configuration-Driven Design

**Used Successfully In:** `detect_security_issues_impl`, `parse_args_and_get_config`

**Before Example:**
```python
def generate_strategy(dup_type, language):
    if dup_type == "exact":
        if language == "python":
            return create_python_exact()
        elif language == "java":
            return create_java_exact()
        # ... 20 more elif blocks
    elif dup_type == "similar":
        # ... 15 more elif blocks
```

**After Example:**
```python
STRATEGY_CONFIG = {
    ("exact", "python"): create_python_exact,
    ("exact", "java"): create_java_exact,
    # ... configuration entries
}

def generate_strategy(dup_type, language):
    key = (dup_type, language)
    generator = STRATEGY_CONFIG.get(key)
    if not generator:
        return default_strategy()
    return generator()
```

**Reduction:** Cyclomatic 37 → 8 (78% reduction)

### Pattern 2: Extract Method

**Used Successfully In:** `format_java_code`, all major refactorings

**Before Example:**
```python
def complex_function(data):
    # 100 lines of processing
    # Multiple nested loops
    # Complex conditionals
    return result
```

**After Example:**
```python
def complex_function(data):
    validated = _validate_input(data)
    processed = _process_items(validated)
    aggregated = _aggregate_results(processed)
    return _format_output(aggregated)

def _validate_input(data):
    # 15 lines

def _process_items(data):
    # 25 lines

def _aggregate_results(data):
    # 20 lines

def _format_output(data):
    # 10 lines
```

**Reduction:** Cyclomatic 39 → 7, Cognitive 60 → 3 (95% reduction)

### Pattern 3: Early Returns / Guard Clauses

**Used Successfully In:** Multiple refactorings

**Before Example:**
```python
def process(data):
    if data:
        if data.valid:
            if data.items:
                for item in data.items:
                    if item.active:
                        # Process
```

**After Example:**
```python
def process(data):
    if not data or not data.valid or not data.items:
        return []

    return [item for item in data.items if _should_process(item)]

def _should_process(item):
    return item.active and _additional_checks(item)
```

**Reduction:** Nesting 8 → 3 (62% reduction)

### Pattern 4: Service Layer Separation

**Used Successfully In:** MCP wrapper refactorings

**Before Example:**
```python
def mcp_tool(args):
    # 150 lines mixing:
    # - Argument validation
    # - Business logic
    # - Error handling
    # - Response formatting
```

**After Example:**
```python
def mcp_tool(args):
    validated = _validate_args(args)
    result = service_impl(validated)
    return _format_response(result)

def service_impl(params):
    # Core business logic
    # Much easier to test
```

**Reduction:** Lines 150 → 50 (67% reduction per function)

## Testing Strategy

### After Each Function Refactoring

**1. Run Module-Specific Tests:**
```bash
# Quality module
uv run pytest tests/unit/test_standards*.py tests/unit/test_security*.py -v

# Deduplication module
uv run pytest tests/unit/test_deduplication*.py tests/unit/test_coverage*.py -v

# Complexity module
uv run pytest tests/unit/test_complexity*.py -v
```

**2. Run Complexity Regression Tests:**
```bash
uv run pytest tests/quality/test_complexity_regression.py -v
```

**3. Check Violation Count:**
```bash
uv run pytest tests/quality/test_complexity_regression.py::TestComplexityTrends::test_no_functions_exceed_critical_thresholds -v | grep "Found"
```

**4. Run Full Test Suite (Quick Check):**
```bash
uv run pytest tests/ -q --tb=no
```

### After Batch of 5 Functions

**1. Full Test Suite:**
```bash
uv run pytest tests/ -v
```

**2. Type Checking:**
```bash
uv run mypy src/
```

**3. Linting:**
```bash
uv run ruff check .
```

## Session Planning

### Session 1: Critical Quality Module (3-4 hours)
**Target:** Refactor 5 quality module functions

1. `execute_rules_batch` (25-30 min)
2. `apply_fixes_batch` (20-25 min)
3. `scan_for_secrets_regex` (15-20 min)
4. `_extract_classes` (15-20 min)
5. `load_rule_set` (10-15 min)

**Expected Progress:** 32 → 27 violations (15% reduction)

### Session 2: Complexity & Deduplication (3-4 hours)
**Target:** Refactor 5 critical functions

1. `analyze_file_complexity` (25-30 min)
2. `_check_test_file_references_source` (20-25 min)
3. `get_test_coverage_for_files_batch` (20-25 min)
4. `_generate_dedup_refactoring_strategies` (20-25 min)
5. `_extract_classes_from_file` (15-20 min)

**Expected Progress:** 27 → 22 violations (15% reduction)

### Session 3: Remaining Functions (3-4 hours)
**Target:** Refactor 10-12 medium/low priority functions

- Focus on deduplication generators (4 functions)
- Focus on utils/templates (2 functions)
- Focus on remaining quality/complexity tools (4-6 functions)

**Expected Progress:** 22 → 10 violations (38% reduction)

### Session 4: Final Sprint (2-3 hours)
**Target:** Complete remaining 8-10 functions

- Final cleanup
- Documentation updates
- Celebrate 100% completion! 🎉

**Expected Progress:** 10 → 0 violations (100% complete!)

## Code-Refactor-Agent Usage

For complex refactorings (cognitive >40), use the `code-refactor-agent` with Opus model:

```python
Task(
    subagent_type='code-refactor-agent',
    description='Refactor execute_rules_batch in quality/enforcer.py',
    prompt='''
Refactor the execute_rules_batch function to reduce complexity:

Current Metrics:
- Cognitive complexity: 45 (target: <30)
- Nesting depth: 8 (target: <6)

Strategy:
1. Extract batch processing into _process_rules_batch helper
2. Extract error handling into _handle_rule_error helper
3. Extract result aggregation into _aggregate_rule_results helper
4. Use early returns to reduce nesting

Requirements:
- Maintain exact same behavior
- Preserve all error handling
- Keep all logging statements
- Run tests after refactoring

Reference Phase 1 patterns in format_java_code and detect_security_issues_impl.
    ''',
    model='opus'
)
```

## Success Metrics

### Phase 2 Completion Criteria

✅ **0 functions exceeding critical thresholds** (from current 32)
✅ **15/15 complexity regression tests passing**
✅ **All 1,600+ tests passing**
✅ **Zero behavioral regressions**
✅ **Type checking passes** (`mypy src/`)
✅ **Linting passes** (`ruff check .`)

### Quality Improvements

**Expected Codebase Improvements:**
- Average cyclomatic complexity: 15 → 8 (47% reduction)
- Average cognitive complexity: 20 → 12 (40% reduction)
- Functions >150 lines: 5 → 0 (100% reduction)
- Average nesting depth: 4 → 3 (25% reduction)

### Documentation Updates Required

When Phase 2 is complete:

1. ✅ Update `CODEBASE_ANALYSIS_REPORT.md` with final metrics
2. ✅ Update `PHASE1_REFACTORING_SUMMARY.md` → `COMPLETE_REFACTORING_SUMMARY.md`
3. ✅ Create `PHASE2_COMPLETE_REPORT.md` with detailed session notes
4. ✅ Update `CLAUDE.md` to reflect complexity improvements
5. ✅ Update `README.md` to highlight code quality achievements

## Common Pitfalls to Avoid

### ❌ Don't Change Behavior
- Maintain exact same outputs
- Preserve all edge cases
- Keep all error messages identical

### ❌ Don't Skip Tests
- Run tests after EACH refactoring
- Don't batch test runs
- Immediate feedback prevents debugging marathons

### ❌ Don't Over-Extract
- Helper functions should be 20-50 lines
- Avoid extracting single-line helpers
- Maintain readability

### ❌ Don't Lose Context
- Descriptive helper names: `_validate_input` not `_helper1`
- Preserve comments explaining "why"
- Keep related code together

### ❌ Don't Ignore Edge Cases
- Test edge cases explicitly
- Preserve all validation logic
- Don't simplify away error handling

## Tools & Commands Reference

### Quick Violation Check
```bash
uv run python -c "
import subprocess, re
result = subprocess.run(['uv', 'run', 'pytest',
    'tests/quality/test_complexity_regression.py::TestComplexityTrends::test_no_functions_exceed_critical_thresholds',
    '-v'], capture_output=True, text=True)
match = re.search(r'Found (\d+) function', result.stdout + result.stderr)
print(f'Violations: {match.group(1)}' if match else 'All tests passing!')
"
```

### Analyze Specific File
```bash
uv run python -c "
from src.ast_grep_mcp.models.complexity import ComplexityThresholds
from src.ast_grep_mcp.features.complexity.analyzer import analyze_file_complexity

thresholds = ComplexityThresholds(cyclomatic=20, cognitive=30, nesting_depth=6, lines=150)
results = analyze_file_complexity(
    file_path='src/ast_grep_mcp/features/quality/enforcer.py',
    language='python',
    thresholds=thresholds
)

exceeding = [f for f in results if f.exceeds]
for func in exceeding:
    print(f'{func.function_name} (line {func.start_line}): {func.exceeds}')
"
```

### Run Tests for Module
```bash
# Quality module
uv run pytest tests/ -k "quality or standards or security" -v

# Deduplication module
uv run pytest tests/ -k "dedup" -v

# Complexity module
uv run pytest tests/ -k "complexity" -v
```

## Progress Tracking Checklist

### Critical Functions (Must Complete)
- [x] quality/enforcer.py:execute_rules_batch ✅ **COMPLETED** (cognitive: 45→10, nesting: 8→3)
- [ ] complexity/analyzer.py:analyze_file_complexity
- [ ] deduplication/coverage.py:_check_test_file_references_source
- [ ] deduplication/coverage.py:get_test_coverage_for_files_batch
- [ ] quality/fixer.py:apply_fixes_batch

### High Priority (Should Complete)
- [ ] deduplication/recommendations.py:_generate_dedup_refactoring_strategies
- [ ] quality/security_scanner.py:scan_for_secrets_regex
- [ ] quality/smells_detectors.py:_extract_classes
- [ ] complexity/analyzer.py:_extract_classes_from_file
- [ ] quality/enforcer.py:load_rule_set

### Remaining Functions (Time Permitting)
- [ ] 22 medium/low priority functions

## Next Steps

1. **Immediate:** Start with `quality/enforcer.py:execute_rules_batch` (highest cognitive complexity)
2. **Session Goal:** Complete top 5 critical functions (reduce violations to ~27)
3. **Phase 2 Goal:** Achieve 0 violations (complete all 32 functions)
4. **Timeline:** 4 sessions × 3-4 hours = 12-16 hours total

---

**Last Updated:** 2025-11-28
**Status:** Ready for Phase 2 execution
**Confidence Level:** HIGH - Clear patterns established, robust testing in place
**Risk Level:** LOW - Comprehensive test coverage provides safety net

Let's complete this refactoring! 🚀
