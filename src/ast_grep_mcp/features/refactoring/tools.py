"""MCP tools for refactoring operations."""

from typing import Any, Dict, Optional
from pydantic import Field
import structlog

from .analyzer import CodeSelectionAnalyzer
from .extractor import FunctionExtractor
from .rename_coordinator import RenameCoordinator
from ...models.refactoring import ExtractFunctionResult, RenameSymbolResult

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


def rename_symbol_tool(
    project_folder: str,
    symbol_name: str,
    new_name: str,
    language: str,
    scope: str = "project",
    file_filter: Optional[str] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Rename a symbol (variable, function, class) across codebase.

    This tool performs scope-aware symbol renaming with:
    - Finding all references across files
    - Respecting scope boundaries (avoiding shadowed symbols)
    - Updating import/export statements
    - Detecting naming conflicts before applying
    - Atomic multi-file updates with rollback

    Args:
        project_folder: Root folder of the project
        symbol_name: Current symbol name to rename
        new_name: New symbol name
        language: Programming language (python, typescript, javascript, java)
        scope: Scope to rename in ('project', 'file', 'function')
        file_filter: Optional glob pattern to filter files (e.g., '*.py', 'src/**/*.ts')
        dry_run: If True, only preview changes without applying (default: True)

    Returns:
        Dict containing:
        - success (bool): Whether rename succeeded
        - old_name (str): Original symbol name
        - new_name (str): New symbol name
        - references_found (int): Number of references found
        - references_updated (int): Number of references updated
        - files_modified (list): List of files modified
        - conflicts (list): List of naming conflicts (if any)
        - diff_preview (str): Unified diff of changes
        - backup_id (str): Backup ID if applied (for rollback)
        - error (str): Error message if failed

    Example:
        ```python
        # Preview renaming
        result = rename_symbol(
            project_folder="/path/to/project",
            symbol_name="processData",
            new_name="transformData",
            language="typescript",
            scope="project",
            dry_run=True  # Preview first
        )

        if result["success"] and not result.get("conflicts"):
            print(f"Found {result['references_found']} references")
            print(result["diff_preview"])

            # Apply if satisfied
            result = rename_symbol(..., dry_run=False)
        ```

    Notes:
        - Always preview with dry_run=True first
        - Checks for naming conflicts before applying
        - Respects scope boundaries (won't rename shadowed variables)
        - Updates imports/exports automatically
        - Creates backup automatically (use rollback_rewrite to undo)
        - Atomic operation: all files updated or none
    """
    try:
        logger.info(
            "rename_symbol_tool_called",
            symbol_name=symbol_name,
            new_name=new_name,
            language=language,
            scope=scope,
            dry_run=dry_run,
        )

        # Create coordinator
        coordinator = RenameCoordinator(language)

        # Perform rename
        result = coordinator.rename_symbol(
            project_folder=project_folder,
            old_name=symbol_name,
            new_name=new_name,
            scope=scope,
            file_filter=file_filter,
            dry_run=dry_run,
        )

        # Format response
        return {
            "success": result.success,
            "old_name": result.old_name,
            "new_name": result.new_name,
            "references_found": result.references_found,
            "references_updated": result.references_updated,
            "files_modified": result.files_modified,
            "conflicts": result.conflicts,
            "diff_preview": result.diff_preview,
            "backup_id": result.backup_id,
            "error": result.error,
        }

    except Exception as e:
        logger.error("rename_symbol_tool_error", error=str(e))
        return {
            "success": False,
            "old_name": symbol_name,
            "new_name": new_name,
            "error": f"Rename symbol failed: {str(e)}",
        }


# MCP wrapper with Pydantic validation
def rename_symbol(
    project_folder: str = Field(description="Root folder of the project"),
    symbol_name: str = Field(description="Current symbol name to rename"),
    new_name: str = Field(description="New symbol name"),
    language: str = Field(description="Programming language (python, typescript, javascript, java)"),
    scope: str = Field("project", description="Scope to rename in ('project', 'file', 'function')"),
    file_filter: Optional[str] = Field(None, description="Optional glob pattern to filter files (e.g., '*.py', 'src/**/*.ts')"),
    dry_run: bool = Field(True, description="If True, only preview changes without applying"),
) -> Dict[str, Any]:
    """Rename a symbol across codebase with scope awareness and conflict detection.

    MCP tool wrapper for rename_symbol_tool.
    """
    return rename_symbol_tool(
        project_folder=project_folder,
        symbol_name=symbol_name,
        new_name=new_name,
        language=language,
        scope=scope,
        file_filter=file_filter,
        dry_run=dry_run,
    )
