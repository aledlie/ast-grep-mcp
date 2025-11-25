"""Unit tests for apply_deduplication tool (Phase 3.1 & 3.2).

Tests cover:
- Tool registration
- Input validation
- Dry-run mode response structure
- Apply mode response structure
- Backup integration (Phase 3.2)
- Rollback functionality
- Error handling
"""

import json
import os
import shutil
import sys
import tempfile
from typing import Any, Dict
from unittest.mock import patch

import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Mock FastMCP before importing main
class MockFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: Dict[str, Any] = {}

    def tool(self, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs: Any) -> None:
        pass


def mock_field(**kwargs: Any) -> Any:
    return kwargs.get("default")


# Import with mocked decorators
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main
        main.register_mcp_tools()


class TestApplyDeduplication:
    """Tests for apply_deduplication MCP tool."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir

        # Create sample Python file
        self.test_file = os.path.join(self.temp_dir, "sample.py")
        with open(self.test_file, "w") as f:
            f.write("def hello():\n    print('hello')\n")

        # Create another sample file
        self.test_file2 = os.path.join(self.temp_dir, "sample2.py")
        with open(self.test_file2, "w") as f:
            f.write("def world():\n    print('world')\n")

        # Get tool function
        self.apply_deduplication = main.mcp.tools.get("apply_deduplication")  # type: ignore
        assert self.apply_deduplication is not None, "apply_deduplication tool not registered"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_refactoring_plan(self, files: list[str], new_content: str = "") -> Dict[str, Any]:
        """Helper to create a valid refactoring plan."""
        replacements = {}
        for f in files:
            replacements[f] = {
                "new_content": new_content or f"# Modified: {f}\n",
                "changes": [{"line": 1, "old": "original", "new": "modified"}]
            }
        return {
            "strategy": "extract_function",
            "files_affected": files,
            "generated_code": {
                "extracted_function": "def common_func():\n    pass\n",
                "replacements": replacements
            },
            "language": "python"
        }

    def test_tool_registered(self) -> None:
        """Test that apply_deduplication tool is registered."""
        assert "apply_deduplication" in main.mcp.tools  # type: ignore
        assert callable(main.mcp.tools["apply_deduplication"])  # type: ignore

    def test_dry_run_returns_correct_structure(self) -> None:
        """Test that dry_run mode returns expected response structure."""
        plan = self._create_refactoring_plan([self.test_file])
        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=True
        )

        assert result["status"] == "preview"
        assert result["dry_run"] is True
        assert "message" in result
        assert result["strategy"] == "extract_function"
        assert "changes_preview" in result
        assert result["group_id"] == 1

    def test_apply_mode_returns_correct_structure(self) -> None:
        """Test that apply mode returns expected response structure."""
        plan = self._create_refactoring_plan([self.test_file])
        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        assert result["status"] == "success"
        assert result["dry_run"] is False
        assert "message" in result
        assert "backup_id" in result
        assert result["backup_id"] is not None
        assert "files_modified" in result
        assert "validation" in result

    def test_validates_project_folder_exists(self) -> None:
        """Test that non-existent project folders are rejected."""
        plan = self._create_refactoring_plan(["/some/file.py"])
        with pytest.raises(ValueError, match="does not exist"):
            self.apply_deduplication(
                project_folder="/non/existent/path",
                group_id=1,
                refactoring_plan=plan,
                dry_run=True
            )

    def test_validates_refactoring_plan_required(self) -> None:
        """Test that empty refactoring plan is rejected."""
        with pytest.raises(ValueError, match="refactoring_plan is required"):
            self.apply_deduplication(
                project_folder=self.project_folder,
                group_id=1,
                refactoring_plan={},
                dry_run=True
            )

    def test_no_files_affected_returns_no_changes(self) -> None:
        """Test handling when no files are affected."""
        plan = {
            "strategy": "extract_function",
            "files_affected": [],
            "generated_code": {}
        }
        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=True
        )
        assert result["status"] == "no_changes"


class TestBackupIntegration:
    """Tests for Phase 3.2 backup integration in apply_deduplication."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir

        # Create sample Python files
        self.test_file1 = os.path.join(self.temp_dir, "file1.py")
        self.original_content1 = "def func1():\n    print('original1')\n"
        with open(self.test_file1, "w") as f:
            f.write(self.original_content1)

        self.test_file2 = os.path.join(self.temp_dir, "file2.py")
        self.original_content2 = "def func2():\n    print('original2')\n"
        with open(self.test_file2, "w") as f:
            f.write(self.original_content2)

        # Get tool functions
        self.apply_deduplication = main.mcp.tools.get("apply_deduplication")  # type: ignore
        assert self.apply_deduplication is not None

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_plan_with_content(self, files: list[str], new_contents: list[str]) -> Dict[str, Any]:
        """Create a refactoring plan with specific new content."""
        replacements = {}
        for f, content in zip(files, new_contents):
            replacements[f] = {
                "new_content": content,
                "changes": [{"line": 1, "old": "original", "new": "modified"}]
            }
        return {
            "strategy": "extract_function",
            "files_affected": files,
            "generated_code": {
                "extracted_function": "",
                "replacements": replacements
            },
            "language": "python"
        }

    def test_backup_created_on_apply(self) -> None:
        """Test that backup is created when applying changes."""
        new_content = "def func1():\n    print('modified')\n"
        plan = self._create_plan_with_content([self.test_file1], [new_content])

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        assert result["status"] == "success"
        assert result["backup_id"] is not None
        assert result["backup_id"].startswith("dedup-backup-")

        # Verify backup directory exists
        backup_dir = os.path.join(self.project_folder, ".ast-grep-backups", result["backup_id"])
        assert os.path.isdir(backup_dir)

        # Verify metadata exists
        metadata_path = os.path.join(backup_dir, "backup-metadata.json")
        assert os.path.isfile(metadata_path)

    def test_backup_metadata_contains_deduplication_info(self) -> None:
        """Test that backup metadata includes deduplication-specific info."""
        new_content = "def func1():\n    print('modified')\n"
        plan = self._create_plan_with_content([self.test_file1], [new_content])

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=42,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        # Read and verify metadata
        metadata_path = os.path.join(
            self.project_folder, ".ast-grep-backups",
            result["backup_id"], "backup-metadata.json"
        )
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        assert metadata["backup_type"] == "deduplication"
        assert "deduplication_metadata" in metadata
        assert metadata["deduplication_metadata"]["duplicate_group_id"] == 42
        assert metadata["deduplication_metadata"]["strategy"] == "extract_function"
        assert "original_hashes" in metadata["deduplication_metadata"]

    def test_backup_preserves_original_files(self) -> None:
        """Test that backup contains the original file content."""
        new_content = "def func1():\n    print('modified')\n"
        plan = self._create_plan_with_content([self.test_file1], [new_content])

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        # Find backup file
        backup_dir = os.path.join(self.project_folder, ".ast-grep-backups", result["backup_id"])
        backup_file = os.path.join(backup_dir, "file1.py")

        assert os.path.isfile(backup_file)

        # Verify backup contains original content
        with open(backup_file, "r") as f:
            backup_content = f.read()
        assert backup_content == self.original_content1

    def test_rollback_restores_original_content(self) -> None:
        """Test that rollback restores original file content."""
        new_content = "def func1():\n    print('modified')\n"
        plan = self._create_plan_with_content([self.test_file1], [new_content])

        # Apply changes
        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        backup_id = result["backup_id"]

        # Verify file was modified
        with open(self.test_file1, "r") as f:
            assert f.read() == new_content

        # Rollback
        restored = main.restore_from_backup(backup_id, self.project_folder)

        # Verify original content restored
        with open(self.test_file1, "r") as f:
            restored_content = f.read()
        assert restored_content == self.original_content1
        assert self.test_file1 in restored["restored_files"]

    def test_multi_file_backup_and_rollback(self) -> None:
        """Test backup and rollback with multiple files."""
        new_content1 = "# Modified file 1\n"
        new_content2 = "# Modified file 2\n"
        plan = self._create_plan_with_content(
            [self.test_file1, self.test_file2],
            [new_content1, new_content2]
        )

        # Apply changes
        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        # Verify both files modified
        with open(self.test_file1, "r") as f:
            assert f.read() == new_content1
        with open(self.test_file2, "r") as f:
            assert f.read() == new_content2

        # Rollback
        restored = main.restore_from_backup(result["backup_id"], self.project_folder)

        # Verify both files restored
        with open(self.test_file1, "r") as f:
            assert f.read() == self.original_content1
        with open(self.test_file2, "r") as f:
            assert f.read() == self.original_content2
        assert len(restored["restored_files"]) == 2

    def test_no_backup_when_backup_false(self) -> None:
        """Test that no backup is created when backup=False."""
        new_content = "def func1():\n    print('modified')\n"
        plan = self._create_plan_with_content([self.test_file1], [new_content])

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=False
        )

        assert result["status"] == "success"
        assert result["backup_id"] is None

        # Verify no backup directory created
        backup_dir = os.path.join(self.project_folder, ".ast-grep-backups")
        if os.path.exists(backup_dir):
            # Should be empty if exists
            assert len(os.listdir(backup_dir)) == 0

    def test_backup_id_in_rollback_command(self) -> None:
        """Test that response includes rollback command with backup_id."""
        new_content = "# Modified\n"
        plan = self._create_plan_with_content([self.test_file1], [new_content])

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        assert "rollback_command" in result
        assert result["backup_id"] in result["rollback_command"]
        assert "rollback_rewrite" in result["rollback_command"]


