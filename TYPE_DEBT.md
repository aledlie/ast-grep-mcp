# Type Debt Tracking

This document tracks remaining type errors (mypy) and lint errors (ruff) for future cleanup.

**Last Updated:** 2025-12-03
**Total Mypy Errors:** 0 ✅
**Total Ruff Errors:** 75

---

## Summary

| Category | Count | Priority | Notes |
|----------|-------|----------|-------|
| Mypy: no-any-return | ~13 | Medium | Functions returning `Any` instead of declared types |
| Mypy: no-untyped-def | 0 | ✅ FIXED | Missing type annotations on functions |
| Mypy: arg-type | ~8 | High | Incompatible argument types |
| Mypy: assignment | ~4 | Medium | PEP 484 implicit Optional issues |
| Mypy: return-value | ~4 | High | Incompatible return value types |
| Mypy: misc | ~4 | Low | Various issues (unexpected syntax, etc.) |
| Mypy: call-arg | ~3 | High | Wrong number of arguments |
| Mypy: no-untyped-call | ~3 | Low | Calls to untyped functions |
| Mypy: dict-item | ~2 | Medium | Dict type mismatches |
| Ruff: E501 line-too-long | 40 | Low | Lines > 140 chars |
| Ruff: E741 ambiguous-variable-name | 22 | Low | Variables named `l`, `O`, `I` |
| Ruff: N806 non-lowercase-variable | 12 | Low | CamelCase in function scope |
| Ruff: F841 unused-variable | 5 | Low | Variables defined but not used |
| Ruff: E731 lambda-assignment | 3 | Low | Lambda assigned to variable |
| Ruff: N812 lowercase-as-non-lowercase | 1 | Low | Import naming |

---

## Mypy Errors by File

### High Priority (arg-type, return-value, call-arg)

#### `features/deduplication/recommendations.py`
- Line 213-214: `arg-type` - Object being passed where float/list expected
  ```python
  # TODO(type-debt): Fix argument types to _calculate_strategy_score
  # base_score and rules need proper type assertions
  ```

#### `features/cross_language/binding_generator.py`
- Line 209: `return-value` - Wrong tuple types returned
- Lines 302, 428, 509: `arg-type` - list[str] passed where list[tuple] expected
  ```python
  # TODO(type-debt): Fix _python_param_string signature or call sites
  # Mismatch between list[str] and list[tuple[str, str, bool]]
  ```

#### `features/deduplication/impact.py`
- Line 746-750: `return-value` - tuple[str, object] vs tuple[str, list[str]]
- Line 746: `operator` - Unsupported <= comparison with object
  ```python
  # TODO(type-debt): Add type assertions for config dict accesses
  ```

#### `features/deduplication/analysis_orchestrator.py`
- Lines 612, 653: `call-arg` - Wrong number of arguments
- Lines 841, 877: `arg-type` - Callable signature mismatch
  ```python
  # TODO(type-debt): Fix _parallel_enrich function signatures
  ```

#### `features/deduplication/generator.py`
- Line 162: `call-arg` - Too many arguments for _generate_generic_function
  ```python
  # TODO(type-debt): Update _generate_generic_function signature
  ```

### Medium Priority (no-any-return, no-untyped-def, assignment, dict-item)

#### `features/complexity/metrics.py`
- Line 255: `no-any-return` - Returning Any from list[str] function

#### `features/deduplication/generator.py`
- Lines 28, 37: `dict-item` - Dict entry type mismatch (str: bool vs str: str)
- Lines 325, 327: `no-any-return`
- Line 113: `no-untyped-def`

#### `features/deduplication/coverage.py`
- Line 689: `no-untyped-def`
- Line 700: `no-any-return`

#### `features/cross_language/binding_generator.py`
- Lines 84, 164, 168, 173: `no-any-return`
- Line 184: `valid-type` - Should use typing.Callable not builtin callable
- Line 197: `misc` - callable? not callable

#### `features/schema/client.py`
- Line 65: `no-any-return`
- Line 186: `no-untyped-call`

#### `features/documentation/readme_generator.py`
- Line 178: `arg-type` - Overloaded function vs expected Callable

#### `features/documentation/api_docs_generator.py`
- Line 666: `attr-defined` - Object has no attribute parse_file

