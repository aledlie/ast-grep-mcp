# ast-grep-mcp Repository Organization Refactoring Plan

**Date:** 2025-11-18
**Status:** Analysis Complete - Ready for Execution
**Estimated Total Effort:** 2-3 hours
**Risk Level:** Low (all changes are reversible via git)

---

## Executive Summary

Repository has **135 tracked files** (180 total including build artifacts) with several organizational issues:

- **CRITICAL**: `.coverage` build artifact tracked in git despite being in `.gitignore`
- **HIGH**: Inconsistent documentation structure (split between root and `dev/`)
- **MEDIUM**: 32 repomix snapshots consuming 216KB (30 potentially redundant)
- **MEDIUM**: 2 standalone tools at root level should move to `scripts/`
- **LOW**: 6 untracked `dev/active/` feature planning directories

**Key Metrics:**
- Main application: 1 file (`main.py`, ~4000 lines)
- Test coverage: 267 tests (254 unit + 13 integration)
- Documentation: 4,252 lines across 7 markdown files
- mcp-docs: 412KB reference documentation (30 MCP servers)

---

## 1. Duplication Analysis

### 1.1 Repomix Snapshot Analysis

**Total: 32 repomix-output.xml files (216KB)**

#### Main Snapshots (Keep - High Value)
```
✅ mcp-docs/repomix-output.xml          - 2,536 lines (55KB)  - Full MCP ecosystem snapshot
✅ tests/repomix-output.xml             - 1,441 lines (45KB)  - Test suite snapshot
✅ tests/fixtures/repomix-output.xml    - 116 lines (3.9KB)   - Test fixture for validation
```
**Rationale:** These provide valuable point-in-time context and are referenced in CLAUDE.md

#### Per-Server Snapshots (Remove - Low Value)
```
❌ mcp-docs/*/repomix-output.xml (29 files) - 116KB total
   - auth0, browserbase, bullmq, cloudflare-*, discord, etc.
   - Each 3-4KB (120-146 lines)
   - Duplicate information already in main mcp-docs/repomix-output.xml
   - Add minimal value (server-specific detail available in README.md)
```

**Decision:** Remove 29 per-server snapshots, keep 3 main ones

**Savings:** 116KB, cleaner directory structure

**Risk:** Very Low
- Information preserved in main snapshot
- Easily regenerable with `repomix mcp-docs/[server-name]` if needed
- No code functionality affected

---

### 1.2 Code Duplication

**Analysis:** No significant code duplication found
- Single-file architecture (`main.py`) prevents fragmentation
- Scripts are distinct utilities (no overlap)
- Test files follow DRY principles with shared fixtures

---

## 2. File Removal Candidates

### 2.1 🔴 CRITICAL: Build Artifacts Tracked in Git

**Issue:** `.coverage` is tracked despite being in `.gitignore` (added Nov 17)

```bash
# Verification
$ git ls-files | grep "\.coverage$"
.coverage  # ❌ SHOULD NOT BE TRACKED

$ cat .gitignore | grep coverage
.coverage  # ✅ IS IN GITIGNORE
```

**Root Cause:** `.coverage` was committed before `.gitignore` entry added

**Action Required:**
```bash
# Remove from git tracking (keeps local file)
git rm --cached .coverage
git commit -m "chore: remove .coverage build artifact from git tracking"
```

**Risk:** None - file kept locally for development, just untracked

---

### 2.2 🟡 HIGH: Redundant Repomix Snapshots

**Files to Remove:** 29 per-server repomix files in `mcp-docs/*/repomix-output.xml`

**Action:**
```bash
# Remove per-server snapshots
find mcp-docs/ -mindepth 2 -name "repomix-output.xml" -delete

# Update gitignore to prevent future per-server snapshots
echo "# Per-server repomix snapshots (main snapshot in mcp-docs/ is sufficient)" >> .gitignore
echo "mcp-docs/*/repomix-output.xml" >> .gitignore
```

**Exception:** Keep these 3:
- `mcp-docs/repomix-output.xml` (main ecosystem snapshot)
- `tests/repomix-output.xml` (test suite snapshot)
- `tests/fixtures/repomix-output.xml` (test fixture)

**Risk:** Very Low
- Easily regenerable
- No functionality impact
- Information preserved in main snapshot

---

### 2.3 ⚪ LOW: htmlcov/ Directory

