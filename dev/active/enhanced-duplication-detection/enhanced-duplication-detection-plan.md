# Enhanced Duplication Detection - Strategic Plan

**Last Updated:** 2025-11-18
**Status:** Planning
**Owner:** Development Team
**Priority:** High

---

## Executive Summary

This plan outlines the enhancement of the existing `find_duplication` MCP tool to move from passive detection and suggestions to active, automated code deduplication with intelligent refactoring capabilities.

**Current State:** The tool detects duplicate code and generates basic refactoring suggestions.

**Proposed State:** An intelligent system that:
1. Analyzes duplicate code to extract parameters and identify patterns
2. Generates concrete refactoring code (not just suggestions)
3. Automatically applies deduplication transformations with safety checks
4. Provides detailed diff previews and rollback capabilities
5. Supports multi-file refactoring scenarios
6. Integrates with existing `rewrite_code` infrastructure

**Expected Impact:**
- **Developer Productivity:** Reduce manual refactoring effort by 70-80%
- **Code Quality:** Systematic DRY principle enforcement across codebases
- **Maintainability:** Automated detection and remediation of duplication
- **Safety:** Preview-first workflow with full rollback support

**Effort Estimate:** 4-6 weeks (XL)
**Risk Level:** Medium (requires careful AST manipulation and testing)

---

## Current State Analysis

### Existing Capabilities

**find_duplication Tool (main.py:1571-1828):**
- ✅ Detects duplicate functions, classes, methods via ast-grep patterns
- ✅ Calculates similarity scores using difflib (0.0-1.0)
- ✅ Groups duplicates by line count buckets (83% performance improvement)
- ✅ Filters by minimum similarity threshold (default: 0.8)
- ✅ Filters by minimum lines (default: 5)
- ✅ Excludes library code patterns (node_modules, site-packages, etc.)
- ✅ Generates basic refactoring suggestions
- ✅ Supports 27+ programming languages via ast-grep

**Refactoring Suggestions (main.py:3206-3275):**
- ✅ Identifies suggestion type (Extract Function, Extract Base Class, etc.)
- ✅ Provides generic descriptions
- ✅ Calculates potential line savings
- ✅ Lists all duplicate locations
- ✅ Includes sample code preview

**Standalone Script (scripts/find_duplication.py):**
- ✅ Command-line interface for duplication detection
- ✅ JSON output support
- ✅ Formatted console reports

### Current Limitations

**Analysis Gaps:**
1. **No Parameter Extraction:** Suggestions are generic, don't identify what should be parameterized
2. **No Pattern Recognition:** Doesn't analyze *what differs* between duplicates
3. **No Complexity Assessment:** All duplicates treated equally regardless of refactoring difficulty
4. **No Dependency Analysis:** Doesn't check if duplicates can be safely merged

**Automation Gaps:**
1. **Manual Refactoring Required:** User must implement suggestions by hand
2. **No Code Generation:** Doesn't create the extracted function/class
3. **No Diff Preview:** Can't see what changes will look like before applying
4. **No Integration with rewrite_code:** Two separate workflows

**Safety Gaps:**
1. **No Impact Analysis:** Doesn't identify which files will be affected
2. **No Test Detection:** Doesn't warn if refactoring affects untested code
3. **No Syntax Validation:** Generated code might not be valid
4. **Limited Rollback:** Only works if integrated with rewrite_code

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ find_duplication Tool                                        │
│                                                               │
│  1. ast-grep pattern search (--pattern, --lang)              │
│  2. Stream results (stream_ast_grep_results)                 │
│  3. Filter excluded paths                                    │
│  4. Group by similarity (group_duplicates)                   │
│  5. Generate generic suggestions (generate_refactoring_...)  │
│  6. Return JSON report                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
                  User reads suggestions
                          ↓
                  Manual refactoring
