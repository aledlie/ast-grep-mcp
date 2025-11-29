"""Symbol renaming logic with scope awareness.

This module handles safe symbol renaming across files:
- Finding all references to a symbol
- Building scope trees
- Handling symbol shadowing
- Updating imports/exports
- Detecting conflicts
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from ast_grep_mcp.core.logging import get_logger

from ...models.refactoring import (
    SymbolReference,
    ScopeInfo,
    RenameSymbolResult,
)
from ...core.executor import run_ast_grep
from ...features.rewrite.backup import create_backup, restore_backup

logger = get_logger(__name__)


class SymbolRenamer:
    """Handles symbol renaming operations."""

    def __init__(self, language: str) -> None:
        """Initialize renamer for specific language.

        Args:
            language: Programming language (python, typescript, javascript, java)
        """
        self.language = language

    def find_symbol_references(
        self,
        project_folder: str,
        symbol_name: str,
        file_filter: Optional[str] = None,
    ) -> List[SymbolReference]:
        """Find all references to a symbol in the project.

        Args:
            project_folder: Project root folder
            symbol_name: Symbol to find references for
            file_filter: Optional glob pattern to filter files

        Returns:
            List of SymbolReference objects
        """
        logger.info(
            "finding_symbol_references",
            symbol_name=symbol_name,
            language=self.language,
        )

        references: List[SymbolReference] = []

        # Use ast-grep to find all occurrences
        pattern = self._get_symbol_pattern(symbol_name)

        try:
            # Run ast-grep to find matches
            result = run_ast_grep(
                command="run",
                args=[
                    "--pattern", pattern,
                    "--json",
                    project_folder,
                ],
            )

            # Parse results
            if result.returncode == 0 and result.stdout:
                import json
                matches = json.loads(result.stdout)

                for match in matches:
                    # ast-grep JSON format: {"file": "path", "range": {"start": {"line": 0, "column": 4}}, "lines": "context"}
                    # Note: ast-grep returns absolute paths and 0-indexed line numbers
                    file_path = match.get("file", "")

                    # Apply file filter if provided
                    if file_filter and not self._matches_filter(file_path, file_filter):
                        continue

                    # Extract line and column from nested range object
                    range_info = match.get("range", {})
                    start_info = range_info.get("start", {})
                    line = start_info.get("line", 0) + 1  # Convert from 0-indexed to 1-indexed
                    column = start_info.get("column", 0)

                    # Create reference
                    # ast-grep returns absolute paths, so use directly without joining
                    ref = SymbolReference(
                        file_path=file_path,
                        line=line,
                        column=column,
                        context=match.get("lines", ""),
                        scope="",  # Will be determined by scope analysis
                    )

                    # Determine if it's a definition, import, or regular reference
                    self._classify_reference(ref)

                    references.append(ref)

        except Exception as e:
            logger.error("find_symbol_references_failed", error=str(e))

        logger.info(
            "symbol_references_found",
            symbol_name=symbol_name,
            count=len(references),
        )

        return references

    def _get_symbol_pattern(self, symbol_name: str) -> str:
        """Get ast-grep pattern for finding symbol references.

        Args:
            symbol_name: Symbol name to search for

        Returns:
            ast-grep pattern string
        """
        if self.language == "python":
            # Match identifier usage (not in strings)
            return f"{symbol_name}"
        elif self.language in ("typescript", "javascript"):
            return f"{symbol_name}"
        elif self.language == "java":
            return f"{symbol_name}"

        return symbol_name

    def _matches_filter(self, file_path: str, file_filter: str) -> bool:
        """Check if file path matches filter pattern.

        Args:
            file_path: File path to check (can be absolute or relative)
            file_filter: Glob pattern (e.g., "*.py", "utils.py", "**/test_*.py")

        Returns:
            True if matches
        """
        from fnmatch import fnmatch
        import os

        # Extract basename for simple filters like "utils.py"
        basename = os.path.basename(file_path)

        # Try matching against basename first (common case)
        if fnmatch(basename, file_filter):
            return True

        # Also try matching against full path for patterns like "**/test_*.py"
        return fnmatch(file_path, file_filter)

    def _classify_reference(self, ref: SymbolReference) -> None:
        """Classify a reference as definition, import, export, or usage.

        Args:
            ref: SymbolReference to classify (modified in place)
        """
        context = ref.context.strip()

        # Use language-specific classifier
        classifier = self._get_language_classifier()
        if classifier:
            classifier(ref, context)

    def _get_language_classifier(self):
        """Get the appropriate classifier function for the current language.

        Returns:
            Classifier function or None if language not supported
        """
        classifiers = {
            "python": self._classify_python_reference,
            "typescript": self._classify_javascript_reference,
            "javascript": self._classify_javascript_reference,
        }
        return classifiers.get(self.language)

    def _classify_python_reference(self, ref: SymbolReference, context: str) -> None:
        """Classify a Python reference.

        Args:
            ref: SymbolReference to classify (modified in place)
            context: The context string (stripped)
        """
        # Check for definition
        if self._is_python_definition(context):
            ref.is_definition = True

        # Check for import
        if "import" in context:
            ref.is_import = True
            self._extract_python_import_source(ref, context)

    def _is_python_definition(self, context: str) -> bool:
        """Check if context indicates a Python definition.

        Args:
            context: The context string

        Returns:
            True if this is a definition
        """
        return context.startswith("def ") or context.startswith("class ")

    def _extract_python_import_source(self, ref: SymbolReference, context: str) -> None:
        """Extract import source from Python import statement.

        Args:
            ref: SymbolReference to update
            context: The context string containing import
        """
        if "from" not in context:
            return

        # from module import symbol
        match = re.search(r'from\s+([\w.]+)', context)
        if match:
            ref.import_source = match.group(1)

    def _classify_javascript_reference(self, ref: SymbolReference, context: str) -> None:
        """Classify a JavaScript/TypeScript reference.

        Args:
            ref: SymbolReference to classify (modified in place)
            context: The context string (stripped)
        """
        # Check for definition
        if self._is_javascript_definition(context):
            ref.is_definition = True

        # Check for import
        if "import" in context:
            ref.is_import = True
            self._extract_javascript_import_source(ref, context)

        # Check for export
        if "export" in context:
            ref.is_export = True

    def _is_javascript_definition(self, context: str) -> bool:
        """Check if context indicates a JavaScript/TypeScript definition.

        Args:
            context: The context string

        Returns:
            True if this is a definition
        """
        return bool(re.search(r'\b(function|class|const|let|var)\s+', context))

    def _extract_javascript_import_source(self, ref: SymbolReference, context: str) -> None:
        """Extract import source from JavaScript/TypeScript import statement.

        Args:
            ref: SymbolReference to update
            context: The context string containing import
        """
        match = re.search(r'from\s+["\']([^"\']+)["\']', context)
        if match:
            ref.import_source = match.group(1)

    def build_scope_tree(
        self,
        file_path: str,
    ) -> List[ScopeInfo]:
        """Build scope tree for a file.

        Args:
            file_path: Path to file

        Returns:
            List of ScopeInfo objects representing scopes in file
        """
        scopes: List[ScopeInfo] = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            if self.language == "python":
                scopes = self._build_python_scope_tree(lines)
            elif self.language in ("typescript", "javascript"):
                scopes = self._build_js_scope_tree(lines)

        except Exception as e:
            logger.error("build_scope_tree_failed", error=str(e), file_path=file_path)

        return scopes

    def _build_python_scope_tree(self, lines: List[str]) -> List[ScopeInfo]:
        """Build scope tree for Python file.

        Args:
            lines: File lines

        Returns:
            List of ScopeInfo objects
        """
        scopes: List[ScopeInfo] = []

        # Module scope
        module_scope = ScopeInfo(
            scope_type="module",
            scope_name="<module>",
            start_line=0,
            end_line=len(lines),
        )
        scopes.append(module_scope)

        # Find function and class definitions
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Function definition
            if stripped.startswith("def "):
                match = re.match(r'def\s+(\w+)\s*\(', stripped)
                if match:
                    func_name = match.group(1)
                    # Find end of function (next def/class at same or lower indentation)
                    indent = len(line) - len(line.lstrip())
                    end_line = self._find_scope_end(lines, i, indent)

                    scope = ScopeInfo(
                        scope_type="function",
                        scope_name=func_name,
                        start_line=i,
                        end_line=end_line,
                        parent_scope="<module>",
                    )
                    scopes.append(scope)

            # Class definition
            elif stripped.startswith("class "):
                match = re.match(r'class\s+(\w+)', stripped)
                if match:
                    class_name = match.group(1)
                    indent = len(line) - len(line.lstrip())
                    end_line = self._find_scope_end(lines, i, indent)

                    scope = ScopeInfo(
                        scope_type="class",
                        scope_name=class_name,
                        start_line=i,
                        end_line=end_line,
                        parent_scope="<module>",
                    )
                    scopes.append(scope)

        return scopes

    def _build_js_scope_tree(self, lines: List[str]) -> List[ScopeInfo]:
        """Build scope tree for JavaScript/TypeScript file.

        Args:
            lines: File lines

        Returns:
            List of ScopeInfo objects
        """
        scopes: List[ScopeInfo] = []

        # Module scope
        module_scope = ScopeInfo(
            scope_type="module",
            scope_name="<module>",
            start_line=0,
            end_line=len(lines),
        )
        scopes.append(module_scope)

        # Find function and class definitions
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Function declaration
            match = re.match(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', stripped)
            if match:
                func_name = match.group(1)
                end_line = self._find_js_scope_end(lines, i)

                scope = ScopeInfo(
                    scope_type="function",
                    scope_name=func_name,
                    start_line=i,
                    end_line=end_line,
                    parent_scope="<module>",
                )
                scopes.append(scope)

            # Class declaration
            match = re.match(r'(?:export\s+)?class\s+(\w+)', stripped)
            if match:
                class_name = match.group(1)
                end_line = self._find_js_scope_end(lines, i)

                scope = ScopeInfo(
                    scope_type="class",
                    scope_name=class_name,
                    start_line=i,
                    end_line=end_line,
                    parent_scope="<module>",
                )
                scopes.append(scope)

        return scopes

    def _find_scope_end(self, lines: List[str], start_line: int, base_indent: int) -> int:
        """Find end of Python scope based on indentation.

        Args:
            lines: File lines
            start_line: Starting line (1-indexed)
            base_indent: Base indentation level

        Returns:
            End line number (1-indexed)
        """
        for i in range(start_line, len(lines)):
            line = lines[i]
            if not line.strip():  # Skip empty lines
                continue

            indent = len(line) - len(line.lstrip())
            if indent <= base_indent and line.strip():
                return i

        return len(lines)

    def _find_js_scope_end(self, lines: List[str], start_line: int) -> int:
        """Find end of JavaScript/TypeScript scope based on braces.

        Args:
            lines: File lines
            start_line: Starting line (1-indexed)

        Returns:
            End line number (1-indexed)
        """
        brace_count = 0
        started = False

        for i in range(start_line - 1, len(lines)):
            line = lines[i]

            for char in line:
                if char == '{':
                    brace_count += 1
                    started = True
                elif char == '}':
                    brace_count -= 1

                if started and brace_count == 0:
                    return i + 1

        return len(lines)

    def check_naming_conflicts(
        self,
        references: List[SymbolReference],
        new_name: str,
        scopes: Dict[str, List[ScopeInfo]],
    ) -> List[str]:
        """Check for naming conflicts if symbol is renamed.

        Args:
            references: List of references to check
            new_name: New symbol name
            scopes: Dict mapping file paths to scope trees

        Returns:
            List of conflict descriptions (empty if no conflicts)
        """
        conflicts: List[str] = []

        # Group references by file
        refs_by_file: Dict[str, List[SymbolReference]] = {}
        for ref in references:
            if ref.file_path not in refs_by_file:
                refs_by_file[ref.file_path] = []
            refs_by_file[ref.file_path].append(ref)

        # Check each file for conflicts
        for file_path, file_refs in refs_by_file.items():
            file_scopes = scopes.get(file_path, [])

            for ref in file_refs:
                # Find the scope this reference is in
                ref_scope = self._find_scope_for_line(file_scopes, ref.line)

                if ref_scope and new_name in ref_scope.defined_symbols:
                    conflicts.append(
                        f"{file_path}:{ref.line} - '{new_name}' already defined in scope '{ref_scope.scope_name}'"
                    )

        return conflicts

    def _find_scope_for_line(
        self,
        scopes: List[ScopeInfo],
        line: int,
    ) -> Optional[ScopeInfo]:
        """Find the innermost scope containing a line.

        Args:
            scopes: List of scopes
            line: Line number

        Returns:
            ScopeInfo or None
        """
        # Find all scopes containing the line
        containing_scopes = [
            s for s in scopes
            if s.start_line <= line <= s.end_line
        ]

        if not containing_scopes:
            return None

        # Return the innermost scope (smallest range)
        return min(containing_scopes, key=lambda s: s.end_line - s.start_line)
