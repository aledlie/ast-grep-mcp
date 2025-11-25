# conftest.py Enhancements Summary

## Overview
Enhanced `tests/conftest.py` from 390 lines to 985 lines by adding 20+ new fixtures and comprehensive documentation.

## New Fixtures Added

### 1. Cache Management with Registration
- **`initialized_cache`** - Provides cache with MCP tools pre-registered
  - Auto-resets before/after tests
  - Eliminates manual setup in cache tests

### 2. Enhanced Temporary Project Fixtures
- **`temp_project_with_files`** - Project with ready-to-use sample files
  - Creates sample.py (simple function)
  - Creates complex.py (high complexity)
  - Creates duplicate1.py and duplicate2.py (similar code)
  - Returns dict with all file paths

### 3. MCP Tool Access
- **`mcp_tools`** - Easy tool accessor with validation
  - Auto-registers all tools
  - Returns function to get tool by name
  - Provides helpful errors if tool not found

### 4. Mock Subprocess
- **`mock_ast_grep_process`** - Pre-configured subprocess mock
  - Returns mock with returncode=0
  - Ready for subprocess.run patching

### 5. Test Coverage
- **`sample_test_paths`** - Source-to-test file mappings
  - Provides realistic test path examples
  - Useful for coverage detection tests

### 6. Complexity Analysis
- **`sample_complexity_thresholds`** - Standard thresholds
  - cyclomatic=10, cognitive=15, nesting_depth=4, lines=50
  - Ready-to-use ComplexityThresholds instance

- **`sample_function_code`** - Code snippets by complexity
  - simple: Basic function
  - high_cyclomatic: Many branches
  - high_nesting: Deep nesting
  - long_function: 100+ lines

### 7. Code Quality & Linting
- **`sample_linting_rule`** - Example LintingRule instance
  - Pre-configured test rule
  - Proper parameter order

- **`sample_rule_templates`** - Template examples
  - JavaScript and Python templates
  - Security and general categories

### 8. Backup Management
- **`backup_dir`** - Temporary backup directory
  - Creates .ast-grep-backups structure
  - Use with main.create_backup() functions

### 9. Multi-Language Code Samples
- **`sample_typescript_code`** - TypeScript function with types
- **`sample_javascript_code`** - JavaScript function
- **`sample_java_code`** - Java class and method

### 10. Schema.org Extended
- **`sample_schema_types`** - Type definitions
  - Thing, Person, Article examples
  - With properties and subClassOf

### 11. Deduplication Extended
- **`sample_deduplication_result`** - Analysis result
  - Candidates with scores
  - Risk levels and recommendations

## Usage Examples

### Simple Test with Tools
```python
def test_find_code(mcp_tools):
    find_code = mcp_tools("find_code")
    result = find_code(pattern="def $FUNC", project_folder="/path")
```

### Test with Project Files
```python
def test_duplication(temp_project_with_files):
    paths = temp_project_with_files
    assert Path(paths["sample_py"]).exists()
    result = detect_duplicates(paths["project"])
```

### Test with Cache
```python
def test_caching(initialized_cache):
    # Cache is ready, tools registered
    result = search_code(...)
    assert initialized_cache.cache is not None
```

### Test with Complexity
```python
def test_complexity(sample_complexity_thresholds):
    thresholds = sample_complexity_thresholds
    analyze(code, thresholds)
```

### Test with Backup
```python
def test_backup(backup_dir, temp_dir):
    test_file = Path(temp_dir) / "test.py"
    test_file.write_text("code")
    backup_id = main.create_backup([str(test_file)], temp_dir)
    assert (backup_dir / backup_id).exists()
```

## Documentation Improvements

Added comprehensive fixture documentation section at end of conftest.py:

- **14 fixture categories** organized and documented
- **Usage examples** for each major fixture
- **Cross-references** between related fixtures
- **Parameter explanations** with types

## Testing

Created `tests/unit/test_conftest_fixtures.py` with:
- **23 tests** covering all new fixtures
- **9 test classes** organized by fixture category
- **Fixture combination tests** showing realistic usage
- **All tests passing**

## Impact on Existing Tests

- **No breaking changes** - all existing fixtures work as before
- **Backward compatible** - existing tests don't need modifications
- **Can gradually adopt** new fixtures by refactoring test setup_method() calls

## File Statistics

- **Original size:** 390 lines
- **New size:** 985 lines
- **Lines added:** 595 lines (153% increase)
- **New fixtures:** 20+
- **Documentation:** 100+ lines of usage guide

## Common Test Patterns Eliminated

### Before (setup_method approach)
```python
def setup_method(self) -> None:
    self.temp_dir = tempfile.mkdtemp()
    self.project_folder = self.temp_dir
    self.test_file = os.path.join(self.temp_dir, "sample.py")
    with open(self.test_file, "w") as f:
        f.write("def hello():\n    print('hello')\n")
    self.rewrite_code = main.mcp.tools.get("rewrite_code")
```

### After (fixture approach)
```python
def test_something(temp_project_with_files, mcp_tools):
    paths = temp_project_with_files
    rewrite_code = mcp_tools("rewrite_code")
    # Test logic...
```

## Next Steps

1. **Gradually refactor existing tests** to use new fixtures
2. **Add more fixtures as patterns emerge** in test suite
3. **Consider parametrization** for complex scenarios
4. **Document fixture performance** if needed

## Key Benefits

1. **Reduced duplication** across test files
2. **Clearer test intent** - fixtures describe what's needed
3. **Easier test writing** - less boilerplate
4. **Better isolation** - fixtures auto-clean
5. **Type safety** - fixtures have proper type hints
6. **Discoverable** - comprehensive documentation in conftest.py
7. **Maintainable** - centralized fixture definitions
