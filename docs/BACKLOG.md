# Backlog


## Complexity Refactoring Queue (2026-03-08 refresh)

Thresholds: cyc >10, cog >15, nest >4, len >50.
Full analysis: [docs/COMPLEXITY-REPORT.md](COMPLEXITY-REPORT.md) (generated 2026-03-09).

> **Maintenance:** When resolving a CX-* item, update both this backlog (mark `[x]`) and the Recommendations section of `docs/COMPLEXITY-REPORT.md` to reflect the new metrics. Re-run the complexity tools to refresh the report when the remaining offender count changes significantly.

Previous baselines: **434** (2026-03-04) → **407** (2026-03-06) → **100** (2026-03-08) → **80** (2026-03-08 shared-util) → **25** (2026-03-08 helper-adoption) → **19** (2026-03-08 condense-decompose) → **18** (2026-03-08 dead-code-removal) → **17** (2026-03-08 docstring-extent-decompose) → **16** (2026-03-08 nested-diff-decompose) → **15** (2026-03-08 filter-files-decompose) → **11** (2026-03-09 analyzer-decompose) → **7** (2026-03-09 complexity-reductions) → **0** (2026-03-09 remaining-offenders).

### Recently Resolved

- **`condense/service.py`** (uncommitted) — all 5 offenders resolved. `condense_pack_impl` (was cyc=15, cog=29, nest=5, len=115) decomposed into `_accumulate_pack_results` + `_build_pack_result`. `extract_surface_impl` (was cyc=12, cog=15, len=73) extracted `_accumulate_surface_results`. `_count_structural_braces` (was cyc=17, cog=28, nest=5) simplified via `CondenseParsing.BRACE_DELTA` lookup. `_extract_python_surface` (was cog=17) and `_extract_js_ts_surface` (was cyc=12) also dropped below thresholds.
- **`deduplication/diff.py:diff_preview_to_dict`** — no longer exceeds thresholds (was cyc=14, cog=29, nest=5, len=53).
- **`constants.py`** (uncommitted) — added `CondenseParsing` class (`QUOTE_CHARS`, `BRACE_DELTA`) to replace magic brace/quote chars in condense and renamer.
- **`refactoring/renamer.py`** (uncommitted) — replaced magic `{`/`}` brace handling with `CondenseParsing.BRACE_DELTA` lookup.
- **`core/executor.py:stream_ast_grep_results`** (`0642b3f`) — extracted `_iter_stdout_matches` (yield-from delegation), `_log_stream_completion`, `_raise_not_found_error`. cyc 16→4, cog 29→2, nest 6→2, len 101→52. Note: len=52 still marginally exceeds len>50 threshold.
- **`deduplication/applicator_backup.py`** (`7880737`, `c847003`) — all 4 functions now below thresholds. Extracted helpers to class + shared `utils/backup.py` primitives (`get_file_hash`, `resolve_backup_dir`, `copy_file_to_backup`, `restore_file_from_backup`). `cleanup_old_backups` cog 33→14, `list_backups` cog 23→14, `create_backup` cog 20→10, `rollback` cog 18→15.
- **`rewrite/backup.py`** (`c847003`) — consolidated duplicate backup primitives into shared `utils/backup.py`, eliminating ~60 lines of duplication. `create_backup`, `create_deduplication_backup`, `_restore_single_file`, `_check_file_conflicts` now delegate to shared utils.
- **`core/executor.py:run_command`** (`0a679bb`) — wrapped with `tool_context()`, eliminated ~35 lines of manual timing + Sentry boilerplate. Still exceeds thresholds (cog=17, nest=5, len=56) — listed in remaining offenders table below.
- **`schema/enhancement_service.py`** (`0a679bb`) — replaced hardcoded 16-entry `_EXCLUDED_DIRS` with derivation from `FilePatterns.DEFAULT_EXCLUDE`.
- **`refactoring/extractor.py`** (`0a679bb`) — `_generate_docstring` (was cog=31), `_generate_function_body` (was cog=25), `_generate_signature` (was cog=13), `_apply_extraction` (was cog=11) all dropped below thresholds via further decomposition.
- **`complexity/analyzer.py:_find_magic_numbers`** (uncommitted) — deleted dead code (was cyc=13, cog=25, nest=5, len=61). Function was never called; active implementation lives in `quality/smells_detectors.py:MagicNumberDetector._find_magic_numbers` (already well-decomposed). Removed unused `SemanticVolumeDefaults` import.
- **`complexity/analyzer.py:_find_docstring_extent`** (uncommitted) — decomposed into `_measure_docstring` + shared `utils/parsing.py` primitives (`detect_triple_quote`, `skip_blank_lines`). cyc 11→4, cog 21→3. All helpers below thresholds. DRY: `deduplication/generator.py` `_get_triple_quotes` and `_skip_blank_lines` now delegate to same shared utils.
- **`deduplication/diff.py:build_nested_diff_tree`** (`b5e9d52`) — extracted `_DiffCounts` accumulator, `_classify_diff_line`, `_parse_unified_diff_lines`, `_build_nested_structure`. cyc 20→7, cog 25→3, nest 6→2, len 96→31. All helpers below thresholds.
- **`core/executor.py:filter_files_by_size`** (uncommitted) — extracted `_walk_and_classify` for os.walk loop and file classification. cyc 19→10, cog 18→8, nest 4→3, len 52→36. Helper below thresholds.
- **`refactoring/analyzer.py`** (`e3ceabb`–`40516c1`) — all 4 offenders resolved. `_find_python_base_variables` (cog 25→7): extracted `_collect_python_identifiers` helper + `_PYTHON_BASE_VAR_PATTERNS` constant. `_get_variable_classification` (cyc 13→7): merged two MODIFIED-return branches. `_scan_and_register_identifiers` (nest 5→4): collapsed for+if into generator. `analyze_selection` (len 63→37): extracted `_build_code_selection`.

