---
name: claude-hooks-lint-fixes
description: Linting fixes applied to ~/.claude/hooks
type: project
---

# ~/.claude/hooks Linting Results & Fixes

## Audit Date: 2026-04-20

### Results Summary
- **4 Errors Fixed** ✅ (0 remaining)
- **22 Warnings** (unused imports/variables — non-critical)
- **Type Check:** PASS ✅

### Critical Errors Fixed

| File | Issue | Fix | Commit |
|------|-------|-----|--------|
| `handlers/user-prompt.ts:190` | Unnecessary escape: `[\+\*\?]` | Changed to `[+*?]` | Applied |
| `handlers/user-prompt.ts:195` | Unnecessary escape: `[\+\*\?]` | Changed to `[+*?]` | Applied |
| `lib/context-tracker.ts:154` | Unnecessary escape: `[{}\[\]]` | Changed to `[{}[\]]` | Applied |
| `handlers/stop.ts:218` | Useless assignment: `let errorCount = 0;` | Removed (assigned later on line 259) | Applied |

### Remaining Warnings (Non-Critical)

**Unused Imports/Variables (17):**
- post-tool.ts: getCacheDir, ensureCacheDir
- pre-tool.ts: getCacheDir, ensureCacheDir, appendToLog
- session-start.ts: getContextStats, getContextTrend
- stop.ts: shouldSampleSession, recordEvaluationSpend
- otel-monitor.ts: error variable
- otel.ts: hostDetector, osDetector, processDetector, Resource
- otel-monitor.test.ts: unused ctx parameters (should use _ctx naming convention)
- otel.ts: safeJsonParse
- trace-context.ts: MAX_ENTRIES_PER_FILE

**Type Issues (1):**
- otel.ts:82: `@typescript-eslint/no-explicit-any` — used explicit `any` type

### Recommendations

1. **unused ctx parameters** — Rename to `_ctx` to follow convention (allows unused args)
2. **Clean up imports** — Remove unused getCacheDir, ensureCacheDir, etc. if truly unneeded
3. **Type safety** — Replace explicit `any` with proper type annotation

### Quick Fixes

```bash
# Run linting
cd ~/.claude/hooks && npm run lint

# Build to compile TypeScript
npm run build

# Run tests
npm run test
```