# Backlog

**See [docs/changelog/2026-03-08-complexity-refactoring-queue.md](changelog/2026-03-08-complexity-refactoring-queue.md) for historical complexity refactoring metrics (434 → 0 offenders, 2026-03-08 refresh completed 2026-03-09).**






## Minor Code Quality Items (2026-03-12)

From code-reviewer final review of CR-01–CR-06.

- [ ] **MQ-01** (P3) Refactor inline comment in `_split_params` to multi-line format — current comment extends line to ~106 chars (cosmetic issue, ruff passes). -- `src/ast_grep_mcp/features/documentation/docstring_generator.py:443`
- [ ] **MQ-02** (P3) Document partial-result streaming semantics in `_execute_search` — currently logs partial matches before re-raising, but accumulated data is discarded. Add docstring clarifying all-or-nothing contract if exception occurs. -- `src/ast_grep_mcp/features/search/service.py:238`

## Library Migration Opportunities (2026-04-19)

Full analysis: [tmp/lib-audit-report.md](../tmp/lib-audit-report.md)

**Phase 1 — Complete:**
- [x] **LM-01** (High) Migrate cache.py to `cachetools.TTLCache` — eliminates 22 LOC manual TTL/LRU tracking
- [x] **LM-02** (High) Regex pattern compilation caching — pre-compiled patterns at module initialization, 21.9% speedup
- [x] **LM-03** (Medium) Migrate config to `pydantic-settings` — ServerSettings model with automatic env var loading. Eliminated 70+ LOC of manual parsing. (commit 87bc433)

**Phase 1.5 — Next quick wins:**
- [x] **LM-04** (Low) Use built-in `tempfile.TemporaryDirectory` — replaced 70 LOC custom temp handling in `rewrite/service.py`. (commit 5db1912)

**Phase 2 — Refactoring (8–16 hours, 25–40% subprocess perf improvement, 350 LOC elimination):**
- [ ] **LM-05** (High) Asyncio subprocess streaming — refactor `core/executor.py:stream_ast_grep_results` from blocking `subprocess.PIPE` + `json.loads` loop to `asyncio.subprocess` with parallel streams. Potential 25–40% faster subprocess calls, eliminates 350 LOC manual buffering/timeout logic.

## Deferred

- [ ] **DF-01** (Low) Strategy pattern filter for deduplication — per `docs/duplicate-detector-misses.md` investigation. Only candidate (Group 5) would save ~18 lines with minor signature mismatch; over-engineering for marginal benefit. (deferred 2026-03-08)
- [ ] **CF-04** (P3) Config-aware search mode — complex feature for PM2/Zod/JSON-LD config patterns. Deferred from 2026-03-11 session as out of scope. -- `src/ast_grep_mcp/features/search/`
- [x] **FG-01** (P2) `detect_structured_data` cannot parse Liquid/Jekyll templates — **RESOLVED** with regex fallback. ast-grep HTML parser fails on `{% if %}`, `{{ variable }}`; regex fallback detects JSON-LD, microdata, and RDFa in Liquid files. (commit 5a9476e)

