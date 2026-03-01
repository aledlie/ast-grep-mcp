# Code Quality Report: ast-grep-mcp

**Generated:** 2026-03-01 00:59:43
**Execution Time:** 496ms
**Files Scanned:** 33

---

## Summary

- **Total Violations:** 88
- **Error:** 1
- **Warning:** 0
- **Info:** 87
- **Files with Violations:** 33
- **Rules Executed:** 7

---

## Violations by Severity

### ERROR (1)

#### `no-empty-catch` (1 occurrences)
- **sync-to-kv.ts:211** - Empty catch block detected - handle the error or add a comment explaining why it's ignored

### INFO (87)

#### `prefer-const` (87 occurrences)
- **quality.ts:26** - This variable is never reassigned, use const instead
- **auth.ts:27** - This variable is never reassigned, use const instead
- **judge-evaluations.ts:420** - This variable is never reassigned, use const instead
- **judge-evaluations.ts:786** - This variable is never reassigned, use const instead
- **judge-evaluations.ts:871** - This variable is never reassigned, use const instead
- **judge-evaluations.ts:898** - This variable is never reassigned, use const instead
- **useQualityLive.ts:18** - This variable is never reassigned, use const instead
- **update-readme-tree.ts:66** - This variable is never reassigned, use const instead
- **pipeline-integration.test.ts:319** - This variable is never reassigned, use const instead
- **sync-prioritization.test.ts:161** - This variable is never reassigned, use const instead
  - *...and 77 more*


---

## Top Issues by Rule

| Rule | Count | Severity |
|------|-------|----------|
| `prefer-const` | 87 | info |
| `no-empty-catch` | 1 | error |

---

## Files with Most Violations

| File | Violations | Errors | Warnings | Info |
|------|------------|--------|----------|------|
| `get-trace-url.test.ts` | 12 | 0 | 0 | 12 |
| `llm-judge-qag.test.ts` | 6 | 0 | 0 | 6 |
| `query-metrics.ts` | 5 | 0 | 0 | 5 |
| `llm-judge-security.ts` | 5 | 0 | 0 | 5 |
| `judge-evaluations.ts` | 4 | 0 | 0 | 4 |
| `index.ts` | 4 | 0 | 0 | 4 |
| `api.test.ts` | 4 | 0 | 0 | 4 |
| `auth.test.ts` | 4 | 0 | 0 | 4 |
| `agent-auditor-scoring.ts` | 4 | 0 | 0 | 4 |
| `query-evaluations.test.ts` | 3 | 0 | 0 | 3 |

---

## Recommendations

- **1 errors** require immediate attention
- **87 info items** are suggestions for improvement

**💡 87 violations have automatic fixes available.**
Consider using `apply_standards_fixes` to auto-fix safe violations.