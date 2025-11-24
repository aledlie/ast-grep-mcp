# Code Quality & Standards - Strategic Plan

**Last Updated:** 2025-11-24
**Status:** In Progress (Phase 1 ✅ Complete, Phase 2A ✅ Complete)
**Owner:** Development Team
**Priority:** Medium-High

---

## Executive Summary

This plan outlines the creation of code quality and standards enforcement tools using ast-grep's pattern matching capabilities to enforce team-specific coding standards, detect anti-patterns, and identify security vulnerabilities.

**Current State:** No custom linting or standards enforcement in MCP server.

**Proposed State:** Quality enforcement tools that:
1. Define and enforce custom linting rules via ast-grep patterns
2. Detect team-specific anti-patterns
3. Scan for common security vulnerabilities
4. Enforce consistent code style across projects
5. Generate quality reports with actionable fixes
6. Integrate with CI/CD for automated checks

**Expected Impact:**
- **Code Quality:** Systematic enforcement of team standards
- **Security:** Early detection of vulnerabilities
- **Consistency:** Uniform code style across team
- **Onboarding:** Automated enforcement teaches best practices

**Effort Estimate:** 5-7 weeks (XL)
**Risk Level:** Medium (requires security expertise)

---

## Current State Analysis

### Existing Capabilities

**Pattern Matching:**
- ✅ ast-grep pattern matching
- ✅ Multi-language support
- ✅ Complex pattern rules (YAML)

**Code Analysis (Completed in code-analysis-metrics):**
- ✅ Complexity analysis (cyclomatic, cognitive, nesting, length)
- ✅ Code smell detection (long functions, parameter bloat, deep nesting, large classes, magic numbers)
- ✅ Dependency analysis

**Related Tools:**
- `find_code` - Find pattern matches
- `rewrite_code` - Fix patterns automatically
- `analyze_complexity` - Measure code complexity metrics
- `detect_code_smells` - Identify code quality issues

**Remaining Gaps:**
- ❌ No pre-built linting rules library
- ❌ No security vulnerability scanning
- ❌ No custom rule management system
- ❌ No CI/CD integration guide
- ❌ No auto-fix for standards violations
- ❌ No quality reporting dashboard

---

## Proposed Future State

### New MCP Tools

**1. `create_linting_rule` - Define Custom Rules**
```python
def create_linting_rule(
    rule_name: str,
    description: str,
    pattern: str,
    severity: str,
    language: str,
    suggested_fix: Optional[str] = None,
    save_to_project: bool = False
) -> Dict[str, Any]:
    """
    Create a custom linting rule.

    Example:
    - Rule: "No console.log in production"
    - Pattern: "console.log($$$)"
    - Severity: "error"
    - Fix: "Remove or replace with proper logging"

    Can save rules to .ast-grep-rules/ for reuse.
    """
```

**2. `enforce_standards` - Check Code Quality**
```python
def enforce_standards(
    project_folder: str,
    language: str,
    rule_set: str = "recommended",
    custom_rules: Optional[List[str]] = None,
    auto_fix: bool = False,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    Enforce coding standards using rule sets.

    Rule sets:
    - recommended: General best practices
    - security: Security-focused rules
    - performance: Performance anti-patterns
    - team_standards: Load from .ast-grep-rules/
    - custom: Specific rule IDs

    Returns violations with locations and suggested fixes.
    """
```

**3. `detect_security_issues` - Security Scanning**
```python
def detect_security_issues(
    project_folder: str,
    language: str,
    issue_types: List[str] = ["all"],
    severity_threshold: str = "medium",
    include_false_positives: bool = False
) -> Dict[str, Any]:
    """
    Scan for security vulnerabilities.

    Issue types:
    - sql_injection: Unsanitized SQL queries
    - xss: Cross-site scripting risks
    - command_injection: Shell command injection
    - path_traversal: Unsafe file path handling
    - hardcoded_secrets: API keys, passwords in code
    - insecure_crypto: Weak cryptography
    - unsafe_deserialization: Pickle, eval() usage

    Returns findings with severity and remediation steps.
    """
```

**4. `apply_standards_fixes` - Auto-Fix Violations**
```python
def apply_standards_fixes(
    project_folder: str,
    violations: List[Dict[str, Any]],
    fix_types: List[str] = ["safe"],
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Automatically fix code quality violations.

    Fix types:
    - safe: Only apply guaranteed-safe fixes
    - suggested: Apply recommended fixes (may need review)
    - all: Apply all available fixes

    Returns diff preview and applies fixes if not dry_run.
    """
```

**5. `generate_quality_report` - Quality Dashboard**
```python
def generate_quality_report(
    project_folder: str,
    language: str,
    report_type: str = "comprehensive",
    compare_to_baseline: bool = False
) -> Dict[str, Any]:
    """
    Generate code quality report.

    Includes:
    - Standards violations summary
    - Security issues summary
    - Trends (if baseline exists)
    - Top issues by severity
    - Auto-fix coverage

    Output: Markdown, HTML, or JSON
    """
```

