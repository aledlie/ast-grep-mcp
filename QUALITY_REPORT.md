# Code Quality Report: ast-grep-mcp

**Generated:** 2026-02-28 22:51:51
**Execution Time:** 413ms
**Files Scanned:** 46

---

## Summary

- **Total Violations:** 162
- **Error:** 0
- **Warning:** 71
- **Info:** 91
- **Files with Violations:** 46
- **Rules Executed:** 7

---

## Violations by Severity

### WARNING (71)

#### `no-console-log` (71 occurrences)
- **generate-token-tree.ts:30** - Remove console.log before committing
- **generate-token-tree.ts:30** - Remove console.log before committing
- **server.ts:34** - Remove console.log before committing
- **judge-evaluations.ts:221** - Remove console.log before committing
- **judge-evaluations.ts:857** - Remove console.log before committing
- **judge-evaluations.ts:911** - Remove console.log before committing
- **judge-evaluations.ts:913** - Remove console.log before committing
- **judge-evaluations.ts:916** - Remove console.log before committing
- **judge-evaluations.ts:922** - Remove console.log before committing
- **judge-evaluations.ts:927** - Remove console.log before committing
  - *...and 61 more*

### INFO (91)

#### `prefer-const` (91 occurrences)
- **server.ts:255** - This variable is never reassigned, use const instead
- **query-sanitizer.ts:187** - This variable is never reassigned, use const instead
- **query-sanitizer.ts:272** - This variable is never reassigned, use const instead
- **get-trace-url.ts:27** - This variable is never reassigned, use const instead
- **error-sanitizer.ts:34** - This variable is never reassigned, use const instead
- **error-sanitizer.ts:177** - This variable is never reassigned, use const instead
- **health-check.ts:113** - This variable is never reassigned, use const instead
- **health-check.ts:114** - This variable is never reassigned, use const instead
- **health-check.ts:139** - This variable is never reassigned, use const instead
- **health-check.ts:140** - This variable is never reassigned, use const instead
  - *...and 81 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `prefer-const` | 91 | info |
| `no-console-log` | 71 | warning |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `judge-evaluations.ts` | 30 | 0 | 26 | 4 |
| `server.test.ts` | 14 | 0 | 0 | 14 |
| `sync-to-kv.ts` | 13 | 0 | 13 | 0 |
| `derive-evaluations.ts` | 10 | 0 | 6 | 4 |
| `populate-dashboard.ts` | 8 | 0 | 8 | 0 |
| `index.ts` | 6 | 0 | 2 | 4 |
| `fuzz-generators.ts` | 5 | 0 | 0 | 5 |
| `memfs-utils.ts` | 5 | 0 | 0 | 5 |
| `query-metrics.ts` | 5 | 0 | 0 | 5 |
| `auth.ts` | 5 | 0 | 2 | 3 |

---

## Recommendations

- **71 warnings** should be addressed
- **91 info items** are suggestions for improvement

**💡 91 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.