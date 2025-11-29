# Refactoring Action Plan - ast-grep-mcp
**Priority:** Critical Issues First
**Timeline:** 6 weeks
**Risk Mitigation:** Test-driven refactoring with backup rollback

## Critical Issue #1: applicator.py - apply_deduplication()

### Current State Analysis
**Location:** `src/ast_grep_mcp/features/deduplication/applicator.py:29`
**Metrics:**
- Lines: 309
- Cyclomatic Complexity: 71
- Cognitive Complexity: 219
- Nesting Depth: 8

**Responsibilities (Too Many!):**
1. Input validation
2. Backup management
3. Code generation
4. Syntax validation
5. File modification
6. Post-validation
7. Rollback on failure
8. Result formatting

### Refactoring Strategy

#### Step 1: Extract Validation Layer
```python
# NEW: applicator_validator.py
from typing import Dict, Any, List
from ..models.deduplication import RefactoringPlan, ValidationResult

class RefactoringPlanValidator:
    """Validates refactoring plans before application."""

    def validate_plan(
        self,
        refactoring_plan: Dict[str, Any],
        group_id: int,
        project_folder: str
    ) -> ValidationResult:
        """Validate refactoring plan completeness and correctness."""
        errors = []

        # Extract validation logic from applicator.py
        errors.extend(self._validate_required_fields(refactoring_plan))
        errors.extend(self._validate_files_exist(refactoring_plan, project_folder))
        errors.extend(self._validate_code_syntax(refactoring_plan))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )

    def _validate_required_fields(self, plan: Dict) -> List[str]:
        """Check plan has all required fields."""
        required = ['generated_code', 'files_affected', 'strategy', 'language']
        return [
            f"Missing required field: {field}"
            for field in required
            if field not in plan
        ]

    def _validate_files_exist(self, plan: Dict, project_folder: str) -> List[str]:
        """Verify all affected files exist."""
        errors = []
        for file_path in plan.get('files_affected', []):
            full_path = Path(project_folder) / file_path
            if not full_path.exists():
                errors.append(f"File not found: {file_path}")
        return errors

    def _validate_code_syntax(self, plan: Dict) -> List[str]:
        """Pre-validate generated code syntax."""
        # Use existing syntax_validator.py
        from ..utils.syntax_validator import validate_code_syntax

        language = plan.get('language')
        code = plan.get('generated_code', '')

        result = validate_code_syntax(code, language)
        return [] if result.is_valid else result.errors
```

#### Step 2: Extract Backup Management
```python
# NEW: applicator_backup.py
from pathlib import Path
from typing import Optional
from ...features.rewrite.backup import BackupManager

class DeduplicationBackupManager:
    """Manages backups for deduplication operations."""

    def __init__(self, project_folder: str):
        self.project_folder = project_folder
        self.backup_manager = BackupManager()

    def create_backup(
        self,
        files: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create backup of files before modification."""
        backup_id = self.backup_manager.create_backup(
            self.project_folder,
            files,
            backup_type='deduplication',
            metadata=metadata or {}
        )
        return backup_id

    def rollback(self, backup_id: str) -> bool:
        """Rollback changes using backup."""
        return self.backup_manager.rollback(
            self.project_folder,
            backup_id
        )

    def cleanup_old_backups(self, days: int = 30) -> int:
        """Remove backups older than specified days."""
        return self.backup_manager.cleanup_old_backups(
            self.project_folder,
            days
        )
```

