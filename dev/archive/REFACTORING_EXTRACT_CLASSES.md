# Refactoring Summary: `_extract_classes`

**Date:** 2025-11-28
**File:** `src/ast_grep_mcp/features/quality/smells_detectors.py`
**Function:** `_extract_classes` (LargeClassDetector)

## Overview

Refactored `_extract_classes` to reduce complexity following Phase 1 patterns. Successfully reduced cognitive complexity by 94% and nesting depth by 71%.

## Metrics

### Before Refactoring
- **Cognitive Complexity:** 35 (17% over limit of 30)
- **Nesting Depth:** 7 (17% over limit of 6)
- **Status:** CRITICAL VIOLATION

### After Refactoring
- **Cyclomatic Complexity:** 2 (90% below limit)
- **Cognitive Complexity:** 2 (93% below limit)
- **Nesting Depth:** 2 (67% below limit)
- **Function Length:** 10 lines (93% below limit)
- **Status:** ✅ COMPLIANT

### Improvements
- **Cognitive:** 35 → 2 (94% reduction)
- **Nesting:** 7 → 2 (71% reduction)
- **Violation Count:** 22 → 21 functions (4.5% progress)

## Refactoring Strategy

Applied Extract Method pattern to break down the monolithic function into focused helpers:

### 1. Configuration Extraction
**Helper:** `_get_class_pattern(language)`
- Extracts language-specific pattern lookup
- **Metrics:** cyclomatic=3, cognitive=0, nesting=2

### 2. AST-Grep Execution
**Helper:** `_run_ast_grep_for_classes(file_path, language, pattern)`
- Handles subprocess execution and JSON parsing
- Implements early returns for failed/empty results
- **Metrics:** cyclomatic=6, cognitive=3, nesting=2

### 3. Match Processing
**Helper:** `_process_class_matches(matches, language)`
- Iterates through matches and delegates to info extraction
- Clean separation between iteration and processing
- **Metrics:** cyclomatic=2, cognitive=2, nesting=2

### 4. Class Information Extraction
**Helper:** `_extract_class_info(match, language)`
- Orchestrates extraction of name, line range, and method count
- **Metrics:** cyclomatic=3, cognitive=1, nesting=2

### 5. Name Extraction
**Helper:** `_extract_class_name(match)`
- Handles both dict and string metavariable formats
- Type-safe with explicit str conversion
- **Metrics:** cyclomatic=8, cognitive=6, nesting=2

### 6. Line Range Extraction
**Helper:** `_extract_line_range(match)`
- Extracts and adjusts line numbers (0-indexed → 1-indexed)
- **Metrics:** cyclomatic=2, cognitive=1, nesting=2

### 7. Method Counting
**Helper:** `_count_methods_in_class(code, language)`
- Language-specific regex patterns for method detection
- **Metrics:** cyclomatic=2, cognitive=2, nesting=2

## Code Structure

### Original (58 lines, deeply nested)
```python
def _extract_classes(self, file_path: str, language: str) -> List[Dict[str, Any]]:
    classes: List[Dict[str, Any]] = []
    class_patterns = {...}
    pattern = class_patterns.get(language.lower(), ...)
    try:
        result = subprocess.run(...)
        if result.returncode == 0 and result.stdout.strip():
            matches = json.loads(result.stdout)
            if isinstance(matches, list):
                for match in matches:
                    # Extract class name (nested conditionals)
                    cls_name = "unknown"
                    meta_vars = match.get("metaVariables", {})
                    if "NAME" in meta_vars:
                        name_data = meta_vars["NAME"]
                        if isinstance(name_data, dict):
                            cls_name = name_data.get("text", "unknown")
                        elif isinstance(name_data, str):
                            cls_name = name_data
                    # Get line numbers
                    range_info = match.get("range", {})
                    start_line = range_info.get("start", {}).get("line", 0) + 1
                    end_line = range_info.get("end", {}).get("line", 0) + 1
                    # Count methods (language-specific)
                    code = match.get("text", "")
                    method_count = 0
                    if language.lower() == "python":
                        method_count = len(re.findall(...))
                    else:
                        method_count = len(re.findall(...))
                    classes.append({...})
    except Exception as e:
        self.logger.warning(...)
    return classes
```

### Refactored (10 lines main function + 7 helpers)
```python
def _extract_classes(self, file_path: str, language: str) -> List[Dict[str, Any]]:
    """Extract all classes from a file using ast-grep."""
    pattern = self._get_class_pattern(language)
    try:
        matches = self._run_ast_grep_for_classes(file_path, language, pattern)
        return self._process_class_matches(matches, language)
    except Exception as e:
        self.logger.warning("extract_classes_failed", file=file_path, error=str(e))
        return []
```

## Key Patterns Applied

1. **Extract Method** - 7 focused helpers from 1 monolithic function
2. **Early Returns** - Guard clauses in `_run_ast_grep_for_classes` reduce nesting
3. **Single Responsibility** - Each helper has one clear purpose
4. **Type Safety** - Explicit type conversions to satisfy mypy
5. **Configuration-Driven** - Pattern dictionary centralized in `_get_class_pattern`

## Testing

All tests pass with zero behavioral changes:

```bash
# Unit tests (27 tests)
uv run pytest tests/unit/test_code_smells.py -v
# Result: 27 passed

# Complexity regression test
uv run pytest tests/quality/test_complexity_regression.py::TestComplexityTrends::test_no_functions_exceed_critical_thresholds -v
# Result: 22 → 21 violations

# Type checking
uv run mypy src/ast_grep_mcp/features/quality/smells_detectors.py
# Result: Success: no issues found

# Linting
uv run ruff check src/ast_grep_mcp/features/quality/smells_detectors.py
# Result: All checks passed
```

## Reusable Pattern

This refactoring establishes a reusable pattern for similar functions:

1. **Identify responsibilities** in the original function
2. **Extract configuration** (patterns, thresholds) to separate method
3. **Extract subprocess execution** with early returns
4. **Extract result processing** into pipeline of helpers
5. **Extract field extraction** into focused accessors
6. **Extract business logic** (e.g., method counting) to language-specific helpers

**Next Target:** `_extract_classes_from_file` in `complexity/analyzer.py` (cognitive=35, nesting=7) can use this exact pattern.

## Files Modified

- `src/ast_grep_mcp/features/quality/smells_detectors.py`

## Related Work

- Phase 1 Complexity Refactoring (see PHASE1_REFACTORING_SUMMARY.md)
- Sibling function: `_extract_classes_from_file` (next priority)
- Part of 22 → 0 violations goal

## Success Criteria

- ✅ Maintain exact same behavior
- ✅ All tests pass (27/27)
- ✅ Zero behavioral regressions
- ✅ Cognitive complexity reduced by >14% (achieved 94%)
- ✅ Nesting depth reduced by >14% (achieved 71%)
- ✅ All helpers below thresholds
- ✅ Type checking passes
- ✅ Linting passes
