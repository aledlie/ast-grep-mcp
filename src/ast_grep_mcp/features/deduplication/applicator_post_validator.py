"""Post-validation logic for deduplication refactoring.

This module handles validation of files after refactoring changes
have been applied to ensure code correctness.
"""
import os
from typing import Any, Dict, List, Optional

from ...core.logging import get_logger


class PostValidationResult:
    """Result of post-validation operation."""

    def __init__(self, is_valid: bool, errors: List[Dict[str, Any]]):
        """Initialize post-validation result.

        Args:
            is_valid: Whether post-validation passed
            errors: List of validation errors found
        """
        self.is_valid = is_valid
        self.errors = errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format.

        Returns:
            Dictionary representation of validation result
        """
        return {
            "passed": self.is_valid,
            "errors": self.errors
        }


class RefactoringPostValidator:
    """Validates files after refactoring modifications."""

    def __init__(self):
        """Initialize the post-validator."""
        self.logger = get_logger("deduplication.post_validator")

    def validate_modified_files(
        self,
        modified_files: List[str],
        language: str
    ) -> PostValidationResult:
        """Validate files after modifications.

        Args:
            modified_files: List of modified file paths
            language: Programming language

        Returns:
            PostValidationResult with validation status and errors
        """
        self.logger.info(
            "post_validation_start",
            file_count=len(modified_files),
            language=language
        )

        errors: List[Dict[str, Any]] = []

        # Validate each modified file
        for file_path in modified_files:
            if not os.path.exists(file_path):
                errors.append({
                    "type": "file_not_found",
                    "file": file_path,
                    "error": f"Modified file not found: {file_path}",
                    "suggestion": "File may have been deleted during operation"
                })
                continue

            # Validate syntax only (matching original behavior)
            syntax_errors = self._validate_file_syntax(file_path, language)
            errors.extend(syntax_errors)

        is_valid = len(errors) == 0
        self.logger.info(
            "post_validation_complete",
            is_valid=is_valid,
            error_count=len(errors)
        )

        return PostValidationResult(is_valid=is_valid, errors=errors)

    def _validate_file_syntax(
        self,
        file_path: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Validate file syntax after modifications.

        Args:
            file_path: Path to file to validate
            language: Programming language

        Returns:
            List of validation error dictionaries
        """
        errors = []

        try:
            # Import here to avoid circular dependency
            from ..rewrite.service import validate_syntax

            result = validate_syntax(file_path, language)
            if not result["valid"]:
                errors.append({
                    "type": "syntax_error",
                    "file": file_path,
                    "error": result.get("error", "Unknown syntax error"),
                    "suggestion": self._suggest_syntax_fix(
                        result.get("error"),
                        language
                    )
                })
                self.logger.warning(
                    "syntax_validation_failed",
                    file=file_path,
                    error=result.get("error", "")[:200]
                )

        except Exception as e:
            errors.append({
                "type": "validation_exception",
                "file": file_path,
                "error": f"Failed to validate syntax: {str(e)}",
                "suggestion": "Check if the file is readable and well-formed"
            })
            self.logger.error(
                "syntax_validation_exception",
                file=file_path,
                error=str(e)
            )

        return errors

    def _validate_file_structure(
        self,
        file_path: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Validate basic file structure.

        Args:
            file_path: Path to file to validate
            language: Programming language

        Returns:
            List of validation error dictionaries
        """
        errors = []

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            lang = language.lower()

            # Basic structural checks
            if not content.strip():
                errors.append({
                    "type": "empty_file",
                    "file": file_path,
                    "error": "File is empty after modifications",
                    "suggestion": "Verify that content was written correctly"
                })

            # Language-specific checks
            if lang == "python":
                errors.extend(self._validate_python_structure(file_path, content))
            elif lang in ("javascript", "typescript", "jsx", "tsx"):
                errors.extend(self._validate_js_structure(file_path, content))
            elif lang == "java":
                errors.extend(self._validate_java_structure(file_path, content))

        except Exception as e:
            errors.append({
                "type": "structure_check_failed",
                "file": file_path,
                "error": f"Failed to check file structure: {str(e)}",
                "suggestion": "Verify file is readable"
            })

        return errors

    def _validate_python_structure(
        self,
        file_path: str,
        content: str
    ) -> List[Dict[str, Any]]:
        """Validate Python-specific structure.

        Args:
            file_path: Path to file
            content: File content

        Returns:
            List of validation errors
        """
        errors = []

        # Check for balanced quotes
        single_quotes = content.count("'") - content.count("\\'")
        double_quotes = content.count('"') - content.count('\\"')

        if single_quotes % 2 != 0:
            errors.append({
                "type": "unbalanced_quotes",
                "file": file_path,
                "error": "Unbalanced single quotes in file",
                "suggestion": "Check for unclosed string literals"
            })

        if double_quotes % 2 != 0:
            errors.append({
                "type": "unbalanced_quotes",
                "file": file_path,
                "error": "Unbalanced double quotes in file",
                "suggestion": "Check for unclosed string literals"
            })

        # Check for basic Python structure markers
        lines = content.split('\n')
        has_content = any(
            line.strip() and not line.strip().startswith('#')
            for line in lines
        )

        if not has_content:
            errors.append({
                "type": "no_code_content",
                "file": file_path,
                "error": "File contains only comments or whitespace",
                "suggestion": "Verify code was written correctly"
            })

        return errors

    def _validate_js_structure(
        self,
        file_path: str,
        content: str
    ) -> List[Dict[str, Any]]:
        """Validate JavaScript/TypeScript structure.

        Args:
            file_path: Path to file
            content: File content

        Returns:
            List of validation errors
        """
        errors = []

        # Check for balanced braces, brackets, parentheses
        if content.count('{') != content.count('}'):
            errors.append({
                "type": "unbalanced_braces",
                "file": file_path,
                "error": "Unbalanced curly braces",
                "suggestion": "Check for missing { or }"
            })

        if content.count('[') != content.count(']'):
            errors.append({
                "type": "unbalanced_brackets",
                "file": file_path,
                "error": "Unbalanced square brackets",
                "suggestion": "Check for missing [ or ]"
            })

        if content.count('(') != content.count(')'):
            errors.append({
                "type": "unbalanced_parentheses",
                "file": file_path,
                "error": "Unbalanced parentheses",
                "suggestion": "Check for missing ( or )"
            })

        return errors

    def _validate_java_structure(
        self,
        file_path: str,
        content: str
    ) -> List[Dict[str, Any]]:
        """Validate Java structure.

        Args:
            file_path: Path to file
            content: File content

        Returns:
            List of validation errors
        """
        errors = []

        # Check for balanced braces
        if content.count('{') != content.count('}'):
            errors.append({
                "type": "unbalanced_braces",
                "file": file_path,
                "error": "Unbalanced curly braces",
                "suggestion": "Check for missing { or }"
            })

        # Check for class definition
        if 'class ' not in content and 'interface ' not in content:
            errors.append({
                "type": "no_class_definition",
                "file": file_path,
                "error": "No class or interface definition found",
                "suggestion": "Java files should contain at least one class or interface"
            })

        return errors

    def _suggest_syntax_fix(
        self,
        error: Optional[str],
        language: str
    ) -> str:
        """Generate syntax fix suggestion based on error.

        Args:
            error: Error message
            language: Programming language

        Returns:
            Suggested fix message
        """
        if not error:
            return "Review file for syntax errors"

        error_lower = error.lower()

        # Common Python errors
        if "indentation" in error_lower:
            return "Fix indentation - ensure consistent use of spaces/tabs"
        elif "unexpected eof" in error_lower or "unexpected indent" in error_lower:
            return "Check for missing closing brackets, parentheses, or quotes"
        elif "invalid syntax" in error_lower:
            return "Review syntax near the error location - check for typos"

        # Common brace/bracket errors
        elif "unbalanced" in error_lower or "mismatched" in error_lower:
            if "brace" in error_lower:
                return "Balance opening and closing braces {}"
            elif "parenthes" in error_lower:
                return "Balance opening and closing parentheses ()"
            elif "bracket" in error_lower:
                return "Balance opening and closing brackets []"

        # Generic suggestion
        return f"Review {language} syntax and fix the error: {error[:100]}"
