# Test Automation Scripts

Scripts for managing fixture migration and tracking test quality metrics.

## Available Scripts

### score_test_file.py

**Purpose:** Calculate refactoring priority scores for test files

**Usage:**
```bash
# Score a single file
python tests/scripts/score_test_file.py tests/unit/test_cache.py

# Score with detailed metrics
python tests/scripts/score_test_file.py tests/unit/test_cache.py --detailed

# Score all test files
python tests/scripts/score_test_file.py --all

# Output as JSON
python tests/scripts/score_test_file.py --all --json > scores.json
```

**Scoring System (0-100):**
- **Pain Points (40%)**: Maintenance burden, flakiness, duplication
- **Opportunity (35%)**: Lines saved, complexity reduction, reusability
- **Risk (15% inverse)**: Test count, self-attributes, dependencies
- **Alignment (10%)**: Feature work, team familiarity

**Score Ranges:**
- **≥70**: HIGH PRIORITY - Refactor soon
- **55-69**: MEDIUM PRIORITY - Refactor when touching file
- **40-54**: LOW PRIORITY - Refactor opportunistically
- **25-39**: DEFER - Keep using setup_method
- **<25**: SKIP - Not worth refactoring

### Future Scripts (Phase 1)

#### track_fixture_metrics.py
Track fixture adoption rates and usage statistics

#### detect_fixture_patterns.py
Identify common patterns that could become fixtures

#### validate_refactoring.py
Validate that refactored tests work correctly

#### benchmark_fixtures.py
Measure fixture performance overhead

## Quick Examples

```bash
# Find high-priority files to refactor
python tests/scripts/score_test_file.py --all | grep "HIGH PRIORITY"

# Get detailed analysis of top candidate
python tests/scripts/score_test_file.py tests/unit/test_rewrite.py --detailed

# Export all scores for tracking
python tests/scripts/score_test_file.py --all --json > baseline_scores.json
```

## Baseline Scores

Baseline scores captured on 2025-11-25:

**High Priority (≥70):**
- test_rewrite.py: 92.2
- test_apply_deduplication.py: 74.6

**Medium Priority (55-69):**
- test_deduplication_rollback.py: 69.4
- test_batch.py: 65.1
- test_cli_duplication.py: 60.1
- test_schema.py: 58.9

See `tests/baseline_scores.json` for complete data.

## Integration with Git Hooks

The pre-commit hook (`.git/hooks/pre-commit`) enforces fixture usage for new test files.

**Bypass (not recommended):**
```bash
git commit --no-verify
```

## Documentation

- [FIXTURE_MIGRATION_GUIDE.md](../FIXTURE_MIGRATION_GUIDE.md) - How to refactor tests
- [FIXTURE_GOVERNANCE.md](../FIXTURE_GOVERNANCE.md) - Fixture lifecycle management
- [FIXTURE_COOKBOOK.md](../FIXTURE_COOKBOOK.md) - Common testing patterns
- [DEVELOPER_ONBOARDING.md](../DEVELOPER_ONBOARDING.md) - Quick start for new developers

## Contributing

When adding new scripts:

1. Follow naming convention: `{verb}_{noun}.py`
2. Include `--help` flag with usage
3. Support `--json` output when applicable
4. Update this README
5. Add tests in `tests/test_scripts/`
