# Phase 2B Quick Reference

**Status:** ✅ Complete | **Lines:** 359 (18849-19207) | **Functions:** 9

## Function Overview

```
Violation Parsing (2)
├── _parse_match_to_violation()  - Convert ast-grep match to RuleViolation
└── _should_exclude_file()       - Check file against exclusion patterns

Rule Execution (2)
├── _execute_rule()              - Execute single rule, return violations
└── _execute_rules_batch()       - Parallel execution with ThreadPoolExecutor

Grouping (3)
├── _group_violations_by_file()     - Group by file path, sort by line
├── _group_violations_by_severity() - Group into error/warning/info
└── _group_violations_by_rule()     - Group by rule ID

Filtering & Reporting (2)
├── _filter_violations_by_severity() - Filter by minimum severity
└── _format_violation_report()       - Generate 80-char text report
```

## Key Features

**Thread Safety:**
- `threading.Lock` protects shared violations list
- Safe for parallel rule execution

**Performance:**
- Parallel execution via ThreadPoolExecutor
- Early termination on max_violations
- Streaming results from ast-grep

**Monitoring:**
- Sentry spans for each rule execution
- Exception capturing with rule context
- Structured logging throughout

**Error Handling:**
- Individual rule failures don't fail scan
- Graceful degradation (returns empty list)
- Comprehensive logging

## Usage Pattern

```python
# 1. Create context
context = RuleExecutionContext(
    project_folder="/path",
    language="python",
    max_threads=4,
    max_violations=1000,
    exclude_patterns=["**/node_modules/**"],
    logger=logger
)

# 2. Load rules (Phase 2A)
rule_set = _load_rule_set("python-best-practices", config)

# 3. Execute rules (Phase 2B)
violations = _execute_rules_batch(rule_set.rules, context)

# 4. Group/filter results
by_file = _group_violations_by_file(violations)
by_severity = _group_violations_by_severity(violations)
errors = _filter_violations_by_severity(violations, "error")

# 5. Generate report
result = EnforcementResult(...)
report = _format_violation_report(result)
```

## Next: Phase 2C

Phase 2C implements the public `enforce_code_standards()` MCP tool that wraps all Phase 2A/2B functionality.

**See:** PHASE-2B-IMPLEMENTATION.md for full details