**Status:** Already gitignored properly via `htmlcov/.gitignore`

**Action:** None needed (working as intended)

---

### 2.4 Backup/Old Files

**Status:** ✅ None found
```bash
$ find . -name "*.backup" -o -name "*.old" -o -name "*~" -o -name "*.bak"
# (no results)
```

---

## 3. Reorganization Recommendations

### 3.1 🟡 HIGH: Documentation Structure Consolidation

**Current State (Inconsistent):**
```
ast-grep-mcp/
├── README.md                       # Main docs (832 lines)
├── CLAUDE.md                       # Claude Code instructions (in repo)
├── ast-grep.mdc                    # ast-grep rule writing guide
└── dev/
    ├── README.md                   # Development workflow (151 lines)
    ├── BENCHMARKING.md             # Performance guide (246 lines)
    ├── CONFIGURATION.md            # Config examples (567 lines)
    ├── DOPPLER-MIGRATION.md        # Migration guide (699 lines)
    └── SENTRY-INTEGRATION.md       # Sentry guide (765 lines)
```

**Problem:** Major feature documentation buried in `dev/` instead of root

**Proposal: Hybrid Structure**

```
ast-grep-mcp/
├── README.md                       # Main docs (keep at root)
├── CLAUDE.md                       # Keep at root (Claude Code requirement)
├── ast-grep.mdc                    # Keep at root (quick reference)
├── BENCHMARKING.md                 # ⬆️ MOVE to root (major feature)
├── CONFIGURATION.md                # ⬆️ MOVE to root (user-facing)
├── DOPPLER-MIGRATION.md            # ⬆️ MOVE to root (major feature)
├── SENTRY-INTEGRATION.md           # ⬆️ MOVE to root (major feature)
└── dev/
    ├── README.md                   # Keep (development workflow)
    └── active/                     # Planning documents
```

**Rationale:**
- **BENCHMARKING.md** (246 lines): Performance is a core feature - users need this
- **CONFIGURATION.md** (567 lines): Users configure MCP server - must be discoverable
- **DOPPLER-MIGRATION.md** (699 lines): Major setup guide - root level visibility
- **SENTRY-INTEGRATION.md** (765 lines): Major feature guide - root level visibility
- **dev/README.md** (151 lines): Development workflow - appropriate in dev/

**Alternative Approach: Create docs/ Directory**

```
ast-grep-mcp/
├── README.md                       # Quick start
├── CLAUDE.md                       # Claude Code instructions
├── ast-grep.mdc                    # ast-grep rules reference
└── docs/
    ├── BENCHMARKING.md
    ├── CONFIGURATION.md
    ├── DEVELOPMENT.md              # (renamed from dev/README.md)
    ├── DOPPLER-MIGRATION.md
    └── SENTRY-INTEGRATION.md
```

**Decision Matrix:**

| Criterion | Hybrid (Move to Root) | Centralized (docs/) |
|-----------|----------------------|---------------------|
| Discoverability | ⭐⭐⭐⭐⭐ (GitHub shows root files) | ⭐⭐⭐ (extra click needed) |
| Organization | ⭐⭐⭐ (root can get cluttered) | ⭐⭐⭐⭐⭐ (clean separation) |
| Precedent | ⭐⭐⭐⭐ (common in Python projects) | ⭐⭐⭐⭐ (common in large projects) |
| Migration Effort | ⭐⭐⭐⭐⭐ (simple mv) | ⭐⭐⭐⭐ (need to update links) |

**RECOMMENDED: Hybrid Approach (Move to Root)**
- Better discoverability for users
- Matches Python project conventions
- Minimal migration effort
- Root won't be cluttered (only 7 markdown files total)

---

### 3.2 🟢 MEDIUM: Tools Organization

**Current State:**
```
ast-grep-mcp/
├── schema-tools.py              # Standalone Schema.org CLI
├── schema-graph-builder.py      # Entity graph builder
└── scripts/
    ├── find_duplication.py
    ├── find_duplication.sh
    ├── run_benchmarks.py
    └── README.md
```

