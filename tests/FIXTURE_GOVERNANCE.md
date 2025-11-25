# Fixture Governance

**Version:** 1.0
**Date:** 2025-11-25
**Status:** Active

## Overview

This document defines the governance process for proposing, reviewing, approving, and maintaining pytest fixtures in the ast-grep-mcp test suite.

## Principles

### Design Principles

1. **Clarity over cleverness** - Fixtures should be obvious and easy to understand
2. **Composability** - Fixtures should work well together
3. **Isolation** - Each fixture should handle its own cleanup
4. **Documentation** - All fixtures must be documented with docstrings and examples
5. **Performance** - Minimize fixture overhead (<100ms per test)

### Quality Standards

- **Type hints** - All fixtures must have proper type annotations
- **Docstrings** - Explain what the fixture provides and when to use it
- **Scope** - Use appropriate scope (function/class/module/session)
- **Dependencies** - Clearly document fixture dependencies
- **Examples** - Provide usage examples in docstring

## Fixture Lifecycle

```
Proposal → Review → Approval → Implementation → Documentation → Maintenance
```

### 1. Proposal

**When to propose a new fixture:**
- Pattern appears in 3+ test files
- Setup code is >10 lines
- Complex cleanup required
- Common testing scenario

**How to propose:**

Create a proposal issue with:

````markdown
## Fixture Proposal: [fixture_name]

**Problem:**
Describe the repetitive pattern or pain point.

**Proposed Solution:**
```python
@pytest.fixture
def fixture_name(dependencies):
    """
    Brief description of what this fixture provides.

    When to use:
    - Scenario 1
    - Scenario 2

    Example:
        def test_example(fixture_name):
            # Usage example
            assert fixture_name.something == expected
    """
    # Setup code
    yield value
    # Cleanup code
```

**Usage Frequency:**
Used in [N] test files, [M] times total.

**Files:**
- tests/unit/test_file1.py (5 uses)
- tests/unit/test_file2.py (3 uses)

**Alternatives Considered:**
1. Alternative 1 - Why not suitable
2. Alternative 2 - Why not suitable

**Impact:**
- Lines saved: ~50 lines
- Tests affected: 8 tests across 3 files
- Breaking changes: None
````

### 2. Review

**Review Criteria:**

1. **Necessity**
   - Is this truly reusable? (3+ files)
   - Could this be a helper function instead?
   - Is the abstraction justified?

2. **Design**
   - Clear, descriptive name?
   - Appropriate scope?
   - Proper cleanup?
   - Type-safe?

3. **Documentation**
   - Comprehensive docstring?
   - Usage examples?
   - When to use / when not to use?

4. **Performance**
   - Acceptable overhead?
   - Efficient implementation?
   - Minimal side effects?

5. **Maintainability**
   - Simple implementation?
   - Easy to debug?
   - Well-tested?

**Review Process:**

1. **Self-review** - Proposer reviews against criteria
2. **Peer review** - 1-2 team members review
3. **Discussion** - Address feedback, iterate design
4. **Decision** - Approve, request changes, or reject

**Timeframe:** 2-5 business days

### 3. Approval

**Approval Authority:**

- **Tier 1 (Auto-approve)**: Simple, obvious fixtures
  - Example: Temporary directory with specific files
  - Requirements: Used 3+ times, <20 lines, no global state

- **Tier 2 (Peer approval)**: Standard fixtures
  - Example: Mock subprocess with common configuration
  - Requirements: 1 peer review, pattern validation

- **Tier 3 (Team approval)**: Complex fixtures
  - Example: Session-scoped database fixture
  - Requirements: 2+ peer reviews, architecture discussion

**Approval Checklist:**

- [ ] Meets necessity criteria (3+ uses OR >10 lines saved)
- [ ] Follows naming conventions
- [ ] Has comprehensive docstring with examples
- [ ] Proper type hints
- [ ] Appropriate scope
- [ ] Handles cleanup properly
- [ ] No performance concerns
- [ ] Tests for the fixture itself

