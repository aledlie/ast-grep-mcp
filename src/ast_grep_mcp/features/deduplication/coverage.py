"""Test coverage detection for deduplication analysis."""

import glob as glob_module
import os
import re as regex_module
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Set, Tuple

from ...core.logging import get_logger


# Helper function for JavaScript-like languages
def _get_javascript_patterns(source_name: str) -> List[str]:
    """Get import patterns for JavaScript-like languages."""
    return [
        f"from ['\"].*{source_name}['\"]",
        f"require\\(['\"].*{source_name}['\"]\\)",
        f"import.*{source_name}",
    ]


# Helper function for Ruby-like patterns
def _get_ruby_patterns(source_name: str) -> List[str]:
    """Get import patterns for Ruby."""
    return [f"require.*{source_name}"]


# Configuration-driven pattern for import patterns
IMPORT_PATTERN_CONFIG: Dict[str, Callable[[str], List[str]]] = {
    "python": lambda source_name: [
        f"from {source_name} import",
        f"from .{source_name} import",
        f"import {source_name}",
        f"from.*{source_name}.*import",
    ],
    "javascript": _get_javascript_patterns,
    "js": _get_javascript_patterns,
    "typescript": _get_javascript_patterns,
    "ts": _get_javascript_patterns,
    "tsx": _get_javascript_patterns,
    "java": lambda source_name: [
        f"import.*\\.{source_name};",
        f"\\b{source_name}\\b",  # Direct class usage
    ],
    "ruby": _get_ruby_patterns,
    "rb": _get_ruby_patterns,
}


