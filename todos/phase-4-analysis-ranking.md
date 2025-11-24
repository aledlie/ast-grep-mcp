# Phase 4: Analysis & Ranking Tool TODOs

## 4.1 Tool Skeleton
- [ ] Create `analyze_deduplication_candidates` signature
- [ ] Add to MCP tool registry
- [ ] Define input/output schema
- [ ] Add logging and Sentry tracking
- [ ] Basic integration test

## 4.2 Ranking Algorithm
- [ ] Define scoring formula
- [ ] Weight factors (savings, complexity, risk)
- [ ] Normalize scores to 0-100
- [ ] Sort results by score
- [ ] Unit tests for ranking

## 4.3 Test Coverage Detection
- [ ] Identify test file patterns (test_*, *_test.*, spec.*)
- [ ] Check if duplicate files have corresponding tests
- [ ] Flag untested duplicates as higher risk
- [ ] Unit tests for coverage detection

## 4.4 Impact Analysis
- [ ] Count files affected
- [ ] Estimate lines changed
- [ ] Identify call sites outside duplicates
- [ ] Flag breaking change risks
- [ ] Unit tests for impact calculation

## 4.5 Recommendation Engine
- [ ] Combine all scoring factors
- [ ] Generate actionable recommendation text
- [ ] Provide multiple strategy options
- [ ] Rank by effort/value ratio
- [ ] Unit tests for recommendations
