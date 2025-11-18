# Enhanced Duplication Detection - Context & Decisions

**Last Updated:** 2025-11-18
**Status:** Planning
**Next Review:** Start of Phase 1

---

## Key Files & Locations

### Existing Implementation

**Core Duplication Detection:**
- `main.py:1571-1828` - `find_duplication()` tool (257 lines)
- `main.py:3206-3275` - `generate_refactoring_suggestions()` (69 lines)
- `main.py:3108-3204` - `group_duplicates()` with hash bucketing (96 lines)
- `main.py:3042-3105` - `calculate_similarity()` using difflib (63 lines)

**Related Tools:**
- `main.py:1369-1569` - `rewrite_code()` tool with backup system
- `main.py:3387-3447` - Backup/rollback utilities

**Standalone Scripts:**
- `scripts/find_duplication.py` - CLI interface (226 lines)
- `scripts/find_duplication.sh` - Bash wrapper

**Tests:**
- `tests/unit/test_duplication.py` - 24 test cases
- `tests/integration/test_integration.py` - Integration tests

**Documentation:**
- `CLAUDE.md:151-168` - Current duplication detection docs
- `scripts/README.md` - Standalone script documentation

### Files to Create

**Phase 1:**
- `main.py` - Add pattern analysis functions (new section)

**Phase 2:**
- `main.py` - Add code generation functions (new section)

**Phase 3:**
- `main.py` - Add `apply_deduplication()` tool
- `tests/unit/test_deduplication_apply.py` - New test file

**Phase 4:**
- `main.py` - Add `analyze_deduplication_candidates()` tool
- `tests/unit/test_deduplication_ranking.py` - New test file

**Phase 5:**
- `scripts/find_duplication.py` - Enhanced CLI with detailed mode
- `DEDUPLICATION-GUIDE.md` - Comprehensive user guide

**Phase 6:**
- `tests/integration/test_deduplication_e2e.py` - End-to-end tests
- `CLAUDE.md` - Update with new tools

---

## Dependencies

### External Dependencies (Already Available)

- **ast-grep CLI:** Pattern matching and code search (already installed)
- **difflib (stdlib):** Text similarity calculation (no install needed)
- **ast (stdlib):** Python AST parsing (no install needed)
- **subprocess (stdlib):** Execute ast-grep commands
- **FastMCP:** MCP server framework (already in use)
- **pydantic:** Input validation (already in use)
- **sentry-sdk:** Error tracking (already configured)

### New Dependencies (if needed)

**Python AST Parsing:**
- ✅ Use stdlib `ast` module (no new dependency)

**TypeScript/JavaScript AST:**
- Option 1: Call `tsc` or Node-based parser via subprocess
- Option 2: Use ast-grep's JSON output (preferred, no new dependency)
- **Decision:** Use ast-grep JSON output, fallback to text diff

**Java AST:**
- Option 1: Use `javac` tree API via subprocess
- Option 2: Use ast-grep JSON output (preferred)
- **Decision:** Use ast-grep JSON, defer full Java support to Phase 4+

### Internal Dependencies

**Requires:**
- `stream_ast_grep_results()` - Already exists
- `run_ast_grep()` - Already exists
- Backup system - Already exists in `rewrite_code()`
- Syntax validation - Already exists for Python/JS/TS

**Builds On:**
- `find_duplication()` - Enhance, don't replace
- `generate_refactoring_suggestions()` - Extend significantly
- `rewrite_code()` - Integrate for multi-file changes

---

## Key Decisions

### Decision 1: Enhance vs. Rewrite
**Date:** 2025-11-18
**Decision:** Enhance existing `find_duplication()`, don't rewrite
**Rationale:**
- Existing tool works well for basic detection
- Tests already cover edge cases
- Preserve backward compatibility
- Add opt-in `analysis_mode` parameter for enhanced features
**Impact:** Less risk, faster development

### Decision 2: Analysis Depth
**Date:** 2025-11-18
**Decision:** Make detailed analysis opt-in via `analysis_mode` parameter
**Rationale:**
- Detailed analysis is more expensive (AST parsing, diff)
- Many users just want quick duplication scan
- Default behavior: "suggestions" (current behavior)
- Enhanced behavior: "detailed" (parameter extraction, code gen)
**Impact:** Performance-conscious, backward compatible

### Decision 3: AST vs. Text-Based Diff
**Date:** 2025-11-18
**Decision:** Prefer AST-based diff, fallback to text diff
**Rationale:**
- AST diff is more accurate for parameter extraction
- Text diff is more reliable/portable
- ast-grep already provides AST via JSON output
- Fallback ensures robustness
**Impact:** Best of both worlds

