"""Unit tests for Phase 4.3: Test Coverage Detection.

Tests the test file pattern detection and coverage checking functions
for the deduplication analysis system.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ast_grep_mcp.features.deduplication.coverage import (
    find_test_file_patterns,
    get_test_coverage_for_files,
    has_test_coverage,
)
from main import (
    _check_test_file_references_source,
    _get_potential_test_paths,
)
    find_test_file_patterns,
    has_test_coverage,
    get_test_coverage_for_files,
    _get_potential_test_paths,
    _check_test_file_references_source,
)


class TestFindTestFilePatterns:
    """Tests for find_test_file_patterns function."""

    def test_python_patterns(self):
        """Test Python test file patterns."""
        patterns = find_test_file_patterns("python")
        assert "test_*.py" in patterns
        assert "*_test.py" in patterns
        assert "**/tests/*.py" in patterns

    def test_javascript_patterns(self):
        """Test JavaScript test file patterns."""
        patterns = find_test_file_patterns("javascript")
        assert "*.test.js" in patterns
        assert "*.spec.js" in patterns
        assert "**/__tests__/*.js" in patterns

    def test_typescript_patterns(self):
        """Test TypeScript test file patterns."""
        patterns = find_test_file_patterns("typescript")
        assert "*.test.ts" in patterns
        assert "*.spec.ts" in patterns
        assert "*.test.tsx" in patterns
        assert "**/__tests__/*.ts" in patterns

    def test_java_patterns(self):
        """Test Java test file patterns."""
        patterns = find_test_file_patterns("java")
        assert "*Test.java" in patterns
        assert "*Tests.java" in patterns
        assert "src/test/**/*.java" in patterns

    def test_go_patterns(self):
        """Test Go test file patterns."""
        patterns = find_test_file_patterns("go")
        assert "*_test.go" in patterns
        assert "**/*_test.go" in patterns

    def test_ruby_patterns(self):
        """Test Ruby test file patterns."""
        patterns = find_test_file_patterns("ruby")
        assert "*_test.rb" in patterns
        assert "*_spec.rb" in patterns
        assert "spec/*.rb" in patterns

    def test_rust_patterns(self):
        """Test Rust test file patterns."""
        patterns = find_test_file_patterns("rust")
        assert "**/tests/*.rs" in patterns

    def test_csharp_patterns(self):
        """Test C# test file patterns."""
        patterns = find_test_file_patterns("csharp")
        assert "*Test.cs" in patterns
        assert "*Tests.cs" in patterns

    def test_unknown_language_fallback(self):
        """Test fallback patterns for unknown languages."""
        patterns = find_test_file_patterns("unknown_lang")
        assert len(patterns) > 0
        assert "**/test*" in patterns

    def test_case_insensitive(self):
        """Test that language matching is case-insensitive."""
        patterns_lower = find_test_file_patterns("python")
        patterns_upper = find_test_file_patterns("PYTHON")
        assert patterns_lower == patterns_upper

    def test_language_aliases(self):
        """Test language aliases work correctly."""
        # JavaScript aliases
        js_patterns = find_test_file_patterns("js")
        javascript_patterns = find_test_file_patterns("javascript")
        assert js_patterns == javascript_patterns

        # TypeScript aliases
        ts_patterns = find_test_file_patterns("ts")
        typescript_patterns = find_test_file_patterns("typescript")
        assert ts_patterns == typescript_patterns