**Proposal: Consolidate to scripts/**

```bash
# Move tools to scripts/
mv schema-tools.py scripts/
mv schema-graph-builder.py scripts/

# Update documentation references
# - README.md
# - CLAUDE.md (2 references)
# - SCHEMA-TOOLS-README.md (if exists)
# - SCHEMA-GRAPH-BUILDER-README.md (if exists)
```

**Benefits:**
- All standalone tools in one location
- Cleaner root directory
- Consistent with Unix conventions

**Link Updates Required:**
- `README.md`: Update "Standalone Tools" section paths
- `CLAUDE.md`: Update "Standalone Tools" section (2 references)
- Any schema tool README files

**Risk:** Low
- Simple file moves
- No code changes needed (both are executable scripts)
- Easy to verify with grep for references

---

### 3.3 🟢 MEDIUM: dev/active/ Management

**Current State:**
```
dev/active/
├── repository-organization-analyzer/  # ✅ TRACKED (this task)
├── code-analysis-metrics/             # ❌ UNTRACKED
├── code-quality-standards/            # ❌ UNTRACKED
├── cross-language-operations/         # ❌ UNTRACKED
├── documentation-generation/          # ❌ UNTRACKED
├── enhanced-duplication-detection/    # ❌ UNTRACKED
├── refactoring-assistants/            # ❌ UNTRACKED
└── NEW-FEATURES-OVERVIEW.md           # ❌ UNTRACKED
```

**Analysis:**

1. **NEW-FEATURES-OVERVIEW.md** (433 lines)
   - High-quality planning overview document
   - References all 6 feature areas
   - Created 2025-11-18 (today)
   - **Action:** TRACK (valuable planning artifact)

2. **6 Feature Planning Directories**
   - Each contains detailed strategic plans
   - Total: ~100KB of planning documentation
   - Created: 2025-11-18 (today, via /dev-docs command)
   - Status: "Planning Complete - Ready for Implementation"
   - **Action:** TRACK (valuable for future implementation)

**Decision: Track All Planning Documents**

**Rationale:**
- These are strategic planning artifacts, not ephemeral notes
- High quality (100KB+ of detailed plans)
- Future implementation reference
- Version control enables tracking plan evolution
- Disk space impact negligible (100KB vs 181MB repo)

**Action:**
```bash
cd dev/active
git add NEW-FEATURES-OVERVIEW.md
git add code-analysis-metrics/
git add code-quality-standards/
git add cross-language-operations/
git add documentation-generation/
git add enhanced-duplication-detection/
git add refactoring-assistants/
git commit -m "docs: add strategic feature planning documents for 6 major features"
```

**Risk:** None - planning documents, no code impact

---

## 4. Naming Convention Assessment

### 4.1 Current Naming Patterns

**Documentation Files:**
```
✅ UPPERCASE.md for root-level docs (README.md, CLAUDE.md)
✅ UPPERCASE.md for major guides (BENCHMARKING.md, etc.)
✅ lowercase-hyphenated.md for nested docs (dev/active/feature-name-plan.md)
```

**Python Files:**
```
✅ snake_case.py (main.py, schema-tools.py, find_duplication.py)
✅ Consistent throughout
```

**Directories:**
```
✅ lowercase-hyphenated (mcp-docs, dev, scripts, tests)
✅ Consistent throughout
```

**Assessment:** ✅ Naming conventions are already consistent and follow best practices

**No action needed**

---

## 5. Migration Plan

### Phase 1: Critical Fixes (5 minutes)
**Priority:** 🔴 CRITICAL
**Effort:** 5 minutes
**Risk:** None

```bash
# 1. Remove .coverage from git tracking
git rm --cached .coverage
git commit -m "chore: remove .coverage build artifact from git tracking"
```

**Verification:**
```bash
git ls-files | grep "\.coverage$"  # Should return nothing
ls -la .coverage                    # File still exists locally
```

---

### Phase 2: Documentation Reorganization (20 minutes)
**Priority:** 🟡 HIGH
**Effort:** 20 minutes
**Risk:** Low

```bash
# 1. Move major documentation to root
cd /Users/alyshialedlie/code/ast-grep-mcp
git mv dev/BENCHMARKING.md .
git mv dev/CONFIGURATION.md .
git mv dev/DOPPLER-MIGRATION.md .
git mv dev/SENTRY-INTEGRATION.md .

# 2. Update internal links (manual - see checklist below)
# Edit these files to update paths:
# - README.md (search for "BENCHMARKING", "CONFIGURATION", "DOPPLER", "SENTRY")
# - CLAUDE.md (search for "dev/BENCHMARKING", "dev/DOPPLER", "dev/SENTRY")

# 3. Commit
git commit -m "docs: move major feature documentation to root for better discoverability

- Move BENCHMARKING.md to root (performance is core feature)
- Move CONFIGURATION.md to root (user-facing setup guide)
- Move DOPPLER-MIGRATION.md to root (major setup guide)
- Move SENTRY-INTEGRATION.md to root (major feature guide)
- Keep dev/README.md for development workflow

Improves discoverability for users browsing repository."
```

**Link Update Checklist:**
- [ ] README.md - Update 4-6 documentation links
- [ ] CLAUDE.md - Update 3-5 references
- [ ] Verify all links work: `grep -r "dev/BENCHMARKING\|dev/CONFIGURATION\|dev/DOPPLER\|dev/SENTRY" *.md`

---

### Phase 3: Tools Consolidation (15 minutes)
**Priority:** 🟢 MEDIUM
**Effort:** 15 minutes
**Risk:** Low

```bash
# 1. Move tools to scripts/
cd /Users/alyshialedlie/code/ast-grep-mcp
git mv schema-tools.py scripts/
git mv schema-graph-builder.py scripts/

# 2. Update documentation references
# Files to edit:
# - README.md (search for "schema-tools.py", "schema-graph-builder.py")
# - CLAUDE.md (search for "schema-tools.py", "schema-graph-builder.py")

# 3. Commit
git commit -m "refactor: move standalone tools to scripts/ directory

- Move schema-tools.py to scripts/
- Move schema-graph-builder.py to scripts/
- Update documentation references

All standalone utilities now in scripts/ for better organization."
```

**Link Update Checklist:**
- [ ] README.md - Update "Standalone Tools" section (2 references)
- [ ] CLAUDE.md - Update "Standalone Tools" section (2 references)
- [ ] Verify: `grep -r "schema-tools.py\|schema-graph-builder.py" *.md`

---

### Phase 4: Repomix Cleanup (10 minutes)
**Priority:** 🟢 MEDIUM
**Effort:** 10 minutes
**Risk:** Very Low

```bash
# 1. Remove redundant per-server snapshots
cd /Users/alyshialedlie/code/ast-grep-mcp
find mcp-docs/ -mindepth 2 -name "repomix-output.xml" -delete

# 2. Update .gitignore to prevent future per-server snapshots
cat >> .gitignore << 'EOF'

# Per-server repomix snapshots (main snapshot in mcp-docs/ is sufficient)
mcp-docs/*/repomix-output.xml
EOF

