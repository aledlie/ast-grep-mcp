# Module Dependencies for ast-grep-mcp

**Date:** 2025-11-24
**Status:** Design Phase

## Overview

This document provides detailed dependency relationships between modules in the refactored architecture. Understanding these dependencies is crucial for maintaining the codebase and avoiding circular dependencies.

## Dependency Rules

### Layer Hierarchy

```
┌────────────────────────────────────────────┐
│           Application Layer                │
│  ┌──────────────────────────────────────┐ │
│  │         main.py (entry point)        │ │
│  │       (re-exports for backward       │ │
│  │          compatibility)              │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│            Server Layer                    │
│  ┌──────────────────────────────────────┐ │
│  │     server/registry.py               │ │
│  │     server/runner.py                 │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│          Features Layer                    │
│  ┌─────────┬─────────┬──────────────┐    │
│  │ search  │ rewrite │ deduplication│    │
│  ├─────────┼─────────┼──────────────┤    │
│  │ schema  │ complex │   quality    │    │
│  └─────────┴─────────┴──────────────┘    │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│           Utils Layer                      │
│  ┌────────────┬────────────┬───────────┐  │
│  │ templates  │ formatters │    text   │  │
│  └────────────┴────────────┴───────────┘  │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│          Models Layer                      │
│  ┌────────┬──────────────┬──────────┐    │
│  │ config │ deduplication│complexity│    │
│  └────────┴──────────────┴──────────┘    │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│           Core Layer                       │
│  ┌────────┬───────┬─────────┬──────────┐  │
│  │ config │ cache │ logging │ executor │  │
│  └────────┴───────┴─────────┴──────────┘  │
└────────────────────────────────────────────┘
```

**Dependency Direction:** Top → Bottom only (no upward dependencies)

## Core Layer Dependencies

### `core/exceptions.py`
**Dependencies:** None (base layer)
```python
# No internal imports
# Only stdlib imports
```

### `core/logging.py`
**Dependencies:**
```python
import structlog              # External
# No internal dependencies
```

### `core/sentry.py`
**Dependencies:**
```python
import sentry_sdk             # External
from ast_grep_mcp.core.logging import get_logger
```

### `core/config.py`
**Dependencies:**
```python
import argparse               # Stdlib
from pydantic import BaseModel
from ast_grep_mcp.core.exceptions import ConfigurationError
```

### `core/cache.py`
**Dependencies:**
```python
import threading              # Stdlib
from collections import OrderedDict
from ast_grep_mcp.core.logging import get_logger
```

### `core/executor.py`
**Dependencies:**
```python
import subprocess             # Stdlib
from ast_grep_mcp.core.config import CONFIG_PATH, AstGrepConfig
from ast_grep_mcp.core.cache import get_query_cache
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.core.exceptions import (
    AstGrepNotFoundError,
    InvalidYAMLError,
    AstGrepExecutionError,
)
```

**Dependency Graph:**
```
executor
  ↓
  ├── config (CONFIG_PATH, AstGrepConfig)
  ├── cache (get_query_cache)
  ├── logging (get_logger)
  └── exceptions (AstGrepNotFoundError, etc.)
```

## Models Layer Dependencies

### `models/config.py`
**Dependencies:**
```python
from pydantic import BaseModel, ConfigDict, Field
# No internal dependencies
```

### `models/deduplication.py`
**Dependencies:**
```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
# No internal dependencies
```

### `models/complexity.py`
**Dependencies:**
```python
from dataclasses import dataclass
from typing import Dict, List, Optional
# No internal dependencies
```

### `models/standards.py`
**Dependencies:**
```python
from pydantic import BaseModel, Field
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from ast_grep_mcp.core.exceptions import (
    RuleValidationError,
    RuleStorageError,
)
```

**Note:** Models should have minimal dependencies. If a model needs core functionality, consider if it should be a service instead.

## Utils Layer Dependencies

### `utils/templates.py`
**Dependencies:**
```python
from typing import Optional, List
# No internal dependencies (pure templates)
```

### `utils/formatters.py`
**Dependencies:**
```python
import subprocess             # Stdlib
from typing import List, Dict, Any
from ast_grep_mcp.core.logging import get_logger
```

### `utils/text.py`
**Dependencies:**
```python
import difflib                # Stdlib
from typing import List, Dict
# No internal dependencies
```

