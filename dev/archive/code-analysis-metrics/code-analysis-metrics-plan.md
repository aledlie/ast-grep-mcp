# Code Analysis & Metrics - Strategic Plan

**Last Updated:** 2025-11-18
**Status:** Planning
**Owner:** Development Team
**Priority:** Medium-High

---

## Executive Summary

This plan outlines the creation of comprehensive code analysis and metrics tools for the ast-grep-mcp server, enabling developers to assess code quality through automated analysis of complexity, code smells, dependencies, and dead code.

**Current State:** No dedicated code analysis tools exist in the MCP server.

**Proposed State:** A suite of analysis tools that:
1. Calculate cyclomatic complexity and nesting depth
2. Detect common code smells (long functions, parameter bloat, etc.)
3. Analyze dependency graphs and detect circular dependencies
4. Identify dead/unused code across projects
5. Generate actionable improvement recommendations
6. Track metrics over time for trend analysis

**Expected Impact:**
- **Code Quality:** Systematic identification of technical debt
- **Maintainability:** Early detection of problematic patterns
- **Refactoring Guidance:** Data-driven priorities for improvement
- **Team Standards:** Objective metrics for code reviews

**Effort Estimate:** 5-7 weeks (XL)
**Risk Level:** Low-Medium (well-understood problem space)

---

## Current State Analysis

### Existing Capabilities

**ast-grep Integration:**
- ✅ Pattern matching for code constructs
- ✅ Multi-language support (27+ languages)
- ✅ JSON output with AST metadata
- ✅ Fast search across large codebases

**Related Tools:**
- `find_code` - Can find specific patterns
- `find_duplication` - Detects duplicate code
- `batch_search` - Execute multiple queries

### Current Limitations

**No Complexity Analysis:**
- Cannot measure cyclomatic complexity
- Cannot detect deep nesting
- No cognitive complexity metrics
- No function length metrics

**No Code Smell Detection:**
- Cannot identify long functions
- Cannot detect parameter bloat
- Cannot find large classes
- No detection of complex conditionals

**No Dependency Analysis:**
- Cannot map import relationships
- Cannot detect circular dependencies
- No unused import detection
- No dependency graph visualization

**No Dead Code Detection:**
- Cannot find unused functions
- Cannot find unused variables
- Cannot find unreachable code
- No whole-program analysis

---

## Proposed Future State

### New MCP Tools

**1. `analyze_complexity` - Complexity Metrics**
```python
def analyze_complexity(
    project_folder: str,
    language: str,
    include_files: Optional[List[str]] = None,
    threshold_cyclomatic: int = 10,
    threshold_nesting: int = 4,
    threshold_function_lines: int = 50
) -> Dict[str, Any]:
    """
    Analyze code complexity metrics.

    Returns:
    - Cyclomatic complexity per function
    - Nesting depth analysis
    - Function length metrics
    - Complexity distribution
    - Functions exceeding thresholds
    """
```

**2. `detect_code_smells` - Code Smell Detection**
```python
def detect_code_smells(
    project_folder: str,
    language: str,
    smell_types: Optional[List[str]] = None,
    severity_threshold: str = "medium"
) -> Dict[str, Any]:
    """
    Detect common code smells.

    Smell types:
    - long_function: Functions exceeding length threshold
    - too_many_parameters: Parameter count > threshold
    - deep_nesting: Nesting depth > threshold
    - large_class: Class size exceeds threshold
    - complex_conditional: Nested if/else beyond threshold
    - magic_numbers: Unexplained literals
    - duplicated_code: Similar code blocks

    Returns detailed report with locations and recommendations.
    """
```

**3. `analyze_dependencies` - Dependency Analysis**
```python
def analyze_dependencies(
    project_folder: str,
    language: str,
    analysis_type: str = "all",
    format: str = "json"
) -> Dict[str, Any]:
    """
    Analyze code dependencies.

    Analysis types:
    - imports: Map all import relationships
    - circular: Detect circular dependencies
    - unused: Find unused imports
    - graph: Generate dependency graph
    - external: Analyze external dependencies

    Returns dependency map, issues, and visualization data.
    """
```

**4. `find_dead_code` - Dead Code Detection**
```python
def find_dead_code(
    project_folder: str,
    language: str,
    analysis_scope: str = "project",
    include_tests: bool = False
) -> Dict[str, Any]:
    """
    Identify unused and unreachable code.

    Detects:
    - Unused functions (never called)
    - Unused variables (never referenced)
    - Unreachable code (after return/break)
    - Unused imports
    - Unused class methods

    Returns list of dead code with confidence scores.
    """
```

