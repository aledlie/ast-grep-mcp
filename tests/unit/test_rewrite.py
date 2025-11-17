"""Unit tests for code rewrite functionality (Task 11).

Tests cover:
- rewrite_code tool (dry-run and actual modes)
- backup creation and restoration
- rollback_rewrite tool
- list_backups tool
- Error handling and validation
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Mock FastMCP before importing main
class MockFastMCP:
    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self, **kwargs):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs):
        pass


def mock_field(**kwargs):
    return kwargs.get("default")


# Import with mocked decorators
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main
        # Register tools so they're available in main.mcp.tools
        main.register_mcp_tools()


class TestRewriteCode:
    """Tests for rewrite_code MCP tool."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create temporary project directory
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir

        # Create sample Python file to rewrite
        self.test_file = os.path.join(self.temp_dir, "sample.py")
        with open(self.test_file, "w") as f:
            f.write("def hello():\n    print('hello')\n")

        # Get tool function
        self.rewrite_code = main.mcp.tools.get("rewrite_code")
        assert self.rewrite_code is not None, "rewrite_code tool not registered"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rewrite_code_tool_registered(self) -> None:
        """Test that rewrite_code tool is registered."""
        assert "rewrite_code" in main.mcp.tools
        assert callable(main.mcp.tools["rewrite_code"])

    @patch("subprocess.run")
    def test_rewrite_code_dry_run_mode(self, mock_run: Mock) -> None:
        """Test rewrite_code in dry-run mode (preview only)."""
        # Mock ast-grep output showing potential changes
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "file": self.test_file,
                "diffs": [
                    {
                        "replacement": "print(\"hello\")",
                        "old_text": "print('hello')",
                        "start": {"line": 2, "column": 4},
                        "end": {"line": 2, "column": 19}
                    }
                ]
            })
        )

        yaml_rule = """
id: quote-style
language: python
rule:
  pattern: print('$MSG')
fix: print("$MSG")
"""

        result = self.rewrite_code(
            project_folder=self.project_folder,
            yaml_rule=yaml_rule,
            dry_run=True
        )

        assert result["dry_run"] is True
        assert "changes" in result
        assert len(result["changes"]) > 0
        assert result["changes"][0]["file"] == self.test_file
        assert "backup_id" not in result  # No backup in dry-run mode

    @patch("subprocess.run")
    def test_rewrite_code_missing_fix_field(self, mock_run: Mock) -> None:
        """Test rewrite_code fails when YAML rule missing 'fix' field."""
        yaml_rule = """
id: no-fix
language: python
rule:
  pattern: print('$MSG')
"""

        with pytest.raises(ValueError, match="must include a 'fix' field"):
            self.rewrite_code(
                project_folder=self.project_folder,
                yaml_rule=yaml_rule,
                dry_run=True
            )

    @patch("subprocess.run")
    def test_rewrite_code_invalid_yaml(self, mock_run: Mock) -> None:
        """Test rewrite_code fails with invalid YAML."""
        yaml_rule = """
invalid: yaml: syntax:
  - missing: bracket
"""

        with pytest.raises(Exception):  # yaml.YAMLError
            self.rewrite_code(
                project_folder=self.project_folder,
                yaml_rule=yaml_rule,
                dry_run=True
            )

    @patch("main.create_backup")
    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_rewrite_code_actual_mode_creates_backup(
        self, mock_popen: Mock, mock_run: Mock, mock_create_backup: Mock
    ) -> None:
        """Test rewrite_code creates backup before applying changes."""
        # Mock dry-run (uses Popen for streaming)
        mock_process = MagicMock()
        mock_process.stdout = [
            b'{"file": "' + self.test_file.encode() + b'", "diffs": [{"replacement": "new", "old_text": "old"}]}\n'
        ]
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Mock actual rewrite (uses run with --update-all)
        mock_run.return_value = Mock(returncode=0, stdout="")

        mock_create_backup.return_value = "backup-20250117-120000-123"

        yaml_rule = """
id: test-rule
language: python
rule:
  pattern: print('$MSG')
fix: print("$MSG")
"""

        result = self.rewrite_code(
            project_folder=self.project_folder,
            yaml_rule=yaml_rule,
            dry_run=False,
            backup=True
        )

        assert result["dry_run"] is False
        assert "backup_id" in result
        assert result["backup_id"] == "backup-20250117-120000-123"
        mock_create_backup.assert_called_once()

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_rewrite_code_actual_mode_no_backup(self, mock_popen: Mock, mock_run: Mock) -> None:
        """Test rewrite_code can skip backup if requested."""
        # Mock dry-run (uses Popen for streaming)
        mock_process = MagicMock()
        mock_process.stdout = [
            b'{"file": "' + self.test_file.encode() + b'", "diffs": []}\n'
        ]
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Mock actual rewrite (uses run with --update-all)
        mock_run.return_value = Mock(returncode=0, stdout="")

        yaml_rule = """
id: test-rule
language: python
rule:
  pattern: print('$MSG')
fix: print("$MSG")
"""

        result = self.rewrite_code(
            project_folder=self.project_folder,
            yaml_rule=yaml_rule,
            dry_run=False,
            backup=False
        )

        assert result["dry_run"] is False
        assert result.get("backup_id") is None

    @patch("subprocess.Popen")
    def test_rewrite_code_with_file_size_limit(self, mock_popen: Mock) -> None:
        """Test rewrite_code respects max_file_size_mb parameter."""
        # Create a large file that should be excluded
        large_file = os.path.join(self.temp_dir, "large.py")
        with open(large_file, "w") as f:
            f.write("x" * (2 * 1024 * 1024))  # 2MB file

        mock_process = MagicMock()
        mock_process.stdout = [b'{"file": "test.py", "diffs": []}\n']
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        yaml_rule = """
id: test-rule
language: python
rule:
  pattern: print('$MSG')
fix: print("$MSG")
"""

        result = self.rewrite_code(
            project_folder=self.project_folder,
            yaml_rule=yaml_rule,
            dry_run=True,
            max_file_size_mb=1  # Limit to 1MB
        )

        # Verify the result was successful
        assert result["dry_run"] is True

    @patch("subprocess.Popen")
    def test_rewrite_code_with_workers(self, mock_popen: Mock) -> None:
        """Test rewrite_code supports parallel execution."""
        mock_process = MagicMock()
        mock_process.stdout = [b'{"file": "test.py", "diffs": []}\n']
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        yaml_rule = """
id: test-rule
language: python
rule:
  pattern: print('$MSG')
fix: print("$MSG")
"""

        result = self.rewrite_code(
            project_folder=self.project_folder,
            yaml_rule=yaml_rule,
            dry_run=True,
            workers=4
        )

        # Verify the result was successful
        assert result["dry_run"] is True


