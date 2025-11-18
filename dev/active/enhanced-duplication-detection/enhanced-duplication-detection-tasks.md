# Enhanced Duplication Detection - Task Checklist

**Last Updated:** 2025-11-18
**Status:** Not Started
**Current Phase:** Planning Complete

---

## Phase 1: Pattern Analysis Engine (Weeks 1-2, Size: L)

### 1.1 AST-Based Diff Analysis (Size: M)
- [ ] Research ast-grep JSON output structure for detailed AST
- [ ] Implement AST node alignment algorithm
- [ ] Create diff tree structure
- [ ] Handle multi-line vs. single-line differences
- [ ] Unit tests with simple duplicate pairs

### 1.2 Parameter Extraction (Size: L)
- [ ] Identify varying literals between duplicates
- [ ] Identify varying identifiers (variable names)
- [ ] Identify varying expressions
- [ ] Generate parameter names (descriptive)
- [ ] Handle complex parameter types
- [ ] Edge case: nested function calls as parameters
- [ ] Unit tests with parameter extraction scenarios

### 1.3 Variation Analysis (Size: M)
- [ ] Classify variations (literals, identifiers, logic)
- [ ] Detect conditional variations (if/else differences)
- [ ] Detect import variations
- [ ] Score variation complexity
- [ ] Unit tests for variation classification

### 1.4 Dependency Detection (Size: M)
- [ ] Extract import statements from matches
- [ ] Identify shared imports
- [ ] Identify unique imports per duplicate
- [ ] Detect internal dependencies (function calls)
- [ ] Unit tests for dependency analysis

### 1.5 Complexity Scoring (Size: S)
- [ ] Define complexity factors (parameters, logic, imports)
- [ ] Implement scoring algorithm (1-10 scale)
- [ ] Calibrate thresholds (low/med/high)
- [ ] Unit tests for scoring edge cases

### 1.6 Enhanced Suggestions (Size: M)
- [ ] Update `generate_refactoring_suggestions` signature
- [ ] Add parameter details to suggestions
- [ ] Add import change details
- [ ] Add complexity score
- [ ] Add refactoring strategy options
- [ ] Update response schema
- [ ] Unit tests for enhanced suggestions

**Phase 1 Completion Criteria:**
- [ ] All Phase 1 tasks completed
- [ ] Parameter extraction accuracy >90%
- [ ] Complexity scoring calibrated
- [ ] All existing tests pass
- [ ] 20+ new tests written and passing

---

## Phase 2: Code Generation Engine (Weeks 2-3, Size: L)

### 2.1 Template System (Size: M)
- [ ] Create function template (Python)
- [ ] Create function template (TypeScript/JavaScript)
- [ ] Create function template (Java)
- [ ] Create class template (Python)
- [ ] Create class template (TypeScript)
- [ ] Template variable substitution
- [ ] Unit tests for templates

### 2.2 Extracted Function Generator (Size: L)
- [ ] Generate function signature from parameters
- [ ] Generate function body from sample code
- [ ] Handle return value detection
- [ ] Handle docstring generation
- [ ] Handle type annotations (Python, TypeScript)
- [ ] Unit tests for function generation

### 2.3 Call Site Replacement (Size: L)
- [ ] Generate replacement call with arguments
- [ ] Preserve indentation at call site
- [ ] Handle different argument passing styles
- [ ] Handle keyword arguments (Python)
- [ ] Handle object destructuring (JavaScript)
- [ ] Unit tests for call site generation

### 2.4 Import Statement Manager (Size: M)
- [ ] Detect where to add import for extracted function
- [ ] Generate import statement (language-specific)
- [ ] Identify imports to remove (if now unused)
- [ ] Handle relative vs. absolute imports
- [ ] Unit tests for import management

### 2.5 Language-Specific Formatters (Size: M)
- [ ] Python: black-style formatting
- [ ] TypeScript: prettier-style formatting
- [ ] JavaScript: prettier-style formatting
- [ ] Java: standard formatting
- [ ] Integration with existing syntax validation
- [ ] Unit tests for formatting