# 3. Commit
git commit -am "chore: remove redundant per-server repomix snapshots

- Remove 29 per-server repomix files (116KB)
- Keep main snapshots: mcp-docs/, tests/, tests/fixtures/
- Add gitignore rule to prevent future per-server snapshots

Information preserved in main mcp-docs/repomix-output.xml snapshot."
```

**Verification:**
```bash
find mcp-docs/ -name "repomix-output.xml" | wc -l  # Should be 1
ls -lh mcp-docs/repomix-output.xml                  # Should exist (55KB)
```

---

### Phase 5: Track Planning Documents (10 minutes)
**Priority:** ⚪ LOW
**Effort:** 10 minutes
**Risk:** None

```bash
# 1. Track feature planning documents
cd /Users/alyshialedlie/code/ast-grep-mcp
git add dev/active/NEW-FEATURES-OVERVIEW.md
git add dev/active/code-analysis-metrics/
git add dev/active/code-quality-standards/
git add dev/active/cross-language-operations/
git add dev/active/documentation-generation/
git add dev/active/enhanced-duplication-detection/
git add dev/active/refactoring-assistants/

# 2. Commit
git commit -m "docs: add strategic feature planning documents

Add comprehensive planning for 6 major features:
- Enhanced duplication detection (4-6 weeks)
- Code analysis & metrics (5-7 weeks)
- Refactoring assistants (6-8 weeks)
- Documentation generation (4-6 weeks)
- Code quality & standards (5-7 weeks)
- Cross-language operations (7-9 weeks)

