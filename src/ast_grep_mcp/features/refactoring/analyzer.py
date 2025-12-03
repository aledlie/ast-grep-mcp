"""Code selection analyzer for refactoring operations.

This module analyzes selected code regions to determine:
- Variables used and their classification (local, parameter, global)
- Parameters needed for extracted functions
- Return values required
- Scope and dependencies
"""

import re
from typing import Dict, List

from ast_grep_mcp.core.logging import get_logger

from ...models.refactoring import (
    CodeSelection,
    VariableInfo,
    VariableType,
)

logger = get_logger(__name__)


class CodeSelectionAnalyzer:
    """Analyzes code selections for refactoring operations."""

    def __init__(self, language: str) -> None:
        """Initialize analyzer for specific language.

        Args:
            language: Programming language (python, typescript, javascript, java)
        """
        self.language = language
        self._variable_patterns = self._get_variable_patterns(language)

    def analyze_selection(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        project_folder: str,
    ) -> CodeSelection:
        """Analyze a code selection for refactoring.

        Args:
            file_path: Path to the file containing selection
            start_line: Starting line of selection (1-indexed)
            end_line: Ending line of selection (1-indexed)
            project_folder: Project root folder

        Returns:
            CodeSelection with analysis results
        """
        logger.info(
            "analyzing_code_selection",
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            language=self.language,
        )

        # Read the selected code
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        selection_lines = lines[start_line - 1 : end_line]
        content = "".join(selection_lines)

        # Detect indentation
        indentation = self._detect_indentation(selection_lines)

        # Create selection object
        selection = CodeSelection(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            language=self.language,
            content=content,
            indentation=indentation,
        )

        # Analyze variables
        self._analyze_variables(selection, lines, project_folder)

        # Determine parameters and return values
        self._determine_parameters_and_returns(selection)

        # Check for early returns and exceptions
        selection.has_early_returns = self._has_early_returns(content)
        selection.has_exceptions = self._has_exception_handling(content)

        logger.info(
            "code_selection_analyzed",
            variables_found=len(selection.variables),
            parameters_needed=len(selection.parameters_needed),
            return_values=len(selection.return_values),
        )

        return selection

    def _detect_indentation(self, lines: List[str]) -> str:
        """Detect indentation style from code lines.

        Args:
            lines: Lines of code

        Returns:
            Indentation string (spaces or tabs)
        """
        for line in lines:
            if line.strip() and line[0] in (" ", "\t"):
                # Extract leading whitespace
                indent = len(line) - len(line.lstrip())
                return line[:indent]

        return ""  # No indentation detected

    def _analyze_variables(
        self,
        selection: CodeSelection,
        all_lines: List[str],
        project_folder: str,
    ) -> None:
        """Analyze variables in selection.

        Identifies:
        - Variables read (used)
        - Variables written (assigned)
        - Variable scope (local, parameter, global)

        Args:
            selection: CodeSelection to populate with variable info
            all_lines: All lines in the file (for context)
            project_folder: Project root for ast-grep search
        """
        _content = selection.content  # noqa: F841
        variables: Dict[str, VariableInfo] = {}

        # Find all variable references using ast-grep patterns
        if self.language == "python":
            self._analyze_python_variables(selection, variables, all_lines, project_folder)
        elif self.language in ("typescript", "javascript"):
            self._analyze_js_ts_variables(selection, variables, all_lines, project_folder)
        elif self.language == "java":
            self._analyze_java_variables(selection, variables, all_lines, project_folder)

        selection.variables = list(variables.values())

    # Python keywords set - shared across multiple methods
    _PYTHON_KEYWORDS = {
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    }

    def _find_python_assignments(
        self,
        content: str,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
    ) -> None:
        """Find variable assignments in Python code.

        Args:
            content: Source code content
            selection: Code selection metadata
            variables: Dict to populate with variable info
        """
        assignment_pattern = r"\b(\w+)\s*="
        for match in re.finditer(assignment_pattern, content):
            var_name = match.group(1)
            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.LOCAL,
                    first_use_line=selection.start_line,
                    is_written=True,
                )
            else:
                variables[var_name].is_written = True

    def _find_python_base_variables(
        self,
        content: str,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
    ) -> None:
        """Find base variables used in subscripts, attributes, and calls.

        Identifies variables in patterns like:
        - variable[...] (subscript)
        - variable.attr (attribute access)
        - variable(...) (function call, excluding method calls)

        Args:
            content: Source code content
            selection: Code selection metadata
            variables: Dict to populate with variable info
        """
        base_vars_found = set()

        # Array/dict access: var[...]
        for match in re.finditer(r"\b([a-zA-Z_]\w*)\s*\[", content):
            var_name = match.group(1)
            if var_name not in self._PYTHON_KEYWORDS:
                base_vars_found.add(var_name)

        # Attribute access: var.attr
        for match in re.finditer(r"\b([a-zA-Z_]\w*)\s*\.", content):
            var_name = match.group(1)
            if var_name not in self._PYTHON_KEYWORDS:
                base_vars_found.add(var_name)

        # Function call: var(...) but NOT method calls like obj.method()
        for match in re.finditer(r"(?<!\.)\b([a-zA-Z_]\w*)\s*\(", content):
            var_name = match.group(1)
            if var_name not in self._PYTHON_KEYWORDS:
                base_vars_found.add(var_name)

        # Register base variables as reads
        for var_name in base_vars_found:
            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.PARAMETER,
                    first_use_line=selection.start_line,
                    is_read=True,
                )
            else:
                variables[var_name].is_read = True

    def _is_in_string_or_comment(self, content: str, match_pos: int) -> bool:
        """Check if a match position is inside a string literal or comment.

        Args:
            content: Source code content
            match_pos: Position of the match

        Returns:
            True if inside string or comment, False otherwise
        """
        # Check if inside string (simple heuristic using quote counts)
        before_text = content[:match_pos]
        if before_text.count("'") % 2 == 1 or before_text.count('"') % 2 == 1:
            return True

        # Check if in a comment (appears after # on same line)
        line_start = content.rfind("\n", 0, match_pos) + 1
        line_to_match = content[line_start:match_pos]
        if "#" in line_to_match:
            return True

        return False

    def _find_python_standalone_identifiers(
        self,
        content: str,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
    ) -> None:
        """Find standalone identifiers not part of subscript/attribute/call.

        Matches identifiers that:
        - Aren't preceded by a dot (not method names)
        - Aren't followed by [, ., or ( (not being accessed)
        - Aren't keywords or in strings/comments

        Args:
            content: Source code content
            selection: Code selection metadata
            variables: Dict to populate with variable info
        """
        identifier_pattern = r"(?<!\.)(?<!\#)\b([a-zA-Z_]\w*)(?!\s*[\[\.\(])\b"
        for match in re.finditer(identifier_pattern, content):
            var_name = match.group(1)

            # Skip keywords
            if var_name in self._PYTHON_KEYWORDS:
                continue

            # Skip if in string or comment
            if self._is_in_string_or_comment(content, match.start()):
                continue

            # Register identifier as read
            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.PARAMETER,
                    first_use_line=selection.start_line,
                    is_read=True,
                )
            else:
                variables[var_name].is_read = True

    def _analyze_python_variables(
        self,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
        all_lines: List[str],
        project_folder: str,
    ) -> None:
        """Analyze Python variables in selection.

        Uses regex patterns to identify:
        - Assignments (x = ...)
        - Function calls (func(...))
        - Attribute access (obj.attr)
        - Variable references

        Args:
            selection: Code selection
            variables: Dict to populate with variable info
            all_lines: All file lines
            project_folder: Project root
        """
        content = selection.content

        # Find assignments (variables being written)
        self._find_python_assignments(content, selection, variables)

        # Find base variables (subscripts, attributes, calls)
        self._find_python_base_variables(content, selection, variables)

        # Find standalone identifiers
        self._find_python_standalone_identifiers(content, selection, variables)

        # Classify variables based on scope analysis
        self._classify_variable_types(selection, variables, all_lines)

    def _is_variable_defined_before(
        self,
        var_name: str,
        before_lines: List[str],
    ) -> bool:
        """Check if variable is defined before selection.

        Args:
            var_name: Variable name to check
            before_lines: Lines before the selection

        Returns:
            True if variable is assigned before selection
        """
        return any(re.search(rf"\b{re.escape(var_name)}\s*=", line) for line in before_lines)

    def _is_variable_used_after(
        self,
        var_name: str,
        after_lines: List[str],
    ) -> bool:
        """Check if variable is used after selection.

        Args:
            var_name: Variable name to check
            after_lines: Lines after the selection

        Returns:
            True if variable is referenced after selection
        """
        return any(re.search(rf"\b{re.escape(var_name)}\b", line) for line in after_lines)

    def _get_variable_classification(
        self,
        var_info: VariableInfo,
        defined_before: bool,
        used_after: bool,
    ) -> VariableType:
        """Classify variable type based on usage pattern.

        Classification rules:
        - Written in selection, not defined before, used after → MODIFIED
        - Written in selection, not defined before, not used after → LOCAL
        - Only read, defined before → PARAMETER
        - Only read, not defined before → PARAMETER (global/builtin)
        - Written and defined before and used after → MODIFIED

        Args:
            var_info: Variable information
            defined_before: True if defined before selection
            used_after: True if used after selection

        Returns:
            Appropriate VariableType
        """
        is_written = var_info.is_written
        is_read = var_info.is_read

        # Created in selection
        if is_written and not defined_before:
            return VariableType.MODIFIED if used_after else VariableType.LOCAL

        # Only read (must be parameter)
        if is_read and not is_written:
            return VariableType.PARAMETER

        # Modified existing variable
        if is_written and defined_before and used_after:
            return VariableType.MODIFIED

        # Default: keep existing type
        return var_info.variable_type

    def _analyze_js_ts_variables(
        self,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
        all_lines: List[str],
        project_folder: str,
    ) -> None:
        """Analyze JavaScript/TypeScript variables in selection.

        Args:
            selection: Code selection
            variables: Dict to populate with variable info
            all_lines: All file lines
            project_folder: Project root
        """
        content = selection.content

        # Find variable declarations and assignments
        # Matches: const x = ..., let y = ..., var z = ..., x = ...
        declaration_pattern = r"\b(?:const|let|var)?\s*(\w+)\s*="
        for match in re.finditer(declaration_pattern, content):
            var_name = match.group(1)
            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.LOCAL,
                    first_use_line=selection.start_line,
                    is_written=True,
                )
            else:
                variables[var_name].is_written = True

        # Find variable reads
        js_keywords = {
            "await",
            "break",
            "case",
            "catch",
            "class",
            "const",
            "continue",
            "debugger",
            "default",
            "delete",
            "do",
            "else",
            "enum",
            "export",
            "extends",
            "false",
            "finally",
            "for",
            "function",
            "if",
            "import",
            "in",
            "instanceof",
            "let",
            "new",
            "null",
            "return",
            "super",
            "switch",
            "this",
            "throw",
            "true",
            "try",
            "typeof",
            "var",
            "void",
            "while",
            "with",
            "yield",
            "async",
            "of",
        }

        identifier_pattern = r"\b([a-zA-Z_$]\w*)\b"
        for match in re.finditer(identifier_pattern, content):
            var_name = match.group(1)

            if var_name in js_keywords:
                continue

            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.PARAMETER,
                    first_use_line=selection.start_line,
                    is_read=True,
                )
            else:
                variables[var_name].is_read = True

        self._classify_variable_types(selection, variables, all_lines)

    def _analyze_java_variables(
        self,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
        all_lines: List[str],
        project_folder: str,
    ) -> None:
        """Analyze Java variables in selection.

        Args:
            selection: Code selection
            variables: Dict to populate with variable info
            all_lines: All file lines
            project_folder: Project root
        """
        content = selection.content

        # Find variable declarations and assignments
        # Matches: Type var = ..., var = ...
        declaration_pattern = r"\b(?:\w+\s+)?(\w+)\s*="
        for match in re.finditer(declaration_pattern, content):
            var_name = match.group(1)
            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.LOCAL,
                    first_use_line=selection.start_line,
                    is_written=True,
                )
            else:
                variables[var_name].is_written = True

        # Find variable reads
        java_keywords = {
            "abstract",
            "assert",
            "boolean",
            "break",
            "byte",
            "case",
            "catch",
            "char",
            "class",
            "const",
            "continue",
            "default",
            "do",
            "double",
            "else",
            "enum",
            "extends",
            "final",
            "finally",
            "float",
            "for",
            "goto",
            "if",
            "implements",
            "import",
            "instanceof",
            "int",
            "interface",
            "long",
            "native",
            "new",
            "package",
            "private",
            "protected",
            "public",
            "return",
            "short",
            "static",
            "strictfp",
            "super",
            "switch",
            "synchronized",
            "this",
            "throw",
            "throws",
            "transient",
            "try",
            "void",
            "volatile",
            "while",
            "true",
            "false",
            "null",
        }

        identifier_pattern = r"\b([a-zA-Z_]\w*)\b"
        for match in re.finditer(identifier_pattern, content):
            var_name = match.group(1)

            if var_name in java_keywords:
                continue

            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.PARAMETER,
                    first_use_line=selection.start_line,
                    is_read=True,
                )
            else:
                variables[var_name].is_read = True

        self._classify_variable_types(selection, variables, all_lines)

    def _classify_variable_types(
        self,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
        all_lines: List[str],
    ) -> None:
        """Classify variables by type based on scope analysis.

        Updates variable_type in variables dict:
        - LOCAL: Defined within selection, not used outside
        - PARAMETER: Used but not defined in selection
        - MODIFIED: Modified in selection, needs to be returned
        - GLOBAL: Module or global scope
        - CLOSURE: From enclosing function scope

        Args:
            selection: Code selection
            variables: Dict of variables to classify
            all_lines: All file lines for context
        """
        # Get lines before and after selection for context
        before_lines = all_lines[: selection.start_line - 1]
        after_lines = all_lines[selection.end_line :]

        for var_name, var_info in variables.items():
            # Detect scope context
            defined_before = self._is_variable_defined_before(var_name, before_lines)
            used_after = self._is_variable_used_after(var_name, after_lines)

            # Classify based on usage pattern
            var_info.variable_type = self._get_variable_classification(
                var_info,
                defined_before,
                used_after,
            )

    def _determine_parameters_and_returns(self, selection: CodeSelection) -> None:
        """Determine which variables should be parameters and return values.

        Args:
            selection: Code selection to update
        """
        # Parameters: Variables that need to be passed in
        parameters = selection.get_variables_by_type(VariableType.PARAMETER)
        selection.parameters_needed = [v.name for v in parameters if v.is_read]

        # Return values: Variables that need to be returned
        modified_vars = selection.get_variables_by_type(VariableType.MODIFIED)
        selection.return_values = [v.name for v in modified_vars]

    def _has_early_returns(self, content: str) -> bool:
        """Check if selection contains early return statements.

        Args:
            content: Code content

        Returns:
            True if early returns detected
        """
        return bool(re.search(r"\breturn\b", content))

    def _has_exception_handling(self, content: str) -> bool:
        """Check if selection contains exception handling.

        Args:
            content: Code content

        Returns:
            True if try/except/throw detected
        """
        if self.language == "python":
            return bool(re.search(r"\b(try|except|raise)\b", content))
        elif self.language in ("typescript", "javascript"):
            return bool(re.search(r"\b(try|catch|throw)\b", content))
        elif self.language == "java":
            return bool(re.search(r"\b(try|catch|throw)\b", content))

        return False

    def _get_variable_patterns(self, language: str) -> Dict[str, str]:
        """Get language-specific variable patterns.

        Args:
            language: Programming language

        Returns:
            Dict of ast-grep patterns for variable detection
        """
        patterns = {
            "python": {
                "assignment": "$VAR = $VALUE",
                "variable_ref": "$VAR",
            },
            "typescript": {
                "declaration": "const $VAR = $VALUE",
                "variable_ref": "$VAR",
            },
            "javascript": {
                "declaration": "const $VAR = $VALUE",
                "variable_ref": "$VAR",
            },
            "java": {
                "declaration": "$TYPE $VAR = $VALUE",
                "variable_ref": "$VAR",
            },
        }

        return patterns.get(language, patterns["python"])
