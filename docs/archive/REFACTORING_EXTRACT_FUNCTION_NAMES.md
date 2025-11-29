# Refactoring: `_extract_function_names_from_code`

**Date:** 2025-11-28
**File:** `src/ast_grep_mcp/features/deduplication/impact.py`
**Function:** `_extract_function_names_from_code`

## Summary

Successfully refactored `_extract_function_names_from_code` to reduce cyclomatic complexity by 83.3% (24 → 4), bringing it well below the critical threshold of 20.

## Problem Statement

**Original Issue:**
- Cyclomatic complexity: 24 (20% over limit of 20)
- Large if-elif chain for language-specific pattern matching (6 branches)
- Complex nested conditionals in filtering logic
- Violation of complexity regression tests

## Refactoring Strategy

Applied three key patterns:

### 1. Configuration-Driven Design
Replaced language-specific if-elif chains with a configuration dictionary mapping languages to their regex patterns. This eliminated 5 conditional branches.

### 2. Extract Method
Broke down the monolithic function into three focused helpers:
- `_get_language_patterns()` - Pattern configuration lookup
- `_apply_extraction_patterns()` - Pattern execution
- `_filter_extracted_names()` - Name filtering and deduplication

### 3. Single Responsibility
Each helper function has one clear purpose, making the code easier to understand, test, and maintain.

## Implementation

### Before (24 cyclomatic complexity, 64 lines)
```python
def _extract_function_names_from_code(self, code: str, language: str) -> List[str]:
    names: List[str] = []
    if not code:
        return names

    lang = language.lower()

    # 6 language-specific if-elif branches
    if lang == "python":
        # Python pattern extraction
    elif lang in ("javascript", "typescript", "jsx", "tsx"):
        # JS/TS pattern extraction
    elif lang in ("java", "csharp", "cpp", "c"):
        # Java/C# pattern extraction
    elif lang == "go":
        # Go pattern extraction
    elif lang == "rust":
        # Rust pattern extraction

    # Complex filtering logic with nested conditionals
    filtered_names = []
    seen = set()
    common_words = {...}
    for name in names:
        if name and name not in seen and name.lower() not in common_words:
            seen.add(name)
            filtered_names.append(name)

    return filtered_names
```

### After (4 cyclomatic complexity, 19 lines)
```python
def _extract_function_names_from_code(self, code: str, language: str) -> List[str]:
    """Extract function/method/class names from code sample."""
    if not code:
        return []

    # Get language-specific patterns and extract names
    patterns = self._get_language_patterns(language.lower())
    names = self._apply_extraction_patterns(code, patterns)

    # Filter and deduplicate
    return self._filter_extracted_names(names)
```

### New Helper Functions

**1. `_get_language_patterns()` (4 cyclomatic, 61 lines)**
- Configuration dictionary with patterns for 11 languages
- Simple dictionary lookup, no branching logic
- Easy to extend with new languages

**2. `_apply_extraction_patterns()` (4 cyclomatic, 19 lines)**
- Applies regex patterns to extract names
- Handles MULTILINE flag for line-start patterns
- Clean iteration with no nesting

**3. `_filter_extracted_names()` (10 cyclomatic, 28 lines)**
- Filters common keywords
- Deduplicates names
- Uses early continue for clarity
- Still well below threshold (10 vs 20 limit)

## Results

### Complexity Metrics

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Cyclomatic Complexity | 24 | 4 | 83.3% |
| Cognitive Complexity | (estimated 20+) | 2 | 90%+ |
| Nesting Depth | (estimated 4-5) | 2 | 50%+ |
| Lines of Code | 64 | 19 | 70.3% |

### All Helper Functions Well Below Thresholds

| Function | Cyclomatic | Cognitive | Nesting | Lines |
|----------|-----------|-----------|---------|-------|
| `_extract_function_names_from_code` | 4 | 2 | 2 | 19 |
| `_get_language_patterns` | 4 | 2 | 3 | 61 |
| `_apply_extraction_patterns` | 4 | 2 | 2 | 19 |
| `_filter_extracted_names` | 10 | 14 | 3 | 28 |
| **Critical Thresholds** | **≤20** | **≤30** | **≤6** | **≤150** |

### Test Results

**All tests passing:**
- ✅ 34/34 deduplication tests pass
- ✅ Behavior maintained (exact same output)
- ✅ Removed from complexity violation list
- ✅ Complexity regression tests improved (48 → 31 violations remaining)

## Benefits

1. **Maintainability**: Clear separation of concerns makes code easier to understand
2. **Extensibility**: Adding new languages only requires updating the configuration dictionary
3. **Testability**: Each helper function can be tested independently
4. **Readability**: Main function reads like documentation
5. **Compliance**: Meets all critical complexity thresholds

## Pattern Recognition

This refactoring demonstrates a common anti-pattern and its solution:

**Anti-pattern:** Large if-elif chains for type/language/category-specific logic
**Solution:** Configuration-driven design with data structures + helper functions

This pattern is applicable to other functions in the codebase with similar structures.

## Related Work

This refactoring is part of Phase 1 Complexity Reduction effort:
- See: `PHASE1_REFACTORING_SUMMARY.md`
- Progress: 33% complete (48 → 31 violations)
- Next targets: Functions with cognitive complexity > 40

## Lessons Learned

1. **Configuration over conditionals**: Dictionary lookup eliminates branching
2. **Extract method aggressively**: Small, focused functions are easier to reason about
3. **Early returns**: Simplify control flow with guard clauses
4. **Preserve behavior**: All tests must pass before considering refactoring complete
5. **Measure improvement**: Quantitative metrics validate the refactoring success