---

## Implementation Phases

### Phase 1: Rule Definition System ✅ COMPLETE (Week 1-2, Size: L)

**Status:** ✅ Complete (2025-11-24)

**Goal:** Create infrastructure for defining and managing custom rules.

**Deliverables:**
1. ✅ Rule schema definition (YAML format) - LintingRule, RuleTemplate data classes
2. ✅ Rule validation system - _validate_rule_definition() with comprehensive checks
3. ✅ Rule storage (.ast-grep-rules/ directory) - _save_rule_to_project(), _load_rule_from_file()
4. ✅ Rule template library (common patterns) - RULE_TEMPLATES with 23 rules across 4 languages
5. ✅ `create_linting_rule` MCP tool - Full implementation with validation and storage

**Key Technical Challenges:**
- ✅ Design flexible rule schema - Supports pattern, constraints, fix suggestions
- ✅ Validate ast-grep patterns - Pattern syntax validation, constraint validation
- ✅ Organize rules by category - Categories: security, code-quality, style, best-practices
- ✅ Version control for rules - Stored in .ast-grep-rules/ for git tracking

**Success Criteria:**
- ✅ Rules are easy to define - Simple YAML format with clear schema
- ✅ Pattern validation works - Comprehensive validation with error messages
- ✅ Rules can be shared across projects - Portable YAML files
- ✅ Template library has 20+ rules - 23 rules across Python, JavaScript, TypeScript, Java

**Implementation Details:**
- **Lines Added:** ~1,100 lines to main.py
- **Data Classes:** LintingRule, RuleTemplate, RuleValidationResult
- **Functions:** create_linting_rule(), _validate_rule_definition(), _save_rule_to_project(), _load_rule_from_file(), _get_available_templates()
- **Rule Templates:** 23 rules covering security, code quality, style, and best practices
- **Languages Supported:** Python (7 rules), JavaScript/TypeScript (11 rules), Java (5 rules)

**Example Rule:**
```yaml
id: no-console-log-production
language: javascript
severity: error
message: "console.log() should not be used in production code"
note: "Use a proper logging library instead"
pattern: console.log($$$)
fix: |
  # Suggest replacement with logger
  logger.debug($$$)
constraints:
  # Only apply in non-test files
  path:
    not: "**/*.test.js"
```

---

### Phase 2: Standards Enforcement Engine (Week 2-3, Size: L)

**Status:** 🚧 In Progress - Phase 2A Complete (2025-11-24)

**Goal:** Implement rule execution and violation reporting.

**Deliverables:**
1. ✅ Rule set manager (recommended, security, etc.) - Phase 2A Complete
   - RULE_SETS configuration with 4 built-in sets
   - _load_rule_set() function for loading rule sets
   - Support for 'all', 'custom', and built-in sets
2. ⏳ Batch rule executor - Phase 2B In Progress
3. ⏳ Violation reporter - Phase 2B In Progress
4. ⏳ Severity scorer - Phase 2B In Progress
5. ⏳ `enforce_standards` MCP tool - Phase 2B In Progress

**Phase 2A: Core Infrastructure ✅ COMPLETE**
- **Lines Added:** ~276 lines (lines 18574-18846 in main.py)
- **Data Classes Added:**
  - RuleViolation - Single violation with location, severity, message, fix suggestion
  - RuleSet - Collection of rules with metadata and priority
  - EnforcementResult - Complete scan results with groupings and statistics
  - RuleExecutionContext - Internal execution context
- **Configuration Added:**
  - RULE_SETS: 4 built-in rule sets (recommended, security, performance, style)
  - Priority system: security (200), recommended (100), performance (50), style (10)
- **Helper Functions Added:**
  - _template_to_linting_rule() - Convert templates to rules
  - _load_custom_rules() - Load from .ast-grep-rules/ directory
  - _load_rule_set() - Load built-in or custom rule sets
- **Testing:**
  - ✅ All imports successful
  - ✅ Data classes properly typed
  - ✅ Helper functions work correctly
  - ✅ Rule set loading tested (all, custom, built-in)
  - ✅ Error handling validated
  - ✅ No regressions (57 existing unit tests pass)

**Phase 2B: Rule Execution (Next)**
- Rule execution engine
- Violation collection and aggregation
- Parallel execution with ThreadPoolExecutor
- Severity scoring and prioritization
- Main `enforce_standards` MCP tool

**Success Criteria:**
- ✅ Rule set infrastructure in place
- ⏳ Executes 50+ rules in <30s
- ⏳ Clear violation reports
- ✅ Supports custom rule sets
- ⏳ Integrates with existing tools

---

### Phase 3: Security Scanner (Week 3-5, Size: XL)

**Goal:** Implement security vulnerability detection.

