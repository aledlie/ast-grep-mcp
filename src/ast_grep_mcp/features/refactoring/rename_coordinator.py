"""Coordinator for multi-file symbol renaming operations.

Handles:
- Planning file modification order
- Atomic updates across files
- Import/export updates
- Rollback on failure
"""

import os
from typing import Dict, List, Optional, Set
from ast_grep_mcp.core.logging import get_logger

from ...models.refactoring import (
    SymbolReference,
    RenameSymbolResult,
    ScopeInfo,
)
from ...features.rewrite.backup import create_backup, restore_backup
from .renamer import SymbolRenamer

logger = get_logger(__name__)


class RenameCoordinator:
    """Coordinates multi-file symbol renaming."""

    def __init__(self, language: str) -> None:
        """Initialize coordinator.

        Args:
            language: Programming language
        """
        self.language = language
        self.renamer = SymbolRenamer(language)

    def rename_symbol(
        self,
        project_folder: str,
        old_name: str,
        new_name: str,
        scope: str = "project",
        file_filter: Optional[str] = None,
        dry_run: bool = True,
    ) -> RenameSymbolResult:
        """Rename a symbol across the project.

        Args:
            project_folder: Project root folder
            old_name: Current symbol name
            new_name: New symbol name
            scope: Scope to rename in ('project', 'file', 'function')
            file_filter: Optional glob pattern to filter files
            dry_run: If True, only preview changes

        Returns:
            RenameSymbolResult with success status and details
        """
        logger.info(
            "rename_symbol_started",
            old_name=old_name,
            new_name=new_name,
            scope=scope,
            dry_run=dry_run,
        )

        try:
            # Step 1: Find all references
            references = self.renamer.find_symbol_references(
                project_folder=project_folder,
                symbol_name=old_name,
                file_filter=file_filter,
            )

            if not references:
                return RenameSymbolResult(
                    success=False,
                    old_name=old_name,
                    new_name=new_name,
                    error=f"No references found for symbol '{old_name}'",
                )

            # Step 2: Build scope trees for all affected files
            affected_files = list(set(ref.file_path for ref in references))
            scope_trees: Dict[str, List[ScopeInfo]] = {}

            for file_path in affected_files:
                scope_trees[file_path] = self.renamer.build_scope_tree(file_path)

            # Step 3: Check for naming conflicts
            conflicts = self.renamer.check_naming_conflicts(
                references=references,
                new_name=new_name,
                scopes=scope_trees,
            )

            if conflicts:
                return RenameSymbolResult(
                    success=False,
                    old_name=old_name,
                    new_name=new_name,
                    conflicts=conflicts,
                    error=f"Naming conflicts detected: {len(conflicts)} conflicts",
                )

            # Step 4: Generate diff preview
            diff_preview = self._generate_diff_preview(
                references=references,
                old_name=old_name,
                new_name=new_name,
            )

            # Step 5: Apply changes if not dry-run
            backup_id = None
            files_modified: List[str] = []

            if not dry_run:
                backup_id, files_modified = self._apply_rename(
                    project_folder=project_folder,
                    references=references,
                    old_name=old_name,
                    new_name=new_name,
                )

            return RenameSymbolResult(
                success=True,
                old_name=old_name,
                new_name=new_name,
                references_found=len(references),
                references_updated=len(references) if not dry_run else 0,
                files_modified=files_modified,
                diff_preview=diff_preview,
                backup_id=backup_id,
            )

        except Exception as e:
            logger.error("rename_symbol_failed", error=str(e))
            return RenameSymbolResult(
                success=False,
                old_name=old_name,
                new_name=new_name,
                error=str(e),
            )

    def _generate_diff_preview(
        self,
        references: List[SymbolReference],
        old_name: str,
        new_name: str,
    ) -> str:
        """Generate unified diff preview of rename operation.

        Args:
            references: List of references to rename
            old_name: Old symbol name
            new_name: New symbol name

        Returns:
            Unified diff string
        """
        lines = []

        # Group by file
        refs_by_file: Dict[str, List[SymbolReference]] = {}
        for ref in references:
            if ref.file_path not in refs_by_file:
                refs_by_file[ref.file_path] = []
            refs_by_file[ref.file_path].append(ref)

        # Generate diff for each file
        for file_path, file_refs in sorted(refs_by_file.items()):
            lines.append(f"--- {file_path}")
            lines.append(f"+++ {file_path}")
            lines.append("")

            for ref in sorted(file_refs, key=lambda r: r.line):
                # Show context with highlight
                old_line = ref.context
                new_line = old_line.replace(old_name, new_name)

                lines.append(f"  Line {ref.line}:")
                lines.append(f"- {old_line}")
                lines.append(f"+ {new_line}")
                lines.append("")

        return '\n'.join(lines)

    def _apply_rename(
        self,
        project_folder: str,
        references: List[SymbolReference],
        old_name: str,
        new_name: str,
    ) -> tuple[str, List[str]]:
        """Apply rename operation to files.

        Args:
            project_folder: Project root
            references: References to rename
            old_name: Old symbol name
            new_name: New symbol name

        Returns:
            Tuple of (backup_id, files_modified)
        """
        # Group references by file
        refs_by_file: Dict[str, List[SymbolReference]] = {}
        for ref in references:
            if ref.file_path not in refs_by_file:
                refs_by_file[ref.file_path] = []
            refs_by_file[ref.file_path].append(ref)

        files_to_modify = list(refs_by_file.keys())

        # Create backup
        backup_id = create_backup(files_to_modify, project_folder)

        try:
            files_modified = []

            # Modify each file
            for file_path, file_refs in refs_by_file.items():
                self._rename_in_file(
                    file_path=file_path,
                    references=file_refs,
                    old_name=old_name,
                    new_name=new_name,
                )
                files_modified.append(file_path)

            logger.info(
                "rename_applied",
                backup_id=backup_id,
                files_modified=len(files_modified),
            )

            return backup_id, files_modified

        except Exception as e:
            # Rollback on error
            logger.error("rename_failed_rolling_back", error=str(e))
            restore_backup(backup_id, project_folder)
            raise RuntimeError(f"Rename failed and was rolled back: {e}")

    def _rename_in_file(
        self,
        file_path: str,
        references: List[SymbolReference],
        old_name: str,
        new_name: str,
    ) -> None:
        """Rename symbol in a single file.

        Args:
            file_path: File to modify
            references: References in this file
            old_name: Old symbol name
            new_name: New symbol name
        """
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Sort references by line (reverse order to maintain line numbers)
        sorted_refs = sorted(references, key=lambda r: r.line, reverse=True)

        # Replace each reference
        for ref in sorted_refs:
            if ref.line <= len(lines):
                line_idx = ref.line - 1
                line = lines[line_idx]

                # Use word boundary replacement to avoid partial matches
                import re
                pattern = r'\b' + re.escape(old_name) + r'\b'
                new_line = re.sub(pattern, new_name, line)

                lines[line_idx] = new_line

        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        logger.debug(
            "file_renamed",
            file_path=file_path,
            references=len(references),
        )
