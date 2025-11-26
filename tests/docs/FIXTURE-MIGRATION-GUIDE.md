# Fixture Migration Guide - Test Helper Methods to Factory Fixtures

**Date:** 2025-11-26
**Status:** Phase 3 - In Progress
**Files Affected:** 7 test files (286 tests)

## Overview

This guide documents the systematic conversion of helper methods from individual test files to shared factory fixtures in `conftest.py`. This migration reduces code duplication, improves test isolation, and makes tests more maintainable.

## Migration Goals

1. **Eliminate setup_method/teardown_method patterns** - Replace with pytest fixtures
2. **Convert helper methods to factory fixtures** - Centralize common test data creation
3. **Improve test isolation** - Automatic cleanup via pytest fixture lifecycle
4. **Reduce code duplication** - Share common patterns across test files
5. **Target: 15-20% code reduction** per file

## Available Factory Fixtures

All fixtures are available in `tests/unit/conftest.py`. Import them by adding them as test parameters.

### Core Fixtures

```python
@pytest.fixture(scope="module")
def mcp_main():
    """Import main module with mocked decorators and registered tools."""
    # Returns main module with all 25 MCP tools registered
```

### Tool Access Fixtures (Module-scoped)

All tool fixtures are module-scoped for performance (tools registered once per module):

```python
# Deduplication tools
apply_deduplication_tool
find_duplication_tool
analyze_deduplication_candidates_tool
benchmark_deduplication_tool

# Rewrite tools
rewrite_code_tool
list_backups_tool
rollback_rewrite_tool

# Search tools
batch_search_tool
find_code_tool
find_code_by_rule_tool

# Complexity tools
analyze_complexity_tool
test_sentry_integration_tool
```

**Usage:**
```python
def test_something(batch_search_tool):
    result = batch_search_tool(project_folder="./", queries=[...])
```

### File Setup Fixtures

```python
@pytest.fixture
def project_folder(tmp_path):
    """Temporary project folder (automatic cleanup)."""
    return tmp_path

@pytest.fixture
def simple_test_files(project_folder):
    """Create simple test files for basic testing."""
    # Returns: {"file1": path, "file2": path}

@pytest.fixture
def backup_test_files(project_folder):
    """Create test files with original content tracking."""
    # Returns: {"file1": path, "file2": path,
    #           "original_content1": str, "original_content2": str}

@pytest.fixture
def orchestration_test_files(project_folder):
    """Create test files in subdirectory with complex content."""
    # Returns: {"src_dir": path, "file1": path, "file2": path,
    #           "original_content1": str, "original_content2": str}
```

### Data Factory Fixtures

#### match_factory
```python
def test_something(match_factory):
    match = match_factory(
        text="hello",
        file="test.py",
        line=10,
        column=0
    )
    # Returns ast-grep match dictionary
```

#### query_factory
```python
def test_batch_search(query_factory):
    query = query_factory(
        id="q1",
        type="pattern",
        pattern="def $FUNC",
        language="python"
    )
    # Returns batch search query dictionary
```

#### yaml_rule_factory
```python
def test_rules(yaml_rule_factory):
    rule = yaml_rule_factory(
        id="test-rule",
        language="python",
        pattern="console.log($$$)",
        message="No console.log",
        severity="error"
    )
    # Returns YAML rule string
```

### Complex Object Factory Fixtures

#### refactoring_plan_factory
```python
def test_refactoring(refactoring_plan_factory):
    plan = refactoring_plan_factory(
        files=["file1.py", "file2.py"],
        new_contents=["# new 1", "# new 2"],
        strategy="extract_function",
        extracted_function="def extracted(): pass",
        function_name="extracted"
    )
    # Returns refactoring plan dictionary
```

#### rule_violation_factory
```python
def test_violations(rule_violation_factory):
    violation = rule_violation_factory(
        file="test.py",
        line=10,
        severity="error",
        rule_id="test-rule",
        message="Test message"
    )
    # Returns RuleViolation dictionary
```