class TestPhase33MultiFileOrchestration:
    """Tests for Phase 3.3 Multi-File Orchestration in apply_deduplication."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir

        # Create subdirectory structure
        self.src_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(self.src_dir)

        # Create sample Python files with imports
        self.test_file1 = os.path.join(self.src_dir, "file1.py")
        self.original_content1 = "import os\n\ndef func1():\n    return os.getcwd()\n"
        with open(self.test_file1, "w") as f:
            f.write(self.original_content1)

        self.test_file2 = os.path.join(self.src_dir, "file2.py")
        self.original_content2 = "import os\n\ndef func2():\n    return os.getcwd()\n"
        with open(self.test_file2, "w") as f:
            f.write(self.original_content2)

        # Get tool function
        self.apply_deduplication = main.mcp.tools.get("apply_deduplication")  # type: ignore
        assert self.apply_deduplication is not None

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_plan_with_extraction(
        self,
        files: list[str],
        new_contents: list[str],
        extracted_function: str = "",
        extract_to_file: str = "",
        function_name: str = "extracted_func"
    ) -> Dict[str, Any]:
        """Create a refactoring plan with extracted function."""
        replacements = {}
        for f, content in zip(files, new_contents):
            replacements[f] = {
                "new_content": content,
                "changes": [{"line": 1, "old": "original", "new": "modified"}]
            }
        return {
            "strategy": "extract_function",
            "files_affected": files,
            "generated_code": {
                "extracted_function": extracted_function,
                "extract_to_file": extract_to_file,
                "function_name": function_name,
                "replacements": replacements
            },
            "language": "python"
        }

    def test_orchestration_creates_extracted_function_file(self) -> None:
        """Test that orchestration creates new file for extracted function."""
        extracted_func = "def get_cwd():\n    import os\n    return os.getcwd()\n"
        target_file = os.path.join(self.src_dir, "utils.py")

        new_content1 = "from utils import get_cwd\n\ndef func1():\n    return get_cwd()\n"
        new_content2 = "from utils import get_cwd\n\ndef func2():\n    return get_cwd()\n"

        plan = self._create_plan_with_extraction(
            files=[self.test_file1, self.test_file2],
            new_contents=[new_content1, new_content2],
            extracted_function=extracted_func,
            extract_to_file=target_file,
            function_name="get_cwd"
        )

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        assert result["status"] == "success"

        # Verify extracted function file was created
        assert os.path.isfile(target_file)
        with open(target_file, "r") as f:
            content = f.read()
        assert "def get_cwd():" in content

    def test_orchestration_creates_file_before_updates(self) -> None:
        """Test that extracted function file is created before updating source files."""
        extracted_func = "def common_func():\n    pass\n"
        target_file = os.path.join(self.src_dir, "_common.py")

        plan = self._create_plan_with_extraction(
            files=[self.test_file1],
            new_contents=["# Modified\n"],
            extracted_function=extracted_func,
            extract_to_file=target_file
        )

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        assert result["status"] == "success"

        # Both files should be in modified list, with target first
        assert target_file in result["files_modified"]
        assert self.test_file1 in result["files_modified"]

    def test_orchestration_atomic_rollback_on_failure(self) -> None:
        """Test that all changes are rolled back on failure."""
        extracted_func = "def common_func():\n    pass\n"
        target_file = os.path.join(self.src_dir, "utils.py")

        # First file will succeed, second will have invalid path
        non_existent = os.path.join(self.temp_dir, "nonexistent", "deep", "file.py")

        plan = self._create_plan_with_extraction(
            files=[self.test_file1],
            new_contents=["# Modified file 1\n"],
            extracted_function=extracted_func,
            extract_to_file=target_file
        )

        # Add a file that doesn't exist to trigger failure after first write
        plan["generated_code"]["replacements"][non_existent] = {
            "new_content": "# This should fail\n"
        }
        plan["files_affected"].append(non_existent)

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        # Should succeed because non-existent file is skipped
        assert result["status"] == "success"

        # Verify file1 was modified
        with open(self.test_file1, "r") as f:
            assert "Modified" in f.read()

    def test_orchestration_appends_to_existing_file(self) -> None:
        """Test that extracted function is appended to existing file."""
        # Create existing utils file
        target_file = os.path.join(self.src_dir, "utils.py")
        existing_content = "# Existing utilities\n\ndef existing_func():\n    pass\n"
        with open(target_file, "w") as f:
            f.write(existing_content)

        extracted_func = "def new_func():\n    pass\n"

        plan = self._create_plan_with_extraction(
            files=[self.test_file1],
            new_contents=["# Modified\n"],
            extracted_function=extracted_func,
            extract_to_file=target_file
        )

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        assert result["status"] == "success"

        # Verify both existing and new content are present
        with open(target_file, "r") as f:
            content = f.read()
        assert "existing_func" in content
        assert "new_func" in content

    def test_orchestration_handles_multiple_files_atomically(self) -> None:
        """Test atomic modification of multiple files."""
        extracted_func = "def shared_func():\n    return 42\n"
        target_file = os.path.join(self.src_dir, "_shared.py")

        new_content1 = "def func1():\n    from _shared import shared_func\n    return shared_func()\n"
        new_content2 = "def func2():\n    from _shared import shared_func\n    return shared_func()\n"

        plan = self._create_plan_with_extraction(
            files=[self.test_file1, self.test_file2],
            new_contents=[new_content1, new_content2],
            extracted_function=extracted_func,
            extract_to_file=target_file,
            function_name="shared_func"
        )

        result = self.apply_deduplication(
            project_folder=self.project_folder,
            group_id=1,
            refactoring_plan=plan,
            dry_run=False,
            backup=True
        )

        assert result["status"] == "success"
        assert len(result["files_modified"]) == 3  # target + 2 source files

        # Verify all files exist and have correct content
        assert os.path.isfile(target_file)
        with open(self.test_file1, "r") as f:
            assert "shared_func" in f.read()
        with open(self.test_file2, "r") as f:
            assert "shared_func" in f.read()


class TestOrchestrationHelperFunctions:
    """Tests for Phase 3.3 orchestration helper functions."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plan_file_modification_order_basic(self) -> None:
        """Test _plan_file_modification_order returns correct structure."""
        files = [os.path.join(self.temp_dir, "file1.py")]
        generated_code = {
            "extracted_function": "def func():\n    pass\n",
            "function_name": "func",
            "extract_to_file": os.path.join(self.temp_dir, "utils.py"),
            "replacements": {}
        }

        plan = main._plan_file_modification_order(
            files_to_modify=files,
            generated_code=generated_code,
            extract_to_file=None,
            project_folder=self.temp_dir,
            language="python"
        )

        assert "create_files" in plan
        assert "update_files" in plan
        assert "import_additions" in plan
        assert len(plan["create_files"]) == 1
        assert len(plan["update_files"]) == 1

    def test_add_import_to_content_python(self) -> None:
        """Test _add_import_to_content for Python files."""
        content = "import os\n\ndef main():\n    pass\n"
        import_stmt = "from utils import helper"

        result = main._add_import_to_content(content, import_stmt, "python")

        assert "from utils import helper" in result
        # Should be after existing imports
        assert result.index("from utils import helper") > result.index("import os")

    def test_add_import_to_content_python_no_existing_imports(self) -> None:
        """Test _add_import_to_content when no imports exist."""
        content = "def main():\n    pass\n"
        import_stmt = "from utils import helper"

        result = main._add_import_to_content(content, import_stmt, "python")

        assert result.startswith("from utils import helper")

    def test_add_import_to_content_typescript(self) -> None:
        """Test _add_import_to_content for TypeScript files."""
        content = "import { useState } from 'react';\n\nfunction App() {}\n"
        import_stmt = "import { helper } from './utils'"

        result = main._add_import_to_content(content, import_stmt, "typescript")

        assert "import { helper } from './utils'" in result

    def test_add_import_to_content_skips_duplicate(self) -> None:
        """Test that duplicate imports are not added."""
        content = "import os\nfrom utils import helper\n\ndef main():\n    pass\n"
        import_stmt = "from utils import helper"

        result = main._add_import_to_content(content, import_stmt, "python")

        # Should appear only once
        assert result.count("from utils import helper") == 1

    def test_generate_import_for_extracted_function(self) -> None:
        """Test _generate_import_for_extracted_function generates correct imports."""
        source = os.path.join(self.temp_dir, "src", "file.py")
        target = os.path.join(self.temp_dir, "src", "utils.py")

        result = main._generate_import_for_extracted_function(
            source_file=source,
            target_file=target,
            function_name="helper",
            project_folder=self.temp_dir,
            language="python"
        )

        assert "helper" in result
        assert "import" in result
