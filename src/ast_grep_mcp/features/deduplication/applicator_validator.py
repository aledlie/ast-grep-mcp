"""Validation logic for deduplication refactoring plans.

This module handles pre-validation of refactoring plans before
they are applied to ensure code quality and prevent syntax errors.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...core.logging import get_logger


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
            is_valid, error_msg = self._validate_code_for_language(
                extracted_function,
                language
            )
            if not is_valid:
                errors.append({
                    "type": "extracted_function",
                    "file": "extracted function",
                    "error": error_msg,
                    "code_preview": extracted_function[:200],
                    "suggestion": self._suggest_syntax_fix(error_msg, language)
                })

        # Validate replacements
        replacements = generated_code.get('replacements', {})
        for file_path, replacement in replacements.items():
            new_content = replacement.get('new_content', '')
            if new_content:
                is_valid, error_msg = self._validate_code_for_language(
                    new_content,
                    language
                )
                if not is_valid:
                    errors.append({
                        "type": "replacement_code",
                        "file": file_path,
                        "error": error_msg,
                        "suggestion": self._suggest_syntax_fix(error_msg, language)
                    })

        return errors

    def _validate_code_for_language(
        self,
        code: str,
        language: str
    ) -> Tuple[bool, str]:
        """Validate code syntax for specific language.

        Args:
            code: Code to validate
            language: Programming language

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not code or not code.strip():
            return False, "Code is empty"

        if language.lower() == "python":
            try:
                import ast
                ast.parse(code)
                return True, ""
            except SyntaxError as e:
                return False, f"Python syntax error: {e}"
            except Exception as e:
                return False, f"Validation error: {e}"

        elif language.lower() in ["javascript", "typescript"]:
            # Basic validation - check for obvious syntax errors
            if code.count('{') != code.count('}'):
                return False, "Mismatched braces"
            if code.count('(') != code.count(')'):
                return False, "Mismatched parentheses"
            if code.count('[') != code.count(']'):
                return False, "Mismatched brackets"
            return True, ""

        elif language.lower() == "java":
            # Basic Java validation
            if code.count('{') != code.count('}'):
                return False, "Mismatched braces"
            if code.count('(') != code.count(')'):
                return False, "Mismatched parentheses"
            return True, ""

        else:
            # For unsupported languages, do basic checks
            self.logger.warning("unsupported_language_validation", language=language)
            return True, ""

    def _suggest_syntax_fix(self, error: Optional[str], language: str) -> str:
        """Generate syntax fix suggestion based on error.

        Args:
            error: Error message
            language: Programming language

        Returns:
            Suggested fix message
        """
        if not error:
            return "Check code syntax and formatting"

        error_lower = error.lower()

        # Common Python errors
        if "indentation" in error_lower:
            return "Fix indentation - ensure consistent use of spaces/tabs"
        elif "unexpected eof" in error_lower or "unexpected indent" in error_lower:
            return "Check for missing closing brackets, parentheses, or quotes"
        elif "invalid syntax" in error_lower:
            return "Review syntax near the error location - check for typos"

        # Common brace/bracket errors
        elif "mismatched" in error_lower:
            if "brace" in error_lower:
                return "Balance opening and closing braces {}"
            elif "parenthes" in error_lower:
                return "Balance opening and closing parentheses ()"
            elif "bracket" in error_lower:
                return "Balance opening and closing brackets []"

        return f"Review {language} syntax and fix the error: {error[:100]}"
