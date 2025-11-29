"""Validation logic for deduplication refactoring plans.

This module handles pre-validation of refactoring plans before
they are applied to ensure code quality and prevent syntax errors.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...core.logging import get_logger
from ...utils.syntax_validation import suggest_syntax_fix, validate_code_for_language


class ValidationResult:
    """Result of validation operation."""

    def __init__(self, is_valid: bool, errors: List[Dict[str, Any]]) -> None:
        """Initialize validation result.

        Args:
            is_valid: Whether validation passed
            errors: List of validation errors
        """
        self.is_valid = is_valid
        self.errors = errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "passed": self.is_valid,
            "errors": self.errors
        }


class RefactoringPlanValidator:
    """Validates refactoring plans before application."""

    def __init__(self) -> None:
        """Initialize the validator."""
        self.logger = get_logger("deduplication.validator")

    def validate_plan(
        self,
        refactoring_plan: Dict[str, Any],
        group_id: int,
        project_folder: str
    ) -> ValidationResult:
        """Validate refactoring plan completeness and correctness.

        Args:
            refactoring_plan: The refactoring plan to validate
            group_id: Duplication group ID
            project_folder: Project root folder

        Returns:
            ValidationResult with validation status and errors
        """
        self.logger.info("validate_plan_start", group_id=group_id)
        errors: List[Dict[str, Any]] = []

        # Validate required fields
        errors.extend(self._validate_required_fields(refactoring_plan))

        # Validate generated code syntax (file existence checked during orchestration)
        errors.extend(self._validate_code_syntax(refactoring_plan))

        is_valid = len(errors) == 0
        self.logger.info(
            "validate_plan_complete",
            is_valid=is_valid,
            error_count=len(errors)
        )

        return ValidationResult(is_valid=is_valid, errors=errors)

    def _validate_required_fields(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check plan has all required fields.

        Args:
            plan: Refactoring plan to validate

        Returns:
            List of error dictionaries
        """
        errors = []
        required_fields = ['generated_code', 'files_affected', 'language']

        for field in required_fields:
            if field not in plan:
                errors.append({
                    "type": "missing_field",
                    "field": field,
                    "error": f"Missing required field: {field}",
                    "suggestion": f"Add '{field}' to the refactoring plan"
                })

        return errors

    def _validate_files_exist(
        self,
        plan: Dict[str, Any],
        project_folder: str
    ) -> List[Dict[str, Any]]:
        """Verify all affected files exist.

        Args:
            plan: Refactoring plan
            project_folder: Project root folder

        Returns:
            List of error dictionaries
        """
        errors = []
        files_affected = plan.get('files_affected', [])

        for file_info in files_affected:
            file_path = file_info if isinstance(file_info, str) else file_info.get("file", "")

            if not file_path:
                continue

            # Try as absolute path first
            full_path = Path(file_path)
            if not full_path.is_absolute():
                # Try relative to project folder
                full_path = Path(project_folder) / file_path

            if not full_path.exists():
                errors.append({
                    "type": "file_not_found",
                    "file": str(file_path),
                    "error": f"File not found: {file_path}",
                    "suggestion": "Verify the file path is correct"
                })
            elif not full_path.is_file():
                errors.append({
                    "type": "not_a_file",
                    "file": str(file_path),
                    "error": f"Path is not a file: {file_path}",
                    "suggestion": "Ensure the path points to a file, not a directory"
                })

        return errors

    def _validate_code_syntax(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Pre-validate generated code syntax.

        Args:
            plan: Refactoring plan with generated code

        Returns:
            List of error dictionaries
        """
        errors = []
        language = plan.get('language', 'python')
        generated_code = plan.get('generated_code', {})

        # Validate extracted function
        extracted_function = generated_code.get('extracted_function', '')
        if extracted_function:
            is_valid, error_msg = validate_code_for_language(
                extracted_function,
                language
            )
            if not is_valid:
                errors.append({
                    "type": "extracted_function",
                    "file": "extracted function",
                    "error": error_msg,
                    "code_preview": extracted_function[:200],
                    "suggestion": suggest_syntax_fix(error_msg, language, context="code")
                })

        # Validate replacements
        replacements = generated_code.get('replacements', {})
        for file_path, replacement in replacements.items():
            new_content = replacement.get('new_content', '')
            if new_content:
                is_valid, error_msg = validate_code_for_language(
                    new_content,
                    language
                )
                if not is_valid:
                    errors.append({
                        "type": "replacement_code",
                        "file": file_path,
                        "error": error_msg,
                        "suggestion": suggest_syntax_fix(error_msg, language, context="code")
                    })

        return errors

