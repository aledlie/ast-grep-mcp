# Code Quality Report: ast-grep-mcp

**Generated:** 2026-03-01 00:16:14
**Execution Time:** 452ms
**Files Scanned:** 53

---

## Summary

- **Total Violations:** 161
- **Error:** 0
- **Warning:** 70
- **Info:** 91
- **Files with Violations:** 53
- **Rules Executed:** 7

---

## Violations by Severity

### WARNING (70)

#### `no-console-log` (67 occurrences)
- **generate-token-tree.ts:30** - Remove console.log before committing
- **auth.ts:68** - Remove console.log before committing
- **auth.ts:89** - Remove console.log before committing
- **index.ts:165** - Remove console.log before committing
- **index.ts:226** - Remove console.log before committing
- **generate-token-tree.ts:30** - Remove console.log before committing
- **server.ts:34** - Remove console.log before committing
- **judge-evaluations.ts:221** - Remove console.log before committing
- **judge-evaluations.ts:856** - Remove console.log before committing
- **judge-evaluations.ts:909** - Remove console.log before committing
  - *...and 57 more*

#### `no-double-equals` (3 occurrences)
- **agents.ts:85** - Use === instead of == for type-safe comparison
- **dashboard.ts:40** - Use === instead of == for type-safe comparison
- **local-jsonl.ts:324** - Use === instead of == for type-safe comparison

### INFO (91)

#### `prefer-const` (91 occurrences)
- **server.ts:255** - This variable is never reassigned, use const instead
- **local-jsonl-circuit-breaker.test.ts:64** - This variable is never reassigned, use const instead
- **query-sanitizer.ts:187** - This variable is never reassigned, use const instead
- **query-sanitizer.ts:272** - This variable is never reassigned, use const instead
- **get-trace-url.ts:27** - This variable is never reassigned, use const instead
- **auth.ts:26** - This variable is never reassigned, use const instead
- **error-sanitizer.ts:34** - This variable is never reassigned, use const instead
- **error-sanitizer.ts:177** - This variable is never reassigned, use const instead
- **cloud.ts:317** - This variable is never reassigned, use const instead
- **server.test.ts:710** - This variable is never reassigned, use const instead
  - *...and 81 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `prefer-const` | 91 | info |
| `no-console-log` | 67 | warning |
| `no-double-equals` | 3 | warning |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `judge-evaluations.ts` | 26 | 0 | 22 | 4 |
| `server.test.ts` | 14 | 0 | 0 | 14 |
| `sync-to-kv.ts` | 13 | 0 | 13 | 0 |
| `derive-evaluations.ts` | 10 | 0 | 6 | 4 |
| `populate-dashboard.ts` | 8 | 0 | 8 | 0 |
| `fuzz-generators.ts` | 5 | 0 | 0 | 5 |
| `memfs-utils.ts` | 5 | 0 | 0 | 5 |
| `query-metrics.ts` | 5 | 0 | 0 | 5 |
| `health-check.ts` | 4 | 0 | 0 | 4 |
| `race-condition-helpers.ts` | 4 | 0 | 0 | 4 |

---

## Recommendations

- **70 warnings** should be addressed
- **91 info items** are suggestions for improvement

**💡 94 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.