class TestGetPotentialTestPaths:
    """Tests for _get_potential_test_paths function."""

    def test_python_test_paths(self):
        """Test potential test path generation for Python."""
        project_root = "/project"
        source_file = "/project/src/utils.py"

        paths = _get_potential_test_paths(source_file, "python", project_root)

        # Should include common Python test patterns
        normalized_paths = [os.path.normpath(p) for p in paths]
        assert any("test_utils.py" in p for p in normalized_paths)
        assert any("utils_test.py" in p for p in normalized_paths)

    def test_javascript_test_paths(self):
        """Test potential test path generation for JavaScript."""
        project_root = "/project"
        source_file = "/project/src/utils.js"

        paths = _get_potential_test_paths(source_file, "javascript", project_root)

        normalized_paths = [os.path.normpath(p) for p in paths]
        assert any("utils.test.js" in p for p in normalized_paths)
        assert any("utils.spec.js" in p for p in normalized_paths)

    def test_typescript_tsx_extension(self):
        """Test that .tsx files get .tsx test paths."""
        project_root = "/project"
        source_file = "/project/src/Component.tsx"

        paths = _get_potential_test_paths(source_file, "typescript", project_root)

        normalized_paths = [os.path.normpath(p) for p in paths]
        assert any("Component.test.tsx" in p for p in normalized_paths)

    def test_typescript_ts_extension(self):
        """Test that .ts files get .ts test paths."""
        project_root = "/project"
        source_file = "/project/src/utils.ts"

        paths = _get_potential_test_paths(source_file, "typescript", project_root)

        normalized_paths = [os.path.normpath(p) for p in paths]
        assert any("utils.test.ts" in p for p in normalized_paths)

    def test_java_test_paths(self):
        """Test potential test path generation for Java."""
        project_root = "/project"
        source_file = "/project/src/main/java/com/example/MyClass.java"

        paths = _get_potential_test_paths(source_file, "java", project_root)

        normalized_paths = [os.path.normpath(p) for p in paths]
        assert any("MyClassTest.java" in p for p in normalized_paths)

    def test_go_test_paths(self):
        """Test potential test path generation for Go."""
        project_root = "/project"
        source_file = "/project/pkg/utils.go"

        paths = _get_potential_test_paths(source_file, "go", project_root)

        normalized_paths = [os.path.normpath(p) for p in paths]
        assert any("utils_test.go" in p for p in normalized_paths)

    def test_paths_are_normalized(self):
        """Test that all returned paths are normalized."""
        project_root = "/project"
        source_file = "/project/src/utils.py"

        paths = _get_potential_test_paths(source_file, "python", project_root)

        for path in paths:
            assert path == os.path.normpath(path)


class TestCheckTestFileReferencesSource:
    """Tests for _check_test_file_references_source function."""

    def test_python_import_detection(self):
        """Test Python import detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import pytest
from utils import helper_function

def test_helper():
    result = helper_function()
    assert result is not None
""")
            f.flush()
            test_path = f.name

        try:
            source_path = "/project/utils.py"
            result = _check_test_file_references_source(test_path, source_path, "python")
            assert result is True
        finally:
            os.unlink(test_path)

    def test_python_from_import_detection(self):
        """Test Python 'from X import' detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from .mymodule import MyClass

def test_myclass():
    obj = MyClass()
""")
            f.flush()
            test_path = f.name

        try:
            source_path = "/project/mymodule.py"
            result = _check_test_file_references_source(test_path, source_path, "python")
            assert result is True
        finally:
            os.unlink(test_path)

    def test_javascript_import_detection(self):
        """Test JavaScript import detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write("""
import { helper } from './utils';

describe('helper', () => {
    it('should work', () => {
        expect(helper()).toBeDefined();
    });
});
""")
            f.flush()
            test_path = f.name

        try:
            source_path = "/project/utils.js"
            result = _check_test_file_references_source(test_path, source_path, "javascript")
            assert result is True
        finally:
            os.unlink(test_path)

    def test_javascript_require_detection(self):
        """Test JavaScript require detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write("""
const utils = require('./utils');

test('utils work', () => {
    expect(utils.helper()).toBeDefined();
});
""")
            f.flush()
            test_path = f.name

        try:
            source_path = "/project/utils.js"
            result = _check_test_file_references_source(test_path, source_path, "javascript")
            assert result is True
        finally:
            os.unlink(test_path)

    def test_java_import_detection(self):
        """Test Java import detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write("""
package com.example.test;

import com.example.MyClass;
import org.junit.Test;

