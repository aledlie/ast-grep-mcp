# Changelog

All notable changes to ast-grep-mcp are documented in version-dated files in the `changelog/` directory.

**Current Total:** 53 MCP tools | 120 modules | 1,622 tests

## Versions

- [2026-03-08: Review Follow-ups & Test Coverage](changelog/2026-03-08-review-follow-ups-testing.md) — Sentry exception capture, logger parameter deduplication, version resolution consistency
- [2026-03-08: Shared Utils & Tool Consolidation](changelog/2026-03-08-shared-utils-consolidation.md) — shared utility extractions, tool_context, normalize_excludes, inline Field() pattern
- [2026-03-08: Complexity Analysis](changelog/2026-03-08-complexity-analysis.md) — 98 functions exceeding thresholds across 22 modules
- [2026-03-08: Changelog Hardening & Test Quality](changelog/2026-03-08-changelog-hardening-test-quality.md) — 4 hardening + 5 test quality items, 1 open issue
- [2026-03-08: Code Quality Fixes](changelog/2026-03-08-quality-fixes.md) — 2 items (magic number, assert)
- [2026-03-08: Code Review Findings Resolution](changelog/2026-03-08-code-review-findings.md) — 4 items (M1, M2, M3, L1)
- [2026-03-07: Type Fixes & Formatting](changelog/2026-03-07-type-fixes-formatting.md) — mypy cross-env suppression, ruff format 42 files
- [2026-03-06: Complexity Refactoring + Code Review Fixes + Duplication](changelog/2026-03-06-complexity-review-fixes.md) — 24 items + post-refactoring lint/type fixes
- [2026-03-06: Critical Bug Fixes](changelog/2026-03-06-critical-bug-fixes.md) — exception consolidation, stderr deadlock, process cleanup
- [2026-03-04: Maintenance + Quality Updates](changelog/2026-03-04-maintenance-quality.md)
- [2026-02-28: Analyzer CLI, Syntax Validation, Quality Fixes](changelog/2026-02-28-analyzer-cli-quality.md) — includes 2026-03-01 off-by-one fix
- [2026-02-26: JSDoc Parsing & Project Context](changelog/2026-02-26-jsdoc-fixes.md) — JSDoc generics/optional param fixes
- [2026-02-25: Code Condensation Feature](changelog/2026-02-25-code-condensation.md) — 6 new tools, 81+ tests
- [2026-02-25: Condense Cleanup](changelog/2026-02-25-condense-cleanup.md)
- [2026-02-12: Formatting & Dedup Refactoring](changelog/2026-02-12-formatting-refactoring.md) — ruff format 72 files, nesting fix, pillow dep
- [2026-02-10: Test Stability & Documentation](changelog/2026-02-10-test-stability-docs.md) — +1 tool (develop_pattern)
- [2026-01-10: Documentation & Rule Builder Tools](changelog/2026-01-10-docs-rule-builder.md) — +3 tools, warning system
- [2026-01-09: Pattern Debugging Tool](changelog/2026-01-09-pattern-debugging.md) — +1 tool (debug_pattern)
- [2025-12-02 thru 2025-12-04: Dedup Phase 5 & Modular Migration](changelog/2025-12-02-thru-2025-12-04-dedup-phase5-modular.md) — MinHash/LSH, CodeBERT, hybrid similarity, modular imports
- [2025-11-23 thru 2025-11-30: Foundation Features](changelog/2025-11-23-thru-2025-11-29.md) — modular architecture, dedup, quality, security, schema, docs generation, Sentry, DRY tool

## Tool Addition Timeline

| Date | Feature | Tools Added |
|------|---------|-------------|
| 2026-02-25 | Code Condensation | +6 (condense_extract_surface, condense_normalize, condense_strip, condense_pack, condense_estimate, condense_train_dictionary) |
| 2026-02-10 | Test Stability & Docs | +1 (develop_pattern) |
| 2026-01-10 | Documentation & Rule Builder | +3 (get_ast_grep_docs, build_rule, get_pattern_examples) |
| 2026-01-09 | Pattern Debugging | +1 (debug_pattern) |
| 2025-11-29 | Entity Graph Enhancement | +1 (enhance_entity_graph) |
| 2025-12-03 | Orphan Detection | +1 (detect_orphans) |
| 2025-12-02 | Dedup Phase 5 | +0 (internal: MinHash/LSH, CodeBERT, hybrid similarity) |
| 2025-11-29 | Documentation Generation | +5 (docstrings, readme, api_docs, changelog, sync) |
| 2025-11-29 | Entity Graph Enhancement | +1 (enhance_entity_graph) |
| 2025-11-27 | Security Scanner | +3 (detect_security_issues, apply_standards_fixes, generate_quality_report) |
| 2025-11-26 | Refactoring Assistants | +2 (extract_function, rename_symbol) |
| 2025-11-24 | Modular Architecture | Multiple tools |
| 2025-11-23 | Enhanced Deduplication | Multiple tools |
| 2025-11-10 | DRY Analysis | +1 (DRY tool) |
