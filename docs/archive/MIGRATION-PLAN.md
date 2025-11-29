# Step-by-Step Migration Plan

**Date:** 2025-11-24
**Status:** Phase 2 Complete
**Estimated Duration:** 4-6 weeks (1 developer, full-time)

## Progress
- ✅ Phase 0: Initial Project Structure (Complete)
- ✅ Phase 1: Core Infrastructure (Complete)
- ✅ Phase 2: Extract Data Models (Complete)
- ⏳ Phase 3: Service Layer (Next)

## Overview

This document provides a detailed, step-by-step plan to migrate from the single-file architecture (19,477 lines) to the modular architecture. Each phase includes specific commands, validation steps, and rollback procedures.

## Prerequisites

### Required Tools
```bash
# Verify Python environment
python --version  # Should be 3.13+

# Verify uv package manager
uv --version

# Verify tests work in current state
uv run pytest  # Should pass 1,561 tests

# Verify type checking works
uv run mypy main.py  # Should have 0 errors

# Verify linting works
uv run ruff check .  # Should be clean
```

### Backup Strategy
```bash
# Create backup branch
git checkout -b backup/pre-refactor
git push origin backup/pre-refactor

# Create backup file
cp main.py main.py.backup

# Create refactor branch
git checkout main
git checkout -b refactor/modular-architecture
```

### Communication Plan

**Before starting:**
- [ ] Announce refactor to team
- [ ] Request feature freeze for 4-6 weeks
- [ ] Schedule daily standups for progress updates
- [ ] Create tracking issue in GitHub

## Phase 0: Preparation (Day 1)

### Step 1: Create Directory Structure

```bash
# Create all directories
mkdir -p src/ast_grep_mcp/{core,models,utils,features,server}
mkdir -p src/ast_grep_mcp/features/{search,rewrite,schema,deduplication,complexity,quality}

# Create all __init__.py files
touch src/ast_grep_mcp/__init__.py
touch src/ast_grep_mcp/core/__init__.py
touch src/ast_grep_mcp/models/__init__.py
touch src/ast_grep_mcp/utils/__init__.py
touch src/ast_grep_mcp/features/__init__.py
touch src/ast_grep_mcp/features/{search,rewrite,schema,deduplication,complexity,quality}/__init__.py
touch src/ast_grep_mcp/server/__init__.py

# Verify structure
tree src/ast_grep_mcp -L 2
```

**Expected output:**
```
src/ast_grep_mcp
├── __init__.py
├── core
│   └── __init__.py
├── features
│   ├── __init__.py
│   ├── complexity
│   ├── deduplication
│   ├── quality
│   ├── rewrite
│   ├── search
│   └── schema
├── models
│   └── __init__.py
├── server
│   └── __init__.py
└── utils
    └── __init__.py
```

### Step 2: Update pyproject.toml

```toml
# Add to pyproject.toml

[project]
name = "ast-grep-mcp"
# ... existing fields

[tool.setuptools.packages.find]
where = ["src"]

[tool.mypy]
mypy_path = "$MYPY_CONFIG_FILE_DIR/src"
explicit_package_bases = true

[[tool.mypy.overrides]]
module = "ast_grep_mcp.*"
ignore_missing_imports = false
```

### Step 3: Set Up Package Installation

```bash
# Install in editable mode
uv pip install -e .

# Verify import works
python -c "import ast_grep_mcp; print('Package structure created')"
```

**Commit:**
```bash
git add src/ pyproject.toml
git commit -m "refactor: create modular directory structure"
```

## Phase 1: Core Infrastructure (Days 2-4)

### Day 2: Exceptions and Logging

**Step 1: Extract Exceptions**

```bash
# Create core/exceptions.py
cat > src/ast_grep_mcp/core/exceptions.py << 'EOF'
"""Custom exceptions for ast-grep MCP server."""


class AstGrepError(Exception):
    """Base exception for ast-grep related errors."""
    pass


class AstGrepNotFoundError(AstGrepError):
    """Raised when ast-grep binary is not found."""

    def __init__(self, paths_searched: list[str]) -> None:
        self.paths_searched = paths_searched
        super().__init__(
            f"ast-grep not found. Searched in: {', '.join(paths_searched)}. "
            "Install it from https://ast-grep.github.io/guide/quick-start.html"
        )


class InvalidYAMLError(AstGrepError):
    """Raised when rule YAML is invalid."""

    def __init__(self, yaml_content: str, error: str) -> None:
        self.yaml_content = yaml_content
        self.error = error
        super().__init__(
            f"Invalid YAML rule: {error}. Make sure the YAML is properly formatted "
            "and includes a 'kind' field. Example:\nrule:\n  kind: function_declaration"
        )


class ConfigurationError(AstGrepError):
    """Raised when configuration is invalid or not found."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Configuration error: {message}")


class AstGrepExecutionError(AstGrepError):
    """Raised when ast-grep command execution fails."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"ast-grep command failed with exit code {returncode}. "
            f"Command: {' '.join(cmd)}\nError: {stderr}"
        )


class NoMatchesError(AstGrepError):
    """Raised when no matches are found (used internally for early termination)."""
    pass
EOF
```

**Step 2: Update core/__init__.py**

