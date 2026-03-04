# Code Quality Report: ast-grep-mcp

**Generated:** 2026-03-01 15:10:14
**Execution Time:** 75ms
**Files Scanned:** 3

---

## Summary

- **Total Violations:** 27
- **Error:** 0
- **Warning:** 27
- **Info:** 0
- **Files with Violations:** 3
- **Rules Executed:** 3

---

## Violations by Severity

### WARNING (27)

#### `no-print-production` (27 occurrences)
- **health_check.py:288** - Use proper logging instead of print()
- **health_check.py:289** - Use proper logging instead of print()
- **health_check.py:290** - Use proper logging instead of print()
- **health_check.py:295** - Use proper logging instead of print()
- **health_check.py:299** - Use proper logging instead of print()
- **health_check.py:301** - Use proper logging instead of print()
- **health_check.py:303** - Use proper logging instead of print()
- **health_check.py:304** - Use proper logging instead of print()
- **health_check.py:307** - Use proper logging instead of print()
- **health_check.py:310** - Use proper logging instead of print()
  - *...and 17 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `no-print-production` | 27 | warning |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `timeline_api.py` | 14 | 0 | 14 | 0 |
| `health_check.py` | 12 | 0 | 12 | 0 |
| `validator.py` | 1 | 0 | 1 | 0 |

---

## Recommendations

- **27 warnings** should be addressed

**💡 27 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.