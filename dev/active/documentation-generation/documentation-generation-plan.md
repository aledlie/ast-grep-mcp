# Documentation Generation - Strategic Plan

**Last Updated:** 2025-11-18
**Status:** Planning
**Owner:** Development Team
**Priority:** Medium

---

## Executive Summary

This plan outlines the creation of automated documentation generation tools that create high-quality documentation from code structure, comments, and git history, reducing manual documentation burden while improving consistency and coverage.

**Current State:** No automated documentation generation in MCP server.

**Proposed State:** Intelligent documentation tools that:
1. Auto-generate JSDoc/docstrings from function signatures
2. Create README sections from code structure analysis
3. Build API documentation from route definitions
4. Generate changelogs from git commits and code changes
5. Keep documentation in sync with code
6. Support multiple output formats (Markdown, HTML, JSON)

**Expected Impact:**
- **Time Savings:** 70-80% reduction in documentation effort
- **Consistency:** Uniform documentation style across projects
- **Coverage:** Higher documentation coverage rates
- **Freshness:** Auto-update docs when code changes

**Effort Estimate:** 4-6 weeks (L-XL)
**Risk Level:** Low (clear problem space, no behavior changes)

---

## Current State Analysis

### Existing Capabilities

**Code Analysis:**
- ✅ ast-grep pattern matching
- ✅ Function/class extraction
- ✅ Multi-language support

**Limitations:**
- ❌ No documentation generation
- ❌ No comment/docstring analysis
- ❌ No git integration for changelogs
- ❌ No README generation

---

## Proposed Future State

### New MCP Tools

**1. `generate_docstrings` - Auto-Generate Documentation**
```python
def generate_docstrings(
    project_folder: str,
    file_pattern: str,
    language: str,
    style: str = "auto",
    overwrite_existing: bool = False,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Generate docstrings/JSDoc for undocumented functions.

    Styles:
    - google (Python)
    - numpy (Python)
    - sphinx (Python)
    - jsdoc (JavaScript/TypeScript)
    - javadoc (Java)
    - auto (detect from project)

    Generates:
    - Function description (inferred from name)
    - Parameter descriptions (inferred from types/names)
    - Return value description
    - Example usage (optional)

    Returns preview or applies changes.
    """
```

**2. `generate_readme_sections` - README Generation**
```python
def generate_readme_sections(
    project_folder: str,
    language: str,
    sections: List[str] = ["all"],
    include_examples: bool = True
) -> Dict[str, Any]:
    """
    Generate README.md sections from code analysis.

    Sections:
    - installation: Detect package manager, create install steps
    - usage: Extract main entry points, create examples
    - api: Document public functions/classes
    - structure: Visualize project structure
    - features: List based on code analysis
    - contributing: Generate from code style analysis

    Returns generated Markdown sections.
    """
```

**3. `generate_api_docs` - API Documentation**
```python
def generate_api_docs(
    project_folder: str,
    language: str,
    framework: Optional[str] = None,
    output_format: str = "markdown",
    include_examples: bool = True
) -> Dict[str, Any]:
    """
    Generate API documentation from route definitions.

    Frameworks supported:
    - express (Node.js)
    - flask/fastapi (Python)
    - spring (Java)
    - auto-detect

    Generates:
    - Endpoint list with methods (GET, POST, etc.)
    - Request/response schemas
    - Authentication requirements
    - Example requests/responses
    - Error codes

    Output formats: markdown, html, openapi/swagger
    """
```

**4. `generate_changelog` - Changelog Generation**
```python
def generate_changelog(
    project_folder: str,
    from_version: Optional[str] = None,
    to_version: str = "HEAD",
    changelog_format: str = "keepachangelog",
    group_by: str = "type"
) -> Dict[str, Any]:
    """
    Generate changelog from git commits and code changes.

    Features:
    - Parse conventional commits
    - Detect breaking changes
    - Group by type (feat, fix, docs, etc.)
    - Link to issues/PRs
    - Detect code additions/removals

    Formats:
    - keepachangelog (Markdown)
    - conventional (Markdown)
    - json

    Returns formatted changelog.
    """
```

**5. `sync_documentation` - Keep Docs Updated**
```python
def sync_documentation(
    project_folder: str,
    doc_types: List[str] = ["all"],
    check_only: bool = False
) -> Dict[str, Any]:
    """
    Synchronize documentation with code.

    Checks:
    - Undocumented functions
    - Stale docstrings (params don't match signature)
    - Missing API endpoints in docs
    - Outdated examples
    - Broken links

    Actions:
    - Update docstrings
    - Add missing API docs
    - Flag manual review items

    Returns sync report and suggested changes.
    """
```

---

## Implementation Phases

### Phase 1: Docstring Generation (Week 1-2, Size: L)

