# Phase 11A: Import Fix Guide

**Status:** Ready for Implementation
**Affected Files:** 21 test files with import errors
**Estimated Time:** 3-4 hours

---

## Summary

Phase 10 refactoring converted standalone functions to class methods, but the backward compatibility layer in `main.py` doesn't export all needed functions. Tests need updating to use the new modular API.

---

## Import Mapping Reference

### Core Executor Functions
```python
# OLD (from main.py)
from main import run_ast_grep, run_command, stream_ast_grep_results

# NEW (modular)
from ast_grep_mcp.core.executor import run_ast_grep, run_command, stream_ast_grep_results
```

### Search/Find Functions
```python
# OLD
from main import find_code, find_code_by_rule, dump_syntax_tree

# NEW - These are now in tools, accessed via MCP
# For testing, import the implementation:
from ast_grep_mcp.features.search.service import (
    find_code_impl as find_code,
    find_code_by_rule_impl as find_code_by_rule,
    dump_syntax_tree_impl as dump_syntax_tree
)
```

### Format Functions
```python
# OLD
from main import format_matches_as_text, format_diff_with_colors

# NEW
from ast_grep_mcp.utils.formatters import format_matches_as_text, format_diff_with_colors
```

### Deduplication - Detection
```python
# OLD
from main import group_duplicates, detect_variations_between_blocks

# NEW - These are now class methods
from ast_grep_mcp.features.deduplication.detector import DuplicationDetector
# In test setup:
detector = DuplicationDetector(executor)
groups = detector.group_duplicates(matches, min_similarity, min_lines)
```

### Deduplication - Analysis
```python
# OLD
from main import (
    classify_variation,
    align_code_blocks,
    analyze_duplicate_variations,
    identify_varying_literals
)

# NEW - Class methods
from ast_grep_mcp.features.deduplication.analyzer import PatternAnalyzer
analyzer = PatternAnalyzer(executor)
result = analyzer.classify_variation(variation_data)
alignment = analyzer.align_code_blocks(code1, code2)
```

### Deduplication - Generation
```python
# OLD
from main import (
    extract_function_template,
    generate_parameterized_function,
    render_python_function,
    generate_replacement_call
)

# NEW - Class methods
from ast_grep_mcp.features.deduplication.generator import CodeGenerator
generator = CodeGenerator()
template = generator.extract_function_template(code, params)
func_code = generator.generate_parameterized_function(template, language)
```

### Deduplication - Ranking
```python
# OLD
from main import (
    calculate_deduplication_score,
    rank_deduplication_candidates,
    calculate_refactoring_complexity
)

# NEW - Class methods
from ast_grep_mcp.features.deduplication.ranker import DuplicationRanker
ranker = DuplicationRanker()
score = ranker.calculate_deduplication_score(candidate)
ranked = ranker.rank_deduplication_candidates(candidates)
```

### Deduplication - Coverage
```python
# OLD
from main import (
    has_test_coverage,
    get_test_coverage_for_files,
    find_test_file_patterns,
    _get_potential_test_paths  # Private function
)

# NEW - Mix of module functions and class methods
from ast_grep_mcp.features.deduplication.coverage import (
    has_test_coverage,
    get_test_coverage_for_files,
    find_test_file_patterns,
    TestCoverageDetector
)
# For private functions, instantiate class:
detector = TestCoverageDetector()
paths = detector._get_potential_test_paths(file_path)
```

### Deduplication - Impact
```python
# OLD
from main import analyze_deduplication_impact

# NEW
from ast_grep_mcp.features.deduplication.impact import analyze_deduplication_impact
```

### Deduplication - Recommendations
```python
# OLD
from main import (
    generate_deduplication_recommendation,
    _generate_refactoring_strategies  # Private
)

# NEW
from ast_grep_mcp.features.deduplication.recommendations import (
    generate_deduplication_recommendation,
    RecommendationEngine
)
# For private functions:
engine = RecommendationEngine()
strategies = engine._generate_refactoring_strategies(candidate)
```

### Deduplication - Reporting
```python
# OLD
from main import (
    create_enhanced_duplication_response,
    generate_before_after_example,
    visualize_complexity
)

# NEW
from ast_grep_mcp.features.deduplication.reporting import (
    create_enhanced_duplication_response,
    generate_before_after_example,
    visualize_complexity
)
```

