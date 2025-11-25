# Fixture Quick Reference Guide

Quick lookup for available test fixtures in `tests/conftest.py`.

## Cache & MCP Tools

```python
# Get initialized cache with tools registered
def test_something(initialized_cache):
    cache = initialized_cache
    assert cache.cache is not None

# Access any MCP tool with validation
def test_tool(mcp_tools):
    find_code = mcp_tools("find_code")
    analyze = mcp_tools("analyze_complexity")
```

## Project & Files

```python
# Basic temp directory (auto-cleanup)
def test_with_temp(temp_dir):
    file = Path(temp_dir) / "test.txt"

# Project with src/tests/docs structure
def test_with_project(temp_project_dir):
    src = Path(temp_project_dir) / "src"

# Project with sample code files
def test_with_files(temp_project_with_files):
    paths = temp_project_with_files
    # paths["project"], paths["sample_py"],
    # paths["complex_py"], paths["duplicate1_py"], etc.

# Create custom files on-the-fly
def test_custom_files(create_test_file):
    file = create_test_file("test.py", "def foo(): pass")
```

## Code Samples

```python
# Language-specific samples
def test_multi_lang(
    sample_python_code,
    sample_typescript_code,
    sample_javascript_code,
    sample_java_code
):
    # Use any language sample

# Complexity samples
def test_complexity(sample_function_code):
    code = sample_function_code
    # code["simple"], code["high_cyclomatic"],
    # code["high_nesting"], code["long_function"]

# Duplicate code samples
def test_duplicates(sample_duplicate_code):
    code1, code2 = sample_duplicate_code
```

## Complexity Analysis

```python
# Standard thresholds
def test_thresholds(sample_complexity_thresholds):
    t = sample_complexity_thresholds
    # t.cyclomatic=10, t.cognitive=15,
    # t.nesting_depth=4, t.lines=50
```

## Code Quality & Linting

```python
# Sample linting rule
def test_rule(sample_linting_rule):
    rule = sample_linting_rule
    assert rule.id == "test-rule"

# Rule templates
def test_templates(sample_rule_templates):
    templates = sample_rule_templates
    # List of template dicts
```

## Backup & Rollback

```python
# Backup directory
def test_backup(backup_dir, temp_dir):
    # Create file
    file = Path(temp_dir) / "test.py"
    file.write_text("code")

    # Create backup
    backup_id = main.create_backup([str(file)], temp_dir)

    # Verify
    assert (backup_dir / backup_id).exists()
```

## Test Coverage

```python
# Sample test paths mapping
def test_coverage(sample_test_paths):
    paths = sample_test_paths
    assert paths["src/module.py"] == "tests/test_module.py"
```

## Schema.org

```python
# Mock client
def test_schema(mock_schema_client):
    types = mock_schema_client.search_schemas("Person")

# Sample types
def test_types(sample_schema_types):
    types = sample_schema_types
    # Thing, Person, Article examples
```

## Deduplication

```python
# Component instances
def test_dedup(
    duplication_detector,
    pattern_analyzer,
    code_generator,
    duplication_ranker,
    recommendation_engine
):
    # Ready-to-use instances

# Sample data
def test_matches(sample_duplication_matches):
    matches = sample_duplication_matches

def test_result(sample_deduplication_result):
    result = sample_deduplication_result
    candidates = result["candidates"]
```

## Subprocess Mocking

```python
# Mock ast-grep process
def test_subprocess(mock_ast_grep_process, monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: mock_ast_grep_process
    )
```

## Parametrization

```python
# Test across all languages
def test_all_languages(language):
    # Runs for: python, javascript, typescript,
    # java, go, rust

# Test across similarity thresholds
def test_similarity(similarity_threshold):
    # Runs for: 0.7, 0.8, 0.85, 0.9, 0.95
```

## Fixture Combinations

Combine multiple fixtures for complex scenarios:

```python
def test_complex_scenario(
    initialized_cache,
    temp_project_with_files,
    mcp_tools,
    sample_complexity_thresholds,
    backup_dir
):
    # Cache ready, project setup, tools available,
    # thresholds configured, backups enabled
    paths = temp_project_with_files
    analyze = mcp_tools("analyze_complexity")
    thresholds = sample_complexity_thresholds

    # Run analysis
    result = analyze(
        project_folder=paths["project"],
        language="python",
        cyclomatic_threshold=thresholds.cyclomatic,
        cognitive_threshold=thresholds.cognitive,
        nesting_threshold=thresholds.nesting_depth,
        length_threshold=thresholds.lines
    )
```

## Auto-Use Fixtures

These run automatically (don't need to be specified):

- `reset_module_state` - Cleans up between tests

## Tips

1. **Use `mcp_tools` instead of manual tool registration**
   ```python
   # Before
   main.register_mcp_tools()
   tool = main.mcp.tools.get("tool_name")

   # After
   def test(mcp_tools):
       tool = mcp_tools("tool_name")
   ```

2. **Use `temp_project_with_files` instead of manual file creation**
   ```python
   # Before
   def setup_method(self):
       self.temp_dir = tempfile.mkdtemp()
       self.file = os.path.join(self.temp_dir, "test.py")
       with open(self.file, "w") as f:
           f.write("def hello(): pass")

   # After
   def test(temp_project_with_files):
       paths = temp_project_with_files
       # Files already exist!
   ```

3. **Use `initialized_cache` for cache tests**
   ```python
   # Before
   def setup_method(self):
       main._query_cache = QueryCache(max_size=10, ttl_seconds=300)
       main.CACHE_ENABLED = True
       main.register_mcp_tools()

   # After
   def test(initialized_cache):
       # Cache and tools ready!
   ```

## Full Documentation

See `tests/conftest.py` for complete fixture documentation with usage examples.

See `tests/CONFTEST_ENHANCEMENTS.md` for detailed enhancement information.

See `tests/unit/test_conftest_fixtures.py` for 23 fixture usage examples.