**5. `generate_metrics_report` - Comprehensive Reporting**
```python
def generate_metrics_report(
    project_folder: str,
    language: str,
    report_format: str = "markdown",
    include_trends: bool = False
) -> Dict[str, Any]:
    """
    Generate comprehensive code metrics report.

    Combines:
    - Complexity metrics
    - Code smell summary
    - Dependency health
    - Dead code findings
    - Trend analysis (if historical data available)

    Returns formatted report with visualizations.
    """
```

---

## Implementation Phases

### Phase 1: Complexity Analysis Engine (Week 1-2, Size: L)

**Goal:** Implement cyclomatic complexity and nesting depth analysis.

**Deliverables:**
1. Cyclomatic complexity calculator
2. Nesting depth analyzer
3. Function length metrics
4. `analyze_complexity` MCP tool
5. Threshold-based reporting

**Key Technical Challenges:**
- Calculate cyclomatic complexity from AST patterns
- Handle language-specific control flow structures
- Optimize for large codebases

**Success Criteria:**
- Accurate complexity scores for Python, TypeScript, Java
- Performance: <10s for 1000 functions
- Clear threshold violations report

---

### Phase 2: Code Smell Detection (Week 2-3, Size: L)

**Goal:** Implement detection for common code smells.

**Deliverables:**
1. Long function detector
2. Parameter bloat detector
3. Deep nesting detector
4. Large class detector
5. Magic number detector
6. `detect_code_smells` MCP tool

**Key Technical Challenges:**
- Define language-specific thresholds
- Balance false positives vs. false negatives
- Provide actionable recommendations

**Success Criteria:**
- Detects 7+ smell types
- <20% false positive rate
- Clear, actionable recommendations

---

### Phase 3: Dependency Analysis (Week 3-5, Size: XL)

**Goal:** Implement dependency graph analysis and circular dependency detection.

**Deliverables:**
1. Import relationship mapper
2. Circular dependency detector
3. Unused import detector
4. Dependency graph generator
5. `analyze_dependencies` MCP tool

**Key Technical Challenges:**
- Parse imports across different languages
- Build dependency graph efficiently
- Detect cycles in large graphs
- Handle dynamic imports

**Success Criteria:**
- Maps dependencies accurately
- Detects circular dependencies
- Generates visualizable graph data
- Performance: <30s for 1000 files

---

### Phase 4: Dead Code Detection (Week 5-6, Size: L)

**Goal:** Identify unused functions, variables, and unreachable code.

**Deliverables:**
1. Unused function detector
2. Unused variable detector
3. Unreachable code detector
4. Call graph builder
5. `find_dead_code` MCP tool

**Key Technical Challenges:**
- Build accurate call graph
- Handle reflection/dynamic calls
- Avoid false positives for public APIs
- Cross-file analysis

**Success Criteria:**
- Detects unused code with >80% accuracy
- Confidence scoring for findings
- Low false positive rate for public APIs

---

### Phase 5: Reporting & Visualization (Week 6-7, Size: M)

**Goal:** Create comprehensive reporting and trend tracking.

**Deliverables:**
1. Markdown report generator
2. JSON report generator
3. Trend tracking (historical comparison)
4. Visualization data (graphs, charts)
5. `generate_metrics_report` MCP tool

**Success Criteria:**
- Clear, readable reports
- Multiple format support
- Trend analysis functional
- Visualizations easy to interpret

---

### Phase 6: Testing & Documentation (Week 7, Size: M)

**Goal:** Comprehensive testing and documentation.

**Deliverables:**
1. 100+ test cases
2. Documentation updates
3. Example gallery
4. Performance benchmarks

**Success Criteria:**
- >95% test coverage
- All documentation complete
- Performance benchmarks pass

---

## Detailed Task Breakdown

### Phase 1: Complexity Analysis Engine

**1.1 Cyclomatic Complexity Calculator (Size: M)**
- [ ] Research cyclomatic complexity formula
- [ ] Identify control flow patterns per language
- [ ] Implement branch counting algorithm
- [ ] Handle try/catch, loops, conditionals
- [ ] Unit tests for known complexity scores

**1.2 Nesting Depth Analyzer (Size: M)**
- [ ] Track nesting levels in AST
- [ ] Identify deeply nested blocks
- [ ] Report maximum nesting depth
- [ ] Unit tests for nesting scenarios

**1.3 Function Length Metrics (Size: S)**
- [ ] Count lines per function
- [ ] Count statements per function
- [ ] Filter comments and whitespace
- [ ] Unit tests

**1.4 Complexity Tool Implementation (Size: M)**
- [ ] Create `analyze_complexity` tool
- [ ] Integrate calculators
- [ ] Add threshold checking
- [ ] Format results
- [ ] Integration tests

---

### Phase 2: Code Smell Detection

**2.1 Long Function Detector (Size: S)**
- [ ] Identify functions exceeding line threshold
- [ ] Provide split suggestions
- [ ] Unit tests