#### Step 3: Extract Code Application Logic
```python
# NEW: applicator_executor.py
from typing import Dict, Any, List
from pathlib import Path

class RefactoringExecutor:
    """Executes the actual code modifications."""

    def apply_changes(
        self,
        refactoring_plan: Dict[str, Any],
        project_folder: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Apply refactoring changes to files."""
        if dry_run:
            return self._preview_changes(refactoring_plan, project_folder)

        return self._apply_changes_to_files(refactoring_plan, project_folder)

    def _preview_changes(
        self,
        plan: Dict[str, Any],
        project_folder: str
    ) -> Dict[str, Any]:
        """Generate diff preview without modifying files."""
        diffs = []

        for file_path, modifications in self._get_file_modifications(plan):
            full_path = Path(project_folder) / file_path
            original_content = full_path.read_text()
            modified_content = self._apply_modifications(
                original_content,
                modifications
            )

            diff = self._generate_diff(
                original_content,
                modified_content,
                file_path
            )
            diffs.append(diff)

        return {
            'status': 'preview',
            'diffs': diffs,
            'files_affected': len(diffs)
        }

    def _apply_changes_to_files(
        self,
        plan: Dict[str, Any],
        project_folder: str
    ) -> Dict[str, Any]:
        """Actually modify the files."""
        modified_files = []
        errors = []

        for file_path, modifications in self._get_file_modifications(plan):
            try:
                self._modify_file(project_folder, file_path, modifications)
                modified_files.append(file_path)
            except Exception as e:
                errors.append({
                    'file': file_path,
                    'error': str(e)
                })

        return {
            'status': 'failed' if errors else 'success',
            'files_modified': modified_files,
            'errors': errors
        }
```

#### Step 4: Refactored Main Applicator (Target: <100 lines)
```python
# REFACTORED: applicator.py
from typing import Dict, Any, Optional
from .applicator_validator import RefactoringPlanValidator
from .applicator_backup import DeduplicationBackupManager
from .applicator_executor import RefactoringExecutor
from .applicator_post_validator import PostApplicationValidator

class DeduplicationApplicator:
    """Applies deduplication refactorings with validation and rollback."""

    def __init__(self):
        self.validator = RefactoringPlanValidator()
        self.post_validator = PostApplicationValidator()

    def apply_deduplication(
        self,
        project_folder: str,
        group_id: int,
        refactoring_plan: Dict[str, Any],
        dry_run: bool = True,
        backup: bool = True,
        extract_to_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply deduplication refactoring with comprehensive validation.

        This is now a clean coordinator function with clear responsibilities.
        """
        # Step 1: Validate plan
        validation = self.validator.validate_plan(
            refactoring_plan,
            group_id,
            project_folder
        )
        if not validation.is_valid:
            return {
                'status': 'failed',
                'validation': {'pre': validation},
                'errors': validation.errors
            }

        # Step 2: Preview mode
        executor = RefactoringExecutor()
        if dry_run:
            return executor.apply_changes(
                refactoring_plan,
                project_folder,
                dry_run=True
            )

        # Step 3: Create backup
        backup_id = None
        if backup:
            backup_mgr = DeduplicationBackupManager(project_folder)
            backup_id = backup_mgr.create_backup(
                files=refactoring_plan['files_affected'],
                metadata={'group_id': group_id}
            )

        # Step 4: Apply changes with automatic rollback
        try:
            result = executor.apply_changes(
                refactoring_plan,
                project_folder,
                dry_run=False
            )

            # Step 5: Post-validation
            post_validation = self.post_validator.validate_after_changes(
                project_folder,
                result['files_modified'],
                refactoring_plan['language']
            )

            if not post_validation.is_valid:
                self._rollback_and_report(backup_mgr, backup_id, post_validation)
                return self._create_rollback_response(post_validation)

            return self._create_success_response(result, backup_id, post_validation)

        except Exception as e:
            if backup and backup_id:
                backup_mgr.rollback(backup_id)
            raise

    def _rollback_and_report(self, backup_mgr, backup_id, validation):
        """Rollback changes and log the issue."""
        backup_mgr.rollback(backup_id)
        logger.error("Post-validation failed, rolled back", errors=validation.errors)

    def _create_success_response(self, result, backup_id, validation):
        """Format successful application response."""
        return {
            'status': 'success',
            'backup_id': backup_id,
            'files_modified': result['files_modified'],
            'validation': {
                'pre': {'is_valid': True},
                'post': validation
            }
        }

    def _create_rollback_response(self, validation):
        """Format rolled-back response."""
        return {
            'status': 'rolled_back',
            'validation': {'post': validation},
            'errors': validation.errors
        }
```

