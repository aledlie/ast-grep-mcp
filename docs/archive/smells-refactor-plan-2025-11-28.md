# Code Smells Detector Refactoring Plan
**Date:** 2025-11-28
**Target:** src/ast_grep_mcp/features/quality/smells.py
**Status:** ✅ COMPLETE (see smells-refactor-results-2025-11-28.md)
**Commit:** `ddf8b0e` - refactor(smells): reduce _extract_classes complexity by 82%

## Executive Summary

The `detect_code_smells_impl` function in smells.py exhibits significant code smells itself (ironic!), with 250 lines and cognitive complexity of 88. This refactoring will apply strategy pattern and functional decomposition to reduce complexity while maintaining all functionality.

## Current State Analysis

### File: src/ast_grep_mcp/features/quality/smells.py
- **Function:** `detect_code_smells_impl` (lines 25-274)
- **Current Metrics:**
  - Lines: 250
  - Cyclomatic complexity: 61
  - Cognitive complexity: 88
  - Nesting depth: 6
  - Parameters: 12

### Code Structure Issues

1. **Monolithic Function**: Single function handling all responsibilities
2. **Deep Nesting**: Nested function `analyze_file_for_smells` with 6 levels
3. **Mixed Concerns**: Input validation, file finding, smell detection, and formatting in one place
4. **Repeated Logic**: Severity calculation repeated for each smell type
5. **High Coupling**: Direct dependencies on multiple modules

## Identified Issues (Categorized by Severity)

### Critical
- Cognitive complexity of 88 (threshold: 15)
- Function length of 250 lines (threshold: 100)

### Major
- Cyclomatic complexity of 61 (threshold: 10)
- Nesting depth of 6 (threshold: 4)
- Parameter count of 12 (threshold: 5)

### Minor
- Mixed abstraction levels
- Repeated severity calculation logic
- Hard-coded threshold multipliers

## Proposed Refactoring Plan

### Phase 1: Extract Helper Functions (Low Risk)

#### 1.1 Extract Input Validation
```python
def _validate_smell_detection_inputs(
    project_folder: str,
    language: str,
    severity_filter: str
) -> tuple[Path, str]:
    """Validate inputs for smell detection.
    Returns: (project_path, file_extension)
    """
```

#### 1.2 Extract File Finding Logic
```python
def _find_smell_analysis_files(
    project_path: Path,
    language: str,
    include_patterns: List[str],
    exclude_patterns: List[str]
) -> List[str]:
    """Find files to analyze for smells."""
```

#### 1.3 Extract Severity Calculation
```python
def _calculate_smell_severity(
    metric: float,
    threshold: float,
    smell_type: str
) -> str:
    """Calculate severity based on metric and threshold."""
```

### Phase 2: Strategy Pattern for Smell Detection (Medium Risk)

#### 2.1 Create Base SmellDetector
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SmellInfo:
    """Information about a detected code smell."""
    type: str
    file: str
    name: str
    line: int
    severity: str
    metric: Any
    threshold: Any
    message: str
    suggestion: str

class SmellDetector(ABC):
    """Base class for smell detectors."""

    @abstractmethod
    def detect(self, file_path: str, content: str, language: str) -> List[SmellInfo]:
        """Detect smells in the given file."""
        pass
```

#### 2.2 Create Specific Detectors
```python
class LongFunctionDetector(SmellDetector):
    """Detects long functions."""
    def __init__(self, threshold: int):
        self.threshold = threshold

    def detect(self, file_path: str, content: str, language: str) -> List[SmellInfo]:
        # Implementation

class ParameterBloatDetector(SmellDetector):
    """Detects parameter bloat."""
    def __init__(self, threshold: int):
        self.threshold = threshold

    def detect(self, file_path: str, content: str, language: str) -> List[SmellInfo]:
        # Implementation

class DeepNestingDetector(SmellDetector):
    """Detects deep nesting."""
    def __init__(self, threshold: int):
        self.threshold = threshold

    def detect(self, file_path: str, content: str, language: str) -> List[SmellInfo]:
        # Implementation

class LargeClassDetector(SmellDetector):
    """Detects large classes."""
    def __init__(self, lines_threshold: int, methods_threshold: int):
        self.lines_threshold = lines_threshold
        self.methods_threshold = methods_threshold

    def detect(self, file_path: str, content: str, language: str) -> List[SmellInfo]:
        # Implementation