### Remaining Offenders

Thresholds: cyc >10, cog >15, nest >4, len >50. All items from this section have been migrated to [2026-03-09 changelog](../changelog/2026-03-09-complexity-offender-reductions.md). Refresh: `uv run python scripts/scan_complexity_offenders.py`


## executor.py Hardening (2026-03-08)

From final code review of `9ad6a2c`–`9d7ea65`.

- [x] **EX-01** (Medium) `_execute_subprocess` Sentry span missing `returncode` on error path: when `check=True` and `subprocess.run` raises `CalledProcessError`, `span.set_data("returncode", ...)` is never reached. Fix: wrap in try/except to set `returncode` before re-raising. (commit e118fe0)
- [x] **EX-02** (Low) `_execute_subprocess` `use_shell` should be keyword-only: add `*` before `use_shell: bool` to prevent positional misuse. (commit 0e537a7)
- [x] **EX-03** (Low) `_load_custom_languages` silently swallows errors: `except Exception: pass` should log at debug level for diagnosability. (commit c5e10f5)

## Test Coverage Gaps (2026-03-09)

From backlog-implementer session implementing CX-01–CX-04 and SC-01–SC-04. New helpers introduced during complexity refactoring and script hardening have no direct test coverage.

- [x] **TC-01** (Medium) `scripts/scan_complexity_offenders.py` has zero tests. No coverage for `_extract_name` (decorator/async handling from SC-02), `_PROJECT_ROOT` resolution (CWD-independence from SC-01), `FILES` language tuple unpacking (SC-03), or `main()` output format. Fix: add `tests/unit/test_scan_complexity_offenders.py` with cases for: decorated functions (`@cache\ndef foo()`), `async def`, running from wrong CWD, `--all` flag, and functions exceeding thresholds. (commits a2b6e63, 9ed086d)
- [x] **TC-02** (Medium) `FunctionExtractor._process_scan_line` (`refactoring/extractor.py:344`) — new helper from CX-01. No direct unit test. Handles 5 branches: skip blank/comment, import start, multiline continuation, post-import break, default. `_scan_imports` itself also untested — existing `test_extract_function.py` exercises end-to-end extraction but never imports. Fix: add parametrized test in `test_extract_function.py` covering multiline `from x import (\n  a,\n  b\n)`, stacked imports, `import x` vs `from x import y`, and the post-import stop condition. (commit f3bc41d)
- [x] **TC-03** (Low) `_ensure_trailing_newline` (`deduplication/diff.py:391`) — new helper from CX-04. `test_generate_file_diff` exists but uses simple single-line inputs and weak assertions (`assert "def foo()" in diff or diff == ""`). Does not verify trailing newline edge cases (content already ending with `\n` vs not, empty content). Fix: add tests for `_ensure_trailing_newline` directly: empty list, single line with newline, single line without newline, multi-line. (commit d0fe662)
- [x] **TC-04** (Low) `_format_diff_alignment` (`deduplication/diff.py:193`) — new helper from CX-03. `test_format_alignment_diff` covers the `diff` alignment type but uses a weak assertion (`assert formatted is not None`). Does not verify the `- old`/`+ new` prefix formatting, empty old/new values, or both empty. Fix: strengthen `test_format_alignment_diff` to assert specific output lines, and add edge cases for empty `old`/`new` fields.