```bash
cat > src/ast_grep_mcp/core/__init__.py << 'EOF'
"""Core infrastructure for ast-grep MCP server."""

from ast_grep_mcp.core.exceptions import (
    AstGrepError,
    AstGrepNotFoundError,
    InvalidYAMLError,
    ConfigurationError,
    AstGrepExecutionError,
    NoMatchesError,
)

__all__ = [
    "AstGrepError",
    "AstGrepNotFoundError",
    "InvalidYAMLError",
    "ConfigurationError",
    "AstGrepExecutionError",
    "NoMatchesError",
]
EOF
```

**Step 3: Extract Logging Setup**

Copy lines 226-262 from main.py to `src/ast_grep_mcp/core/logging.py`

```bash
# Extract logging setup
# Manually copy lines 226-262 to src/ast_grep_mcp/core/logging.py
# Update imports to be absolute
```

**Step 4: Test Extraction**

```bash
# Test imports work
python -c "from ast_grep_mcp.core.exceptions import AstGrepError; print('✓')"
python -c "from ast_grep_mcp.core.logging import get_logger; print('✓')"

# Run unit tests (should still import from main.py)
uv run pytest tests/unit/ -v

# Commit
git add src/ast_grep_mcp/core/
git commit -m "refactor: extract exceptions and logging to core/"
```

### Day 3: Config and Sentry

**Step 1: Extract Configuration**

Copy lines 30-37, 577-622, 663-800 from main.py to `src/ast_grep_mcp/core/config.py`

**Step 2: Extract Sentry**

Copy lines 274-410 from main.py to `src/ast_grep_mcp/core/sentry.py`

**Step 3: Update Imports**

```python
# In core/config.py
from ast_grep_mcp.core.exceptions import ConfigurationError

# In core/sentry.py
from ast_grep_mcp.core.logging import get_logger
```

**Step 4: Test**

```bash
# Test imports
python -c "from ast_grep_mcp.core.config import parse_args_and_get_config; print('✓')"
python -c "from ast_grep_mcp.core.sentry import init_sentry; print('✓')"

# Run tests
uv run pytest tests/unit/ -k "config or sentry" -v

# Commit
git add src/ast_grep_mcp/core/
git commit -m "refactor: extract config and sentry to core/"
```

### Day 4: Cache and Executor

**Step 1: Extract Cache**

Copy lines 456-576 from main.py to `src/ast_grep_mcp/core/cache.py`

```python
# Update imports
from ast_grep_mcp.core.logging import get_logger
```

**Step 2: Extract Executor**

Copy lines 801-1307 from main.py to `src/ast_grep_mcp/core/executor.py`

```python
# Update imports
from ast_grep_mcp.core.exceptions import (
    AstGrepNotFoundError,
    InvalidYAMLError,
    AstGrepExecutionError,
    NoMatchesError,
)
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.core.cache import get_query_cache
from ast_grep_mcp.core.config import CONFIG_PATH, AstGrepConfig
```

**Step 3: Test**

```bash
# Test imports
python -c "from ast_grep_mcp.core.cache import QueryCache; print('✓')"
python -c "from ast_grep_mcp.core.executor import run_ast_grep; print('✓')"

# Run all unit tests
uv run pytest tests/unit/ -v

# Commit
git add src/ast_grep_mcp/core/
git commit -m "refactor: extract cache and executor to core/"
```

**Phase 1 Complete Checklist:**
- [x] All core modules created
- [x] All imports updated to absolute paths
- [x] All tests still pass
- [x] Type checking passes
- [ ] Committed and pushed

## Phase 2: Models (Days 5-6)

### Day 5: Config and Deduplication Models

**Step 1: Extract Config Models**

```bash
# Create models/config.py
# Copy CustomLanguageConfig (lines 577-595)
# Copy AstGrepConfig (lines 597-622)
```

**Step 2: Extract Deduplication Models**

```bash
# Create models/deduplication.py
# Copy all dataclasses from lines 5785-14895:
# - VariationCategory
# - VariationSeverity
# - AlignmentSegment
# - AlignmentResult
# - DiffTreeNode
# - DiffTree
# - FunctionTemplate
# - ParameterType
# - ParameterInfo
# - FileDiff
# - DiffPreview
# - EnhancedDuplicationCandidate
```

**Step 3: Test**

```bash
python -c "from ast_grep_mcp.models.config import AstGrepConfig; print('✓')"
python -c "from ast_grep_mcp.models.deduplication import AlignmentResult; print('✓')"

uv run pytest tests/unit/ -v

git add src/ast_grep_mcp/models/
git commit -m "refactor: extract config and deduplication models"
```

### Day 6: Complexity and Standards Models

**Step 1: Extract Complexity Models**

```bash
# Create models/complexity.py
# Copy from lines 17336-17358:
# - ComplexityMetrics
# - FunctionComplexity
# - ComplexityThresholds
```

**Step 2: Extract Standards Models**

```bash
# Create models/standards.py
# Copy from lines 18216-18907:
# - RuleValidationError
# - RuleStorageError
# - LintingRule
# - RuleTemplate
# - RuleValidationResult
# - RuleViolation
# - RuleSet
# - EnforcementResult
# - RuleExecutionContext
```

**Step 3: Update Imports**

```python
# In models/standards.py
from ast_grep_mcp.core.exceptions import (
    RuleValidationError as BaseRuleValidationError,
    RuleStorageError as BaseRuleStorageError,
)
```

**Step 4: Test**

