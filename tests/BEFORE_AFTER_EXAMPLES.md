# Before & After: Test Refactoring Examples

Examples showing how to refactor existing tests to use the new conftest.py fixtures.

## Example 1: Cache Tests

### Before (from test_cache.py)
```python
class TestCacheIntegration:
    def setup_method(self) -> None:
        """Reset global cache before each test"""
        main._query_cache = QueryCache(max_size=10, ttl_seconds=300)
        main.CACHE_ENABLED = True
        main.register_mcp_tools()

    def test_find_code_cache_miss_then_hit(self) -> None:
        """Test that find_code caches results correctly"""
        find_code = main.mcp.tools.get("find_code")
        # Test logic...
```

### After (using new fixtures)
```python
class TestCacheIntegration:
    def test_find_code_cache_miss_then_hit(
        self, initialized_cache, mcp_tools
    ) -> None:
        """Test that find_code caches results correctly"""
        find_code = mcp_tools("find_code")
        # Test logic...
        # Cache is automatically initialized and cleaned up
```

**Benefits:**
- 5 lines of setup eliminated
- More readable test signature
- Automatic cleanup
- Reusable across tests

---

## Example 2: Rewrite Tests with Files

### Before (from test_rewrite.py)
```python
class TestRewriteCode:
    def setup_method(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir
        self.test_file = os.path.join(self.temp_dir, "sample.py")
        with open(self.test_file, "w") as f:
            f.write("def hello():\n    print('hello')\n")
        self.rewrite_code = main.mcp.tools.get("rewrite_code")

    def teardown_method(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rewrite_code_dry_run_mode(self) -> None:
        """Test rewrite_code in dry-run mode"""
        # Use self.test_file and self.rewrite_code
```

### After (using new fixtures)
```python
class TestRewriteCode:
    def test_rewrite_code_dry_run_mode(
        self, temp_project_with_files, mcp_tools
    ) -> None:
        """Test rewrite_code in dry-run mode"""
        paths = temp_project_with_files
        rewrite_code = mcp_tools("rewrite_code")
        # Use paths["sample_py"] - file already exists!
```

**Benefits:**
- 11 lines of setup/teardown eliminated
- No manual file creation
- No manual cleanup needed
- Multiple sample files available

---

## Example 3: Complexity Analysis Tests

### Before (manual setup)
```python
def test_complexity_analysis():
    thresholds = ComplexityThresholds(
        cyclomatic=10,
        cognitive=15,
        nesting_depth=4,
        lines=50
    )

    code = """def complex_function(x, y):
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x
    else:
        return y
    """

    # Run analysis...
```

### After (using fixtures)
```python
def test_complexity_analysis(
    sample_complexity_thresholds,
    sample_function_code
):
    thresholds = sample_complexity_thresholds
    code = sample_function_code["high_cyclomatic"]
    # Run analysis...
```

**Benefits:**
- Standard thresholds used consistently
- Multiple complexity examples available
- No hardcoded test data
- Easy to test different complexity levels

---

## Example 4: Backup Tests

### Before (manual backup directory)
```python
class TestBackupManagement:
    def setup_method(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir
        self.backup_path = os.path.join(
            self.temp_dir, ".ast-grep-backups"
        )
        os.makedirs(self.backup_path, exist_ok=True)

        self.file1 = os.path.join(self.temp_dir, "file1.py")
        with open(self.file1, "w") as f:
            f.write("def test(): pass")

    def teardown_method(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)
```

### After (using fixtures)
```python
class TestBackupManagement:
    def test_create_backup(
        self, backup_dir, temp_project_with_files
    ):
        paths = temp_project_with_files
        # backup_dir already exists
        # Sample files already created
        backup_id = main.create_backup(
            [paths["sample_py"]], paths["project"]
        )
```

**Benefits:**
- Backup directory pre-created
- Sample files available
- Automatic cleanup
- Clear separation of concerns

---

## Example 5: Multi-Language Tests

### Before (manual language samples)
```python
def test_language_support():
    python_code = "def foo(): pass"
    js_code = "function foo() {}"
    ts_code = "function foo(): void {}"
    java_code = "public void foo() {}"

    for code in [python_code, js_code, ts_code, java_code]:
        # Test logic...
```

### After (using fixtures)
```python
def test_language_support(
    sample_python_code,
    sample_javascript_code,
    sample_typescript_code,
    sample_java_code
):
    for code in [
        sample_python_code,
        sample_javascript_code,
        sample_typescript_code,
        sample_java_code
    ]:
        # Test logic...
```

**Benefits:**
- Consistent, realistic code samples
- Proper syntax for each language
- Type annotations included where appropriate
- Easy to add more languages

---

## Example 6: Deduplication Tests

