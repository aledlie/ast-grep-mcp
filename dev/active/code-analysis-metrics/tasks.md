# Code Analysis & Metrics - Tasks

**Last Updated:** 2025-11-24

## Phase 1: Complexity Analysis Engine ✅

### 1.1 Cyclomatic Complexity Calculator ✅
- [x] Research cyclomatic complexity formula
- [x] Identify control flow patterns per language
- [x] Implement branch counting algorithm
- [x] Handle try/catch, loops, conditionals
- [x] Unit tests for known complexity scores

### 1.2 Nesting Depth Analyzer ✅
- [x] Track nesting levels
- [x] Identify deeply nested blocks
- [x] Report maximum nesting depth
- [x] Unit tests for nesting scenarios

### 1.3 Function Length Metrics ✅
- [x] Count lines per function
- [x] Count statements per function
- [x] Unit tests

### 1.4 Complexity Tool Implementation ✅
- [x] Create `analyze_complexity` tool
- [x] Integrate calculators
- [x] Add threshold checking
- [x] Format results
- [x] Integration tests

### 1.5 Storage & Trends ✅
- [x] SQLite database schema
- [x] Store analysis runs
- [x] Project trend queries
- [x] Git commit/branch tracking

### 1.6 Documentation ✅
- [x] Update CLAUDE.md
- [x] Add to Recent Updates section
- [x] Document tool usage

---

## Phase 2: Code Smell Detection 🔄

### 2.1 Long Function Detector
- [ ] Identify functions exceeding line threshold
- [ ] Provide split suggestions
- [ ] Unit tests

### 2.2 Parameter Bloat Detector
- [ ] Count function parameters
- [ ] Flag functions with >5 parameters
- [ ] Suggest object parameter pattern
- [ ] Unit tests

### 2.3 Deep Nesting Detector
- [ ] Reuse nesting depth analyzer
- [ ] Flag depth >4
- [ ] Suggest extraction
- [ ] Unit tests

### 2.4 Large Class Detector
- [ ] Count methods per class
- [ ] Count lines per class
- [ ] Suggest class splitting
- [ ] Unit tests

### 2.5 Magic Number Detector
- [ ] Identify numeric/string literals
- [ ] Exclude common values (0, 1, -1)
- [ ] Suggest named constants
- [ ] Unit tests

### 2.6 Code Smell Tool Implementation
- [ ] Create `detect_code_smells` tool
- [ ] Integrate detectors
- [ ] Severity scoring
- [ ] Integration tests

---

## Remaining Phases

### Phase 3: Dependency Analysis
- [ ] Import relationship mapper
- [ ] Circular dependency detector
- [ ] Unused import detector
- [ ] Dependency graph generator
- [ ] `analyze_dependencies` MCP tool

### Phase 4: Dead Code Detection
- [ ] Call graph builder
- [ ] Unused function detector
- [ ] Unused variable detector
- [ ] Unreachable code detector
- [ ] `find_dead_code` MCP tool

### Phase 5: Reporting & Visualization
- [ ] Markdown report generator
- [ ] JSON report generator
- [ ] Trend tracking
- [ ] `generate_metrics_report` MCP tool

### Phase 6: Testing & Documentation
- [ ] Comprehensive test coverage
- [ ] Performance benchmarks
- [ ] Documentation updates

---

## Backlog / Future Improvements

- [ ] Add benchmark tests to verify <10s for 1000 functions
- [ ] Use scientific thinking to improve cognitive complexity algorithm accuracy
- [ ] Add Halstead metrics
- [ ] Add maintainability index
- [ ] Support more languages (Go, Rust, C++)
