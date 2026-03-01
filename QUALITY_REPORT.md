# Code Quality Report: ast-grep-mcp

**Generated:** 2026-03-01 14:46:55
**Execution Time:** 78ms
**Files Scanned:** 4

---

## Summary

- **Total Violations:** 96
- **Error:** 0
- **Warning:** 96
- **Info:** 0
- **Files with Violations:** 4
- **Rules Executed:** 3

---

## Violations by Severity

### WARNING (96)

#### `no-print-production` (96 occurrences)
- **health_check.py:286** - Use proper logging instead of print()
- **health_check.py:287** - Use proper logging instead of print()
- **health_check.py:288** - Use proper logging instead of print()
- **health_check.py:293** - Use proper logging instead of print()
- **health_check.py:297** - Use proper logging instead of print()
- **health_check.py:299** - Use proper logging instead of print()
- **health_check.py:301** - Use proper logging instead of print()
- **health_check.py:302** - Use proper logging instead of print()
- **health_check.py:305** - Use proper logging instead of print()
- **health_check.py:308** - Use proper logging instead of print()
  - *...and 86 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `no-print-production` | 96 | warning |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `migration.py` | 65 | 0 | 65 | 0 |
| `timeline_api.py` | 14 | 0 | 14 | 0 |
| `health_check.py` | 12 | 0 | 12 | 0 |
| `cost_integration.py` | 5 | 0 | 5 | 0 |

---

## Recommendations

- **96 warnings** should be addressed

**💡 96 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.