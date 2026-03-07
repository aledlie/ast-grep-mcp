# Code Quality Report: ast-grep-mcp

**Generated:** 2026-03-04 21:13:06
**Execution Time:** 35ms
**Files Scanned:** 3

---

## Summary

- **Total Violations:** 50
- **Error:** 0
- **Warning:** 50
- **Info:** 0
- **Files with Violations:** 3
- **Rules Executed:** 3

---

## Violations by Severity

### WARNING (50)

#### `no-print-production` (50 occurrences)
- **test_extract_blocks.py:329** - Use proper logging instead of print()
- **test_extract_blocks.py:330** - Use proper logging instead of print()
- **test_extract_blocks.py:331** - Use proper logging instead of print()
- **test_extract_blocks.py:364** - Use proper logging instead of print()
- **test_extract_blocks.py:367** - Use proper logging instead of print()
- **test_extract_blocks.py:370** - Use proper logging instead of print()
- **test_extract_blocks.py:373** - Use proper logging instead of print()
- **test_extract_blocks.py:374** - Use proper logging instead of print()
- **test_extract_blocks.py:375** - Use proper logging instead of print()
- **test_runner.py:11** - Use proper logging instead of print()
  - *...and 40 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `no-print-production` | 50 | warning |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `test_models.py` | 31 | 0 | 31 | 0 |
| `test_runner.py` | 10 | 0 | 10 | 0 |
| `test_extract_blocks.py` | 9 | 0 | 9 | 0 |

---

## Recommendations

- **50 warnings** should be addressed

**💡 50 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.