# Test Pattern Analysis: test_apply_deduplication.py

**File:** tests/unit/test_apply_deduplication.py
**Total Lines:** 708
**Test Classes:** 4
**Test Methods:** 24
**Current Pattern:** setup_method/teardown_method (legacy)

## Test Class Structure

### 1. TestApplyDeduplication (Lines 54-174)
**Tests:** 6
**Purpose:** Core tool functionality, input validation, response structures

**Current Setup:**
```python
def setup_method(self) -> None:
    self.temp_dir = tempfile.mkdtemp()
    self.project_folder = self.temp_dir
    self.test_file = os.path.join(self.temp_dir, "sample.py")
    self.test_file2 = os.path.join(self.temp_dir, "sample2.py")
    # Write sample files
    self.apply_deduplication = main.mcp.tools.get("apply_deduplication")
```

**Current Teardown:**
```python
def teardown_method(self) -> None:
    shutil.rmtree(self.temp_dir, ignore_errors=True)
```

**Helper Methods:**
- `_create_refactoring_plan()` - Creates basic refactoring plan

**Test Methods:**
1. `test_tool_registered` - Tool registration check
2. `test_dry_run_returns_correct_structure` - Dry-run mode validation
3. `test_apply_mode_returns_correct_structure` - Apply mode validation
4. `test_validates_project_folder_exists` - Error handling
5. `test_validates_refactoring_plan_required` - Error handling
6. `test_no_files_affected_returns_no_changes` - Empty result handling

### 2. TestBackupIntegration (Lines 176-398)
**Tests:** 7
**Purpose:** Backup creation, metadata, rollback functionality

**Current Setup:**
```python
def setup_method(self) -> None:
    self.temp_dir = tempfile.mkdtemp()
    self.project_folder = self.temp_dir
    self.test_file1 = os.path.join(self.temp_dir, "file1.py")
    self.test_file2 = os.path.join(self.temp_dir, "file2.py")
    self.original_content1 = "def func1():\n    pass\n"
    self.original_content2 = "def func2():\n    pass\n"
    # Write files with original content
    self.apply_deduplication = main.mcp.tools.get("apply_deduplication")
```

**Helper Methods:**
- `_create_plan_with_content()` - Creates plan with specific content

**Test Methods:**
1. `test_backup_created_on_apply` - Backup directory creation
2. `test_backup_metadata_contains_deduplication_info` - Metadata validation
3. `test_backup_preserves_original_files` - Backup content verification
4. `test_rollback_restores_original_content` - Single file rollback
5. `test_multi_file_backup_and_rollback` - Multi-file rollback
6. `test_no_backup_when_backup_false` - No backup when disabled
7. `test_backup_id_in_rollback_command` - Rollback command format

### 3. TestPhase33MultiFileOrchestration (Lines 400-618)
**Tests:** 5
**Purpose:** Multi-file orchestration, file creation, atomic operations

**Current Setup:**
```python
def setup_method(self) -> None:
    self.temp_dir = tempfile.mkdtemp()
    self.project_folder = self.temp_dir
    self.src_dir = os.path.join(self.temp_dir, "src")
    os.makedirs(self.src_dir)
    self.test_file1 = os.path.join(self.src_dir, "file1.py")
    self.test_file2 = os.path.join(self.src_dir, "file2.py")
    self.original_content1 = "import os\n\ndef func1():\n    return os.getcwd()\n"
    self.original_content2 = "import os\n\ndef func2():\n    return os.getcwd()\n"
    # Write files
    self.apply_deduplication = main.mcp.tools.get("apply_deduplication")
```

**Helper Methods:**
- `_create_plan_with_extraction()` - Creates plan with extracted function

**Test Methods:**
1. `test_orchestration_creates_extracted_function_file` - New file creation
2. `test_orchestration_creates_file_before_updates` - File order
3. `test_orchestration_atomic_rollback_on_failure` - Atomic operations
4. `test_orchestration_appends_to_existing_file` - Append operations
5. `test_orchestration_handles_multiple_files_atomically` - Multi-file atomicity

