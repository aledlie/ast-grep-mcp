# Fixture Cookbook

**Version:** 1.0
**Date:** 2025-11-25

Real-world testing recipes using pytest fixtures for common scenarios in the ast-grep-mcp test suite.

## Table of Contents

1. [File System Operations](#file-system-operations)
2. [Subprocess & Command Execution](#subprocess--command-execution)
3. [Caching & State Management](#caching--state-management)
4. [MCP Tool Testing](#mcp-tool-testing)
5. [Mock & Patch Patterns](#mock--patch-patterns)
6. [Test Data Generation](#test-data-generation)
7. [Performance Testing](#performance-testing)
8. [Integration Testing](#integration-testing)

## File System Operations

### Recipe 1: Test File Creation and Modification

**Problem:** Need to create test files, modify them, verify changes

**Solution:**
```python
def test_file_modification(temp_project_with_files):
    """Test modifying files using temp_project_with_files fixture."""
    sample_py = temp_project_with_files["sample_py"]

    # Read original
    with open(sample_py) as f:
        original = f.read()

    # Modify
    with open(sample_py, "w") as f:
        f.write(original.replace("hello", "world"))

    # Verify
    with open(sample_py) as f:
        modified = f.read()
    assert "world" in modified
    # Cleanup automatic via fixture
```

### Recipe 2: Multiple Test Files with Specific Content

**Before (setup_method):**
```python
class TestRewrite:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file1 = os.path.join(self.temp_dir, "file1.py")
        self.file2 = os.path.join(self.temp_dir, "file2.py")
        with open(self.file1, "w") as f:
            f.write("# File 1")
        with open(self.file2, "w") as f:
            f.write("# File 2")
```

**After (fixtures):**
```python
def test_rewrite(temp_project_with_files):
    """Use provided files or create custom ones."""
    project = temp_project_with_files["project"]

    # Use existing files
    sample_py = temp_project_with_files["sample_py"]

    # Or create custom file
    custom_py = Path(project) / "custom.py"
    custom_py.write_text("# Custom")
```

### Recipe 3: Backup and Rollback Testing

```python
def test_backup_creation(temp_project_with_files, mcp_tools):
    """Test that rewrite creates backups."""
    rewrite_code = mcp_tools("rewrite_code")
    project = temp_project_with_files["project"]

    result = rewrite_code(
        project_folder=project,
        pattern="hello",
        replacement="world",
        language="python"
    )

    # Verify backup created
    backup_dir = Path(project) / ".ast-grep-backups"
    assert backup_dir.exists()
    backups = list(backup_dir.glob("backup-*"))
    assert len(backups) >= 1
```

## Subprocess & Command Execution

### Recipe 4: Mock Streaming Command Output

**Problem:** Test streaming ast-grep output without running actual command

**Solution:**
```python
def test_streaming_search(mock_popen):
    """Test streaming results using mock_popen fixture."""
    # Configure mock to return streaming output
    mock_popen.return_value.stdout = iter([
        '{"text": "result 1"}',
        '{"text": "result 2"}',
        '{"text": "result 3"}'
    ])
    mock_popen.return_value.poll.return_value = None
    mock_popen.return_value.wait.return_value = 0

    # Run test
    from src.ast_grep_mcp.core.executor import stream_ast_grep_results
    results = list(stream_ast_grep_results(...))

    assert len(results) == 3
    assert results[0]["text"] == "result 1"
```

### Recipe 5: Mock Non-Streaming Commands

```python
def test_rewrite_command(mock_subprocess_run):
    """Test rewrite using mock_subprocess_run fixture."""
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stdout = "Rewrite successful"

    from src.ast_grep_mcp.features.rewrite.service import rewrite_code_impl
    result = rewrite_code_impl(...)

    assert "success" in result.lower()
    mock_subprocess_run.assert_called_once()
```

## Caching & State Management

### Recipe 6: Test Cache Operations

```python
def test_cache_basic(initialized_cache):
    """Test basic cache operations."""
    # Cache already initialized and ready
    initialized_cache.set("key", "value")
    assert initialized_cache.get("key") == "value"

    # Test expiration
    initialized_cache.set("temp", "data", ttl=0)
    time.sleep(0.1)
    assert initialized_cache.get("temp") is None
```

### Recipe 7: Test Without Cache

```python
def test_without_cache(cache_disabled):
    """Test behavior with cache disabled."""
    # cache_disabled fixture sets CACHE_ENABLED=False
    from src.ast_grep_mcp.features.search.service import find_code_impl

    result1 = find_code_impl(...)
    result2 = find_code_impl(...)  # Should not use cache

    # Each call executes ast-grep
```

### Recipe 8: Test Cache Hit/Miss

```python
def test_cache_effectiveness(initialized_cache, mock_subprocess_run):
    """Test that cache reduces subprocess calls."""
    from src.ast_grep_mcp.features.search.tools import find_code_tool

    # First call - cache miss
    result1 = find_code_tool(pattern="test", project_folder="/tmp")
    assert mock_subprocess_run.call_count == 1

    # Second call - cache hit
    result2 = find_code_tool(pattern="test", project_folder="/tmp")
    assert mock_subprocess_run.call_count == 1  # No additional call
```

## MCP Tool Testing

### Recipe 9: Test MCP Tool Registration

```python
def test_tool_registration(mcp_tools):
    """Test that MCP tools are properly registered."""
    find_code = mcp_tools("find_code")
    assert find_code is not None
    assert callable(find_code)

    # Verify tool can be called
    result = find_code(pattern="test", ...)
    assert result is not None
```

### Recipe 10: Test Multiple Tools Together

```python
def test_search_and_rewrite(temp_project_with_files, mcp_tools):
    """Test searching and rewriting together."""
    find_code = mcp_tools("find_code")
    rewrite_code = mcp_tools("rewrite_code")
    project = temp_project_with_files["project"]

    # Find matches
    results = find_code(pattern="hello", project_folder=project)
    assert len(results) > 0

    # Rewrite matches
    rewrite_result = rewrite_code(
        pattern="hello",
        replacement="world",
        project_folder=project
    )
    assert "success" in rewrite_result.lower()
```

## Mock & Patch Patterns

### Recipe 11: Mock ast-grep Success

```python
def test_successful_search(mock_ast_grep_success):
    """Test successful search using mock_ast_grep_success fixture."""
    # mock_ast_grep_success already configured for success
    from src.ast_grep_mcp.features.search.service import find_code_impl

    result = find_code_impl(pattern="test", ...)
    assert len(result) > 0
```

### Recipe 12: Mock ast-grep Failure

```python
def test_failed_search(mock_ast_grep_failure):
    """Test search failure handling."""
    from src.ast_grep_mcp.features.search.service import find_code_impl

    with pytest.raises(Exception):
        find_code_impl(pattern="test", ...)
```

### Recipe 13: Combine Multiple Mocks

```python
def test_complex_scenario(mock_popen, mock_subprocess_run, temp_dir):
    """Test scenario requiring multiple mocks."""
    # mock_popen for streaming
    mock_popen.return_value.stdout = iter(['{"text": "result"}'])

    # mock_subprocess_run for non-streaming
    mock_subprocess_run.return_value.returncode = 0

    # Run test in temp_dir
    # ... test code ...
```

## Test Data Generation

### Recipe 14: Use Sample Data Fixtures

```python
def test_with_sample_data(sample_search_result):
    """Test using sample_search_result fixture."""
    # sample_search_result provides realistic test data
    assert "text" in sample_search_result
    assert "file" in sample_search_result

    # Use in your test
    result = process_search_result(sample_search_result)
    assert result is not None
```

### Recipe 15: Parametrize with Sample Data

```python
@pytest.mark.parametrize("data_fixture", [
    "sample_search_result",
    "sample_duplication_data",
    "sample_schema_data"
], indirect=True)
def test_data_processing(data_fixture):
    """Test with different sample data types."""
    result = process_data(data_fixture)
    assert result is not None
```

## Performance Testing

### Recipe 16: Benchmark with Fixtures

```python
def test_search_performance(temp_project_with_files, benchmark):
    """Benchmark search performance."""
    project = temp_project_with_files["project"]

    def search():
        from src.ast_grep_mcp.features.search.service import find_code_impl
        return find_code_impl(pattern="def", project_folder=project)

    result = benchmark(search)
    assert len(result) > 0
```

### Recipe 17: Test Fixture Overhead

```python
def test_fixture_overhead(benchmark):
    """Measure fixture overhead."""
    def with_fixture(temp_dir):
        # Minimal operation
        return os.path.exists(temp_dir)

    # Benchmark includes fixture setup/teardown
    result = benchmark.pedantic(
        with_fixture,
        setup=lambda: pytest.fixture_request.getfixturevalue("temp_dir")
    )
```

## Integration Testing

### Recipe 18: End-to-End Workflow

```python
def test_complete_workflow(temp_project_with_files, mcp_tools):
    """Test complete search -> analyze -> rewrite workflow."""
    project = temp_project_with_files["project"]
    find_code = mcp_tools("find_code")
    find_duplication = mcp_tools("find_duplication")
    rewrite_code = mcp_tools("rewrite_code")

    # 1. Search for patterns
    results = find_code(pattern="def", project_folder=project)
    assert len(results) > 0

    # 2. Find duplicates
    duplicates = find_duplication(project_folder=project, language="python")

    # 3. Rewrite if needed
    if len(duplicates) > 0:
        rewrite_result = rewrite_code(
            pattern=duplicates[0]["pattern"],
            replacement="improved_version",
            project_folder=project
        )
        assert "success" in rewrite_result.lower()
```

### Recipe 19: Test Configuration

```python
def test_custom_config(test_config, temp_dir):
    """Test with custom configuration."""
    # test_config provides default test configuration
    config = test_config.copy()
    config["max_results"] = 5
    config["cache_enabled"] = False

    from src.ast_grep_mcp.features.search.service import find_code_impl
    result = find_code_impl(..., config=config)

    assert len(result) <= 5
```

## Tips & Best Practices

### Tip 1: Fixture Composition

```python
@pytest.fixture
def prepared_project(temp_project_with_files, mcp_tools):
    """Compose fixtures for common scenario."""
    project = temp_project_with_files["project"]
    find_code = mcp_tools("find_code")

    # Pre-populate with specific data
    sample_py = temp_project_with_files["sample_py"]
    Path(sample_py).write_text("def example(): pass")

    return {
        "project": project,
        "find_code": find_code,
        "sample_file": sample_py
    }

def test_with_composition(prepared_project):
    """Use composed fixture."""
    results = prepared_project["find_code"](
        pattern="def",
        project_folder=prepared_project["project"]
    )
    assert len(results) > 0
```

### Tip 2: Fixture Parametrization

```python
@pytest.fixture(params=["python", "typescript", "javascript"])
def language(request):
    """Parametrize by language."""
    return request.param

def test_multi_language(temp_project_with_files, language):
    """Test runs 3 times, once per language."""
    # Test code here
    pass
```

### Tip 3: Fixture Scope for Performance

```python
@pytest.fixture(scope="module")
def expensive_setup():
    """Run once per module, not per test."""
    # Expensive operation
    data = load_large_dataset()
    return data

def test_1(expensive_setup):
    # Uses cached expensive_setup
    pass

def test_2(expensive_setup):
    # Reuses same expensive_setup
    pass
```

## Migration Patterns

### Pattern 1: Self Attributes → Fixtures

**Before:**
```python
class TestExample:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache = QueryCache()

    def test_something(self):
        file_path = os.path.join(self.temp_dir, "test.txt")
        self.cache.set("key", "value")
```

**After:**
```python
def test_something(temp_dir, initialized_cache):
    file_path = os.path.join(temp_dir, "test.txt")
    initialized_cache.set("key", "value")
```

### Pattern 2: Complex Setup → Helper + Fixtures

**Before:**
```python
class TestComplex:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self._create_project_structure()  # 20 lines
        self._initialize_mocks()          # 15 lines

    def _create_project_structure(self):
        # ... 20 lines ...

    def _initialize_mocks(self):
        # ... 15 lines ...
```

**After:**
```python
def create_custom_project(temp_dir):
    """Helper function for complex setup."""
    # ... project structure creation ...
    return project_path

def test_complex(temp_dir, mock_popen):
    project = create_custom_project(temp_dir)
    # mock_popen already initialized
    # ... test code ...
```

## Resources

- [FIXTURE_QUICK_REFERENCE.md](FIXTURE_QUICK_REFERENCE.md) - Quick lookup
- [FIXTURE_MIGRATION_GUIDE.md](FIXTURE_MIGRATION_GUIDE.md) - Step-by-step migration
- [FIXTURE_GOVERNANCE.md](FIXTURE_GOVERNANCE.md) - Proposing new fixtures
- [Pytest fixture docs](https://docs.pytest.org/en/stable/fixture.html)