### 2.6 Syntax Validator (Size: S)
- [ ] Integrate with existing Python validation
- [ ] Integrate with existing JS/TS validation
- [ ] Add Java validation (javac or parser)
- [ ] Return detailed error messages
- [ ] Unit tests for validation

**Phase 2 Completion Criteria:**
- [ ] All Phase 2 tasks completed
- [ ] Generated code is syntactically valid (Python, TypeScript)
- [ ] Call sites preserve original behavior
- [ ] Import management works correctly
- [ ] 30+ new tests written and passing

---

## Phase 3: Automated Application Tool (Weeks 3-4, Size: XL)

### 3.1 Tool Skeleton (Size: S)
- [ ] Create `apply_deduplication` function signature
- [ ] Add to MCP tool registry
- [ ] Define input/output schema
- [ ] Add logging instrumentation
- [ ] Add Sentry error tracking
- [ ] Basic integration test

### 3.2 Backup Integration (Size: M)
- [ ] Identify backup directory location
- [ ] Create backup metadata structure
- [ ] Copy files before modification
- [ ] Return backup_id to caller
- [ ] Integration test with rollback

### 3.3 Multi-File Orchestration (Size: L)
- [ ] Plan file modification order
- [ ] Handle extracted function file creation
- [ ] Update all duplicate location files
- [ ] Ensure atomicity (all or nothing)
- [ ] Handle failure scenarios (partial rollback)
- [ ] Integration tests for multi-file changes

### 3.4 Diff Preview Generator (Size: M)
- [ ] Generate unified diff for each file
- [ ] Format diffs for readability
- [ ] Include context lines
- [ ] Return structured diff data
- [ ] Unit tests for diff generation

### 3.5 Syntax Validation Pipeline (Size: M)
- [ ] Validate before applying changes
- [ ] Validate after applying changes
- [ ] Rollback on validation failure
- [ ] Detailed error reporting
- [ ] Integration tests for validation

### 3.6 Rollback Mechanism (Size: S)
- [ ] Leverage existing `rollback_rewrite` tool
- [ ] Ensure backup format compatibility
- [ ] Add deduplication-specific metadata
- [ ] Integration test rollback flow

**Phase 3 Completion Criteria:**
- [ ] All Phase 3 tasks completed
- [ ] Dry-run preview shows accurate diffs
- [ ] Applied refactoring passes all tests
- [ ] Rollback works 100% of the time
- [ ] Multi-file changes are atomic
- [ ] 20+ new tests written and passing

---

## Phase 4: Analysis & Ranking Tool (Weeks 4-5, Size: M)

### 4.1 Tool Skeleton (Size: S)
- [ ] Create `analyze_deduplication_candidates` signature
- [ ] Add to MCP tool registry
- [ ] Define input/output schema
- [ ] Add logging and Sentry tracking
- [ ] Basic integration test

### 4.2 Ranking Algorithm (Size: M)
- [ ] Define scoring formula
- [ ] Weight factors (savings, complexity, risk)
- [ ] Normalize scores to 0-100
- [ ] Sort results by score
- [ ] Unit tests for ranking

### 4.3 Test Coverage Detection (Size: M)
- [ ] Identify test file patterns (test_*, *_test.*, spec.*)
- [ ] Check if duplicate files have corresponding tests
- [ ] Flag untested duplicates as higher risk
- [ ] Unit tests for coverage detection

### 4.4 Impact Analysis (Size: M)
- [ ] Count files affected
- [ ] Estimate lines changed
- [ ] Identify call sites outside duplicates
- [ ] Flag breaking change risks
- [ ] Unit tests for impact calculation

### 4.5 Recommendation Engine (Size: M)
- [ ] Combine all scoring factors
- [ ] Generate actionable recommendation text
- [ ] Provide multiple strategy options
- [ ] Rank by effort/value ratio
- [ ] Unit tests for recommendations

**Phase 4 Completion Criteria:**
- [ ] All Phase 4 tasks completed
- [ ] Ranking prioritizes high-value refactorings
- [ ] Test coverage detection is accurate
- [ ] Top 5 recommendations are actionable
- [ ] 10+ new tests written and passing

---

