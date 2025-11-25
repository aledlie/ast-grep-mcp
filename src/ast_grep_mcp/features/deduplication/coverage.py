"""Test coverage detection for deduplication analysis."""

import os
import glob as glob_module
import re as regex_module
from typing import Dict, List, Optional

from ...utils import get_logger


class TestCoverageDetector:
    """Detects test coverage for source files to assess refactoring risk."""

    def __init__(self):
        """Initialize the test coverage detector."""
        self.logger = get_logger("deduplication.test_coverage")

    def find_test_file_patterns(self, language: str) -> List[str]:
        """Get test file patterns for a given programming language.

        Args:
            language: Programming language (python, javascript, typescript, java, etc.)

        Returns:
            List of glob patterns for test files in that language
        """
        lang = language.lower()

        if lang == "python":
            return [
                "test_*.py",
                "*_test.py",
                "tests/*.py",
                "**/tests/*.py",
                "**/test/*.py",
                "**/*_test.py",
                "**/test_*.py",
            ]
        elif lang in ("javascript", "js"):
            return [
                "*.test.js",
                "*.spec.js",
                "__tests__/*.js",
                "**/__tests__/*.js",
                "**/tests/*.js",
                "**/test/*.js",
                "**/*.test.js",
                "**/*.spec.js",
            ]
        elif lang in ("typescript", "ts", "tsx"):
            return [
                "*.test.ts",
                "*.test.tsx",
                "*.spec.ts",
                "*.spec.tsx",
                "__tests__/*.ts",
                "__tests__/*.tsx",
                "**/__tests__/*.ts",
                "**/__tests__/*.tsx",
                "**/tests/*.ts",
                "**/tests/*.tsx",
                "**/*.test.ts",
                "**/*.test.tsx",
                "**/*.spec.ts",
                "**/*.spec.tsx",
            ]
        elif lang == "java":
            return [
                "*Test.java",
                "*Tests.java",
                "**/*Test.java",
                "**/*Tests.java",
                "**/test/**/*.java",
                "src/test/**/*.java",
            ]
        elif lang == "go":
            return [
                "*_test.go",
                "**/*_test.go",
            ]
        elif lang in ("ruby", "rb"):
            return [
                "*_test.rb",
                "*_spec.rb",
                "test/*.rb",
                "spec/*.rb",
                "**/test/*.rb",
                "**/spec/*.rb",
                "**/*_test.rb",
                "**/*_spec.rb",
            ]
        elif lang in ("rust", "rs"):
            return [
                "**/tests/*.rs",
                "**/tests/**/*.rs",
            ]
        elif lang in ("csharp", "cs", "c#"):
            return [
                "*Tests.cs",
                "*Test.cs",
                "**/*Tests.cs",
                "**/*Test.cs",
                "**/Tests/**/*.cs",
            ]
        else:
            # Generic patterns for unknown languages
            return [
                "**/test*",
                "**/tests/*",
                "**/*test*",
                "**/*spec*",
            ]

    def _get_potential_test_paths(
        self,
        file_path: str,
        language: str,
        project_root: str
    ) -> List[str]:
        """Generate potential test file paths for a source file.

        Args:
            file_path: Path to the source file
            language: Programming language
            project_root: Root directory of the project

        Returns:
            List of potential test file paths that could contain tests for this file
        """
        # Get relative path from project root
        try:
            rel_path = os.path.relpath(file_path, project_root)
        except ValueError:
            rel_path = os.path.basename(file_path)

        # Get base name without extension
        basename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(basename)[0]
        ext = os.path.splitext(basename)[1]
        dir_path = os.path.dirname(rel_path)

        potential_paths: List[str] = []
        lang = language.lower()

        if lang == "python":
            # test_<name>.py, <name>_test.py
            potential_paths.extend([
                os.path.join(project_root, dir_path, f"test_{name_without_ext}.py"),
                os.path.join(project_root, dir_path, f"{name_without_ext}_test.py"),
                os.path.join(project_root, "tests", f"test_{name_without_ext}.py"),
                os.path.join(project_root, "tests", dir_path, f"test_{name_without_ext}.py"),
                os.path.join(project_root, "test", f"test_{name_without_ext}.py"),
                os.path.join(project_root, "tests", "unit", f"test_{name_without_ext}.py"),
                os.path.join(project_root, "tests", "integration", f"test_{name_without_ext}.py"),
            ])

        elif lang in ("javascript", "js"):
            potential_paths.extend([
                os.path.join(project_root, dir_path, f"{name_without_ext}.test.js"),
                os.path.join(project_root, dir_path, f"{name_without_ext}.spec.js"),
                os.path.join(project_root, dir_path, "__tests__", f"{name_without_ext}.js"),
                os.path.join(project_root, "tests", f"{name_without_ext}.test.js"),
                os.path.join(project_root, "__tests__", f"{name_without_ext}.js"),
            ])

        elif lang in ("typescript", "ts", "tsx"):
            # Handle both .ts and .tsx
            ts_ext = ".tsx" if ext == ".tsx" else ".ts"
            potential_paths.extend([
                os.path.join(project_root, dir_path, f"{name_without_ext}.test{ts_ext}"),
                os.path.join(project_root, dir_path, f"{name_without_ext}.spec{ts_ext}"),
                os.path.join(project_root, dir_path, "__tests__", f"{name_without_ext}{ts_ext}"),
                os.path.join(project_root, "tests", f"{name_without_ext}.test{ts_ext}"),
                os.path.join(project_root, "__tests__", f"{name_without_ext}{ts_ext}"),
            ])

        elif lang == "java":
            # Convert class name: MyClass.java -> MyClassTest.java
            potential_paths.extend([
                os.path.join(project_root, dir_path, f"{name_without_ext}Test.java"),
                os.path.join(project_root, dir_path, f"{name_without_ext}Tests.java"),
                # Maven/Gradle standard: src/test/java mirrors src/main/java
                os.path.join(
                    project_root, "src", "test", "java",
                    dir_path.replace("src/main/java/", "").replace("src\\main\\java\\", ""),
                    f"{name_without_ext}Test.java"
                ),
            ])

        elif lang == "go":
            potential_paths.extend([
                os.path.join(project_root, dir_path, f"{name_without_ext}_test.go"),
            ])

        elif lang in ("ruby", "rb"):
            potential_paths.extend([
                os.path.join(project_root, dir_path, f"{name_without_ext}_test.rb"),
                os.path.join(project_root, dir_path, f"{name_without_ext}_spec.rb"),
                os.path.join(project_root, "test", f"{name_without_ext}_test.rb"),
                os.path.join(project_root, "spec", f"{name_without_ext}_spec.rb"),
            ])

        return [os.path.normpath(p) for p in potential_paths]

    def _check_test_file_references_source(
        self,
        test_file_path: str,
        source_file_path: str,
        language: str
    ) -> bool:
        """Check if a test file references/imports the source file.

        Args:
            test_file_path: Path to the test file
            source_file_path: Path to the source file being tested
            language: Programming language

        Returns:
            True if the test file appears to test the source file
        """
        if not os.path.exists(test_file_path):
            return False

        try:
            with open(test_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except (IOError, OSError):
            return False

        # Get the module/class name from source file
        source_name = os.path.splitext(os.path.basename(source_file_path))[0]
        lang = language.lower()

        # Check for imports/references based on language
        if lang == "python":
            # Check for: from <module> import, import <module>
            import_patterns = [
                f"from {source_name} import",
                f"from .{source_name} import",
                f"import {source_name}",
                f"from.*{source_name}.*import",
            ]
            for pattern in import_patterns:
                if regex_module.search(pattern, content, regex_module.IGNORECASE):
                    return True

        elif lang in ("javascript", "js", "typescript", "ts", "tsx"):
            # Check for: require('<module>'), import from '<module>'
            import_patterns = [
                f"from ['\"].*{source_name}['\"]",
                f"require\\(['\"].*{source_name}['\"]\\)",
                f"import.*{source_name}",
            ]
            for pattern in import_patterns:
                if regex_module.search(pattern, content, regex_module.IGNORECASE):
                    return True

        elif lang == "java":
            # Check for: import <package>.<ClassName>
            class_name = source_name
            if regex_module.search(f"import.*\\.{class_name};", content):
                return True
            # Also check if class name is directly used
            if regex_module.search(f"\\b{class_name}\\b", content):
                return True

        elif lang == "go":
            # Go test files in same directory automatically have access
            source_dir = os.path.dirname(source_file_path)
            test_dir = os.path.dirname(test_file_path)
            if os.path.normpath(source_dir) == os.path.normpath(test_dir):
                return True
            # Check for package import
            if regex_module.search(f"import.*{source_name}", content):
                return True

        elif lang in ("ruby", "rb"):
            # Check for require/require_relative
            if regex_module.search(f"require.*{source_name}", content, regex_module.IGNORECASE):
                return True

        # Fallback: check if source file name appears anywhere in test
        if source_name.lower() in content.lower():
            return True

        return False

    def has_test_coverage(
        self,
        file_path: str,
        language: str,
        project_root: str
    ) -> bool:
        """Check if a source file has corresponding test coverage.

        Args:
            file_path: Path to the source file
            language: Programming language
            project_root: Root directory of the project

        Returns:
            True if test coverage exists for the file
        """
        # Get potential test file paths
        potential_tests = self._get_potential_test_paths(file_path, language, project_root)

        # Check if any potential test file exists
        for test_path in potential_tests:
            if os.path.exists(test_path):
                self.logger.debug(
                    "found_test_file",
                    source_file=file_path,
                    test_file=test_path
                )
                return True

        # Also search using glob patterns for more flexible matching
        patterns = self.find_test_file_patterns(language)

        for pattern in patterns:
            full_pattern = os.path.join(project_root, pattern)
            try:
                matches = glob_module.glob(full_pattern, recursive=True)
                for match in matches:
                    # Check if this test file references our source
                    if self._check_test_file_references_source(match, file_path, language):
                        self.logger.debug(
                            "found_test_by_reference",
                            source_file=file_path,
                            test_file=match
                        )
                        return True
            except Exception as e:
                self.logger.warning("glob_search_failed", pattern=pattern, error=str(e))
                continue

        self.logger.debug("no_test_coverage", source_file=file_path)
        return False

    def get_test_coverage_for_files(
        self,
        file_paths: List[str],
        language: str,
        project_root: str
    ) -> Dict[str, bool]:
        """Get test coverage status for multiple files.

        Args:
            file_paths: List of source file paths
            language: Programming language
            project_root: Root directory of the project

        Returns:
            Dictionary mapping file paths to their test coverage status
        """
        coverage_map: Dict[str, bool] = {}
        covered_count = 0

        for file_path in file_paths:
            has_coverage = self.has_test_coverage(file_path, language, project_root)
            coverage_map[file_path] = has_coverage
            if has_coverage:
                covered_count += 1

        self.logger.info(
            "test_coverage_analysis_complete",
            total_files=len(file_paths),
            files_with_coverage=covered_count,
            files_without_coverage=len(file_paths) - covered_count
        )

        return coverage_map


# Module-level functions for backwards compatibility
_detector = TestCoverageDetector()

def find_test_file_patterns(language: str) -> List[str]:
    """Get test file patterns for a given programming language."""
    return _detector.find_test_file_patterns(language)

def has_test_coverage(file_path: str, language: str, project_root: str) -> bool:
    """Check if a source file has corresponding test coverage."""
    return _detector.has_test_coverage(file_path, language, project_root)

def get_test_coverage_for_files(
    file_paths: List[str],
    language: str,
    project_root: str
) -> Dict[str, bool]:
    """Get test coverage status for multiple files."""
    return _detector.get_test_coverage_for_files(file_paths, language, project_root)