#### linting_rule_factory
```python
def test_linting(linting_rule_factory):
    rule = linting_rule_factory(
        id="no-console",
        language="javascript",
        severity="warning",
        pattern="console.log($$$)",
        message="Avoid console.log"
    )
    # Returns LintingRule dictionary
```

### Mock Object Factory Fixtures

#### mock_popen_factory
```python
def test_subprocess(mock_popen_factory):
    mock_proc = mock_popen_factory(
        stdout_lines=['{"text": "match"}', '{"text": "match2"}'],
        returncode=0
    )
    # Returns configured Mock Popen process
```

#### mock_httpx_client
```python
async def test_http(mock_httpx_client):
    async with mock_httpx_client as client:
        response = await client.get("https://schema.org")
        data = response.json()
    # Returns AsyncMock httpx client
```

### State Management Fixtures (Auto-use)

These fixtures run automatically before/after each test:

```python
@pytest.fixture(autouse=True)
def reset_cache(mcp_main):
    """Auto-reset cache before each test."""
    # Automatically clears _query_cache before/after each test

@pytest.fixture(autouse=True)
def reset_schema_client(mcp_main):
    """Auto-reset Schema.org client before each test."""
    # Automatically resets _schema_org_client before/after each test
```

**No manual cache/client reset needed!** These fixtures handle it automatically.

## Migration Patterns

### Pattern 1: Replace setup_method/teardown_method

**Before:**
```python
class TestClass:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir
        self.tool = main.mcp.tools.get("some_tool")

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_something(self):
        result = self.tool(project_folder=self.project_folder)
```

**After:**
```python
class TestClass:
    def test_something(self, project_folder, some_tool_fixture):
        result = some_tool_fixture(project_folder=str(project_folder))
```

**Benefits:**
- No manual cleanup needed
- Automatic temp directory creation and removal
- Tool reference via fixture (module-scoped for performance)
- 5-8 lines removed per test class

### Pattern 2: Convert Helper Methods to Factory Usage

**Before:**
```python
class TestClass:
    def _create_query(self, id="q1", pattern="test"):
        return {
            "id": id,
            "type": "pattern",
            "pattern": pattern,
            "language": "python"
        }

    def test_query(self):
        query = self._create_query(id="query1", pattern="def $FUNC")
```

**After:**
```python
class TestClass:
    def test_query(self, query_factory):
        query = query_factory(id="query1", pattern="def $FUNC")
```

**Benefits:**
- Helper method removed (shared in conftest.py)
- Factory available to all test modules
- 6-10 lines removed per helper method

### Pattern 3: Replace Manual Cache Resets with Auto-use Fixture

**Before:**
```python
class TestClass:
    def setup_method(self):
        main._query_cache.cache.clear()
        main._query_cache.hits = 0
        main._query_cache.misses = 0

    def test_cache(self):
        # Test code
```

**After:**
```python
class TestClass:
    # reset_cache fixture runs automatically
    def test_cache(self):
        # Test code - cache already reset
```

**Benefits:**
- No manual reset code needed
- Automatic isolation between tests
- 4-6 lines removed per test class

### Pattern 4: Replace Repeated Mock Setup with Factory

**Before:**
```python
def test_subprocess(self):
    mock_proc = Mock()
    mock_proc.stdout = iter(['{"text": "match"}'])
    mock_proc.poll.return_value = 0
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0
    # ... more configuration
```

**After:**
```python
def test_subprocess(self, mock_popen_factory):
    mock_proc = mock_popen_factory(
        stdout_lines=['{"text": "match"}'],
        returncode=0
    )
```

**Benefits:**
- Mock configuration centralized
- Consistent mock behavior across tests
- 8-12 lines removed per mock setup

## Migration Checklist

For each test file:

- [ ] **Analyze setup_method/teardown_method**
  - Identify temp directory creation → Use `project_folder` fixture
  - Identify tool references → Use tool access fixtures
  - Identify cache resets → Remove (auto-use fixture handles it)

