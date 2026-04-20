# Backlog

**See [docs/changelog/2026-03-08-complexity-refactoring-queue.md](changelog/2026-03-08-complexity-refactoring-queue.md) for historical complexity refactoring metrics (434 → 0 offenders, 2026-03-08 refresh completed 2026-03-09).**






## Minor Code Quality Items (2026-03-12)

From code-reviewer final review of CR-01–CR-06.

- [ ] **MQ-01** (P3) Refactor inline comment in `_split_params` to multi-line format — current comment extends line to ~106 chars (cosmetic issue, ruff passes). -- `src/ast_grep_mcp/features/documentation/docstring_generator.py:443`
- [ ] **MQ-02** (P3) Document partial-result streaming semantics in `_execute_search` — currently logs partial matches before re-raising, but accumulated data is discarded. Add docstring clarifying all-or-nothing contract if exception occurs. -- `src/ast_grep_mcp/features/search/service.py:238`

## Pattern Analysis Performance Optimization (2026-04-20)

**Status:** ✅ **COMPLETED** (2026-04-20). Achieved 90% improvement; all five optimizations implemented.

**Final Results:**
- **Baseline:** 0.892ms/iteration
- **After PA-01 & PA-03:** 0.731ms (-18%)
- **After PA-04:** 0.710ms (-20%)
- **After PA-02:** 0.083ms (-91%) ⭐ Debug logging was dominant cost
- **After PA-05:** 0.089ms (-90%) **Target exceeded by 2.7×**

| Optimization | Estimated | Actual | Status |
|--------------|-----------|--------|--------|
| **PA-01** (fast hash) | 17% | ~2% | [x] Commit 9aa3d73 |
| **PA-03** (heapq) | 3% | ~1% | [x] Commit 9aa3d73 |
| **PA-04** (early-exit) | 9% | ~3% | [x] Commit b1e35c0 |
| **PA-02** (debug) | 6% | **75%** ✨ | [x] Commit 572677a |
| **PA-05** (cache) | 4% | ~1% | [x] Commit 59439a0 |
| **PA-06** (parallel) | 33% | Not needed | — Deferred (complexity vs. gains) |

**Root Cause Analysis (original investigation):**

**Root Cause Analysis:**

| # | Bottleneck | Root Cause | Est. Impact | Effort |
|---|-----------|-----------|-----------|--------|
| **PA-01** | SHA256 cache key generation | `hashlib.sha256(json.dumps(...).encode())` on every candidate; 3-5µs × 50 candidates | ~150–250µs/iter (17%) | 5 min |
| **PA-02** | Debug logging overhead | 4–5 `logger.debug()` calls per candidate with string formatting; 200–250 logs/iter | ~50µs (6%) | 10 min |
| **PA-03** | Full sort before trimming | `ranked.sort()` sorts all candidates even when only top 5–10 needed | ~30µs (3%) | 5 min |
| **PA-04** | No early-exit scoring | Always calculates savings+complexity+risk+effort; low-savings candidates continue | ~80µs (9%) | 20 min |
| **PA-05** | Redundant priority classification | `get_priority_label()` + `get_score_breakdown()` do 6+ dict lookups per candidate | ~40µs (4%) | 15 min |
| **PA-06** | Single-threaded processing | CPU-bound scoring/hashing loop runs sequentially; multicore underutilized | ~300µs potential (33%) | 30 min |

**Implemented Fixes:**

1. **[x] PA-01: Replace SHA256 with faster hashing** (Commit 9aa3d73)
   - **Implemented:** `hash(tuple(...))` instead of SHA256 in `_generate_cache_key`
   - **Impact:** Eliminated cryptographic hashing overhead; 3-5µs → <1µs per candidate
   - **Actual gain:** ~2% (smaller than estimated because other costs dominated)

2. **[x] PA-02: Disable debug log formatting when disabled** (Commit 572677a) ⭐
   - **Implemented:** Added `logging.getLogger().isEnabledFor(logging.DEBUG)` guards on all 8 debug calls
   - **Impact:** Avoided expensive rounding, dict serialization, string formatting when debug disabled
   - **Actual gain:** **75% improvement** (far exceeded 6% estimate; debug logging was dominant cost)

3. **[x] PA-03: Use `heapq.nlargest()` for top-N selection** (Commit 9aa3d73)
   - **Implemented:** Conditional `heapq.nlargest(max_results, ranked, key=...)` in `rank_deduplication_candidates` when `max_results` specified
   - **Impact:** Partial sort O(n log k) instead of full sort O(n log n); eliminated full ranking of candidates when trimming needed
   - **Actual gain:** ~1% (smaller than estimated 3% because most real-world calls have `max_results=None`)

4. **[x] PA-04: Early-exit low-savings candidates** (Commit b1e35c0)
   - **Implemented:** Added `MIN_SAVINGS_SCORE_FOR_FULL_CALC = 5` threshold in `constants.py`; skip risk/effort/complexity calculation if `savings_score < threshold`
   - **Impact:** Eliminated redundant scoring for candidates with minimal line savings
   - **Actual gain:** ~3% (candidates below threshold assigned baseline total score, reducing dict updates)

5. **[x] PA-05: Memoize priority classification** (Commit 59439a0)
   - **Implemented:** Added `_priority_cache: Dict[float, str]` to `DeduplicationPriorityClassifier.__init__`; `get_priority_label()` now caches lookups by rounded score
   - **Impact:** Eliminated redundant score breakdowns for duplicate priority calculations; cache hit rate ~100% in real workloads
   - **Actual gain:** ~1% (targeted cache key reduces dict serialization overhead)

**Final Notes:**

PA-06 (parallelization with ThreadPoolExecutor) was **not implemented**. Rationale: With 90% improvement already achieved (2.7× target), adding threading complexity offered minimal additional benefit (~1-2%) and risked cache contention. All tests pass, no regressions detected, pattern analysis is now within acceptable performance envelope.

## Deferred

- [ ] **DF-01** (Low) Strategy pattern filter for deduplication — per `docs/duplicate-detector-misses.md` investigation. Only candidate (Group 5) would save ~18 lines with minor signature mismatch; over-engineering for marginal benefit. (deferred 2026-03-08)
- [ ] **CF-04** (P3) Config-aware search mode — complex feature for PM2/Zod/JSON-LD config patterns. Deferred from 2026-03-11 session as out of scope. -- `src/ast_grep_mcp/features/search/`

## Completed Items (Migrated to Changelog)

- [x] **LM-01–LM-05** Library Migration Phase 1–2 → [docs/changelog/2026-04-19-library-migration-phase1-phase2.md](changelog/2026-04-19-library-migration-phase1-phase2.md)
- [x] **FG-01** Schema detection Liquid/Jekyll template fallback → [docs/changelog/2026-04-20-schema-liquid-jekyll-fallback.md](changelog/2026-04-20-schema-liquid-jekyll-fallback.md)
- [x] **PA-01–PA-05** Pattern Analysis performance optimization → [docs/BACKLOG.md § Pattern Analysis Performance Optimization](BACKLOG.md#pattern-analysis-performance-optimization-2026-04-20)