### Decision 4: Language Support Priority
**Date:** 2025-11-18
**Decision:** Phase 1-3: Python, TypeScript, JavaScript. Phase 4+: Java, others
**Rationale:**
- Python and TypeScript are most common in target projects
- Simpler syntax for initial implementation
- ast-grep supports all languages, but code gen varies
- Test with 2-3 languages before expanding
**Impact:** Faster MVP, reduced scope

### Decision 5: Integration with rewrite_code
**Date:** 2025-11-18
**Decision:** Reuse existing backup system, don't duplicate
**Rationale:**
- `rewrite_code()` already has robust backup/rollback
- Consistent backup format across tools
- Leverage existing tests
- Users already familiar with workflow
**Impact:** Less code, more consistency

### Decision 6: Dry-Run Default
**Date:** 2025-11-18
**Decision:** `apply_deduplication` defaults to `dry_run=True`
**Rationale:**
- Safety first: preview before applying
- Matches `rewrite_code` pattern
- Reduces accidental destructive changes
- User must explicitly opt-in to actual changes
**Impact:** Safer, better UX

### Decision 7: New Tools vs. Enhanced Existing
**Date:** 2025-11-18
**Decision:** Create 2 new tools (`apply_deduplication`, `analyze_deduplication_candidates`) + enhance 1 existing (`find_duplication`)
**Rationale:**
- Clear separation of concerns
- `find_duplication`: detection + analysis
- `apply_deduplication`: automation
- `analyze_deduplication_candidates`: prioritization
- Each tool is independently useful
**Impact:** Clearer API, modular design

---

## Architecture Decisions

### Pattern Analysis Architecture

```
Input: List of duplicate matches from ast-grep
  ↓
Extract AST from each match (ast-grep JSON output)
  ↓
Align AST nodes by structure
  ↓
Identify differing nodes (literals, identifiers, expressions)
  ↓
Generate parameters from differences
  ↓
Classify variations (simple, complex, conditional)
  ↓
Output: Parameter list + variation classification
```

**Key Components:**
- AST extraction: Use ast-grep `--json=stream` output
- Node alignment: Match by position and type
- Diff detection: Compare node values
- Parameter naming: Heuristics from context (variable names, literals)

### Code Generation Architecture

```
Input: Duplicate group + extracted parameters
  ↓
Load template for language/construct type
  ↓
Generate function signature (name, params, types)
  ↓
Generate function body (use first duplicate as base)
  ↓
Generate replacement calls (substitute params at each site)
  ↓
Generate import statements (add/remove as needed)
  ↓
Validate syntax of generated code
  ↓
Output: Complete refactoring code
```

**Key Components:**
- Template system: Language-specific function/class templates
- Signature generation: Infer types from context
- Body generation: Replace varying parts with parameters
- Call generation: Build function calls with extracted arguments
- Import management: Track and update imports

### Application Architecture

```
Input: Refactoring plan from find_duplication
  ↓
Create backup (via existing backup system)
  ↓
Plan file modifications (extract to file X, update files Y, Z)
  ↓
Generate diffs for preview (if dry_run)
  ↓
Apply changes atomically (if not dry_run):
  1. Create extracted function file (or add to existing)
  2. Replace duplicates with calls
  3. Update imports
  ↓
Validate syntax of all modified files
  ↓
Rollback if validation fails
  ↓
Output: Backup ID, diffs, validation results
```

**Key Components:**
- Backup integration: Use existing `create_backup_metadata()`
- Multi-file orchestration: Plan order, handle failures
- Diff generation: Use difflib to create unified diffs
- Atomic changes: Transaction model (all or nothing)
- Validation: Existing syntax validators

---

## Technical Constraints

### Performance Constraints

**Current Performance:**
- `find_duplication()` on 1000 functions: ~5-10 seconds
- Hash-based bucketing reduces comparisons 83%
- Streaming results for large codebases

**Target Performance:**
- Detailed analysis: <2x current time (10-20 seconds for 1000 functions)
- Code generation: <1 second per group
- Full refactoring: <5 seconds typical case

**Optimization Strategies:**
- Cache AST parsing results
- Parallelize group analysis (ThreadPoolExecutor)
- Lazy evaluation (only analyze groups user selects)
- Limit detailed analysis to top N candidates

### Safety Constraints

**Must-Have Safety Features:**
- ✅ Syntax validation before and after changes
- ✅ Automatic backup before modifications
- ✅ Full rollback capability
- ✅ Dry-run mode as default
- ✅ Clear warning for risky refactorings

**Risk Indicators:**
- Missing test coverage
- High complexity score (>7/10)
- External dependencies detected
- Conditional logic variations
- Multi-file modifications

### Compatibility Constraints

**Backward Compatibility:**
- Existing `find_duplication()` API must remain unchanged
- New features opt-in via `analysis_mode` parameter
- JSON response schema extends, doesn't break
- Existing tests must pass

