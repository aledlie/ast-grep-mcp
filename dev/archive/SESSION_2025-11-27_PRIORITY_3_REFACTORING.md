# Priority 3 Refactoring: ranker.py Modularization

**Session Date:** 2025-11-27
**Refactoring Target:** `src/ast_grep_mcp/features/deduplication/ranker.py`
**Status:** ✅ **COMPLETE** (All 396 tests passing)

---

## Executive Summary

Successfully refactored the `DuplicationRanker` class by extracting scoring and priority classification logic into two specialized modules. The refactoring reduced the main file from 233 → 165 lines (29% reduction) while improving code organization, testability, and separation of concerns.

**Results:**
- **Original:** 233 lines, estimated complexity ~95
- **After:** 165 lines ranker.py + 350 lines in 2 new modules = 515 total lines
- **Main class:** Simplified orchestration with delegated responsibilities
- **All tests passing:** 396/396 (100%)
- **Zero breaking changes:** Complete backward compatibility maintained

---

## Problem Statement

### Original Metrics

**File:** `src/ast_grep_mcp/features/deduplication/ranker.py`
- **Total lines:** 233
- **Main class:** `DuplicationRanker`
- **Estimated complexity:** ~95 (cyclomatic + cognitive combined)

### Issues Identified

1. **Mixed Responsibilities:**
   - Score calculation (savings, complexity, risk, effort) - lines 20-94
   - Ranking and sorting logic - lines 96-151
   - Priority classification - lines 153-164
   - Score breakdown formatting - lines 166-185
   - Recommendation generation - lines 187-201

2. **Code Organization:**
   - Scoring weights hardcoded in main class
   - Priority thresholds hardcoded in helper method
   - Multiple score calculation methods mixed together
   - Difficult to unit test individual scoring components
   - Hard to modify scoring algorithm independently

3. **Maintainability:**
   - Changes to scoring require modifying main class
   - Priority labels tightly coupled to ranker
   - Recommendation logic buried in private method
   - No clear separation between calculation and classification

### Existing Structure

The file was already well-structured with:
- ✅ Class-based design (`DuplicationRanker`)
- ✅ Clear method separation
- ✅ Good documentation
- ✅ Singleton pattern for convenience

**However**, there was opportunity to:
- Extract scoring logic into dedicated calculator
- Extract priority classification into dedicated classifier
- Improve testability of individual components

---

## Solution Design

### Architecture Pattern

**Extract Module Pattern** - Separate calculation and classification concerns:

1. **DeduplicationScoreCalculator** - Score calculation logic
2. **DeduplicationPriorityClassifier** - Priority classification and recommendations
3. **DuplicationRanker** - Orchestration and ranking

### Module Responsibilities

```
DeduplicationScoreCalculator
├── calculate_total_score() - Main entry point
├── calculate_savings_score() - Lines saved (40% weight)
├── calculate_complexity_score() - Code complexity (20% weight)
├── calculate_risk_score() - Test coverage + breaking risk (25% weight)
└── calculate_effort_score() - Files + instances (15% weight)

DeduplicationPriorityClassifier
├── get_priority_label() - Convert score → priority label
├── get_score_breakdown() - Build detailed breakdown
├── get_recommendation() - Generate recommendation text
└── classify_batch() - Classify multiple candidates

DuplicationRanker (orchestrator)
├── calculate_deduplication_score() - Delegates to calculator
├── rank_deduplication_candidates() - Orchestrates ranking
└── [Removed 3 private helper methods]
```

### Dependency Injection

```python
class DuplicationRanker:
    def __init__(self):
        self.logger = get_logger("deduplication.ranker")
        self.score_calculator = DeduplicationScoreCalculator()
        self.priority_classifier = DeduplicationPriorityClassifier()
```

---

## Implementation Details

### Module 1: score_calculator.py (194 lines)

**Purpose:** Calculate component scores for deduplication priority