```bash
python -c "from ast_grep_mcp.models.complexity import ComplexityMetrics; print('✓')"
python -c "from ast_grep_mcp.models.standards import LintingRule; print('✓')"

uv run pytest tests/unit/ -v
uv run mypy src/ast_grep_mcp/

git add src/ast_grep_mcp/models/
git commit -m "refactor: extract complexity and standards models"
```

**Phase 2 Complete Checklist:**
- [x] All models extracted (config, deduplication, complexity, standards)
- [x] No business logic in models (pure data structures)
- [x] All imports updated (models/__init__.py exports all)
- [x] Tests pass (config validation tests verified)
- [x] Type checking passes (model imports verified)

## Phase 3: Utils (Days 7-9)

### Day 7: Templates

**Step 1: Extract Templates**

```bash
# Create utils/templates.py
# Copy lines 38-410:
# - PYTHON_CLASS_TEMPLATE
# - JAVA_CLASS_TEMPLATE
# - TYPESCRIPT_CLASS_TEMPLATE
# - format_python_class
# - format_java_code
# - format_typescript_class
# - format_java_method
# - format_typescript_function
```

**Step 2: Test**

```bash
python -c "from ast_grep_mcp.utils.templates import format_python_class; print('✓')"

uv run pytest tests/unit/test_templates.py -v

git add src/ast_grep_mcp/utils/
git commit -m "refactor: extract code generation templates to utils/"
```

### Day 8: Formatters and Text

**Step 1: Extract Formatters**

```bash
# Create utils/formatters.py
# Extract format_matches_as_text (lines 5674-5704)
# Extract format_diff_with_colors (from deduplication section)
# Extract other formatting utilities
```

**Step 2: Extract Text Utilities**

```bash
# Create utils/text.py
# Extract normalize_code (lines 5707-5723)
# Extract calculate_similarity (lines 5726-5747)
```

**Step 3: Test**

```bash
python -c "from ast_grep_mcp.utils.formatters import format_matches_as_text; print('✓')"
python -c "from ast_grep_mcp.utils.text import normalize_code; print('✓')"

uv run pytest tests/unit/ -v

git add src/ast_grep_mcp/utils/
git commit -m "refactor: extract formatters and text utilities"
```

### Day 9: Validation

**Step 1: Extract Validation**

```bash
# Create utils/validation.py
# Extract validate_config_file (lines 623-662)
# Extract YAML validation utilities
```

**Step 2: Update Imports**

```python
# In utils/validation.py
from ast_grep_mcp.core.exceptions import InvalidYAMLError, ConfigurationError
from ast_grep_mcp.models.config import AstGrepConfig
```

**Step 3: Test**

```bash
python -c "from ast_grep_mcp.utils.validation import validate_config_file; print('✓')"

uv run pytest tests/unit/ -v

git add src/ast_grep_mcp/utils/
git commit -m "refactor: extract validation utilities"
```

**Phase 3 Complete Checklist:**
- [ ] All utilities extracted
- [ ] No state in utilities
- [ ] All imports updated
- [ ] Tests pass

## Phase 4: Search Feature (Days 10-11)

### Day 10: Search Service

**Step 1: Create Service Module**

```bash
# Create features/search/service.py
# Extract business logic from tools:
# - dump_syntax_tree_impl (from lines 1323-1376)
# - test_match_code_rule_impl (from lines 1381-1450)
# - find_code_impl (from lines 1452-1625)
# - find_code_by_rule_impl (from lines 1627-1814)
# - scan_project_impl (from lines 1816-2093)
```

**Step 2: Update Imports**

```python
# In features/search/service.py
from ast_grep_mcp.core.executor import run_ast_grep, get_supported_languages
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.core.cache import get_query_cache
from ast_grep_mcp.core.config import CONFIG_PATH
from ast_grep_mcp.utils.formatters import format_matches_as_text
```

**Step 3: Test**

```bash
python -c "from ast_grep_mcp.features.search.service import find_code_impl; print('✓')"

uv run pytest tests/unit/test_unit.py -v

git add src/ast_grep_mcp/features/search/
git commit -m "refactor: extract search service layer"
```

### Day 11: Search Tools

**Step 1: Create Tools Module**

```bash
# Create features/search/tools.py
```

