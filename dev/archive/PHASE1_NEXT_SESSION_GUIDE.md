# Phase 1 Refactoring - Next Session Quick Guide

**Current Status:** 19/48 violations remaining (60% complete) ✅
**Last Updated:** 2025-11-28 22:55 PST (Session 2 Complete)
**Latest Commit:** `ddf8b0e` - refactor(smells): reduce _extract_classes complexity by 82%

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

### Critical (Cognitive Complexity >30)

1. **schema/client.py:initialize**
   - Cognitive: 34 (13% over limit)
   - Strategy: Extract schema type initialization, separate HTTP client setup
   - Estimated time: 15-20 minutes

2. **refactoring/renamer.py:_classify_reference**
   - Cognitive: 33 (10% over limit)
   - Strategy: Extract classification rules to configuration-driven approach
   - Estimated time: 15-20 minutes

3. **quality/enforcer.py:load_rule_set**
   - Cognitive: 32 (7% over limit)
   - Strategy: Extract rule loading logic, simplify conditional chains
   - Estimated time: 10-15 minutes

### High Priority (Cyclomatic >22 or Lines >160)

4. **complexity/tools.py:analyze_complexity_tool**
   - Lines: 174 (16% over limit)
   - Strategy: Extract parameter processing and result formatting helpers
   - Estimated time: 15-20 minutes

5. **deduplication/generator.py:_infer_parameter_type**
   - Cyclomatic: 24 (20% over limit)
   - Strategy: Configuration-driven type inference with mapping dictionary
   - Estimated time: 15-20 minutes

6. **deduplication/applicator_post_validator.py:_suggest_syntax_fix**
   - Cyclomatic: 24 (20% over limit)
   - Strategy: Extract fix suggestion rules, reduce conditional nesting
   - Estimated time: 15-20 minutes

7. **refactoring/analyzer.py:_classify_variable_types**
   - Cyclomatic: 24 (20% over limit)
   - Strategy: Configuration-driven classification with pattern matching
   - Estimated time: 15-20 minutes

8. **deduplication/impact.py:_extract_function_names_from_code**
   - Cyclomatic: 24 (20% over limit)
   - Strategy: Extract language-specific parsing logic
   - Estimated time: 15-20 minutes

### Medium Priority (Minor violations 5-20% over)

9. **deduplication/generator.py:generate_extracted_function**
   - Cyclomatic: 23 (15% over limit)
   - Strategy: Extract template variable substitution
   - Estimated time: 10-15 minutes

10. **deduplication/generator.py:substitute_template_variables**
    - Cyclomatic: 22 (10% over limit)
    - Strategy: Configuration-driven variable substitution
    - Estimated time: 10-15 minutes

**Total Estimated Time for Top 10:** ~2.5 hours

## Remaining 9 Functions (Lower Priority)

After completing the top 8, tackle these remaining functions:

### Deduplication Module (3 more)
- `_suggest_syntax_fix` (applicator_validator) - cyclomatic=23
- `apply_deduplication` (applicator) - cyclomatic=21
- `substitute_template_variables` (generator) - cyclomatic=22

### Quality/Complexity Tools (3 more)
- `enforce_standards_tool` (quality/tools) - cyclomatic=22
- `detect_code_smells_tool` (complexity/tools) - cyclomatic=22
- `register_search_tools` (search/tools) - lines=158

### Search/Refactoring (2 more)
- `find_code_impl` (search/service) - cyclomatic=22
- `extract_function_tool` (refactoring/tools) - cyclomatic=21

### Utils/Templates (2 more)
- `format_typescript_function` (utils/templates) - nesting=7
- `format_javascript_function` (utils/templates) - nesting=7

**Total Remaining Estimated Time:** ~1.5 hours

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