Total: ~100KB of detailed strategic plans, task breakdowns, and technical designs.
Status: Planning complete, ready for prioritization and implementation."
```

---

### Phase 6: Update CLAUDE.md (10 minutes)
**Priority:** 🟢 MEDIUM
**Effort:** 10 minutes
**Risk:** None

Update CLAUDE.md to reflect new structure:

1. **Documentation paths** (line ~11-20)
2. **Standalone tools paths** (line ~40-50)
3. **Repomix strategy** (line ~450-470)
4. **Repository structure section** (line ~800-850)

**Key changes:**
- Update documentation file paths (remove `dev/` prefix)
- Update tools paths (add `scripts/` prefix)
- Note per-server repomix snapshots removed
- Update dev/active/ status (now tracked)

---

## 6. Execution Summary

### 6.1 Migration Order (Minimize Breakage)

**Recommended sequence:**

1. **Phase 1: Critical Fixes** (5 min)
   - Remove .coverage from tracking
   - Zero user impact

2. **Phase 2: Documentation Reorganization** (20 min)
   - Move major docs to root
   - Update links in README.md, CLAUDE.md
   - Medium user impact (broken links if incomplete)

3. **Phase 3: Tools Consolidation** (15 min)
   - Move tools to scripts/
   - Update documentation references
   - Low user impact (paths change but documented)

4. **Phase 4: Repomix Cleanup** (10 min)
   - Remove redundant snapshots
   - Zero user impact (internal files)

5. **Phase 5: Track Planning Documents** (10 min)
   - Add strategic plans to git
   - Zero user impact (new files only)

6. **Phase 6: Update CLAUDE.md** (10 min)
   - Reflect all changes
   - Zero user impact (documentation only)

**Total Time:** 70 minutes (1 hour 10 minutes)

---

### 6.2 Risk Assessment by Phase

| Phase | Risk Level | Impact if Failed | Mitigation |
|-------|-----------|------------------|------------|
| 1. Critical Fixes | None | None | Git revert |
| 2. Documentation | Low | Broken doc links | grep verification before commit |
| 3. Tools | Low | Import errors if paths hardcoded | Test after move |
| 4. Repomix Cleanup | Very Low | Regenerable files | Keep main snapshots |
| 5. Planning Docs | None | None | New files only |
| 6. CLAUDE.md | None | None | Documentation only |

**Overall Risk:** LOW

---

### 6.3 Rollback Procedures

**All phases are reversible via git:**

```bash
# Rollback individual phase
git log --oneline -10                    # Find commit hash
git revert <commit-hash>                 # Create reverse commit

# Or reset to before changes (destructive)
git reset --hard <commit-before-changes>

# Recover deleted files (before commit)
git checkout HEAD -- <file-path>
```

**No irreversible operations** - all changes are version controlled

---

## 7. Expected Outcomes

### 7.1 Before → After Comparison

**Root Directory:**
```diff
  ast-grep-mcp/
  ├── README.md
  ├── CLAUDE.md
  ├── ast-grep.mdc
+ ├── BENCHMARKING.md           # ⬆️ Moved from dev/
+ ├── CONFIGURATION.md           # ⬆️ Moved from dev/
+ ├── DOPPLER-MIGRATION.md       # ⬆️ Moved from dev/
+ ├── SENTRY-INTEGRATION.md      # ⬆️ Moved from dev/
  ├── main.py
  ├── pyproject.toml
- ├── schema-tools.py            # ⬇️ Moved to scripts/
- ├── schema-graph-builder.py    # ⬇️ Moved to scripts/
  └── uv.lock
```

**scripts/ Directory:**
```diff
  scripts/
  ├── find_duplication.py
  ├── find_duplication.sh
  ├── run_benchmarks.py
+ ├── schema-tools.py            # ⬆️ Moved from root
+ ├── schema-graph-builder.py    # ⬆️ Moved from root
  └── README.md
```

**dev/ Directory:**
```diff
  dev/
  ├── README.md                  # ✅ Kept (development workflow)
- ├── BENCHMARKING.md            # ⬆️ Moved to root
- ├── CONFIGURATION.md           # ⬆️ Moved to root
- ├── DOPPLER-MIGRATION.md       # ⬆️ Moved to root
- ├── SENTRY-INTEGRATION.md      # ⬆️ Moved to root
  └── active/
+     ├── NEW-FEATURES-OVERVIEW.md           # ✅ Now tracked
+     ├── code-analysis-metrics/             # ✅ Now tracked
+     ├── code-quality-standards/            # ✅ Now tracked
+     ├── cross-language-operations/         # ✅ Now tracked
+     ├── documentation-generation/          # ✅ Now tracked
+     ├── enhanced-duplication-detection/    # ✅ Now tracked
+     ├── refactoring-assistants/            # ✅ Now tracked
      └── repository-organization-analyzer/  # ✅ Already tracked