```

**Key Files:**
- `main.py:1571-1828` - find_duplication tool
- `main.py:3206-3275` - generate_refactoring_suggestions
- `main.py:3108-3204` - group_duplicates (hash-based bucketing)
- `main.py:3042-3105` - calculate_similarity (difflib)
- `scripts/find_duplication.py` - Standalone CLI

---

## Proposed Future State

### Enhanced Architecture

```
┌────────────────────────────────────────────────────────────────┐
│ Enhanced find_duplication Tool                                  │
│                                                                  │
│  1. ast-grep pattern search                                     │
│  2. Stream results                                              │
│  3. Filter excluded paths                                       │
│  4. Group by similarity                                         │
│  5. ANALYZE PATTERNS (new)                                      │
│     - Extract parameters                                        │
│     - Identify varying logic                                    │
│     - Detect dependencies                                       │
│  6. GENERATE CONCRETE CODE (new)                                │
│     - Create extracted function/class                           │
│     - Generate replacement calls                                │
│     - Build complete refactoring plan                           │
│  7. VALIDATE & PREVIEW (new)                                    │
│     - Syntax check generated code                               │
│     - Generate diff preview                                     │
│     - Calculate impact scope                                    │
│  8. Return enhanced report with actionable refactoring          │
└────────────────────────────────────────────────────────────────┘
                          ↓
         ┌────────────────┴────────────────┐
         │                                  │
    Manual Review                   apply_deduplication Tool (new)
         │                                  │
         ↓                                  ↓
    Implement by hand                Auto-apply refactoring
                                            │
                                            ├─ Create backup (via rewrite_code)
                                            ├─ Generate extracted code
                                            ├─ Replace duplicates with calls
                                            ├─ Validate syntax
                                            └─ Return diff + rollback info
