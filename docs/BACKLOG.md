# Backlog

**See [docs/changelog/2026-03-08-complexity-refactoring-queue.md](changelog/2026-03-08-complexity-refactoring-queue.md) for historical complexity refactoring metrics (434 → 0 offenders, 2026-03-08 refresh completed 2026-03-09).**






## Deferred

- [ ] **DRY-01** (P1) Replace `_run_tool()` with `tool_context` in cross_language — consolidate timing + error handling in `cross_language/tools.py:40-57` with shared `tool_context`. Removes ~20 lines and aligns with all other tool modules. Affects 5 cross-language tools. -- `src/ast_grep_mcp/features/cross_language/tools.py:40-57` (2026-03-08 DRY review)
- [ ] **DRY-02** (P1) Replace hardcoded exclude patterns with `FilePatterns` — 8 files (detector.py, sync_checker.py, readme_generator.py, api_docs_generator.py, security_scanner.py, estimator.py, executor.py, orphan.py) hardcode their own exclude lists instead of using `constants.FilePatterns.DEFAULT_EXCLUDE` and `SKIP_DIR_NAMES`. Removes ~40 lines and establishes single source of truth. -- `src/ast_grep_mcp/constants.py` + 8 files (2026-03-08 DRY review)
- [ ] **DRY-03** (P2) Adopt `read_file_lines` + `write_file_lines` in 4 files — polyglot_refactoring.py, renamer.py, fixer.py, sync_checker.py each manually open/read files. Consolidate via shared utils. Removes ~12 lines and ensures consistent error handling. -- `src/ast_grep_mcp/utils/text.py` (2026-03-08 DRY review)
- [ ] **DRY-04** (P3) Remove redundant re-timing inside `tool_context` — 20+ tools in condense, documentation, schema, quality modules calculate elapsed time manually after `tool_context` already reports it. Removes ~30 lines of noise. -- `src/ast_grep_mcp/features/{condense,documentation,schema,quality}/tools.py` (2026-03-08 DRY review)
- [ ] **DRY-05** (P3) Add `generate_backup_timestamp()` helper — rewrite/backup.py and deduplication/applicator_backup.py both call `datetime.now().strftime(...)` identically 3 times. Consolidate into shared helper. Removes ~6 lines. -- `src/ast_grep_mcp/utils/backup.py` (2026-03-08 DRY review)
- [ ] **DRY-06** (P3) Consolidate `LANGUAGE_EXTENSIONS` maps — `analyze_codebase.py:39` defines `{lang: "ext"}` (singular) while `src/ast_grep_mcp/constants.py:361` defines `{lang: ["ext", ...]}` (list). `scripts/api_docs_generator.py` has a third variant. Converge on one shape in `constants.py` and adopt across scripts. -- `analyze_codebase.py:39`, `scripts/api_docs_generator.py` (2026-04-23 analyze_codebase reuse review)
- [ ] **DRY-07** (P3) Extract shared `find_source_files(root, language, exclude_patterns)` helper — `analyze_codebase.py:74`, `scripts/sync_checker.py`, and `scripts/api_docs_generator.py` each reinvent `rglob + exclude` discovery. Candidate home: `utils/file_discovery.py`. -- `src/ast_grep_mcp/utils/` (2026-04-23 analyze_codebase reuse review)
- [ ] **DRY-08** (P3) Extract `_run_tsc_check`-style subprocess runner — `analyze_codebase.py:335-371` duplicates subprocess-with-timeout + output-parsing patterns found in `features/rewrite/service.py` and formatter wrappers. Candidate home: `core/executor.py` or new `utils/subprocess_runner.py`. -- `analyze_codebase.py:335` (2026-04-23 analyze_codebase reuse review)
- [ ] **DRY-09** (P4) Delete `out()` wrapper in `analyze_codebase.py:53-55` — thin passthrough to `console.log(str(...))`; ~40 callsites could call `console.log` directly. Low priority (churn vs. clarity). -- `analyze_codebase.py:53` (2026-04-23 analyze_codebase reuse review)
- [ ] **HC-01** (P2) Add ESLint to pre-commit hooks — integrate `npm run lint:fix && npm run check` for TypeScript verification at commit time. Reduces lint-on-CI friction and catches issues earlier. -- `hooks/`
- [ ] **DF-01** (Low) Strategy pattern filter for deduplication — per `docs/duplicate-detector-misses.md` investigation. Only candidate (Group 5) would save ~18 lines with minor signature mismatch; over-engineering for marginal benefit. (deferred 2026-03-08)
- [ ] **CF-04** (P3) Config-aware search mode — complex feature for PM2/Zod/JSON-LD config patterns. Deferred from 2026-03-11 session as out of scope. -- `src/ast_grep_mcp/features/search/`
- [ ] **SR-01** (P2) Unit tests for security scanner — add pytest test file for `detect_security_issues_impl()` covering SQL injection, XSS, command injection, secrets, and crypto patterns. Currently no test coverage. -- `tests/unit/test_detect_security_issues.py` (new)
- [ ] **SR-02** (P3) Integration tests for Python security YAML rules — validate that 12 rules in `rules/python-security-high-priority.yaml` fire correctly on sample vulnerable code. Add test fixtures for each CWE. -- `tests/integration/test_python_security_rules.py` (new)
- [ ] **SR-03** (P3) Document Python security rule coverage — create guide explaining which CWEs are covered (798, 327, 489, 521, 532, 377, 295), known limitations (e.g., follow/precedes matching edge cases), and migration path for integrating rules into quality/rules.py template system. -- `docs/PYTHON-SECURITY-RULES-GUIDE.md` (new)
- [ ] **SR-04** (P4) Expand security pattern examples — add coverage for additional CWE types (330: Use of Insufficiently Random Values, 434: Unrestricted Upload, 611: XXE). Currently 30+ patterns focused on CWE-798/327/489/521. -- `src/ast_grep_mcp/features/search/pattern_examples.json`

## Completed Items (Migrated to Changelog)

- [x] **LM-01–LM-05** Library Migration Phase 1–2 → [docs/changelog/2026-04-19-library-migration-phase1-phase2.md](changelog/2026-04-19-library-migration-phase1-phase2.md)
- [x] **FG-01** Schema detection Liquid/Jekyll template fallback → [docs/changelog/2026-04-20-schema-liquid-jekyll-fallback.md](changelog/2026-04-20-schema-liquid-jekyll-fallback.md)
- [x] **MQ-01–MQ-02** Minor Code Quality Items → [docs/changelog/2026-03-12-minor-code-quality-items.md](changelog/2026-03-12-minor-code-quality-items.md)
- [x] **PA-01–PA-05** Pattern Analysis performance optimization → [docs/changelog/2026-04-20-pattern-analysis-performance-optimization.md](changelog/2026-04-20-pattern-analysis-performance-optimization.md)
- [x] **PA-06** Parallel candidate scoring → [docs/changelog/2026-04-20-pa06-parallel-scoring.md](changelog/2026-04-20-pa06-parallel-scoring.md)

