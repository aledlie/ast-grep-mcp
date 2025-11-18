# ast-grep-mcp New Features - Overview

**Last Updated:** 2025-11-18
**Status:** Planning Complete
**Next Step:** Prioritize and begin implementation

---

## Executive Summary

This document provides a high-level overview of 6 major feature areas planned for the ast-grep-mcp server. All detailed plans have been created and are ready for implementation.

**Total Planning Documents:** 6 comprehensive strategic plans
**Total Estimated Effort:** 31-43 weeks (7-10 months for one developer)
**Recommended Approach:** Prioritize and implement incrementally

---

## Feature Areas Overview

### 1. Enhanced Duplication Detection ⭐ **HIGHEST PRIORITY**

**Location:** `dev/active/enhanced-duplication-detection/`
**Status:** Planning complete, ready to start
**Effort:** 4-6 weeks
**Risk:** Medium
**Impact:** High

**What It Does:**
- Move from passive "here are duplicates" to active "here's the refactored code"
- Intelligent parameter extraction from duplicate code
- Automated deduplication with preview and rollback
- Concrete refactoring code generation (not just suggestions)

**New MCP Tools:**
- `find_duplication` (enhanced) - Add intelligent analysis mode
- `apply_deduplication` - Auto-apply refactorings with safety
- `analyze_deduplication_candidates` - Prioritize best opportunities

**Why Prioritize:**
- Builds on existing solid foundation (`find_duplication` already works)
- High developer productivity impact (70-80% time savings)
- Clear user value proposition
- Reuses existing backup/rollback infrastructure

**Example Workflow:**
```python
# 1. Find duplicates with intelligent analysis
result = find_duplication(project_folder="/path", language="python", analysis_mode="detailed")

# 2. Preview automated refactoring
preview = apply_deduplication(group_id=1, refactoring_plan=result["suggestions"][0], dry_run=True)

# 3. Apply with one command
apply_deduplication(group_id=1, refactoring_plan=result["suggestions"][0], dry_run=False)
# Auto-creates backup, extracts function, replaces duplicates, validates syntax
```

---

### 2. Refactoring Assistants

**Location:** `dev/active/refactoring-assistants/`
**Effort:** 6-8 weeks
**Risk:** Medium-High
**Impact:** High

**What It Does:**
- Extract functions/methods from selected code
- Rename symbols safely across entire codebase
- Convert between code styles (class ↔ functional, promise ↔ async/await)
- Simplify complex conditional logic
- Batch multiple refactorings atomically

**New MCP Tools:**
- `extract_function` - Intelligent function extraction with parameter detection
- `rename_symbol` - Scope-aware symbol renaming
- `convert_code_style` - Pattern conversions (6+ types)
- `simplify_conditionals` - Reduce complexity
- `refactor_batch` - Atomic multi-step refactorings

**Why Valuable:**
- Automates tedious manual refactoring
- Ensures behavior preservation
- Teaches best practices through automation
- 60-70% faster refactoring workflows

**Example:**
```python
# Extract function with auto-detected parameters
extract_function(
    file_path="app.py",
    start_line=45,
    end_line=52,
    function_name="validate_email"  # Optional, can auto-generate
)
# Auto-detects: parameters needed, return values, proper location
```

---

### 3. Code Analysis & Metrics

**Location:** `dev/active/code-analysis-metrics/`
**Effort:** 5-7 weeks
**Risk:** Low-Medium
**Impact:** Medium-High

**What It Does:**
- Calculate cyclomatic complexity and nesting depth
- Detect code smells (long functions, parameter bloat, etc.)
- Analyze dependency graphs and circular dependencies
- Identify dead/unused code
- Track metrics over time

**New MCP Tools:**
- `analyze_complexity` - Complexity metrics (cyclomatic, nesting, etc.)
- `detect_code_smells` - Common anti-patterns (7+ types)
- `analyze_dependencies` - Import graphs and circular dependencies
- `find_dead_code` - Unused functions, variables, imports
- `generate_metrics_report` - Comprehensive quality dashboard

**Why Valuable:**
- Data-driven refactoring priorities
- Objective code review metrics
- Early detection of technical debt
- Team alignment on quality standards

**Example:**
```python
# Find high-complexity functions
result = analyze_complexity(
    project_folder="/path",
    language="python",
    threshold_cyclomatic=10
)
# Returns: Functions exceeding thresholds, complexity distribution, recommendations
```