### Complexity Analysis
```python
# OLD
from main import (
    analyze_complexity,
    calculate_cyclomatic_complexity,
    calculate_cognitive_complexity
)

# NEW - Mix of functions and classes
from ast_grep_mcp.features.complexity.analyzer import (
    calculate_cyclomatic_complexity,
    calculate_cognitive_complexity,
    analyze_file_complexity
)
from ast_grep_mcp.features.complexity.metrics import ComplexityMetrics
```

### Code Quality
```python
# OLD
from main import (
    create_linting_rule,
    _validate_rule_pattern,  # Private
    _template_to_linting_rule  # Private
)

# NEW
from ast_grep_mcp.features.quality.rules import create_linting_rule, RULE_TEMPLATES
from ast_grep_mcp.features.quality.validator import (
    _validate_rule_pattern,
    _validate_rule_definition
)
```

### Code Formatting
```python
# OLD
from main import (
    format_python_code,
    format_typescript_code,
    detect_import_insertion_point,
    detect_return_value
)

# NEW
from ast_grep_mcp.utils.formatters import (
    format_python_code,
    format_typescript_code
)
from ast_grep_mcp.features.deduplication.generator import CodeGenerator
# For import/return detection:
generator = CodeGenerator()
insert_point = generator._detect_import_insertion_point(code)
return_val = generator._detect_return_value(code)
```

### Template Functions
```python
# OLD
from main import (
    PYTHON_FUNCTION_TEMPLATE,
    TYPESCRIPT_FUNCTION_TEMPLATE,
    format_python_function
)

# NEW
from ast_grep_mcp.utils.templates import (
    PYTHON_FUNCTION_TEMPLATE,
    TYPESCRIPT_FUNCTION_TEMPLATE,
    format_python_function
)
```

### Data Models
```python
# OLD
from main import (
    AlignmentResult,
    AlignmentSegment,
    DiffTree,
    DiffTreeNode,
    VariationCategory,
    FunctionTemplate
)

# NEW
from ast_grep_mcp.models.deduplication import (
    AlignmentResult,
    AlignmentSegment,
    DiffTree,
    DiffTreeNode,
    VariationCategory,
    FunctionTemplate,
    ParameterInfo,
    FileDiff,
    DiffPreview
)
```

### Configuration & Exceptions
```python
# OLD
from main import ConfigurationError, InvalidYAMLError, CustomLanguageConfig

# NEW
from ast_grep_mcp.core.exceptions import ConfigurationError, InvalidYAMLError
from ast_grep_mcp.models.config import CustomLanguageConfig
```

### Cache
```python
# OLD
from main import QueryCache, get_query_cache

# NEW
from ast_grep_mcp.core.cache import QueryCache
# In test setup:
cache = QueryCache()
```

### Validation Functions
```python
# OLD
from main import (
    _validate_code_for_language,  # Private
    _count_function_parameters,   # Private
    _extract_function_names_from_code  # Private
)

# NEW - These may be in different modules or need class instantiation
from ast_grep_mcp.features.deduplication.analyzer import PatternAnalyzer
from ast_grep_mcp.utils.validation import validate_code_syntax

# For private functions, you may need to:
# 1. Make them public in the new module
# 2. Access via class instance
# 3. Duplicate the logic in test helpers
```

---

## Fix Patterns by Test File

### 1. test_unit.py (28 imports) ⚠️⚠️⚠️

**Approach:** This file tests MCP tools, needs special handling

**Current Pattern:**
```python
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    import main
    from main import format_matches_as_text, run_ast_grep
    main.register_mcp_tools()
    find_code = main.mcp.tools.get("find_code")
```

**New Pattern:**
```python
# Import directly from service implementations
from ast_grep_mcp.features.search.service import find_code_impl as find_code
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.utils.formatters import format_matches_as_text

# Or use the registry
from ast_grep_mcp.server.registry import register_all_tools
```

### 2. test_benchmark.py (9 imports) ⚠️⚠️

**Imports to fix:**
- `find_duplication` → Use `DuplicationDetector` class
- `analyze_deduplication_candidates` → Use `DuplicationRanker` class
- `benchmark_deduplication` → Import from `features.deduplication.benchmark`