public class MyClassTest {
    @Test
    public void testSomething() {
        MyClass obj = new MyClass();
    }
}
""")
            f.flush()
            test_path = f.name

        try:
            source_path = "/project/MyClass.java"
            result = _check_test_file_references_source(test_path, source_path, "java")
            assert result is True
        finally:
            os.unlink(test_path)

    def test_go_same_directory_detection(self):
        """Test Go test file in same directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source and test in same directory
            source_path = os.path.join(tmpdir, "utils.go")
            test_path = os.path.join(tmpdir, "utils_test.go")

            with open(source_path, 'w') as f:
                f.write("package main\n")

            with open(test_path, 'w') as f:
                f.write("package main\n\nfunc TestUtils(t *testing.T) {}\n")

            result = _check_test_file_references_source(test_path, source_path, "go")
            assert result is True

    def test_fallback_name_in_content(self):
        """Test fallback: source name appears in test content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
# Testing utils functionality
def test_something():
    # This tests utils behavior
    pass
""")
            f.flush()
            test_path = f.name

        try:
            source_path = "/project/utils.py"
            result = _check_test_file_references_source(test_path, source_path, "python")
            assert result is True
        finally:
            os.unlink(test_path)

    def test_no_reference_found(self):
        """Test when no reference is found."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def test_something():
    assert True
""")
            f.flush()
            test_path = f.name

        try:
            source_path = "/project/mymodule.py"
            result = _check_test_file_references_source(test_path, source_path, "python")
            assert result is False
        finally:
            os.unlink(test_path)

    def test_nonexistent_test_file(self):
        """Test handling of nonexistent test file."""
        result = _check_test_file_references_source(
            "/nonexistent/test.py",
            "/project/utils.py",
            "python"
        )
        assert result is False