**2.2 Parameter Bloat Detector (Size: S)**
- [ ] Count function parameters
- [ ] Flag functions with >5 parameters
- [ ] Suggest object parameter pattern
- [ ] Unit tests

**2.3 Deep Nesting Detector (Size: S)**
- [ ] Reuse nesting depth analyzer
- [ ] Flag depth >4
- [ ] Suggest extraction
- [ ] Unit tests

**2.4 Large Class Detector (Size: M)**
- [ ] Count methods per class
- [ ] Count lines per class
- [ ] Suggest class splitting
- [ ] Unit tests

**2.5 Magic Number Detector (Size: M)**
- [ ] Identify numeric/string literals
- [ ] Exclude common values (0, 1, -1)
- [ ] Suggest named constants
- [ ] Unit tests

**2.6 Code Smell Tool Implementation (Size: M)**
- [ ] Create `detect_code_smells` tool
- [ ] Integrate detectors
- [ ] Severity scoring
- [ ] Integration tests

---

### Phase 3: Dependency Analysis

**3.1 Import Relationship Mapper (Size: L)**
- [ ] Extract import statements (Python, TS, Java)
- [ ] Build file-to-file dependency map
- [ ] Handle relative imports
- [ ] Handle aliased imports
- [ ] Unit tests

**3.2 Circular Dependency Detector (Size: M)**
- [ ] Implement cycle detection algorithm (Tarjan's)
- [ ] Identify circular import chains
- [ ] Report cycle paths
- [ ] Unit tests with known cycles

**3.3 Unused Import Detector (Size: M)**
- [ ] Track imported symbols
- [ ] Track symbol usage
- [ ] Flag unused imports
- [ ] Unit tests

**3.4 Dependency Graph Generator (Size: M)**
- [ ] Generate graph data structure
- [ ] Format for visualization (Graphviz, Mermaid)
- [ ] Add metrics (depth, fan-in, fan-out)
- [ ] Unit tests

**3.5 Dependency Tool Implementation (Size: M)**
- [ ] Create `analyze_dependencies` tool
- [ ] Integrate analyzers
- [ ] Format results
- [ ] Integration tests

---

### Phase 4: Dead Code Detection

**4.1 Call Graph Builder (Size: L)**
- [ ] Extract function definitions
- [ ] Extract function calls
- [ ] Build caller-callee relationships
- [ ] Handle methods, closures
- [ ] Unit tests

**4.2 Unused Function Detector (Size: M)**
- [ ] Identify functions with no callers
- [ ] Exclude entry points (main, exports)
- [ ] Confidence scoring
- [ ] Unit tests

**4.3 Unused Variable Detector (Size: M)**
- [ ] Track variable definitions
- [ ] Track variable usage
- [ ] Flag write-only variables
- [ ] Unit tests

**4.4 Unreachable Code Detector (Size: M)**
- [ ] Detect code after return
- [ ] Detect code after break/continue
- [ ] Detect unreachable branches
- [ ] Unit tests

**4.5 Dead Code Tool Implementation (Size: M)**
- [ ] Create `find_dead_code` tool
- [ ] Integrate detectors
- [ ] Confidence scoring
- [ ] Integration tests

---

## Success Metrics

**Accuracy:**
- Complexity scores within 5% of industry tools
- Code smell detection: <20% false positive rate
- Dead code detection: >80% accuracy

**Performance:**
- Complexity analysis: <10s for 1000 functions
- Dependency analysis: <30s for 1000 files
- Dead code detection: <60s for 5000 functions

**Coverage:**
- Languages: Python, TypeScript, JavaScript, Java
- Metrics: 15+ different measurements
- Test coverage: >95%

**Usability:**
- Clear, actionable reports
- Threshold customization
- Integration with existing tools

---

## Risk Assessment

**Risk 1: Language-Specific Variations** (Medium Impact)
- **Mitigation:** Start with 2-3 languages, expand incrementally
- Test edge cases extensively

**Risk 2: False Positives in Dead Code** (Medium Impact)
- **Mitigation:** Confidence scoring, exclude public APIs
- Manual review workflow

**Risk 3: Performance on Large Codebases** (Medium Impact)
- **Mitigation:** Streaming, caching, incremental analysis
- Performance benchmarks in CI

---

## Timeline

- **Week 1-2:** Phase 1 (Complexity Analysis)
- **Week 2-3:** Phase 2 (Code Smell Detection)
- **Week 3-5:** Phase 3 (Dependency Analysis)
- **Week 5-6:** Phase 4 (Dead Code Detection)
- **Week 6-7:** Phase 5 (Reporting)
- **Week 7:** Phase 6 (Testing & Docs)

**Total:** 5-7 weeks

---

**End of Plan**
**Last Updated:** 2025-11-18