**Key Methods:**
```python
class DeduplicationScoreCalculator:
    # Scoring weights as class constants
    WEIGHT_SAVINGS = 0.4  # 40%
    WEIGHT_COMPLEXITY = 0.2  # 20%
    WEIGHT_RISK = 0.25  # 25%
    WEIGHT_EFFORT = 0.15  # 15%

    def calculate_total_score(
        self,
        duplicate_group: Dict[str, Any],
        complexity: Optional[Dict[str, Any]] = None,
        test_coverage: Optional[float] = None,
        impact_analysis: Optional[Dict[str, Any]] = None
    ) -> tuple[float, Dict[str, float]]:
        """Calculate total score with component breakdown."""
        scores = {}
        scores["savings"] = self.calculate_savings_score(duplicate_group)
        scores["complexity"] = self.calculate_complexity_score(complexity)
        scores["risk"] = self.calculate_risk_score(test_coverage, impact_analysis)
        scores["effort"] = self.calculate_effort_score(duplicate_group)

        total_score = sum(scores.values())
        return round(total_score, 2), scores

    def calculate_savings_score(self, duplicate_group: Dict[str, Any]) -> float:
        """Calculate savings score (40% weight)."""
        lines_saved = duplicate_group.get("potential_line_savings", 0)
        savings_score = min(lines_saved / 5, 100)  # Cap at 500 lines
        return savings_score * self.WEIGHT_SAVINGS

    def calculate_complexity_score(
        self, complexity: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate complexity score (20% weight)."""
        if complexity:
            complexity_value = complexity.get("complexity_score", 5)
            complexity_score = max(0, 100 - (complexity_value - 1) * 16.67)
        else:
            complexity_score = 50  # Default middle score
        return complexity_score * self.WEIGHT_COMPLEXITY

    def calculate_risk_score(
        self,
        test_coverage: Optional[float] = None,
        impact_analysis: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate risk score (25% weight)."""
        risk_score = 50  # Default
        if test_coverage is not None:
            risk_score = test_coverage
        if impact_analysis:
            breaking_risk = impact_analysis.get("breaking_change_risk", "medium")
            risk_multipliers = {"low": 1.0, "medium": 0.7, "high": 0.3}
            risk_score *= risk_multipliers.get(breaking_risk, 0.7)
        return risk_score * self.WEIGHT_RISK

    def calculate_effort_score(self, duplicate_group: Dict[str, Any]) -> float:
        """Calculate effort score (15% weight)."""
        instance_count = len(duplicate_group.get("instances", []))
        file_count = len(set(
            inst.get("file", "") for inst in duplicate_group.get("instances", [])
        ))
        effort_score = max(0, 100 - (instance_count * 5 + file_count * 10))
        return effort_score * self.WEIGHT_EFFORT
```

**Features:**
- Scoring weights as class constants (easy to adjust)
- Separate calculation methods for each component
- Detailed logging for each score
- Returns both total and component scores
- Clear documentation of scoring algorithm

**Original code:** Lines 45-92 in ranker.py
**New location:** score_calculator.py

### Module 2: priority_classifier.py (156 lines)

**Purpose:** Classify candidates by priority and generate recommendations

**Key Methods:**
```python
class DeduplicationPriorityClassifier:
    # Priority thresholds as class constants
    THRESHOLD_CRITICAL = 80
    THRESHOLD_HIGH = 60
    THRESHOLD_MEDIUM = 40
    THRESHOLD_LOW = 20

    def get_priority_label(self, score: float) -> str:
        """Get priority label from score."""
        if score >= self.THRESHOLD_CRITICAL:
            return "critical"
        elif score >= self.THRESHOLD_HIGH:
            return "high"
        elif score >= self.THRESHOLD_MEDIUM:
            return "medium"
        elif score >= self.THRESHOLD_LOW:
            return "low"
        else:
            return "minimal"

    def get_score_breakdown(
        self,
        candidate: Dict[str, Any],
        total_score: float,
        score_components: Dict[str, float]
    ) -> Dict[str, Any]:
        """Get detailed breakdown with recommendation."""
        return {
            "total_score": total_score,
            "components": score_components,
            "factors": {...},
            "recommendation": self.get_recommendation(...)
        }

    def get_recommendation(
        self, score: float, lines_saved: int, instance_count: int
    ) -> str:
        """Generate recommendation based on score."""
        if score >= self.THRESHOLD_CRITICAL:
            return f"Immediate refactoring recommended. Will save {lines_saved} lines..."
        elif score >= self.THRESHOLD_HIGH:
            return "High-value refactoring opportunity..."
        # ...

    def classify_batch(
        self, candidates: list[Dict[str, Any]], scores: list[float]
    ) -> Dict[str, list[Dict[str, Any]]]:
        """Classify multiple candidates by priority."""
        classified = {"critical": [], "high": [], "medium": [], "low": [], "minimal": []}
        for candidate, score in zip(candidates, scores):
            priority = self.get_priority_label(score)
            classified[priority].append({...})
        return classified
```

**Features:**
- Priority thresholds as class constants
- Clear priority level mapping
- Detailed score breakdown formatting
- Context-aware recommendations
- Batch classification support
- Structured logging

**Original code:** Lines 153-201 in ranker.py
**New location:** priority_classifier.py

### Module 3: Refactored ranker.py (165 lines, down from 233)

**Changes Made:**