**Goal:** Auto-generate docstrings from function signatures and names.

**Deliverables:**
1. Function signature parser
2. Parameter description generator
3. Return type analyzer
4. Docstring template system (multiple styles)
5. `generate_docstrings` MCP tool

**Key Technical Challenges:**
- Infer meaningful descriptions from names
- Handle type annotations across languages
- Support multiple docstring styles
- Preserve existing partial docs

**Success Criteria:**
- Generates valid docstrings for 95%+ of functions
- Supports 3+ languages (Python, TypeScript, Java)
- Supports 3+ docstring styles
- Doesn't overwrite good existing docs

**Example Output:**
```python
# Before
def calculate_tax(amount, rate):
    return amount * rate

# After
def calculate_tax(amount, rate):
    """
    Calculate tax amount based on a given rate.

    Args:
        amount (float): The base amount to calculate tax on.
        rate (float): The tax rate as a decimal (e.g., 0.08 for 8%).

    Returns:
        float: The calculated tax amount.

    Example:
        >>> calculate_tax(100.0, 0.08)
        8.0
    """
    return amount * rate
```

---

### Phase 2: README Generation (Week 2-3, Size: M)

**Goal:** Generate README sections from code analysis.

**Deliverables:**
1. Project structure analyzer
2. Entry point detector
3. Feature list generator
4. Usage example generator
5. `generate_readme_sections` MCP tool

**Success Criteria:**
- Generates 6+ README sections
- Detects package manager correctly
- Creates valid usage examples
- Professional markdown formatting

---

### Phase 3: API Documentation (Week 3-4, Size: L)

**Goal:** Extract and document API endpoints.

**Deliverables:**
1. Route definition parser (Express, Flask, FastAPI)
2. Request/response schema extractor
3. OpenAPI/Swagger generator
4. Markdown API doc generator
5. `generate_api_docs` MCP tool

**Success Criteria:**
- Parses routes from 3+ frameworks
- Generates valid OpenAPI 3.0 spec
- Creates human-readable markdown docs
- Includes request/response examples

**Example Output:**
```markdown
## API Endpoints

### POST /api/users
Create a new user account.

**Request Body:**
```json
{
  "name": "string (required)",
  "email": "string (required)",
  "age": "number (optional)"
}
```

**Response (201 Created):**
```json
{
  "id": "string",
  "name": "string",
  "email": "string",
  "createdAt": "string (ISO 8601)"
}
```

**Errors:**
- 400: Invalid request body
- 409: Email already exists
```

---

### Phase 4: Changelog Generation (Week 4-5, Size: M)

**Goal:** Generate changelogs from git history and code changes.

**Deliverables:**
1. Git commit parser (conventional commits)
2. Breaking change detector
3. Code change analyzer (additions/removals)
4. Changelog formatter (Keep a Changelog)
5. `generate_changelog` MCP tool

**Success Criteria:**
- Parses conventional commits correctly
- Detects breaking changes
- Groups changes by type
- Generates valid markdown

**Example Output:**
```markdown
# Changelog

## [2.0.0] - 2025-11-18

### Added
- New `analyze_complexity` tool for code metrics
- Support for Java and TypeScript in duplication detection

### Changed
- **BREAKING:** `find_duplication` now requires `language` parameter
- Improved performance of dependency analysis by 50%

### Fixed
- Fixed incorrect parameter extraction for nested functions
- Resolved issue with circular dependency detection

### Removed
- **BREAKING:** Removed deprecated `find_code_v1` tool
```

---

### Phase 5: Documentation Sync (Week 5, Size: M)

**Goal:** Keep documentation synchronized with code.

**Deliverables:**
1. Stale docstring detector
2. Undocumented function finder
3. API docs consistency checker
4. Auto-update suggestions
5. `sync_documentation` MCP tool

**Success Criteria:**
- Detects 100% of signature mismatches
- Finds all undocumented functions
- Suggests concrete updates
- Non-destructive (preview mode)

---

### Phase 6: Testing & Documentation (Week 6, Size: M)

**Goal:** Comprehensive testing and documentation.

**Deliverables:**
1. 80+ test cases
2. Documentation updates
3. Example gallery

**Success Criteria:**
- >95% test coverage
- All documentation complete
- Examples comprehensive

---

## Detailed Task Breakdown

### Phase 1: Docstring Generation

**1.1 Function Signature Parser (Size: M)**
- [ ] Extract function name, parameters, return type
- [ ] Handle type annotations (Python, TypeScript)
- [ ] Handle default values
- [ ] Handle variadic parameters (*args, **kwargs)
- [ ] Unit tests

**1.2 Description Generator (Size: M)**
- [ ] Infer description from function name (camelCase, snake_case)
- [ ] Use parameter names for hints
- [ ] Handle common patterns (get_, set_, calculate_, etc.)
- [ ] Unit tests with various naming patterns