```python
"""MCP tool definitions for search features."""

from typing import Literal
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.features.search.service import (
    dump_syntax_tree_impl,
    test_match_code_rule_impl,
    find_code_impl,
    find_code_by_rule_impl,
    scan_project_impl,
)

DumpFormat = Literal["pattern", "ast", "cst"]
OutputFormat = Literal["text", "json"]


def register_search_tools(mcp: FastMCP) -> None:
    """Register all search-related MCP tools."""

    @mcp.tool()
    def dump_syntax_tree(
        code: str = Field(description="The code you need"),
        language: str = Field(description="The language of the code"),
        format: DumpFormat = Field(description="Code dump format", default="cst"),
    ) -> str:
        """Dump code's syntax structure or dump a query's pattern structure."""
        return dump_syntax_tree_impl(code, language, format)

    @mcp.tool()
    def test_match_code_rule(
        pattern: str = Field(description="The pattern to search for"),
        code: str = Field(description="The code to match against"),
        language: str = Field(description="The language of the code"),
    ) -> str:
        """Test if a pattern matches code without requiring a project folder."""
        return test_match_code_rule_impl(pattern, code, language)

    @mcp.tool()
    def find_code(
        pattern: str = Field(description="The pattern to search for"),
        path: str = Field(description="File or folder path to search in"),
        language: str = Field(description="The language to search in"),
        output_format: OutputFormat = Field(default="text"),
    ) -> str:
        """Find code using ast-grep pattern matching."""
        return find_code_impl(pattern, path, language, output_format)

    @mcp.tool()
    def find_code_by_rule(
        rule_yaml: str = Field(description="YAML rule definition"),
        path: str = Field(description="File or folder path to search in"),
        language: str = Field(description="The language to search in"),
        output_format: OutputFormat = Field(default="text"),
    ) -> str:
        """Find code using ast-grep YAML rules."""
        return find_code_by_rule_impl(rule_yaml, path, language, output_format)

    @mcp.tool()
    def scan_project(
        pattern: str = Field(description="The pattern to search for"),
        project_folder: str = Field(description="Project folder to scan"),
        language: str = Field(description="The language to search in"),
        max_results: int = Field(default=100),
        output_format: OutputFormat = Field(default="text"),
    ) -> str:
        """Scan entire project for pattern matches (streaming)."""
        return scan_project_impl(pattern, project_folder, language, max_results, output_format)
```

**Step 2: Test Tools**

```bash
# Test tool registration
python -c "
from mcp.server.fastmcp import FastMCP
from ast_grep_mcp.features.search.tools import register_search_tools

mcp = FastMCP('test')
register_search_tools(mcp)
print(f'Registered {len(mcp.tools)} tools')
"

# Run integration tests
uv run pytest tests/integration/test_search_integration.py -v

git add src/ast_grep_mcp/features/search/
git commit -m "refactor: extract search MCP tools"
```

**Phase 4 Complete Checklist:**
- [ ] Search service extracted
- [ ] Search tools extracted
- [ ] Tool registration works
- [ ] All search tests pass

## Phase 5: Rewrite Feature (Days 12-13)

### Day 12: Backup Module

**Step 1: Extract Backup Management**

```bash
# Create features/rewrite/backup.py
# Extract backup-related functions
# (Backup creation, restoration, listing)
```

**Step 2: Test Backup**

```bash
python -c "from ast_grep_mcp.features.rewrite.backup import create_backup; print('✓')"

uv run pytest tests/unit/ -k "backup" -v

git add src/ast_grep_mcp/features/rewrite/
git commit -m "refactor: extract backup management"
```

### Day 13: Rewrite Service and Tools

**Step 1: Extract Rewrite Service**

```bash
# Create features/rewrite/service.py
# Extract rewrite_code_impl
# Extract list_backups_impl
# Extract rollback_rewrite_impl
```

**Step 2: Create Rewrite Tools**

```bash
# Create features/rewrite/tools.py
# Similar pattern to search tools
```

**Step 3: Test**

```bash
uv run pytest tests/unit/ -k "rewrite" -v
uv run pytest tests/integration/ -k "rewrite" -v

git add src/ast_grep_mcp/features/rewrite/
git commit -m "refactor: extract rewrite service and tools"
```

**Phase 5 Complete Checklist:**
- [ ] Backup module extracted
- [ ] Rewrite service extracted
- [ ] Rewrite tools extracted
- [ ] All rewrite tests pass

## Phase 6: Schema Feature (Day 14)

### Step 1: Extract Schema Client

```bash
# Create features/schema/client.py
# Extract SchemaOrgClient class (lines 800-1307)
# Extract get_schema_org_client function
```

### Step 2: Create Schema Tools

```bash
# Create features/schema/tools.py
# Register 8 Schema.org tools
```

### Step 3: Test

```bash
python -c "from ast_grep_mcp.features.schema.client import SchemaOrgClient; print('✓')"

uv run pytest tests/unit/test_schema.py -v

git add src/ast_grep_mcp/features/schema/
git commit -m "refactor: extract schema.org feature"
```

**Phase 6 Complete Checklist:**
- [ ] Schema client extracted
- [ ] Schema tools extracted
- [ ] All schema tests pass
- [ ] Integration tests pass

## Phase 7: Deduplication Feature (Days 15-21)

This is the largest feature with 11 sub-modules. We'll extract incrementally.

### Day 15: Detector and Analyzer

**Step 1: Extract Detector**

```bash
# Create features/deduplication/detector.py
# Extract find_duplication_impl
# Extract detect_variations_between_blocks
# Extract detect_conditional_variations
# Extract group_duplicates
```

**Step 2: Extract Analyzer**

```bash
# Create features/deduplication/analyzer.py
# Extract classify_variation
# Extract classify_variations
# Extract analyze_duplicate_variations
# Extract build_diff_tree
# Extract align_code_blocks
```

**Step 3: Test**

```bash
uv run pytest tests/unit/test_duplication.py -v

git add src/ast_grep_mcp/features/deduplication/
git commit -m "refactor: extract deduplication detector and analyzer"
```

### Day 16-17: Generator and Ranker

**Step 1: Extract Generator**

```bash
# Create features/deduplication/generator.py
# Extract generate_refactoring_suggestions
# Extract generate_parameter_names
# Extract identify_varying_identifiers
# Extract generate_function_code
```

**Step 2: Extract Ranker**