**Deliverables:**
1. SQL injection detector
2. XSS vulnerability detector
3. Command injection detector
4. Hardcoded secret scanner
5. Insecure crypto detector
6. `detect_security_issues` MCP tool

**Key Technical Challenges:**
- Balance false positives vs. false negatives
- Understand data flow (taint analysis)
- Language-specific vulnerabilities
- Keep vulnerability patterns updated

**Success Criteria:**
- Detects 7+ vulnerability types
- <30% false positive rate
- Clear remediation guidance
- Severity scoring accurate

**Example Detections:**
```python
# SQL Injection
cursor.execute(f"SELECT * FROM users WHERE name = '{user_input}'")  # VULNERABLE
cursor.execute("SELECT * FROM users WHERE name = ?", (user_input,))  # SAFE

# XSS
html = f"<div>{user_input}</div>"  # VULNERABLE
html = f"<div>{escape(user_input)}</div>"  # SAFE

# Command Injection
os.system(f"ls {user_input}")  # VULNERABLE
subprocess.run(["ls", user_input])  # SAFE

# Hardcoded Secrets
api_key = "sk-1234567890abcdef"  # VULNERABLE
api_key = os.environ.get("API_KEY")  # SAFE
```

---

### Phase 4: Auto-Fix System (Week 5-6, Size: L)

**Goal:** Automatically fix detected violations.

**Deliverables:**
1. Safe fix applicator (guaranteed-safe fixes)
2. Suggested fix applicator (may need review)
3. Fix validation system
4. Multi-fix coordinator
5. `apply_standards_fixes` MCP tool

**Success Criteria:**
- Applies fixes without breaking code
- Syntax validation passes
- Behavior preserved
- Clear diff preview

---

### Phase 5: Quality Reporting (Week 6, Size: M)

**Goal:** Generate comprehensive quality reports.

**Deliverables:**
1. Report generator (Markdown, HTML, JSON)
2. Trend tracking (baseline comparison)
3. Dashboard visualizations
4. CI/CD integration guide
5. `generate_quality_report` MCP tool

**Success Criteria:**
- Professional report format
- Trend tracking works
- Easy CI/CD integration
- Actionable insights

---

### Phase 6: Testing & Documentation (Week 7, Size: M)

**Goal:** Comprehensive testing and documentation.

**Deliverables:**
1. 100+ test cases
2. Rule library documentation
3. Security scanning guide
4. CI/CD integration examples

**Success Criteria:**
- >95% test coverage
- All documentation complete
- Example integrations work

---

## Pre-Built Rule Sets

### Recommended Rules (General Best Practices)

**JavaScript/TypeScript:**
- No var (use const/let)
- No == (use ===)
- No console.log in production
- Prefer const over let
- No unused variables
- No empty catch blocks
- Proper error handling

**Python:**
- No bare except
- No mutable default arguments
- No eval() or exec()
- Proper with statement usage
- No print() in production (use logging)
- Type hints for public functions

**Java:**
- No System.out.println (use logging)
- Proper exception handling
- No empty catch blocks
- Use try-with-resources
- No raw types

### Security Rules

**SQL Injection:**
- No string concatenation in queries
- Require parameterized queries
- Flag dynamic SQL

**XSS:**
- No unescaped user input in HTML
- Require sanitization
- Flag innerHTML usage

**Command Injection:**
- No shell=True with user input
- Require subprocess array form
- Flag os.system() usage

**Secrets:**
- No hardcoded passwords
- No API keys in code
- Flag suspicious patterns (sk-, Bearer, etc.)

**Crypto:**
- No MD5/SHA1 for passwords
- Require bcrypt/argon2
- Flag weak SSL/TLS

---

## Success Metrics

**Accuracy:**
- Rule execution: 100% pattern match
- Security detection: <30% false positives
- Auto-fix success: >90%

**Performance:**
- 50 rules on 1000 files: <60s
- Security scan: <120s
- Report generation: <10s

**Coverage:**
- Rule library: 50+ rules
- Security patterns: 20+ vulnerabilities
- Languages: Python, TypeScript, Java

---

## Risk Assessment

**Risk 1: False Positives in Security Scanning** (High Impact)
- **Mitigation:** Conservative patterns, confidence scoring, manual review

**Risk 2: Breaking Changes from Auto-Fix** (High Impact)
- **Mitigation:** Dry-run default, syntax validation, test integration

**Risk 3: Performance on Large Codebases** (Medium Impact)
- **Mitigation:** Incremental scanning, caching, parallel execution

---

## Timeline

- **Week 1-2:** Phase 1 (Rule Definition)
- **Week 2-3:** Phase 2 (Standards Enforcement)
- **Week 3-5:** Phase 3 (Security Scanner)
- **Week 5-6:** Phase 4 (Auto-Fix)
- **Week 6:** Phase 5 (Quality Reporting)
- **Week 7:** Phase 6 (Testing & Docs)

**Total:** 5-7 weeks

---

**End of Plan**
**Last Updated:** 2025-11-18