class TestHasTestCoverage:
    """Tests for has_test_coverage function."""

    def test_finds_direct_test_file(self):
        """Test finding a direct test file match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source file
            source_path = os.path.join(tmpdir, "utils.py")
            with open(source_path, 'w') as f:
                f.write("def helper(): pass\n")

            # Create corresponding test file
            test_path = os.path.join(tmpdir, "test_utils.py")
            with open(test_path, 'w') as f:
                f.write("from utils import helper\ndef test_helper(): pass\n")

            result = has_test_coverage(source_path, "python", tmpdir)
            assert result is True

    def test_finds_test_in_tests_directory(self):
        """Test finding a test file in tests/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source file
            source_path = os.path.join(tmpdir, "utils.py")
            with open(source_path, 'w') as f:
                f.write("def helper(): pass\n")

            # Create tests directory with test file
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(tests_dir)
            test_path = os.path.join(tests_dir, "test_utils.py")
            with open(test_path, 'w') as f:
                f.write("from utils import helper\ndef test_helper(): pass\n")

            result = has_test_coverage(source_path, "python", tmpdir)
            assert result is True

    def test_no_coverage_found(self):
        """Test when no test coverage exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source file only
            source_path = os.path.join(tmpdir, "utils.py")
            with open(source_path, 'w') as f:
                f.write("def helper(): pass\n")

            result = has_test_coverage(source_path, "python", tmpdir)
            assert result is False

    def test_finds_test_by_reference(self):
        """Test finding test via content reference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source file
            source_path = os.path.join(tmpdir, "mymodule.py")
            with open(source_path, 'w') as f:
                f.write("def helper(): pass\n")

            # Create test file with different name but importing the module
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(tests_dir)
            test_path = os.path.join(tests_dir, "test_all.py")
            with open(test_path, 'w') as f:
                f.write("from mymodule import helper\ndef test_helper(): pass\n")

            result = has_test_coverage(source_path, "python", tmpdir)
            assert result is True

    def test_javascript_coverage(self):
        """Test JavaScript test coverage detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source file
            source_path = os.path.join(tmpdir, "utils.js")
            with open(source_path, 'w') as f:
                f.write("export const helper = () => {};\n")

            # Create test file
            test_path = os.path.join(tmpdir, "utils.test.js")
            with open(test_path, 'w') as f:
                f.write("import { helper } from './utils';\ntest('helper', () => {});\n")

            result = has_test_coverage(source_path, "javascript", tmpdir)
            assert result is True


class TestGetTestCoverageForFiles:
    """Tests for get_test_coverage_for_files function."""

    def test_multiple_files_coverage(self):
        """Test coverage detection for multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source files
            source1 = os.path.join(tmpdir, "utils.py")
            source2 = os.path.join(tmpdir, "helpers.py")
            source3 = os.path.join(tmpdir, "models.py")

            for path in [source1, source2, source3]:
                with open(path, 'w') as f:
                    f.write("# source\n")

            # Create test only for utils
            test_path = os.path.join(tmpdir, "test_utils.py")
            with open(test_path, 'w') as f:
                f.write("from utils import something\n")

            # Create test only for helpers
            test_path2 = os.path.join(tmpdir, "helpers_test.py")
            with open(test_path2, 'w') as f:
                f.write("from helpers import something\n")

            result = get_test_coverage_for_files(
                [source1, source2, source3],
                "python",
                tmpdir
            )

            assert result[source1] is True
            assert result[source2] is True
            assert result[source3] is False

    def test_empty_file_list(self):
        """Test with empty file list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_test_coverage_for_files([], "python", tmpdir)
            assert result == {}

    def test_all_covered(self):
        """Test when all files have coverage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source and test files
            source1 = os.path.join(tmpdir, "utils.py")
            source2 = os.path.join(tmpdir, "helpers.py")

            with open(source1, 'w') as f:
                f.write("# source\n")
            with open(source2, 'w') as f:
                f.write("# source\n")

            with open(os.path.join(tmpdir, "test_utils.py"), 'w') as f:
                f.write("from utils import x\n")
            with open(os.path.join(tmpdir, "test_helpers.py"), 'w') as f:
                f.write("from helpers import x\n")

            result = get_test_coverage_for_files(
                [source1, source2],
                "python",
                tmpdir
            )

            assert all(result.values())
            assert len(result) == 2

    def test_none_covered(self):
        """Test when no files have coverage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source1 = os.path.join(tmpdir, "utils.py")
            source2 = os.path.join(tmpdir, "helpers.py")

            with open(source1, 'w') as f:
                f.write("# source\n")
            with open(source2, 'w') as f:
                f.write("# source\n")

            result = get_test_coverage_for_files(
                [source1, source2],
                "python",
                tmpdir
            )

            assert not any(result.values())
            assert len(result) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_file_with_special_characters(self):
        """Test handling of files with special characters in name."""
        patterns = find_test_file_patterns("python")
        assert len(patterns) > 0

    def test_deeply_nested_path(self):
        """Test deeply nested file paths."""
        project_root = "/project"
        source_file = "/project/src/main/java/com/example/service/impl/MyClass.java"

        paths = _get_potential_test_paths(source_file, "java", project_root)
        assert len(paths) > 0

    def test_file_read_error_handling(self):
        """Test handling of file read errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "test.py")
            with open(test_path, 'w') as f:
                f.write("test content")

            # Make file unreadable
            os.chmod(test_path, 0o000)

            try:
                result = _check_test_file_references_source(
                    test_path,
                    "/project/utils.py",
                    "python"
                )
                # Should return False on error, not raise
                assert result is False
            finally:
                # Restore permissions for cleanup
                os.chmod(test_path, 0o644)

    def test_unicode_content(self):
        """Test handling of files with unicode content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                         delete=False, encoding='utf-8') as f:
            f.write("""
# -*- coding: utf-8 -*-
from utils import helper

def test_unicode():
    assert helper() == "Testing"
""")
            f.flush()
            test_path = f.name

        try:
            result = _check_test_file_references_source(
                test_path,
                "/project/utils.py",
                "python"
            )
            assert result is True
        finally:
            os.unlink(test_path)
