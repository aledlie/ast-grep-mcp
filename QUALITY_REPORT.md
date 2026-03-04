# Code Quality Report: ast-grep-mcp

**Generated:** 2026-03-04 01:24:59
**Execution Time:** 134ms
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
- **analyze_codebase.py:47** - Use proper logging instead of print()
- **analyze_codebase.py:48** - Use proper logging instead of print()
- **analyze_codebase.py:49** - Use proper logging instead of print()
- **analyze_codebase.py:76** - Use proper logging instead of print()
- **analyze_codebase.py:93** - Use proper logging instead of print()
- **analyze_codebase.py:96** - Use proper logging instead of print()
- **analyze_codebase.py:104** - Use proper logging instead of print()
- **analyze_codebase.py:105** - Use proper logging instead of print()
- **analyze_codebase.py:108** - Use proper logging instead of print()
- **analyze_codebase.py:110** - Use proper logging instead of print()
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