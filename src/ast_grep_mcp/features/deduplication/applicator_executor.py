"""Code execution logic for deduplication refactoring.

This module handles the actual code modifications during
deduplication refactoring operations.
"""
import os
from pathlib import Path
from typing import Any, Dict, List

from ...core.logging import get_logger


class RefactoringExecutor:
    """Executes the actual code modifications for refactoring."""

    def __init__(self) -> None:
        """Initialize the refactoring executor."""
        self.logger = get_logger("deduplication.executor")

    def apply_changes(
        self,
        orchestration_plan: Dict[str, Any],
        replacements: Dict[str, Dict[str, Any]],
        language: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Apply refactoring changes to files.

        Args:
            orchestration_plan: The orchestration plan with file operations
            replacements: Dictionary of file replacements
            language: Programming language
            dry_run: If True, preview changes without applying

        Returns:
            Dictionary with:
                - modified_files: List of modified file paths
                - failed_files: List of failed operations
                - dry_run: Whether this was a dry run
        """
        self.logger.info(
            "apply_changes_start",
            dry_run=dry_run,
            create_count=len(orchestration_plan.get("create_files", [])),
            update_count=len(orchestration_plan.get("update_files", []))
        )

        modified_files: List[str] = []
        failed_files: List[Dict[str, Any]] = []

        if dry_run:
            # Preview mode - just log what would happen
            self.logger.info("dry_run_mode", message="Preview only, no changes applied")
            return {
                "modified_files": [],
                "failed_files": [],
                "dry_run": True,
                "preview": self._generate_preview(orchestration_plan, replacements)
            }

        try:
            # Step 1: Create new files for extracted functions
            create_result = self._create_files(
                orchestration_plan.get("create_files", [])
            )
            modified_files.extend(create_result["created"])
            failed_files.extend(create_result["failed"])

            # Step 2: Update duplicate location files
            update_result = self._update_files(
                orchestration_plan.get("update_files", []),
                replacements,
                orchestration_plan.get("import_additions", {}),
                language
            )
            modified_files.extend(update_result["updated"])
            failed_files.extend(update_result["failed"])

            self.logger.info(
                "apply_changes_complete",
                modified_count=len(modified_files),
                failed_count=len(failed_files)
            )

        except Exception as e:
            self.logger.error(
                "apply_changes_failed",
                error=str(e),
                modified_count=len(modified_files),
                failed_count=len(failed_files)
            )
            raise

        return {
            "modified_files": modified_files,
            "failed_files": failed_files,
            "dry_run": False
        }

    def _create_files(
        self,
        create_file_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create new files for extracted functions.

        Args:
            create_file_list: List of file creation operations

        Returns:
            Dictionary with created and failed file lists
        """
        created: List[str] = []
        failed: List[Dict[str, Any]] = []

        for create_info in create_file_list:
            target_path = create_info.get("path", "")
            content = create_info.get("content", "")

            if not target_path or not content:
                continue

            try:
                # Create parent directory if needed
                target_dir = os.path.dirname(target_path)
                if target_dir and not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)

                # Determine write mode (append or write)
                mode = 'a' if os.path.exists(target_path) and create_info.get("append", False) else 'w'
                prefix = "\n\n" if mode == 'a' else ""

                # Write file
                with open(target_path, mode) as f:
                    f.write(prefix + content)

                created.append(target_path)
                self.logger.info("file_created", file=target_path, mode=mode)

            except Exception as e:
                failed.append({
                    "file": target_path,
                    "operation": "create",
                    "error": str(e)
                })
                self.logger.error(
                    "file_creation_failed",
                    file=target_path,
                    error=str(e)
                )
                raise  # Fail fast for atomicity

        return {"created": created, "failed": failed}

    def _update_files(
        self,
        update_file_list: List[Dict[str, Any]],
        replacements: Dict[str, Dict[str, Any]],
        import_additions: Dict[str, Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        """Update duplicate location files.

        Args:
            update_file_list: List of file update operations
            replacements: Dictionary of file replacements
            import_additions: Dictionary of import additions per file
            language: Programming language

        Returns:
            Dictionary with updated and failed file lists
        """
        updated: List[str] = []
        failed: List[Dict[str, Any]] = []

        for update_info in update_file_list:
            file_path = update_info.get("path", "")

            if not file_path or not os.path.exists(file_path):
                continue

            try:
                # Read current content
                with open(file_path, 'r') as f:
                    current_content = f.read()

                new_content = current_content

                # Apply replacement
                replacement = replacements.get(file_path, {})
                if replacement.get("new_content"):
                    new_content = replacement["new_content"]

                # Add import statement
                import_info = import_additions.get(file_path)
                if import_info:
                    new_content = self._add_import_to_content(
                        content=new_content,
                        import_statement=import_info.get("import_statement", ""),
                        language=language
                    )

                # Write updated content
                with open(file_path, 'w') as f:
                    f.write(new_content)

                updated.append(file_path)
                self.logger.info("file_updated", file=file_path)

            except Exception as e:
                failed.append({
                    "file": file_path,
                    "operation": "update",
                    "error": str(e)
                })
                self.logger.error(
                    "file_update_failed",
                    file=file_path,
                    error=str(e)
                )
                raise  # Fail fast for atomicity

        return {"updated": updated, "failed": failed}

    def _find_python_import_location(self, lines: List[str]) -> int:
        """Find where to insert an import in Python code.

        Args:
            lines: Code lines

        Returns:
            Line index to insert import
        """
        # Find last import statement
        last_import_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                last_import_idx = i
            elif stripped and not stripped.startswith("#") and last_import_idx >= 0:
                break

        if last_import_idx >= 0:
            return last_import_idx + 1

        # No imports found, add at the top after any shebang/encoding
        insert_idx = 0
        for i, line in enumerate(lines):
            if not line.strip() or line.startswith("#"):
                insert_idx = i + 1
            else:
                break
        return insert_idx

    def _find_javascript_import_location(self, lines: List[str]) -> int:
        """Find where to insert an import in JavaScript/TypeScript code.

        Args:
            lines: Code lines

        Returns:
            Line index to insert import
        """
        last_import_idx = -1
        for i, line in enumerate(lines):
            if "import " in line or "require(" in line:
                last_import_idx = i

        return last_import_idx + 1 if last_import_idx >= 0 else 0

    def _find_java_import_location(self, lines: List[str]) -> tuple[int, bool]:
        """Find where to insert an import in Java code.

        Args:
            lines: Code lines

        Returns:
            Tuple of (insert_index, needs_blank_before)
        """
        package_idx = -1
        last_import_idx = -1

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("package "):
                package_idx = i
            elif stripped.startswith("import "):
                last_import_idx = i

        if last_import_idx >= 0:
            return (last_import_idx + 1, False)
        elif package_idx >= 0:
            return (package_idx + 1, True)
        else:
            return (0, False)

    def _insert_import_python(self, lines: List[str], import_statement: str) -> List[str]:
        """Insert import in Python code.

        Args:
            lines: Code lines
            import_statement: Import to add

        Returns:
            Modified lines
        """
        insert_idx = self._find_python_import_location(lines)
        lines.insert(insert_idx, import_statement)

        # Add blank line if inserting at top without existing imports
        if insert_idx > 0 and not any(
            l.strip().startswith(("import ", "from ")) for l in lines[:insert_idx]
        ):
            lines.insert(insert_idx, "")

        return lines

    def _insert_import_javascript(self, lines: List[str], import_statement: str) -> List[str]:
        """Insert import in JavaScript/TypeScript code.

        Args:
            lines: Code lines
            import_statement: Import to add

        Returns:
            Modified lines
        """
        insert_idx = self._find_javascript_import_location(lines)
        lines.insert(insert_idx, import_statement)

        # Add blank line after if inserting at top
        if insert_idx == 0:
            lines.insert(1, "")

        return lines

    def _insert_import_java(self, lines: List[str], import_statement: str) -> List[str]:
        """Insert import in Java code.

        Args:
            lines: Code lines
            import_statement: Import to add

        Returns:
            Modified lines
        """
        insert_idx, needs_blank = self._find_java_import_location(lines)

        if needs_blank:
            lines.insert(insert_idx, "")
            lines.insert(insert_idx + 1, import_statement)
        else:
            lines.insert(insert_idx, import_statement)
            if insert_idx == 0:
                lines.insert(1, "")

        return lines

    def _add_import_to_content(
        self,
        content: str,
        import_statement: str,
        language: str
    ) -> str:
        """Add an import statement to file content.

        Args:
            content: Current file content
            import_statement: Import statement to add
            language: Programming language

        Returns:
            Updated content with import statement
        """
        if not import_statement:
            return content

        # Check if import already exists
        if import_statement.strip() in content:
            return content

        lines = content.split('\n')
        lang = language.lower()

        # Language-specific import insertion
        if lang == "python":
            lines = self._insert_import_python(lines, import_statement)
        elif lang in ("javascript", "typescript", "jsx", "tsx"):
            lines = self._insert_import_javascript(lines, import_statement)
        elif lang == "java":
            lines = self._insert_import_java(lines, import_statement)
        # For other languages, just add at the top
        else:
            lines.insert(0, import_statement)
            lines.insert(1, "")

        return '\n'.join(lines)

    def _generate_preview(
        self,
        orchestration_plan: Dict[str, Any],
        replacements: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate preview of changes for dry run.

        Args:
            orchestration_plan: The orchestration plan
            replacements: Dictionary of file replacements

        Returns:
            Dictionary with preview information
        """
        preview: Dict[str, Any] = {
            "files_to_create": [],
            "files_to_update": []
        }

        # Preview file creations
        for create_info in orchestration_plan.get("create_files", []):
            target_path = create_info.get("path", "")
            if target_path:
                preview["files_to_create"].append({
                    "path": target_path,
                    "mode": "append" if create_info.get("append", False) else "write",
                    "content_lines": len(create_info.get("content", "").split('\n'))
                })

        # Preview file updates
        for update_info in orchestration_plan.get("update_files", []):
            file_path = update_info.get("path", "")
            if file_path:
                replacement = replacements.get(file_path, {})
                preview["files_to_update"].append({
                    "path": file_path,
                    "has_replacement": bool(replacement.get("new_content")),
                    "has_import_addition": file_path in orchestration_plan.get("import_additions", {})
                })

        return preview
