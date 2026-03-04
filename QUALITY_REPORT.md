# Code Quality Report: ast-grep-mcp

**Generated:** 2026-03-04 05:20:03
**Execution Time:** 142ms
**Files Scanned:** 1

---

## Summary

- **Total Violations:** 75
- **Error:** 0
- **Warning:** 75
- **Info:** 0
- **Files with Violations:** 1
- **Rules Executed:** 3

---

## Violations by Severity

### WARNING (75)

#### `no-print-production` (75 occurrences)
- **analyze_codebase.py:48** - Use proper logging instead of print()
- **analyze_codebase.py:49** - Use proper logging instead of print()
- **analyze_codebase.py:50** - Use proper logging instead of print()
- **analyze_codebase.py:77** - Use proper logging instead of print()
- **analyze_codebase.py:100** - Use proper logging instead of print()
- **analyze_codebase.py:103** - Use proper logging instead of print()
- **analyze_codebase.py:108** - Use proper logging instead of print()
- **analyze_codebase.py:109** - Use proper logging instead of print()
- **analyze_codebase.py:112** - Use proper logging instead of print()
- **analyze_codebase.py:117** - Use proper logging instead of print()
  - *...and 65 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `no-print-production` | 75 | warning |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `analyze_codebase.py` | 75 | 0 | 75 | 0 |

---

## Recommendations

- **75 warnings** should be addressed

**💡 75 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.