1. **Added imports:**
   ```python
   from .priority_classifier import DeduplicationPriorityClassifier
   from .score_calculator import DeduplicationScoreCalculator
   ```

2. **Dependency injection in `__init__`:**
   ```python
   def __init__(self):
       self.logger = get_logger("deduplication.ranker")
       self.score_calculator = DeduplicationScoreCalculator()
       self.priority_classifier = DeduplicationPriorityClassifier()
   ```

3. **Refactored `calculate_deduplication_score`:**
   ```python
   def calculate_deduplication_score(self, ...) -> float:
       # Delegate to score calculator
       total_score, score_components = self.score_calculator.calculate_total_score(...)

       # Log the result
       self.logger.info("deduplication_score_calculated", ...)

       return total_score
   ```

4. **Refactored `rank_deduplication_candidates`:**
   ```python
   def rank_deduplication_candidates(self, ...) -> List[Dict[str, Any]]:
       ranked = []

       for candidate in candidates:
           # Calculate score
           total_score, score_components = self.score_calculator.calculate_total_score(...)

           # Get priority label
           priority = self.priority_classifier.get_priority_label(total_score)

           # Build ranked candidate
           ranked_candidate = {**candidate, "score": total_score, "priority": priority}

           # Add breakdown if requested
           if include_analysis:
               ranked_candidate["score_breakdown"] = self.priority_classifier.get_score_breakdown(...)

           ranked.append(ranked_candidate)

       # Sort by score
       ranked.sort(key=lambda x: x["score"], reverse=True)

       # Add rank numbers
       for i, candidate in enumerate(ranked):
           candidate["rank"] = i + 1

       return ranked
   ```

5. **Removed private helper methods:**
   - Deleted `_get_priority_label()` - moved to priority_classifier
   - Deleted `_get_score_breakdown()` - moved to priority_classifier
   - Deleted `_get_recommendation()` - moved to priority_classifier

**Reduction:** 233 → 165 lines (29% reduction)

---

## Test Results

### Full Test Suite

```bash
uv run pytest tests/ -v
```

**Results:**
- **Total tests:** 398
- **Passed:** 396
- **Skipped:** 2 (CI benchmarks - expected)
- **Failed:** 0
- **Warnings:** 73 (deprecation warnings in Sentry SDK - not critical)
- **Execution time:** 3.50 seconds

### Ranking Tests

All deduplication and ranking tests passing:
- `test_ranking.py` - All passing
- `test_analyze_deduplication_candidates.py` - All passing
- Integration tests - All passing

### Backward Compatibility

✅ **Zero breaking changes:**
- All existing tests pass without modification
- API signatures unchanged
- Response format identical
- Singleton pattern preserved
- Standalone functions still work

---

## Metrics and Improvements

### Line Count Changes

| Component | Before | After | Change |
|-----------|--------|-------|--------|
| ranker.py | 233 lines | 165 lines | -68 lines (-29%) |
| **New modules** | - | 350 lines | +350 lines |
| **Total codebase** | 233 lines | 515 lines | +282 lines (+121%) |

**Note:** Total lines increased because logic was extracted into separate, testable modules with clear responsibilities.

### Complexity Reduction

| Metric | Before | After (estimated) | Improvement |
|--------|--------|-------------------|-------------|
| Cyclomatic complexity | ~50 | ~15 | 70% reduction |
| Cognitive complexity | ~45 | ~20 | 56% reduction |
| Combined complexity | 95 | 35 | 63% reduction |
| Methods in main class | 7 | 4 | 43% reduction |

### Code Quality Improvements

✅ **Single Responsibility Principle**
- ScoreCalculator: Only calculates scores
- PriorityClassifier: Only classifies and recommends
- Ranker: Only orchestrates ranking

✅ **Constants Extracted**
- Scoring weights as class constants (easy to tune)
- Priority thresholds as class constants (easy to adjust)

✅ **Improved Testability**
- Can unit test individual score components
- Can test priority classification independently
- Can mock calculator/classifier for ranker tests

✅ **Better Documentation**
- Clear docstrings for each component
- Type hints throughout
- Documented scoring algorithm

✅ **Structured Logging**
- Debug logging for each score component
- Info logging for totals and rankings
- Clear event names

---

## Technical Decisions

### 1. Module Granularity

**Decision:** Create two modules instead of three

**Rationale:**
- Score calculation has 4 related methods (savings, complexity, risk, effort)
- Priority classification has 4 related methods (label, breakdown, recommendation, batch)
- Ranker orchestrates both and handles ranking logic
- Balance between granularity and practicality

### 2. Return Tuple from calculate_total_score

**Decision:** Return `(total_score, score_components)` tuple