```

**mcp-docs/ Directories:**
```diff
  mcp-docs/
  ├── ast-grep/
  │   ├── README.md
- │   └── repomix-output.xml     # ❌ Removed (redundant)
  ├── [28 more servers...]
  ├── README.md
  └── repomix-output.xml          # ✅ Kept (main snapshot)
```

---

### 7.2 Quantitative Improvements

**File Count:**
- Before: 135 tracked files
- After: 113 tracked files (-22 redundant repomix files, +7 planning docs = -15 net)
- Reduction: 11% fewer tracked files

**Size Reduction:**
- Repomix cleanup: -116KB
- New planning docs: +100KB
- Net: -16KB

**Documentation Discoverability:**
- Before: 3 major docs at root (README, CLAUDE, ast-grep.mdc)
- After: 7 major docs at root (+BENCHMARKING, CONFIGURATION, DOPPLER, SENTRY)
- Improvement: 133% increase in root-level documentation

**Build Artifacts:**
- Before: 1 tracked build artifact (.coverage)
- After: 0 tracked build artifacts
- Improvement: 100% reduction ✅

---

### 7.3 Qualitative Improvements

**For Users:**
- ✅ Major feature documentation immediately visible (no navigation needed)
- ✅ Clearer project organization (tools in scripts/, docs at root)
- ✅ No build artifacts polluting git history

**For Developers:**
- ✅ All planning documents version-controlled (track evolution)
- ✅ Consistent file organization (tools in scripts/)
- ✅ Cleaner `git status` (no build artifacts)

**For Maintainers:**
- ✅ Less clutter (29 fewer redundant files)
- ✅ Standard Python project structure
- ✅ Easier onboarding (docs at root)

---

## 8. Testing Strategy

### 8.1 Pre-Migration Testing

```bash
# 1. Verify all tests pass before changes
uv run pytest
# Expected: 267 passed (or 266 passed, 1 skipped)

# 2. Verify no uncommitted changes
git status
# Expected: clean working directory (or only expected unstaged files)

# 3. Create backup branch
git checkout -b backup-before-refactor
git checkout main
```

---

### 8.2 Post-Migration Testing

**After Each Phase:**

```bash
# 1. Verify tests still pass
uv run pytest

# 2. Verify no broken imports
uv run python -c "import main; print('✅ Main imports OK')"

# 3. Verify documentation links
grep -r "\[.*\](.*\.md)" *.md | grep -v "^Binary" > /tmp/links.txt
# Manual review of links

# 4. Verify tools still executable
uv run python scripts/schema-tools.py --help
uv run python scripts/schema-graph-builder.py --help
uv run python scripts/find_duplication.py --help
```

**Final Verification:**

```bash
# 1. Full test suite
uv run pytest --cov=main --cov-report=term-missing

# 2. Linting
uv run ruff check .
uv run mypy main.py

# 3. Git status check
git status                               # Should show only expected changes
git ls-files | grep "\.coverage$"        # Should be empty

# 4. Documentation completeness
ls -1 *.md                               # Verify all moved docs present
ls -1 scripts/*.py                       # Verify all tools present
ls -1 dev/active/*/                      # Verify all planning dirs tracked
```

---

## 9. Communication Plan

### 9.1 Commit Messages

**Phase 1:**
```
chore: remove .coverage build artifact from git tracking

Build artifacts should not be version controlled.
The .coverage file is already in .gitignore (added Nov 17)
but was committed before that entry.
```

**Phase 2:**
```
docs: move major feature documentation to root for better discoverability

- Move BENCHMARKING.md to root (performance is core feature)
- Move CONFIGURATION.md to root (user-facing setup guide)
- Move DOPPLER-MIGRATION.md to root (major setup guide)
- Move SENTRY-INTEGRATION.md to root (major feature guide)
- Keep dev/README.md for development workflow
- Update all internal links

Improves discoverability for users browsing repository.
Follows Python project conventions (major docs at root).
```

**Phase 3:**
```
refactor: move standalone tools to scripts/ directory

- Move schema-tools.py to scripts/
- Move schema-graph-builder.py to scripts/
- Update documentation references

All standalone utilities now in scripts/ for consistency.
```

**Phase 4:**
```
chore: remove redundant per-server repomix snapshots

