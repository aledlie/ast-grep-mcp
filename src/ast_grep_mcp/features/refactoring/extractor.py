"""Function extraction logic for refactoring operations.

This module handles:
- Generating function signatures from code analysis
- Creating function bodies with proper indentation
- Generating call site replacements
- Inserting extracted functions at proper locations
"""

from typing import Dict, List, Optional

from ast_grep_mcp.core.logging import get_logger

from ...features.rewrite.backup import create_backup, restore_backup
from ...models.refactoring import (
    CodeSelection,
    ExtractFunctionResult,
    FunctionSignature,
)

logger = get_logger(__name__)


class FunctionExtractor:
    """Handles function extraction refactoring."""

    def __init__(self, language: str) -> None:
        """Initialize extractor for specific language.

        Args:
            language: Programming language (python, typescript, javascript, java)
        """
        self.language = language

    def extract_function(
        self,
        selection: CodeSelection,
        function_name: Optional[str] = None,
        extract_location: str = "before",
        dry_run: bool = True,
    ) -> ExtractFunctionResult:
        """Extract selected code into a new function.

        Args:
            selection: Analyzed code selection
            function_name: Name for extracted function (auto-generated if None)
            extract_location: Where to place function ('before', 'after', 'top')
            dry_run: If True, only preview changes

        Returns:
            ExtractFunctionResult with success status and details
        """
        logger.info(
            "extracting_function",
            file_path=selection.file_path,
            start_line=selection.start_line,
            end_line=selection.end_line,
            function_name=function_name,
            dry_run=dry_run,
        )

        try:
            # Generate function name if not provided
            if not function_name:
                function_name = self._generate_function_name(selection)

            # Generate function signature
            signature = self._generate_signature(selection, function_name)

            # Generate function body
            function_body = self._generate_function_body(selection, signature)

            # Generate call site replacement
            call_replacement = self._generate_call_site(selection, signature)

            # Determine insertion line
            insertion_line = self._determine_insertion_line(selection, extract_location)

            # Generate diff preview
            diff_preview = self._generate_diff_preview(
                selection,
                function_body,
                call_replacement,
                insertion_line,
            )

            if not dry_run:
                # Apply the refactoring
                backup_id = self._apply_extraction(
                    selection,
                    function_body,
                    call_replacement,
                    insertion_line,
                )
            else:
                backup_id = None

            return ExtractFunctionResult(
                success=True,
                function_signature=signature,
                function_body=function_body,
                call_site_replacement=call_replacement,
                insertion_line=insertion_line,
                diff_preview=diff_preview,
                backup_id=backup_id,
            )

        except Exception as e:
            logger.error("extract_function_failed", error=str(e))
            return ExtractFunctionResult(
                success=False,
                error=str(e),
            )

    def _generate_function_name(self, selection: CodeSelection) -> str:
        """Generate a function name based on code content.

        Args:
            selection: Code selection

        Returns:
            Generated function name
        """
        # Simple heuristic: look for common action verbs or nouns
        content_lower = selection.content.lower()

        action_verbs = [
            "validate",
            "process",
            "calculate",
            "format",
            "parse",
            "convert",
            "transform",
            "filter",
            "map",
            "reduce",
            "check",
            "verify",
            "create",
            "update",
            "delete",
            "get",
            "set",
            "fetch",
            "load",
            "save",
            "send",
        ]

        for verb in action_verbs:
            if verb in content_lower:
                return f"{verb}_extracted"

        # Default fallback
        return "extracted_function"

    def _generate_signature(
        self,
        selection: CodeSelection,
        function_name: str,
    ) -> FunctionSignature:
        """Generate function signature from analyzed selection.

        Args:
            selection: Analyzed code selection
            function_name: Name for the function

        Returns:
            FunctionSignature
        """
        # Build parameter list
        parameters: List[Dict[str, str]] = []
        for param_name in selection.parameters_needed:
            # Find variable info for type inference
            var_info = next((v for v in selection.variables if v.name == param_name), None)

            param_type = var_info.inferred_type if var_info and var_info.inferred_type else ""
            param: Dict[str, str] = {
                "name": param_name,
                "type": param_type,
            }
            parameters.append(param)

        # Determine return type
        return_type = None
        if len(selection.return_values) == 0:
            return_type = "None" if self.language == "python" else "void"
        elif len(selection.return_values) == 1:
            # Single return value
            var_info = next((v for v in selection.variables if v.name == selection.return_values[0]), None)
            return_type = var_info.inferred_type if var_info else None
        else:
            # Multiple return values
            if self.language == "python":
                return_type = f"tuple[{', '.join(['Any'] * len(selection.return_values))}]"
            elif self.language in ("typescript", "javascript"):
                return_type = f"[{', '.join(['any'] * len(selection.return_values))}]"

        # Generate docstring
        docstring = self._generate_docstring(
            function_name,
            parameters,
            return_type,
            selection,
        )

        return FunctionSignature(
            name=function_name,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
        )

    def _generate_docstring(
        self,
        function_name: str,
        parameters: List[Dict[str, str]],
        return_type: Optional[str],
        selection: CodeSelection,
    ) -> str:
        """Generate docstring for extracted function.

        Args:
            function_name: Function name
            parameters: Parameter list
            return_type: Return type
            selection: Code selection

        Returns:
            Docstring text
        """
        if self.language == "python":
            lines = [f'"""Extracted function from {selection.file_path}.']

            if parameters:
                lines.append("")
                lines.append("Args:")
                for param in parameters:
                    param_type = f" ({param.get('type')})" if param.get("type") else ""
                    lines.append(f"    {param['name']}{param_type}: Parameter extracted from code")

            if return_type and return_type != "None":
                lines.append("")
                lines.append("Returns:")
                lines.append(f"    {return_type}: Extracted return value")

            lines.append('"""')
            return "\n".join(lines)

        elif self.language in ("typescript", "javascript"):
            lines = ["/**"]
            lines.append(f" * Extracted function from {selection.file_path}")

            if parameters:
                lines.append(" *")
                for param in parameters:
                    param_type = param.get("type", "any")
                    lines.append(f" * @param {{{param_type}}} {param['name']} - Parameter extracted from code")

            if return_type:
                lines.append(f" * @returns {{{return_type}}} Extracted return value")

            lines.append(" */")
            return "\n".join(lines)

        return ""

    def _generate_function_body(
        self,
        selection: CodeSelection,
        signature: FunctionSignature,
    ) -> str:
        """Generate complete function body with signature, docstring, and code.

        Args:
            selection: Code selection
            signature: Function signature

        Returns:
            Complete function code
        """
        lines = []

        # Add signature
        if self.language == "python":
            lines.append(signature.to_python_signature())
        elif self.language in ("typescript", "javascript"):
            lines.append(signature.to_typescript_signature())

        # Add docstring
        if signature.docstring:
            docstring_lines = signature.docstring.split("\n")
            for line in docstring_lines:
                lines.append(f"    {line}")

        # Add function body (selection content with proper indentation)
        content_lines = selection.content.split("\n")
        for line in content_lines:
            # Add extra indentation for function body
            if line.strip():
                lines.append(f"    {line}")
            else:
                lines.append("")

        # Add return statement if needed
        if selection.return_values:
            return_stmt = self._generate_return_statement(selection.return_values)
            lines.append(f"    {return_stmt}")

        if self.language in ("typescript", "javascript"):
            lines.append("}")

        return "\n".join(lines)

    def _generate_return_statement(self, return_values: List[str]) -> str:
        """Generate return statement for extracted function.

        Args:
            return_values: List of variable names to return

        Returns:
            Return statement
        """
        if len(return_values) == 0:
            return ""
        elif len(return_values) == 1:
            return f"return {return_values[0]}"
        else:
            # Multiple returns - tuple for Python, array for JS/TS
            if self.language == "python":
                return f"return {', '.join(return_values)}"
            else:
                return f"return [{', '.join(return_values)}]"

    def _generate_call_site(
        self,
        selection: CodeSelection,
        signature: FunctionSignature,
    ) -> str:
        """Generate code to replace selection with function call.

        Args:
            selection: Code selection
            signature: Function signature

        Returns:
            Call site replacement code
        """
        # Build argument list
        args = ", ".join(signature.parameters[i]["name"] for i in range(len(signature.parameters)))

        # Generate call
        function_call = f"{signature.name}({args})"

        # Handle return value assignment
        if len(selection.return_values) == 0:
            return f"{selection.indentation}{function_call}"
        elif len(selection.return_values) == 1:
            return f"{selection.indentation}{selection.return_values[0]} = {function_call}"
        else:
            # Multiple returns - tuple unpacking
            vars_str = ", ".join(selection.return_values)
            return f"{selection.indentation}{vars_str} = {function_call}"

    def _find_import_section_end(self, file_path: str) -> int:
        """Find the line number after the import section ends.

        Args:
            file_path: Path to the source file

        Returns:
            Line number after last import (1-indexed), or 1 if no imports
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.warning("failed_to_read_file_for_imports", error=str(e))
            return 1

        last_import_line, _ = self._scan_imports(lines)
        return last_import_line + 1 if last_import_line > 0 else 1

    def _scan_imports(self, lines: list[str]) -> tuple[int, bool]:
        """Scan lines for import statements.

        Args:
            lines: Source file lines

        Returns:
            Tuple of (last_import_line, in_multiline_import)
        """
        last_import_line = 0
        in_multiline = False

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()

            if self._should_skip_line(stripped):
                continue

            if self._is_import_start(stripped):
                last_import_line = i
                in_multiline = self._check_multiline_import(stripped)
            elif in_multiline:
                last_import_line = i
                if ")" in stripped:
                    in_multiline = False
            elif last_import_line > 0:
                break

        return last_import_line, in_multiline

    def _should_skip_line(self, stripped: str) -> bool:
        """Check if line should be skipped (empty or comment)."""
        return not stripped or stripped.startswith("#")

    def _is_import_start(self, stripped: str) -> bool:
        """Check if line starts an import statement."""
        return stripped.startswith("import ") or stripped.startswith("from ")

    def _check_multiline_import(self, stripped: str) -> bool:
        """Check if import starts a multiline block."""
        return "(" in stripped and ")" not in stripped

    def _determine_insertion_line(
        self,
        selection: CodeSelection,
        extract_location: str,
    ) -> int:
        """Determine where to insert the extracted function.

        Args:
            selection: Code selection
            extract_location: 'before', 'after', or 'top'

        Returns:
            Line number for insertion (1-indexed)
        """
        if extract_location == "before":
            # Insert before the selection, leaving some space
            return max(1, selection.start_line - 2)
        elif extract_location == "after":
            # Insert after the selection
            return selection.end_line + 2
        elif extract_location == "top":
            # Insert at top of file (after imports)
            return self._find_import_section_end(selection.file_path)
        else:
            return selection.start_line - 2

    def _generate_diff_preview(
        self,
        selection: CodeSelection,
        function_body: str,
        call_replacement: str,
        insertion_line: int,
    ) -> str:
        """Generate unified diff preview of changes.

        Args:
            selection: Code selection
            function_body: Generated function code
            call_replacement: Call site replacement
            insertion_line: Where function will be inserted

        Returns:
            Unified diff string
        """
        lines = []
        lines.append(f"--- {selection.file_path}")
        lines.append(f"+++ {selection.file_path}")
        lines.append(f"@@ -{selection.start_line},{selection.end_line - selection.start_line + 1} +{insertion_line},... @@")

        # Show function insertion
        lines.append(f"+ {function_body.split(chr(10))[0]}")  # First line of function
        lines.append("+   ...")
        lines.append("+")

        # Show call site replacement
        lines.append(f"- {selection.content.split(chr(10))[0]}")  # First line of original
        lines.append("-   ...")
        lines.append(f"+ {call_replacement}")

        return "\n".join(lines)

    def _apply_extraction(
        self,
        selection: CodeSelection,
        function_body: str,
        call_replacement: str,
        insertion_line: int,
    ) -> str:
        """Apply the function extraction to the file.

        Args:
            selection: Code selection
            function_body: Generated function code
            call_replacement: Call site replacement
            insertion_line: Where to insert function

        Returns:
            Backup ID for rollback
        """
        # Create backup
        import os

        project_folder = os.path.dirname(selection.file_path)
        backup_id = create_backup([selection.file_path], project_folder)

        try:
            # Read file
            with open(selection.file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Insert function at insertion_line
            function_lines = [line + "\n" for line in function_body.split("\n")]
            function_lines.append("\n\n")  # Add spacing
            lines[insertion_line - 1 : insertion_line - 1] = function_lines

            # Replace selection with call
            # Adjust line numbers after insertion
            adjusted_start = selection.start_line + len(function_lines)
            adjusted_end = selection.end_line + len(function_lines)

            call_line = call_replacement + "\n"
            lines[adjusted_start - 1 : adjusted_end] = [call_line]

            # Write file
            with open(selection.file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.info(
                "extraction_applied",
                file_path=selection.file_path,
                backup_id=backup_id,
            )

            return backup_id

        except Exception as e:
            # Rollback on error
            restore_backup(backup_id, project_folder)
            raise RuntimeError(f"Failed to apply extraction: {e}")