### 4. TestOrchestrationHelperFunctions (Lines 620-708)
**Tests:** 6
**Purpose:** Helper function unit tests (no file I/O)

**Current Setup:**
```python
def setup_method(self) -> None:
    # No setup needed for pure functions
    pass
```

**Test Methods:**
1. `test_plan_file_modification_order_basic` - File ordering logic
2. `test_add_import_to_content_python` - Python import addition
3. `test_add_import_to_content_python_no_existing_imports` - No imports case
4. `test_add_import_to_content_typescript` - TypeScript import addition
5. `test_add_import_to_content_skips_duplicate` - Duplicate detection
6. `test_generate_import_for_extracted_function` - Import generation

## Common Patterns Identified

### 1. Temporary Directory Pattern (Classes 1-3)
**Repeated in 3 classes:**
```python
self.temp_dir = tempfile.mkdtemp()
self.project_folder = self.temp_dir
# teardown: shutil.rmtree(self.temp_dir, ignore_errors=True)
```

### 2. Test Files Pattern (Classes 1-3)
**Variations:**
- Class 1: `sample.py`, `sample2.py` (simple content)
- Class 2: `file1.py`, `file2.py` (with original_content attributes)
- Class 3: `src/file1.py`, `src/file2.py` (with subdirectory, complex content)

### 3. Tool Access Pattern (Classes 1-3)
**Repeated in 3 classes:**
```python
self.apply_deduplication = main.mcp.tools.get("apply_deduplication")
assert self.apply_deduplication is not None
```

### 4. Helper Method Pattern (Classes 1-3)
**Each class has custom helper(s):**
- Class 1: `_create_refactoring_plan()` - Basic plan
- Class 2: `_create_plan_with_content()` - Plan with specific content
- Class 3: `_create_plan_with_extraction()` - Plan with extraction

## Recommended Fixtures

### High Priority (Used by 3 classes)

1. **`project_folder`** - Temporary directory with automatic cleanup
   ```python
   @pytest.fixture
   def project_folder(tmp_path):
       """Temporary project folder for testing."""
       return tmp_path
   ```

2. **`apply_deduplication_tool`** - Tool access
   ```python
   @pytest.fixture(scope="module")
   def apply_deduplication_tool():
       """Get apply_deduplication tool function."""
       tool = main.mcp.tools.get("apply_deduplication")
       assert tool is not None, "apply_deduplication tool not registered"
       return tool
   ```

3. **`simple_test_files`** - Simple Python files (Class 1)
   ```python
   @pytest.fixture
   def simple_test_files(project_folder):
       """Create simple test files."""
       file1 = project_folder / "sample.py"
       file2 = project_folder / "sample2.py"
       file1.write_text("def hello():\n    print('hello')\n")
       file2.write_text("def world():\n    print('world')\n")
       return {"file1": str(file1), "file2": str(file2)}
   ```

4. **`backup_test_files`** - Files with tracked original content (Class 2)
   ```python
   @pytest.fixture
   def backup_test_files(project_folder):
       """Create test files with original content tracking."""
       original_content1 = "def func1():\n    pass\n"
       original_content2 = "def func2():\n    pass\n"

       file1 = project_folder / "file1.py"
       file2 = project_folder / "file2.py"
       file1.write_text(original_content1)
       file2.write_text(original_content2)

       return {
           "file1": str(file1),
           "file2": str(file2),
           "original_content1": original_content1,
           "original_content2": original_content2,
       }
   ```

