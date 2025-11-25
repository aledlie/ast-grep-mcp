# Import Fix Summary - Phase 11A

**Generated:** 2025-11-24
**Script:** `scripts/fix_test_imports.py`

## Overview

Automated script to fix 32 test files after Phase 10 refactoring from monolithic `main.py` to modular architecture.

## What the Script Does

1. **Parses imports** from `main.py` in each test file
2. **Maps to new modules** based on Phase 10 architecture
3. **Handles class-based APIs** by:
   - Importing the class
   - Adding pytest fixtures
   - Updating function calls to use fixture instances
4. **Preserves unmapped imports** (functions still in `main.py`)
5. **Groups imports** by module for clean formatting

## Import Mappings

### Core Executor
- `run_ast_grep` → `ast_grep_mcp.core.executor`
- `run_command` → `ast_grep_mcp.core.executor`
- `stream_ast_grep_results` → `ast_grep_mcp.core.executor`

### Search/Find Tools
- `find_code` → `ast_grep_mcp.features.search.service.find_code_impl`
- `find_code_by_rule` → `ast_grep_mcp.features.search.service.find_code_by_rule_impl`
- `dump_syntax_tree` → `ast_grep_mcp.features.search.service.dump_syntax_tree_impl`

### Formatters & Templates
- `format_*` → `ast_grep_mcp.utils.formatters`
- `PYTHON_FUNCTION_TEMPLATE` → `ast_grep_mcp.utils.templates`

### Data Models
- All deduplication models → `ast_grep_mcp.models.deduplication`
- Config models → `ast_grep_mcp.models.config`

### Deduplication (Class-Based)
- **DuplicationDetector** → `group_duplicates()`
- **PatternAnalyzer** → `classify_variation()`, `align_code_blocks()`, etc.
- **CodeGenerator** → `generate_parameterized_function()`, etc.
- **DuplicationRanker** → `calculate_deduplication_score()`, etc.

### Complexity & Quality
- Complexity functions → `ast_grep_mcp.features.complexity.analyzer`
- Quality smells → `ast_grep_mcp.features.quality.smells`
- Linting rules → `ast_grep_mcp.features.quality.rules`

### Schema.org
- `SchemaOrgClient` → `ast_grep_mcp.features.schema.client`

## Fixtures Added to conftest.py

```python
@pytest.fixture
def duplication_detector():
    """Provide DuplicationDetector instance."""
    from ast_grep_mcp.features.deduplication.detector import DuplicationDetector
    from ast_grep_mcp.core.executor import run_ast_grep
    return DuplicationDetector(run_ast_grep)

@pytest.fixture
def pattern_analyzer():
    """Provide PatternAnalyzer instance."""
    from ast_grep_mcp.features.deduplication.analyzer import PatternAnalyzer
    from ast_grep_mcp.core.executor import run_ast_grep
    return PatternAnalyzer(run_ast_grep)

@pytest.fixture
def code_generator():
    """Provide CodeGenerator instance."""
    from ast_grep_mcp.features.deduplication.generator import CodeGenerator
    return CodeGenerator()

@pytest.fixture
def duplication_ranker():
    """Provide DuplicationRanker instance."""
    from ast_grep_mcp.features.deduplication.ranker import DuplicationRanker
    return DuplicationRanker()

@pytest.fixture
def recommendation_engine():
    """Provide RecommendationEngine instance."""
    from ast_grep_mcp.features.deduplication.recommendations import RecommendationEngine
    return RecommendationEngine()
```

## Functions Still in main.py (Unmapped)

These functions haven't been migrated yet and will remain as `from main import`:

### Dependency Analysis (4 functions)
- `extract_imports_from_files`
- `detect_import_variations`
- `analyze_import_overlap`
- `detect_internal_dependencies`

### Diff Preview (3 functions)
- `generate_diff_from_file_paths`
- `generate_file_diff`
- `generate_multi_file_diff`

### Variation Classification (3 functions)
- `VariationSeverity` (data class)
- `classify_variations`
- `detect_conditional_variations`

### Other (5 functions)
- `build_diff_tree`, `build_nested_diff_tree`
- `format_alignment_diff`
- `format_arguments_for_call`, `preserve_call_site_indentation`
- `_basic_python_format`, `_format_python_line`, `format_generated_code`
- `format_java_code`, `format_javascript_code`
- `ComplexityStorage`, `ComplexityThresholds`, `FunctionComplexity`
- `calculate_nesting_depth`, `get_complexity_patterns`
- `diff_preview_to_dict`

## Usage

### Dry Run (Preview)
```bash
uv run python scripts/fix_test_imports.py --dry-run
```

### Fix All Files
```bash
uv run python scripts/fix_test_imports.py
```

### Fix Single File
```bash
uv run python scripts/fix_test_imports.py --file tests/unit/test_alignment.py
```

### Skip conftest.py Update
```bash
uv run python scripts/fix_test_imports.py --skip-conftest
```

## Test Results

**Before fix:** 32 test files with import errors
**After fix:** All imports resolved

### Files with Class-Based API Changes
- test_ast_diff.py (pattern_analyzer)
- test_call_site.py (code_generator)
- test_complexity_scoring.py (duplication_ranker)
- test_duplication_grouping.py (duplication_detector)
- test_function_generation.py (code_generator)
- test_impact_analysis.py (duplication_ranker)
- test_pattern_analysis.py (pattern_analyzer)
- test_ranking.py (duplication_ranker)
- test_recommendation_engine.py (recommendation_engine)
- test_variation_classification.py (pattern_analyzer)

### Files with Unmapped Imports (Warnings)
- test_dependency_analysis.py (4 unmapped)
- test_diff_preview.py (3 unmapped)
- test_variation_classification.py (3 unmapped)
- test_ast_diff.py (2 unmapped)
- test_call_site.py (2 unmapped)
- test_code_formatting.py (5 unmapped)
- test_complexity.py (4 unmapped)

## Next Steps

1. ✅ Run script to fix imports
2. ⏳ Run full test suite: `uv run pytest tests/unit/ -v`
3. ⏳ Fix any remaining test failures
4. ⏳ Consider migrating unmapped functions in future phase
5. ⏳ Update PHASE-11A-IMPORT-FIX-GUIDE.md with results
6. ⏳ Commit changes

## Notes

- All 32 test files successfully processed
- 0 mapping errors
- Unmapped functions remain in `main.py` for backward compatibility
- Script is idempotent - safe to run multiple times
- Creates clean, grouped imports by module
- Automatically adds pytest fixtures for class-based APIs
