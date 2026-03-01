# Code Quality Report: ast-grep-mcp

**Generated:** 2026-03-01 04:26:40
**Execution Time:** 14ms
**Files Scanned:** 1

---

## Summary

- **Total Violations:** 36
- **Error:** 0
- **Warning:** 36
- **Info:** 0
- **Files with Violations:** 1
- **Rules Executed:** 3

---

## Violations by Severity

### WARNING (36)

#### `no-print-production` (36 occurrences)
- **collect_git_activity.py:76** - Use proper logging instead of print()
- **collect_git_activity.py:89** - Use proper logging instead of print()
- **collect_git_activity.py:101** - Use proper logging instead of print()
- **collect_git_activity.py:122** - Use proper logging instead of print()
- **collect_git_activity.py:125** - Use proper logging instead of print()
- **collect_git_activity.py:168** - Use proper logging instead of print()
- **collect_git_activity.py:307** - Use proper logging instead of print()
- **collect_git_activity.py:344** - Use proper logging instead of print()
- **collect_git_activity.py:389** - Use proper logging instead of print()
- **collect_git_activity.py:410** - Use proper logging instead of print()
  - *...and 26 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `no-print-production` | 36 | warning |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `collect_git_activity.py` | 36 | 0 | 36 | 0 |

---

## Recommendations

- **36 warnings** should be addressed

**💡 36 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.