# Duplicate Detector False Positives (2026-03-08)

Investigation of 5 duplicate groups reported by `find_duplication` (sim >= 0.82). All are false positives or low-value for refactoring.

## Group 1 (sim=0.84): `models/refactoring.py:75-82` vs `:84-91`

`to_python_signature()` and `to_typescript_signature()` — intentionally parallel language-specific formatters. Same params/ret/async_prefix structure, different output format (`def` vs `function`). Not duplicates.

## Group 2 (sim=0.82): `utils/console_logger.py:131-140` vs `:142-151`

`error()` and `warning()` — thin wrappers that delegate to shared `_log_to_stderr()` with different prefixes. Already deduplicated; the methods exist for semantic API.

## Group 3 (sim=0.84): `core/usage_tracking.py:336-341` vs `:344-349`

`_db_calls_by_tool()` and `_db_calls_by_operation()` — same 6-line query pattern differing only in `GROUP BY` column. Parameterizing would introduce a dynamic column name in SQL (mild injection smell for negligible savings).

## Group 4 (sim=0.93): `refactoring/extractor.py:27-33` vs `renamer.py:29-35`

Identical `__init__(self, language: str)` doing `self.language = language`. Trivial one-liner constructor on unrelated classes (`FunctionExtractor`, `SymbolRenamer`). A shared base class for this would be over-engineering.

## Group 5 (sim=0.89): `quality/smells_detectors.py:83-91`, `:121-129`, `:195-203`

Three `detect()` methods on `LongFunctionDetector`, `ParameterBloatDetector`, `DeepNestingDetector`. All follow the same pattern:

```python
rel_path = str(Path(file_path).relative_to(project_path))
try:
    funcs = extract_functions_from_file(file_path, language)
    return [s for s in (self._check_func(f, rel_path, ...) for f in funcs) if s]
except Exception as e:
    self.logger.warning("detection_failed", file=file_path, error=str(e))
    return []
```

Only candidate worth considering — could lift to a template method on `SmellDetector` base class. However, ~18 lines saved with added indirection, and a minor signature mismatch (`_check_func` with/without `language` arg). Low priority.

## Patterns Causing False Positives

1. **Trivial constructors** — `__init__` that only assigns `self.language` flagged across unrelated classes
2. **Intentionally parallel APIs** — language-specific formatters (Python/TypeScript) with matching structure
3. **Thin semantic wrappers** — `error()`/`warning()` delegating to a shared method
4. **Small private helpers** — 6-line functions with similar SQL structure but different column names
5. **Strategy pattern implementations** — subclasses implementing an abstract method with shared boilerplate

## Recommended Detector Improvements

- Exclude `__init__` methods under N lines (e.g., 10) from duplicate detection
- Discount similarity for methods that delegate to a shared helper (already deduplicated)
- Reduce weight for strategy/template pattern implementations sharing abstract method boilerplate
- Add minimum line savings threshold (e.g., 20+ lines) before reporting
- Consider excluding dataclass/model `to_*` methods with parallel structure