### 3. Files with 1-2 imports each (19 files) ⚠️

**Strategy:** Quick batch fixes using the mapping reference above

Most common fixes:
- Data models → `ast_grep_mcp.models.deduplication`
- Standalone functions → Class methods (instantiate class in test setup)
- Formatters → `ast_grep_mcp.utils.formatters`
- Templates → `ast_grep_mcp.utils.templates`

---

## Step-by-Step Fix Process

### Step 1: Start with Data Models (Easiest)

Files that only import data classes are easiest to fix:
```bash
grep -l "AlignmentResult\|DiffTree\|VariationCategory" tests/unit/test_*.py
```

Fix by replacing:
```python
from main import AlignmentResult, DiffTree
# with:
from ast_grep_mcp.models.deduplication import AlignmentResult, DiffTree
```

### Step 2: Fix Utility Functions

Files importing formatters/templates:
```python
from main import format_matches_as_text, format_python_function
# with:
from ast_grep_mcp.utils.formatters import format_matches_as_text
from ast_grep_mcp.utils.templates import format_python_function
```

### Step 3: Fix Class-Based APIs

For files needing deduplication classes:

**Before:**
```python
from main import group_duplicates, classify_variation

def test_something():
    groups = group_duplicates(matches, 0.8, 5)
    classification = classify_variation(data)
```

**After:**
```python
from ast_grep_mcp.features.deduplication.detector import DuplicationDetector
from ast_grep_mcp.features.deduplication.analyzer import PatternAnalyzer
from ast_grep_mcp.core.executor import run_ast_grep

@pytest.fixture
def detector():
    executor = run_ast_grep  # or mock it
    return DuplicationDetector(executor)

@pytest.fixture
def analyzer():
    executor = run_ast_grep
    return PatternAnalyzer(executor)

def test_something(detector, analyzer):
    groups = detector.group_duplicates(matches, 0.8, 5)
    classification = analyzer.classify_variation(data)
```

### Step 4: Add Fixtures to conftest.py

For commonly used classes, add fixtures:

```python
# In tests/conftest.py
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
```

Then use in tests:
```python
def test_something(duplication_detector, pattern_analyzer):
    # Classes are automatically injected
    groups = duplication_detector.group_duplicates(...)
    classification = pattern_analyzer.classify_variation(...)
```

### Step 5: Handle Private Functions

For private functions (`_function_name`):

**Option 1:** Make them public in new module
```python
# In module file
def _validate_code_for_language(code, language):  # Remove underscore
    ...
```

**Option 2:** Access via class instance
```python
# In test
analyzer = PatternAnalyzer(executor)
result = analyzer._validate_code_for_language(code, lang)
```

**Option 3:** Duplicate in test helpers
```python
# In tests/helpers.py
def validate_code_for_language(code, language):
    # Copy implementation for testing
    ...
```

---

## Validation Checklist

After each file fix:
- [ ] Run the specific test file: `uv run pytest tests/unit/test_xxx.py -v`
- [ ] Check all tests in that file pass
- [ ] Verify no new import errors
- [ ] Commit with descriptive message: `fix: update test imports for test_xxx.py`

After all files fixed:
- [ ] Run full test suite: `uv run pytest -v`
- [ ] Verify 1,536 tests collected (no collection errors)
- [ ] Check pass/fail status
- [ ] Run type checking: `uv run mypy tests/`
- [ ] Run linting: `uv run ruff check tests/`

---

## Time Estimates

| Task | Files | Time |
|------|-------|------|
| Data model imports | 5 files | 15 min |
| Utility function imports | 6 files | 30 min |
| Class-based API conversions | 8 files | 90 min |
| test_unit.py (complex) | 1 file | 45 min |
| test_benchmark.py | 1 file | 20 min |
| Add fixtures to conftest.py | - | 20 min |
| Testing & validation | - | 30 min |
| **Total** | **21 files** | **~4 hours** |

---

## Next Steps

1. Add class fixtures to `tests/conftest.py` (from Step 4)
2. Start with easiest files (data models)
3. Work through utility functions
4. Handle class-based conversions
5. Tackle test_unit.py last (most complex)
6. Run full test suite
7. Document results in Phase 11 completion report

---

**Status:** Ready to implement | **Priority:** HIGH | **Est. Time:** 3-4 hours
