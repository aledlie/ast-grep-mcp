"""ast-grep documentation content for LLM context.

This module provides condensed ast-grep documentation that can be
retrieved on-demand to provide context to LLMs, reducing hallucinations
and improving pattern/rule writing accuracy.

Based on: https://ast-grep.github.io/llms-full.txt
"""

from typing import Dict, List, Optional

# Documentation content organized by topic
AST_GREP_DOCS: Dict[str, str] = {
    "pattern": """# ast-grep Pattern Syntax

## Overview
Patterns are code snippets that match against target code using AST (Abstract Syntax Tree)
structure. Unlike text-based regex, patterns understand code syntax.

## Key Principle
**Pattern code must be valid, parseable code** that tree-sitter can parse.

## Metavariables
Metavariables are placeholders that match AST nodes. They use `$` prefix.

### Single-Node Metavariables: `$NAME`
- Match exactly ONE AST node
- Must use UPPERCASE letters, underscores, or digits (1-9)
- Valid: `$NAME`, `$VAR1`, `$MY_VAR`, `$_`, `$_123`
- Invalid: `$name` (lowercase), `$123` (starts with digit), `$KEBAB-CASE` (hyphen)

Examples:
```
function $NAME() { }     # Matches: function foo() { }
$OBJ.$METHOD()           # Matches: console.log(), arr.push()
$A == $A                 # Matches: x == x (same var both sides)
```

### Multi-Node Metavariables: `$$$` or `$$$NAME`
- Match ZERO OR MORE AST nodes
- Essential for function arguments, array elements, statement blocks

Examples:
```
foo($$$ARGS)             # Matches: foo(), foo(a), foo(a, b, c)
function $F($$$PARAMS) { $$$BODY }   # Matches any function
[$$$ELEMENTS]            # Matches any array literal
```

### Non-Capturing: `$_` or `$_NAME`
- Match but don't capture (performance optimization)
- Use when you don't need the matched value

Example:
```
$_FUNC($_ARG)            # Matches any function call, doesn't capture
```

### Unnamed Node Capture: `$$VAR`
- Captures unnamed tree-sitter nodes (advanced usage)
- Rarely needed in typical patterns

## Pattern Matching Rules
1. Patterns match at the AST level, not text level
2. Whitespace and formatting differences are ignored
3. Same metavariable name enforces structural equality: `$A == $A` matches `x == x` but not `x == y`
4. Nested patterns match nested code

## Common Patterns by Language

### JavaScript/TypeScript
```
console.log($$$ARGS)                    # Console logs
import $NAME from '$PATH'               # Named imports
const $NAME = ($$$PARAMS) => $BODY      # Arrow functions
async function $NAME($$$) { $$$BODY }   # Async functions
```

### Python
```
def $NAME($$$PARAMS): $$$BODY           # Function definitions
import $MODULE                          # Imports
class $NAME: $$$BODY                    # Class definitions
for $VAR in $ITER: $$$BODY              # For loops
```

### Go
```
func $NAME($$$PARAMS) $RET { $$$BODY }  # Functions
if err != nil { $$$BODY }               # Error handling
go $FUNC($$$ARGS)                       # Goroutines
```

## Best Practices
1. Start simple, add complexity gradually
2. Use `dump_syntax_tree` to understand code structure
3. Test patterns with `test_match_code_rule` before deployment
4. Use `debug_pattern` when patterns don't match as expected
5. Verify patterns in the ast-grep playground
""",
    "rules": """# ast-grep YAML Rule Configuration

## Rule Structure
Every YAML rule must have these required fields:

```yaml
id: unique-rule-identifier    # Required: unique ID for the rule
language: python              # Required: target language
rule:                         # Required: the matching rule
  pattern: def $NAME($$$): $$$
```

## Optional Fields
```yaml
message: "Description of what was found"   # Human-readable message
severity: warning                          # error, warning, info, hint
fix: "replacement code"                    # Auto-fix template
```

## Rule Object
The `rule` field can contain:

### Atomic Rules (match specific nodes)
- `pattern`: Match code structure
- `kind`: Match node type (e.g., `function_declaration`)
- `regex`: Match node text with regex (Rust regex syntax)

### Relational Rules (match based on position)
- `inside`: Match nodes inside a parent
- `has`: Match nodes containing a child
- `follows`: Match nodes after another
- `precedes`: Match nodes before another

### Composite Rules (combine rules)
- `all`: ALL sub-rules must match (AND)
- `any`: ANY sub-rule must match (OR)
- `not`: Rule must NOT match (negation)

## The `stopBy` Parameter (CRITICAL!)

⚠️ **This is the #1 source of "why doesn't my rule match?" issues**

Relational rules have a `stopBy` parameter:
- `neighbor` (DEFAULT): Only checks IMMEDIATE parent/sibling
- `end`: Searches to tree boundaries (usually what you want!)
- Custom rule object: Stops when match is found

### WRONG (common mistake):
```yaml
rule:
  pattern: $CALL
  inside:
    kind: function_declaration   # Missing stopBy: end!
```

### CORRECT:
```yaml
rule:
  pattern: $CALL
  inside:
    stopBy: end                  # Searches entire tree!
    kind: function_declaration
```

## Rule Ordering

⚠️ **Rule objects are UNORDERED!**

YAML doesn't guarantee field order. If order matters, use `all`:

```yaml
rule:
  all:
    - pattern: $FIRST
    - follows:
        pattern: $SECOND
```

## Complete Example

```yaml
id: no-console-in-production
language: javascript
severity: warning
message: "Remove console.log before production"
rule:
  any:
    - pattern: console.log($$$)
    - pattern: console.warn($$$)
    - pattern: console.error($$$)
  inside:
    stopBy: end
    kind: function_declaration
fix: ""
```

## Strictness Modes
For pattern matching, you can adjust strictness:
- `cst` (strictest): Match exact concrete syntax
- `smart` (default): Ignore trivial differences
- `ast`: Match abstract syntax only
- `relaxed`: More lenient matching
- `signature`: Match function signatures only

```yaml
rule:
  pattern:
    context: "function $F($$$) { $$$BODY }"
    strictness: relaxed
```
""",
    "relational": """# ast-grep Relational Rules

Relational rules match nodes based on their position relative to other nodes.

## The Four Relational Rules

### `inside` - Match nodes WITHIN a parent
```yaml
rule:
  pattern: console.log($$$)
  inside:
    stopBy: end
    kind: function_declaration
```
Matches `console.log()` calls that are inside a function.

### `has` - Match nodes that CONTAIN a child
```yaml
rule:
  kind: function_declaration
  has:
    stopBy: end
    pattern: return $VALUE
```
Matches functions that have a return statement.

### `follows` - Match nodes that come AFTER another
```yaml
rule:
  pattern: $USAGE
  follows:
    pattern: const $NAME = $VALUE
```
Matches code that follows a const declaration.

### `precedes` - Match nodes that come BEFORE another
```yaml
rule:
  pattern: const $NAME = $VALUE
  precedes:
    pattern: $NAME($$$)
```
Matches const declarations before their usage.

## The `stopBy` Parameter

⚠️ **CRITICAL: Always specify stopBy for relational rules!**

| Value | Behavior | When to Use |
|-------|----------|-------------|
| `neighbor` | Only immediate parent/sibling (DEFAULT) | Rarely what you want |
| `end` | Search to tree boundary | Most common use case |
| `{rule}` | Stop when rule matches | Advanced filtering |

### Examples

**Find console.log anywhere inside a function:**
```yaml
rule:
  pattern: console.log($$$)
  inside:
    stopBy: end              # Search up the entire tree
    kind: function_declaration
```

**Find console.log only at top level of function (immediate child):**
```yaml
rule:
  pattern: console.log($$$)
  inside:
    stopBy: neighbor         # Only immediate parent
    kind: block              # Function body block
```

**Find variables declared inside try blocks, stopping at function boundary:**
```yaml
rule:
  pattern: let $NAME = $VALUE
  inside:
    stopBy:
      kind: function_declaration   # Stop at function boundary
    kind: try_statement
```

## The `field` Parameter

Specify which child field to match (for `inside` and `has`):

```yaml
rule:
  kind: if_statement
  has:
    field: condition         # Only match in the condition field
    pattern: $A == null
```

## Combining Relational Rules

Use `all` to combine multiple relational constraints:

```yaml
rule:
  all:
    - pattern: $VAR
    - inside:
        stopBy: end
        kind: function_declaration
    - follows:
        pattern: const $VAR = $$$
```

## Common Patterns

### Find function calls inside async functions:
```yaml
rule:
  pattern: await $PROMISE
  inside:
    stopBy: end
    pattern: async function $NAME($$$) { $$$BODY }
```

### Find unused variables (declared but not used):
```yaml
rule:
  pattern: const $NAME = $VALUE
  not:
    has:
      stopBy: end
      pattern: $NAME
```

### Find error handling patterns:
```yaml
rule:
  kind: catch_clause
  has:
    stopBy: end
    pattern: console.error($$$)
```
""",
    "metavariables": """# ast-grep Metavariable Reference

Metavariables are placeholders in patterns that match AST nodes.

## Quick Reference Table

| Syntax | Name | Matches | Example |
|--------|------|---------|---------|
| `$NAME` | Single | One AST node | `$FUNC()` |
| `$$$` | Multi (anonymous) | Zero or more nodes | `foo($$$)` |
| `$$$NAME` | Multi (named) | Zero or more nodes | `foo($$$ARGS)` |
| `$_` | Non-capturing | One node (not captured) | `$_($$$)` |
| `$_NAME` | Non-capturing named | One node (not captured) | `$_FUNC($_ARG)` |
| `$$VAR` | Unnamed | Unnamed tree-sitter nodes | Advanced |

## Valid Naming Rules

### VALID metavariable names:
- `$NAME` - uppercase letters
- `$MY_VAR` - uppercase with underscores
- `$VAR1` - uppercase with trailing digits
- `$_` - single underscore (non-capturing wildcard)
- `$_123` - underscore with digits

### INVALID metavariable names:
- `$name` - ❌ lowercase letters not allowed
- `$myVar` - ❌ mixed case not allowed
- `$123` - ❌ cannot start with digit
- `$KEBAB-CASE` - ❌ hyphens not allowed
- `$` - ❌ bare dollar sign

## Single-Node Metavariables: `$NAME`

Match exactly one AST node.

```javascript
// Pattern: $OBJ.$METHOD($$$ARGS)
// Matches:
console.log("hello")     // $OBJ=console, $METHOD=log
array.push(1, 2, 3)      // $OBJ=array, $METHOD=push
user.getName()           // $OBJ=user, $METHOD=getName
```

### Structural Equality
Same metavariable name must match identical structure:

```javascript
// Pattern: $A == $A
// Matches: x == x, foo.bar == foo.bar
// Does NOT match: x == y, a.b == a.c
```

## Multi-Node Metavariables: `$$$`

Match zero or more consecutive AST nodes.

### In Function Arguments
```javascript
// Pattern: foo($$$ARGS)
// Matches:
foo()              // $$$ARGS = (empty)
foo(a)             // $$$ARGS = a
foo(a, b, c)       // $$$ARGS = a, b, c
```

### In Function Parameters
```javascript
// Pattern: function $NAME($$$PARAMS) { $$$BODY }
// Matches any function with any number of parameters
```

### In Arrays
```javascript
// Pattern: [$$$ELEMENTS]
// Matches: [], [1], [1, 2, 3], ["a", "b"]
```

### In Statements
```javascript
// Pattern: { $$$STATEMENTS }
// Matches any block with any statements
```

## Non-Capturing: `$_`

Use when you need to match but don't care about the value.
Performance optimization - doesn't store the match.

```javascript
// Pattern: $_FUNC($_ARG)
// Matches any single-argument function call
// Both $_FUNC and $_ARG can be different in the match
```

vs:

```javascript
// Pattern: $FUNC($ARG)
// Captures both the function name and argument
```

## Common Mistakes

### 1. Using lowercase metavariables
```
❌ $name, $myVar
✅ $NAME, $MY_VAR
```

### 2. Single metavariable for multiple arguments
```
❌ foo($ARG)      - Only matches foo(x), not foo(x, y)
✅ foo($$$ARGS)   - Matches foo(), foo(x), foo(x, y, z)
```

### 3. Forgetting $$$  in function definitions
```
❌ def $NAME($PARAM):     - Only matches single-param functions
✅ def $NAME($$$PARAMS):  - Matches any number of params
```

## Metavariables in Fixes

Metavariables captured in patterns can be used in fix templates:

```yaml
id: convert-to-template-literal
language: javascript
rule:
  pattern: $A + $B
fix: "`${$A}${$B}`"
```

Input: `name + greeting`
Output: `` `${name}${greeting}` ``
""",
    "workflow": """# ast-grep Development Workflow

## Recommended Iterative Approach

The ast-grep documentation recommends an iterative, trial-and-error workflow:

### 1. Start Simple
Begin with a basic pattern using `find_code`:
```
find_code(pattern="console.log($$$)", language="javascript")
```

### 2. Understand the Structure
Use `dump_syntax_tree` to see how code is parsed:
```
dump_syntax_tree(code="function foo() { console.log('hi'); }",
                 language="javascript",
                 format="cst")
```

### 3. Build Incrementally
Add complexity one step at a time:
1. Start with the core pattern
2. Add one relational rule
3. Test after each addition
4. Debug failures before adding more

### 4. Test Iterations
Use `test_match_code_rule` to validate against sample code:
```
test_match_code_rule(
    code="function foo() { console.log('test'); }",
    yaml_rule=your_rule
)
```

### 5. Debug Failures
Use `debug_pattern` when patterns don't match:
```
debug_pattern(
    pattern="console.log($message)",  # Wrong! lowercase
    code="console.log('hello')",
    language="javascript"
)
```

## Tool Selection Guide

| Task | Tool |
|------|------|
| Quick pattern search | `find_code` |
| Complex rules (relational, composite) | `find_code_by_rule` |
| Understand code structure | `dump_syntax_tree` |
| Validate rule against sample | `test_match_code_rule` |
| Debug pattern matching issues | `debug_pattern` |
| Build rule from components | `build_rule` |
| Get documentation help | `get_ast_grep_docs` |

## Common Development Patterns

### Pattern 1: Find and Refine
```
1. find_code with broad pattern
2. Review results
3. Add constraints to narrow results
4. Repeat until precise
```

### Pattern 2: Debug First
```
1. Write expected pattern
2. dump_syntax_tree on target code
3. Compare structures
4. Adjust pattern to match structure
```

### Pattern 3: Build Up Rules
```
1. Start with pattern-only rule
2. Add 'inside' with stopBy: end
3. Add 'has' constraints
4. Add 'not' exclusions
5. Test each iteration
```

## Troubleshooting Checklist

1. ✅ Metavariables are UPPERCASE
2. ✅ Using `$$$` for multiple arguments/elements
3. ✅ `stopBy: end` on all relational rules
4. ✅ Pattern is valid, parseable code
5. ✅ Correct language specified
6. ✅ Pattern matches the actual AST structure (use dump_syntax_tree)
""",
}