**Language Compatibility:**
- Phase 1-3: Python, TypeScript, JavaScript
- Phase 4+: Java, Go, others
- Graceful degradation for unsupported languages
- Clear error messages for language limitations

---

## Open Questions

### Question 1: Where to Place Extracted Functions?
**Status:** Needs Decision
**Options:**
1. **Auto-detect:** Find common parent module, create `utils.py`/`utils.ts`
2. **User-specified:** Require `extract_to_file` parameter
3. **Same file as first duplicate:** Add to existing file

**Recommendation:** Option 1 (auto-detect) with Option 2 (user override) fallback

**Decision Needed By:** Phase 2 start

---

### Question 2: How to Name Extracted Functions?
**Status:** Needs Decision
**Options:**
1. **Auto-generate:** Use pattern like `extracted_function_1`
2. **Infer from code:** Use common terms in function names
3. **User-specified:** Require `extract_function_name` parameter
4. **Hybrid:** Auto-generate but allow override

**Recommendation:** Option 4 (hybrid) - auto-generate descriptive name, allow override

**Decision Needed By:** Phase 2 start

---

### Question 3: Handle Type Annotations?
**Status:** Needs Research
**Consideration:**
- Python: Type hints optional, infer from usage?
- TypeScript: Type required, infer from literals?
- JavaScript: No types (skip)

**Recommendation:** Phase 1: infer simple types (str, int, bool), Phase 2: advanced types

**Decision Needed By:** Phase 2 middle

---

### Question 4: Multi-Language Refactoring?
**Status:** Deferred
**Scenario:** Duplicates span multiple languages (rare)

**Recommendation:** Phase 1-3: single language only, Phase 4+: research multi-language

**Decision Needed By:** Phase 4

---

## Blockers & Dependencies

### Current Blockers
- None (all dependencies available)

### Potential Blockers
1. **AST Parsing Reliability:** If ast-grep JSON output insufficient, may need native parsers
   - **Mitigation:** Fallback to text-based diff
   - **Risk:** Low

2. **TypeScript Parser Access:** May need Node.js subprocess for TS parsing
   - **Mitigation:** Use ast-grep JSON output
   - **Risk:** Low

3. **Performance on Large Codebases:** Analysis may be too slow
   - **Mitigation:** Opt-in detailed mode, caching, parallelization
   - **Risk:** Medium

---

## Success Criteria

### Phase 1 Success Criteria
- ✅ Parameter extraction accuracy >90%
- ✅ Complexity scoring calibrated (low/med/high)
- ✅ Enhanced suggestions include parameter details
- ✅ All existing tests pass
- ✅ 20+ new tests for pattern analysis

### Phase 2 Success Criteria
- ✅ Generated Python code is syntactically valid
- ✅ Generated TypeScript code is syntactically valid
- ✅ Call sites preserve behavior
- ✅ Import management works correctly
- ✅ 30+ new tests for code generation

### Phase 3 Success Criteria
- ✅ Dry-run preview shows accurate diffs
- ✅ Applied refactoring passes all tests
- ✅ Rollback works 100% of the time
- ✅ Multi-file changes are atomic
- ✅ 20+ new tests for application

### Phase 4 Success Criteria
- ✅ Ranking prioritizes high-value refactorings
- ✅ Test coverage detection is accurate
- ✅ Top 5 recommendations are actionable
- ✅ 10+ new tests for ranking

### Phase 5 Success Criteria
- ✅ CLI output is user-friendly
- ✅ Diffs are readable and accurate
- ✅ Documentation is comprehensive
- ✅ Examples are clear

### Phase 6 Success Criteria
- ✅ >95% test coverage for new code
- ✅ All documentation updated
- ✅ Performance benchmarks pass
- ✅ Ready for production use

---

## Notes & Observations

### 2025-11-18: Initial Planning
- Reviewed existing `find_duplication()` implementation
- Identified 257 lines of existing code to build on
- Confirmed all dependencies available (no new installs needed)
- Estimated 4-6 weeks for full implementation
- Designed 3-tool architecture (enhance 1, create 2 new)

### Key Insights
- Hash-based bucketing (83% speedup) should be preserved
- Backup system already solid, reuse it
- ast-grep JSON output is rich enough for AST analysis
- Text-based fallback ensures robustness
- Dry-run workflow matches existing UX patterns

### Potential Future Enhancements (Post-MVP)
- Machine learning for parameter naming
- Template customization (user-defined templates)
- Multi-repository refactoring
- Integration with IDE plugins
- Batch refactoring (apply all high-confidence candidates)
- Refactoring history tracking

---

**End of Context Document**
**Last Updated:** 2025-11-18
