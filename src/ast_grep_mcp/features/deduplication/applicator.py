"""Apply deduplication refactoring with validation and rollback."""

import os
from typing import Any, Dict, List, Optional

from ...core.logging import get_logger
from .applicator_backup import DeduplicationBackupManager
from .applicator_executor import RefactoringExecutor
from .applicator_post_validator import RefactoringPostValidator
from .applicator_validator import RefactoringPlanValidator
from .generator import CodeGenerator

__all__ = [
    'DeduplicationApplicator',
    '_plan_file_modification_order',
    '_add_import_to_content',
    '_generate_import_for_extracted_function'
]


class DeduplicationApplicator:
    """Applies deduplication refactoring with backup and validation."""

    def __init__(self):
        """Initialize the deduplication applicator."""
        self.logger = get_logger("deduplication.applicator")
        self.code_generator = CodeGenerator()
        self.validator = RefactoringPlanValidator()
        self.executor = RefactoringExecutor()
        self.post_validator = RefactoringPostValidator()

    def apply_deduplication(
        self,
        project_folder: str,
        group_id: int,
        refactoring_plan: Dict[str, Any],
        dry_run: bool = True,
        backup: bool = True,
        extract_to_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply automated deduplication refactoring with comprehensive syntax validation.

        Phase 3.5 VALIDATION PIPELINE:
        1. PRE-VALIDATION: Validate all generated code before applying
        2. APPLICATION: Create backup and apply changes
        3. POST-VALIDATION: Validate modified files
        4. AUTO-ROLLBACK: Restore from backup if validation fails

        Args:
            project_folder: The absolute path to the project folder
            group_id: The duplication group ID from find_duplication results
            refactoring_plan: The refactoring plan with generated_code, files_affected, strategy, language
            dry_run: Preview changes without applying (default: true for safety)
            backup: Create backup before applying changes (default: true)
            extract_to_file: Where to place extracted function (auto-detect if None)

        Returns:
            Dict with:
            - status: "preview" | "success" | "failed" | "rolled_back"
            - validation: Pre and post validation results with detailed errors
            - errors: Detailed error info with file, line, message, and suggested fix
        """
        self.logger.info(
            "apply_deduplication_start",
            project_folder=project_folder,
            group_id=group_id,
            dry_run=dry_run,
            backup=backup
        )

        # Initialize validation results
        validation_result: Dict[str, Any] = {
            "pre_validation": {"passed": False, "errors": []},
            "post_validation": {"passed": False, "errors": []}
        }

        try:
            # Validate inputs
            if not os.path.isdir(project_folder):
                raise ValueError(f"Project folder does not exist: {project_folder}")
            if not refactoring_plan:
                raise ValueError("refactoring_plan is required")

            # Extract plan components
            files_affected = refactoring_plan.get("files_affected", [])
            generated_code = refactoring_plan.get("generated_code", {})
            language = refactoring_plan.get("language", "python")
            strategy = refactoring_plan.get("strategy", "extract_function")

            if not files_affected:
                return self._build_response("no_changes", "No files affected", validation_result, dry_run=dry_run, group_id=group_id)

            # Resolve file paths
            files_to_modify = self._resolve_file_paths(files_affected, project_folder)
            if not files_to_modify:
                return self._build_response("no_files", "No valid files found", validation_result, dry_run=dry_run, group_id=group_id)

            # Create orchestration plan
            orchestration_plan = self._plan_file_modification_order(
                files_to_modify, generated_code, extract_to_file, project_folder, language
            )

            # PRE-VALIDATION: Validate generated code syntax
            pre_validation_result = self.validator.validate_plan(refactoring_plan, group_id, project_folder)
            validation_result["pre_validation"] = pre_validation_result.to_dict()

            if not pre_validation_result.is_valid:
                return self._build_response(
                    "failed",
                    f"Pre-validation failed with {len(pre_validation_result.errors)} error(s)",
                    validation_result,
                    errors=pre_validation_result.errors,
                    dry_run=dry_run,
                    group_id=group_id
                )

            # DRY RUN: Preview changes
            if dry_run:
                return self._build_dry_run_response(files_to_modify, validation_result, group_id, strategy)

            # CREATE BACKUP
            backup_id: Optional[str] = None
            if backup:
                backup_manager = DeduplicationBackupManager(project_folder)
                backup_id = backup_manager.create_backup(
                    files=[fp for fp in files_to_modify if os.path.exists(fp)],
                    metadata={
                        "duplicate_group_id": group_id,
                        "strategy": strategy,
                        "file_count": len(files_to_modify)
                    }
                )

            # APPLY CHANGES
            try:
                apply_result = self.executor.apply_changes(
                    orchestration_plan,
                    generated_code.get("replacements", {}),
                    language,
                    dry_run=False
                )
                modified_files = apply_result["modified_files"]

            except Exception as e:
                # Rollback on application failure
                if backup_id:
                    backup_manager = DeduplicationBackupManager(project_folder)
                    backup_manager.rollback(backup_id)
                raise

            # POST-VALIDATION: Validate modified files
            post_validation_result = self.post_validator.validate_modified_files(modified_files, language)
            validation_result["post_validation"] = post_validation_result.to_dict()

            # AUTO-ROLLBACK if post-validation fails
            if not post_validation_result.is_valid and backup_id:
                backup_manager = DeduplicationBackupManager(project_folder)
                restored = backup_manager.rollback(backup_id)
                return self._build_response(
                    "rolled_back",
                    f"Rolled back due to {len(post_validation_result.errors)} validation error(s)",
                    validation_result,
                    files_restored=restored,
                    backup_id=backup_id,
                    errors=post_validation_result.errors,
                    group_id=group_id
                )

            # SUCCESS
            return self._build_response(
                "success",
                f"Applied deduplication to {len(modified_files)} file(s)",
                validation_result,
                files_modified=modified_files,
                backup_id=backup_id,
                group_id=group_id,
                strategy=strategy,
                rollback_command=f"rollback_rewrite(project_folder='{project_folder}', backup_id='{backup_id}')"
            )

        except Exception as e:
            self.logger.error("apply_deduplication_failed", error=str(e)[:200])
            raise

    def _resolve_file_paths(
        self,
        files_affected: List[Any],
        project_folder: str
    ) -> List[str]:
        """Resolve file paths from files_affected list.

        Args:
            files_affected: List of file paths or file info dicts
            project_folder: Project root folder

        Returns:
            List of resolved absolute file paths
        """
        files_to_modify = []
        for file_info in files_affected:
            file_path = file_info if isinstance(file_info, str) else file_info.get("file", "")
            if file_path and os.path.isfile(file_path):
                files_to_modify.append(file_path)
            elif file_path and os.path.isfile(os.path.join(project_folder, file_path)):
                files_to_modify.append(os.path.join(project_folder, file_path))
        return files_to_modify

    def _build_response(
        self,
        status: str,
        message: str,
        validation_result: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Build standardized response dictionary.

        Args:
            status: Response status
            message: Response message
            validation_result: Validation results
            **kwargs: Additional response fields

        Returns:
            Response dictionary
        """
        response = {
            "status": status,
            "message": message,
            "validation": validation_result,
            "dry_run": kwargs.get("dry_run", False)
        }
        response.update(kwargs)
        return response

    def _build_dry_run_response(
        self,
        files_to_modify: List[str],
        validation_result: Dict[str, Any],
        group_id: int,
        strategy: str
    ) -> Dict[str, Any]:
        """Build dry run preview response.

        Args:
            files_to_modify: List of files that would be modified
            validation_result: Validation results
            group_id: Duplication group ID
            strategy: Refactoring strategy

        Returns:
            Preview response dictionary
        """
        changes_preview = []
        for fp in files_to_modify:
            with open(fp, 'r') as f:
                changes_preview.append({
                    "file": fp,
                    "lines": len(f.read().splitlines())
                })

        return {
            "status": "preview",
            "dry_run": True,
            "message": f"Preview of changes to {len(files_to_modify)} file(s)",
            "changes_preview": changes_preview,
            "validation": validation_result,
            "group_id": group_id,
            "strategy": strategy
        }

    def _plan_file_modification_order(
        self,
        files_to_modify: List[str],
        generated_code: Dict[str, Any],
        extract_to_file: Optional[str],
        project_folder: str,
        language: str
    ) -> Dict[str, Any]:
        """Plan the order of file modifications for atomic deduplication."""
        plan: Dict[str, Any] = {
            "create_files": [],
            "update_files": [],
            "import_additions": {}
        }

        extracted_function = generated_code.get("extracted_function", "")
        function_name = generated_code.get("function_name", "extracted_function")

        # Determine target file for extracted function
        target_file = extract_to_file or generated_code.get("extract_to_file")
        if not target_file and files_to_modify:
            # Auto-detect: create utilities module
            first_file = files_to_modify[0]
            file_dir = os.path.dirname(first_file)
            ext = os.path.splitext(first_file)[1]
            target_file = os.path.join(file_dir, f"_extracted_utils{ext}")

        if target_file and not os.path.isabs(target_file):
            target_file = os.path.join(project_folder, target_file)

        # Plan file creation for extracted function
        if extracted_function and target_file:
            append_mode = os.path.exists(target_file)
            plan["create_files"].append({
                "path": target_file,
                "content": extracted_function,
                "append": append_mode,
                "operation": "append" if append_mode else "create"
            })

        # Plan updates for duplicate location files
        for file_path in files_to_modify:
            plan["update_files"].append({
                "path": file_path,
                "operation": "replace_duplicate"
            })

            # Generate import statement if needed
            if extracted_function and target_file and file_path != target_file:
                import_stmt = self._generate_import_for_extracted_function(
                    source_file=file_path,
                    target_file=target_file,
                    function_name=function_name,
                    project_folder=project_folder,
                    language=language
                )

                if import_stmt:
                    plan["import_additions"][file_path] = {
                        "import_statement": import_stmt,
                        "from_file": target_file,
                        "function_name": function_name
                    }

        return plan

    def _generate_import_for_extracted_function(
        self,
        source_file: str,
        target_file: str,
        function_name: str,
        project_folder: str,
        language: str
    ) -> str:
        """Generate import statement for an extracted function."""
        # Calculate relative path from source to target
        source_dir = os.path.dirname(source_file)
        target_rel = os.path.relpath(target_file, source_dir)

        # Convert path to module path
        module_path = os.path.splitext(target_rel)[0]
        module_path = module_path.replace(os.sep, ".")
        module_path = module_path.replace("/", ".")

        # Handle parent directory references
        if module_path.startswith(".."):
            # Convert ../foo to relative import
            parts = module_path.split(".")
            parent_count = sum(1 for p in parts if p == "")
            module_parts = [p for p in parts if p and p != ".."]
            module_path = "." * parent_count + ".".join(module_parts)

        # Generate import using code generator
        return self.code_generator.generate_import_statement(
            module_path=module_path,
            import_names=[function_name],
            is_relative=module_path.startswith(".")
        )

    def _add_import_to_content(
        self,
        content: str,
        import_statement: str,
        language: str
    ) -> str:
        """Add an import statement to file content."""
        if not import_statement:
            return content

        lines = content.split('\n')
        lang = language.lower()

        # Check if import already exists
        if import_statement.strip() in content:
            return content

        if lang == "python":
            # Find last import statement
            last_import_idx = -1
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    last_import_idx = i
                elif stripped and not stripped.startswith("#") and last_import_idx >= 0:
                    break

            if last_import_idx >= 0:
                lines.insert(last_import_idx + 1, import_statement)
            else:
                # No imports found, add at the top after any shebang/encoding
                insert_idx = 0
                for i, line in enumerate(lines):
                    if not line.strip() or line.startswith("#"):
                        insert_idx = i + 1
                    else:
                        break
                lines.insert(insert_idx, import_statement)
                if insert_idx > 0:
                    lines.insert(insert_idx, "")

        elif lang in ("javascript", "typescript", "jsx", "tsx"):
            # Add after last import/require
            last_import_idx = -1
            for i, line in enumerate(lines):
                if "import " in line or "require(" in line:
                    last_import_idx = i

            if last_import_idx >= 0:
                lines.insert(last_import_idx + 1, import_statement)
            else:
                lines.insert(0, import_statement)
                lines.insert(1, "")

        elif lang == "java":
            # Add after package statement but before class
            package_idx = -1
            last_import_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith("package "):
                    package_idx = i
                elif line.strip().startswith("import "):
                    last_import_idx = i

            if last_import_idx >= 0:
                lines.insert(last_import_idx + 1, import_statement)
            elif package_idx >= 0:
                lines.insert(package_idx + 1, "")
                lines.insert(package_idx + 2, import_statement)
            else:
                lines.insert(0, import_statement)
                lines.insert(1, "")

        else:
            # Default: add at the top
            lines.insert(0, import_statement)
            lines.insert(1, "")

        return '\n'.join(lines)

    def _validate_code_for_language(self, code: str, language: str) -> tuple[bool, str]:
        """Basic syntax validation for generated code."""
        # This is a simplified version - in production, use proper parsers
        lang = language.lower()

        if lang == "python":
            try:
                compile(code, '<string>', 'exec')
                return True, ""
            except SyntaxError as e:
                return False, str(e)

        # For other languages, do basic checks
        return True, ""

    def _suggest_syntax_fix(self, error: Optional[str], language: str) -> str:
        """Suggest a fix for common syntax errors."""
        if not error:
            return "Check syntax and indentation"

        lang = language.lower()
        error_lower = error.lower()

        if lang == "python":
            if "indentation" in error_lower:
                return "Check indentation - Python uses 4 spaces"
            elif "invalid syntax" in error_lower:
                return "Check for missing colons, parentheses, or quotes"

        return "Review the generated code for syntax errors"

    def create_deduplication_backup(
        self,
        files_to_backup: List[str],
        project_folder: str,
        duplicate_group_id: int,
        strategy: str,
        original_hashes: Dict[str, str]
    ) -> str:
        """Create a backup with deduplication-specific metadata."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        backup_id = f"dedup-backup-{timestamp}"
        backup_base_dir = os.path.join(project_folder, ".ast-grep-backups")
        backup_dir = os.path.join(backup_base_dir, backup_id)

        # Handle collision by appending counter
        counter = 1
        while os.path.exists(backup_dir):
            backup_id = f"dedup-backup-{timestamp}-{counter}"
            backup_dir = os.path.join(backup_base_dir, backup_id)
            counter += 1

        os.makedirs(backup_dir, exist_ok=True)

        metadata: Dict[str, Any] = {
            "backup_id": backup_id,
            "backup_type": "deduplication",
            "timestamp": datetime.now().isoformat(),
            "files": [],
            "project_folder": project_folder,
            "deduplication_metadata": {
                "duplicate_group_id": duplicate_group_id,
                "strategy": strategy,
                "original_hashes": original_hashes,
                "affected_files": files_to_backup
            }
        }

        for file_path in files_to_backup:
            if not os.path.exists(file_path):
                continue

            rel_path = os.path.relpath(file_path, project_folder)
            backup_file_path = os.path.join(backup_dir, rel_path)

            os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
            shutil.copy2(file_path, backup_file_path)

            metadata["files"].append({
                "original": file_path,
                "relative": rel_path,
                "backup": backup_file_path,
                "original_hash": original_hashes.get(file_path, "")
            })

        metadata_path = os.path.join(backup_dir, "backup-metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return backup_id

    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file's contents."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (OSError, IOError):
            return ""

    def restore_from_backup(self, backup_id: str, project_folder: str) -> List[str]:
        """Restore files from a backup."""
        backup_dir = os.path.join(project_folder, ".ast-grep-backups", backup_id)
        metadata_path = os.path.join(backup_dir, "backup-metadata.json")

        if not os.path.exists(metadata_path):
            raise ValueError(f"Backup '{backup_id}' not found or invalid")

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        restored_files = []
        for file_info in metadata["files"]:
            backup_file = file_info["backup"]
            original_file = file_info["original"]

            if not os.path.exists(backup_file):
                continue

            os.makedirs(os.path.dirname(original_file), exist_ok=True)
            shutil.copy2(backup_file, original_file)
            restored_files.append(original_file)

        return restored_files


# Module-level functions for backward compatibility with tests
_applicator_instance = None

def _get_applicator():
    """Get or create the global applicator instance."""
    global _applicator_instance
    if _applicator_instance is None:
        _applicator_instance = DeduplicationApplicator()
    return _applicator_instance

def _plan_file_modification_order(
    files_to_modify: List[str],
    generated_code: Dict[str, Any],
    extract_to_file: Optional[str],
    project_folder: str,
    language: str
) -> Dict[str, Any]:
    """Module-level wrapper for _plan_file_modification_order."""
    return _get_applicator()._plan_file_modification_order(
        files_to_modify, generated_code, extract_to_file, project_folder, language
    )

def _add_import_to_content(
    content: str,
    import_statement: str,
    language: str
) -> str:
    """Module-level wrapper for _add_import_to_content."""
    return _get_applicator()._add_import_to_content(content, import_statement, language)

def _generate_import_for_extracted_function(
    source_file: str,
    target_file: str,
    function_name: str,
    language: str,
    project_folder: str
) -> str:
    """Module-level wrapper for _generate_import_for_extracted_function."""
    return _get_applicator()._generate_import_for_extracted_function(
        source_file, target_file, function_name, language, project_folder
    )
