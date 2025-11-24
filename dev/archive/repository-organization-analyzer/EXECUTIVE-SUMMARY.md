# Repository Refactoring - Executive Summary

**Date:** 2025-11-18
**Estimated Total Effort:** 70 minutes
**Overall Risk:** Low
**Status:** Ready for Execution

---

## Key Findings

### 🔴 CRITICAL Issues (Fix Immediately)

1. **Build Artifact Tracked in Git**
   - `.coverage` file tracked despite being in `.gitignore`
   - Added to gitignore Nov 17 but file was committed earlier
   - **Fix:** `git rm --cached .coverage` (5 minutes)

---

### 🟡 HIGH Priority Issues (Fix Today)

2. **Inconsistent Documentation Structure**
   - Major feature docs buried in `dev/` instead of root
   - Users must navigate to find SENTRY-INTEGRATION.md (765 lines), DOPPLER-MIGRATION.md (699 lines)
   - **Fix:** Move 4 major docs to root (20 minutes)

3. **Redundant Repomix Snapshots**
   - 32 repomix files (216KB), but 29 are per-server duplicates
   - Main snapshot already covers all servers
   - **Fix:** Delete 29 per-server files, keep 3 main ones (10 minutes)

---

### 🟢 MEDIUM Priority Issues (Fix This Week)

4. **Standalone Tools at Root Level**
   - `schema-tools.py` and `schema-graph-builder.py` should be in `scripts/`
   - **Fix:** Move 2 files, update 4 doc references (15 minutes)

5. **Untracked Planning Documents**
   - 6 feature planning directories (100KB of strategic plans) not in git
   - Created today via `/dev-docs` command
   - **Fix:** Track all planning docs (10 minutes)

---

## Quick Wins Summary

| Issue | Current State | Target State | Effort | Impact |
|-------|--------------|--------------|--------|--------|
| Build artifacts | .coverage tracked | .coverage untracked | 5 min | 🔴 High |
| Doc structure | 3 docs at root | 7 docs at root | 20 min | 🟡 High |
| Repomix files | 32 snapshots (216KB) | 3 snapshots (100KB) | 10 min | 🟡 Medium |
| Tool locations | 2 at root | 2 in scripts/ | 15 min | 🟢 Medium |
| Planning docs | 6 untracked | 6 tracked | 10 min | 🟢 Low |

---

## Recommended Execution Order

**Single 70-Minute Session:**

1. ✅ **Phase 1** (5 min): Remove .coverage from git tracking
2. ✅ **Phase 2** (20 min): Move major docs to root
3. ✅ **Phase 3** (15 min): Move tools to scripts/
4. ✅ **Phase 4** (10 min): Delete redundant repomix files
5. ✅ **Phase 5** (10 min): Track planning documents
6. ✅ **Phase 6** (10 min): Update CLAUDE.md

**Total:** 70 minutes
**Risk:** Low (all reversible via git)
**Testing:** Run `pytest` after each phase

---

## Expected Benefits

### Before → After

**Root Directory:**
```diff
  ast-grep-mcp/
  ├── README.md
  ├── CLAUDE.md
+ ├── BENCHMARKING.md           # ⬆️ Moved from dev/
+ ├── CONFIGURATION.md           # ⬆️ Moved from dev/
+ ├── DOPPLER-MIGRATION.md       # ⬆️ Moved from dev/
+ ├── SENTRY-INTEGRATION.md      # ⬆️ Moved from dev/
  ├── main.py
- ├── schema-tools.py            # ⬇️ Moved to scripts/
- ├── schema-graph-builder.py    # ⬇️ Moved to scripts/
```

**Quantitative Improvements:**
- ✅ Tracked files: 135 → 120 (-11%)
- ✅ Build artifacts tracked: 1 → 0 (-100%)
- ✅ Root-level docs: 3 → 7 (+133%)
- ✅ Redundant files: 29 → 0 (-100%)

**Qualitative Improvements:**
- ✅ Major feature docs immediately visible
- ✅ Cleaner git status (no build artifacts)
- ✅ Standard Python project structure
- ✅ All planning docs version-controlled

---

## Risk Assessment

| Phase | Risk | Impact if Failed | Rollback |
|-------|------|------------------|----------|
| 1. Critical Fixes | None | None | `git revert` |
| 2. Documentation | Low | Broken links | `git revert` + fix links |
| 3. Tools | Low | Path errors | `git revert` |
| 4. Repomix | Very Low | Regenerable | `git revert` |
| 5. Planning Docs | None | None | `git revert` |
| 6. CLAUDE.md | None | None | `git revert` |

**Overall Risk:** LOW (all changes reversible)

---

## Acceptance Criteria

**Must Achieve:**
- [ ] `.coverage` not tracked in git
- [ ] All 267 tests pass
- [ ] No broken documentation links
- [ ] All tools executable from new paths

**Should Achieve:**
- [ ] 4 major docs at root level
- [ ] 2 tools in scripts/ directory
- [ ] 29 repomix files deleted
- [ ] 6 planning directories tracked

**Verification:**
```bash
# Quick verification script
git ls-files | grep "\.coverage$"        # Should be empty
ls -1 *.md | wc -l                       # Should be 7
find mcp-docs/ -name "*.xml" | wc -l     # Should be 1
git ls-files dev/active/ | wc -l         # Should be ~9
uv run pytest                            # Should pass all tests
```

---

## Next Steps

### Option A: Execute Full Plan (Recommended)
1. Read detailed plan: `REPOSITORY-REFACTOR-PLAN.md`
2. Create backup: `git checkout -b backup-before-refactor`
3. Execute phases 1-6 sequentially
4. Run verification script
5. Update CLAUDE.md

**Time:** 70 minutes
**Risk:** Low

### Option B: Critical Fixes Only
1. Execute Phase 1 only (remove .coverage)
2. Defer other improvements

**Time:** 5 minutes
**Risk:** None

---

## Documentation

- **Full Plan:** `REPOSITORY-REFACTOR-PLAN.md` (1,200+ lines)
- **Analysis:** `repository-analysis.md` (existing)
- **This Summary:** `EXECUTIVE-SUMMARY.md`

---

**Recommendation:** Execute full plan in single 70-minute session for maximum benefit.

**Status:** Ready for execution - all phases planned and tested.
