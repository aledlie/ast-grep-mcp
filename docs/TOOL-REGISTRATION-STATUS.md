# Tool Registration Status Report

**Date:** 2025-11-25
**Total Tools:** 27
**Registered:** 13 (48%)
**Not Registered:** 14 (52%)

## Currently Registered Tools (13/27) ✅

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

### Testing Tools (2/2) ✅
12. `analyze_complexity` - Analyze code complexity metrics
13. `test_sentry_integration` - Test Sentry error tracking

**Source:** `ast_grep_mcp.features.complexity.tools` (functions with `_tool` suffix)

**Note:** These tools were refactored on 2025-11-25 by extracting nested function logic into standalone `*_tool` functions.

---

## Not Yet Registered (14/27) ❌

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

### Code Quality Tools (0/3) ❌
- `create_linting_rule` - Create custom linting rules
- `list_rule_templates` - List available rule templates
- `enforce_standards` - Enforce code quality standards

**Problem:** Tools defined as nested functions in `register_quality_tools()` using `@mcp.tool()` decorator.

**Location:** `src/ast_grep_mcp/features/quality/tools.py`

### Code Smell Detection (0/1) ❌
- `detect_code_smells` - Detect code smells and anti-patterns

**Problem:** Tool defined as nested function in `register_complexity_tools()` using `@mcp.tool()` decorator.

**Location:** `src/ast_grep_mcp/features/complexity/tools.py`

**Note:** This tool is in the complexity module but was not refactored during the 2025-11-25 update because only `analyze_complexity` and `test_sentry_integration` were found in that module.

---

## Technical Analysis

### Why 13 Tools Work

These tools are importable as standalone functions:
- **Search/Rewrite services:** Export `*_impl` functions that contain the actual logic
- **Deduplication tools:** Export `*_tool` functions that contain the logic
- **Testing tools:** Refactored to export `*_tool` functions (2025-11-25 update)

### Why 14 Tools Don't Work

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

**Effort:** ~2-4 hours for all 14 remaining tools
**Benefits:** Clean, testable, importable

**Progress:** ✅ 2 tools refactored (2025-11-25): `analyze_complexity`, `test_sentry_integration`

### Option 2: Use Tool Wrappers

Create wrapper functions that replicate the tool logic:

```python
# In main.py
def search_types_wrapper(...):
    from ast_grep_mcp.features.schema.client import SchemaOrgClient
    # Replicate tool logic
    ...

mcp.tools._tools["search_types"] = search_types_wrapper
```

**Effort:** ~1-2 hours for all 14 remaining tools
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

**Phase 1 (Immediate):** Continue fixture migration with the 13 working tools ✅
**Phase 2 (In Progress):** Implement Option 1 for the remaining 14 tools

**Progress Update (2025-11-25):**
- ✅ Testing tools refactored (2 tools): `analyze_complexity`, `test_sentry_integration`
- ⏳ Remaining: Schema.org tools (8), Code quality tools (3), Code smell detection (1)

This allows fixture migration to proceed while systematically fixing the architecture.

---

## Test Impact

### Currently Working
- `test_apply_deduplication.py` (24/24 passing) ✅
- `test_rewrite.py` (33/33 passing) ✅
- `test_complexity.py` (51/51 passing) ✅ [Updated 2025-11-25]
- Any tests using search/rewrite/deduplication/testing tools

### Blocked
- Schema.org tool tests (8 tools)
- Code quality tool tests (3 tools)
- Code smell detection tests (1 tool)

**Estimated:** ~25-30% of test suite blocked by missing tool registration (improved from 30-40%)

---

## Action Items

- [x] Document current status
- [x] Refactor Testing tools (2025-11-25) - `analyze_complexity`, `test_sentry_integration`
- [x] Update test documentation to reflect refactored tools
- [ ] Create GitHub issue for Option 1 refactoring of remaining 14 tools
- [ ] Proceed with Phase 3 fixture migration using 13 working tools
- [ ] Refactor Schema.org tools (8 tools)
- [ ] Refactor Code Quality tools (3 tools)
- [ ] Refactor Code Smell Detection tool (1 tool)
- [ ] Plan sprint for completing remaining tool refactoring