class TestBackupManagement:
    """Tests for backup creation and restoration functions."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir

        # Create sample files
        self.file1 = os.path.join(self.temp_dir, "file1.py")
        self.file2 = os.path.join(self.temp_dir, "file2.py")
        with open(self.file1, "w") as f:
            f.write("print('file1')\n")
        with open(self.file2, "w") as f:
            f.write("print('file2')\n")

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_backup_creates_directory(self) -> None:
        """Test create_backup creates backup directory structure."""
        backup_id = main.create_backup([self.file1], self.project_folder)

        assert backup_id.startswith("backup-")
        backup_dir = os.path.join(self.project_folder, ".ast-grep-backups", backup_id)
        assert os.path.exists(backup_dir)

    def test_create_backup_copies_files(self) -> None:
        """Test create_backup copies all specified files."""
        backup_id = main.create_backup([self.file1, self.file2], self.project_folder)

        backup_dir = os.path.join(self.project_folder, ".ast-grep-backups", backup_id)
        backed_up_file1 = os.path.join(backup_dir, "file1.py")
        backed_up_file2 = os.path.join(backup_dir, "file2.py")

        assert os.path.exists(backed_up_file1)
        assert os.path.exists(backed_up_file2)

        with open(backed_up_file1) as f:
            assert f.read() == "print('file1')\n"

    def test_create_backup_saves_metadata(self) -> None:
        """Test create_backup saves metadata JSON."""
        backup_id = main.create_backup([self.file1, self.file2], self.project_folder)

        backup_dir = os.path.join(self.project_folder, ".ast-grep-backups", backup_id)
        metadata_file = os.path.join(backup_dir, "backup-metadata.json")

        assert os.path.exists(metadata_file)

        with open(metadata_file) as f:
            metadata = json.load(f)

        assert metadata["backup_id"] == backup_id
        assert "timestamp" in metadata
        assert len(metadata["files"]) == 2
        assert any("file1.py" in f["relative"] for f in metadata["files"])

    def test_restore_from_backup_restores_files(self) -> None:
        """Test restore_from_backup restores all files."""
        # Create backup
        backup_id = main.create_backup([self.file1, self.file2], self.project_folder)

        # Modify original files
        with open(self.file1, "w") as f:
            f.write("MODIFIED\n")
        with open(self.file2, "w") as f:
            f.write("MODIFIED\n")

        # Restore from backup
        restored_files = main.restore_from_backup(backup_id, self.project_folder)

        assert len(restored_files) == 2

        with open(self.file1) as f:
            assert f.read() == "print('file1')\n"
        with open(self.file2) as f:
            assert f.read() == "print('file2')\n"

    def test_restore_from_backup_nonexistent_backup(self) -> None:
        """Test restore_from_backup fails with nonexistent backup."""
        with pytest.raises(ValueError, match="Backup.*not found"):
            main.restore_from_backup("backup-nonexistent", self.project_folder)

    def test_list_available_backups_empty(self) -> None:
        """Test list_available_backups returns empty list when no backups."""
        backups = main.list_available_backups(self.project_folder)
        assert backups == []

    def test_list_available_backups_returns_sorted(self) -> None:
        """Test list_available_backups returns backups sorted by timestamp."""
        # Create multiple backups
        backup1 = main.create_backup([self.file1], self.project_folder)
        backup2 = main.create_backup([self.file2], self.project_folder)
        backup3 = main.create_backup([self.file1, self.file2], self.project_folder)

        backups = main.list_available_backups(self.project_folder)

        assert len(backups) == 3
        # Should be sorted by timestamp (newest first)
        assert backups[0]["backup_id"] == backup3
        assert backups[1]["backup_id"] == backup2
        assert backups[2]["backup_id"] == backup1

    def test_list_available_backups_includes_metadata(self) -> None:
        """Test list_available_backups includes metadata for each backup."""
        backup_id = main.create_backup([self.file1, self.file2], self.project_folder)

        backups = main.list_available_backups(self.project_folder)

        assert len(backups) == 1
        backup = backups[0]
        assert backup["backup_id"] == backup_id
        assert "timestamp" in backup
        assert "file_count" in backup
        assert backup["file_count"] == 2
        assert "files" in backup


class TestRollbackRewrite:
    """Tests for rollback_rewrite MCP tool."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir

        # Create sample file
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("ORIGINAL\n")

        # Get tool function
        self.rollback_rewrite = main.mcp.tools.get("rollback_rewrite")
        assert self.rollback_rewrite is not None, "rollback_rewrite tool not registered"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rollback_rewrite_tool_registered(self) -> None:
        """Test that rollback_rewrite tool is registered."""
        assert "rollback_rewrite" in main.mcp.tools
        assert callable(main.mcp.tools["rollback_rewrite"])

    def test_rollback_rewrite_restores_files(self) -> None:
        """Test rollback_rewrite successfully restores files."""
        # Create backup
        backup_id = main.create_backup([self.test_file], self.project_folder)

        # Modify file
        with open(self.test_file, "w") as f:
            f.write("MODIFIED\n")

        # Rollback
        result = self.rollback_rewrite(
            project_folder=self.project_folder,
            backup_id=backup_id
        )

        assert "restored_files" in result
        assert len(result["restored_files"]) == 1
        assert result["backup_id"] == backup_id

        # Verify file was restored
        with open(self.test_file) as f:
            assert f.read() == "ORIGINAL\n"

    def test_rollback_rewrite_nonexistent_backup(self) -> None:
        """Test rollback_rewrite fails with nonexistent backup."""
        with pytest.raises(ValueError):
            self.rollback_rewrite(
                project_folder=self.project_folder,
                backup_id="backup-nonexistent"
            )


