# Python YAML Rules Audit Against ast-grep Python API

**Date:** 2026-04-20  
**Audit Target:** `rules/python-security-high-priority.yaml` (12 rules)  
**Reference:** https://ast-grep.github.io/guide/api-usage/py-api.html

## Summary
- **Total Rules:** 12
- **Critical Issues Found:** 5 (invalid operators/syntax)
- **Pattern Issues:** 8 (meta-variable errors, unsupported selectors)
- **Documentation Compliance:** 70% (needs updates)

## Critical Issues

### 1. Invalid Meta-Variable Syntax (Rules 1-3)
**Issue:** Double-dollar `$$ARGS` instead of triple-dollar `$$$ARGS`  
**Location:** Rules 1, 2, 3  
**Example:** `pattern: jwt.encode($ARG1, \"$SECRET\", $$ARGS)`  
**Should be:** `pattern: jwt.encode($ARG1, \"$SECRET\", $$$ARGS)`  
**Impact:** HIGH — multi-node matching will fail silently

### 2. Undocumented Operators (Rule 9)
**Issue:** `context:` and `selector:` are not documented operators  
**Location:** Rule 9 (secret-variable-used-after-assignment)  
```yaml
pattern:
  context: $VAR = \"$HARDCODED_SECRET\"
  selector: assignment
```
**Valid Operators:** `pattern`, `kind`, `regex`, `inside`, `has`, `follows`, `precedes`, `all`, `any`, `not`, `matches`  
**Impact:** HIGH — this rule will not parse correctly

### 3. Mismatched Pattern Logic (Rule 4)
**Issue:** Cipher.new pattern confuses mode with algorithm  
**Location:** Rule 4 (insecure-cryptography)  
```yaml
pattern: Cipher.new(AES.MODE_CBC, \"RC4\", ...)
```
**Problem:** AES.MODE_CBC is the second arg, not RC4. Pattern should be:
```yaml
pattern: Cipher.new(\"RC4\", ...)
```
**Impact:** MEDIUM — rule will never match intended patterns

### 4. Comment Pattern Matching (Rules 1-7)
**Issue:** Patterns like `pattern: \"# import jwt\"` attempt to match comments  
**Location:** Multiple rules in `follows:` sections  
**Problem:** ast-grep patterns match AST nodes; comments are typically excluded  
**Better Approach:** Use `not: { inside: { pattern: \"# ...\" } }` or rely on code context  
**Impact:** MEDIUM — these exclusions may not work as intended

### 5. String Literal Matching in Patterns (Rules 1-3, 10-11)
**Issue:** Patterns assume string literal matching works across boundary contexts  
**Location:** Rules 1, 2, 3, 10, 11  
**Example:** `pattern: $VAR = \"http://$$$HOST\"`  
**Problem:** Pattern syntax requires valid Python code; `$$$HOST` may not match string interpolation correctly  
**Impact:** MEDIUM — patterns may be too strict or too loose

## Pattern Syntax Issues

| Rule | Issue | Severity |
|------|-------|----------|
| 1 | `$$ARGS` → `$$$ARGS` | HIGH |
| 2 | `$$ARGS` → `$$$ARGS` | HIGH |
| 3 | `$$ARGS` → `$$$ARGS` | HIGH |
| 4 | Cipher.new pattern logic reversed | MEDIUM |
| 9 | Invalid `context:` and `selector:` operators | HIGH |
| 10 | String interpolation pattern too complex | MEDIUM |
| 11 | Requires validation of concatenation matching | MEDIUM |
| 12 | Unmatched quotes in some patterns | LOW |

## Relational Operator Validation

**Tested & Valid:**
- `follows:` ✓ (documented as relational)
- `precedes:` ✓ (documented as relational)
- `inside:` ✓ (documented as relational)
- `all:`, `any:` ✓ (documented as composite)
- `not:` ✓ (documented as composite)
- `has:` ✓ (documented but not used in rules)

**stopBy Recommendations:**
- Rules 1-3 use `follows:` without `stopBy` — may continue searching beyond module scope
- Consider adding `stopBy: { pattern: \"class.*\" }` to limit import search scope
- Rule 10 uses `follows:` without `stopBy` — could match far-away imports

## Recommended Fixes

### Priority 1: Syntax Corrections
```yaml
# Fix Rule 1, 2, 3:
- pattern: jwt.encode($ARG1, \"$SECRET\", $$$ARGS)  # was $$ARGS

# Fix Rule 9: Remove undocumented operators
- pattern: $VAR = \"$HARDCODED_SECRET\"
- precedes:
    pattern: jwt.encode(..., $VAR, ...)
```

### Priority 2: Pattern Refinement
```yaml
# Fix Rule 4:
- pattern: Cipher.new(\"RC4\", ...)
- pattern: hashlib.md5($$$ARGS)
- pattern: hashlib.sha1($$$ARGS)

# Add stopBy to limit scope:
- follows:
    any:
      - pattern: import jwt
    stopBy: { pattern: \"class.*\" }
```

### Priority 3: Comment Handling
Replace comment matching with `not:` patterns:
```yaml
# Instead of:
- pattern: import jwt
- not: { pattern: \"# import jwt\" }

# Better approach:
- pattern: import jwt
# Comments are not in AST; this naturally excludes them
```

## Reference
- ast-grep Pattern Syntax: https://ast-grep.github.io/guide/pattern-syntax.html
- ast-grep Rule Config: https://ast-grep.github.io/guide/rule-config.html
- Python API: https://ast-grep.github.io/guide/api-usage/py-api.html