**1.3 Docstring Template System (Size: M)**
- [ ] Google-style template (Python)
- [ ] NumPy-style template (Python)
- [ ] JSDoc template (JavaScript/TypeScript)
- [ ] Javadoc template (Java)
- [ ] Template rendering engine
- [ ] Unit tests for each style

**1.4 Generate Docstrings Tool (Size: M)**
- [ ] Create `generate_docstrings` MCP tool
- [ ] Integrate parser and generators
- [ ] Add overwrite protection
- [ ] Dry-run mode
- [ ] Integration tests

---

### Phase 2: README Generation

**2.1 Project Structure Analyzer (Size: M)**
- [ ] Detect directory structure
- [ ] Identify entry points (main, index, app)
- [ ] Detect package manager (package.json, requirements.txt, etc.)
- [ ] Identify framework (React, Flask, Spring, etc.)
- [ ] Unit tests

**2.2 Feature List Generator (Size: S)**
- [ ] Analyze exported functions
- [ ] Analyze API routes
- [ ] Group by category
- [ ] Generate feature descriptions
- [ ] Unit tests

**2.3 Usage Example Generator (Size: M)**
- [ ] Extract public API
- [ ] Generate code examples
- [ ] Add install instructions
- [ ] Unit tests

**2.4 Generate README Tool (Size: M)**
- [ ] Create `generate_readme_sections` MCP tool
- [ ] Integrate analyzers
- [ ] Format markdown
- [ ] Integration tests

---

### Phase 3: API Documentation

**3.1 Route Parser (Size: L)**
- [ ] Parse Express routes (app.get, router.post)
- [ ] Parse Flask/FastAPI routes (@app.route, @router.get)
- [ ] Parse Spring routes (@GetMapping, @PostMapping)
- [ ] Extract route paths, methods, handlers
- [ ] Unit tests per framework

**3.2 Schema Extractor (Size: M)**
- [ ] Extract request body schemas (Joi, Zod, Pydantic)
- [ ] Extract response schemas
- [ ] Infer schemas from code if not explicit
- [ ] Unit tests

**3.3 OpenAPI Generator (Size: M)**
- [ ] Generate OpenAPI 3.0 spec
- [ ] Add paths, schemas, responses
- [ ] Add authentication info
- [ ] Validate generated spec
- [ ] Unit tests

**3.4 Generate API Docs Tool (Size: M)**
- [ ] Create `generate_api_docs` MCP tool
- [ ] Integrate parsers
- [ ] Support multiple formats
- [ ] Integration tests

---

### Phase 4: Changelog Generation

**4.1 Git Commit Parser (Size: M)**
- [ ] Execute git log commands
- [ ] Parse conventional commits (type(scope): message)
- [ ] Extract breaking changes (BREAKING CHANGE:)
- [ ] Link to issues (#123) and PRs
- [ ] Unit tests with mock git output

**4.2 Code Change Analyzer (Size: M)**
- [ ] Use git diff to detect additions/removals
- [ ] Categorize changes (new features, deprecations)
- [ ] Unit tests

**4.3 Changelog Formatter (Size: S)**
- [ ] Keep a Changelog format
- [ ] Group by type (Added, Changed, Fixed, Removed)
- [ ] Sort by importance
- [ ] Unit tests

**4.4 Generate Changelog Tool (Size: M)**
- [ ] Create `generate_changelog` MCP tool
- [ ] Integrate git parser
- [ ] Integration tests

---

## Success Metrics

**Accuracy:**
- Docstring generation: >90% meaningful
- API docs: 100% endpoint coverage
- Changelog: 100% commit coverage
- README: Accurate project structure

**Usability:**
- Clear, professional output
- Multiple format support
- Easy customization
- Non-destructive defaults

**Coverage:**
- Languages: Python, TypeScript, Java
- Frameworks: Express, Flask, FastAPI, Spring
- Docstring styles: 4+

---

## Risk Assessment

**Risk 1: Generated Docs Are Generic** (Medium Impact)
- **Mitigation:** Smart inference from names, allow customization, human review step

**Risk 2: Framework Detection Failures** (Low Impact)
- **Mitigation:** Manual framework specification, graceful degradation

---

## Timeline

- **Week 1-2:** Phase 1 (Docstring Generation)
- **Week 2-3:** Phase 2 (README Generation)
- **Week 3-4:** Phase 3 (API Documentation)
- **Week 4-5:** Phase 4 (Changelog Generation)
- **Week 5:** Phase 5 (Documentation Sync)
- **Week 6:** Phase 6 (Testing & Docs)

**Total:** 4-6 weeks

---

**End of Plan**
**Last Updated:** 2025-11-18