def get_docs(topic: str) -> str:
    """
    Get ast-grep documentation for a specific topic.

    Args:
        topic: One of 'pattern', 'rules', 'relational', 'metavariables', 'workflow', or 'all'

    Returns:
        Documentation string for the requested topic
    """
    if topic == "all":
        sections = []
        for name, content in AST_GREP_DOCS.items():
            sections.append(f"{'=' * 80}\n{name.upper()}\n{'=' * 80}\n\n{content}")
        return "\n\n".join(sections)

    if topic in AST_GREP_DOCS:
        return AST_GREP_DOCS[topic]

    available = ", ".join(sorted(AST_GREP_DOCS.keys()))
    return f"Unknown topic: '{topic}'. Available topics: {available}, all"


# =============================================================================
# Pattern Examples by Language and Category
# =============================================================================

# Pattern examples organized by language and category
# Each pattern includes: pattern string, description, notes (optional)
PATTERN_EXAMPLES: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "javascript": {
        "function": [
            {
                "pattern": "function $NAME($$$PARAMS) { $$$BODY }",
                "description": "Function declaration",
                "notes": "Use $$$PARAMS for any number of parameters",
            },
            {
                "pattern": "const $NAME = ($$$PARAMS) => $BODY",
                "description": "Arrow function (expression body)",
            },
            {
                "pattern": "const $NAME = ($$$PARAMS) => { $$$BODY }",
                "description": "Arrow function (block body)",
            },
            {
                "pattern": "async function $NAME($$$PARAMS) { $$$BODY }",
                "description": "Async function declaration",
            },
            {
                "pattern": "$OBJ.$METHOD($$$ARGS)",
                "description": "Method call on object",
                "notes": "Matches console.log(), arr.push(), etc.",
            },
        ],
        "class": [
            {
                "pattern": "class $NAME { $$$BODY }",
                "description": "Class declaration",
            },
            {
                "pattern": "class $NAME extends $PARENT { $$$BODY }",
                "description": "Class with inheritance",
            },
            {
                "pattern": "constructor($$$PARAMS) { $$$BODY }",
                "description": "Class constructor",
            },
        ],
        "import": [
            {
                "pattern": "import $NAME from '$PATH'",
                "description": "Default import",
            },
            {
                "pattern": "import { $$$NAMES } from '$PATH'",
                "description": "Named imports",
            },
            {
                "pattern": "import * as $NAME from '$PATH'",
                "description": "Namespace import",
            },
            {
                "pattern": "require('$PATH')",
                "description": "CommonJS require",
            },
        ],
        "variable": [
            {
                "pattern": "const $NAME = $VALUE",
                "description": "Const declaration",
            },
            {
                "pattern": "let $NAME = $VALUE",
                "description": "Let declaration",
            },
            {
                "pattern": "var $NAME = $VALUE",
                "description": "Var declaration (legacy)",
            },
            {
                "pattern": "const { $$$PROPS } = $OBJ",
                "description": "Object destructuring",
            },
            {
                "pattern": "const [$$$ITEMS] = $ARR",
                "description": "Array destructuring",
            },
        ],
        "control_flow": [
            {
                "pattern": "if ($COND) { $$$BODY }",
                "description": "If statement",
            },
            {
                "pattern": "if ($COND) { $$$THEN } else { $$$ELSE }",
                "description": "If-else statement",
            },
            {
                "pattern": "for (const $ITEM of $ITERABLE) { $$$BODY }",
                "description": "For-of loop",
            },
            {
                "pattern": "while ($COND) { $$$BODY }",
                "description": "While loop",
            },
            {
                "pattern": "$COND ? $THEN : $ELSE",
                "description": "Ternary expression",
            },
        ],
        "error_handling": [
            {
                "pattern": "try { $$$TRY } catch ($ERR) { $$$CATCH }",
                "description": "Try-catch block",
            },
            {
                "pattern": "throw new Error($MSG)",
                "description": "Throw error",
            },
            {
                "pattern": "throw $ERR",
                "description": "Throw any value",
            },
        ],
        "async": [
            {
                "pattern": "await $PROMISE",
                "description": "Await expression",
            },
            {
                "pattern": "Promise.all([$$$PROMISES])",
                "description": "Promise.all",
            },
            {
                "pattern": "new Promise(($RESOLVE, $REJECT) => { $$$BODY })",
                "description": "Promise constructor",
            },
            {
                "pattern": "$PROMISE.then($HANDLER)",
                "description": "Promise then",
            },
            {
                "pattern": "$PROMISE.catch($HANDLER)",
                "description": "Promise catch",
            },
        ],
    },
    "typescript": {
        "function": [
            {
                "pattern": "function $NAME($$$PARAMS): $RET { $$$BODY }",
                "description": "Typed function declaration",
            },
            {
                "pattern": "const $NAME = ($$$PARAMS): $RET => $BODY",
                "description": "Typed arrow function",
            },
            {
                "pattern": "async function $NAME($$$PARAMS): Promise<$T> { $$$BODY }",
                "description": "Async function with Promise return type",
            },
        ],
        "class": [
            {
                "pattern": "class $NAME implements $INTERFACE { $$$BODY }",
                "description": "Class implementing interface",
            },
            {
                "pattern": "private $NAME: $TYPE",
                "description": "Private property declaration",
            },
            {
                "pattern": "public $NAME: $TYPE",
                "description": "Public property declaration",
            },
        ],
        "import": [
            {
                "pattern": "import type { $$$NAMES } from '$PATH'",
                "description": "Type-only import",
            },
            {
                "pattern": "import { type $NAME } from '$PATH'",
                "description": "Inline type import",
            },
        ],
        "variable": [
            {
                "pattern": "const $NAME: $TYPE = $VALUE",
                "description": "Typed const declaration",
            },
            {
                "pattern": "let $NAME: $TYPE = $VALUE",
                "description": "Typed let declaration",
            },
            {
                "pattern": "$VAR as $TYPE",
                "description": "Type assertion",
            },
            {
                "pattern": "<$TYPE>$VAR",
                "description": "Type assertion (angle bracket)",
            },
        ],
        "control_flow": [
            {
                "pattern": "if ($VAR !== null && $VAR !== undefined) { $$$BODY }",
                "description": "Null check pattern",
            },
        ],
        "error_handling": [
            {
                "pattern": "try { $$$TRY } catch ($ERR: unknown) { $$$CATCH }",
                "description": "Typed catch clause",
            },
        ],
        "async": [
            {
                "pattern": "await $PROMISE as $TYPE",
                "description": "Await with type assertion",
            },
        ],
    },
    "python": {
        "function": [
            {
                "pattern": "def $NAME($$$PARAMS):\n    $$$BODY",
                "description": "Function definition",
                "notes": "Python patterns need proper indentation",
            },
            {
                "pattern": "def $NAME($$$PARAMS) -> $RET:\n    $$$BODY",
                "description": "Function with return type hint",
            },
            {
                "pattern": "async def $NAME($$$PARAMS):\n    $$$BODY",
                "description": "Async function definition",
            },
            {
                "pattern": "lambda $PARAMS: $BODY",
                "description": "Lambda expression",
            },
            {
                "pattern": "@$DECORATOR\ndef $NAME($$$PARAMS):\n    $$$BODY",
                "description": "Decorated function",
            },
        ],
        "class": [
            {
                "pattern": "class $NAME:\n    $$$BODY",
                "description": "Class definition",
            },
            {
                "pattern": "class $NAME($PARENT):\n    $$$BODY",
                "description": "Class with inheritance",
            },
            {
                "pattern": "def __init__(self, $$$PARAMS):\n    $$$BODY",
                "description": "Constructor method",
            },
            {
                "pattern": "@dataclass\nclass $NAME:\n    $$$BODY",
                "description": "Dataclass definition",
            },
        ],
        "import": [
            {
                "pattern": "import $MODULE",
                "description": "Simple import",
            },
            {
                "pattern": "from $MODULE import $NAME",
                "description": "From import",
            },
            {
                "pattern": "from $MODULE import $$$NAMES",
                "description": "Multiple from imports",
            },
            {
                "pattern": "import $MODULE as $ALIAS",
                "description": "Import with alias",
            },
        ],
        "variable": [
            {
                "pattern": "$NAME = $VALUE",
                "description": "Assignment",
            },
            {
                "pattern": "$NAME: $TYPE = $VALUE",
                "description": "Typed assignment",
            },
            {
                "pattern": "$A, $B = $VALUE",
                "description": "Tuple unpacking",
            },
        ],
        "control_flow": [
            {
                "pattern": "if $COND:\n    $$$BODY",
                "description": "If statement",
            },
            {
                "pattern": "for $VAR in $ITERABLE:\n    $$$BODY",
                "description": "For loop",
            },
            {
                "pattern": "while $COND:\n    $$$BODY",
                "description": "While loop",
            },
            {
                "pattern": "[$EXPR for $VAR in $ITERABLE]",
                "description": "List comprehension",
            },
            {
                "pattern": "{$KEY: $VALUE for $VAR in $ITERABLE}",
                "description": "Dict comprehension",
            },
            {
                "pattern": "$THEN if $COND else $ELSE",
                "description": "Ternary expression",
            },
        ],
        "error_handling": [
            {
                "pattern": "try:\n    $$$TRY\nexcept $EXC:\n    $$$EXCEPT",
                "description": "Try-except block",
            },
            {
                "pattern": "raise $EXC",
                "description": "Raise exception",
            },
            {
                "pattern": "with $CTX as $VAR:\n    $$$BODY",
                "description": "Context manager",
            },
        ],
        "async": [
            {
                "pattern": "await $AWAITABLE",
                "description": "Await expression",
            },
            {
                "pattern": "async with $CTX as $VAR:\n    $$$BODY",
                "description": "Async context manager",
            },
            {
                "pattern": "async for $VAR in $ITERABLE:\n    $$$BODY",
                "description": "Async for loop",
            },
        ],
    },
    "go": {
        "function": [
            {
                "pattern": "func $NAME($$$PARAMS) $RET { $$$BODY }",
                "description": "Function declaration",
            },
            {
                "pattern": "func ($RECV $TYPE) $NAME($$$PARAMS) $RET { $$$BODY }",
                "description": "Method with receiver",
            },
            {
                "pattern": "func($$$PARAMS) $RET { $$$BODY }",
                "description": "Anonymous function",
            },
        ],
        "class": [
            {
                "pattern": "type $NAME struct { $$$FIELDS }",
                "description": "Struct definition",
            },
            {
                "pattern": "type $NAME interface { $$$METHODS }",
                "description": "Interface definition",
            },
        ],
        "import": [
            {
                "pattern": 'import "$PATH"',
                "description": "Single import",
            },
            {
                "pattern": "import (\n$$$IMPORTS\n)",
                "description": "Import block",
            },
        ],
        "variable": [
            {
                "pattern": "$NAME := $VALUE",
                "description": "Short variable declaration",
            },
            {
                "pattern": "var $NAME $TYPE = $VALUE",
                "description": "Full variable declaration",
            },
            {
                "pattern": "const $NAME = $VALUE",
                "description": "Constant declaration",
            },
        ],
        "control_flow": [
            {
                "pattern": "if $COND { $$$BODY }",
                "description": "If statement",
            },
            {
                "pattern": "if $INIT; $COND { $$$BODY }",
                "description": "If with initialization",
            },
            {
                "pattern": "for $INIT; $COND; $POST { $$$BODY }",
                "description": "For loop",
            },
            {
                "pattern": "for $KEY, $VALUE := range $ITERABLE { $$$BODY }",
                "description": "Range loop",
            },
            {
                "pattern": "switch $EXPR { $$$CASES }",
                "description": "Switch statement",
            },
            {
                "pattern": "select { $$$CASES }",
                "description": "Select statement",
            },
        ],
        "error_handling": [
            {
                "pattern": "if err != nil { $$$BODY }",
                "description": "Error check pattern",
            },
            {
                "pattern": "$VAL, err := $CALL",
                "description": "Error return pattern",
            },
            {
                "pattern": "defer $CALL",
                "description": "Defer statement",
            },
            {
                "pattern": "panic($MSG)",
                "description": "Panic call",
            },
            {
                "pattern": "recover()",
                "description": "Recover call",
            },
        ],
        "async": [
            {
                "pattern": "go $FUNC($$$ARGS)",
                "description": "Goroutine",
            },
            {
                "pattern": "$CHAN <- $VALUE",
                "description": "Channel send",
            },
            {
                "pattern": "$VAR := <-$CHAN",
                "description": "Channel receive",
            },
            {
                "pattern": "make(chan $TYPE)",
                "description": "Create channel",
            },
        ],
    },
    "rust": {
        "function": [
            {
                "pattern": "fn $NAME($$$PARAMS) -> $RET { $$$BODY }",
                "description": "Function with return type",
            },
            {
                "pattern": "fn $NAME($$$PARAMS) { $$$BODY }",
                "description": "Function without return",
            },
            {
                "pattern": "pub fn $NAME($$$PARAMS) -> $RET { $$$BODY }",
                "description": "Public function",
            },
            {
                "pattern": "async fn $NAME($$$PARAMS) -> $RET { $$$BODY }",
                "description": "Async function",
            },
            {
                "pattern": "|$$$PARAMS| $BODY",
                "description": "Closure",
            },
        ],
        "class": [
            {
                "pattern": "struct $NAME { $$$FIELDS }",
                "description": "Struct definition",
            },
            {
                "pattern": "impl $NAME { $$$METHODS }",
                "description": "Implementation block",
            },
            {
                "pattern": "impl $TRAIT for $NAME { $$$METHODS }",
                "description": "Trait implementation",
            },
            {
                "pattern": "trait $NAME { $$$METHODS }",
                "description": "Trait definition",
            },
            {
                "pattern": "enum $NAME { $$$VARIANTS }",
                "description": "Enum definition",
            },
        ],
        "import": [
            {
                "pattern": "use $PATH;",
                "description": "Use statement",
            },
            {
                "pattern": "use $PATH::{$$$ITEMS};",
                "description": "Multiple imports from path",
            },
            {
                "pattern": "use $PATH::*;",
                "description": "Glob import",
            },
        ],
        "variable": [
            {
                "pattern": "let $NAME = $VALUE;",
                "description": "Immutable binding",
            },
            {
                "pattern": "let mut $NAME = $VALUE;",
                "description": "Mutable binding",
            },
            {
                "pattern": "let $NAME: $TYPE = $VALUE;",
                "description": "Typed binding",
            },
            {
                "pattern": "const $NAME: $TYPE = $VALUE;",
                "description": "Constant",
            },
        ],
        "control_flow": [
            {
                "pattern": "if $COND { $$$BODY }",
                "description": "If expression",
            },
            {
                "pattern": "match $EXPR { $$$ARMS }",
                "description": "Match expression",
            },
            {
                "pattern": "for $VAR in $ITER { $$$BODY }",
                "description": "For loop",
            },
            {
                "pattern": "while $COND { $$$BODY }",
                "description": "While loop",
            },
            {
                "pattern": "loop { $$$BODY }",
                "description": "Infinite loop",
            },
        ],
        "error_handling": [
            {
                "pattern": "$EXPR?",
                "description": "Error propagation",
            },
            {
                "pattern": "unwrap()",
                "description": "Unwrap Result/Option",
            },
            {
                "pattern": "expect($MSG)",
                "description": "Expect with message",
            },
            {
                "pattern": "Ok($VALUE)",
                "description": "Ok variant",
            },
            {
                "pattern": "Err($VALUE)",
                "description": "Err variant",
            },
            {
                "pattern": "panic!($MSG)",
                "description": "Panic macro",
            },
        ],
        "async": [
            {
                "pattern": "$FUTURE.await",
                "description": "Await future",
            },
            {
                "pattern": "tokio::spawn($FUTURE)",
                "description": "Tokio spawn",
            },
        ],
    },
    "java": {
        "function": [
            {
                "pattern": "public $RET $NAME($$$PARAMS) { $$$BODY }",
                "description": "Public method",
            },
            {
                "pattern": "private $RET $NAME($$$PARAMS) { $$$BODY }",
                "description": "Private method",
            },
            {
                "pattern": "public static $RET $NAME($$$PARAMS) { $$$BODY }",
                "description": "Static method",
            },
        ],
        "class": [
            {
                "pattern": "public class $NAME { $$$BODY }",
                "description": "Public class",
            },
            {
                "pattern": "public class $NAME extends $PARENT { $$$BODY }",
                "description": "Class with inheritance",
            },
            {
                "pattern": "public class $NAME implements $INTERFACE { $$$BODY }",
                "description": "Class implementing interface",
            },
            {
                "pattern": "public interface $NAME { $$$BODY }",
                "description": "Interface definition",
            },
        ],
        "import": [
            {
                "pattern": "import $PATH;",
                "description": "Import statement",
            },
            {
                "pattern": "import static $PATH;",
                "description": "Static import",
            },
        ],
        "variable": [
            {
                "pattern": "$TYPE $NAME = $VALUE;",
                "description": "Variable declaration",
            },
            {
                "pattern": "final $TYPE $NAME = $VALUE;",
                "description": "Final variable",
            },
            {
                "pattern": "private $TYPE $NAME;",
                "description": "Private field",
            },
        ],
        "control_flow": [
            {
                "pattern": "if ($COND) { $$$BODY }",
                "description": "If statement",
            },
            {
                "pattern": "for ($TYPE $VAR : $ITERABLE) { $$$BODY }",
                "description": "Enhanced for loop",
            },
            {
                "pattern": "switch ($EXPR) { $$$CASES }",
                "description": "Switch statement",
            },
        ],
        "error_handling": [
            {
                "pattern": "try { $$$TRY } catch ($TYPE $VAR) { $$$CATCH }",
                "description": "Try-catch block",
            },
            {
                "pattern": "throw new $TYPE($MSG);",
                "description": "Throw exception",
            },
        ],
        "async": [
            {
                "pattern": "CompletableFuture.supplyAsync($$$ARGS)",
                "description": "Async computation",
            },
            {
                "pattern": "$FUTURE.thenApply($FUNC)",
                "description": "Future chain",
            },
        ],
    },
    "ruby": {
        "function": [
            {
                "pattern": "def $NAME($$$PARAMS)\n  $$$BODY\nend",
                "description": "Method definition",
            },
            {
                "pattern": "def self.$NAME($$$PARAMS)\n  $$$BODY\nend",
                "description": "Class method",
            },
            {
                "pattern": "->($$$PARAMS) { $$$BODY }",
                "description": "Lambda",
            },
            {
                "pattern": "proc { |$$$PARAMS| $$$BODY }",
                "description": "Proc",
            },
        ],
        "class": [
            {
                "pattern": "class $NAME\n  $$$BODY\nend",
                "description": "Class definition",
            },
            {
                "pattern": "class $NAME < $PARENT\n  $$$BODY\nend",
                "description": "Class with inheritance",
            },
            {
                "pattern": "module $NAME\n  $$$BODY\nend",
                "description": "Module definition",
            },
        ],
        "import": [
            {
                "pattern": "require '$PATH'",
                "description": "Require file",
            },
            {
                "pattern": "require_relative '$PATH'",
                "description": "Require relative",
            },
            {
                "pattern": "include $MODULE",
                "description": "Include module",
            },
        ],
        "variable": [
            {
                "pattern": "$NAME = $VALUE",
                "description": "Local variable",
            },
            {
                "pattern": "@$NAME = $VALUE",
                "description": "Instance variable",
            },
            {
                "pattern": "@@$NAME = $VALUE",
                "description": "Class variable",
            },
        ],
        "control_flow": [
            {
                "pattern": "if $COND\n  $$$BODY\nend",
                "description": "If statement",
            },
            {
                "pattern": "unless $COND\n  $$$BODY\nend",
                "description": "Unless statement",
            },
            {
                "pattern": "$ITERABLE.each { |$VAR| $$$BODY }",
                "description": "Each block",
            },
            {
                "pattern": "$COND ? $THEN : $ELSE",
                "description": "Ternary",
            },
        ],
        "error_handling": [
            {
                "pattern": "begin\n  $$$TRY\nrescue $EXC\n  $$$RESCUE\nend",
                "description": "Begin-rescue block",
            },
            {
                "pattern": "raise $MSG",
                "description": "Raise exception",
            },
        ],
        "async": [
            {
                "pattern": "Thread.new { $$$BODY }",
                "description": "New thread",
            },
        ],
    },
    "c": {
        "function": [
            {
                "pattern": "$RET $NAME($$$PARAMS) { $$$BODY }",
                "description": "Function definition",
            },
            {
                "pattern": "static $RET $NAME($$$PARAMS) { $$$BODY }",
                "description": "Static function",
            },
        ],
        "class": [
            {
                "pattern": "struct $NAME { $$$FIELDS };",
                "description": "Struct definition",
            },
            {
                "pattern": "typedef struct { $$$FIELDS } $NAME;",
                "description": "Typedef struct",
            },
            {
                "pattern": "enum $NAME { $$$VALUES };",
                "description": "Enum definition",
            },
        ],
        "import": [
            {
                "pattern": '#include "$PATH"',
                "description": "Include local header",
            },
            {
                "pattern": "#include <$PATH>",
                "description": "Include system header",
            },
        ],
        "variable": [
            {
                "pattern": "$TYPE $NAME = $VALUE;",
                "description": "Variable declaration",
            },
            {
                "pattern": "const $TYPE $NAME = $VALUE;",
                "description": "Const variable",
            },
            {
                "pattern": "$TYPE *$NAME = $VALUE;",
                "description": "Pointer declaration",
            },
        ],
        "control_flow": [
            {
                "pattern": "if ($COND) { $$$BODY }",
                "description": "If statement",
            },
            {
                "pattern": "for ($INIT; $COND; $INCR) { $$$BODY }",
                "description": "For loop",
            },
            {
                "pattern": "while ($COND) { $$$BODY }",
                "description": "While loop",
            },
            {
                "pattern": "switch ($EXPR) { $$$CASES }",
                "description": "Switch statement",
            },
        ],
        "error_handling": [
            {
                "pattern": "if ($VAR == NULL) { $$$BODY }",
                "description": "NULL check",
            },
            {
                "pattern": "if ($RET < 0) { $$$BODY }",
                "description": "Error return check",
            },
        ],
        "async": [],  # C doesn't have built-in async
    },
    "cpp": {
        "function": [
            {
                "pattern": "$RET $NAME($$$PARAMS) { $$$BODY }",
                "description": "Function definition",
            },
            {
                "pattern": "auto $NAME($$$PARAMS) -> $RET { $$$BODY }",
                "description": "Trailing return type",
            },
            {
                "pattern": "[$$$CAPTURE]($$$PARAMS) { $$$BODY }",
                "description": "Lambda expression",
            },
        ],
        "class": [
            {
                "pattern": "class $NAME { $$$BODY };",
                "description": "Class definition",
            },
            {
                "pattern": "class $NAME : public $PARENT { $$$BODY };",
                "description": "Class with inheritance",
            },
            {
                "pattern": "template<$$$PARAMS>\nclass $NAME { $$$BODY };",
                "description": "Template class",
            },
        ],
        "import": [
            {
                "pattern": '#include "$PATH"',
                "description": "Include local header",
            },
            {
                "pattern": "#include <$PATH>",
                "description": "Include system header",
            },
            {
                "pattern": "using namespace $NS;",
                "description": "Using namespace",
            },
        ],
        "variable": [
            {
                "pattern": "auto $NAME = $VALUE;",
                "description": "Auto type deduction",
            },
            {
                "pattern": "std::unique_ptr<$TYPE> $NAME = $VALUE;",
                "description": "Unique pointer",
            },
            {
                "pattern": "std::shared_ptr<$TYPE> $NAME = $VALUE;",
                "description": "Shared pointer",
            },
        ],
        "control_flow": [
            {
                "pattern": "if ($COND) { $$$BODY }",
                "description": "If statement",
            },
            {
                "pattern": "for (auto& $VAR : $CONTAINER) { $$$BODY }",
                "description": "Range-based for",
            },
            {
                "pattern": "if constexpr ($COND) { $$$BODY }",
                "description": "Compile-time if",
            },
        ],
        "error_handling": [
            {
                "pattern": "try { $$$TRY } catch ($TYPE $VAR) { $$$CATCH }",
                "description": "Try-catch block",
            },
            {
                "pattern": "throw $EXPR;",
                "description": "Throw exception",
            },
            {
                "pattern": "std::optional<$TYPE>",
                "description": "Optional type",
            },
        ],
        "async": [
            {
                "pattern": "std::async($POLICY, $FUNC, $$$ARGS)",
                "description": "Async call",
            },
            {
                "pattern": "co_await $EXPR",
                "description": "Coroutine await",
            },
            {
                "pattern": "std::thread($FUNC, $$$ARGS)",
                "description": "Create thread",
            },
        ],
    },
}