---

### 4. Documentation Generation

**Location:** `dev/active/documentation-generation/`
**Effort:** 4-6 weeks
**Risk:** Low
**Impact:** Medium

**What It Does:**
- Auto-generate docstrings/JSDoc from function signatures
- Create README sections from code structure
- Build API documentation from route definitions
- Generate changelogs from git commits
- Keep documentation synchronized with code

**New MCP Tools:**
- `generate_docstrings` - Auto-create function documentation
- `generate_readme_sections` - README automation (6+ sections)
- `generate_api_docs` - OpenAPI/Markdown from routes
- `generate_changelog` - Conventional commits → changelog
- `sync_documentation` - Keep docs current

**Why Valuable:**
- 70-80% reduction in documentation time
- Consistent documentation style
- Never outdated (can auto-regenerate)
- Lower barrier to documentation

**Example:**
```python
# Generate missing docstrings
generate_docstrings(
    project_folder="/path",
    file_pattern="src/**/*.py",
    language="python",
    style="google"
)
# Adds Google-style docstrings to all undocumented functions
```

---

### 5. Code Quality & Standards

**Location:** `dev/active/code-quality-standards/`
**Effort:** 5-7 weeks
**Risk:** Medium
**Impact:** Medium-High

**What It Does:**
- Define custom linting rules via ast-grep patterns
- Enforce team-specific coding standards
- Scan for security vulnerabilities (SQL injection, XSS, etc.)
- Auto-fix violations with safety checks
- Generate quality reports

**New MCP Tools:**
- `create_linting_rule` - Define custom rules
- `enforce_standards` - Check against rule sets
- `detect_security_issues` - Scan for vulnerabilities (7+ types)
- `apply_standards_fixes` - Auto-fix violations
- `generate_quality_report` - Quality dashboard

**Why Valuable:**
- Systematic standards enforcement
- Early security vulnerability detection
- Automated onboarding (rules teach patterns)
- Team-wide consistency

**Example:**
```python
# Scan for security issues
result = detect_security_issues(
    project_folder="/path",
    language="python",
    issue_types=["sql_injection", "xss", "hardcoded_secrets"]
)
# Returns: Vulnerabilities with severity and remediation steps
```

---

### 6. Cross-Language Operations

**Location:** `dev/active/cross-language-operations/`
**Effort:** 7-9 weeks
**Risk:** High
**Impact:** Medium (specialized use cases)

**What It Does:**
- Search across multiple languages simultaneously
- Convert code between languages (Python → TypeScript, etc.)
- Find equivalent patterns across languages
- Refactor across language boundaries (rename API across frontend/backend)
- Generate API client bindings for multiple languages

**New MCP Tools:**
- `search_multi_language` - Polyglot search with semantic grouping
- `convert_code_language` - Language conversion (3+ pairs)
- `find_language_equivalents` - Pattern equivalence mapping
- `refactor_polyglot` - Cross-language refactoring
- `generate_language_bindings` - API client generation

**Why Valuable:**
- Supports polyglot development
- Assists language migrations
- Generates client libraries automatically
- Learning tool (see patterns across languages)

**Example:**
```python
# Convert Python to TypeScript
convert_code_language(
    code_snippet=python_function,
    from_language="python",
    to_language="typescript",
    conversion_style="idiomatic"
)
# Returns: Idiomatic TypeScript equivalent with conversion notes
```

---

## Recommended Prioritization

### Phase 1: Quick Wins (Weeks 1-10)
**Start with:** Enhanced Duplication Detection (4-6 weeks)
- Builds on existing solid foundation
- Clear ROI
- Low risk
- High user demand

**Then:** Documentation Generation (4-6 weeks)
- Low risk
- High value
- Complements duplication work

**Rationale:** Fast time to value, low risk, builds momentum

---

### Phase 2: High-Impact Features (Weeks 11-24)
**Next:** Refactoring Assistants (6-8 weeks)
- High developer productivity impact
- Natural progression from duplication detection
- Shares infrastructure

**Then:** Code Analysis & Metrics (5-7 weeks)
- Data-driven insights complement refactoring tools
- Clear quality improvements
- Enables better prioritization

**Rationale:** Maximum productivity gains for developers

---

### Phase 3: Advanced Features (Weeks 25-35)
**Next:** Code Quality & Standards (5-7 weeks)
- Prevents problems detected by analysis tools
- Security value proposition
- Team-wide benefits