```bash
# Create features/deduplication/ranker.py
# Extract calculate_deduplication_score
# Extract rank_deduplication_candidates
# Extract calculate_refactoring_complexity
# Extract get_complexity_level
```

**Step 3: Test**

```bash
uv run pytest tests/unit/test_ranking.py -v
uv run pytest tests/unit/test_function_generation.py -v

git add src/ast_grep_mcp/features/deduplication/
git commit -m "refactor: extract deduplication generator and ranker"
```

### Day 18-19: Coverage, Impact, Recommendations

**Step 1: Extract Coverage**

```bash
# Create features/deduplication/coverage.py
# Extract has_test_coverage
# Extract get_test_coverage_for_files
# Extract find_test_file_patterns
```

**Step 2: Extract Impact**

```bash
# Create features/deduplication/impact.py
# Extract analyze_deduplication_impact
# Extract assess_breaking_change_risk
```

**Step 3: Extract Recommendations**

```bash
# Create features/deduplication/recommendations.py
# Extract generate_deduplication_recommendation
# Extract generate_refactoring_strategies
```

**Step 4: Test**

```bash
uv run pytest tests/unit/test_coverage_detection.py -v
uv run pytest tests/unit/test_impact_analysis.py -v
uv run pytest tests/unit/test_recommendation_engine.py -v

git add src/ast_grep_mcp/features/deduplication/
git commit -m "refactor: extract coverage, impact, and recommendations"
```

### Day 20: Applicator, Reporting, Benchmark

**Step 1: Extract Applicator**

```bash
# Create features/deduplication/applicator.py
# Extract apply_deduplication_impl
# Extract create_deduplication_backup
# Extract validate_refactoring
```

**Step 2: Extract Reporting**

```bash
# Create features/deduplication/reporting.py
# Extract format_diff_with_colors
# Extract generate_before_after_example
# Extract visualize_complexity
# Extract create_enhanced_duplication_response
```

**Step 3: Extract Benchmark**

```bash
# Create features/deduplication/benchmark.py
# Extract benchmark_deduplication_impl
# Extract check_performance_regression
```

**Step 4: Test**

```bash
uv run pytest tests/unit/test_apply_deduplication.py -v
uv run pytest tests/unit/test_enhanced_reporting.py -v
uv run pytest tests/integration/test_benchmark.py -v

git add src/ast_grep_mcp/features/deduplication/
git commit -m "refactor: extract applicator, reporting, and benchmark"
```

### Day 21: Deduplication Tools

**Step 1: Create Tools Module**

```bash
# Create features/deduplication/tools.py
# Register 4 tools:
# - find_duplication
# - analyze_deduplication_candidates
# - apply_deduplication
# - benchmark_deduplication
```

**Step 2: Test All Deduplication**

```bash
# Run all deduplication tests
uv run pytest tests/unit/ -k "dedup" -v
uv run pytest tests/integration/ -k "dedup" -v

# Verify 1000+ tests pass
git add src/ast_grep_mcp/features/deduplication/
git commit -m "refactor: extract deduplication MCP tools"
```

**Phase 7 Complete Checklist:**
- [ ] All 11 deduplication modules extracted
- [ ] All imports updated
- [ ] 1000+ deduplication tests pass
- [ ] Integration tests pass

## Phase 8: Complexity Feature (Day 22-23)

### Day 22: Metrics and Storage

**Step 1: Extract Metrics**

```bash
# Create features/complexity/metrics.py
# Extract calculate_cyclomatic_complexity
# Extract calculate_cognitive_complexity
# Extract calculate_nesting_depth
```

**Step 2: Extract Storage**

```bash
# Create features/complexity/storage.py
# Extract ComplexityStorage class
# Extract store_complexity_results
# Extract get_historical_trends
```

**Step 3: Test**

```bash
uv run pytest tests/unit/test_complexity.py -v

git add src/ast_grep_mcp/features/complexity/
git commit -m "refactor: extract complexity metrics and storage"
```

### Day 23: Complexity Analyzer and Tools

**Step 1: Extract Analyzer**

```bash
# Create features/complexity/analyzer.py
# Extract analyze_complexity_impl
# Extract analyze_file_complexity
```

**Step 2: Create Tools**

```bash
# Create features/complexity/tools.py
# Register 2 tools:
# - analyze_complexity
# - test_sentry_integration
```

**Step 3: Test**

```bash
uv run pytest tests/unit/test_complexity.py -v
uv run pytest tests/integration/ -k "complexity" -v

git add src/ast_grep_mcp/features/complexity/
git commit -m "refactor: extract complexity analyzer and tools"
```

**Phase 8 Complete Checklist:**
- [ ] Complexity modules extracted
- [ ] All complexity tests pass
- [ ] Benchmarks pass (<10s for 1000 functions)

## Phase 9: Quality Feature (Day 24-25)

### Day 24: Smells and Rules

**Step 1: Extract Smells**

```bash
# Create features/quality/smells.py
# Extract detect_code_smells_impl
# Extract detect_long_functions
# Extract detect_parameter_bloat
# Extract detect_magic_numbers
```

**Step 2: Extract Rules**

```bash
# Create features/quality/rules.py
# Extract load_rules
# Extract create_rule_from_template
# Extract store_rule
```

**Step 3: Test**

```bash
uv run pytest tests/unit/test_code_smells.py -v
uv run pytest tests/unit/test_linting_rules.py -v

git add src/ast_grep_mcp/features/quality/
git commit -m "refactor: extract code smells and rules"
```

