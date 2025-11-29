# Phase 1 Refactoring - Next Session Quick Guide

**Current Status:** 24/48 violations remaining (50% complete) ✅
**Last Updated:** 2025-11-28 (Session 2)

## Quick Start Commands

```bash
# Check current violation count
uv run pytest tests/quality/test_complexity_regression.py::TestComplexityTrends::test_no_functions_exceed_critical_thresholds -v

# Run all tests
uv run pytest tests/ -q --tb=no

# Run tests for specific module
uv run pytest tests/ -k "deduplication" -v
```

## Priority List: Top 10 Functions to Refactor Next

### Critical (Highest Complexity - Do These First!)

1. **deduplication/detector.py:_merge_overlapping_groups**
   - Cognitive: 58 (93% over limit) ⚠️ HIGHEST IN CODEBASE
   - Nesting: 8 (33% over limit)
   - Strategy: Extract connection processing logic, reduce nested loops
   - Estimated time: 30-40 minutes

2. **quality/enforcer.py:execute_rules_batch**
   - Cognitive: 45 (50% over limit)
   - Nesting: 8 (33% over limit)
   - Strategy: Extract batch processing helpers, reduce error handling nesting
   - Estimated time: 20-30 minutes

3. **complexity/analyzer.py:analyze_file_complexity**
   - Cognitive: 45 (50% over limit)
   - Strategy: Extract language-specific analysis, separate concerns
   - Estimated time: 20-30 minutes

4. **deduplication/coverage.py:_check_test_file_references_source**
   - Cyclomatic: 30 (50% over limit)
   - Cognitive: 44 (47% over limit)
   - Strategy: Extract reference checking logic, use early returns
   - Estimated time: 20-25 minutes

### High Priority (Moderate Complexity)

5. **deduplication/coverage.py:get_test_coverage_for_files_batch**
   - Cognitive: 40 (33% over limit)
   - Strategy: Extract batch processing, parallelize operations
   - Estimated time: 15-20 minutes

6. **quality/fixer.py:apply_fixes_batch**
   - Cyclomatic: 26 (30% over limit)
   - Cognitive: 39 (30% over limit)
   - Strategy: Extract fix application logic, reduce branching
   - Estimated time: 20-25 minutes

7. **deduplication/recommendations.py:_generate_dedup_refactoring_strategies**
   - Cyclomatic: 37 (85% over limit)
   - Strategy: Configuration-driven strategy generation
   - Estimated time: 15-20 minutes

8. **quality/security_scanner.py:scan_for_secrets_regex**
   - Cognitive: 36 (20% over limit)
   - Nesting: 8 (33% over limit)
   - Strategy: Extract pattern matching, reduce nesting
   - Estimated time: 15-20 minutes

9. **quality/smells_detectors.py:_extract_classes**
   - Cognitive: 35 (17% over limit)
   - Nesting: 7 (17% over limit)
   - Strategy: Extract class detection logic, early returns
   - Estimated time: 15-20 minutes

10. **complexity/analyzer.py:_extract_classes_from_file**
    - Cognitive: 35 (17% over limit)
    - Nesting: 7 (17% over limit)
    - Strategy: Similar to #9, extract detection patterns
    - Estimated time: 15-20 minutes

**Total Estimated Time for Top 10:** ~3.5 hours

## Remaining 22 Functions (Medium/Low Priority)

After completing the top 10, tackle these in batches by module:

### Deduplication Module (4 more)
- `_calculate_variation_complexity` - cyclomatic=28
- `generate_extracted_function` - cyclomatic=23
- `_suggest_syntax_fix` (applicator_validator) - cyclomatic=23
- `_suggest_syntax_fix` (applicator_post_validator) - cyclomatic=24

### Quality Module (2 more)
- `enforce_standards_tool` - cyclomatic=22
- `load_rule_set` - cognitive=32

### Complexity Module (2 more)
- `analyze_complexity_tool` - lines=174
- `detect_code_smells_tool` - cyclomatic=22

### Utils/Templates (2 more)
- `format_typescript_function` - nesting=7
- `format_javascript_function` - nesting=7

### Other Modules (~10 more)
- Various functions in rewrite, backup, search, schema modules

**Total Remaining Estimated Time:** ~2.5 hours

## Refactoring Strategy by Complexity Type

### For High Cognitive Complexity (40-58)
1. **Identify nested loops and conditionals**
2. **Extract inner loops into helper functions**
3. **Use early returns to reduce nesting**
4. **Consider breaking algorithm into stages**

**Example Pattern:**
```python
# Before: Cognitive complexity 58
def complex_function(data):
    result = []
    for item in data:
        if condition1:
            for nested_item in item.children:
                if condition2:
                    for deep_item in nested_item.values:
                        if condition3:
                            result.append(process(deep_item))
    return result

# After: Cognitive complexity 15
def complex_function(data):
    result = []
    for item in data:
        if not condition1:
            continue
        result.extend(_process_children(item.children))
    return result

def _process_children(children):
    result = []
    for child in children:
        if not condition2:
            continue
        result.extend(_process_values(child.values))
    return result
```

### For High Cyclomatic Complexity (25-37)
1. **Use configuration dictionaries instead of if-elif chains**
2. **Extract decision logic into separate functions**
3. **Consider using Strategy Pattern**

