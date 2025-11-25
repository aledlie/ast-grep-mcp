# Fixture Migration Guide

**Version:** 1.0
**Date:** 2025-11-25
**Status:** Active

## Table of Contents

1. [Overview](#overview)
2. [When to Migrate](#when-to-migrate)
3. [Step-by-Step Migration Process](#step-by-step-migration-process)
4. [Common Migration Patterns](#common-migration-patterns)
5. [Before & After Examples](#before--after-examples)
6. [Troubleshooting](#troubleshooting)
7. [Validation Checklist](#validation-checklist)

## Overview

This guide provides step-by-step instructions for migrating existing tests from `setup_method`/`teardown_method` patterns to pytest fixtures.

### Why Migrate?

**Benefits:**
- **Reduced boilerplate** - Eliminate repetitive setup/teardown code
- **Better reusability** - Share setup logic across multiple tests
- **Improved clarity** - Explicit dependencies via function parameters
- **Automatic cleanup** - Fixtures handle teardown automatically
- **Composability** - Easily combine multiple fixtures

**When NOT to migrate:**
- Tests work well and don't need changes
- File has very few tests (<5)
- Setup is highly specific to individual tests
- Team is unfamiliar with fixtures (train first)

### Prerequisites

Before migrating, ensure you:
1. Have read [FIXTURE_QUICK_REFERENCE.md](FIXTURE_QUICK_REFERENCE.md)
2. Understand pytest fixture basics
3. Have baseline test results (`pytest -v`)
4. Have created a backup branch

## When to Migrate

### Trigger Conditions (Migrate NOW)

1. **Rewriting test class** - Already modifying substantial test code
2. **Adding 10+ new tests** - File growing significantly
3. **High pain score** - File scored ≥70 in baseline analysis
4. **Maintenance issues** - Frequent test failures or flakiness

### Defer Conditions (Wait)

1. **Low pain score** - File scored <40 in baseline analysis
2. **Working well** - Tests stable and maintainable
3. **Few tests** - <5 tests in file
4. **High risk** - Complex mocking or external dependencies

### Check Your Score

```bash
# Score a specific file
python tests/scripts/score_test_file.py tests/unit/test_cache.py --detailed

# See all scores
python tests/scripts/score_test_file.py --all
```

## Step-by-Step Migration Process

### Phase 1: Preparation (5-10 minutes)

**1. Create feature branch**
```bash
git checkout -b refactor/migrate-test-cache
```

**2. Run baseline tests**
```bash
pytest tests/unit/test_cache.py -v > baseline_results.txt
```

**3. Analyze current patterns**
```bash
# Score the file
python tests/scripts/score_test_file.py tests/unit/test_cache.py --detailed

# Identify patterns
grep -n "def setup_method" tests/unit/test_cache.py
grep -n "self\." tests/unit/test_cache.py | head -20
```

**4. Review available fixtures**
```bash
# See what fixtures exist
grep -n "@pytest.fixture" tests/conftest.py
```

### Phase 2: Identify Fixture Needs (10-15 minutes)

**1. List self attributes**

Extract all `self.attribute` assignments from `setup_method`:

```python
# Example from test_cache.py
def setup_method(self):
    self.cache = QueryCache(max_size=10, ttl_seconds=300)  # → initialized_cache fixture
    self.temp_dir = tempfile.mkdtemp()                     # → temp_dir fixture
    self.test_file = os.path.join(self.temp_dir, "test.py") # → temp_project_with_files fixture
```

**2. Match to existing fixtures**

| Self Attribute | Existing Fixture | Notes |
|----------------|------------------|-------|
| `self.temp_dir` | `temp_dir` | Direct replacement |
| `self.cache` | `initialized_cache` | Cache with MCP tools |
| `self.test_file` | `temp_project_with_files["sample_py"]` | Multi-file project |
| `self.tool` | `mcp_tools("tool_name")` | Factory fixture |
| `self.mock_run` | `mock_subprocess_run` | Mock subprocess.run |

**3. Identify gaps**

If no fixture exists:
- Check if pattern appears in 3+ files → **Propose new fixture**
- Unique to this file → **Keep as helper function**

### Phase 3: Create Migration Plan (5 minutes)

**Document your plan:**

```markdown
## Migration Plan: test_cache.py

**Target Score:** 38.9 → <25 (defer category)

**Changes:**
1. Remove setup_method (5 lines)
2. Remove teardown_method (3 lines)
3. Update 12 test functions to use fixtures
4. Replace 8 self.cache references
5. Replace 4 self.temp_dir references

**Fixtures to use:**
- initialized_cache (existing)
- temp_dir (existing)

**Estimated effort:** 30 minutes
**Risk level:** Low (few tests, simple mocking)
```

### Phase 4: Execute Migration (20-40 minutes)

**1. Remove setup_method**

```python
# BEFORE
class TestCache:
    def setup_method(self):
        self.cache = QueryCache(max_size=10, ttl_seconds=300)
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
```

```python
# AFTER
class TestCache:
    # Remove both methods
    pass
```

**2. Update test signatures**

```python
# BEFORE
def test_cache_hit(self):
    self.cache.set("key", "value")
    assert self.cache.get("key") == "value"

# AFTER
def test_cache_hit(self, initialized_cache):
    initialized_cache.set("key", "value")
    assert initialized_cache.get("key") == "value"
```

**3. Replace self references**

Use regex search and replace:

```bash
# Find: self\.cache
# Replace: initialized_cache

# Find: self\.temp_dir
# Replace: temp_dir
```

**4. Fix fixture access patterns**

```python
# BEFORE
self.test_file = os.path.join(self.temp_dir, "test.py")

# AFTER
test_file = os.path.join(temp_dir, "test.py")
# OR use existing fixture:
test_file = temp_project_with_files["sample_py"]
```

### Phase 5: Validation (10-15 minutes)

**1. Syntax check**
```bash
pytest tests/unit/test_cache.py --collect-only
```

**2. Run tests**
```bash
pytest tests/unit/test_cache.py -v
```

**3. Compare results**
```bash
# Should show same number of tests passing
diff baseline_results.txt <(pytest tests/unit/test_cache.py -v)
```

**4. Check coverage (optional)**
```bash
pytest tests/unit/test_cache.py --cov=src --cov-report=term
```

**5. Validate refactoring**
```bash
python tests/scripts/validate_refactoring.py tests/unit/test_cache.py
```

### Phase 6: Cleanup & Document (5 minutes)

**1. Remove empty test classes**

```python
# If class is now empty, remove it
class TestCache:
    pass  # ← Remove this
```

**2. Update docstrings**

```python
def test_cache_hit(self, initialized_cache):
    """Test cache hit using initialized_cache fixture."""
    # ...
```

**3. Commit changes**

```bash
git add tests/unit/test_cache.py
git commit -m "refactor(test): migrate test_cache to use fixtures

- Remove setup_method/teardown_method (8 lines)
- Use initialized_cache and temp_dir fixtures
- Update 12 test functions
- All tests passing, coverage maintained

Score: 38.9 → 15.2 (refactored)"
```

## Common Migration Patterns

### Pattern 1: Temporary Directory

**Before:**
```python
class TestExample:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_something(self):
        file_path = os.path.join(self.temp_dir, "test.txt")
```

**After:**
```python
def test_something(temp_dir):
    file_path = os.path.join(temp_dir, "test.txt")
```

### Pattern 2: Initialized Cache

**Before:**
```python
class TestCache:
    def setup_method(self):
        main._query_cache = QueryCache(max_size=10, ttl_seconds=300)
        main.CACHE_ENABLED = True
        main.register_mcp_tools()

    def teardown_method(self):
        main._query_cache = None
        main.CACHE_ENABLED = False

    def test_cache(self):
        result = main._query_cache.get("key")
```

**After:**
```python
def test_cache(initialized_cache):
    result = initialized_cache.get("key")
```

### Pattern 3: Multiple Test Files

**Before:**
```python
class TestRewrite:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_py = os.path.join(self.temp_dir, "sample.py")
        self.complex_py = os.path.join(self.temp_dir, "complex.py")
        # Create files...

    def test_rewrite(self):
        with open(self.sample_py) as f:
            content = f.read()
```

**After:**
```python
def test_rewrite(temp_project_with_files):
    sample_py = temp_project_with_files["sample_py"]
    with open(sample_py) as f:
        content = f.read()
```

### Pattern 4: Mock Subprocess

**Before:**
```python
class TestSearch:
    def setup_method(self):
        self.mock_popen = patch("subprocess.Popen")

    @patch("subprocess.Popen")
    def test_search(self, mock_popen):
        mock_popen.return_value.stdout = iter(["line1", "line2"])
```

**After:**
```python
def test_search(mock_popen):
    mock_popen.return_value.stdout = iter(["line1", "line2"])
```

### Pattern 5: MCP Tools

**Before:**
```python
class TestTools:
    def setup_method(self):
        main.register_mcp_tools()
        self.find_code = main.mcp.tools.get("find_code")

    def test_find_code(self):
        result = self.find_code(...)
```

**After:**
```python
def test_find_code(mcp_tools):
    find_code = mcp_tools("find_code")
    result = find_code(...)
```

## Before & After Examples

### Example 1: test_rewrite.py (Score: 92.2)

**Before (with setup_method):**
```python
class TestRewrite:
    def setup_method(self):
        """Setup for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "sample.py")
        self.rewrite_code = main.mcp.tools.get("rewrite_code")

        # Create sample file
        with open(self.test_file, "w") as f:
            f.write("def hello():\n    print('hello')\n")

    def teardown_method(self):
        """Cleanup after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rewrite_function(self):
        """Test rewriting a function."""
        result = self.rewrite_code(
            project_folder=self.temp_dir,
            pattern="def hello():",
            replacement="def hello(name):",
            language="python"
        )

        with open(self.test_file, "r") as f:
            content = f.read()

        assert "def hello(name):" in content

    def test_rewrite_with_backup(self):
        """Test rewrite creates backup."""
        result = self.rewrite_code(
            project_folder=self.temp_dir,
            pattern="print('hello')",
            replacement="print('world')",
            language="python"
        )

        # Check backup exists
        backup_dir = Path(self.temp_dir) / ".ast-grep-backups"
        assert backup_dir.exists()
```

**After (with fixtures):**
```python
def test_rewrite_function(temp_project_with_files, mcp_tools):
    """Test rewriting a function using fixtures."""
    rewrite_code = mcp_tools("rewrite_code")
    project = temp_project_with_files["project"]
    sample_py = temp_project_with_files["sample_py"]

    result = rewrite_code(
        project_folder=project,
        pattern="def hello():",
        replacement="def hello(name):",
        language="python"
    )

    with open(sample_py, "r") as f:
        content = f.read()

    assert "def hello(name):" in content

def test_rewrite_with_backup(temp_project_with_files, mcp_tools):
    """Test rewrite creates backup using fixtures."""
    rewrite_code = mcp_tools("rewrite_code")
    project = temp_project_with_files["project"]

    result = rewrite_code(
        project_folder=project,
        pattern="print('hello')",
        replacement="print('world')",
        language="python"
    )

    # Check backup exists
    backup_dir = Path(project) / ".ast-grep-backups"
    assert backup_dir.exists()
```

**Changes:**
- Removed 15 lines of setup/teardown code
- Tests now explicit about dependencies (temp_project_with_files, mcp_tools)
- Automatic cleanup handled by fixtures
- More readable and maintainable

### Example 2: test_cache.py (Score: 38.9)

**Before (defer - keep as is):**
```python
class TestCache:
    def setup_method(self):
        """Setup for each test."""
        main._query_cache = QueryCache(max_size=10, ttl_seconds=300)
        main.CACHE_ENABLED = True

    def teardown_method(self):
        """Cleanup after each test."""
        main._query_cache = None
        main.CACHE_ENABLED = False

    def test_cache_basic(self):
        """Test basic cache operations."""
        main._query_cache.set("key", "value")
        assert main._query_cache.get("key") == "value"
```

**Decision:** Keep as-is (score <40, simple setup, low maintenance burden)

## Troubleshooting

### Issue 1: Tests failing after migration

**Symptom:** Tests pass before migration, fail after

**Common causes:**
1. **Forgot to pass fixture** - Add fixture parameter to test function
2. **Wrong fixture name** - Check spelling/case
3. **Fixture scope mismatch** - Need session/module fixture instead of function
4. **Missing cleanup** - Fixture doesn't reset state properly

**Solution:**
```bash
# Compare test outputs
pytest tests/unit/test_cache.py -v --tb=short

# Check fixture is being used
pytest tests/unit/test_cache.py -v --setup-show
```

### Issue 2: Self references remain

**Symptom:** `AttributeError: 'TestClass' object has no attribute 'temp_dir'`

**Solution:**
```bash
# Find remaining self references
grep -n "self\." tests/unit/test_cache.py

# Replace with fixture parameter name
# self.temp_dir → temp_dir
```

### Issue 3: Fixture not found

**Symptom:** `fixture 'initialized_cache' not found`

**Solution:**
```bash
# Check fixture exists
grep -n "def initialized_cache" tests/conftest.py

# Check fixture is in scope (should be in tests/conftest.py)
# If not, move it there or import properly
```

### Issue 4: Tests slower after migration

**Symptom:** Test execution time increased

**Solution:**
```bash
# Benchmark before/after
pytest tests/unit/test_cache.py --durations=10

# Check fixture scope
# Change from 'function' to 'class' or 'module' if safe:
@pytest.fixture(scope="class")
def expensive_fixture():
    # ...
```

### Issue 5: Circular fixture dependencies

**Symptom:** `Fixture 'a' depends on 'b' which depends on 'a'`

**Solution:**
- Redesign fixtures to remove circular dependency
- Extract common logic to separate fixture
- Use fixture parameters instead of fixture composition

## Validation Checklist

Use this checklist after migration:

### Functional Validation

- [ ] All tests collect successfully (`pytest --collect-only`)
- [ ] All tests pass (`pytest -v`)
- [ ] Same number of tests as before migration
- [ ] No skipped tests that weren't skipped before
- [ ] No new test warnings

### Code Quality

- [ ] No `self.` references remain (except in test classes that still need them)
- [ ] All fixture parameters are used
- [ ] No unused imports
- [ ] Docstrings updated to reflect fixture usage
- [ ] Test names still descriptive

### Performance

- [ ] Test execution time within 5% of baseline
- [ ] No fixture overhead >100ms per test
- [ ] Appropriate fixture scope (function/class/module/session)

### Documentation

- [ ] Commit message explains changes
- [ ] Complex fixture usage has comments
- [ ] Updated test file header if present

### Coverage

- [ ] Code coverage maintained or improved
- [ ] No new untested code paths

### Run Validation Script

```bash
# Automated validation
python tests/scripts/validate_refactoring.py tests/unit/test_cache.py

# Manual checks
pytest tests/unit/test_cache.py -v --tb=short
pytest tests/unit/test_cache.py --durations=5
```

## Next Steps

After successful migration:

1. **Update tracking**
   ```bash
   python tests/scripts/track_fixture_metrics.py
   ```

2. **Share knowledge**
   - Add example to FIXTURE_COOKBOOK.md
   - Mention in team standup
   - Update REFACTORING_ANALYSIS.md

3. **Identify patterns**
   - If you created helper functions, consider converting to fixtures
   - If pattern appears in 3+ files, propose new shared fixture

4. **Document lessons learned**
   - What went well?
   - What was difficult?
   - How could process be improved?

## Resources

- **Quick reference**: [FIXTURE_QUICK_REFERENCE.md](FIXTURE_QUICK_REFERENCE.md)
- **Governance**: [FIXTURE_GOVERNANCE.md](FIXTURE_GOVERNANCE.md)
- **Cookbook**: [FIXTURE_COOKBOOK.md](FIXTURE_COOKBOOK.md)
- **Onboarding**: [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)
- **Pytest docs**: https://docs.pytest.org/en/stable/fixture.html

## Feedback

Have suggestions for improving this guide? Please:
- Open an issue with tag `fixture-migration`
- Propose changes via PR
- Discuss in team meetings
