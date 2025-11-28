"""File discovery and filtering for complexity analysis.

This module handles finding files to analyze based on include/exclude
patterns and language-specific file extensions.
"""
import glob
from pathlib import Path
from typing import List, Set

from ...core.logging import get_logger


class ComplexityFileFinder:
    """Finds and filters files for complexity analysis."""

    def __init__(self) -> None:
        """Initialize the file finder."""
        self.logger = get_logger("complexity.file_finder")

    def find_files(
        self,
        project_folder: str,
        language: str,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> List[str]:
        """Find files to analyze based on patterns and language.

        Args:
            project_folder: Project root folder
            language: Programming language
            include_patterns: Glob patterns for files to include
            exclude_patterns: Glob patterns for files to exclude

        Returns:
            List of file paths to analyze
        """
        self.logger.info(
            "find_files_start",
            project_folder=project_folder,
            language=language,
            include_count=len(include_patterns),
            exclude_count=len(exclude_patterns)
        )

        # Validate project folder
        project_path = Path(project_folder)
        if not project_path.exists():
            raise ValueError(f"Project folder does not exist: {project_folder}")

        # Get language-specific file extensions
        extensions = self._get_language_extensions(language)

        # Find all matching files
        all_files = self._find_matching_files(
            project_path,
            include_patterns,
            extensions
        )

        # Filter excluded files
        files_to_analyze = self._filter_excluded_files(
            all_files,
            exclude_patterns
        )

        self.logger.info(
            "find_files_complete",
            total_found=len(all_files),
            after_exclusion=len(files_to_analyze)
        )

        return files_to_analyze

    def _get_language_extensions(self, language: str) -> List[str]:
        """Get file extensions for a programming language.

        Args:
            language: Programming language

        Returns:
            List of file extensions (e.g., ['.py', '.pyi'])
        """
        lang_extensions = {
            "python": [".py"],
            "typescript": [".ts", ".tsx"],
            "javascript": [".js", ".jsx"],
            "java": [".java"]
        }
        return lang_extensions.get(language.lower(), [".py"])

    def _find_matching_files(
        self,
        project_path: Path,
        include_patterns: List[str],
        extensions: List[str]
    ) -> Set[str]:
        """Find all files matching include patterns and extensions.

        Args:
            project_path: Project root path
            include_patterns: Glob patterns to include
            extensions: File extensions to match

        Returns:
            Set of matching file paths
        """
        all_files: Set[str] = set()

        for pattern in include_patterns:
            for ext in extensions:
                glob_pattern = str(project_path / pattern)

                # Adjust pattern to match extension
                if not glob_pattern.endswith(ext):
                    if glob_pattern.endswith("*"):
                        glob_pattern = glob_pattern[:-1] + f"*{ext}"
                    else:
                        glob_pattern = glob_pattern + f"/**/*{ext}"

                # Find files
                for file_path in glob.glob(glob_pattern, recursive=True):
                    all_files.add(file_path)

        return all_files

    def _filter_excluded_files(
        self,
        all_files: Set[str],
        exclude_patterns: List[str]
    ) -> List[str]:
        """Filter out files matching exclusion patterns.

        Args:
            all_files: All files found
            exclude_patterns: Glob patterns to exclude

        Returns:
            List of files after applying exclusions
        """
        files_to_analyze: List[str] = []

        for file_path in all_files:
            excluded = False

            for exclude_pattern in exclude_patterns:
                # Parse exclude pattern into path components
                pattern_parts = exclude_pattern.replace("**", "").replace("*", "").split("/")

                # Check if any pattern part is in the file path
                if any(part in file_path for part in pattern_parts if part):
                    excluded = True
                    break

            if not excluded:
                files_to_analyze.append(file_path)

        return files_to_analyze
