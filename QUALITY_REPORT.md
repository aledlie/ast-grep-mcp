# Code Quality Report: ast-grep-mcp

**Generated:** 2026-02-28 23:26:26
**Execution Time:** 362ms
**Files Scanned:** 43

---

## Summary

- **Total Violations:** 157
- **Error:** 0
- **Warning:** 67
- **Info:** 90
- **Files with Violations:** 43
- **Rules Executed:** 7

---

## Violations by Severity

### WARNING (67)

#### `no-console-log` (67 occurrences)
- **generate-token-tree.ts:30** - Remove console.log before committing
- **server.ts:35** - Remove console.log before committing
- **auth.ts:68** - Remove console.log before committing
- **auth.ts:89** - Remove console.log before committing
- **generate-token-tree.ts:30** - Remove console.log before committing
- **index.ts:165** - Remove console.log before committing
- **index.ts:226** - Remove console.log before committing
- **judge-evaluations.ts:221** - Remove console.log before committing
- **judge-evaluations.ts:856** - Remove console.log before committing
- **judge-evaluations.ts:909** - Remove console.log before committing
  - *...and 57 more*

### INFO (90)

#### `prefer-const` (90 occurrences)
- **server.ts:255** - This variable is never reassigned, use const instead
- **sessions.ts:70** - This variable is never reassigned, use const instead
- **sessions.ts:71** - This variable is never reassigned, use const instead
- **metrics.ts:67** - This variable is never reassigned, use const instead
- **metrics.ts:116** - This variable is never reassigned, use const instead
- **get-trace-url.ts:27** - This variable is never reassigned, use const instead
- **health-check.ts:113** - This variable is never reassigned, use const instead
- **health-check.ts:114** - This variable is never reassigned, use const instead
- **health-check.ts:139** - This variable is never reassigned, use const instead
- **health-check.ts:140** - This variable is never reassigned, use const instead
  - *...and 80 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `prefer-const` | 90 | info |
| `no-console-log` | 67 | warning |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `judge-evaluations.ts` | 26 | 0 | 22 | 4 |
| `server.test.ts` | 14 | 0 | 0 | 14 |
| `sync-to-kv.ts` | 13 | 0 | 13 | 0 |
| `get-trace-url.test.ts` | 12 | 0 | 0 | 12 |
| `derive-evaluations.ts` | 10 | 0 | 6 | 4 |
| `populate-dashboard.ts` | 8 | 0 | 8 | 0 |
| `fuzz-generators.ts` | 5 | 0 | 0 | 5 |
| `memfs-utils.ts` | 5 | 0 | 0 | 5 |
| `query-metrics.ts` | 5 | 0 | 0 | 5 |
| `health-check.ts` | 4 | 0 | 0 | 4 |

---

## Recommendations

- **67 warnings** should be addressed
- **90 info items** are suggestions for improvement

**💡 90 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.