### `utils/validation.py`
**Dependencies:**
```python
import yaml                   # External
from pathlib import Path
from ast_grep_mcp.core.exceptions import InvalidYAMLError, ConfigurationError
from ast_grep_mcp.models.config import AstGrepConfig
```

## Features Layer Dependencies

### Search Feature

**`features/search/service.py`**
```python
from ast_grep_mcp.core.executor import run_ast_grep, get_supported_languages
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.core.cache import get_query_cache
from ast_grep_mcp.core.config import CONFIG_PATH
from ast_grep_mcp.utils.formatters import format_matches_as_text
```

**`features/search/syntax.py`**
```python
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.core.logging import get_logger
```

**`features/search/tools.py`**
```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from ast_grep_mcp.features.search.service import (
    dump_syntax_tree_impl,
    find_code_impl,
    # ...
)
```

**Dependency Graph:**
```
search/tools
  ↓
search/service
  ↓
  ├── core/executor
  ├── core/logging
  ├── core/cache
  ├── core/config
  └── utils/formatters
```

### Rewrite Feature

**`features/rewrite/backup.py`**
```python
import shutil                 # Stdlib
from pathlib import Path
from datetime import datetime
from ast_grep_mcp.core.logging import get_logger
```

**`features/rewrite/service.py`**
```python
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.core.config import CONFIG_PATH
from ast_grep_mcp.features.rewrite.backup import (
    create_backup,
    restore_backup,
    list_available_backups,
)
from ast_grep_mcp.utils.validation import validate_yaml_rule
```

**`features/rewrite/tools.py`**
```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from ast_grep_mcp.features.rewrite.service import (
    rewrite_code_impl,
    list_backups_impl,
    rollback_rewrite_impl,
)
```

**Dependency Graph:**
```
rewrite/tools
  ↓
rewrite/service
  ↓
  ├── core/executor
  ├── core/logging
  ├── core/config
  ├── rewrite/backup
  └── utils/validation
      ↓
      ├── core/exceptions
      └── models/config
```

### Schema Feature

**`features/schema/client.py`**
```python
import httpx                  # External
from typing import Dict, List, Optional, Any
from ast_grep_mcp.core.logging import get_logger
```

**`features/schema/tools.py`**
```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from ast_grep_mcp.features.schema.client import (
    SchemaOrgClient,
    get_schema_org_client,
)
```

**Dependency Graph:**
```
schema/tools
  ↓
schema/client
  ↓
  └── core/logging
```

**Note:** Schema feature is highly independent - good candidate for extraction.

### Deduplication Feature

**`features/deduplication/detector.py`**
```python
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.core.config import CONFIG_PATH
from ast_grep_mcp.models.deduplication import (
    AlignmentSegment,
    AlignmentResult,
    DiffTreeNode,
    DiffTree,
)
from ast_grep_mcp.utils.text import normalize_code, calculate_similarity
from ast_grep_mcp.utils.formatters import format_matches_as_text
```

**`features/deduplication/analyzer.py`**
```python
import difflib                # Stdlib
from ast_grep_mcp.models.deduplication import (
    VariationCategory,
    VariationSeverity,
    AlignmentSegment,
    AlignmentResult,
    DiffTree,
)
from ast_grep_mcp.utils.text import normalize_code
```

**`features/deduplication/ranker.py`**
```python
from ast_grep_mcp.models.deduplication import EnhancedDuplicationCandidate
from ast_grep_mcp.features.deduplication.coverage import get_test_coverage_for_files
from ast_grep_mcp.features.deduplication.impact import analyze_deduplication_impact
```

**`features/deduplication/generator.py`**
```python
from ast_grep_mcp.models.deduplication import (
    FunctionTemplate,
    ParameterType,
    ParameterInfo,
)
from ast_grep_mcp.utils.templates import (
    format_python_class,
    format_java_method,
    format_typescript_function,
)
from ast_grep_mcp.features.deduplication.analyzer import classify_variations
```

**`features/deduplication/applicator.py`**
```python
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.rewrite.backup import create_backup
from ast_grep_mcp.features.deduplication.generator import generate_function_code
from ast_grep_mcp.models.deduplication import FileDiff, DiffPreview
```

