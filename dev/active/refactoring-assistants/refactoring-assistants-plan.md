# Refactoring Assistants - Strategic Plan

**Last Updated:** 2025-11-18
**Status:** Planning
**Owner:** Development Team
**Priority:** High

---

## Executive Summary

This plan outlines the creation of intelligent refactoring assistant tools that automate common code transformations, moving beyond simple find-and-replace to structure-aware refactorings that preserve code behavior.

**Current State:** Basic `rewrite_code` tool with YAML rules and manual refactoring.

**Proposed State:** Intelligent refactoring assistants that:
1. Extract functions/methods from selected code
2. Rename symbols safely across entire codebase
3. Convert between code styles (class ↔ functional, etc.)
4. Simplify complex conditional logic automatically
5. Apply multiple refactorings atomically with preview
6. Validate behavior preservation via tests

**Expected Impact:**
- **Development Speed:** 60-70% faster refactoring workflows
- **Code Quality:** Systematic application of best practices
- **Safety:** Behavior-preserving transformations with validation
- **Learning:** Developers learn patterns from AI refactorings

**Effort Estimate:** 6-8 weeks (XL)
**Risk Level:** Medium-High (requires correct behavior preservation)

---

## Current State Analysis

### Existing Capabilities

**Code Rewrite Infrastructure:**
- ✅ `rewrite_code()` tool with ast-grep YAML rules
- ✅ Backup system with rollback capability
- ✅ Syntax validation (Python, JS/TS)
- ✅ Dry-run preview mode

**Limitations:**
- ❌ Requires manual YAML rule creation
- ❌ No intelligent code selection
- ❌ No scope analysis
- ❌ No automatic parameter detection
- ❌ No behavior validation

---

## Proposed Future State

### New MCP Tools

**1. `extract_function` - Extract Function/Method**
```python
def extract_function(
    project_folder: str,
    file_path: str,
    start_line: int,
    end_line: int,
    language: str,
    function_name: Optional[str] = None,
    extract_location: str = "before",
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Extract selected code into a new function.

    Process:
    1. Analyze selected code for variables used
    2. Detect input parameters and return values
    3. Generate function signature
    4. Create function at specified location
    5. Replace selection with function call
    6. Preview or apply transformation

    Returns diff preview and backup_id if applied.
    """
```

**2. `rename_symbol` - Safe Rename Across Codebase**
```python
def rename_symbol(
    project_folder: str,
    symbol_name: str,
    new_name: str,
    language: str,
    scope: str = "project",
    file_filter: Optional[str] = None,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Rename a symbol (variable, function, class) across codebase.

    Features:
    - Scope-aware renaming (don't rename shadowed symbols)
    - Import statement updates
    - Comment and docstring updates
    - Multi-file atomic changes
    - Conflict detection

    Returns locations changed and diff preview.
    """
```

**3. `convert_code_style` - Style Conversion**
```python
def convert_code_style(
    project_folder: str,
    conversion_type: str,
    file_pattern: str,
    language: str,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Convert between code styles.

    Conversion types:
    - class_to_functional: Convert class components to functional (React)
    - functional_to_class: Convert functional to class components
    - promise_to_async: Convert .then() to async/await
    - loop_to_comprehension: Convert loops to list comprehensions (Python)
    - var_to_const: Convert var to const/let (JavaScript)
    - props_to_destructuring: Convert props.x to destructured params

    Returns conversion report and diff preview.
    """
```

**4. `simplify_conditionals` - Conditional Logic Simplification**
```python
def simplify_conditionals(
    project_folder: str,
    file_pattern: str,
    language: str,
    simplification_types: List[str] = ["all"],
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Simplify complex conditional logic.

    Simplification types:
    - nested_if_to_guard: Convert nested if to early returns
    - de_morgan: Apply De Morgan's laws
    - redundant_else: Remove unnecessary else clauses
    - boolean_simplification: Simplify boolean expressions
    - switch_to_dict: Convert switch/if-chains to dict lookup

    Returns simplified code and diff preview.
    """
```

**5. `refactor_batch` - Batch Refactoring**
```python
def refactor_batch(
    project_folder: str,
    refactorings: List[Dict[str, Any]],
    language: str,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Apply multiple refactorings atomically.

    Allows chaining:
    1. Extract function
    2. Rename extracted function
    3. Simplify conditionals
    4. Convert code style

    All-or-nothing: if any fails, all rollback.
    Returns combined diff preview.
    """
```

---

## Implementation Phases

### Phase 1: Extract Function Engine (Week 1-2, Size: XL)

**Goal:** Implement intelligent function extraction with parameter detection.

**Deliverables:**
1. Code selection analyzer (variables used, scope)
2. Parameter detection algorithm
3. Return value inference
4. Function signature generator
5. Call site replacement
6. `extract_function` MCP tool

**Key Technical Challenges:**
- Detect all variables used in selection
- Classify as: local, parameter, or closure
- Handle multiple return values
- Preserve indentation and formatting
- Detect side effects