**Then:** Cross-Language Operations (7-9 weeks) - **Optional**
- More specialized
- High complexity
- Defer if resources constrained

**Rationale:** Systematic quality enforcement, specialized needs

---

## Alternative Prioritization Strategies

### Strategy A: Security-Focused
1. Code Quality & Standards (security scanning) - 5-7 weeks
2. Enhanced Duplication Detection - 4-6 weeks
3. Code Analysis & Metrics - 5-7 weeks
4. Refactoring Assistants - 6-8 weeks

**Use When:** Security is top priority

---

### Strategy B: Quick Documentation Wins
1. Documentation Generation - 4-6 weeks
2. Enhanced Duplication Detection - 4-6 weeks
3. Refactoring Assistants - 6-8 weeks

**Use When:** Documentation debt is high

---

### Strategy C: Full-Stack Polyglot Teams
1. Cross-Language Operations - 7-9 weeks
2. Refactoring Assistants - 6-8 weeks
3. Documentation Generation - 4-6 weeks

**Use When:** Multi-language codebases are primary use case

---

## Success Metrics Across All Features

### Productivity Metrics
- **Refactoring time:** Reduce by 60-80%
- **Documentation time:** Reduce by 70-80%
- **Code review time:** Reduce by 30-40% (automated checks)
- **Bug detection:** Increase by 50%+ (security, dead code, complexity)

### Quality Metrics
- **Test coverage:** Increase (better refactoring enables testing)
- **Code duplication:** Reduce by 40-60%
- **Cyclomatic complexity:** Reduce by 30%+
- **Documentation coverage:** Increase to 80%+

### Developer Experience
- **Onboarding time:** Reduce by 40% (automated enforcement teaches patterns)
- **Learning:** Cross-language learning via equivalence mapping
- **Confidence:** Safe refactoring with preview/rollback

---

## Implementation Recommendations

### Parallel Development Strategy
If multiple developers available, consider:
- **Developer 1:** Enhanced Duplication Detection (4-6 weeks)
- **Developer 2:** Documentation Generation (4-6 weeks)
- **Total time:** 4-6 weeks (parallel) vs. 8-12 weeks (sequential)

### Incremental Delivery
- Ship minimal viable version of each tool first
- Gather user feedback
- Iterate and add advanced features
- Example: Ship `extract_function` basic version before `refactor_batch`

### Infrastructure Reuse
Many features share infrastructure:
- Backup/rollback system (already exists)
- AST parsing (ast-grep integration)
- Syntax validation (already exists)
- Diff generation
- Sentry error tracking

**Recommendation:** Build shared utilities first, reuse aggressively

---

## Next Steps

1. **Review Plans:** Read detailed plans for prioritized features
2. **Finalize Priority:** Choose strategy (recommended: Phase 1 → Phase 2 → Phase 3)
3. **Start Implementation:** Begin with Enhanced Duplication Detection
4. **Iterate:** Ship MVP, gather feedback, improve

---

## Planning Documents Index

All plans are comprehensive and ready for implementation:

1. **Enhanced Duplication Detection** ⭐
   - Plan: `dev/active/enhanced-duplication-detection/enhanced-duplication-detection-plan.md` (34KB)
   - Context: `enhanced-duplication-detection-context.md` (14KB)
   - Tasks: `enhanced-duplication-detection-tasks.md` (11KB)

2. **Code Analysis & Metrics**
   - Plan: `dev/active/code-analysis-metrics/code-analysis-metrics-plan.md`

3. **Refactoring Assistants**
   - Plan: `dev/active/refactoring-assistants/refactoring-assistants-plan.md`

4. **Documentation Generation**
   - Plan: `dev/active/documentation-generation/documentation-generation-plan.md`

5. **Code Quality & Standards**
   - Plan: `dev/active/code-quality-standards/code-quality-standards-plan.md`

6. **Cross-Language Operations**
   - Plan: `dev/active/cross-language-operations/cross-language-operations-plan.md`

---

**Total Documentation:** ~100KB of detailed strategic plans, task breakdowns, technical designs, and risk assessments.

**Status:** Ready to begin implementation.
**Recommended Start:** Enhanced Duplication Detection (dev/active/enhanced-duplication-detection/)

---

**Last Updated:** 2025-11-18
**Prepared By:** Strategic Planning Assistant