**`features/deduplication/coverage.py`**
```python
import os                     # Stdlib
from pathlib import Path
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.core.logging import get_logger
```

**`features/deduplication/impact.py`**
```python
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.features.deduplication.coverage import has_test_coverage
```

**`features/deduplication/recommendations.py`**
```python
from ast_grep_mcp.models.deduplication import EnhancedDuplicationCandidate
from ast_grep_mcp.features.deduplication.ranker import calculate_deduplication_score
from ast_grep_mcp.features.deduplication.generator import generate_refactoring_strategies
```

**`features/deduplication/reporting.py`**
```python
import difflib                # Stdlib
from ast_grep_mcp.models.deduplication import EnhancedDuplicationCandidate
from ast_grep_mcp.utils.formatters import format_diff_with_colors
```

**`features/deduplication/benchmark.py`**
```python
import time                   # Stdlib
from ast_grep_mcp.features.deduplication.detector import find_duplication_impl
from ast_grep_mcp.core.logging import get_logger
```

**`features/deduplication/tools.py`**
```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from ast_grep_mcp.features.deduplication.detector import find_duplication_impl
from ast_grep_mcp.features.deduplication.ranker import analyze_deduplication_candidates_impl
from ast_grep_mcp.features.deduplication.applicator import apply_deduplication_impl
from ast_grep_mcp.features.deduplication.benchmark import benchmark_deduplication_impl
```

**Dependency Graph:**
```
deduplication/tools
  ↓
  ├── deduplication/detector
  │   ↓
  │   ├── core/executor
  │   ├── core/logging
  │   ├── models/deduplication
  │   ├── utils/text
  │   └── utils/formatters
  │
  ├── deduplication/ranker
  │   ↓
  │   ├── models/deduplication
  │   ├── deduplication/coverage
  │   └── deduplication/impact
  │
  ├── deduplication/applicator
  │   ↓
  │   ├── core/executor
  │   ├── rewrite/backup
  │   ├── deduplication/generator
  │   └── models/deduplication
  │
  └── deduplication/benchmark
      ↓
      ├── deduplication/detector
      └── core/logging
```

**Note:** Deduplication has internal sub-feature dependencies, which is acceptable since they're all within the same feature.

### Complexity Feature

**`features/complexity/metrics.py`**
```python
import re                     # Stdlib
from ast_grep_mcp.models.complexity import ComplexityMetrics
```

**`features/complexity/storage.py`**
```python
import sqlite3                # Stdlib
from pathlib import Path
from ast_grep_mcp.models.complexity import (
    ComplexityMetrics,
    FunctionComplexity,
)
from ast_grep_mcp.core.logging import get_logger
```

**`features/complexity/analyzer.py`**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.complexity import (
    ComplexityMetrics,
    FunctionComplexity,
    ComplexityThresholds,
)
from ast_grep_mcp.features.complexity.metrics import (
    calculate_cyclomatic_complexity,
    calculate_cognitive_complexity,
    calculate_nesting_depth,
)
from ast_grep_mcp.features.complexity.storage import ComplexityStorage
```

**`features/complexity/tools.py`**
```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from ast_grep_mcp.features.complexity.analyzer import analyze_complexity_impl
```

**Dependency Graph:**
```
complexity/tools
  ↓
complexity/analyzer
  ↓
  ├── core/executor
  ├── core/logging
  ├── models/complexity
  ├── complexity/metrics
  └── complexity/storage
      ↓
      ├── models/complexity
      └── core/logging
```

### Quality Feature

**`features/quality/smells.py`**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.standards import RuleViolation
```

**`features/quality/rules.py`**
```python
import json                   # Stdlib
from pathlib import Path
from ast_grep_mcp.models.standards import (
    LintingRule,
    RuleTemplate,
    RuleSet,
)
from ast_grep_mcp.core.logging import get_logger
```

**`features/quality/validator.py`**
```python
import yaml                   # External
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.models.standards import (
    RuleValidationResult,
    RuleValidationError,
)
from ast_grep_mcp.core.logging import get_logger
```

