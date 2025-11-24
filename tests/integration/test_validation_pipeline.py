"""
Integration tests for Phase 3.5: Syntax Validation Pipeline
Tests the apply_deduplication tool's validation features.
"""

import os
import tempfile
import shutil
import pytest

# Import the main module functions
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from main import (
    _validate_code_for_language,
    _suggest_syntax_fix,
    validate_syntax,
    create_backup,
    restore_from_backup,
)


class TestValidateCodeForLanguage:
    """Test the _validate_code_for_language helper function."""

    def test_valid_python_code(self):
        """Test validation passes for valid Python code."""
        code = "def hello():\n    return 'world'"
        is_valid, error = _validate_code_for_language(code, "python")
        assert is_valid is True
        assert error is None

    def test_invalid_python_syntax(self):
        """Test validation fails for invalid Python syntax."""
        code = "def hello(\n    return 'world'"
        is_valid, error = _validate_code_for_language(code, "python")
        assert is_valid is False
        assert error is not None
        assert "syntax" in error.lower() or "line" in error.lower()

    def test_valid_javascript_code(self):
        """Test validation passes for valid JavaScript code."""
        code = "function hello() { return 'world'; }"
        is_valid, error = _validate_code_for_language(code, "javascript")
        # Note: JS validation may pass or skip depending on node availability
        assert is_valid is True or "not implemented" in (error or "").lower()

    def test_unsupported_language(self):
        """Test that unsupported languages return True with a note."""
        code = "some code"
        is_valid, error = _validate_code_for_language(code, "rust")
        assert is_valid is True
        assert error is not None
        assert "not implemented" in error.lower()


class TestSuggestSyntaxFix:
    """Test the _suggest_syntax_fix helper function."""

    def test_indent_error_suggestion(self):
        """Test suggestion for indentation errors."""
        suggestion = _suggest_syntax_fix("unexpected indent", "python")
        assert suggestion is not None
        assert "indent" in suggestion.lower()

    def test_missing_colon_suggestion(self):
        """Test suggestion for missing colon errors."""
        suggestion = _suggest_syntax_fix("expected ':'", "python")
        assert suggestion is not None
        assert "colon" in suggestion.lower()

    def test_unexpected_token_suggestion(self):
        """Test suggestion for unexpected token errors."""
        suggestion = _suggest_syntax_fix("Unexpected token", "javascript")
        assert suggestion is not None
        assert "semicolon" in suggestion.lower() or "bracket" in suggestion.lower()

    def test_no_error_returns_none(self):
        """Test that None error returns None suggestion."""
        suggestion = _suggest_syntax_fix(None, "python")
        assert suggestion is None

    def test_generic_error_gets_generic_suggestion(self):
        """Test that unknown errors get a generic suggestion."""
        suggestion = _suggest_syntax_fix("some unknown error", "python")
        assert suggestion is not None
        assert "review" in suggestion.lower()


class TestValidationPipelineIntegration:
    """Integration tests for the full validation pipeline."""

    def setup_method(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up the temporary directory after each test."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_validate_syntax_valid_python_file(self):
        """Test validate_syntax with a valid Python file."""
        file_path = os.path.join(self.test_dir, "valid.py")
        with open(file_path, 'w') as f:
            f.write("def hello():\n    return 'world'\n")

        result = validate_syntax(file_path, "python")
        assert result["valid"] is True
        assert result["error"] is None

    def test_validate_syntax_invalid_python_file(self):
        """Test validate_syntax with an invalid Python file."""
        file_path = os.path.join(self.test_dir, "invalid.py")
        with open(file_path, 'w') as f:
            f.write("def hello(\n    return 'world'\n")

        result = validate_syntax(file_path, "python")
        assert result["valid"] is False
        assert result["error"] is not None

    def test_backup_and_restore(self):
        """Test that backup and restore work correctly."""
        # Create a test file
        file_path = os.path.join(self.test_dir, "test.py")
        original_content = "original content"
        with open(file_path, 'w') as f:
            f.write(original_content)

        # Create backup
        backup_id = create_backup([file_path], self.test_dir)
        assert backup_id is not None

        # Modify the file
        modified_content = "modified content"
        with open(file_path, 'w') as f:
            f.write(modified_content)

        # Verify modification
        with open(file_path, 'r') as f:
            assert f.read() == modified_content

        # Restore from backup
        restored = restore_from_backup(backup_id, self.test_dir)
        assert file_path in restored

        # Verify restoration
        with open(file_path, 'r') as f:
            assert f.read() == original_content


class TestPreValidationScenarios:
    """Test pre-validation scenarios for apply_deduplication."""

    def test_pre_validation_catches_syntax_error(self):
        """Test that pre-validation catches syntax errors in extracted function."""
        # This tests the logic without calling the full tool
        invalid_code = "def broken(\n    return True"
        is_valid, error = _validate_code_for_language(invalid_code, "python")
        assert is_valid is False

        suggestion = _suggest_syntax_fix(error, "python")
        assert suggestion is not None

    def test_pre_validation_passes_valid_code(self):
        """Test that pre-validation passes valid extracted function."""
        valid_code = "def process_data(item):\n    return item.upper()"
        is_valid, error = _validate_code_for_language(valid_code, "python")
        assert is_valid is True


class TestPostValidationRollback:
    """Test post-validation and rollback scenarios."""

    def setup_method(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up the temporary directory after each test."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_rollback_restores_original_content(self):
        """Test that rollback properly restores original file content."""
        file_path = os.path.join(self.test_dir, "rollback_test.py")

        # Create original file
        original = "def original():\n    pass\n"
        with open(file_path, 'w') as f:
            f.write(original)

        # Create backup
        backup_id = create_backup([file_path], self.test_dir)

        # Write invalid content (simulating failed modification)
        invalid = "def broken(\n    pass"
        with open(file_path, 'w') as f:
            f.write(invalid)

        # Verify file is now invalid
        result = validate_syntax(file_path, "python")
        assert result["valid"] is False

        # Restore from backup
        restore_from_backup(backup_id, self.test_dir)

        # Verify file is restored and valid
        result = validate_syntax(file_path, "python")
        assert result["valid"] is True

        with open(file_path, 'r') as f:
            assert f.read() == original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