## Tool Invocation Failures (2026-03-10)

Errors encountered when callers (MCP sessions, batch scripts, agents) invoke ast-grep-mcp tools with incorrect arguments, nonexistent imports, or wrong input formats. Each entry documents the failure, root cause, and correct usage to prevent recurrence.

| ID | Severity | Tool | Status |
|----|----------|------|--------|
| TF-01 | Medium | `refactor_polyglot` | Done — `rename` accepted as alias for `rename_api` (commit e4d6eb2) |
| TF-02 | Low | `rewrite_code` | Deferred — 2-minute timeout scanning large directories; scope scans to subdirectories |
| TF-03 | Medium | `extract_function` | Done — documented public API in CLAUDE.md |
| TF-04 | Medium | `find_code_tool` (nonexistent) | Done — documented correct imports in CLAUDE.md |
| TF-05 | Medium | `get_ast_grep_docs_impl` (nonexistent) | Done — documented correct imports in CLAUDE.md |
| TF-06 | Medium | `rewrite_code_impl` | Done — documented correct signature in CLAUDE.md |
| TF-07 | Medium | `no-double-equals` rule | Done — excluded `== null`/`== undefined` idiom (commit 0976fb9) |
| TF-08 | Medium | `find_dedup_candidates` (nonexistent) | Done — documented below |
| TF-09 | Low | `find_by_rule` / `test_match` / `pattern_examples` | Done — documented below |
| TF-10 | Medium | `rewrite_code` YAML `$VAR` shell escaping | Done — documented below |
| TF-11 | Medium | `generate_language_bindings` | Done — documented below |
| TF-12 | Medium | `build_entity_graph` / `enhance_entity_graph` | Done — documented below |

### TF-08: `find_dedup_candidates` does not exist

**Error:** `ImportError: cannot import name 'find_dedup_candidates' from 'ast_grep_mcp.features.deduplication.tools'`

**Root cause:** Callers assume a `find_dedup_candidates` or `find_dedup_candidates_tool` function exists. It does not. The deduplication module exports:
- `find_duplication_tool()` — find duplicate code blocks across files
- `analyze_deduplication_candidates_tool()` — analyze specific candidates for refactoring
- `apply_deduplication_tool()` — apply deduplication refactoring
- `benchmark_deduplication_tool()` — benchmark deduplication performance

**Correct import:** `from ast_grep_mcp.features.deduplication.tools import analyze_deduplication_candidates_tool`

**Note:** The MCP registration uses inner functions (`_register_find_duplication`, etc.) — the `*_tool()` module-level functions are the importable public API.

### TF-09: `find_by_rule`, `test_match`, `pattern_examples` are MCP-only

**Error:** `ImportError: cannot import name 'find_by_rule' from 'ast_grep_mcp.features.search.tools'`

**Root cause:** These are inner functions defined inside `_register_*()` closures in `search/tools.py`, decorated with `@mcp.tool()`. They are registered at MCP server startup but are NOT importable as Python symbols.