### Testing Strategy
```python
# tests/unit/test_refactored_applicator.py
import pytest
from ast_grep_mcp.features.deduplication.applicator import DeduplicationApplicator
from ast_grep_mcp.features.deduplication.applicator_validator import RefactoringPlanValidator

class TestRefactoredApplicator:
    """Tests for refactored applicator with isolated components."""

    def test_validator_rejects_missing_fields(self):
        """Validator should catch incomplete plans early."""
        validator = RefactoringPlanValidator()
        result = validator.validate_plan(
            refactoring_plan={},  # Missing all fields
            group_id=1,
            project_folder='/tmp'
        )
        assert not result.is_valid
        assert 'Missing required field' in str(result.errors)

    def test_dry_run_returns_preview(self):
        """Dry run mode should return diffs without modifying files."""
        applicator = DeduplicationApplicator()
        result = applicator.apply_deduplication(
            project_folder='/tmp/test-project',
            group_id=1,
            refactoring_plan=create_valid_plan(),
            dry_run=True
        )
        assert result['status'] == 'preview'
        assert 'diffs' in result

    def test_rollback_on_post_validation_failure(self, tmp_path):
        """Should automatically rollback if post-validation fails."""
        # Setup test files
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        applicator = DeduplicationApplicator()
        result = applicator.apply_deduplication(
            project_folder=str(tmp_path),
            group_id=1,
            refactoring_plan=create_plan_with_syntax_error(),
            dry_run=False,
            backup=True
        )

        assert result['status'] == 'rolled_back'
        # Original file should be restored
        assert test_file.read_text() == "def foo(): pass"
```

### Migration Checklist
- [ ] Create new validator module
- [ ] Create backup manager module
- [ ] Create executor module
- [ ] Create post-validator module
- [ ] Write unit tests for each new module (aim for 100% coverage)
- [ ] Refactor main applicator to use new modules
- [ ] Run full test suite (1,586 tests should all pass)
- [ ] Verify complexity metrics: cyclomatic <15, cognitive <20, lines <100
- [ ] Update documentation
- [ ] Create migration notes for other contributors

---

## Critical Issue #2: tools.py - analyze_complexity_tool()

### Current State
**Location:** `src/ast_grep_mcp/features/complexity/tools.py:29`
**Metrics:**
- Lines: 304
- Cyclomatic Complexity: 55
- Cognitive Complexity: 117

### Refactoring Strategy

#### Extract File Discovery
```python
# NEW: complexity_file_finder.py
from typing import List, Set
from pathlib import Path
import glob

class ComplexityFileFinder:
    """Finds files to analyze based on patterns and language."""

    def __init__(self, project_folder: str, language: str):
        self.project_folder = Path(project_folder)
        self.language = language
        self.extensions = self._get_language_extensions()

    def find_files(
        self,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> List[Path]:
        """Find all files matching criteria."""
        all_files = self._find_matching_files(include_patterns)
        filtered_files = self._filter_excluded(all_files, exclude_patterns)
        return sorted(filtered_files)

    def _get_language_extensions(self) -> List[str]:
        """Get file extensions for language."""
        extensions_map = {
            "python": [".py"],
            "typescript": [".ts", ".tsx"],
            "javascript": [".js", ".jsx"],
            "java": [".java"]
        }
        return extensions_map.get(self.language.lower(), [".py"])

    def _find_matching_files(self, patterns: List[str]) -> Set[Path]:
        """Find files matching include patterns."""
        all_files = set()
        for pattern in patterns:
            for ext in self.extensions:
                glob_pattern = str(self.project_folder / pattern)
                if not glob_pattern.endswith(ext):
                    if glob_pattern.endswith("*"):
                        glob_pattern = glob_pattern[:-1] + f"*{ext}"
                    else:
                        glob_pattern = f"{glob_pattern}/**/*{ext}"

                for file_path in glob.glob(glob_pattern, recursive=True):
                    all_files.add(Path(file_path))
        return all_files

    def _filter_excluded(
        self,
        files: Set[Path],
        exclude_patterns: List[str]
    ) -> List[Path]:
        """Remove excluded files."""
        filtered = []
        for file_path in files:
            if not self._is_excluded(file_path, exclude_patterns):
                filtered.append(file_path)
        return filtered

    def _is_excluded(self, file_path: Path, patterns: List[str]) -> bool:
        """Check if file matches any exclude pattern."""
        file_str = str(file_path)
        for pattern in patterns:
            pattern_parts = pattern.replace("**", "").replace("*", "").split("/")
            if any(part in file_str for part in pattern_parts if part):
                return True
        return False
```

