"""MCP tools for refactoring operations."""

from typing import Any, Dict, Optional
from pydantic import Field
import structlog

from .analyzer import CodeSelectionAnalyzer
from .extractor import FunctionExtractor
from ...models.refactoring import ExtractFunctionResult

logger = structlog.get_logger(__name__)


def extract_function_tool(
    project_folder: str,
    file_path: str,
    start_line: int,
    end_line: int,
    language: str,
    function_name: Optional[str] = None,
    extract_location: str = "before",
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Extract selected code into a new function.

    This tool performs intelligent function extraction with automatic parameter
    and return value detection. It analyzes the selected code to determine:
    - Which variables need to be passed as parameters
    - Which variables need to be returned
    - Appropriate function signature with type hints
    - Proper placement of the extracted function

    Args:
        project_folder: Root folder of the project
        file_path: Path to the file (relative to project_folder or absolute)
        start_line: Starting line of code to extract (1-indexed)
        end_line: Ending line of code to extract (1-indexed, inclusive)
        language: Programming language (python, typescript, javascript, java)
        function_name: Optional name for extracted function (auto-generated if None)
        extract_location: Where to place function ('before', 'after', 'top')
        dry_run: If True, only preview changes without applying (default: True)

    Returns:
        Dict containing:
        - success (bool): Whether extraction succeeded
        - function_name (str): Name of extracted function
        - function_signature (str): Generated function signature
        - parameters (list): Parameters detected
        - return_values (list): Values to be returned
        - diff_preview (str): Unified diff of changes
        - backup_id (str): Backup ID if applied (for rollback)
        - warnings (list): Any warnings about the extraction
        - error (str): Error message if failed

    Example:
        ```python
        # Extract a code block into a function
        result = extract_function(
            project_folder="/path/to/project",
            file_path="src/utils.py",
            start_line=45,
            end_line=52,
            language="python",
            function_name="validate_email",  # Optional
            dry_run=True  # Preview first
        )

        if result["success"]:
            print(result["diff_preview"])
            # If satisfied, apply it:
            # result = extract_function(..., dry_run=False)
        ```

    Notes:
        - Always preview with dry_run=True first
        - The tool automatically detects parameters and return values
        - Function will be placed before/after/top of the selection
        - Original code is replaced with a function call
        - Type hints are inferred when possible
        - Backup is created automatically (use rollback_rewrite to undo)
    """
    try:
        logger.info(
            "extract_function_tool_called",
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            language=language,
            dry_run=dry_run,
        )

        # Build absolute file path
        if not file_path.startswith('/'):
            import os
            file_path = os.path.join(project_folder, file_path)

        # Analyze the code selection
        analyzer = CodeSelectionAnalyzer(language)
        selection = analyzer.analyze_selection(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            project_folder=project_folder,
        )

        # Extract the function
        extractor = FunctionExtractor(language)
        result = extractor.extract_function(
            selection=selection,
            function_name=function_name,
            extract_location=extract_location,
            dry_run=dry_run,
        )

        # Format response
        if result.success:
            return {
                "success": True,
                "function_name": result.function_signature.name if result.function_signature else None,
                "function_signature": (
                    result.function_signature.to_python_signature()
                    if result.function_signature and language == "python"
                    else result.function_signature.to_typescript_signature()
                    if result.function_signature
                    else None
                ),
                "parameters": selection.parameters_needed,
                "return_values": selection.return_values,
                "diff_preview": result.diff_preview,
                "backup_id": result.backup_id,
                "warnings": result.warnings,
                "has_early_returns": selection.has_early_returns,
                "has_exceptions": selection.has_exceptions,
            }
        else:
            return {
                "success": False,
                "error": result.error,
            }

    except Exception as e:
        logger.error("extract_function_tool_error", error=str(e))
        return {
            "success": False,
            "error": f"Extract function failed: {str(e)}",
        }


# MCP wrapper with Pydantic validation
def extract_function(
    project_folder: str = Field(description="Root folder of the project"),
    file_path: str = Field(description="Path to the file (relative or absolute)"),
    start_line: int = Field(description="Starting line of code to extract (1-indexed)", ge=1),
    end_line: int = Field(description="Ending line of code to extract (1-indexed, inclusive)", ge=1),
    language: str = Field(description="Programming language (python, typescript, javascript, java)"),
    function_name: Optional[str] = Field(None, description="Optional name for extracted function (auto-generated if None)"),
    extract_location: str = Field("before", description="Where to place function ('before', 'after', 'top')"),
    dry_run: bool = Field(True, description="If True, only preview changes without applying"),
) -> Dict[str, Any]:
    """Extract selected code into a new function with automatic parameter detection.

    MCP tool wrapper for extract_function_tool.
    """
    return extract_function_tool(
        project_folder=project_folder,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        language=language,
        function_name=function_name,
        extract_location=extract_location,
        dry_run=dry_run,
    )