**Correct alternatives:**
- `find_by_rule` → `from ast_grep_mcp.features.search.service import find_code_by_rule_impl`
- `test_match` → no direct equivalent; use `find_code_impl` with the pattern
- `pattern_examples` → `from ast_grep_mcp.features.search.docs import get_pattern_examples` (signature: `get_pattern_examples(language, category=None)`)
- Other search `_impl` functions: `find_code_impl`, `dump_syntax_tree_impl`, `debug_pattern_impl`, `build_rule_impl`, `develop_pattern_impl` — all in `search.service`
- Doc helper: `get_docs(topic)` in `search.docs`

**Pattern:** Search is the only feature module that uses inner-function MCP registration. All other feature modules use importable `*_tool()` functions.

### TF-10: `rewrite_code` YAML patterns with `$VAR` shell escaping

**Error:** `rewrite_code_impl` silently matches nothing, or produces garbled output when YAML `pattern` field contains ast-grep metavariables like `$MSG`, `$NAME`, `$ARGS`.

**Root cause:** When constructing YAML rule strings in shell contexts (bash `-c`, subprocess), `$MSG` is interpreted as a shell variable and expands to empty string. The resulting pattern `console.log()` instead of `console.log($MSG)` matches nothing or matches wrong nodes.

**Correct usage:**
```python
# Use raw strings — the YAML is passed via --inline-rules, not shell-interpolated
yaml_rule = """
id: remove-console-log
language: typescript
rule:
  pattern: console.log($$$ARGS)
fix: ''
"""
result = rewrite_code_impl(project_folder, yaml_rule, dry_run=True)
```

**Key points:**
- `rewrite_code_impl` passes YAML to `ast-grep scan --inline-rules <yaml>` — the YAML string goes through Python's `subprocess.run(args_list)` which does NOT invoke a shell by default
- The danger is in the *caller's* context: if you build the YAML string in a bash `-c` command or f-string with `$`, Python or bash may interpolate it before it reaches `rewrite_code_impl`
- Always use single-quoted strings in bash, raw strings in Python, or escape `$` as `\$` in double-quoted contexts

### TF-11: `generate_language_bindings` expects OpenAPI spec, not `package.json`

**Error:** `ValueError: Unsupported API specification format`

**Root cause:** `generate_language_bindings_impl()` in `cross_language/binding_generator.py` parses the input file and checks for `openapi` or `swagger` top-level keys. A `package.json` has neither.

**What the function expects:**
- OpenAPI 3.x spec (`.json` or `.yaml`) with `"openapi": "3.x.x"` key
- Swagger 2.0 spec (`.json` or `.yaml`) with `"swagger": "2.0"` key
- The spec must define `paths` with HTTP methods, parameters, request bodies, and responses

**What it generates:** Per-language client bindings (Python `requests`-based, TypeScript `fetch`-based, etc.) with typed method signatures for each API endpoint.

**Correct import:** `from ast_grep_mcp.features.cross_language.tools import generate_language_bindings_tool`

### TF-12: `build_entity_graph` / `enhance_entity_graph` format mismatches

**Error:** Caller passes raw JSON-LD to `build_entity_graph`, or passes entity definition dicts to `enhance_entity_graph`. Both fail silently or produce wrong output.

**Root cause:** The two functions expect *different* input formats:

**`build_entity_graph`** (in `schema/client.py`, async):
- Input: list of entity definition dicts — NOT JSON-LD
- Each dict: `{"type": "Organization", "properties": {"name": "..."}, "relationships": {"author": "id-fragment"}, "slug": "...", "id_fragment": "..."}`
- Output: complete JSON-LD `{"@context": "https://schema.org", "@graph": [...]}`
- Two-pass algorithm: first builds `id_fragment` → `@id` URL map, then resolves relationship references

**`enhance_entity_graph`** (in `schema/enhancement_service.py`, async):
- Actual function name: `analyze_entity_graph(input_source, input_type="file", output_mode="analysis")`
- Input: path to file or directory containing existing JSON-LD with `@context`/`@type`/`@graph`
- Output modes: `"analysis"` (suggestions + SEO scores), `"enhanced"` (full improved graph), `"diff"` (additions only)
- Validates: checks for `@context` containing "schema.org", detects broken `@id` references, scores missing properties per Google Rich Results requirements