#### Extract Analysis Orchestration
```python
# NEW: complexity_analyzer.py
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from .file_finder import ComplexityFileFinder
from ..analyzer import analyze_file_complexity

class ComplexityAnalyzer:
    """Orchestrates complexity analysis across multiple files."""

    def __init__(self, max_threads: int = 4):
        self.max_threads = max_threads

    def analyze_project(
        self,
        file_finder: ComplexityFileFinder,
        thresholds: ComplexityThresholds
    ) -> List[FunctionComplexity]:
        """Analyze all files in parallel."""
        files = file_finder.find_files()

        if not files:
            return []

        return self._analyze_files_parallel(files, thresholds)

    def _analyze_files_parallel(
        self,
        files: List[Path],
        thresholds: ComplexityThresholds
    ) -> List[FunctionComplexity]:
        """Analyze files using thread pool."""
        all_functions = []

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {
                executor.submit(
                    analyze_file_complexity,
                    str(file),
                    file_finder.language,
                    thresholds
                ): file
                for file in files
            }

            for future in as_completed(futures):
                try:
                    functions = future.result()
                    all_functions.extend(functions)
                except Exception as e:
                    file = futures[future]
                    logger.warning("File analysis failed", file=str(file), error=str(e))

        return all_functions
```

#### Refactored Main Tool (Target: <80 lines)
```python
# REFACTORED: tools.py - analyze_complexity_tool()
def analyze_complexity_tool(
    project_folder: str,
    language: str,
    include_patterns: List[str] | None = None,
    exclude_patterns: List[str] | None = None,
    cyclomatic_threshold: int = 10,
    cognitive_threshold: int = 15,
    nesting_threshold: int = 4,
    length_threshold: int = 50,
    store_results: bool = True,
    include_trends: bool = False,
    max_threads: int = 4
) -> Dict[str, Any]:
    """Analyze code complexity metrics for functions in a project."""
    # Set defaults
    include_patterns = include_patterns or ["**/*"]
    exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS

    logger = get_logger("tool.analyze_complexity")
    start_time = time.time()

    try:
        # Step 1: Setup
        thresholds = ComplexityThresholds(
            cyclomatic=cyclomatic_threshold,
            cognitive=cognitive_threshold,
            nesting_depth=nesting_threshold,
            lines=length_threshold
        )

        # Step 2: Find files
        file_finder = ComplexityFileFinder(project_folder, language)
        files = file_finder.find_files(include_patterns, exclude_patterns)

        if not files:
            return create_empty_result(time.time() - start_time)

        # Step 3: Analyze
        analyzer = ComplexityAnalyzer(max_threads)
        all_functions = analyzer.analyze_project(files, thresholds)

        # Step 4: Calculate statistics
        stats = ComplexityStatisticsCalculator().calculate(all_functions)

        # Step 5: Store results
        storage_info = None
        if store_results:
            storage_info = store_analysis_results(
                project_folder,
                stats,
                all_functions
            )

        # Step 6: Get trends
        trends = None
        if include_trends:
            trends = get_complexity_trends(project_folder, days=30)

        # Step 7: Format response
        return format_complexity_response(
            stats,
            all_functions,
            thresholds,
            storage_info,
            trends,
            time.time() - start_time
        )

    except Exception as e:
        logger.error("Analysis failed", error=str(e))
        sentry_sdk.capture_exception(e)
        raise
```

