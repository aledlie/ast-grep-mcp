# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### 2026-01-10: Documentation & Rule Builder Tools + Warning System

Based on the [ast-grep Prompting Guide](https://ast-grep.github.io/advanced/prompting.html), implemented comprehensive improvements to reduce LLM hallucinations and improve pattern/rule accuracy.

**New Tools:**

1. **`get_ast_grep_docs`** - On-demand documentation retrieval
   - Topics: `pattern`, `rules`, `relational`, `metavariables`, `workflow`, `all`
   - Reduces hallucinations by providing accurate reference content
   - Location: `src/ast_grep_mcp/features/search/docs.py`

2. **`build_rule`** - YAML rule builder with automatic best practices
   - Automatically adds `stopBy: end` to relational rules (prevents #1 mistake!)
   - Supports pattern-based and kind-based relational rules (`inside`, `has`, `follows`, `precedes`)
   - Auto-generates unique rule IDs
   - Returns valid YAML ready for `find_code_by_rule`
   - Location: `src/ast_grep_mcp/features/search/service.py`

3. **`get_pattern_examples`** - Common patterns by language and category
   - Categories: `function`, `class`, `import`, `variable`, `control_flow`, `error_handling`, `async`, `all`
   - Languages: JavaScript, TypeScript, Python, Go, Rust, Java, Ruby, C, C++
   - Provides ready-to-use patterns with explanations

**Automatic Warning Detection:**

- `find_code_by_rule` now detects common mistakes in YAML rules:
  - Missing `stopBy` in relational rules (`inside`, `has`, `follows`, `precedes`)
  - Lowercase metavariables in patterns (e.g., `$name` instead of `$NAME`)
- Warnings prepended to text output
- JSON output includes `{"warnings": [...], "matches": [...]}`
- Location: `src/ast_grep_mcp/features/search/service.py`

**Enhanced Tool Descriptions:**

- `find_code_by_rule`: Added stopBy warning with correct/incorrect examples, minimal rule templates, composite rules guidance
- `debug_pattern`: Added metavariable quick reference table, common mistakes detected
- All search tools now include pattern syntax quick reference

**Implementation Details:**

- New documentation module: `docs.py` with comprehensive ast-grep reference
- Helper functions: `_check_relational_rule_for_stopby()`, `_check_yaml_rule_for_common_mistakes()`
- 24+ new tests in `tests/unit/test_docs_and_rule_builder.py`

**References:**
- [ast-grep Prompting Guide](https://ast-grep.github.io/advanced/prompting.html)
- [Pattern Syntax Reference](https://ast-grep.github.io/guide/pattern-syntax.html)
- [Rule Configuration](https://ast-grep.github.io/reference/rule.html)

---

#### 2026-01-09: Pattern Debugging Tool

- Added `debug_pattern` tool for diagnosing why patterns don't match code
- Validates metavariable syntax (detects `$name` vs `$NAME`, `$123`, `$KEBAB-CASE` errors)
- Compares pattern AST with code AST to find structural mismatches
- Attempts actual matching and reports results
- Provides prioritized suggestions for fixing pattern issues
- Warns about common mistakes like using `$ARG` instead of `$$$ARGS` for function arguments
- New models: `pattern_debug.py` with 8 dataclasses/enums
- 31 new tests for pattern debugging
- Total MCP tools: 43

---

#### 2025-11-29: Entity Graph Enhancement Tool

- Added `enhance_entity_graph` tool for analyzing existing Schema.org JSON-LD graphs
- Suggests missing properties based on Schema.org vocabulary and Google Rich Results guidelines
- Suggests missing entity types (FAQPage, WebSite, BreadcrumbList, Review)
- Calculates SEO completeness scores (0-100) for entities and overall graph
- Validates @id references across the graph
- Three output modes: analysis, enhanced (with placeholders), diff (additions only)
- 51 new tests covering all enhancement functionality
- New models: `schema_enhancement.py` with 6 dataclasses/enums
- New modules: `enhancement_rules.py`, `enhancement_service.py`
- Total MCP tools: 38

---

#### 2025-11-29: Documentation Generation Feature

- Added `generate_docstrings` tool with 5 docstring styles (Google, NumPy, Sphinx, JSDoc, Javadoc)
- Added `generate_readme_sections` tool with project analysis
- Added `generate_api_docs` tool with OpenAPI 3.0 spec generation
- Added `generate_changelog` tool with Keep a Changelog and Conventional formats
- Added `sync_documentation` tool for detecting stale docs and broken links
- 32 new tests for documentation generation
- Total MCP tools: 37

---

#### 2025-11-28: Phase 2 Complexity Refactoring Complete

- **ZERO violations achieved** (48 → 0 functions, 100% complete)
- Refactored all 25 remaining complex functions
- Created [PATTERNS.md](PATTERNS.md) with proven refactoring techniques
- Quality gate now **PASSING** (15/15 regression tests)
- 278 module tests passing (all refactored code verified)
- Key achievements:
  - 100% cognitive reduction in `_assess_breaking_change_risk` (44→0)
  - 97% cognitive reduction in `_parallel_enrich` (74→2, highest violation)
  - 94% reduction in both `_extract_classes` functions (35→2 each)
  - Eliminated 118 lines of duplicate code via DRY principle
  - Created shared `utils/syntax_validation.py` module

---

#### 2025-11-27: Security Scanner & Auto-Fix

- Added `detect_security_issues` tool (SQL injection, XSS, command injection, secrets, crypto)
- Added `apply_standards_fixes` tool with safety classification
- Added `generate_quality_report` tool (Markdown/JSON formats)

---

#### 2025-11-26: Refactoring Assistants

- Added `extract_function` tool with parameter/return detection
- Added `rename_symbol` tool with scope-aware renaming
- 32 tests passing for both tools

---

#### 2025-11-25: Tool Registration Complete

- 100% tool registration (38 tools)
- Consistent two-layer pattern (standalone + MCP wrapper)

---

#### 2025-11-24: Modular Architecture & Code Quality

- Migrated to 64-module architecture
- Added code complexity analysis tools
- Added code smell detection
- Created linting rule system (24+ templates)
- `main.py` reduced to entry point only (10 lines)

---

#### 2025-11-23: Enhanced Deduplication

- Complete rewrite with intelligent analysis
- Automated refactoring with validation
- 1,000+ new tests
- 9+ language test coverage support

---

## Summary

| Date | Feature | Tools Added |
|------|---------|-------------|
| 2026-01-10 | Documentation & Rule Builder | +3 (get_ast_grep_docs, build_rule, get_pattern_examples) |
| 2026-01-09 | Pattern Debugging | +1 (debug_pattern) |
| 2025-11-29 | Entity Graph Enhancement | +1 (enhance_entity_graph) |
| 2025-11-29 | Documentation Generation | +5 (docstrings, readme, api_docs, changelog, sync) |
| 2025-11-28 | Phase 2 Refactoring | Quality improvements only |
| 2025-11-27 | Security Scanner | +3 (detect_security_issues, apply_standards_fixes, generate_quality_report) |
| 2025-11-26 | Refactoring Assistants | +2 (extract_function, rename_symbol) |
| 2025-11-25 | Tool Registration | Infrastructure only |
| 2025-11-24 | Modular Architecture | Multiple tools |
| 2025-11-23 | Enhanced Deduplication | Multiple tools |

**Current Total:** 46 MCP tools