```

### New Capabilities

**1. Intelligent Pattern Analysis**
- Extract parameters from duplicate code variations
- Identify conditional logic that should be preserved
- Detect shared vs. varying imports
- Assess refactoring complexity (low/medium/high)
- Analyze dependencies between duplicates

**2. Concrete Code Generation**
- Generate complete extracted function/class with proper signature
- Create replacement call sites with correct arguments
- Handle import statements (add/remove as needed)
- Generate language-appropriate idioms (Python/TypeScript/etc.)
- Support multiple refactoring strategies per group

**3. Automated Application (New Tool: apply_deduplication)**
- Apply refactoring with single command
- Full integration with `rewrite_code` backup system
- Dry-run mode with diff preview
- Atomic multi-file changes
- Syntax validation before and after
- Rollback via existing backup system

**4. Enhanced Reporting**
- Refactoring difficulty score (1-10)
- Parameter extraction analysis
- Impact assessment (files affected, lines changed)
- Risk indicators (tests missing, complex logic, etc.)
- Multiple refactoring strategy options

**5. Safety & Verification**
- Pre-flight syntax validation
- Test coverage detection
- Dependency conflict detection
- Detailed diff generation
- Automatic backup creation
- Full rollback support

### New MCP Tools

**1. `find_duplication` (Enhanced)**
- All existing functionality preserved
- New `analysis_mode` parameter: "suggestions" (default) or "detailed"
- Detailed mode includes parameter extraction and code generation
- Returns concrete refactoring code, not just suggestions

**2. `apply_deduplication` (New)**
```python
def apply_deduplication(
    project_folder: str,
    group_id: int,
    refactoring_plan: Dict[str, Any],
    dry_run: bool = True,
    extract_to_file: Optional[str] = None,
    extract_function_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Apply an automated deduplication refactoring.

    Args:
        project_folder: Project root path
        group_id: ID from find_duplication results
        refactoring_plan: Plan generated by find_duplication (detailed mode)
        dry_run: If True, preview changes without applying (default)
        extract_to_file: Where to place extracted function (auto-detect if None)
        extract_function_name: Name for extracted function (auto-generate if None)

    Returns:
        {
            "status": "success" | "preview" | "failed",
            "changes_preview": [...],  # Diff for each file
            "backup_id": "...",        # If dry_run=False
            "files_modified": [...],
            "validation": {...}
        }
    """
```

**3. `analyze_deduplication_candidates` (New)**
```python
def analyze_deduplication_candidates(
    project_folder: str,
    language: str,
    min_similarity: float = 0.8,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Find and rank the best deduplication opportunities.

    Prioritizes by:
    - Potential line savings (higher = better)
    - Refactoring complexity (lower = easier)
    - Test coverage (higher = safer)

    Returns top candidates with full analysis.
    """
```

---

## Implementation Phases

### Phase 1: Pattern Analysis Engine (Week 1-2, Size: L)

**Goal:** Enhance duplication detection with intelligent pattern analysis.

**Deliverables:**
1. Parameter extraction algorithm
2. Variation analysis (what differs between duplicates)
3. Dependency detection
4. Complexity scoring
5. Enhanced refactoring suggestions with concrete details

**Key Tasks:**
- Implement AST-based diff analysis
- Build parameter extraction logic
- Create complexity assessment algorithm
- Add dependency graph analysis
- Enhance `generate_refactoring_suggestions` with details

**Success Criteria:**
- Correctly identifies parameters in 90%+ of cases
- Assigns appropriate complexity scores
- Detects import dependencies
- Enhanced suggestions include parameter lists

**Testing:**
- Unit tests with known duplicate patterns
- Edge cases: nested functions, closures, class methods
- Multi-language validation (Python, TypeScript, Java)

---

### Phase 2: Code Generation Engine (Week 2-3, Size: L)

**Goal:** Generate concrete refactoring code, not just suggestions.

**Deliverables:**
1. Extracted function/class code generator
2. Replacement call site generator
3. Import statement manager
4. Language-specific code formatters
5. Syntax validator

**Key Tasks:**
- Build template system for extracted functions
- Implement parameter substitution
- Create call site replacement logic
- Handle import additions/removals
- Add syntax validation hooks

**Success Criteria:**
- Generated code is syntactically valid
- Preserves original behavior (verified by tests)
- Handles edge cases (default args, kwargs, etc.)
- Supports Python, TypeScript, JavaScript, Java

**Testing:**
- Golden file tests (input duplicates → expected output)
- Syntax validation for each language
- Integration tests with real codebases
- Regression tests for edge cases

---

### Phase 3: Automated Application Tool (Week 3-4, Size: XL)

**Goal:** Implement `apply_deduplication` tool with safety features.

**Deliverables:**
1. New `apply_deduplication` MCP tool
2. Integration with `rewrite_code` backup system
3. Multi-file atomic changes
4. Diff preview generation
5. Rollback mechanism

**Key Tasks:**
- Create `apply_deduplication` tool skeleton
- Integrate with existing backup system
- Implement multi-file orchestration
- Build diff preview generator
- Add syntax validation pipeline
- Connect rollback to existing infrastructure

**Success Criteria:**
- Successful refactoring in dry-run mode (preview)
- Atomic multi-file changes when applied
- Full rollback capability via backup_id
- Syntax remains valid after refactoring
- All tests pass after refactoring

**Testing:**
- End-to-end refactoring scenarios
- Rollback verification tests
- Multi-file change atomicity tests
- Syntax validation tests
- Integration with existing rewrite_code tests

---

### Phase 4: Analysis & Ranking Tool (Week 4-5, Size: M)

**Goal:** Implement `analyze_deduplication_candidates` for prioritization.

**Deliverables:**
1. New `analyze_deduplication_candidates` MCP tool
2. Ranking algorithm (savings × ease ÷ risk)
3. Test coverage detection
4. Impact analysis
5. Recommendation engine

**Key Tasks:**
- Implement scoring algorithm
- Add test coverage detection (look for test files)
- Build impact analyzer (files affected, LOC changed)
- Create prioritization logic
- Add filtering options

**Success Criteria:**
- Top recommendations are genuinely high-value
- Scoring is transparent and explainable
- Test coverage accurately detected
- Recommendations actionable

**Testing:**
- Ranking correctness on known datasets
- Test coverage detection accuracy
- Impact analysis validation
- User acceptance testing

---

### Phase 5: Enhanced Reporting & UI (Week 5-6, Size: M)

**Goal:** Improve reporting with actionable insights.

**Deliverables:**
1. Enhanced JSON response format
2. Detailed diff preview formatting
3. Complexity visualization
4. Before/after code examples
5. Updated CLI script

**Key Tasks:**
- Design new response schema
- Implement diff formatter (unified diff style)
- Add before/after code generation
- Create complexity visualization
- Update `scripts/find_duplication.py`
- Add color coding for CLI output

**Success Criteria:**
- Reports are clear and actionable
- Diffs are easy to understand
- CLI output is user-friendly
- JSON schema is backward compatible

**Testing:**
- Response schema validation
- Diff formatting tests
- CLI output regression tests
- Documentation review

---

### Phase 6: Testing & Documentation (Week 6, Size: M)

**Goal:** Comprehensive testing and documentation.

**Deliverables:**
1. 100+ new test cases
2. Updated CLAUDE.md
3. New DEDUPLICATION-GUIDE.md
4. Updated README.md
5. Example gallery

**Key Tasks:**
- Write unit tests for all new functions
- Create integration tests for workflows
- Add edge case tests
- Update documentation
- Create example gallery (before/after)
- Performance benchmarking

**Success Criteria:**
- >95% test coverage for new code
- All documentation updated
- Examples are clear and compelling
- Performance benchmarks established

**Testing:**
- Test coverage report
- Documentation review
- Example validation
- Performance benchmarks pass

---

## Detailed Task Breakdown

### Phase 1: Pattern Analysis Engine

**1.1 AST-Based Diff Analysis (Size: M)**
- [ ] Research ast-grep JSON output structure for detailed AST
- [ ] Implement AST node alignment algorithm
- [ ] Create diff tree structure
- [ ] Handle multi-line vs. single-line differences
- [ ] Unit tests with simple duplicate pairs

**1.2 Parameter Extraction (Size: L)**
- [ ] Identify varying literals between duplicates
- [ ] Identify varying identifiers (variable names)
- [ ] Identify varying expressions
- [ ] Generate parameter names (descriptive)
- [ ] Handle complex parameter types
- [ ] Edge case: nested function calls as parameters
- [ ] Unit tests with parameter extraction scenarios

**1.3 Variation Analysis (Size: M)**
- [ ] Classify variations (literals, identifiers, logic)
- [ ] Detect conditional variations (if/else differences)
- [ ] Detect import variations
- [ ] Score variation complexity
- [ ] Unit tests for variation classification

**1.4 Dependency Detection (Size: M)**
- [ ] Extract import statements from matches
- [ ] Identify shared imports
- [ ] Identify unique imports per duplicate
- [ ] Detect internal dependencies (function calls)
- [ ] Unit tests for dependency analysis

**1.5 Complexity Scoring (Size: S)**
- [ ] Define complexity factors (parameters, logic, imports)
- [ ] Implement scoring algorithm (1-10 scale)
- [ ] Calibrate thresholds (low/med/high)
- [ ] Unit tests for scoring edge cases

**1.6 Enhanced Suggestions (Size: M)**
- [ ] Update `generate_refactoring_suggestions` signature
- [ ] Add parameter details to suggestions
- [ ] Add import change details
- [ ] Add complexity score
- [ ] Add refactoring strategy options
- [ ] Update response schema
- [ ] Unit tests for enhanced suggestions

---

### Phase 2: Code Generation Engine

**2.1 Template System (Size: M)**
- [ ] Create function template (Python)
- [ ] Create function template (TypeScript/JavaScript)
- [ ] Create function template (Java)
- [ ] Create class template (Python)
- [ ] Create class template (TypeScript)
- [ ] Template variable substitution
- [ ] Unit tests for templates

**2.2 Extracted Function Generator (Size: L)**
- [ ] Generate function signature from parameters
- [ ] Generate function body from sample code
- [ ] Handle return value detection
- [ ] Handle docstring generation
- [ ] Handle type annotations (Python, TypeScript)
- [ ] Unit tests for function generation

**2.3 Call Site Replacement (Size: L)**
- [ ] Generate replacement call with arguments
- [ ] Preserve indentation at call site
- [ ] Handle different argument passing styles
- [ ] Handle keyword arguments (Python)
- [ ] Handle object destructuring (JavaScript)
- [ ] Unit tests for call site generation

**2.4 Import Statement Manager (Size: M)**
- [ ] Detect where to add import for extracted function
- [ ] Generate import statement (language-specific)
- [ ] Identify imports to remove (if now unused)
- [ ] Handle relative vs. absolute imports
- [ ] Unit tests for import management

**2.5 Language-Specific Formatters (Size: M)**
- [ ] Python: black-style formatting
- [ ] TypeScript: prettier-style formatting
- [ ] JavaScript: prettier-style formatting
- [ ] Java: standard formatting
- [ ] Integration with existing syntax validation
- [ ] Unit tests for formatting

**2.6 Syntax Validator (Size: S)**
- [ ] Integrate with existing Python validation
- [ ] Integrate with existing JS/TS validation
- [ ] Add Java validation (javac or parser)
- [ ] Return detailed error messages
- [ ] Unit tests for validation

---

### Phase 3: Automated Application Tool

**3.1 Tool Skeleton (Size: S)**
- [ ] Create `apply_deduplication` function signature
- [ ] Add to MCP tool registry
- [ ] Define input/output schema
- [ ] Add logging instrumentation
- [ ] Add Sentry error tracking
- [ ] Basic integration test

**3.2 Backup Integration (Size: M)**
- [ ] Identify backup directory location
- [ ] Create backup metadata structure
- [ ] Copy files before modification
- [ ] Return backup_id to caller
- [ ] Integration test with rollback

**3.3 Multi-File Orchestration (Size: L)**
- [ ] Plan file modification order
- [ ] Handle extracted function file creation
- [ ] Update all duplicate location files
- [ ] Ensure atomicity (all or nothing)
- [ ] Handle failure scenarios (partial rollback)
- [ ] Integration tests for multi-file changes

**3.4 Diff Preview Generator (Size: M)**
- [ ] Generate unified diff for each file
- [ ] Format diffs for readability
- [ ] Include context lines
- [ ] Return structured diff data
- [ ] Unit tests for diff generation

**3.5 Syntax Validation Pipeline (Size: M)**
- [ ] Validate before applying changes
- [ ] Validate after applying changes
- [ ] Rollback on validation failure
- [ ] Detailed error reporting
- [ ] Integration tests for validation

**3.6 Rollback Mechanism (Size: S)**
- [ ] Leverage existing `rollback_rewrite` tool
- [ ] Ensure backup format compatibility
- [ ] Add deduplication-specific metadata
- [ ] Integration test rollback flow

---

### Phase 4: Analysis & Ranking Tool

**4.1 Tool Skeleton (Size: S)**
- [ ] Create `analyze_deduplication_candidates` signature
- [ ] Add to MCP tool registry
- [ ] Define input/output schema
- [ ] Add logging and Sentry tracking
- [ ] Basic integration test

**4.2 Ranking Algorithm (Size: M)**
- [ ] Define scoring formula
- [ ] Weight factors (savings, complexity, risk)
- [ ] Normalize scores to 0-100
- [ ] Sort results by score
- [ ] Unit tests for ranking

**4.3 Test Coverage Detection (Size: M)**
- [ ] Identify test file patterns (test_*, *_test.*, spec.*)
- [ ] Check if duplicate files have corresponding tests
- [ ] Flag untested duplicates as higher risk
- [ ] Unit tests for coverage detection

**4.4 Impact Analysis (Size: M)**
- [ ] Count files affected
- [ ] Estimate lines changed
- [ ] Identify call sites outside duplicates
- [ ] Flag breaking change risks
- [ ] Unit tests for impact calculation

**4.5 Recommendation Engine (Size: M)**
- [ ] Combine all scoring factors
- [ ] Generate actionable recommendation text
- [ ] Provide multiple strategy options
- [ ] Rank by effort/value ratio
- [ ] Unit tests for recommendations

---

### Phase 5: Enhanced Reporting & UI

**5.1 Response Schema Design (Size: S)**
- [ ] Design JSON schema for enhanced responses
- [ ] Ensure backward compatibility
- [ ] Document schema in CLAUDE.md
- [ ] Validate with JSON schema tools

**5.2 Diff Formatter (Size: M)**
- [ ] Implement unified diff formatting
- [ ] Add color coding (CLI)
- [ ] Add line numbers
- [ ] Handle multi-file diffs
- [ ] Unit tests for formatting

**5.3 Before/After Examples (Size: S)**
- [ ] Generate before code snippet
- [ ] Generate after code snippet (with extracted function)
- [ ] Include in response
- [ ] Format for readability

**5.4 Complexity Visualization (Size: S)**
- [ ] Create complexity bar (1-10)
- [ ] Add text descriptions (low/med/high)
- [ ] Add recommendations based on complexity
- [ ] CLI visualization

**5.5 CLI Script Update (Size: M)**
- [ ] Update `scripts/find_duplication.py`
- [ ] Add `--detailed` flag for enhanced analysis
- [ ] Add color output
- [ ] Add diff preview display
- [ ] Update help text and examples
- [ ] Integration tests for CLI

---

### Phase 6: Testing & Documentation

**6.1 Unit Tests (Size: L)**
- [ ] Pattern analysis tests (20+ cases)
- [ ] Code generation tests (30+ cases)
- [ ] Refactoring application tests (20+ cases)
- [ ] Ranking tests (10+ cases)
- [ ] Edge case tests (20+ cases)
- [ ] Achieve >95% coverage

**6.2 Integration Tests (Size: M)**
- [ ] End-to-end refactoring workflows (5+ scenarios)
- [ ] Multi-language support (Python, TypeScript, Java)
- [ ] Rollback scenarios (3+ cases)
- [ ] Error handling scenarios (5+ cases)

**6.3 Documentation (Size: M)**
- [ ] Update CLAUDE.md with new tools
- [ ] Create DEDUPLICATION-GUIDE.md
- [ ] Update README.md
- [ ] Add example gallery
- [ ] Document refactoring strategies
- [ ] Add troubleshooting section

**6.4 Performance Benchmarking (Size: S)**
- [ ] Benchmark pattern analysis
- [ ] Benchmark code generation
- [ ] Benchmark full refactoring workflow
- [ ] Add to `scripts/run_benchmarks.py`
- [ ] Set regression thresholds

---

## Risk Assessment & Mitigation

### Technical Risks

**Risk 1: Generated Code is Incorrect** (Likelihood: Medium, Impact: High)
- **Mitigation:**
  - Comprehensive syntax validation before and after
  - Golden file tests with known-good transformations
  - Dry-run mode as default
  - Full rollback capability
  - Test coverage detection warns about untested code

**Risk 2: AST Diff Algorithm is Unreliable** (Likelihood: Medium, Impact: Medium)
- **Mitigation:**
  - Fall back to text-based diff if AST unavailable
  - Extensive testing with edge cases
  - Conservative parameter extraction (when in doubt, suggest manual)
  - User review before application

**Risk 3: Multi-File Changes Cause Conflicts** (Likelihood: Low, Impact: High)
- **Mitigation:**
  - Atomic transaction model (all or nothing)
  - Pre-flight validation of all files
  - Automatic rollback on any failure
  - Clear error messages about conflicts

**Risk 4: Performance Degradation** (Likelihood: Medium, Impact: Low)
- **Mitigation:**
  - Detailed analysis is opt-in (`analysis_mode="detailed"`)
  - Caching of analysis results
  - Streaming for large codebases
  - Performance benchmarks in CI

**Risk 5: Language-Specific Edge Cases** (Likelihood: High, Impact: Medium)
- **Mitigation:**
  - Start with well-tested languages (Python, TypeScript)
  - Add languages incrementally
  - Extensive edge case testing per language
  - Clear documentation of limitations

### Process Risks

**Risk 6: Scope Creep** (Likelihood: High, Impact: Medium)
- **Mitigation:**
  - Clear phase boundaries
  - MVP per phase (minimal viable product)
  - Defer advanced features to future iterations
  - Regular stakeholder reviews

**Risk 7: Testing Complexity** (Likelihood: Medium, Impact: Medium)
- **Mitigation:**
  - Test-driven development
  - Reuse existing test infrastructure
  - Golden file approach for complex cases
  - Automated test generation where possible

---

## Success Metrics

### Quantitative Metrics

1. **Accuracy:**
   - Parameter extraction accuracy: >90%
   - Generated code validity: >95%
   - Successful refactoring rate: >85%

2. **Performance:**
   - Analysis time: <2x current duplication detection
   - Code generation: <1 second per group
   - Full refactoring: <5 seconds for typical case

3. **Coverage:**
   - Test coverage: >95% for new code
   - Language support: Python, TypeScript, JavaScript, Java (Phase 1-3)
   - Edge case coverage: >50 edge cases tested

4. **Impact:**
   - Reduce manual refactoring time: 70-80%
   - Lines of code saved: Track across all uses
   - Adoption rate: >50% of duplication findings use auto-apply

### Qualitative Metrics

1. **Usability:**
   - Clear, actionable error messages
   - Intuitive dry-run workflow
   - Helpful documentation

2. **Safety:**
   - Zero data loss incidents
   - 100% rollback success rate
   - Clear warnings for risky refactorings

3. **Developer Experience:**
   - Positive user feedback
   - Low support burden
   - High recommendation rate

---

## Required Resources & Dependencies

### Technical Dependencies

**Existing Infrastructure:**
- ✅ `find_duplication` tool (main.py:1571-1828)
- ✅ `rewrite_code` tool with backup system
- ✅ `rollback_rewrite` tool
- ✅ ast-grep CLI integration
- ✅ Syntax validation for Python, JavaScript, TypeScript
- ✅ Test infrastructure (pytest)

**New Dependencies:**
- Python AST library (stdlib `ast` module)
- TypeScript AST parser (likely `@typescript-eslint/typescript-estree` via Node)
- Java AST parser (optional, for Java support)
- Diff library enhancements (stdlib `difflib` sufficient)

**Development Tools:**
- Existing: pytest, ruff, mypy, uv
- New: None required

### Human Resources

**Required Skills:**
- Strong Python programming (AST manipulation, code generation)
- Understanding of ast-grep patterns and output
- Experience with code refactoring
- Testing expertise
- Technical writing (documentation)

**Estimated Effort:**
- Phase 1: 1-2 weeks (1 developer)
- Phase 2: 1 week (1 developer)
- Phase 3: 1 week (1 developer)
- Phase 4: 1 week (1 developer)
- Phase 5: 1 week (1 developer)
- Phase 6: 1 week (1 developer)

**Total:** 4-6 weeks for 1 full-time developer

### Budget & Timeline

**Timeline:**
- Weeks 1-2: Phase 1 (Pattern Analysis)
- Weeks 2-3: Phase 2 (Code Generation)
- Weeks 3-4: Phase 3 (Automated Application)
- Week 4-5: Phase 4 (Analysis & Ranking)
- Week 5-6: Phase 5 (Enhanced Reporting)
- Week 6: Phase 6 (Testing & Documentation)

**Milestones:**
- End of Week 2: Enhanced analysis with parameter extraction
- End of Week 3: Code generation working for Python
- End of Week 4: Full refactoring workflow functional
- End of Week 5: Analysis and ranking tool complete
- End of Week 6: Production-ready with full documentation

**Budget:**
- Development time: 4-6 weeks × 1 developer
- Code review: 5% of development time
- Testing: 20% of development time (included in phases)
- Documentation: 10% of development time (included in Phase 6)

---

## Appendix A: Example Workflows

### Workflow 1: Enhanced Detection + Manual Review

```python
# Step 1: Find duplicates with detailed analysis
result = find_duplication(
    project_folder="/path/to/project",
    language="python",
    analysis_mode="detailed"  # NEW
)

# Step 2: Review suggestions with concrete code
for suggestion in result["refactoring_suggestions"]:
    print(f"Group {suggestion['group_id']}")
    print(f"Complexity: {suggestion['complexity_score']}/10")
    print(f"Extracted function:")
    print(suggestion['generated_code']['extracted_function'])  # NEW
    print(f"Replacement calls:")
    for call in suggestion['generated_code']['replacement_calls']:  # NEW
        print(f"  {call['file']}:{call['line']}: {call['code']}")

# Step 3: Manual implementation (or proceed to Workflow 2)
```

### Workflow 2: Automated Refactoring with Preview

```python
# Step 1: Find and analyze duplicates
result = find_duplication(
    project_folder="/path/to/project",
    language="python",
    analysis_mode="detailed"
)

# Step 2: Preview automated refactoring (dry-run)
group_id = 1  # First duplication group
plan = result["refactoring_suggestions"][0]

preview = apply_deduplication(
    project_folder="/path/to/project",
    group_id=group_id,
    refactoring_plan=plan,
    dry_run=True  # Preview only
)

# Step 3: Review diff
for change in preview["changes_preview"]:
    print(f"\nFile: {change['file']}")
    print(change['diff'])  # Unified diff

# Step 4: Apply refactoring
if looks_good:
    result = apply_deduplication(
        project_folder="/path/to/project",
        group_id=group_id,
        refactoring_plan=plan,
        dry_run=False  # Actually apply
    )

    print(f"Backup ID: {result['backup_id']}")
    print(f"Files modified: {len(result['files_modified'])}")

    # Step 5: If something went wrong, rollback
    if tests_failed:
        rollback_rewrite(
            project_folder="/path/to/project",
            backup_id=result['backup_id']
        )
```

### Workflow 3: Prioritized Refactoring

```python
# Step 1: Find best refactoring opportunities
candidates = analyze_deduplication_candidates(
    project_folder="/path/to/project",
    language="python",
    max_results=5
)

# Step 2: Review top candidates
for candidate in candidates["ranked_candidates"]:
    print(f"Score: {candidate['score']}/100")
    print(f"Potential savings: {candidate['potential_line_savings']} lines")
    print(f"Complexity: {candidate['complexity']}")
    print(f"Risk: {candidate['risk_level']}")
    print(f"Has tests: {candidate['has_test_coverage']}")

# Step 3: Apply top candidate
top = candidates["ranked_candidates"][0]
preview = apply_deduplication(
    project_folder="/path/to/project",
    group_id=top['group_id'],
    refactoring_plan=top['refactoring_plan'],
    dry_run=True
)

# ... review and apply as in Workflow 2
```

---

## Appendix B: Technical Design Details

### Parameter Extraction Algorithm

```
1. For each duplicate group:
   a. Extract AST from each instance (via ast-grep or native parser)
   b. Align AST nodes by structure
   c. Identify nodes that differ:
      - Literal values (strings, numbers, booleans)
      - Identifiers (variable names, function calls)
      - Expressions (complex varying logic)
   d. For each differing node:
      - Generate descriptive parameter name
      - Infer parameter type (if possible)
      - Detect default value patterns
   e. Return list of parameters with metadata

2. Handle edge cases:
   - Nested function calls → extract as parameter
   - Conditional logic variations → flag as complex
   - Import variations → handle separately
```

### Code Generation Templates

**Python Function Template:**
```python
def {function_name}({parameters}) -> {return_type}:
    """
    {docstring}

    Args:
        {param_docs}

    Returns:
        {return_doc}
    """
    {function_body}
    return {return_value}
```

**TypeScript Function Template:**
```typescript
export function {function_name}({parameters}): {return_type} {
    {function_body}
    return {return_value};
}
```

### Complexity Scoring Formula

```
complexity_score = (
    parameter_count * 1.0 +
    import_changes * 0.5 +
    conditional_variations * 2.0 +
    nested_calls * 1.5 +
    line_count * 0.1
)

scaled_score = min(10, complexity_score / 2)

if scaled_score < 3: "low complexity"
elif scaled_score < 7: "medium complexity"
else: "high complexity"
```

### Ranking Algorithm

```
value_score = potential_line_savings * 10
ease_score = 100 - (complexity_score * 10)
risk_score = (
    (100 if has_tests else 0) +
    (50 if no_external_dependencies else 0)
)

final_score = (
    value_score * 0.4 +
    ease_score * 0.3 +
    risk_score * 0.3
)

normalized = final_score / 100  # 0-100 scale
```

---

**End of Plan**
**Last Updated:** 2025-11-18
**Status:** Ready for Review