---

## Quick Wins (Can Be Done Immediately)

### 1. Replace Print Statements
```bash
# Find all print statements
uv run python -c "
from ast_grep_mcp.features.quality.tools import enforce_standards_tool
result = enforce_standards_tool(
    project_folder='/Users/alyshialedlie/code/ast-grep-mcp',
    language='python',
    rule_set='recommended',
    output_format='json'
)

# Show files with print statements
for file, violations in result['violations_by_file'].items():
    print(f'{file}: {len(violations)} print statements')
"

# Manual fix in config.py (4 instances)
# Replace:
print(f"Config loaded: {config}")

# With:
logger = get_logger(__name__)
logger.info("Config loaded", config_path=config_path)
```

### 2. Extract Common Constants
```python
# NEW: src/ast_grep_mcp/constants.py
"""Shared constants across the codebase."""

class ComplexityDefaults:
    """Default thresholds for complexity analysis."""
    CYCLOMATIC_THRESHOLD = 10
    COGNITIVE_THRESHOLD = 15
    NESTING_THRESHOLD = 4
    LENGTH_THRESHOLD = 50

class ParallelProcessing:
    """Parallel processing defaults."""
    DEFAULT_WORKERS = 4
    MAX_WORKERS = 16

    @staticmethod
    def get_optimal_workers(max_threads: int = 0) -> int:
        """Calculate optimal worker count."""
        if max_threads > 0:
            return min(max_threads, ParallelProcessing.MAX_WORKERS)
        import os
        cpu_count = os.cpu_count() or 4
        return max(1, min(cpu_count - 1, ParallelProcessing.MAX_WORKERS))

class CacheDefaults:
    """Cache configuration."""
    TTL_SECONDS = 3600  # 1 hour
    MAX_SIZE_MB = 100
    CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes

class FilePatterns:
    """Common file patterns."""
    DEFAULT_EXCLUDE = [
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/venv/**",
        "**/.venv/**",
        "**/site-packages/**",
        "**/dist/**",
        "**/build/**",
        "**/.git/**"
    ]
```

### 3. Add Performance Monitoring
```python
# Add to all tool functions
import time
from functools import wraps

def monitor_performance(func):
    """Decorator to monitor tool performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.info(
                "tool_performance",
                tool=func.__name__,
                duration_ms=int(duration * 1000),
                status="success"
            )
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(
                "tool_performance",
                tool=func.__name__,
                duration_ms=int(duration * 1000),
                status="failed",
                error=str(e)[:200]
            )
            raise
    return wrapper

# Apply to all tools
@monitor_performance
def analyze_complexity_tool(...):
    ...
```

## Success Metrics

### Before Refactoring
- Functions exceeding complexity: 240/397 (60%)
- Average cyclomatic complexity: ~12
- Average cognitive complexity: ~18
- Largest function: 309 lines
- Code smells: 395
- Standards violations: 254

### After Refactoring (Targets)
- Functions exceeding complexity: <40/397 (<10%)
- Average cyclomatic complexity: <8
- Average cognitive complexity: <12
- Largest function: <100 lines
- Code smells: <100
- Standards violations: <50 (only in scripts)

### Continuous Monitoring
```bash
# Add to pre-commit hook
uv run python -c "
from ast_grep_mcp.features.complexity.tools import analyze_complexity_tool

result = analyze_complexity_tool(
    project_folder='.',
    language='python',
    cyclomatic_threshold=15,
    cognitive_threshold=20
)

if result['summary']['exceeding_threshold'] > 10:
    print(f\"❌ Complexity check failed: {result['summary']['exceeding_threshold']} functions exceed thresholds\")
    exit(1)

print('✅ Complexity check passed')
"
```