**Success Criteria:**
- Correctly extracts functions 95%+ of cases
- Auto-detects parameters accurately
- Generated code passes syntax validation
- Original behavior preserved

**Example Transformation:**
```python
# Before
def process_user(user):
    name = user['name']
    email = user['email']
    if '@' not in email:
        return None
    # [SELECT START]
    normalized_email = email.lower().strip()
    domain = normalized_email.split('@')[1]
    # [SELECT END]
    return {'name': name, 'email': normalized_email, 'domain': domain}

# After (extract function)
def extract_email_domain(email: str) -> tuple[str, str]:
    normalized_email = email.lower().strip()
    domain = normalized_email.split('@')[1]
    return normalized_email, domain

def process_user(user):
    name = user['name']
    email = user['email']
    if '@' not in email:
        return None
    normalized_email, domain = extract_email_domain(email)
    return {'name': name, 'email': normalized_email, 'domain': domain}
```

---

### Phase 2: Symbol Renaming (Week 2-3, Size: L)

**Goal:** Implement safe, scope-aware symbol renaming.

**Deliverables:**
1. Symbol reference finder
2. Scope analyzer (avoid renaming shadows)
3. Import statement updater
4. Multi-file coordinator
5. Conflict detector
6. `rename_symbol` MCP tool

**Key Technical Challenges:**
- Build accurate scope tree
- Handle symbol shadowing
- Update all references atomically
- Detect naming conflicts
- Handle dynamic references

**Success Criteria:**
- Finds 100% of symbol references
- Respects scope boundaries
- Updates imports correctly
- Detects conflicts before applying

**Example Transformation:**
```typescript
// File: utils.ts
export function processData(data) { ... }

// File: app.ts
import { processData } from './utils';
const result = processData(input);

// After rename_symbol(symbol_name="processData", new_name="transformData")
// File: utils.ts
export function transformData(data) { ... }

// File: app.ts
import { transformData } from './utils';
const result = transformData(input);
```

---

### Phase 3: Code Style Conversion (Week 3-5, Size: XL)

**Goal:** Implement conversions between common code patterns.

**Deliverables:**
1. Class to functional converter (React)
2. Functional to class converter
3. Promise to async/await converter
4. Loop to comprehension converter (Python)
5. var to const/let converter (JS)
6. `convert_code_style` MCP tool

**Key Technical Challenges:**
- Preserve behavior across paradigms
- Handle state management (class → functional)
- Convert lifecycle methods correctly
- Maintain type safety

**Success Criteria:**
- Conversions preserve behavior
- Tests pass after conversion
- Idiomatic code in target style
- Works for 6+ conversion types

**Example Transformation:**
```javascript
// Before (class component)
class UserProfile extends React.Component {
  constructor(props) {
    super(props);
    this.state = { loading: true };
  }

  componentDidMount() {
    fetchUser(this.props.userId).then(user => {
      this.setState({ user, loading: false });
    });
  }

  render() {
    const { loading, user } = this.state;
    if (loading) return <div>Loading...</div>;
    return <div>{user.name}</div>;
  }
}

// After (functional component with hooks)
function UserProfile({ userId }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetchUser(userId).then(user => {
      setUser(user);
      setLoading(false);
    });
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  return <div>{user.name}</div>;
}
```

---

### Phase 4: Conditional Simplification (Week 5-6, Size: L)

**Goal:** Automatically simplify complex conditional logic.

**Deliverables:**
1. Nested if to guard clause converter
2. De Morgan's law applicator
3. Redundant else remover
4. Boolean expression simplifier
5. Switch to dict converter
6. `simplify_conditionals` MCP tool

**Success Criteria:**
- Reduces nesting depth by 50%+
- Simplifies boolean expressions
- Maintains logical equivalence
- Improves readability

**Example Transformation:**
```python
# Before (nested ifs)
def check_eligibility(user):
    if user.age >= 18:
        if user.has_license:
            if not user.is_banned:
                return True
            else:
                return False
        else:
            return False
    else:
        return False

# After (guard clauses)
def check_eligibility(user):
    if user.age < 18:
        return False
    if not user.has_license:
        return False
    if user.is_banned:
        return False
    return True
```

---

### Phase 5: Batch Refactoring (Week 6-7, Size: M)

**Goal:** Enable atomic multi-step refactorings.

**Deliverables:**
1. Refactoring pipeline orchestrator
2. Dependency resolver (order refactorings)
3. Combined diff generator
4. Atomic transaction manager
5. `refactor_batch` MCP tool

**Success Criteria:**
- Executes 5+ refactorings in sequence
- All-or-nothing atomicity
- Clear combined diff
- Rollback on any failure

---

### Phase 6: Testing & Documentation (Week 7-8, Size: M)

**Goal:** Comprehensive testing and documentation.

**Deliverables:**
1. 150+ test cases
2. Behavior preservation tests
3. Documentation updates
4. Example gallery