### 4. Implementation

**Implementation Requirements:**

1. **Location**
   - Simple fixtures: `tests/conftest.py`
   - Complex fixtures: `tests/fixtures/*.py` (imported in conftest.py)

2. **Naming Conventions**
   - Use descriptive, noun-based names
   - Prefix with domain if ambiguous
   - Examples: `temp_dir`, `initialized_cache`, `mock_popen`

3. **Type Hints**
   ```python
   from typing import Generator, Dict
   from pathlib import Path

   @pytest.fixture
   def temp_dir() -> Generator[str, None, None]:
       """Type hint the yield value."""
       pass
   ```

4. **Docstring Format**
   ```python
   @pytest.fixture
   def fixture_name(dependencies) -> ReturnType:
       """
       One-line summary.

       Longer description explaining what this fixture provides,
       when to use it, and any important caveats.

       Args:
           dependency: Description if using other fixtures

       Yields:
           Type: Description of what's yielded

       Example:
           def test_example(fixture_name):
               result = fixture_name.do_something()
               assert result == expected

       Notes:
           - Important note 1
           - Important note 2
       """
       pass
   ```

5. **Cleanup**
   ```python
   @pytest.fixture
   def resource():
       """Always use yield + cleanup pattern."""
       # Setup
       resource = create_resource()

       yield resource

       # Cleanup (always runs, even if test fails)
       resource.cleanup()
   ```

### 5. Documentation

**Documentation Requirements:**

1. **FIXTURE_QUICK_REFERENCE.md**
   - Add fixture to appropriate category
   - Include brief description
   - Add usage example

2. **FIXTURE_COOKBOOK.md**
   - If fixture solves common problem, add recipe
   - Include before/after example
   - Explain when to use

3. **DEVELOPER_ONBOARDING.md**
   - Update list of available fixtures
   - Add to "Fixtures You Should Know" if commonly used

4. **tests/test_conftest_fixtures.py**
   - Add test(s) demonstrating fixture usage
   - Verify cleanup works properly
   - Test edge cases

**Example Documentation:**

```markdown
### temp_dir

Provides a temporary directory that is automatically cleaned up after test execution.

**When to use:**
- Tests that need to write files
- Tests that need isolated file system space

**Example:**
```python
def test_file_operations(temp_dir):
    file_path = os.path.join(temp_dir, "test.txt")
    with open(file_path, "w") as f:
        f.write("test content")
    assert os.path.exists(file_path)
    # temp_dir automatically deleted after test
```
```

### 6. Maintenance

**Ongoing Responsibilities:**

1. **Monitor Usage**
   ```bash
   # Track fixture adoption
   python tests/scripts/track_fixture_metrics.py
   ```

2. **Performance Monitoring**
   ```bash
   # Check fixture overhead
   python tests/scripts/benchmark_fixtures.py
   ```

3. **Quarterly Reviews**
   - Review all fixtures
   - Identify unused fixtures (candidates for deprecation)
   - Identify frequently-used patterns (candidates for new fixtures)
   - Check for fixture bloat

4. **Deprecation Process**
   - Mark fixture as deprecated with warning
   - Provide migration path
   - Give 2 release cycles before removal
   - Update all documentation

**Deprecation Example:**

```python
@pytest.fixture
def old_fixture():
    """
    .. deprecated:: 2.5.0
       Use :func:`new_fixture` instead. This will be removed in 3.0.0.
    """
    warnings.warn(
        "old_fixture is deprecated, use new_fixture instead",
        DeprecationWarning,
        stacklevel=2
    )
    # ...
```

## Decision Matrix

Use this matrix to decide: fixture, helper function, or leave as-is?

| Criteria | Fixture | Helper Function | Leave As-Is |
|----------|---------|-----------------|-------------|
| **Usage frequency** | 3+ files | 1-2 files | Single file |
| **Setup complexity** | >10 lines | Any | <5 lines |
| **Cleanup needed** | Yes | Maybe | No |
| **Automatic cleanup** | Required | Optional | Not needed |
| **Composability** | High | Medium | Low |
| **Shared state** | Needs isolation | Can share | File-local OK |