- Remove 29 per-server repomix files (116KB)
- Keep main snapshots: mcp-docs/, tests/, tests/fixtures/
- Add gitignore rule to prevent future per-server snapshots

Information preserved in main mcp-docs/repomix-output.xml snapshot.
```

**Phase 5:**
```
docs: add strategic feature planning documents

Add comprehensive planning for 6 major features:
- Enhanced duplication detection (4-6 weeks, HIGH PRIORITY)
- Code analysis & metrics (5-7 weeks)
- Refactoring assistants (6-8 weeks)
- Documentation generation (4-6 weeks)
- Code quality & standards (5-7 weeks)
- Cross-language operations (7-9 weeks)

Total: ~100KB of detailed strategic plans and task breakdowns.
Status: Planning complete, ready for prioritization.

Created via /dev-docs command on 2025-11-18.
```

**Phase 6:**
```
docs: update CLAUDE.md to reflect repository reorganization

- Update documentation paths (moved to root)
- Update tools paths (moved to scripts/)
- Document repomix cleanup (per-server snapshots removed)
- Update dev/active/ status (now tracked)
- Refresh repository structure section
```

---

### 9.2 Documentation Updates

**README.md Updates:**
1. "Standalone Tools" section - update paths
2. "Documentation" section - update links
3. Table of contents - add new root-level docs

**CLAUDE.md Updates:**
1. "Quick Start" section - update tool paths
2. "Standalone Tools" section - update paths
3. "Documentation" section - update links
4. "Repository Structure" section - reflect new organization
5. "Repomix Snapshots" section - document cleanup decision
6. "Recent Updates" section - add reorganization entry

---

## 10. Success Metrics

### 10.1 Acceptance Criteria

**Must Achieve (Mandatory):**
- [ ] .coverage no longer tracked in git
- [ ] All 267 tests still pass
- [ ] No broken documentation links
- [ ] All tools executable and functional
- [ ] ruff and mypy checks pass

**Should Achieve (Highly Desirable):**
- [ ] Major docs visible at root level
- [ ] All tools in scripts/ directory
- [ ] Per-server repomix files removed
- [ ] Planning documents tracked in git

**Nice to Have (Optional):**
- [ ] Updated CLAUDE.md reflects all changes
- [ ] Git history has clear commit messages
- [ ] No merge conflicts with existing branches

---

### 10.2 Measurement

**Before Metrics:**
```bash
git ls-files | wc -l                     # 135 files
git ls-files | grep "\.coverage$"        # .coverage (bad)
ls -1 *.md | wc -l                       # 3 docs at root
find mcp-docs/ -name "*.xml" | wc -l     # 32 repomix files
git ls-files dev/active/ | wc -l         # 2 tracked
```

**After Metrics:**
```bash
git ls-files | wc -l                     # ~120 files (-15)
git ls-files | grep "\.coverage$"        # (empty - good)
ls -1 *.md | wc -l                       # 7 docs at root (+4)
find mcp-docs/ -name "*.xml" | wc -l     # 3 repomix files (-29)
git ls-files dev/active/ | wc -l         # ~9 tracked (+7)
```

**Verification Script:**
```bash
#!/bin/bash
echo "=== Repository Organization Metrics ==="
echo "Tracked files: $(git ls-files | wc -l)"
echo "Build artifacts tracked: $(git ls-files | grep -c '\.coverage$' || echo 0)"
echo "Root docs: $(ls -1 *.md 2>/dev/null | wc -l)"
echo "Repomix snapshots: $(find mcp-docs/ tests/ -name "*.xml" 2>/dev/null | wc -l)"
echo "Scripts directory: $(ls -1 scripts/*.py 2>/dev/null | wc -l) tools"
echo "Planning docs tracked: $(git ls-files dev/active/ | wc -l) files"
echo ""
echo "=== Test Status ==="
uv run pytest --quiet --tb=no
echo ""
echo "=== Lint Status ==="
uv run ruff check . --quiet && echo "✅ ruff: PASS"
uv run mypy main.py --quiet && echo "✅ mypy: PASS"
```

---

## 11. Future Recommendations

### 11.1 Maintenance

**Monthly:**
- [ ] Regenerate main repomix snapshots (mcp-docs/, tests/)
- [ ] Review dev/active/ for completed features → archive
- [ ] Verify .gitignore prevents build artifacts

**Quarterly:**
- [ ] Review documentation for outdated content
- [ ] Check for new duplicate files
- [ ] Verify tests still cover 90%+ of main.py

**Yearly:**
- [ ] Consider splitting main.py if >6000 lines
- [ ] Review mcp-docs/ for removed servers
- [ ] Archive old planning documents

---

### 11.2 Scaling Considerations

**If main.py grows >6000 lines:**
Consider refactoring to module structure:
```
src/
├── __init__.py
├── server.py           # MCP server setup
├── ast_grep.py         # ast-grep tools
├── schema.py           # Schema.org tools
├── rewrite.py          # Code rewrite functionality
└── cache.py            # Caching logic
```

**If mcp-docs/ grows >50 servers:**
Consider organizing by category:
```
mcp-docs/
├── ai-ml/              # AI/ML servers
├── database/           # Database servers
├── dev-tools/          # Development tools
└── ...
```

---

## 12. Appendices

### Appendix A: Full File Manifest

**Files to Move:**
```
dev/BENCHMARKING.md              → BENCHMARKING.md
dev/CONFIGURATION.md             → CONFIGURATION.md
dev/DOPPLER-MIGRATION.md         → DOPPLER-MIGRATION.md
dev/SENTRY-INTEGRATION.md        → SENTRY-INTEGRATION.md
schema-tools.py                  → scripts/schema-tools.py
schema-graph-builder.py          → scripts/schema-graph-builder.py
```

**Files to Delete:**
```
mcp-docs/ast-grep/repomix-output.xml
mcp-docs/auth0/repomix-output.xml
mcp-docs/browserbase/repomix-output.xml
[... 26 more per-server repomix files ...]
```

**Files to Untrack:**
```
.coverage
```

**Files to Track:**
```
dev/active/NEW-FEATURES-OVERVIEW.md
dev/active/code-analysis-metrics/*
dev/active/code-quality-standards/*
dev/active/cross-language-operations/*
dev/active/documentation-generation/*
dev/active/enhanced-duplication-detection/*
dev/active/refactoring-assistants/*
```

---

### Appendix B: Link Update Commands

**Find all documentation links:**
```bash
grep -r "\[.*\](.*\.md)" *.md | grep -v "^Binary"
```

**Find references to moved files:**
```bash
grep -r "dev/BENCHMARKING\|dev/CONFIGURATION\|dev/DOPPLER\|dev/SENTRY" *.md
grep -r "schema-tools.py\|schema-graph-builder.py" *.md | grep -v "scripts/"
```

**Verify no broken links (after changes):**
```bash
# Extract all markdown links
grep -rh "\[.*\](.*\.md)" *.md | \
  sed 's/.*(\(.*\.md\).*/\1/' | \
  sort -u > /tmp/links.txt