## Phase 5: Enhanced Reporting & UI (Weeks 5-6, Size: M)

### 5.1 Response Schema Design (Size: S)
- [ ] Design JSON schema for enhanced responses
- [ ] Ensure backward compatibility
- [ ] Document schema in CLAUDE.md
- [ ] Validate with JSON schema tools

### 5.2 Diff Formatter (Size: M)
- [ ] Implement unified diff formatting
- [ ] Add color coding (CLI)
- [ ] Add line numbers
- [ ] Handle multi-file diffs
- [ ] Unit tests for formatting

### 5.3 Before/After Examples (Size: S)
- [ ] Generate before code snippet
- [ ] Generate after code snippet (with extracted function)
- [ ] Include in response
- [ ] Format for readability

### 5.4 Complexity Visualization (Size: S)
- [ ] Create complexity bar (1-10)
- [ ] Add text descriptions (low/med/high)
- [ ] Add recommendations based on complexity
- [ ] CLI visualization

### 5.5 CLI Script Update (Size: M)
- [ ] Update `scripts/find_duplication.py`
- [ ] Add `--detailed` flag for enhanced analysis
- [ ] Add color output
- [ ] Add diff preview display
- [ ] Update help text and examples
- [ ] Integration tests for CLI

**Phase 5 Completion Criteria:**
- [ ] All Phase 5 tasks completed
- [ ] CLI output is user-friendly
- [ ] Diffs are readable and accurate
- [ ] Documentation is comprehensive
- [ ] Examples are clear

---

## Phase 6: Testing & Documentation (Week 6, Size: M)

### 6.1 Unit Tests (Size: L)
- [ ] Pattern analysis tests (20+ cases)
- [ ] Code generation tests (30+ cases)
- [ ] Refactoring application tests (20+ cases)
- [ ] Ranking tests (10+ cases)
- [ ] Edge case tests (20+ cases)
- [ ] Achieve >95% coverage

### 6.2 Integration Tests (Size: M)
- [ ] End-to-end refactoring workflows (5+ scenarios)
- [ ] Multi-language support (Python, TypeScript, Java)
- [ ] Rollback scenarios (3+ cases)
- [ ] Error handling scenarios (5+ cases)

### 6.3 Documentation (Size: M)
- [ ] Update CLAUDE.md with new tools
- [ ] Create DEDUPLICATION-GUIDE.md
- [ ] Update README.md
- [ ] Add example gallery
- [ ] Document refactoring strategies
- [ ] Add troubleshooting section

### 6.4 Performance Benchmarking (Size: S)
- [ ] Benchmark pattern analysis
- [ ] Benchmark code generation
- [ ] Benchmark full refactoring workflow
- [ ] Add to `scripts/run_benchmarks.py`
- [ ] Set regression thresholds

**Phase 6 Completion Criteria:**
- [ ] All Phase 6 tasks completed
- [ ] >95% test coverage for new code
- [ ] All documentation updated
- [ ] Performance benchmarks pass
- [ ] Ready for production use

---

## Final Checklist

### Pre-Release Checklist
- [ ] All 6 phases completed
- [ ] All tests passing (unit + integration)
- [ ] Performance benchmarks pass
- [ ] Documentation complete (CLAUDE.md, DEDUPLICATION-GUIDE.md, README.md)
- [ ] Code review completed
- [ ] Sentry integration tested
- [ ] Backward compatibility verified
- [ ] CLI script working
- [ ] Example gallery created

### Release Checklist
- [ ] Create release notes
- [ ] Update version number
- [ ] Tag release in git
- [ ] Update CHANGELOG.md
- [ ] Announce to users

---

## Progress Tracking

**Overall Progress:** 0/150 tasks completed (0%)

**Phase 1:** 0/28 tasks (0%)
**Phase 2:** 0/28 tasks (0%)
**Phase 3:** 0/26 tasks (0%)
**Phase 4:** 0/19 tasks (0%)
**Phase 5:** 0/17 tasks (0%)
**Phase 6:** 0/23 tasks (0%)

**Status:** Planning complete, ready to start Phase 1

---

**Last Updated:** 2025-11-18
**Next Update:** After first task completion