# Categories available
PATTERN_CATEGORIES = [
    "function",
    "class",
    "import",
    "variable",
    "control_flow",
    "error_handling",
    "async",
]

# Languages available
PATTERN_LANGUAGES = list(PATTERN_EXAMPLES.keys())


def get_pattern_examples(
    language: str,
    category: Optional[str] = None,
) -> str:
    """
    Get common pattern examples for a language and optional category.

    Args:
        language: Target language (javascript, typescript, python, go, rust, java, ruby, c, cpp)
        category: Optional category filter (function, class, import, variable, control_flow,
                  error_handling, async, or 'all' for everything)

    Returns:
        Formatted string with pattern examples
    """
    language = language.lower()

    # Handle language aliases
    language_aliases = {
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "golang": "go",
        "c++": "cpp",
    }
    language = language_aliases.get(language, language)

    if language not in PATTERN_EXAMPLES:
        available = ", ".join(sorted(PATTERN_EXAMPLES.keys()))
        return f"Unknown language: '{language}'. Available: {available}"

    lang_patterns = PATTERN_EXAMPLES[language]

    # Determine which categories to show
    if category is None or category == "all":
        categories_to_show = list(lang_patterns.keys())
    else:
        category = category.lower()
        if category not in lang_patterns:
            available = ", ".join(sorted(lang_patterns.keys()))
            return f"Unknown category: '{category}'. Available: {available}, all"
        categories_to_show = [category]

    # Build output
    lines = [f"# {language.title()} Pattern Examples", ""]

    for cat in categories_to_show:
        patterns = lang_patterns.get(cat, [])
        if not patterns:
            continue

        lines.append(f"## {cat.replace('_', ' ').title()}")
        lines.append("")

        for p in patterns:
            lines.append(f"### {p['description']}")
            lines.append("```")
            lines.append(p["pattern"])
            lines.append("```")
            if "notes" in p:
                lines.append(f"*{p['notes']}*")
            lines.append("")

    return "\n".join(lines)