class MagicNumberDetector(SmellDetector):
    """Detects magic numbers."""
    def detect(self, file_path: str, content: str, language: str) -> List[SmellInfo]:
        # Implementation
```

### Phase 3: Orchestrator Function (Low Risk)

#### 3.1 Create SmellAnalyzer Orchestrator
```python
class SmellAnalyzer:
    """Orchestrates smell detection across files."""

    def __init__(self, detectors: List[SmellDetector], max_threads: int = 4):
        self.detectors = detectors
        self.max_threads = max_threads

    def analyze_project(
        self,
        project_path: Path,
        language: str,
        files: List[str],
        severity_filter: str = "all"
    ) -> Dict[str, Any]:
        """Analyze project for code smells."""
        # Parallel execution logic
        # Result aggregation
        # Summary generation
```

### Phase 4: Response Formatting (Low Risk)

#### 4.1 Extract Response Formatter
```python
def _format_smell_detection_response(
    project_folder: str,
    language: str,
    files_analyzed: int,
    smells: List[SmellInfo],
    thresholds: Dict[str, Any]
) -> Dict[str, Any]:
    """Format the smell detection response."""
```

## Risk Assessment & Mitigation

### Risks
1. **Breaking existing API**: Mitigated by keeping `detect_code_smells_impl` signature unchanged
2. **Test failures**: Mitigated by incremental refactoring with test runs after each step
3. **Performance degradation**: Mitigated by maintaining ThreadPoolExecutor pattern

### Mitigation Strategy
1. Keep original function as orchestrator
2. Extract incrementally with tests after each extraction
3. Use existing test suite (27 tests) for validation
4. Preserve all error handling
5. Maintain backward compatibility

## Testing Strategy

1. **Unit Tests**: Run existing 27 tests after each extraction
2. **Integration Tests**: Verify MCP tool registration still works
3. **Performance Tests**: Compare execution time before/after
4. **Coverage Tests**: Ensure no loss of code coverage

## Success Metrics

### Target Complexity per Function
- Lines: < 100
- Cyclomatic complexity: < 10
- Cognitive complexity: < 20
- Nesting depth: < 5

### Expected Results
- **Main function**: ~50 lines (orchestration only)
- **Detector classes**: ~30-50 lines each
- **Helper functions**: ~20-30 lines each
- **Total functions**: 8-10 small, focused functions

## Step-by-Step Migration

1. Create `smells_detectors.py` module for detector classes
2. Extract validation and file finding helpers
3. Implement SmellDetector base class
4. Extract each smell detection to its detector class
5. Create SmellAnalyzer orchestrator
6. Extract response formatting
7. Update main function to use new components
8. Run full test suite
9. Document new structure

## Complete Dependency Map

### Current Dependencies
- `ast_grep_mcp.core.logging`
- `ast_grep_mcp.features.complexity.analyzer` (extract_functions_from_file, calculate_nesting_depth)
- Standard library: json, re, subprocess, pathlib, fnmatch, concurrent.futures

### New Internal Structure
```
smells.py (main entry point)
├── Uses: smells_detectors.py
├── Uses: smells_helpers.py
└── Maintains: detect_code_smells_impl()

smells_detectors.py (new module)
├── SmellDetector (base class)
├── LongFunctionDetector
├── ParameterBloatDetector
├── DeepNestingDetector
├── LargeClassDetector
└── MagicNumberDetector

smells_helpers.py (new module)
├── _validate_smell_detection_inputs()
├── _find_smell_analysis_files()
├── _calculate_smell_severity()
└── _format_smell_detection_response()
```

## Anti-patterns Found and Fixes

1. **God Function**: Split into 8-10 focused functions
2. **Deep Nesting**: Reduced to max 3 levels
3. **Parameter Bloat**: Use configuration objects
4. **Mixed Abstraction**: Separate orchestration from implementation
5. **Repeated Logic**: Extract common severity calculation

## Implementation Order

1. **Immediate** (Phase 1): Extract helpers - 1 hour
2. **Next** (Phase 2): Implement detectors - 2 hours
3. **Then** (Phase 3): Create orchestrator - 1 hour
4. **Finally** (Phase 4): Format response - 30 minutes

Total estimated effort: 4.5 hours