**Key distinction:** `build_entity_graph` *creates* JSON-LD from scratch; `analyze_entity_graph` *analyzes and improves* existing JSON-LD.

## Observability Toolkit Optimization (2026-03-10)

Full analysis: [docs/reports/OBSERVABILITY-TOOLKIT-QUALITY-REPORT.md](reports/OBSERVABILITY-TOOLKIT-QUALITY-REPORT.md)

Target: `~/.claude/mcp-servers/observability-toolkit/src/` (217 files, 102K lines TypeScript)

Analyzed with all 53 ast-grep-mcp tools (complexity, smells, standards, security, duplication, anti-patterns, orphans, condense, quality report, rule templates). Summary: 0 errors, 5 complexity offenders, 554 magic numbers, 93 prefer-const, 0 duplication, 0 orphans.

- [x] **OT-CX-01** (High) Decompose `cost-estimation.ts:424-613` — cyc=32, cog=36, len=190. Extracted `_executeRecordSpend` + `_buildTrackerSummary` + `BudgetTrackerState` (commit 3f21ac8, review: PASS)
- [x] **OT-CX-02** (Medium) Decompose `server.ts:146-304` — cyc=21, len=159. Extracted `_registerRequestHandlers`, `_connectStdioTransport`, `_setupGracefulShutdown` (commit ece0615, review: PASS)
- [x] **OT-CX-03** (Medium) Decompose `estimate-cost.ts:31-125` — cyc=20, len=95. Extracted `_buildModelRows`, `_sortModelRows`, `_formatModelRow` (commit 6df8542, review: PASS)
- [ ] **OT-SM-01** (Medium) Extract magic numbers to named constants in `cost-estimation.ts`, `quality-feature-engineering.ts`, `export-utils.ts`.
- [x] **OT-CX-04** (Low) Decompose `query-metrics.ts:65-133` — cyc=17. Extracted `_processSpanForCost` with `CostAccumulator` state (commit 9c17b7a, review: PASS)
- [x] **OT-CX-05** (Low) Decompose `context-stats.ts:187-316` — cyc=13, len=130. Extracted `_findSessionById`, `_buildBaseResult`, `_appendCostSection`, `_appendBreakdownSection`, `_appendHistorySection` (commit f0fb17a, review: PASS)
- [ ] **OT-STD-01** (Low) Batch `let` → `const` for ~50 non-reassigned variables in production code.
- [ ] **OT-AP-01** (Low) Replace `ToolDefinition<any>[]` in `server.ts:82` with specific generic type.
- [ ] **OT-SM-02** (Medium) Decompose `instrumentation.ts` — grew from 377 → **715 lines** (2026-03-11 check). Growth threshold exceeded; decompose into focused sub-modules (e.g., span-lifecycle, attribute-collection, hook-instrumentation). -- `~/.claude/mcp-servers/observability-toolkit/src/lib/observability/instrumentation.ts`
- [ ] **OT-SEC-01** (Info) Extract test fixture Bearer tokens to per-file named constants (e.g., `const TEST_BEARER_TOKEN`) to reduce secret-scanning noise.
- [ ] **OT-STD-02** (Info) Add suppression comment for intentional `console.log` in `logger.ts:72`.
- [ ] **OT-DOC-01** (Info) Add baseline token count to Table 8 (Token Condensation Estimates) in quality report. Include source total (e.g., "~910,000 tokens raw") to allow readers to verify reduction percentages. -- `docs/reports/OBSERVABILITY-TOOLKIT-QUALITY-REPORT.md:160-165`

## Config File Support in MCP (2026-03-11)

Session: `run_all_tools.py` testing against `~/code/jobs/config/` revealed ast-grep-mcp tools lack config-file awareness.

#### CF-01: Add `languageGlobs` support to MCP tool invocations ✅
**Priority**: P2 | **Source**: session:2026-03-11 | **Done**: commits f5fb506, 3a42b76

