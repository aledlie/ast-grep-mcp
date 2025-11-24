# Phase 1: Pattern Analysis Engine TODOs

## 1.1 AST-Based Diff Analysis
- [ ] Research ast-grep JSON output structure for detailed AST
- [ ] Implement AST node alignment algorithm
- [ ] Create diff tree structure
- [ ] Handle multi-line vs. single-line differences
- [ ] Unit tests with simple duplicate pairs

## 1.2 Parameter Extraction
- [ ] Identify varying literals between duplicates
- [ ] Identify varying identifiers (variable names)
- [ ] Identify varying expressions
- [ ] Generate parameter names (descriptive)
- [ ] Handle complex parameter types
- [ ] Edge case: nested function calls as parameters
- [ ] Unit tests with parameter extraction scenarios

## 1.3 Variation Analysis
- [ ] Classify variations (literals, identifiers, logic)
- [ ] Detect conditional variations (if/else differences)
- [ ] Detect import variations
- [ ] Score variation complexity
- [ ] Unit tests for variation classification

## 1.4 Dependency Detection
- [ ] Extract import statements from matches
- [ ] Identify shared imports
- [ ] Identify unique imports per duplicate
- [ ] Detect internal dependencies (function calls)
- [ ] Unit tests for dependency analysis

## 1.5 Complexity Scoring
- [ ] Define complexity factors (parameters, logic, imports)
- [ ] Implement scoring algorithm (1-10 scale)
- [ ] Calibrate thresholds (low/med/high)
- [ ] Unit tests for scoring edge cases

## 1.6 Enhanced Suggestions
- [ ] Update `generate_refactoring_suggestions` signature
- [ ] Add parameter details to suggestions
- [ ] Add import change details
- [ ] Add complexity score
- [ ] Add refactoring strategy options
- [ ] Update response schema
- [ ] Unit tests for enhanced suggestions