**Rationale:**
- Avoids duplicate calculation in ranking loop
- Provides breakdown data for detailed analysis
- Cleaner than separate method calls
- Follows Python convention for related values

### 3. Constants as Class Attributes

**Decision:** Define weights and thresholds as class constants

**Rationale:**
- Makes configuration explicit and visible
- Easy to modify without digging through code
- Allows subclassing to override if needed
- Documents the scoring algorithm clearly

### 4. Backward Compatibility

**Decision:** Maintain exact API signatures

**Rationale:**
- All existing code continues to work
- Tests don't require modification
- No impact on tool registration
- Smooth migration path

---

## Files Modified

### Created Files

1. **score_calculator.py** (194 lines)
   - Location: `src/ast_grep_mcp/features/deduplication/score_calculator.py`
   - Purpose: Score calculation with component breakdown

2. **priority_classifier.py** (156 lines)
   - Location: `src/ast_grep_mcp/features/deduplication/priority_classifier.py`
   - Purpose: Priority classification and recommendations

### Modified Files

1. **ranker.py** (233 → 165 lines)
   - Location: `src/ast_grep_mcp/features/deduplication/ranker.py`
   - Changes:
     - Added imports for new modules
     - Injected dependencies in `__init__`
     - Refactored `calculate_deduplication_score` to delegate
     - Refactored `rank_deduplication_candidates` to use modules
     - Removed 3 private helper methods

---

## Comparison with Priority 1 & 2

| Metric | Priority 1 | Priority 2 | Priority 3 |
|--------|-----------|-----------|-----------|
| Original complexity | 219 (cognitive) | 117 (combined) | 95 (combined) |
| Original lines | 683 | 670 | 233 |
| Modules created | 4 | 3 | 2 |
| Total new lines | 1,257 | 485 | 350 |
| Main reduction | 61% | 36% | 29% |
| Bugs encountered | 6 | 0 | 0 |
| Time to complete | ~3 hours | ~1.5 hours | ~1 hour |
| Tests passing | 396/396 | 396/396 | 396/396 |

**Key Insights:**
- Smaller files = faster refactoring
- Learning from previous priorities = fewer bugs
- Well-structured code = easier extraction
- All priorities achieved 100% test pass rate

---

## Lessons Learned

### What Went Well

1. **Clear Module Boundaries**
   - Calculator vs classifier separation very clear
   - No overlap in responsibilities
   - Clean interfaces

2. **No Bugs**
   - All tests passed on first try
   - Pattern now well-established
   - Good understanding of codebase

3. **Fast Execution**
   - Completed in ~1 hour
   - Efficient module creation
   - No debugging needed

4. **Return Tuple Pattern**
   - Returning both total and components worked well
   - Avoided duplicate calculations
   - Cleaner than separate calls

### Continuous Improvements

1. **Consistency Across Priorities**
   - Same patterns applied successfully
   - Predictable results
   - Reusable approach

2. **Incremental Learning**
   - Each priority faster than previous
   - Fewer mistakes over time
   - Better anticipation of issues

---

## Next Steps

### Remaining Priority Targets

Based on REFACTORING_ACTION_PLAN.md:

1. **Priority 4: benchmark.py** (205 lines, complexity 52)
   - Extract benchmark execution
   - Extract report generation
   - Extract regression detection

2. **Priority 5: deduplication/tools.py** (190 lines, complexity 47)
   - Extract orchestration logic
   - Extract response building
   - Extract validation

### Recommended Approach

Continue the same pattern:
1. Read and analyze current structure
2. Identify clear responsibilities (2-4 modules)
3. Create focused modules with single responsibilities
4. Refactor main function/class to orchestrate
5. Run tests immediately
6. Document completion

---

## Conclusion

Priority 3 refactoring successfully completed with:
- ✅ 2 new modules created (350 total lines)
- ✅ Main file reduced by 29% (233 → 165 lines)
- ✅ Complexity reduced by 63% (95 → 35 estimated)
- ✅ All 396 tests passing
- ✅ Zero breaking changes
- ✅ Zero bugs encountered
- ✅ Improved maintainability and testability

The modular architecture provides clear benefits:
- Easy to adjust scoring weights (class constants)
- Easy to modify priority thresholds (class constants)
- Easy to add new score components
- Easy to test individual components
- Easy to customize recommendations

**Total Refactoring Progress:**
- Priority 1: ✅ Complete (applicator.py)
- Priority 2: ✅ Complete (tools.py)
- Priority 3: ✅ Complete (ranker.py)
- Priority 4-5: 📋 Pending

---

**Session End Time:** 2025-11-27
**Total Session Duration:** ~1 hour
**Status:** SUCCESS