### Day 25: Validator, Enforcer, Tools

**Step 1: Extract Validator**

```bash
# Create features/quality/validator.py
# Extract validate_linting_rules_impl
# Extract validate_rule_syntax
```

**Step 2: Extract Enforcer**

```bash
# Create features/quality/enforcer.py
# Extract enforce_standards_impl
# Extract execute_rules
# Extract collect_violations
```

**Step 3: Create Tools**

```bash
# Create features/quality/tools.py
# Register 3 tools:
# - detect_code_smells
# - validate_linting_rules
# - enforce_standards
```

**Step 4: Test**

```bash
uv run pytest tests/unit/test_standards_enforcement.py -v

git add src/ast_grep_mcp/features/quality/
git commit -m "refactor: extract quality validator, enforcer, and tools"
```

**Phase 9 Complete Checklist:**
- [ ] Quality modules extracted
- [ ] All quality tests pass
- [ ] Integration tests pass

## Phase 10: Server Integration (Day 26-28)

### Day 26: Server Registry

**Step 1: Create Registry**

```bash
# Create server/registry.py
```

```python
"""Central tool registration for MCP server."""

from mcp.server.fastmcp import FastMCP

from ast_grep_mcp.features.search.tools import register_search_tools
from ast_grep_mcp.features.rewrite.tools import register_rewrite_tools
from ast_grep_mcp.features.deduplication.tools import register_deduplication_tools
from ast_grep_mcp.features.complexity.tools import register_complexity_tools
from ast_grep_mcp.features.quality.tools import register_quality_tools
from ast_grep_mcp.features.schema.tools import register_schema_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register all MCP tools from all features.

    This is the central registration point for all tools in the system.
    Tools are organized by feature and registered in order:
    1. Search (6 tools)
    2. Rewrite (3 tools)
    3. Deduplication (4 tools)
    4. Complexity (2 tools)
    5. Quality (3 tools)
    6. Schema.org (8 tools)

    Total: 27 tools
    """
    register_search_tools(mcp)
    register_rewrite_tools(mcp)
    register_deduplication_tools(mcp)
    register_complexity_tools(mcp)
    register_quality_tools(mcp)
    register_schema_tools(mcp)
```

**Step 2: Test Registry**

```bash
# Test all tools are registered
python -c "
from mcp.server.fastmcp import FastMCP
from ast_grep_mcp.server.registry import register_all_tools

mcp = FastMCP('ast-grep')
register_all_tools(mcp)
print(f'Total tools registered: {len(mcp.tools)}')
assert len(mcp.tools) == 27, f'Expected 27 tools, got {len(mcp.tools)}'
print('✓ All 27 tools registered successfully')
"

git add src/ast_grep_mcp/server/
git commit -m "refactor: create central tool registry"
```

### Day 27: Server Runner

**Step 1: Create Runner**

```bash
# Create server/runner.py
```

```python
"""MCP server entry point."""

from mcp.server.fastmcp import FastMCP

from ast_grep_mcp.core.config import parse_args_and_get_config
from ast_grep_mcp.core.sentry import init_sentry
from ast_grep_mcp.server.registry import register_all_tools

# Create FastMCP instance
mcp = FastMCP("ast-grep")


def run_mcp_server() -> None:
    """Run the MCP server.

    This function:
    1. Parses command-line arguments and loads configuration
    2. Initializes Sentry error tracking (if configured)
    3. Registers all MCP tools from all features
    4. Starts the MCP server with stdio transport
    """
    parse_args_and_get_config()  # Sets CONFIG_PATH global
    init_sentry()  # Initialize error tracking (no-op if not configured)
    register_all_tools(mcp)  # Register all 27 tools
    mcp.run(transport="stdio")
```

**Step 2: Test Runner**

```bash
# Test server startup
timeout 5 python -c "
from ast_grep_mcp.server.runner import run_mcp_server
import sys

# This will timeout after 5 seconds, which is expected
# We just want to verify it starts without errors
run_mcp_server()
" || echo "✓ Server starts successfully (timeout expected)"

git add src/ast_grep_mcp/server/
git commit -m "refactor: create MCP server runner"
```

### Day 28: Refactor main.py

**Step 1: Create New main.py**