# Verify each file exists
while read link; do
  if [ ! -f "$link" ]; then
    echo "❌ BROKEN: $link"
  else
    echo "✅ OK: $link"
  fi
done < /tmp/links.txt
```

---

### Appendix C: Emergency Rollback

**Full rollback to pre-refactor state:**
```bash
# Option 1: Revert all changes (creates reverse commits)
git log --oneline -10                    # Find first refactor commit
git revert <commit-hash>^..<latest>      # Revert range

# Option 2: Hard reset (destructive, loses commits)
git reflog                               # Find commit before refactor
git reset --hard <commit-hash>

# Option 3: Restore from backup branch
git checkout backup-before-refactor
git branch -D main
git checkout -b main
```

**Partial rollback (single phase):**
```bash
git log --oneline --grep="<phase-keyword>"  # Find phase commit
git revert <commit-hash>                     # Revert that phase
```

---

## Conclusion

This refactoring plan provides a systematic, low-risk approach to improving repository organization. All changes are:

✅ **Reversible** (git-tracked)
✅ **Testable** (verification steps provided)
✅ **Incremental** (6 independent phases)
✅ **Low-risk** (no code changes, only file moves)
✅ **High-value** (better discoverability, cleaner structure)

**Total Effort:** 70 minutes
**Total Risk:** Low
**Recommended Approach:** Execute phases 1-6 sequentially in a single session

**Next Step:** Begin Phase 1 (Critical Fixes)

---

**Document Status:** Ready for Execution
**Last Updated:** 2025-11-18
**Prepared By:** Repository Organization Analyzer