#### `features/documentation/sync_checker.py`
- (All PEP 484 Optional issues fixed)

#### `features/documentation/tools.py`
- Lines 278, 691: `no-untyped-def`
- Line 738: `no-untyped-call`

#### `features/deduplication/applicator.py`
- Line 84: `no-any-return`

#### `features/deduplication/impact.py`
- Line 455: `no-any-return`

#### `features/rewrite/service.py`
- Line 138: `no-untyped-call`

#### `features/refactoring/renamer.py`
- Line 171: `no-untyped-call`
- Line 175: `no-untyped-def`

#### `features/quality/security_scanner.py`
- Line 699: `arg-type` - Object vs dict expected

#### `features/quality/tools.py`
- Lines 556, 557: `no-any-return`
- Line 1053: `no-untyped-def`
- Line 1161: `no-untyped-call`

#### `features/cross_language/tools.py`
- Lines 28, 38, 51, 63, 68, 78, 93: `no-untyped-def`
- Line 697: `no-untyped-def`
- Line 742: `no-untyped-call`

### Low Priority (misc)

#### `features/deduplication/analyzer.py`
- Line 558: `no-untyped-call`

#### `features/deduplication/analysis_orchestrator.py`
- Lines 585, 630, 666: `misc` - Unexpected "..."
- Line 663: `no-untyped-def`

---

## Ruff Errors by Category

### E501 line-too-long (40 errors)
These are in documentation strings, long template patterns, and config descriptions.
Most are intentionally long for readability. Consider adding `# noqa: E501` where appropriate.

**Files with most E501 errors:**
- `features/cross_language/pattern_database.py` - Template strings
- `features/deduplication/*.py` - Config descriptions
- `core/config.py` - Help text

### E741 ambiguous-variable-name (22 errors)
Variables using `l`, `O`, or `I` which can be confused with `1`, `0`.

**Recommendation:** Rename to more descriptive names:
- `l` -> `length`, `line`, `items`
- `O` -> `output`, `object_val`
- `I` -> `index`, `item`

### N806 non-lowercase-variable-in-function (12 errors)
CamelCase variables inside functions (common in config dicts and constants).

**Recommendation:** Either rename to snake_case or add `# noqa: N806` if intentional.

### F841 unused-variable (5 errors)
Variables assigned but never used.

**Recommendation:** Remove or prefix with `_` if intentionally ignored.

### E731 lambda-assignment (3 errors)
Lambda expressions assigned to variables instead of using `def`.

**Files:**
- `features/cross_language/binding_generator.py:295,419,501`

**Recommendation:** Convert to regular functions:
```python
# Before
type_converter = lambda t: OPENAPI_TO_PYTHON.get(t, "Any")

# After
def type_converter(t: str) -> str:
    return OPENAPI_TO_PYTHON.get(t, "Any")
```

### N812 lowercase-imported-as-non-lowercase (1 error)
Import alias doesn't follow naming convention.

---

## Detailed `no-untyped-def` Analysis (15 errors)

Investigation completed 2025-12-03. All 15 errors categorized with fixes:

### Formatter Functions - cross_language/tools.py (8 errors)

Missing parameter types for internal formatter functions:

| Line | Function | Fix |
|------|----------|-----|
| 28 | `_format_example(ex)` | `ex: PatternExample` |
| 38 | `_format_equivalence(e)` | `e: PatternEquivalence` |
| 51 | `_format_equivalents_result(result)` | `result: LanguageEquivalentsResult` |
| 63 | `_format_type_mapping(t)` | `t: TypeMapping` |
| 68 | `_format_warning(w)` | `w: ConversionWarning` |
| 78 | `_format_conversion(c)` | `c: CodeConversion` |
| 93 | `_format_conversion_result(result)` | `result: CodeConversionResult` |
| 697 | `_create_mcp_field_definitions()` | Return: `Dict[str, Dict[str, Field]]` |

### MCP Field Definition Functions (3 errors)

All missing return type annotations:

| File | Line | Fix |
|------|------|-----|
| `documentation/tools.py` | 691 | `-> Dict[str, Dict[str, Field]]` |
| `quality/tools.py` | 1053 | `-> Dict[str, Dict[str, Field]]` |
| `cross_language/tools.py` | 697 | (included above) |