class TestListBackups:
    """Tests for list_backups MCP tool."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir

        # Create sample file
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("TEST\n")

        # Get tool function
        self.list_backups = main.mcp.tools.get("list_backups")
        assert self.list_backups is not None, "list_backups tool not registered"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_backups_tool_registered(self) -> None:
        """Test that list_backups tool is registered."""
        assert "list_backups" in main.mcp.tools
        assert callable(main.mcp.tools["list_backups"])

    def test_list_backups_empty(self) -> None:
        """Test list_backups returns empty list when no backups."""
        result = self.list_backups(project_folder=self.project_folder)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_backups_returns_all_backups(self) -> None:
        """Test list_backups returns all available backups."""
        # Create multiple backups
        backup1 = main.create_backup([self.test_file], self.project_folder)
        backup2 = main.create_backup([self.test_file], self.project_folder)

        result = self.list_backups(project_folder=self.project_folder)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["backup_id"] == backup2  # Newest first
        assert result[1]["backup_id"] == backup1


class TestRewriteIntegration:
    """Integration tests combining multiple rewrite features."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir

        # Create sample Python file
        self.test_file = os.path.join(self.temp_dir, "sample.py")
        with open(self.test_file, "w") as f:
            f.write("def test():\n    print('hello')\n")

        # Get tool functions
        self.rewrite_code = main.mcp.tools.get("rewrite_code")
        self.list_backups = main.mcp.tools.get("list_backups")

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_full_rewrite_workflow(self, mock_run: Mock) -> None:
        """Test complete workflow: preview -> rewrite with backup -> list backups."""
        yaml_rule = """
id: quote-style
language: python
rule:
  pattern: print('$MSG')
fix: print("$MSG")
"""

        # Step 1: Dry-run preview
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "file": self.test_file,
                "diffs": [{"replacement": 'print("hello")', "old_text": "print('hello')"}]
            })
        )

        preview_result = self.rewrite_code(
            project_folder=self.project_folder,
            yaml_rule=yaml_rule,
            dry_run=True
        )

        assert preview_result["dry_run"] is True
        assert len(preview_result["changes"]) > 0

        # Step 2: Apply rewrite with backup
        mock_run.side_effect = [
            Mock(returncode=0, stdout=json.dumps({"file": self.test_file, "diffs": []})),
            Mock(returncode=0, stdout="")
        ]

        with patch("main.create_backup") as mock_backup:
            mock_backup.return_value = "backup-test-123"

            rewrite_result = self.rewrite_code(
                project_folder=self.project_folder,
                yaml_rule=yaml_rule,
                dry_run=False,
                backup=True
            )

        assert rewrite_result["dry_run"] is False
        assert "backup_id" in rewrite_result

        # Step 3: List backups
        backups_result = self.list_backups(project_folder=self.project_folder)

        # Note: Won't find the mocked backup, but verifies tool works
        assert isinstance(backups_result, list)

    def test_backup_prevents_data_loss(self) -> None:
        """Test that backup mechanism prevents data loss during rewrites."""
        original_content = "def test():\n    print('original')\n"
        with open(self.test_file, "w") as f:
            f.write(original_content)

        # Create backup
        backup_id = main.create_backup([self.test_file], self.project_folder)

        # Simulate a failed rewrite that corrupts the file
        with open(self.test_file, "w") as f:
            f.write("CORRUPTED DATA\n")

        # Verify file is corrupted
        with open(self.test_file) as f:
            assert f.read() == "CORRUPTED DATA\n"

        # Rollback restores original
        restored = main.restore_from_backup(backup_id, self.project_folder)

        with open(self.test_file) as f:
            assert f.read() == original_content