5. **`orchestration_test_files`** - Complex files with subdirectory (Class 3)
   ```python
   @pytest.fixture
   def orchestration_test_files(project_folder):
       """Create test files in subdirectory with complex content."""
       src_dir = project_folder / "src"
       src_dir.mkdir()

       original_content1 = "import os\n\ndef func1():\n    return os.getcwd()\n"
       original_content2 = "import os\n\ndef func2():\n    return os.getcwd()\n"

       file1 = src_dir / "file1.py"
       file2 = src_dir / "file2.py"
       file1.write_text(original_content1)
       file2.write_text(original_content2)

       return {
           "src_dir": str(src_dir),
           "file1": str(file1),
           "file2": str(file2),
           "original_content1": original_content1,
           "original_content2": original_content2,
       }
   ```

### Medium Priority (Helper methods)

6. **`refactoring_plan_factory`** - Factory fixture for creating plans
   ```python
   @pytest.fixture
   def refactoring_plan_factory():
       """Factory for creating refactoring plans."""
       def _create_plan(
           files: list[str],
           new_contents: list[str] = None,
           strategy: str = "extract_function",
           extracted_function: str = "",
           extract_to_file: str = "",
           function_name: str = "extracted_func",
           language: str = "python"
       ) -> Dict[str, Any]:
           if new_contents is None:
               new_contents = [f"# Modified: {f}\n" for f in files]

           replacements = {}
           for f, content in zip(files, new_contents):
               replacements[f] = {
                   "new_content": content,
                   "changes": [{"line": 1, "old": "original", "new": "modified"}]
               }

           plan = {
               "strategy": strategy,
               "files_affected": files,
               "generated_code": {
                   "extracted_function": extracted_function,
                   "replacements": replacements
               },
               "language": language
           }

           if extract_to_file:
               plan["generated_code"]["extract_to_file"] = extract_to_file
               plan["generated_code"]["function_name"] = function_name

           return plan

       return _create_plan
   ```

## Migration Strategy

### Phase 1: Add fixtures to conftest.py
- Create all 6 fixtures in `tests/unit/conftest.py`
- Verify fixtures work with existing tests

### Phase 2: Migrate TestOrchestrationHelperFunctions (Easiest)
- Already has minimal setup
- No file I/O dependencies
- Quick win for validation

### Phase 3: Migrate TestApplyDeduplication
- Replace setup_method with `project_folder`, `simple_test_files`, `apply_deduplication_tool`
- Replace `_create_refactoring_plan()` with `refactoring_plan_factory`
- Remove teardown_method (automatic with tmp_path)

### Phase 4: Migrate TestBackupIntegration
- Replace setup_method with `project_folder`, `backup_test_files`, `apply_deduplication_tool`
- Replace `_create_plan_with_content()` with `refactoring_plan_factory`
- Remove teardown_method

### Phase 5: Migrate TestPhase33MultiFileOrchestration
- Replace setup_method with `project_folder`, `orchestration_test_files`, `apply_deduplication_tool`
- Replace `_create_plan_with_extraction()` with `refactoring_plan_factory`
- Remove teardown_method

## Expected Benefits

### Code Reduction
- **Current:** 708 lines with duplicate setup code
- **After:** ~600 lines (15% reduction)
- Eliminate ~100 lines of duplicate setup/teardown code

### Performance
- **Current:** Each test creates temp dirs independently
- **After:** pytest's tmp_path fixture manages cleanup efficiently
- **Expected improvement:** 5-10% faster test execution

### Maintainability
- Centralized fixture definitions in conftest.py
- Easy to add new test classes using existing fixtures
- Clear separation between setup (fixtures) and test logic

## Risk Assessment

### Low Risk
- TestOrchestrationHelperFunctions (no file I/O)
- Tool access pattern (simple fixture)

### Medium Risk
- TestApplyDeduplication (simple file setup)
- File fixture patterns (well-tested by pytest)

### Higher Risk (require careful validation)
- TestBackupIntegration (complex backup operations)
- TestPhase33MultiFileOrchestration (atomic operations, subdirectories)

## Success Criteria

1. All 24 tests pass after migration
2. No performance regression (within 5%)
3. Code reduction of at least 10%
4. No warnings in pytest output
5. Baseline validation passes
