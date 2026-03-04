# Code Quality Report: ast-grep-mcp

**Generated:** 2026-03-04 03:23:10
**Execution Time:** 143ms
**Files Scanned:** 1

---

## Summary

- **Total Violations:** 63
- **Error:** 0
- **Warning:** 63
- **Info:** 0
- **Files with Violations:** 1
- **Rules Executed:** 3

---

## Violations by Severity

### WARNING (63)

#### `no-print-production` (63 occurrences)
- **analyze_codebase.py:48** - Use proper logging instead of print()
- **analyze_codebase.py:49** - Use proper logging instead of print()
- **analyze_codebase.py:50** - Use proper logging instead of print()
- **analyze_codebase.py:77** - Use proper logging instead of print()
- **analyze_codebase.py:100** - Use proper logging instead of print()
- **analyze_codebase.py:103** - Use proper logging instead of print()
- **analyze_codebase.py:111** - Use proper logging instead of print()
- **analyze_codebase.py:112** - Use proper logging instead of print()
- **analyze_codebase.py:115** - Use proper logging instead of print()
- **analyze_codebase.py:120** - Use proper logging instead of print()
  - *...and 53 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `no-print-production` | 63 | warning |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `analyze_codebase.py` | 63 | 0 | 63 | 0 |

---

## Recommendations

- **63 warnings** should be addressed

**💡 63 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.