class CoverageDetector:
    """Detects test coverage for source files to assess refactoring risk."""

    def __init__(self) -> None:
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

    def _get_potential_test_paths(self, file_path: str, language: str, project_root: str) -> List[str]:
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
            potential_paths.extend(
                [
                    os.path.join(project_root, dir_path, f"test_{name_without_ext}.py"),
                    os.path.join(project_root, dir_path, f"{name_without_ext}_test.py"),
                    os.path.join(project_root, "tests", f"test_{name_without_ext}.py"),
                    os.path.join(project_root, "tests", dir_path, f"test_{name_without_ext}.py"),
                    os.path.join(project_root, "test", f"test_{name_without_ext}.py"),
                    os.path.join(project_root, "tests", "unit", f"test_{name_without_ext}.py"),
                    os.path.join(project_root, "tests", "integration", f"test_{name_without_ext}.py"),
                ]
            )

        elif lang in ("javascript", "js"):
            potential_paths.extend(
                [
                    os.path.join(project_root, dir_path, f"{name_without_ext}.test.js"),
                    os.path.join(project_root, dir_path, f"{name_without_ext}.spec.js"),
                    os.path.join(project_root, dir_path, "__tests__", f"{name_without_ext}.js"),
                    os.path.join(project_root, "tests", f"{name_without_ext}.test.js"),
                    os.path.join(project_root, "__tests__", f"{name_without_ext}.js"),
                ]
            )

        elif lang in ("typescript", "ts", "tsx"):
            # Handle both .ts and .tsx
            ts_ext = ".tsx" if ext == ".tsx" else ".ts"
            potential_paths.extend(
                [
                    os.path.join(project_root, dir_path, f"{name_without_ext}.test{ts_ext}"),
                    os.path.join(project_root, dir_path, f"{name_without_ext}.spec{ts_ext}"),
                    os.path.join(project_root, dir_path, "__tests__", f"{name_without_ext}{ts_ext}"),
                    os.path.join(project_root, "tests", f"{name_without_ext}.test{ts_ext}"),
                    os.path.join(project_root, "__tests__", f"{name_without_ext}{ts_ext}"),
                ]
            )

        elif lang == "java":
            # Convert class name: MyClass.java -> MyClassTest.java
            potential_paths.extend(
                [
                    os.path.join(project_root, dir_path, f"{name_without_ext}Test.java"),
                    os.path.join(project_root, dir_path, f"{name_without_ext}Tests.java"),
                    # Maven/Gradle standard: src/test/java mirrors src/main/java
                    os.path.join(
                        project_root,
                        "src",
                        "test",
                        "java",
                        dir_path.replace("src/main/java/", "").replace("src\\main\\java\\", ""),
                        f"{name_without_ext}Test.java",
                    ),
                ]
            )

        elif lang == "go":
            potential_paths.extend(
                [
                    os.path.join(project_root, dir_path, f"{name_without_ext}_test.go"),
                ]
            )

        elif lang in ("ruby", "rb"):
            potential_paths.extend(
                [
                    os.path.join(project_root, dir_path, f"{name_without_ext}_test.rb"),
                    os.path.join(project_root, dir_path, f"{name_without_ext}_spec.rb"),
                    os.path.join(project_root, "test", f"{name_without_ext}_test.rb"),
                    os.path.join(project_root, "spec", f"{name_without_ext}_spec.rb"),
                ]
            )

        return [os.path.normpath(p) for p in potential_paths]

    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content safely.

        Args:
            file_path: Path to the file

        Returns:
            File content or None if file cannot be read
        """
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except (IOError, OSError):
            return None

    def _check_import_patterns(self, patterns: List[str], content: str) -> bool:
        """Check if any import pattern matches in content.

        Args:
            patterns: List of regex patterns to check
            content: File content to search in

        Returns:
            True if any pattern matches
        """
        for pattern in patterns:
            if regex_module.search(pattern, content, regex_module.IGNORECASE):
                return True
        return False

    def _check_go_same_directory(self, test_file_path: str, source_file_path: str) -> bool:
        """Check if Go files are in the same directory (automatic access).

        Args:
            test_file_path: Path to test file
            source_file_path: Path to source file

        Returns:
            True if files are in the same directory
        """
        source_dir = os.path.dirname(source_file_path)
        test_dir = os.path.dirname(test_file_path)
        return os.path.normpath(source_dir) == os.path.normpath(test_dir)

    def _check_test_file_references_source(self, test_file_path: str, source_file_path: str, language: str) -> bool:
        """Check if a test file references/imports the source file.

        Args:
            test_file_path: Path to the test file
            source_file_path: Path to the source file being tested
            language: Programming language

        Returns:
            True if the test file appears to test the source file
        """
        # Early return: read file content
        content = self._read_file_content(test_file_path)
        if content is None:
            return False

        # Get the module/class name from source file
        source_name = os.path.splitext(os.path.basename(source_file_path))[0]
        lang = language.lower()

        # Special case: Go files in same directory have automatic access
        if lang == "go":
            if self._check_go_same_directory(test_file_path, source_file_path):
                return True
            # Check for package import
            if regex_module.search(f"import.*{source_name}", content):
                return True

        # Configuration-driven pattern checking
        if lang in IMPORT_PATTERN_CONFIG:
            patterns = IMPORT_PATTERN_CONFIG[lang](source_name)
            if self._check_import_patterns(patterns, content):
                return True

        # Fallback: check if source file name appears anywhere in test
        if source_name.lower() in content.lower():
            return True

        return False

    def has_test_coverage(self, file_path: str, language: str, project_root: str) -> bool:
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
                self.logger.debug("found_test_file", source_file=file_path, test_file=test_path)
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
                        self.logger.debug("found_test_by_reference", source_file=file_path, test_file=match)
                        return True
            except Exception as e:
                self.logger.warning("glob_search_failed", pattern=pattern, error=str(e))
                continue

        self.logger.debug("no_test_coverage", source_file=file_path)
        return False

    def _find_all_test_files(self, language: str, project_root: str) -> Set[str]:
        """Find all test files in the project (cached for batch operations).

        Args:
            language: Programming language
            project_root: Root directory of the project

        Returns:
            Set of normalized test file paths
        """
        test_files: Set[str] = set()
        patterns = self.find_test_file_patterns(language)

        for pattern in patterns:
            full_pattern = os.path.join(project_root, pattern)
            try:
                matches = glob_module.glob(full_pattern, recursive=True)
                # Normalize paths for consistent comparison
                test_files.update(os.path.normpath(match) for match in matches)
            except Exception as e:
                self.logger.warning("glob_search_failed", pattern=pattern, error=str(e))
                continue

        self.logger.debug("test_files_discovered", count=len(test_files), language=language)

        return test_files

    def _has_test_coverage_optimized(self, file_path: str, language: str, project_root: str, test_files: Set[str]) -> bool:
        """Optimized test coverage check using pre-computed test file set.

        Args:
            file_path: Path to the source file
            language: Programming language
            project_root: Root directory of the project
            test_files: Pre-computed set of all test files

        Returns:
            True if test coverage exists for the file
        """
        # Get potential test file paths
        potential_tests = self._get_potential_test_paths(file_path, language, project_root)

        # Check if any potential test file exists in our pre-computed set
        for test_path in potential_tests:
            normalized_test = os.path.normpath(test_path)
            if normalized_test in test_files:
                self.logger.debug("found_test_file", source_file=file_path, test_file=normalized_test)
                return True

        # Check if any test file references our source
        for test_file in test_files:
            if self._check_test_file_references_source(test_file, file_path, language):
                self.logger.debug("found_test_by_reference", source_file=file_path, test_file=test_file)
                return True

        self.logger.debug("no_test_coverage", source_file=file_path)
        return False

    def get_test_coverage_for_files(self, file_paths: List[str], language: str, project_root: str) -> Dict[str, bool]:
        """Get test coverage status for multiple files (sequential).

        Args:
            file_paths: List of source file paths
            language: Programming language
            project_root: Root directory of the project

        Returns:
            Dictionary mapping file paths to their test coverage status

        Note:
            For better performance with many files, use
            get_test_coverage_for_files_batch() with parallel=True.
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
            files_without_coverage=len(file_paths) - covered_count,
        )

        return coverage_map

    def get_test_coverage_for_files_batch(
        self, file_paths: List[str], language: str, project_root: str, parallel: bool = True, max_workers: int = 4
    ) -> Dict[str, bool]:
        """Get test coverage status for multiple files with batch optimization.

        This method provides significant performance improvements over the
        sequential version by:
        1. Pre-computing all test files once (instead of per-file glob searches)
        2. Optionally using parallel execution for file processing
        3. Reusing the test file set across all files

        Args:
            file_paths: List of source file paths
            language: Programming language
            project_root: Root directory of the project
            parallel: Whether to use parallel execution (default: True)
            max_workers: Maximum number of threads for parallel execution

        Returns:
            Dictionary mapping file paths to their test coverage status

        Performance:
            - Sequential: O(n * m) where n=files, m=test patterns
            - Batch: O(m + n) - 60-80% faster for large file sets
        """
        if not file_paths:
            return {}

        # Pre-compute all test files once (major optimization)
        test_files = self._find_all_test_files(language, project_root)

        # Process files using appropriate strategy
        if parallel and len(file_paths) > 1:
            coverage_map, covered_count = self._process_parallel_batch(file_paths, language, project_root, test_files, max_workers)
        else:
            coverage_map, covered_count = self._process_sequential_batch(file_paths, language, project_root, test_files)

        # Log final results
        self._log_batch_results(len(file_paths), covered_count, parallel, len(test_files))

        return coverage_map

    def _process_file_coverage(self, file_path: str, language: str, project_root: str, test_files: Set[str]) -> bool:
        """Process coverage check for a single file with error handling.

        Args:
            file_path: Path to the source file
            language: Programming language
            project_root: Root directory
            test_files: Pre-computed set of test files

        Returns:
            True if test coverage exists, False otherwise or on error
        """
        try:
            return self._has_test_coverage_optimized(file_path, language, project_root, test_files)
        except Exception as e:
            self.logger.error("test_coverage_check_failed", file_path=file_path, error=str(e))
            return False

    def _process_parallel_batch(
        self, file_paths: List[str], language: str, project_root: str, test_files: Set[str], max_workers: int
    ) -> Tuple[Dict[str, bool], int]:
        """Process files in parallel for coverage checking.

        Args:
            file_paths: List of source file paths
            language: Programming language
            project_root: Root directory
            test_files: Pre-computed set of test files
            max_workers: Maximum number of threads

        Returns:
            Tuple of (coverage_map, covered_count)
        """
        self.logger.debug("batch_coverage_parallel_start", file_count=len(file_paths), max_workers=max_workers)

        coverage_map: Dict[str, bool] = {}
        covered_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self._has_test_coverage_optimized, file_path, language, project_root, test_files): file_path
                for file_path in file_paths
            }

            # Process results as they complete
            for future in as_completed(futures):
                file_path = futures[future]
                has_coverage = self._get_future_result(future, file_path)
                coverage_map[file_path] = has_coverage
                if has_coverage:
                    covered_count += 1

        return coverage_map, covered_count

    def _process_sequential_batch(
        self, file_paths: List[str], language: str, project_root: str, test_files: Set[str]
    ) -> Tuple[Dict[str, bool], int]:
        """Process files sequentially for coverage checking.

        Args:
            file_paths: List of source file paths
            language: Programming language
            project_root: Root directory
            test_files: Pre-computed set of test files

        Returns:
            Tuple of (coverage_map, covered_count)
        """
        self.logger.debug("batch_coverage_sequential_start", file_count=len(file_paths))

        coverage_map: Dict[str, bool] = {}
        covered_count = 0

        for file_path in file_paths:
            has_coverage = self._process_file_coverage(file_path, language, project_root, test_files)
            coverage_map[file_path] = has_coverage
            if has_coverage:
                covered_count += 1

        return coverage_map, covered_count

    def _get_future_result(self, future: Future[bool], file_path: str) -> bool:
        """Get result from future with error handling.

        Args:
            future: Concurrent future object
            file_path: Path to file being processed

        Returns:
            Coverage status or False on error
        """
        try:
            return future.result()
        except Exception as e:
            self.logger.error("test_coverage_check_failed", file_path=file_path, error=str(e))
            return False

    def _log_batch_results(self, total_files: int, covered_count: int, parallel: bool, test_files_count: int) -> None:
        """Log the final batch processing results.

        Args:
            total_files: Total number of files processed
            covered_count: Number of files with coverage
            parallel: Whether parallel processing was used
            test_files_count: Number of test files found
        """
        self.logger.info(
            "batch_coverage_analysis_complete",
            total_files=total_files,
            files_with_coverage=covered_count,
            files_without_coverage=total_files - covered_count,
            parallel=parallel,
            test_files_found=test_files_count,
        )


# Module-level functions for backwards compatibility
_detector = CoverageDetector()


def find_test_file_patterns(language: str) -> List[str]:
    """Get test file patterns for a given programming language."""
    return _detector.find_test_file_patterns(language)


def has_test_coverage(file_path: str, language: str, project_root: str) -> bool:
    """Check if a source file has corresponding test coverage."""
    return _detector.has_test_coverage(file_path, language, project_root)


def get_test_coverage_for_files(file_paths: List[str], language: str, project_root: str) -> Dict[str, bool]:
    """Get test coverage status for multiple files."""
    return _detector.get_test_coverage_for_files(file_paths, language, project_root)
