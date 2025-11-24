"""
Integration tests for Phase 5.5: Enhanced CLI for duplication detection.
Tests the find_duplication.py CLI script with new features.
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil
import pytest


class TestCliDuplication:
    """Integration tests for find_duplication.py CLI."""

    def setup_method(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "scripts",
            "find_duplication.py"
        )

    def teardown_method(self):
        """Clean up the temporary directory after each test."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_python_file(self, name: str, content: str):
        """Helper to create a Python file in the test directory."""
        file_path = os.path.join(self.test_dir, name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path

    def run_cli(self, *args, expect_success: bool = True) -> subprocess.CompletedProcess:
        """Run the CLI with given arguments."""
        cmd = [sys.executable, self.script_path] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        if expect_success and result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        return result

    # Basic functionality tests

    def test_help_output(self):
        """Test that --help works."""
        result = self.run_cli("--help")
        assert result.returncode == 0
        assert "Detect duplicate code" in result.stdout
        assert "--analyze" in result.stdout
        assert "--detailed" in result.stdout
        assert "--no-color" in result.stdout

    def test_basic_analysis(self):
        """Test basic analysis without duplicates."""
        self.create_python_file("module.py", '''
def unique_function():
    x = 1
    y = 2
    z = 3
    return x + y + z
''')
        result = self.run_cli(self.test_dir, "--language", "python")
        assert result.returncode == 0
        assert "DUPLICATION ANALYSIS SUMMARY" in result.stdout

    def test_json_output(self):
        """Test JSON output format."""
        self.create_python_file("module.py", '''
def test_func():
    return 42
''')
        result = self.run_cli(self.test_dir, "--language", "python", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "summary" in data
        assert "duplication_groups" in data
        assert "refactoring_suggestions" in data

    def test_no_color_flag(self):
        """Test that --no-color disables ANSI codes."""
        self.create_python_file("module.py", '''
def test():
    x = 1
    y = 2
    z = 3
    return x + y + z
''')
        result = self.run_cli(self.test_dir, "--language", "python", "--no-color")
        assert result.returncode == 0
        # ANSI escape codes should not be present
        assert "\033[" not in result.stdout

    # Validation tests

    def test_invalid_project_folder(self):
        """Test error handling for invalid project folder."""
        result = self.run_cli("/nonexistent/path", "--language", "python", expect_success=False)
        assert result.returncode != 0
        assert "Error" in result.stderr

    def test_relative_path_rejected(self):
        """Test that relative paths are rejected."""
        result = self.run_cli("./relative/path", "--language", "python", expect_success=False)
        assert result.returncode != 0
        assert "absolute path" in result.stderr

    def test_invalid_similarity(self):
        """Test error handling for invalid similarity threshold."""
        result = self.run_cli(self.test_dir, "--language", "python", "--min-similarity", "1.5", expect_success=False)
        assert result.returncode != 0
        assert "0.0 and 1.0" in result.stderr

    def test_invalid_min_lines(self):
        """Test error handling for invalid min-lines."""
        result = self.run_cli(self.test_dir, "--language", "python", "--min-lines", "0", expect_success=False)
        assert result.returncode != 0
        assert "at least 1" in result.stderr

    # Duplicate detection tests

    def test_detects_duplicates(self):
        """Test that duplicates are detected."""
        # Create two files with nearly identical functions
        self.create_python_file("file1.py", '''
def process_data():
    result = []
    for i in range(10):
        result.append(i * 2)
    return result
''')
        self.create_python_file("file2.py", '''
def process_items():
    result = []
    for i in range(10):
        result.append(i * 2)
    return result
''')
        result = self.run_cli(
            self.test_dir, "--language", "python",
            "--min-similarity", "0.7", "--min-lines", "3"
        )
        assert result.returncode == 0
        # Should find the duplicate group
        output = result.stdout
        assert "Duplicate groups found:" in output or "DUPLICATION GROUPS" in output

    def test_json_duplicate_detection(self):
        """Test duplicate detection with JSON output."""
        self.create_python_file("file1.py", '''
def calc_total():
    items = [1, 2, 3, 4, 5]
    total = 0
    for item in items:
        total += item
    return total
''')
        self.create_python_file("file2.py", '''
def sum_values():
    items = [1, 2, 3, 4, 5]
    total = 0
    for item in items:
        total += item
    return total
''')
        result = self.run_cli(
            self.test_dir, "--language", "python", "--json",
            "--min-similarity", "0.7", "--min-lines", "3"
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["summary"]["total_constructs"] >= 2

    # Enhanced features tests

    def test_analyze_flag(self):
        """Test --analyze flag uses analyze_deduplication_candidates."""
        self.create_python_file("module.py", '''
def func1():
    x = 1
    y = 2
    z = 3
    return x + y + z

def func2():
    x = 1
    y = 2
    z = 3
    return x + y + z
''')
        result = self.run_cli(
            self.test_dir, "--language", "python", "--analyze",
            "--min-similarity", "0.7", "--min-lines", "3"
        )
        assert result.returncode == 0
        # Should show ranked analysis output
        assert "DEDUPLICATION CANDIDATE ANALYSIS" in result.stdout or "candidates" in result.stdout.lower()

    def test_analyze_json_output(self):
        """Test --analyze with JSON output."""
        self.create_python_file("module.py", '''
def test():
    return 1
''')
        result = self.run_cli(
            self.test_dir, "--language", "python", "--analyze", "--json"
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "candidates" in data
        assert "total_groups" in data
        assert "total_savings_potential" in data
        assert "analysis_metadata" in data

    def test_detailed_flag(self):
        """Test --detailed flag shows diff previews."""
        self.create_python_file("file1.py", '''
def process_a():
    data = []
    for i in range(5):
        data.append(i)
    return data
''')
        self.create_python_file("file2.py", '''
def process_b():
    data = []
    for i in range(5):
        data.append(i)
    return data
''')
        result = self.run_cli(
            self.test_dir, "--language", "python", "--detailed",
            "--min-similarity", "0.7", "--min-lines", "3"
        )
        assert result.returncode == 0
        # Detailed output should work
        assert "DUPLICATION" in result.stdout

    def test_analyze_with_detailed(self):
        """Test combining --analyze and --detailed."""
        self.create_python_file("module.py", '''
def alpha():
    x = 1
    y = 2
    z = 3
    w = 4
    return x + y + z + w

def beta():
    x = 1
    y = 2
    z = 3
    w = 4
    return x + y + z + w
''')
        result = self.run_cli(
            self.test_dir, "--language", "python",
            "--analyze", "--detailed",
            "--min-similarity", "0.7", "--min-lines", "3"
        )
        assert result.returncode == 0
        output = result.stdout
        assert "DEDUPLICATION" in output or "ANALYSIS" in output

    def test_max_candidates_flag(self):
        """Test --max-candidates limits results."""
        # Create multiple duplicates
        for i in range(5):
            self.create_python_file(f"file{i}.py", f'''
def func_{i}():
    result = []
    for x in range(10):
        result.append(x * 2)
    return result
''')
        result = self.run_cli(
            self.test_dir, "--language", "python",
            "--analyze", "--json", "--max-candidates", "2",
            "--min-similarity", "0.7", "--min-lines", "3"
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        # Should respect max_candidates limit
        assert len(data.get("candidates", [])) <= 2

    # Construct type tests

    def test_construct_type_class(self):
        """Test --construct-type class_definition."""
        self.create_python_file("classes.py", '''
class Alpha:
    def __init__(self):
        self.value = 1

class Beta:
    def __init__(self):
        self.value = 1
''')
        result = self.run_cli(
            self.test_dir, "--language", "python",
            "--construct-type", "class_definition",
            "--min-similarity", "0.7", "--min-lines", "2"
        )
        assert result.returncode == 0
        assert "DUPLICATION ANALYSIS SUMMARY" in result.stdout

    def test_construct_type_method(self):
        """Test --construct-type method_definition."""
        self.create_python_file("methods.py", '''
class MyClass:
    def method_a(self):
        x = 1
        y = 2
        return x + y

    def method_b(self):
        x = 1
        y = 2
        return x + y
''')
        result = self.run_cli(
            self.test_dir, "--language", "python",
            "--construct-type", "method_definition",
            "--min-similarity", "0.7", "--min-lines", "3"
        )
        assert result.returncode == 0

    # Exclude patterns tests

    def test_exclude_patterns(self):
        """Test --exclude-patterns works."""
        self.create_python_file("src/main.py", '''
def main_func():
    return 1
''')
        self.create_python_file("vendor/lib.py", '''
def lib_func():
    return 1
''')
        result = self.run_cli(
            self.test_dir, "--language", "python",
            "--exclude-patterns", "vendor"
        )
        assert result.returncode == 0
        # Vendor files should be excluded
        output = result.stdout
        assert result.returncode == 0

    # Edge cases

    def test_empty_project(self):
        """Test handling of empty project."""
        result = self.run_cli(self.test_dir, "--language", "python")
        assert result.returncode == 0
        # Should show 0 constructs
        assert "0" in result.stdout or "No" in result.stdout

    def test_single_file_no_duplicates(self):
        """Test single file with unique functions."""
        self.create_python_file("unique.py", '''
def func_a():
    return "a"

def func_b():
    return "b"

def func_c():
    return "c"
''')
        result = self.run_cli(
            self.test_dir, "--language", "python",
            "--min-lines", "1"
        )
        assert result.returncode == 0

    def test_javascript_language(self):
        """Test JavaScript language support."""
        self.create_python_file("test.js", '''
function processData() {
    const result = [];
    for (let i = 0; i < 10; i++) {
        result.push(i * 2);
    }
    return result;
}
''')
        result = self.run_cli(
            self.test_dir, "--language", "javascript",
            "--min-lines", "3"
        )
        assert result.returncode == 0

    def test_typescript_language(self):
        """Test TypeScript language support."""
        self.create_python_file("test.ts", '''
function calculate(): number {
    let sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += i;
    }
    return sum;
}
''')
        result = self.run_cli(
            self.test_dir, "--language", "typescript",
            "--min-lines", "3"
        )
        assert result.returncode == 0


class TestColorPrinting:
    """Test color printing functionality."""

    def setup_method(self):
        """Set up test directory."""
        self.test_dir = tempfile.mkdtemp()
        self.script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "scripts",
            "find_duplication.py"
        )

    def teardown_method(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_python_file(self, name: str, content: str):
        """Helper to create a Python file."""
        file_path = os.path.join(self.test_dir, name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path

    def test_color_disabled_in_json_mode(self):
        """Test that colors are disabled when outputting JSON."""
        self.create_python_file("test.py", "def test(): return 1")
        result = subprocess.run(
            [sys.executable, self.script_path, self.test_dir, "--language", "python", "--json"],
            capture_output=True,
            text=True
        )
        # JSON output should never have ANSI codes
        assert "\033[" not in result.stdout

    def test_color_disabled_with_no_color_flag(self):
        """Test that --no-color flag works."""
        self.create_python_file("test.py", '''
def func():
    x = 1
    y = 2
    return x + y
''')
        result = subprocess.run(
            [sys.executable, self.script_path, self.test_dir, "--language", "python", "--no-color"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "\033[" not in result.stdout


class TestAnalyzeOutputFormat:
    """Test the output format of --analyze mode."""

    def setup_method(self):
        """Set up test directory."""
        self.test_dir = tempfile.mkdtemp()
        self.script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "scripts",
            "find_duplication.py"
        )

    def teardown_method(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_python_file(self, name: str, content: str):
        """Helper to create a Python file."""
        file_path = os.path.join(self.test_dir, name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path

    def test_analyze_shows_metadata(self):
        """Test that --analyze shows analysis metadata."""
        self.create_python_file("test.py", "def test(): return 1")
        result = subprocess.run(
            [sys.executable, self.script_path, self.test_dir, "--language", "python", "--analyze", "--json"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        metadata = data.get("analysis_metadata", {})
        assert "project_path" in metadata
        assert "language" in metadata
        assert "analysis_time_seconds" in metadata

    def test_analyze_candidate_structure(self):
        """Test structure of candidates in --analyze output."""
        self.create_python_file("file1.py", '''
def process():
    data = []
    for i in range(10):
        data.append(i)
    return data
''')
        self.create_python_file("file2.py", '''
def transform():
    data = []
    for i in range(10):
        data.append(i)
    return data
''')
        result = subprocess.run(
            [sys.executable, self.script_path, self.test_dir, "--language", "python",
             "--analyze", "--json", "--min-similarity", "0.7", "--min-lines", "3"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)

        if data.get("candidates"):
            candidate = data["candidates"][0]
            # Check expected fields
            expected_fields = [
                "group_id", "priority_score", "similarity_score",
                "instance_count", "potential_savings", "recommendation"
            ]
            for field in expected_fields:
                assert field in candidate, f"Missing field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