**`features/quality/enforcer.py`**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from ast_grep_mcp.core.executor import run_ast_grep
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.standards import (
    RuleSet,
    RuleViolation,
    EnforcementResult,
    RuleExecutionContext,
)
from ast_grep_mcp.features.quality.rules import load_rules
```

**`features/quality/tools.py`**
```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from ast_grep_mcp.features.quality.smells import detect_code_smells_impl
from ast_grep_mcp.features.quality.validator import validate_linting_rules_impl
from ast_grep_mcp.features.quality.enforcer import enforce_standards_impl
```

**Dependency Graph:**
```
quality/tools
  ↓
  ├── quality/smells
  │   ↓
  │   ├── core/executor
  │   ├── core/logging
  │   └── models/standards
  │
  ├── quality/validator
  │   ↓
  │   ├── core/executor
  │   ├── core/logging
  │   └── models/standards
  │
  └── quality/enforcer
      ↓
      ├── core/executor
      ├── core/logging
      ├── models/standards
      └── quality/rules
          ↓
          ├── models/standards
          └── core/logging
```

## Server Layer Dependencies

### `server/registry.py`
```python
from mcp.server.fastmcp import FastMCP
from ast_grep_mcp.features.search.tools import register_search_tools
from ast_grep_mcp.features.rewrite.tools import register_rewrite_tools
from ast_grep_mcp.features.deduplication.tools import register_deduplication_tools
from ast_grep_mcp.features.complexity.tools import register_complexity_tools
from ast_grep_mcp.features.quality.tools import register_quality_tools
from ast_grep_mcp.features.schema.tools import register_schema_tools
```

### `server/runner.py`
```python
from mcp.server.fastmcp import FastMCP
from ast_grep_mcp.core.config import parse_args_and_get_config
from ast_grep_mcp.core.sentry import init_sentry
from ast_grep_mcp.server.registry import register_all_tools
```

**Dependency Graph:**
```
server/runner
  ↓
  ├── core/config
  ├── core/sentry
  └── server/registry
      ↓
      ├── features/search/tools
      ├── features/rewrite/tools
      ├── features/deduplication/tools
      ├── features/complexity/tools
      ├── features/quality/tools
      └── features/schema/tools
```

## Application Layer Dependencies

### `main.py` (Entry Point)
```python
# Re-exports for backward compatibility
from ast_grep_mcp.server.runner import run_mcp_server
from ast_grep_mcp.core.config import parse_args_and_get_config
from ast_grep_mcp.core.sentry import init_sentry

# Re-export all functions for backward compatibility
from ast_grep_mcp.features.search.service import *
from ast_grep_mcp.features.rewrite.service import *
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
from ast_grep_mcp.features.schema.client import *
from ast_grep_mcp.core.executor import *
from ast_grep_mcp.core.cache import *
from ast_grep_mcp.core.logging import *
from ast_grep_mcp.models.config import *
from ast_grep_mcp.models.deduplication import *
from ast_grep_mcp.models.complexity import *
from ast_grep_mcp.models.standards import *
from ast_grep_mcp.utils.templates import *
from ast_grep_mcp.utils.formatters import *
from ast_grep_mcp.utils.text import *

if __name__ == "__main__":
    run_mcp_server()
```

**Note:** After test migration, remove star imports and only re-export what's needed.

## Circular Dependency Prevention

### Rules to Prevent Cycles

1. **No upward dependencies:** Lower layers cannot import from higher layers
2. **No sibling feature imports:** Features cannot import from other features
3. **Shared code goes in utils/core:** If two features need the same code, extract to lower layer
4. **Models are data-only:** Models cannot import from features or utils

### Detecting Circular Dependencies

```bash
# Import cycles will fail at module load time
python -c "import ast_grep_mcp"

# Or use pytest collection
pytest --collect-only

# Or use tools like pydeps
pip install pydeps
pydeps --show-cycles ast_grep_mcp
```

### Example: Avoiding Circular Dependency

**Problem:** Deduplication needs complexity analysis, complexity needs deduplication patterns

**Wrong Approach:**
```python
# features/deduplication/ranker.py
from ast_grep_mcp.features.complexity.analyzer import calculate_complexity  # ❌

# features/complexity/analyzer.py
from ast_grep_mcp.features.deduplication.detector import find_patterns  # ❌
```

**Right Approach:**
```python
# Extract shared code to utils
# utils/code_analysis.py
def analyze_code_structure(code: str) -> Dict[str, Any]:
    """Shared code analysis used by both features"""
    pass