**Example Pattern:**
```python
# Before: Cyclomatic 37
def generate_strategy(dup_type, language, params):
    if dup_type == "exact":
        if language == "python":
            return create_python_exact(params)
        elif language == "java":
            return create_java_exact(params)
        # ... 20 more elif blocks
    elif dup_type == "similar":
        # ... another 15 elif blocks

# After: Cyclomatic 8
STRATEGY_GENERATORS = {
    ("exact", "python"): create_python_exact,
    ("exact", "java"): create_java_exact,
    # ... configuration entries
}

def generate_strategy(dup_type, language, params):
    key = (dup_type, language)
    generator = STRATEGY_GENERATORS.get(key)
    if not generator:
        return default_strategy(params)
    return generator(params)
```

### For High Nesting (7-8 levels)
1. **Use guard clauses and early returns**
2. **Extract nested blocks into functions**
3. **Invert conditionals where possible**

**Example Pattern:**
```python
# Before: Nesting 8
def process(data):
    if data:
        if data.valid:
            if data.items:
                for item in data.items:
                    if item.active:
                        if item.value:
                            if check(item):
                                if process_item(item):
                                    results.append(item)

# After: Nesting 3
def process(data):
    if not data or not data.valid or not data.items:
        return []

    return [item for item in data.items if _should_process_item(item)]

def _should_process_item(item):
    if not item.active or not item.value:
        return False
    if not check(item):
        return False
    return process_item(item)
```

## Testing Strategy

After refactoring each function:

1. **Run specific tests:**
   ```bash
   # For deduplication
   uv run pytest tests/unit/test_deduplication*.py -v

   # For quality
   uv run pytest tests/unit/test_standards*.py tests/unit/test_security*.py -v

   # For complexity
   uv run pytest tests/unit/test_complexity*.py -v
   ```

2. **Run complexity regression:**
   ```bash
   uv run pytest tests/quality/test_complexity_regression.py -v
   ```

3. **Check violation count:**
   ```python
   # Should decrease after each successful refactoring
   uv run python -c "
   import subprocess, re
   result = subprocess.run(['uv', 'run', 'pytest',
       'tests/quality/test_complexity_regression.py::TestComplexityTrends::test_no_functions_exceed_critical_thresholds',
       '-v'], capture_output=True, text=True)
   match = re.search(r'Found (\d+) function', result.stdout + result.stderr)
   print(f'Violations remaining: {match.group(1)}' if match else 'Could not parse')
   "
   ```

## Progress Tracking

Update this checklist as you complete functions:

### Critical Functions
- [ ] _merge_overlapping_groups (deduplication/detector.py)
- [ ] execute_rules_batch (quality/enforcer.py)
- [ ] analyze_file_complexity (complexity/analyzer.py)
- [ ] _check_test_file_references_source (deduplication/coverage.py)

### High Priority
- [ ] get_test_coverage_for_files_batch (deduplication/coverage.py)
- [ ] apply_fixes_batch (quality/fixer.py)
- [ ] _generate_dedup_refactoring_strategies (deduplication/recommendations.py)
- [ ] scan_for_secrets_regex (quality/security_scanner.py)
- [ ] _extract_classes (quality/smells_detectors.py)
- [ ] _extract_classes_from_file (complexity/analyzer.py)

### Remaining 22 Functions
- [ ] [Update as you go]

## Success Metrics

**Target for Phase 1 Completion:**
- ✅ 0 violations (from current 32)
- ✅ 15/15 complexity regression tests passing
- ✅ All 1,600+ tests passing
- ✅ No behavioral regressions

**Session Goal:**
- Reduce violations by 50% (32 → 16)
- Focus on top 10 critical/high-priority functions
- Estimated session time: 3-4 hours

## Common Pitfalls to Avoid

1. **Don't change behavior** - Maintain exact same outputs
2. **Don't skip tests** - Run tests after each refactoring
3. **Don't over-extract** - Keep helper functions reasonably sized (20-50 lines)
4. **Don't lose context** - Helper function names should be descriptive
5. **Don't ignore edge cases** - Preserve all error handling

## Tools to Use

**Primary Tool:**
```python
Task(
    subagent_type='code-refactor-agent',
    description='Refactor [function_name]',
    prompt='[Detailed refactoring instructions]',
    model='opus'  # Use Opus for complex refactoring
)
```

**Verification:**
```bash
# After each batch
uv run pytest tests/ -q --tb=no
uv run pytest tests/quality/test_complexity_regression.py -v
```

## Documentation to Update After Completion

When Phase 1 is complete (0 violations):

1. Update `PHASE1_REFACTORING_SUMMARY.md` with final metrics
2. Update `CODEBASE_ANALYSIS_REPORT.md` to reflect improvements
3. Create `PHASE1_COMPLETE_REPORT.md` with full details
4. Consider updating `README.md` with complexity improvements

---

**Last Session Achievement:** 16 functions refactored (33% progress)
**Next Session Goal:** Refactor top 10 functions (reach ~60% progress)
**Final Session Goal:** Complete remaining ~12-14 functions (100% ✅)

Good luck with the next session! 🚀