- [ ] **Identify helper methods**
  - Data builders (_create_query, _create_match) → Use factory fixtures
  - Complex object builders → Use factory fixtures
  - Mock builders → Use mock factory fixtures

- [ ] **Update test signatures**
  - Add fixture parameters to test methods
  - Remove self.attribute references
  - Use fixture return values directly

- [ ] **Remove duplicated code**
  - Delete setup_method/teardown_method
  - Delete helper methods (now in conftest.py)
  - Remove manual cleanup code

- [ ] **Verify tests pass**
  - Run: `uv run pytest tests/unit/test_file.py -v`
  - Check: All tests pass
  - Measure: Lines of code reduction

- [ ] **Document changes**
  - Update test file docstring
  - Note fixtures used
  - Record metrics (lines removed, performance)

## Files to Migrate (Phase 3)

| File | Tests | Status | Priority |
|------|-------|--------|----------|
| test_batch.py | 18 | Pending | High |
| test_cache.py | 26 | Pending | High |
| test_unit.py | 57 | Pending | High |
| test_edge_cases.py | 18 | Pending | Medium |
| test_phase2.py | 21 | Pending | Medium |
| test_schema.py | 52 | Pending | Medium |
| test_standards_enforcement.py | 94 | Pending | Low (complex) |

**Total:** 286 tests across 7 files

## Success Metrics

Target metrics for each file migration:

- **Code reduction:** 15-20% fewer lines
- **Test pass rate:** 100% (no regressions)
- **Performance:** ≤5% slower (or faster with module-scoped fixtures)
- **Maintainability:** Reduced duplication, clearer dependencies

## Example Migration: test_batch.py

### Before (setup_method pattern)
```python
class TestBatchSearchBasic:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir
        self.batch_search = main.mcp.tools.get("batch_search")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_batch_search_single_query(self):
        queries = [
            {
                "id": "query1",
                "type": "pattern",
                "pattern": "def $FUNC",
                "language": "python"
            }
        ]
        result = self.batch_search(project_folder=self.project_folder, queries=queries)
```

### After (fixture pattern)
```python
class TestBatchSearchBasic:
    def test_batch_search_single_query(self, project_folder, batch_search_tool, query_factory):
        queries = [query_factory(id="query1", pattern="def $FUNC")]
        result = batch_search_tool(project_folder=str(project_folder), queries=queries)
```

**Improvements:**
- Removed setup_method/teardown_method (10 lines)
- Query creation simplified with factory
- Automatic temp directory cleanup
- 12 lines → 3 lines (75% reduction)

## Common Issues and Solutions

### Issue: Fixture not found
**Error:** `fixture 'some_fixture' not found`
**Solution:** Ensure fixture is defined in conftest.py and spell check the parameter name

### Issue: Module vs. function scope
**Error:** Fixtures have conflicting scopes
**Solution:** Tool fixtures are module-scoped, file fixtures are function-scoped. Don't mix setup_method with fixtures.

### Issue: Autouse fixture not running
**Error:** Cache not reset between tests
**Solution:** Check that `mcp_main` is included in a fixture dependency chain (tool fixtures depend on it)

### Issue: Path type mismatch
**Error:** `TypeError: expected str, got PosixPath`
**Solution:** Convert pathlib.Path to str: `str(project_folder)`

## References

- [Phase 2 Completion Report](fixture-migration-phase2-report.md) - test_apply_deduplication.py migration
- [pytest fixtures documentation](https://docs.pytest.org/en/stable/fixture.html)
- [conftest.py](../conftest.py) - All available fixtures

## Next Steps

1. Migrate high-priority files first (test_batch.py, test_cache.py, test_unit.py)
2. Validate each migration with full test run
3. Document metrics and improvements
4. Create Phase 3 completion report
5. Update REMAINING-TASKS-SUMMARY.md with progress