```bash
# Backup old main.py
mv main.py main.py.old

# Create new main.py
cat > main.py << 'EOF'
"""ast-grep MCP Server - Entry point and backward compatibility layer.

This module serves two purposes:
1. Entry point for the MCP server
2. Backward compatibility layer for existing imports

After test migration, re-exports can be removed.
"""

# Entry point
from ast_grep_mcp.server.runner import run_mcp_server

# Backward compatibility - Re-export all functions
# TODO: Remove after test migration
from ast_grep_mcp.core.config import *
from ast_grep_mcp.core.cache import *
from ast_grep_mcp.core.logging import *
from ast_grep_mcp.core.sentry import *
from ast_grep_mcp.core.executor import *
from ast_grep_mcp.core.exceptions import *
from ast_grep_mcp.models.config import *
from ast_grep_mcp.models.deduplication import *
from ast_grep_mcp.models.complexity import *
from ast_grep_mcp.models.standards import *
from ast_grep_mcp.utils.templates import *
from ast_grep_mcp.utils.formatters import *
from ast_grep_mcp.utils.text import *
from ast_grep_mcp.utils.validation import *
from ast_grep_mcp.features.search.service import *
from ast_grep_mcp.features.rewrite.service import *
from ast_grep_mcp.features.rewrite.backup import *
from ast_grep_mcp.features.schema.client import *
from ast_grep_mcp.features.deduplication.detector import *
from ast_grep_mcp.features.deduplication.analyzer import *
from ast_grep_mcp.features.deduplication.ranker import *
from ast_grep_mcp.features.deduplication.generator import *
from ast_grep_mcp.features.deduplication.applicator import *
from ast_grep_mcp.features.deduplication.coverage import *
from ast_grep_mcp.features.deduplication.impact import *
from ast_grep_mcp.features.deduplication.recommendations import *
from ast_grep_mcp.features.deduplication.reporting import *
from ast_grep_mcp.features.deduplication.benchmark import *
from ast_grep_mcp.features.complexity.analyzer import *
from ast_grep_mcp.features.complexity.metrics import *
from ast_grep_mcp.features.complexity.storage import *
from ast_grep_mcp.features.quality.smells import *
from ast_grep_mcp.features.quality.rules import *
from ast_grep_mcp.features.quality.validator import *
from ast_grep_mcp.features.quality.enforcer import *

if __name__ == "__main__":
    run_mcp_server()
EOF
```

**Step 2: Test Everything**

```bash
# Test imports still work
python -c "from main import run_ast_grep; print('✓')"
python -c "from main import find_code_impl; print('✓')"
python -c "from main import calculate_deduplication_score; print('✓')"

# Run ALL tests
uv run pytest tests/ -v

# Test MCP server
timeout 5 uv run python main.py || echo "✓ Server works"

# Test type checking
uv run mypy src/ast_grep_mcp/

# Test linting
uv run ruff check .

git add main.py
git commit -m "refactor: create new main.py with backward compatibility"
```

**Phase 10 Complete Checklist:**
- [ ] Server registry created
- [ ] Server runner created
- [ ] main.py refactored
- [ ] All 1,561 tests pass
- [ ] Type checking passes
- [ ] Linting passes
- [ ] MCP server works

## Phase 11: Documentation Update (Day 29)

### Step 1: Update CLAUDE.md

```bash
# Update CLAUDE.md with new structure
# Document import paths
# Update architecture section
# Add module guide
```

### Step 2: Update README.md

```bash
# Update README.md
# Add architecture diagram
# Update import examples
# Add migration notes
```

### Step 3: Create Module Guide

```bash
# Already done:
# - MODULAR-ARCHITECTURE.md
# - MODULE-DEPENDENCIES.md
# - MIGRATION-PLAN.md (this file)
```

**Commit:**
```bash
git add docs/ README.md CLAUDE.md
git commit -m "docs: update documentation for modular architecture"
```

## Phase 12: Final Validation (Day 30)

### Comprehensive Testing

```bash
# 1. Run full test suite
uv run pytest tests/ -v
# Expected: 1,561 tests pass

# 2. Run type checking
uv run mypy src/ast_grep_mcp/
# Expected: 0 errors

# 3. Run linting
uv run ruff check .
# Expected: No errors

# 4. Test MCP server startup
timeout 10 uv run python main.py
# Expected: Starts without errors

# 5. Test with MCP client
# Manually test a few tools in Claude Code

# 6. Run benchmarks
uv run pytest tests/integration/test_benchmark.py -v
# Expected: No performance regression

# 7. Check import structure
python -c "
import ast_grep_mcp
print('Package version:', ast_grep_mcp.__version__ if hasattr(ast_grep_mcp, '__version__') else 'dev')
"

# 8. Verify all 27 tools
python -c "
from mcp.server.fastmcp import FastMCP
from ast_grep_mcp.server.registry import register_all_tools

mcp = FastMCP('ast-grep')
register_all_tools(mcp)
assert len(mcp.tools) == 27
print('✓ All 27 tools registered')
"
```

### Pre-Merge Checklist

- [ ] All 1,561 tests pass
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] MCP server starts successfully
- [ ] All 27 tools registered correctly
- [ ] Manual testing completed
- [ ] No performance regression (<5%)
- [ ] Documentation updated
- [ ] CLAUDE.md updated
- [ ] README.md updated
- [ ] Migration docs complete
- [ ] Team review completed
- [ ] CI/CD passes

### Create Pull Request

```bash
# Push feature branch
git push origin refactor/modular-architecture

# Create PR with template
gh pr create \
  --title "refactor: migrate to modular architecture" \
  --body "$(cat docs/PR-TEMPLATE.md)" \
  --base main \
  --head refactor/modular-architecture
```

**PR Description:**

