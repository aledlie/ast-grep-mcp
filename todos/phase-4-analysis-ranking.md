# Phase 4: Analysis & Ranking Tool TODOs

**Status: COMPLETED**
**Completed Date: 2025-11-23**

## 4.1 Tool Skeleton
- [x] Create `analyze_deduplication_candidates` signature
- [x] Add to MCP tool registry
- [x] Define input/output schema
- [x] Add logging and Sentry tracking
- [x] Basic integration test

## 4.2 Ranking Algorithm
- [x] Define scoring formula
- [x] Weight factors (savings 40%, complexity 20%, risk 25%, effort 15%)
- [x] Normalize scores to 0-100
- [x] Sort results by score
- [x] Unit tests for ranking

## 4.3 Test Coverage Detection
- [x] Identify test file patterns (test_*, *_test.*, spec.*)
- [x] Check if duplicate files have corresponding tests
- [x] Flag untested duplicates as higher risk
- [x] Unit tests for coverage detection

## 4.4 Impact Analysis
- [x] Count files affected
- [x] Estimate lines changed
- [x] Identify call sites outside duplicates
- [x] Flag breaking change risks
- [x] Unit tests for impact calculation

## 4.5 Recommendation Engine
- [x] Combine all scoring factors
- [x] Generate actionable recommendation text
- [x] Provide multiple strategy options
- [x] Rank by effort/value ratio
- [x] Unit tests for recommendations

## Summary

- **22/22 tasks completed**
- **137 tests written** (23 ranking, 40 coverage, 33 impact, 27 recommendation, 14 integration)
- Key functions: `calculate_deduplication_score`, `has_test_coverage`, `analyze_deduplication_impact`, `generate_deduplication_recommendation`
- Supports 9 languages for test pattern detection
- All tests passing