**Success Criteria:**
- >95% test coverage
- All refactorings tested
- Documentation complete

---

## Detailed Task Breakdown

### Phase 1: Extract Function Engine

**1.1 Code Selection Analyzer (Size: L)**
- [ ] Parse selected code region
- [ ] Identify all variables referenced
- [ ] Classify variables (local, param, global, closure)
- [ ] Detect variables modified (assignments)
- [ ] Detect return values needed
- [ ] Handle exceptions and early returns
- [ ] Unit tests for variable analysis

**1.2 Parameter Detection (Size: M)**
- [ ] Determine input parameters needed
- [ ] Infer parameter types (if possible)
- [ ] Generate parameter names
- [ ] Handle default values
- [ ] Unit tests for parameter detection

**1.3 Return Value Inference (Size: M)**
- [ ] Detect values used after selection
- [ ] Handle single vs. multiple returns
- [ ] Generate return statement
- [ ] Infer return type
- [ ] Unit tests

**1.4 Function Signature Generator (Size: M)**
- [ ] Generate function name (auto or user-provided)
- [ ] Build parameter list with types
- [ ] Build return type annotation
- [ ] Generate docstring
- [ ] Unit tests

**1.5 Call Site Replacement (Size: M)**
- [ ] Generate function call
- [ ] Handle unpacking return values
- [ ] Preserve indentation
- [ ] Unit tests

**1.6 Extract Function Tool (Size: M)**
- [ ] Create `extract_function` MCP tool
- [ ] Integrate analyzers
- [ ] Add preview mode
- [ ] Integration tests

---

### Phase 2: Symbol Renaming

**2.1 Symbol Reference Finder (Size: L)**
- [ ] Find all occurrences of symbol
- [ ] Build scope tree
- [ ] Filter by scope (avoid shadows)
- [ ] Handle imports/exports
- [ ] Unit tests

**2.2 Conflict Detector (Size: M)**
- [ ] Check if new name conflicts
- [ ] Check across all files
- [ ] Report conflicts before applying
- [ ] Unit tests

**2.3 Multi-File Coordinator (Size: M)**
- [ ] Plan file modification order
- [ ] Update all files atomically
- [ ] Handle failures
- [ ] Integration tests

**2.4 Rename Symbol Tool (Size: M)**
- [ ] Create `rename_symbol` MCP tool
- [ ] Integrate components
- [ ] Add preview mode
- [ ] Integration tests

---

### Phase 3: Code Style Conversion

**3.1 Class to Functional (React) (Size: L)**
- [ ] Extract state variables
- [ ] Convert lifecycle methods to useEffect
- [ ] Convert instance methods to functions
- [ ] Handle refs
- [ ] Unit tests

**3.2 Promise to Async/Await (Size: M)**
- [ ] Detect promise chains
- [ ] Convert .then() to await
- [ ] Add async keyword
- [ ] Handle .catch()
- [ ] Unit tests

**3.3 Loop to Comprehension (Python) (Size: M)**
- [ ] Detect simple loops
- [ ] Convert to list/dict comprehension
- [ ] Handle filters
- [ ] Unit tests

**3.4 Var to Const/Let (JavaScript) (Size: S)**
- [ ] Analyze variable reassignment
- [ ] Convert to const if never reassigned
- [ ] Convert to let if reassigned
- [ ] Unit tests

**3.5 Convert Code Style Tool (Size: M)**
- [ ] Create `convert_code_style` MCP tool
- [ ] Integrate converters
- [ ] Add preview mode
- [ ] Integration tests

---

## Success Metrics

**Accuracy:**
- Extract function: 95%+ success rate
- Symbol rename: 100% reference finding
- Style conversion: Behavior preserved
- Conditional simplification: Logical equivalence

**Performance:**
- Extract function: <5s
- Symbol rename: <10s for 100 files
- Style conversion: <15s per file
- Conditional simplification: <10s per file

**Usability:**
- Clear error messages
- Helpful parameter suggestions
- Readable diffs
- Rollback always works

---

## Risk Assessment

**Risk 1: Incorrect Refactoring** (High Impact)
- **Mitigation:** Extensive testing, dry-run default, behavior validation

**Risk 2: Scope Analysis Errors** (Medium Impact)
- **Mitigation:** Conservative approach, clear warnings, manual review

**Risk 3: Language Edge Cases** (Medium Impact)
- **Mitigation:** Start with well-understood languages, expand incrementally

---

## Timeline

- **Week 1-2:** Phase 1 (Extract Function)
- **Week 2-3:** Phase 2 (Symbol Renaming)
- **Week 3-5:** Phase 3 (Style Conversion)
- **Week 5-6:** Phase 4 (Conditional Simplification)
- **Week 6-7:** Phase 5 (Batch Refactoring)
- **Week 7-8:** Phase 6 (Testing & Docs)

**Total:** 6-8 weeks

---

**End of Plan**
**Last Updated:** 2025-11-18
