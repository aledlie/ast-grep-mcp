# Tool Registration Status Report

**Date:** 2025-11-25
**Total Tools:** 27
**Registered:** 11 (41%)
**Not Registered:** 16 (59%)

## Currently Registered Tools (11/27) ✅

### Code Search (4/4) ✅
1. `dump_syntax_tree` - Dump AST/CST for debugging
2. `test_match_code_rule` - Test YAML rules against code
3. `find_code` - Search code with patterns
4. `find_code_by_rule` - Search with YAML rules

**Source:** `ast_grep_mcp.features.search.service` (functions with `_impl` suffix)

### Code Rewrite (3/3) ✅
5. `rewrite_code` - Transform code with ast-grep
6. `list_backups` - List available backups
7. `rollback_rewrite` - Restore from backup

**Sources:**
- `ast_grep_mcp.features.rewrite.service` (`rewrite_code_impl`, `list_backups_impl`)
- `ast_grep_mcp.features.rewrite.backup` (`restore_backup`)

### Deduplication (4/4) ✅
8. `find_duplication` - Find duplicate code
9. `analyze_deduplication_candidates` - Rank duplicates by value
10. `apply_deduplication` - Apply refactoring
11. `benchmark_deduplication` - Performance benchmarks

**Source:** `ast_grep_mcp.features.deduplication.tools` (functions with `_tool` suffix)

---

## Not Yet Registered (16/27) ❌

### Schema.org Tools (0/8) ❌
- `search_types` - Search Schema.org vocabulary
- `get_type_details` - Get type definition
- `get_type_hierarchy` - Get inheritance tree
- `get_type_properties` - List type properties
- `validate_markup` - Validate Schema.org markup
- `compare_types` - Compare two types
- `find_related_types` - Find related types
- `get_vocab_stats` - Get vocabulary statistics

**Problem:** Tools defined as nested functions in `register_schema_tools()` using `@mcp.tool()` decorator. Cannot be directly imported.

**Location:** `src/ast_grep_mcp/features/schema/tools.py`

### Complexity Tools (0/2) ❌
- `analyze_complexity` - Analyze code complexity metrics
- `detect_code_smells` - Detect code smells

**Problem:** Tools defined as nested functions in `register_complexity_tools()` using `@mcp.tool()` decorator.

**Location:** `src/ast_grep_mcp/features/complexity/tools.py`

### Code Quality Tools (0/3) ❌
- `create_linting_rule` - Create custom linting rules
- `list_rule_templates` - List available rule templates
- `enforce_standards` - Enforce code quality standards

**Problem:** Tools defined as nested functions in `register_quality_tools()` using `@mcp.tool()` decorator.

**Location:** `src/ast_grep_mcp/features/quality/tools.py`

### Testing Tools (0/3) ❌
- `test_sentry_integration` - Test Sentry error tracking
- (2 other testing tools - need to identify)

**Problem:** Tools defined as nested functions using `@mcp.tool()` decorator.

---

## Technical Analysis

### Why 11 Tools Work

These tools are importable as standalone functions:
- **Search/Rewrite services:** Export `*_impl` functions that contain the actual logic
- **Deduplication tools:** Export `*_tool` functions that contain the logic

### Why 16 Tools Don't Work

These tools use the decorator pattern:

```python
def register_*_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def tool_name(...):
        # Logic defined inline
        ...
```

The functions are:
1. **Nested** inside `register_*_tools()`
2. **Not exported** from the module
3. **Only exist** after calling `register_*_tools(mcp)`

### Attempted Solution

```python
# In main.py register_mcp_tools()
from ast_grep_mcp.server.registry import register_all_tools
temp_mcp = FastMCP("ast-grep-test")
register_all_tools(temp_mcp)
# Try to extract from temp_mcp._tool_manager._tools
```

**Result:** Failed - Cannot reliably access tools from MCP's internal structure.

---

## Solutions

### Option 1: Extract Tool Logic (Recommended)

Refactor each nested tool into an importable function:

**Before:**
```python
def register_complexity_tools(mcp):
    @mcp.tool()
    def analyze_complexity(...):
        # 100 lines of logic
```

**After:**
```python
def analyze_complexity_tool(...):
    """Standalone function with tool logic."""
    # 100 lines of logic

def register_complexity_tools(mcp):
    mcp.tool()(analyze_complexity_tool)
```

**Effort:** ~2-4 hours for all 16 tools
**Benefits:** Clean, testable, importable

### Option 2: Use Tool Wrappers

Create wrapper functions that replicate the tool logic:

```python
# In main.py
def analyze_complexity_wrapper(...):
    from ast_grep_mcp.features.complexity.analyzer import analyze_file_complexity
    # Replicate tool logic
    ...

mcp.tools._tools["analyze_complexity"] = analyze_complexity_wrapper
```

**Effort:** ~1-2 hours for all 16 tools
**Benefits:** Quick fix
**Drawbacks:** Code duplication, maintenance burden

### Option 3: Integration Testing Only

Don't register these tools for unit tests. Instead:
- Use integration tests that start the actual MCP server
- Tests import directly from modular structure

**Effort:** Update test files
**Benefits:** No refactoring needed
**Drawbacks:** Tests become integration tests (slower)

---

## Recommendation

**Phase 1 (Immediate):** Continue fixture migration with the 11 working tools
**Phase 2 (Next sprint):** Implement Option 1 for the remaining 16 tools

This allows fixture migration to proceed while properly fixing the architecture.

---

## Test Impact

### Currently Working
- `test_apply_deduplication.py` (22/24 passing)
- `test_rewrite.py` (33/33 passing)
- Any tests using search/rewrite/deduplication tools

### Blocked
- Schema.org tool tests
- Complexity tool tests
- Quality tool tests
- Testing tool tests

**Estimated:** ~30-40% of test suite blocked by missing tool registration

---

## Action Items

- [x] Document current status
- [ ] Create GitHub issue for Option 1 refactoring
- [ ] Update test documentation to note limitation
- [ ] Proceed with Phase 3 fixture migration using working tools
- [ ] Plan sprint for completing tool refactoring