### **kwargs Type Annotations (2 errors)

| File | Line | Function | Fix |
|------|------|----------|-----|
| `generator.py` | 113 | `_generate_generic_function` | `**kwargs: Any` |
| `analysis_orchestrator.py` | 663 | `_parallel_enrich` | `**kwargs: Any` |

### Other Missing Types (3 errors)

| File | Line | Function | Fix |
|------|------|----------|-----|
| `documentation/tools.py` | 278 | `_format_route_for_output(route)` | `route: ApiRoute` |
| `coverage.py` | 689 | `_get_future_result(self, future, ...)` | `future: Future[bool]` |
| `renamer.py` | 175 | `_get_language_classifier(self)` | Return: `Optional[Callable[[ReferenceInfo, Dict], None]]` |

---

## Action Items

### Quick Wins (Completed)
1. ~~**Fix PEP 484 implicit Optional** (4 errors in sync_checker.py, readme_generator.py)~~ ✅ DONE
2. ~~**Fix E731 lambda-assignment** (3 errors in binding_generator.py)~~ ✅ DONE
3. ~~**Fix valid-type error** (1 error in binding_generator.py)~~ ✅ Already correct

### Medium Effort
1. ~~**Add type annotations** to functions in tools.py (10+ functions missing annotations)~~ ✅ DONE
2. **Fix return type mismatches** in binding_generator.py
3. **Add type assertions** for config dict accesses

### Requires Design Review (All Resolved)
1. ~~**_parallel_enrich signature**~~ ✅ Already uses correct `Callable[..., None]` syntax
2. ~~**_python_param_string**~~ ✅ False positive - type flow is correct
3. ~~**Executor.submit calls**~~ ✅ False positive - all calls match signatures

---

## Ignoring Intentional Issues

Some errors are intentional and can be ignored via configuration:

### pyproject.toml (ruff)
```toml
[tool.ruff.lint]
ignore = [
    "E501",   # Line too long (handled by formatter)
    "E741",   # Ambiguous variable name (context-dependent)
    "N806",   # Non-lowercase variable (config patterns)
]
```

### pyproject.toml (mypy)
```toml
[tool.mypy]
disable_error_code = [
    "no-any-return",    # Too strict for dynamic code
    "no-untyped-call",  # Calls to untyped third-party code
]
```

---

## Progress Log

| Date | Action | Errors Before | Errors After |
|------|--------|---------------|--------------|
| 2025-12-03 | Fixed type-arg (4) and var-annotated (9) errors | 77 mypy | 64 mypy |
| 2025-12-03 | Created TYPE_DEBT.md tracking | - | - |
| 2025-12-03 | Fixed E731 lambda-assignment (3) + valid-type (1) in binding_generator.py | 83 ruff | 79 ruff |
| 2025-12-03 | Fixed all no-any-return errors (14) across 9 files | 64 mypy | 50 mypy |
| 2025-12-03 | Fixed all arg-type/call-arg errors (12) across 6 files | 50 mypy | 32 mypy |
| 2025-12-03 | Fixed all F841 unused-variable errors (5) across 5 files | 79 ruff | 75 ruff |
| 2025-12-03 | Fixed PEP 484 implicit Optional (4) in sync_checker.py, readme_generator.py | 32 mypy | 28 mypy |
| 2025-12-03 | Investigated "Design Review" items - all 3 already resolved/false positives | - | - |
| 2025-12-03 | Fixed all no-untyped-def errors (15) + removed redundant cast | 28 mypy | 9 mypy |
| 2025-12-03 | Fixed impact.py TypedDict for risk_levels config (3 errors) | 9 mypy | 6 mypy |
| 2025-12-03 | Fixed no-untyped-call in analyzer.py, client.py, service.py (typed lambda dicts) | 6 mypy | 3 mypy |
| 2025-12-03 | Fixed attr-defined in api_docs_generator.py (RouteParser Protocol) | 3 mypy | 2 mypy |
| 2025-12-03 | Fixed dict-item in generator.py (Union[str, bool] for TYPE_INFERENCE_CONFIG) | 2 mypy | 0 mypy |
