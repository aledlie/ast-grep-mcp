# Backlog

**See [docs/changelog/2026-03-08-complexity-refactoring-queue.md](changelog/2026-03-08-complexity-refactoring-queue.md) for historical complexity refactoring metrics (434 → 0 offenders, 2026-03-08 refresh completed 2026-03-09).**






## Deferred

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