Pipe `languageGlobs` through to `ast-grep scan --config` so non-standard extensions are parsed with the correct Tree-sitter grammar. Implementation:
1. Add optional `language_globs: dict[str, list[str]]` param to `run_command` / `stream_ast_grep_results` in `core/executor.py`
2. When provided, generate a temporary `sgconfig.yml` with the `languageGlobs` key and pass `--config <tmpdir>/sgconfig.yml` to ast-grep
3. Expose the param on tool wrappers that accept `project_folder` (search, rewrite, complexity, quality, dedup, condense)
4. Default mapping when no explicit globs provided and target contains only config files:
   - `.cjs` → `javascript`
   - `.json`, `.schema.json`, `.eslintrc`, `.babelrc` → `json`
   - `.yml`, `.yaml` → `yaml`

**How to add support for config files** (from ast-grep docs research):

**Option 1: `languageGlobs` in `sgconfig.yml`** (Recommended)
```yaml
languageGlobs:
  javascript: ['**/*.cjs', 'config/**/*.js']
  json: ['.eslintrc', '.babelrc', '*.schema.json']
  yaml: ['*.config.yml']
```
This tells ast-grep to:
- Parse `.cjs` files as JavaScript (already default, but explicit)
- Parse `.schema.json` as JSON
- Parse `.eslintrc` (no extension) as JSON

**Option 2: Register custom language** (for non-standard config formats)
```yaml
customLanguages:
  myconfig:
    libraryPath: ./path/to/custom.so  # compiled Tree-sitter grammar
    extensions: [myconfig]
    expandoChar: _  # char to replace $ in patterns
```

-- `src/ast_grep_mcp/core/executor.py`

#### CF-02: Config-aware search patterns documentation ✅
**Priority**: P3 | **Source**: session:2026-03-11 | **Done**: commits 5b470da, d0bc59c, 6b571a7

Config files contain declarations/objects, not executable code. Current sample patterns (`function $NAME($$$ARGS)`, `console.log($$$ARGS)`) return zero matches on config dirs. Document patterns that work:
- **CommonJS config** (`.cjs`): `module.exports = $VALUE`, `apps: [$$$ITEMS]`, `env: { $$$PROPS }`
- **JSON data**: `"$KEY": $VALUE` (requires `json` language)
- **YAML config**: `$KEY: $VALUE`, `- $ITEM` (requires `yml` language)
- **PM2 ecosystem**: `name: $APP`, `script: $PATH`, `cron_restart: $CRON`, `env_production: { $$$VARS }`
- **Zod schemas**: `z.object({ $$$FIELDS })`, `z.string()`, `z.array($INNER)`
- **JSON-LD / Schema.org**: `"@type": $TYPE`, `"@context": $CTX`, `"@id": $ID`

-- `docs/CONFIG_PATTERNS.md` (new file)

#### CF-03: Auto-detect config file types in `run_all_tools.py` ✅
**Priority**: P3 | **Source**: session:2026-03-11 | **Done**: commits 2e8eb7e, 5064c82

Before running tools, scan the target directory for file extensions and print language recommendations. If all files are config types (`.cjs`, `.json`, `.yml`, `.schema.json`), suggest running with multiple languages or warn that function-oriented patterns will return empty.

-- `scripts/run_all_tools.py`

#### CF-04: Config-aware search mode
**Priority**: P3 | **Source**: session:2026-03-11

Add a `search_config_files` tool or `config_mode` flag to existing search tools that understands common config file structures:
- **PM2 ecosystem** (`ecosystem.config.cjs`): extract `apps[]` entries, environment variables, cron schedules, cluster settings
- **Zod schemas**: extract type definitions, validators, default values
- **JSON-LD markup**: extract `@graph` entities, `@type` declarations, cross-references via `@id`
- **JSON Schema** (`.schema.json`): extract `properties`, `required` fields, `$ref` references

Implementation: pattern library per config type, auto-selected based on filename conventions.

-- `src/ast_grep_mcp/features/search/`

## Deferred (2026-03-08)

- [ ] **DF-01** (Low) Strategy pattern filter for deduplication — per `docs/duplicate-detector-misses.md` investigation. Only candidate (Group 5) would save ~18 lines with minor signature mismatch; over-engineering for marginal benefit.