```markdown
# Refactor: Modular Architecture

## Summary
Refactor main.py (19,477 lines) into modular package structure (44 files, ~450 lines average).

## Changes
- Extract core infrastructure (6 files)
- Extract data models (4 files)
- Extract utilities (4 files)
- Extract search feature (3 files)
- Extract rewrite feature (3 files)
- Extract schema feature (2 files)
- Extract deduplication feature (11 files)
- Extract complexity feature (4 files)
- Extract quality feature (5 files)
- Create server layer (2 files)
- Refactor main.py to entry point (100 lines)

## Testing
- ✅ All 1,561 tests pass
- ✅ Type checking passes
- ✅ Linting passes
- ✅ MCP server works
- ✅ All 27 tools registered
- ✅ No performance regression
- ✅ Manual testing completed

## Documentation
- ✅ MODULAR-ARCHITECTURE.md created
- ✅ MODULE-DEPENDENCIES.md created
- ✅ MIGRATION-PLAN.md created
- ✅ CLAUDE.md updated
- ✅ README.md updated

## Backward Compatibility
- ✅ All existing imports still work
- ✅ main.py re-exports everything
- ✅ Tests unchanged (use existing imports)
- ✅ No breaking changes

## Next Steps
1. Merge to main
2. Deploy to production
3. Monitor for issues
4. Plan test migration (optional Phase 13)

## Breaking Changes
None - full backward compatibility maintained.
```

### Merge to Main

```bash
# After PR approval
git checkout main
git merge refactor/modular-architecture
git push origin main

# Tag release
git tag -a v2.0.0 -m "Modular architecture refactor"
git push origin v2.0.0
```

## Rollback Procedures

### If Tests Fail During Migration

```bash
# Rollback current phase
git reset --hard HEAD~1

# Or rollback entire migration
git checkout main
git reset --hard backup/pre-refactor
git push origin main --force
```

### If Production Issues After Merge

```bash
# Revert merge commit
git revert -m 1 <merge-commit-hash>
git push origin main

# Or hard reset to pre-merge
git reset --hard <commit-before-merge>
git push origin main --force
```

### If Import Errors

```bash
# Quick fix: Add missing re-export to main.py
# Example:
echo "from ast_grep_mcp.features.search.service import missing_function" >> main.py

# Or: Update test imports temporarily
# Find and replace in tests:
# from main import function → from ast_grep_mcp.features.X.service import function
```

## Optional Phase 13: Test Migration (Week 7)

**Only after successful production deployment.**

### Day 31-35: Update Test Imports

```bash
# Create test migration script
cat > scripts/migrate_test_imports.py << 'EOF'
#!/usr/bin/env python3
"""Migrate test imports from main.py to package imports."""

import re
from pathlib import Path

def migrate_test_file(file_path: Path) -> None:
    content = file_path.read_text()

    # Replace: from main import X
    # With: from ast_grep_mcp.features.Y.service import X
    replacements = {
        "from main import run_ast_grep": "from ast_grep_mcp.core.executor import run_ast_grep",
        "from main import find_code_impl": "from ast_grep_mcp.features.search.service import find_code_impl",
        # ... add all replacements
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    file_path.write_text(content)

# Process all test files
for test_file in Path("tests").rglob("test_*.py"):
    print(f"Migrating {test_file}")
    migrate_test_file(test_file)
EOF

chmod +x scripts/migrate_test_imports.py

# Run migration
python scripts/migrate_test_imports.py

# Test
uv run pytest tests/ -v

git add tests/
git commit -m "test: migrate imports to package structure"
```

### Remove Backward Compatibility

```bash
# Remove re-exports from main.py
cat > main.py << 'EOF'
"""ast-grep MCP Server - Entry point."""

from ast_grep_mcp.server.runner import run_mcp_server

if __name__ == "__main__":
    run_mcp_server()
EOF

# Test
uv run pytest tests/ -v

git add main.py
git commit -m "refactor: remove backward compatibility layer"
git push origin main
```

## Success Metrics

### Code Quality Metrics

**Before:**
- File size: 19,477 lines
- Largest function: 4,354 lines (register_mcp_tools)
- Average function: unknown (hard to measure)
- Files: 1
- Imports: unclear

**After:**
- Max file size: ~1,800 lines
- Average file size: ~450 lines
- Total files: 44 files
- Average function: 20-50 lines
- Clear module boundaries

### Developer Productivity

**Before:**
- Find function: 2-5 minutes
- Add feature: requires reading 19K lines
- Merge conflicts: high probability
- IDE performance: slow

**After:**
- Find function: <30 seconds (navigate to feature)
- Add feature: 2-3x faster (clear structure)
- Merge conflicts: low probability (different features)
- IDE performance: fast

### Maintainability

**Before:**
- Cognitive load: extremely high
- Onboarding: overwhelming
- Testing: difficult (large file)
- Refactoring: risky

**After:**
- Cognitive load: manageable (focused modules)
- Onboarding: gradual (start with one feature)
- Testing: easy (isolated components)
- Refactoring: safe (clear boundaries)

## Conclusion

This migration plan provides a detailed, step-by-step approach to refactoring the ast-grep-mcp codebase from a single 19,477-line file into a maintainable modular architecture with 44 files organized into clear layers and features.

**Key Success Factors:**
1. Incremental approach (12 phases)
2. Test after every phase
3. Maintain backward compatibility
4. Clear rollback procedures
5. Comprehensive documentation

**Timeline Summary:**
- Weeks 1-2: Core, models, utils (Days 1-9)
- Week 2-3: Search, rewrite, schema (Days 10-14)
- Weeks 3-4: Deduplication (Days 15-21)
- Week 4-5: Complexity, quality, server (Days 22-28)
- Week 5: Documentation, validation (Days 29-30)
- Optional Week 6-7: Test migration (Days 31-35)

**Total: 4-6 weeks for complete migration with full backward compatibility.**

---

**Ready to begin? Start with Phase 0 on Day 1.**