**Examples:**

- **Fixture**: Temporary directory (used everywhere, needs cleanup, isolation)
- **Helper**: Create sample JSON (used 2 times, simple, no cleanup)
- **Leave as-is**: Test-specific mock config (unique to one test, 3 lines)

## Anti-Patterns to Avoid

### 1. Fixture Bloat

**Problem:** Too many fixtures, hard to find the right one

**Solution:**
- Only create fixtures for patterns appearing 3+ times
- Prefer helper functions for one-off needs
- Regular fixture audits

### 2. Overly Complex Fixtures

**Problem:** Fixture does too much, hard to understand

**Solution:**
- Keep fixtures focused on single responsibility
- Break complex fixtures into smaller composable ones
- Document complexity in docstring

### 3. Hidden Dependencies

**Problem:** Fixture modifies global state without cleanup

**Solution:**
- Always use yield + cleanup pattern
- Document side effects in docstring
- Use autouse sparingly

### 4. Performance Penalties

**Problem:** Fixture adds significant overhead to tests

**Solution:**
- Use appropriate scope (function/class/module/session)
- Lazy initialization when possible
- Benchmark and optimize

### 5. Unclear Naming

**Problem:** Fixture name doesn't describe what it provides

**Solution:**
- Use descriptive, noun-based names
- Avoid abbreviations
- Examples: `temp_dir` (good), `td` (bad)

## Fixture Naming Conventions

### General Rules

1. **Descriptive nouns** - What does it provide?
2. **Lowercase with underscores** - `snake_case`
3. **No abbreviations** - Spell out words
4. **Avoid test prefix** - Don't start with `test_`

### Patterns

| Pattern | Example | When to Use |
|---------|---------|-------------|
| `<resource>` | `temp_dir`, `cache` | Provides a resource |
| `mock_<thing>` | `mock_popen`, `mock_subprocess_run` | Mocks something |
| `initialized_<thing>` | `initialized_cache` | Pre-configured instance |
| `sample_<data>` | `sample_search_result` | Test data |
| `<action>_<resource>` | `create_temp_file` | Factory function |

### Examples

**Good:**
- `temp_dir` - Clear, describes what it provides
- `initialized_cache` - Clear state (initialized)
- `mock_subprocess_run` - Clear it's a mock
- `sample_search_result` - Clear it's test data

**Bad:**
- `td` - Unclear abbreviation
- `tmp` - Too abbreviated
- `test_cache` - Confusing (sounds like a test)
- `fixture1` - Meaningless name

## Scope Guidelines

Choose the appropriate fixture scope based on usage:

### Function Scope (Default)

**Use when:**
- State must be isolated per test
- Cleanup required after each test
- Resource is cheap to create (<10ms)

**Example:**
```python
@pytest.fixture  # scope="function" is default
def temp_dir():
    """Fresh temp directory for each test."""
    pass
```

### Class Scope

**Use when:**
- Multiple tests in class share setup
- Resource expensive to create (10-100ms)
- Safe to share within class

**Example:**
```python
@pytest.fixture(scope="class")
def database_connection():
    """One DB connection per test class."""
    pass
```

### Module Scope

**Use when:**
- All tests in module share setup
- Very expensive to create (>100ms)
- Read-only resource

**Example:**
```python
@pytest.fixture(scope="module")
def loaded_schema():
    """Load schema once per module."""
    pass
```

### Session Scope

**Use when:**
- Shared across entire test suite
- Extremely expensive (>1s)
- Truly immutable

**Example:**
```python
@pytest.fixture(scope="session")
def docker_container():
    """One container for entire test run."""
    pass
```

## Testing Fixtures

All fixtures should be tested in `tests/test_conftest_fixtures.py`:

```python
def test_temp_dir_fixture(temp_dir):
    """Test that temp_dir fixture provides working directory."""
    # Verify it's a valid directory
    assert os.path.isdir(temp_dir)

    # Verify we can write to it
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")

    assert os.path.exists(test_file)

def test_temp_dir_cleanup(temp_dir):
    """Test that temp_dir is cleaned up after test."""
    saved_path = temp_dir
    # After this test, pytest should clean up temp_dir
    # We can't directly test cleanup, but we document it

def test_temp_dir_isolation(temp_dir):
    """Test that temp_dir is isolated per test."""
    # Each test gets its own temp_dir
    # Write a file
    test_file = os.path.join(temp_dir, "isolation_test.txt")
    with open(test_file, "w") as f:
        f.write("isolated")
    # This file won't exist in other tests
```

## Metrics & Tracking

### Fixture Adoption Rate

Track what percentage of tests use fixtures:

```bash
python tests/scripts/track_fixture_metrics.py
```

**Target metrics:**
- Phase 1: 15% baseline
- Phase 2: 40% adoption
- Phase 3: 60% adoption
- Phase 4: 80% adoption

### Fixture Usage

Track which fixtures are most/least used:

```bash
python tests/scripts/track_fixture_metrics.py --detailed
```

**Actions:**
- **Highly used (>50 uses)**: Ensure well-documented, well-tested
- **Moderately used (10-50 uses)**: Monitor, consider optimization
- **Rarely used (<10 uses)**: Consider deprecation if <3 files use it

### Performance

Track fixture overhead:

```bash
python tests/scripts/benchmark_fixtures.py
```

**Thresholds:**
- **Good**: <10ms overhead
- **Acceptable**: 10-50ms
- **Needs optimization**: 50-100ms
- **Must fix**: >100ms

## FAQs

### When should I create a fixture vs. a helper function?

**Create a fixture when:**
- Used in 3+ test files
- Requires automatic cleanup
- Provides a resource that needs setup/teardown
- Benefits from pytest's dependency injection

**Create a helper function when:**
- Used in 1-2 test files
- Doesn't require cleanup
- Simple data generation
- Better as an explicit function call

### Can I modify existing fixtures?

**Minor changes (non-breaking):**
- Yes, just update the fixture
- Update documentation
- Add tests for new behavior

**Breaking changes:**
- Deprecate old fixture
- Create new fixture with new name
- Provide migration guide
- Give 2 release cycles notice

### What if my fixture needs another fixture?

**Use fixture composition:**

```python
@pytest.fixture
def base_fixture():
    return "base"

@pytest.fixture
def composed_fixture(base_fixture):
    return f"{base_fixture}_composed"
```

**Keep dependency chain shallow** (max 2-3 levels)

### How do I handle fixture cleanup failures?

**Use finalizers:**

```python
@pytest.fixture
def resource(request):
    r = create_resource()

    def cleanup():
        try:
            r.cleanup()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    request.addfinalizer(cleanup)
    return r
```

### Can I have optional fixture parameters?

**Use indirect parametrization:**

```python
@pytest.fixture
def configurable_cache(request):
    size = getattr(request, 'param', 10)  # Default 10
    return QueryCache(max_size=size)

@pytest.mark.parametrize('configurable_cache', [5, 10, 20], indirect=True)
def test_cache_sizes(configurable_cache):
    # Test runs 3 times with different cache sizes
    pass
```

## Resources

- [FIXTURE_QUICK_REFERENCE.md](FIXTURE_QUICK_REFERENCE.md) - All available fixtures
- [FIXTURE_MIGRATION_GUIDE.md](FIXTURE_MIGRATION_GUIDE.md) - How to migrate tests
- [FIXTURE_COOKBOOK.md](FIXTURE_COOKBOOK.md) - Common patterns and recipes
- [Pytest fixture docs](https://docs.pytest.org/en/stable/fixture.html)

## Changelog

### Version 1.0 (2025-11-25)
- Initial governance document
- Defined proposal/review/approval process
- Established naming conventions and scope guidelines
- Created decision matrix for fixture vs. helper function
