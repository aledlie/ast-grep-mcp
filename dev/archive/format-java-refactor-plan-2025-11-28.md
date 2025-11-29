# format_java_code Refactoring Plan
**Date:** 2025-11-28
**Target Function:** `src/ast_grep_mcp/utils/templates.py::format_java_code` (lines 80-204)
**Status:** ✅ COMPLETE
**Commit:** `a16fce2` - refactor(utils): extract java code formatting into focused functions

## Executive Summary
Refactor the `format_java_code` function to reduce complexity from 39 cyclomatic/60 cognitive to ≤20/≤30 by extracting distinct responsibilities into focused helper functions.

## Current State Analysis

### Metrics
- **Cyclomatic Complexity:** 39 (95% over limit of 20)
- **Cognitive Complexity:** 60 (100% over limit of 30)
- **Function Length:** 125 lines
- **Nesting Depth:** 4 levels

### Code Structure
The function has three distinct responsibilities interleaved:
1. **External Formatter Execution** (lines 97-122): Attempts to use google-java-format
2. **Import Processing** (lines 132-174): Separates and sorts import statements
3. **Indentation/Brace Formatting** (lines 176-204): Applies consistent indentation

### Identified Issues
**Critical:**
- Cyclomatic complexity nearly double the threshold
- Cognitive complexity double the threshold
- Multiple responsibilities violating SRP

**Major:**
- Deep nesting in import processing logic
- Complex control flow with multiple state variables
- Difficult to test individual formatting rules

## Proposed Refactoring Plan

### Phase 1: Extract Helper Functions

#### 1. _try_google_java_format
```python
def _try_google_java_format(code: str) -> Optional[str]:
    """Try to format Java code using google-java-format.

    Args:
        code: Java source code to format

    Returns:
        Formatted code if successful, None if tool unavailable or error
    """
```
**Responsibility:** Execute external formatter with temp file handling
**Complexity Reduction:** -8 cyclomatic, -12 cognitive

#### 2. _process_java_imports
```python
def _process_java_imports(lines: list[str]) -> tuple[list[str], list[str]]:
    """Separate and sort Java import statements.

    Args:
        lines: Raw code lines

    Returns:
        Tuple of (sorted_import_lines, non_import_lines)
    """
```
**Responsibility:** Extract and sort imports by Java conventions
**Complexity Reduction:** -12 cyclomatic, -20 cognitive

#### 3. _apply_java_indentation
```python
def _apply_java_indentation(lines: list[str]) -> str:
    """Apply consistent indentation and brace formatting.

    Args:
        lines: Code lines to format

    Returns:
        Formatted code string with proper indentation
    """
```
**Responsibility:** Handle brace matching and indentation levels
**Complexity Reduction:** -10 cyclomatic, -15 cognitive

#### 4. _merge_package_imports_code
```python
def _merge_package_imports_code(
    import_lines: list[str],
    non_import_lines: list[str]
) -> list[str]:
    """Merge package declaration, imports, and code with proper spacing.

    Args:
        import_lines: Sorted import statements
        non_import_lines: Package declaration and code

    Returns:
        Merged lines with proper spacing
    """
```
**Responsibility:** Reconstruct code with imports in correct position
**Complexity Reduction:** -5 cyclomatic, -8 cognitive

### Phase 2: Refactor Main Function

```python
def format_java_code(code: str) -> str:
    """Format Java code using google-java-format or basic formatting fallback."""
    # Try external formatter first
    formatted = _try_google_java_format(code)
    if formatted is not None:
        return formatted

    # Fall back to basic formatting
    lines = code.split('\n')
    import_lines, non_import_lines = _process_java_imports(lines)
    all_lines = _merge_package_imports_code(import_lines, non_import_lines)
    return _apply_java_indentation(all_lines)
```
**Target Metrics:**
- Cyclomatic: 2 (well under 20)
- Cognitive: 3 (well under 30)
- Lines: ~12 (well under 100)

## Risk Assessment & Mitigation

### Risks
1. **Behavior Changes:** Helper extraction could alter formatting
   - **Mitigation:** Preserve exact logic, add comprehensive tests

2. **Import Order Changes:** Sorting logic might differ
   - **Mitigation:** Copy exact sort key function

3. **Whitespace Differences:** Line joining might change
   - **Mitigation:** Preserve exact '\n'.join() patterns

## Testing Strategy
1. Create snapshot tests with current output before refactoring
2. Test each helper in isolation
3. Verify main function produces identical output
4. Run full test suite to catch regressions

## Success Metrics
- [x] Cyclomatic complexity ≤ 20 (achieved: 7)
- [x] Cognitive complexity ≤ 30 (achieved: ~3)
- [x] Main function < 30 lines (achieved: 26 lines)
- [x] Each helper < 50 lines (all helpers 31-41 lines)
- [x] All existing tests pass (verified)
- [x] No behavior changes (verified)

## Implementation Order
1. Create helper function signatures
2. Extract _try_google_java_format (simplest, most isolated)
3. Extract _process_java_imports (complex but well-defined)
4. Extract _merge_package_imports_code (simple merging logic)
5. Extract _apply_java_indentation (formatting rules)
6. Refactor main function
7. Verify tests pass

## Complete Dependency Map
**Importers of format_java_code:**
- `src/ast_grep_mcp/utils/formatters.py` - Uses for Java formatting
- `src/ast_grep_mcp/utils/__init__.py` - Re-exports function
- `main.py` - Re-exports for backward compatibility

**No breaking changes:** Function signature remains identical

## Completion Summary (2025-11-28)

### Refactoring Results

**Before Refactoring:**
- Cyclomatic complexity: 39 (95% over limit)
- Cognitive complexity: 60 (100% over limit)
- Function length: 125 lines
- Single monolithic function with 3 interleaved responsibilities

**After Refactoring:**
- Main function cyclomatic: 7 (65% below limit) ✅
- Main function cognitive: ~3 (90% below limit) ✅
- Main function length: 26 lines (79% reduction) ✅
- 4 focused helper functions with single responsibilities

### Extracted Helper Functions

1. **_try_google_java_format** (39 lines)
   - Cyclomatic: 13, Cognitive: ~4
   - Handles external formatter execution with temp file management

2. **_process_java_imports** (41 lines)
   - Cyclomatic: 20, Cognitive: ~25
   - Separates and sorts import statements by Java conventions

3. **_merge_package_imports_code** (31 lines)
   - Cyclomatic: 10, Cognitive: ~13
   - Merges package, imports, and code with proper spacing

4. **_apply_java_indentation** (40 lines)
   - Cyclomatic: 12, Cognitive: ~15
   - Applies consistent indentation and brace formatting

### Key Improvements

- **Separation of Concerns:** Each helper has a single, clear responsibility
- **Testability:** Functions can now be tested in isolation
- **Readability:** Main function is now a simple orchestrator
- **Maintainability:** Changes to formatting rules isolated to specific helpers
- **No Breaking Changes:** External API remains identical
- **All Tests Pass:** Verified no behavior changes

### Files Modified

- `/Users/alyshialedlie/code/ast-grep-mcp/src/ast_grep_mcp/utils/templates.py`
  - Lines affected: 80-264 (refactored region)
  - Net change: +60 lines (due to docstrings and better organization)