### Before (manual component creation)
```python
def test_deduplication():
    from ast_grep_mcp.features.deduplication.detector import DuplicationDetector
    from ast_grep_mcp.features.deduplication.ranker import DuplicationRanker
    from ast_grep_mcp.core.executor import run_ast_grep

    detector = DuplicationDetector(run_ast_grep)
    ranker = DuplicationRanker()

    # Test logic...
```

### After (using fixtures)
```python
def test_deduplication(duplication_detector, duplication_ranker):
    # Components already instantiated and ready
    # Test logic...
```

**Benefits:**
- No import boilerplate
- Consistent initialization
- Easy to test component interactions
- Can mock at fixture level if needed

---

## Example 7: Tool Access with Error Handling

### Before (manual tool access)
```python
def test_tool():
    main.register_mcp_tools()
    tool = main.mcp.tools.get("find_code")
    if tool is None:
        pytest.skip("Tool not found")
    # Test logic...
```

### After (using mcp_tools fixture)
```python
def test_tool(mcp_tools):
    tool = mcp_tools("find_code")
    # Raises ValueError with helpful message if not found
    # Test logic...
```

**Benefits:**
- Automatic tool registration
- Better error messages
- No None checks needed
- Lists available tools on error

---

## Example 8: Subprocess Mocking

### Before (manual mock setup)
```python
def test_ast_grep_execution(monkeypatch):
    from unittest.mock import Mock

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: mock_result
    )
    # Test logic...
```

### After (using fixture)
```python
def test_ast_grep_execution(mock_ast_grep_process, monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: mock_ast_grep_process
    )
    # Test logic...
```

**Benefits:**
- Pre-configured mock
- Consistent mock behavior
- Less boilerplate
- Easy to customize if needed

---

## Example 9: Coverage Detection Tests

### Before (hardcoded paths)
```python
def test_coverage_detection():
    test_paths = {
        "src/module.py": "tests/test_module.py",
        "src/utils.py": "tests/test_utils.py",
    }
    # Test logic...
```

### After (using fixture)
```python
def test_coverage_detection(sample_test_paths):
    test_paths = sample_test_paths
    # Test logic with realistic path patterns
```

**Benefits:**
- Realistic path patterns
- Multiple conventions included
- Easy to extend
- Consistent across tests

---

## Example 10: Complex Integration Test

### Before (massive setup)
```python
class TestIntegration:
    def setup_method(self):
        # Setup temp dir
        self.temp_dir = tempfile.mkdtemp()

        # Create files
        self.file1 = os.path.join(self.temp_dir, "file1.py")
        with open(self.file1, "w") as f:
            f.write("def foo(): pass")

        # Setup cache
        main._query_cache = QueryCache()
        main.CACHE_ENABLED = True

        # Register tools
        main.register_mcp_tools()

        # Get tools
        self.find_code = main.mcp.tools.get("find_code")
        self.analyze = main.mcp.tools.get("analyze_complexity")

        # Setup thresholds
        self.thresholds = ComplexityThresholds(
            cyclomatic=10,
            cognitive=15,
            nesting_depth=4,
            lines=50
        )

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if main._query_cache:
            main._query_cache.cache.clear()
```

### After (using multiple fixtures)
```python
class TestIntegration:
    def test_workflow(
        self,
        initialized_cache,
        temp_project_with_files,
        mcp_tools,
        sample_complexity_thresholds
    ):
        # Everything is ready!
        paths = temp_project_with_files
        find_code = mcp_tools("find_code")
        analyze = mcp_tools("analyze_complexity")
        thresholds = sample_complexity_thresholds

        # Test logic...
```

**Benefits:**
- 30+ lines of setup eliminated
- No teardown needed
- Clear test dependencies
- Easy to add more fixtures
- Automatic cleanup

---

## Summary

### Lines of Code Saved
- **Example 1:** 5 lines setup → 0 lines (fixtures in params)
- **Example 2:** 11 lines setup/teardown → 0 lines
- **Example 3:** 15 lines setup → 2 lines
- **Example 4:** 14 lines setup/teardown → 0 lines
- **Example 10:** 30+ lines setup/teardown → 0 lines

### Common Patterns Eliminated
1. ✅ `tempfile.mkdtemp()` + `shutil.rmtree()`
2. ✅ Manual file creation with `open()` + `write()`
3. ✅ `main.register_mcp_tools()`
4. ✅ `main.mcp.tools.get()`
5. ✅ Manual cache initialization
6. ✅ Manual mock setup
7. ✅ Hardcoded test data
8. ✅ Manual cleanup in teardown_method

### Migration Strategy
1. Start with new tests - use fixtures from day 1
2. Refactor high-duplication test files first
3. Convert tests incrementally (no rush)
4. Keep setup_method for complex custom setups
5. Mix fixtures with custom setup when needed
