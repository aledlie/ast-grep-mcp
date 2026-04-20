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

**Phase 2 — Refactoring:**
- [x] **LM-05** (High) Asyncio subprocess streaming — refactor `core/executor.py:stream_ast_grep_results` from blocking `subprocess.PIPE` + `json.loads` loop to `asyncio.subprocess` with parallel streams. Eliminates threading.Thread, adds timeout support, 5 helper functions removed. (commit 8a3724a)

## Pattern Analysis Performance Optimization (2026-04-20)

**Current Baseline:** 0.89ms/iteration (50 iterations), 17% of total deduplication benchmark time.

**Issue:** Benchmark regression check identified Pattern Analysis as bottleneck. Investigation revealed 6 key performance anti-patterns in `DuplicationRanker.rank_deduplication_candidates()`.

**Root Cause Analysis:**

| # | Bottleneck | Root Cause | Est. Impact | Effort |
|---|-----------|-----------|-----------|--------|
| **PA-01** | SHA256 cache key generation | `hashlib.sha256(json.dumps(...).encode())` on every candidate; 3-5µs × 50 candidates | ~150–250µs/iter (17%) | 5 min |
| **PA-02** | Debug logging overhead | 4–5 `logger.debug()` calls per candidate with string formatting; 200–250 logs/iter | ~50µs (6%) | 10 min |
| **PA-03** | Full sort before trimming | `ranked.sort()` sorts all candidates even when only top 5–10 needed | ~30µs (3%) | 5 min |
| **PA-04** | No early-exit scoring | Always calculates savings+complexity+risk+effort; low-savings candidates continue | ~80µs (9%) | 20 min |
| **PA-05** | Redundant priority classification | `get_priority_label()` + `get_score_breakdown()` do 6+ dict lookups per candidate | ~40µs (4%) | 15 min |
| **PA-06** | Single-threaded processing | CPU-bound scoring/hashing loop runs sequentially; multicore underutilized | ~300µs potential (33%) | 30 min |

**Recommended Fixes (Priority Order):**

1. **PA-01: Replace SHA256 with faster hashing**
   - **What:** Use `hash(tuple(sorted_fields))` or `zlib.crc32()` instead of SHA256
   - **Where:** `src/ast_grep_mcp/features/deduplication/ranker.py:335–350` (`_generate_cache_key`)
   - **Why:** SHA256 is cryptographic overkill; simple non-cryptographic hash sufficient for cache collision avoidance
   - **Expected gain:** ~150µs (17% of 0.89ms)

2. **PA-02: Disable debug log formatting when disabled**
   - **What:** Check `logger.isEnabledFor(logging.DEBUG)` before format operations
   - **Where:** `ranker.py:55, 79, 90+` (all `logger.debug()` calls in scoring)
   - **Why:** Even disabled loggers evaluate string format arguments
   - **Expected gain:** ~50µs (6%)

3. **PA-03: Use `heapq.nlargest()` for top-N selection**
   - **What:** Replace `ranked.sort(...); ranked = ranked[:max_results]` with `heapq.nlargest(max_results, ranked, key=lambda x: x["score"])`
   - **Where:** `ranker.py:487–489` (`rank_deduplication_candidates`)
   - **Why:** Partial sort is O(n log k) instead of O(n log n) for k << n
   - **Expected gain:** ~30µs (3%)

4. **PA-04: Early-exit low-savings candidates (optional)**
   - **What:** If `savings_score < threshold` (e.g., < 5), skip risk/effort calculation; assign minimum total score
   - **Where:** `ranker.py:60–61` (after `calculate_savings_score`)
   - **Why:** Candidates with minimal line savings unlikely to be ranked high
   - **Expected gain:** ~80µs (9%)
   - **Trade-off:** Reduces accuracy slightly; acceptable if threshold tuned to match real data

5. **PA-06: Parallelize scoring with ThreadPoolExecutor**
   - **What:** Use `concurrent.futures.ThreadPoolExecutor(max_workers=4)` to parallelize `_score_candidate()` loop
   - **Where:** `ranker.py:481–486` (main candidate loop)
   - **Why:** CPU-bound hashing/scoring; 4 workers → ~4× speedup (practical: ~2.5× due to GIL overhead on hashing)
   - **Expected gain:** ~200µs (23% realistically)
   - **Trade-off:** Adds dependency on threading; test for race conditions in cache

**Testing Plan:**

```bash
# Baseline
uv run pytest tests/deduplication/test_benchmark.py::test_pattern_analysis_baseline -v

# After each fix
uv run pytest tests/deduplication/test_benchmark.py -k pattern_analysis --benchmark-only
uv run python -c "from ast_grep_mcp.features.deduplication.tools import benchmark_deduplication_tool; result = benchmark_deduplication_tool(); print(result['results'][1])"
```

**Acceptance Criteria:**
- Pattern Analysis regression threshold remains at 0.15 (currently: no regression detected)
- After all fixes: ≤ 0.6ms/iteration (33% reduction)
- No new cache misses; cache hit rate ≥ 95%

## Deferred

- [ ] **DF-01** (Low) Strategy pattern filter for deduplication — per `docs/duplicate-detector-misses.md` investigation. Only candidate (Group 5) would save ~18 lines with minor signature mismatch; over-engineering for marginal benefit. (deferred 2026-03-08)
- [ ] **CF-04** (P3) Config-aware search mode — complex feature for PM2/Zod/JSON-LD config patterns. Deferred from 2026-03-11 session as out of scope. -- `src/ast_grep_mcp/features/search/`
- [x] **FG-01** (P2) `detect_structured_data` cannot parse Liquid/Jekyll templates — **RESOLVED** with regex fallback. ast-grep HTML parser fails on `{% if %}`, `{{ variable }}`; regex fallback detects JSON-LD, microdata, and RDFa in Liquid files. (commit 5a9476e)