# features/deduplication/ranker.py
from ast_grep_mcp.utils.code_analysis import analyze_code_structure  # ✓

# features/complexity/analyzer.py
from ast_grep_mcp.utils.code_analysis import analyze_code_structure  # ✓
```

## Cross-Cutting Concerns

### Logging

**Used by:** All modules
**Pattern:** Import at module level, use in functions
```python
from ast_grep_mcp.core.logging import get_logger

logger = get_logger(__name__)

def some_function():
    logger.info("event", key="value")
```

### Caching

**Used by:** Search features only
**Pattern:** Get singleton instance
```python
from ast_grep_mcp.core.cache import get_query_cache

def cached_search(...):
    cache = get_query_cache()
    if cache:
        result = cache.get(key)
```

### Sentry

**Used by:** All features (error tracking)
**Pattern:** Import at usage site
```python
import sentry_sdk

try:
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e, extras={...})
    raise
```

### Configuration

**Used by:** All features needing config
**Pattern:** Import global constants
```python
from ast_grep_mcp.core.config import CONFIG_PATH, CACHE_ENABLED
```

## Import Best Practices

### DO: Use Absolute Imports
```python
from ast_grep_mcp.core.executor import run_ast_grep  # ✓
```

### DON'T: Use Relative Imports for Cross-Module
```python
from ...core.executor import run_ast_grep  # ❌
```

### DO: Import Specific Items
```python
from ast_grep_mcp.models.complexity import ComplexityMetrics  # ✓
```

### DON'T: Import Everything (except in main.py)
```python
from ast_grep_mcp.models.complexity import *  # ❌ (except main.py)
```

### DO: Import at Top of File
```python
from ast_grep_mcp.core.logging import get_logger

def function():
    logger = get_logger(__name__)
```

### DON'T: Import Inside Functions (except lazy imports)
```python
def function():
    from ast_grep_mcp.core.logging import get_logger  # ❌ (usually)
```

### Exception: Lazy Imports for Circular Dependencies
```python
def function_with_lazy_import():
    # Only if absolutely necessary
    from ast_grep_mcp.features.other import helper
    return helper()
```

## Dependency Validation

### Manual Validation Checklist

Before merging a module:

- [ ] No circular dependencies
- [ ] Only imports from lower layers
- [ ] No feature-to-feature imports
- [ ] Models have no business logic
- [ ] Utils have no state
- [ ] Core has minimal dependencies
- [ ] Type hints are complete
- [ ] Tests pass

### Automated Validation

```bash
# Check import order and cycles
ruff check --select I,TID ast_grep_mcp/

# Check type hints
mypy ast_grep_mcp/

# Check for circular imports
pytest --collect-only
```

## Module Integration Points

### Where Features Interact

**Search ↔ Rewrite:** Both use `core/executor`
**Deduplication ↔ Rewrite:** Deduplication uses `rewrite/backup`
**Deduplication ↔ Complexity:** Both use similar AST patterns (via utils)
**Quality ↔ Complexity:** Quality uses complexity metrics (via models)

### Integration Pattern

Features interact through:
1. **Shared utilities** (utils layer)
2. **Shared models** (models layer)
3. **Shared infrastructure** (core layer)

Features **never** interact directly with each other's business logic.

## Summary

**Key Takeaways:**

1. **Strict layer hierarchy:** Features → Utils → Models → Core
2. **No circular dependencies:** Enforced by layer rules
3. **Feature isolation:** Features don't import from other features
4. **Shared code in lower layers:** utils/ or core/
5. **Cross-cutting concerns:** Logging, caching, Sentry, config
6. **Import best practices:** Absolute imports, specific items, top-level
7. **Validation:** Manual checklist + automated tools

**Dependency Count by Layer:**

- Core: 0 internal dependencies (only external)
- Models: 1-2 internal dependencies (core/exceptions)
- Utils: 2-3 internal dependencies (core, models)
- Features: 5-10 internal dependencies (core, models, utils, same-feature)
- Server: 6+ internal dependencies (all feature tools)

**Total Internal Dependencies:** ~30 dependency relationships across 44 files

---

**Next Steps:**
1. Review dependency rules with team
2. Validate no circular dependencies during extraction
3. Update this document as architecture evolves
4. Add automated dependency checking to CI/CD
